#!/usr/bin/env python3
"""
Script för att generera företagsbeskrivningar med Claude AI.

Läser skrapad hemsidetext från CSV och genererar inspirerande
3-menings beskrivningar i rätt stil.

Användning:
    export ANTHROPIC_API_KEY="your-api-key"
    python3 scripts/generate_descriptions.py --input results/scraped_websites.csv
    python3 scripts/generate_descriptions.py --input results/scraped_websites.csv --limit 10
"""

import sqlite3
import csv
import argparse
import sys
import time
from pathlib import Path
from datetime import datetime
import os

try:
    from anthropic import Anthropic
except ImportError:
    print("❌ Fel: 'anthropic' library saknas!")
    print("Installera med: pip install anthropic")
    sys.exit(1)


def get_example_descriptions(cursor, limit=8):
    """
    Hämta exempel på bra descriptions från databasen.
    """
    cursor.execute('''
        SELECT name, description, type
        FROM companies
        WHERE description IS NOT NULL
        AND description != ''
        AND length(description) BETWEEN 150 AND 600
        ORDER BY data_quality_score DESC, RANDOM()
        LIMIT ?
    ''', (limit,))

    examples = []
    for name, desc, ctype in cursor.fetchall():
        examples.append({
            'name': name,
            'description': desc,
            'type': ctype
        })

    return examples


def get_company_metadata(cursor, company_id):
    """
    Hämta sectors, domains och dimensions för ett företag.
    """
    metadata = {
        'sectors': [],
        'domains': [],
        'dimensions': []
    }

    # Hämta sectors
    cursor.execute('''
        SELECT s.name FROM sectors s
        JOIN company_sectors cs ON s.id = cs.sector_id
        WHERE cs.company_id = ?
    ''', (company_id,))
    metadata['sectors'] = [row[0] for row in cursor.fetchall()]

    # Hämta domains
    cursor.execute('''
        SELECT d.name FROM domains d
        JOIN company_domains cd ON d.id = cd.domain_id
        WHERE cd.company_id = ?
    ''', (company_id,))
    metadata['domains'] = [row[0] for row in cursor.fetchall()]

    # Hämta dimensions
    cursor.execute('''
        SELECT d.name FROM dimensions d
        JOIN company_dimensions cd ON d.id = cd.dimension_id
        WHERE cd.company_id = ?
    ''', (company_id,))
    metadata['dimensions'] = [row[0] for row in cursor.fetchall()]

    return metadata


def build_prompt(company_name, company_type, scraped_text, meta_description, metadata, examples):
    """
    Bygg prompt för Claude att generera description.
    """
    # Bygg exempel-sektionen
    examples_text = "\n\n".join([
        f"Företag: {ex['name']} (typ: {ex['type']})\nBeskrivning: {ex['description']}"
        for ex in examples[:5]  # Ta max 5 exempel
    ])

    # Bygg metadata-text
    metadata_parts = []
    if metadata['sectors']:
        metadata_parts.append(f"Bransch/Sektor: {', '.join(metadata['sectors'])}")
    if metadata['domains']:
        metadata_parts.append(f"Affärsområden: {', '.join(metadata['domains'])}")
    if metadata['dimensions']:
        metadata_parts.append(f"AI-dimensioner: {', '.join(metadata['dimensions'])}")

    metadata_text = "\n".join(metadata_parts) if metadata_parts else "Ingen tillgänglig metadata"

    # Förkortad hemsidetext (max 2000 tecken)
    website_text = scraped_text[:2000] if scraped_text else "Ingen hemsidetext tillgänglig"

    prompt = f"""Du är en expert på att skriva inspirerande och koncisa företagsbeskrivningar för en AI-företagsdatabas.

Din uppgift är att skriva en kort, professionell beskrivning av företaget nedan. Beskrivningen ska vara exakt 3 meningar lång.

STIL OCH TON:
- Professionell men inspirerande
- Värdefokuserad (vad företaget gör och vilken nytta det ger)
- Konkret (undvik fluff och tomma ord)
- Kan vara på svenska eller engelska beroende på företagets kommunikation

STRUKTUR (3 meningar):
1. Vad företaget gör / huvudsaklig verksamhet
2. Hur de gör det / teknologi / metod / fokusområde
3. Värde / nytta / resultat för kunder/samhälle

EXEMPEL PÅ BRA BESKRIVNINGAR:

{examples_text}

---

FÖRETAG ATT BESKRIVA:

Företagsnamn: {company_name}
Typ: {company_type}

Metadata från databas:
{metadata_text}

Meta description från hemsida:
{meta_description or 'Ingen tillgänglig'}

Text från hemsida:
{website_text}

---

Skriv nu en 3-menings beskrivning av företaget {company_name}. Svara ENDAST med beskrivningen, ingen extra text."""

    return prompt


def generate_description(client, company_data, metadata, examples):
    """
    Generera description med Claude AI.
    """
    company_name = company_data['name']
    company_type = company_data['type']
    scraped_text = company_data.get('scraped_text', '')
    meta_description = company_data.get('meta_description', '')

    print(f"\n🤖 Genererar beskrivning för: {company_name}")

    # Bygg prompt
    prompt = build_prompt(
        company_name,
        company_type,
        scraped_text,
        meta_description,
        metadata,
        examples
    )

    try:
        # Anropa Claude API
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Snabb och billig modell
            max_tokens=500,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        description = message.content[0].text.strip()

        # Validera att det är ca 3 meningar
        sentence_count = description.count('.') + description.count('!') + description.count('?')

        if sentence_count < 2 or sentence_count > 5:
            print(f"   ⚠ Varning: Beskrivningen har {sentence_count} meningar (förväntat 3)")

        print(f"   ✓ Genererad beskrivning ({len(description)} tecken, ~{sentence_count} meningar)")
        print(f"   📝 \"{description[:80]}...\"")

        return {
            'description': description,
            'status': 'success',
            'sentence_count': sentence_count,
            'char_count': len(description)
        }

    except Exception as e:
        print(f"   ✗ Fel: {type(e).__name__}: {str(e)}")
        return {
            'description': '',
            'status': f'error_{type(e).__name__}',
            'sentence_count': 0,
            'char_count': 0
        }


def main():
    parser = argparse.ArgumentParser(description='Generera företagsbeskrivningar med Claude AI')
    parser.add_argument('--input', required=True, help='Input CSV från scrape_company_websites.py')
    parser.add_argument('--db', default='databases/ai_companies.db', help='Sökväg till databas')
    parser.add_argument('--output', default='results/generated_descriptions.csv', help='Output CSV-fil')
    parser.add_argument('--limit', type=int, help='Begränsa antal företag (för test)')
    parser.add_argument('--api-key', help='Anthropic API key (eller sätt ANTHROPIC_API_KEY env var)')
    parser.add_argument('--delay', type=float, default=0.5, help='Fördröjning mellan API-anrop (sekunder)')
    args = parser.parse_args()

    # Skapa results-mapp om den inte finns
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🤖 DESCRIPTION GENERATOR - CLAUDE AI")
    print("=" * 70)

    # Hämta API key
    api_key = args.api_key or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("\n❌ Fel: Ingen API key hittades!")
        print("Sätt ANTHROPIC_API_KEY environment variable eller använd --api-key")
        print("\nExempel:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("  python3 scripts/generate_descriptions.py --input results/scraped_websites.csv")
        sys.exit(1)

    # Initiera Claude client
    client = Anthropic(api_key=api_key)
    print("✓ Claude AI client initierad")

    # Läs input CSV
    print(f"\n📂 Läser skrapad data från: {args.input}")
    if not Path(args.input).exists():
        print(f"❌ Fel: Filen {args.input} finns inte!")
        sys.exit(1)

    with open(args.input, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        scraped_data = list(reader)

    # Filtrera bort misslyckade skrapningar
    successful_scrapes = [
        row for row in scraped_data
        if row.get('status') in ['success', 'success_http'] and row.get('scraped_text')
    ]

    print(f"✓ Läste {len(scraped_data)} rader")
    print(f"✓ {len(successful_scrapes)} lyckade skrapningar att bearbeta")

    if args.limit:
        successful_scrapes = successful_scrapes[:args.limit]
        print(f"⚠ TESTLÄGE: Begränsat till {args.limit} företag")

    if not successful_scrapes:
        print("❌ Inga företag att bearbeta!")
        sys.exit(1)

    # Anslut till databas
    print(f"\n📂 Ansluter till databas: {args.db}")
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    # Hämta exempel-descriptions
    print("📚 Hämtar exempel-beskrivningar från databasen...")
    examples = get_example_descriptions(cursor, limit=8)
    print(f"✓ Hämtade {len(examples)} exempel-beskrivningar")

    # Generera descriptions
    print("\n" + "=" * 70)
    print("🚀 STARTAR GENERERING")
    print("=" * 70)
    print(f"⏱️  Fördröjning mellan API-anrop: {args.delay}s")
    print(f"💰 Kostnad (uppskattad): ~${len(successful_scrapes) * 0.0003:.4f}")

    results = []
    success_count = 0

    for i, row in enumerate(successful_scrapes, 1):
        company_id = row['id']
        company_name = row['name']

        print(f"\n[{i}/{len(successful_scrapes)}] " + "=" * 60)
        print(f"ID: {company_id} | {company_name}")

        # Hämta metadata från databas
        metadata = get_company_metadata(cursor, company_id)

        if metadata['sectors'] or metadata['domains']:
            print(f"📊 Metadata: {len(metadata['sectors'])} sectors, {len(metadata['domains'])} domains")

        # Generera description
        gen_result = generate_description(client, row, metadata, examples)

        results.append({
            'id': company_id,
            'name': company_name,
            'website': row.get('website', ''),
            'type': row.get('type', ''),
            'generated_description': gen_result['description'],
            'char_count': gen_result['char_count'],
            'sentence_count': gen_result['sentence_count'],
            'sectors': ', '.join(metadata['sectors']),
            'domains': ', '.join(metadata['domains']),
            'status': gen_result['status']
        })

        if gen_result['status'] == 'success':
            success_count += 1

        # Vänta lite mellan API-anrop
        if i < len(successful_scrapes):
            time.sleep(args.delay)

    # Exportera resultat
    print("\n" + "=" * 70)
    print("📊 EXPORTERAR RESULTAT")
    print("=" * 70)

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'name', 'website', 'type', 'generated_description',
                      'char_count', 'sentence_count', 'sectors', 'domains', 'status']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Statistik
    failed = len(results) - success_count
    success_rate = (success_count / len(results) * 100) if results else 0

    avg_chars = sum(r['char_count'] for r in results) / len(results) if results else 0
    avg_sentences = sum(r['sentence_count'] for r in results) / len(results) if results else 0

    print(f"\n✅ Exporterat till: {args.output}")
    print(f"\n📈 RESULTAT:")
    print(f"   ✓ Lyckade genereringar: {success_count}")
    print(f"   ✗ Misslyckade: {failed}")
    print(f"   📊 Total: {len(results)}")
    print(f"   🎯 Framgångsgrad: {success_rate:.1f}%")
    print(f"\n📝 KVALITET:")
    print(f"   Genomsnittlig längd: {avg_chars:.0f} tecken")
    print(f"   Genomsnittligt antal meningar: {avg_sentences:.1f}")

    conn.close()

    print("\n" + "=" * 70)
    print("✓ KLART!")
    print("=" * 70)
    print(f"\n💡 Nästa steg: Granska {args.output} och importera de bra beskrivningarna till databasen")


if __name__ == '__main__':
    main()

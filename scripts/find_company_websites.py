#!/usr/bin/env python3
"""
Script för att hitta företagshemsidor via smart domängissning.

Läser företag från ai_companies.db som saknar website och:
1. Genererar troliga domännamn baserat på företagsnamn
2. Verifierar via DNS-lookup om domänen existerar
3. Besöker sidan och verifierar att företagsnamnet finns där
4. Exporterar resultat till CSV

Användning:
    python3 scripts/find_company_websites.py
    python3 scripts/find_company_websites.py --limit 10  # Testa på 10 företag först
"""

import sqlite3
import re
import socket
import requests
import csv
from datetime import datetime
from urllib.parse import urlparse
import argparse
import sys
from pathlib import Path

# Timeout för HTTP requests
HTTP_TIMEOUT = 10
DNS_TIMEOUT = 5

# TLDs att testa (i prioritetsordning)
TLDS = ['.se', '.com', '.ai', '.io', '.net', '.org']


def normalize_company_name(name):
    """
    Normalisera företagsnamn för domängenerering.

    Tar bort:
    - AB, Aktiebolag
    - Special characters
    - Extra mellanslag
    """
    # Ta bort vanliga företagsformer
    name = re.sub(r'\b(AB|Aktiebolag|Ltd|Limited|Inc|Corp|Corporation)\b', '', name, flags=re.IGNORECASE)

    # Ta bort allt inom parentes
    name = re.sub(r'\([^)]*\)', '', name)

    # Ta bort special characters men behåll bindestreck och mellanslag
    name = re.sub(r'[^\w\s-]', '', name)

    # Ta bort extra mellanslag
    name = ' '.join(name.split())

    return name.strip()


def generate_domain_variants(company_name):
    """
    Generera troliga domännamn baserat på företagsnamn.

    Exempel:
    - "Knowing Company" -> knowingcompany, knowing-company, knowing
    - "Layke Analytics" -> laykeanalytics, layke-analytics, layke
    """
    normalized = normalize_company_name(company_name)
    variants = []

    # Variant 1: Allt ihop utan mellanslag (knowingcompany)
    no_spaces = normalized.lower().replace(' ', '').replace('-', '')
    if no_spaces:
        variants.append(no_spaces)

    # Variant 2: Med bindestreck istället för mellanslag (knowing-company)
    with_dash = normalized.lower().replace(' ', '-')
    if with_dash and with_dash != no_spaces:
        variants.append(with_dash)

    # Variant 3: Första ordet (knowing)
    words = normalized.split()
    if len(words) > 1 and words[0].lower() not in ['the', 'a', 'an']:
        variants.append(words[0].lower())

    # Variant 4: Utan bindestreck om det finns (knowingcompany från knowing-company)
    if '-' in normalized:
        no_dash = normalized.lower().replace('-', '').replace(' ', '')
        if no_dash not in variants:
            variants.append(no_dash)

    return variants


def dns_lookup(domain):
    """
    DNS lookup - DEPRECATED: Används inte längre.
    HTTP request testar både DNS och tillgänglighet i ett svep.
    """
    # Inte använd - HTTP request gör jobbet
    return True


def verify_website(url, company_name):
    """
    Besök en URL och verifiera att företagsnamnet finns på sidan.

    Returns:
        tuple: (success: bool, status: str)
    """
    try:
        # Testa både http och https
        for protocol in ['https', 'http']:
            full_url = f"{protocol}://{url}"
            try:
                response = requests.get(
                    full_url,
                    timeout=HTTP_TIMEOUT,
                    allow_redirects=True,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; CompanyFinder/1.0)'}
                )

                if response.status_code == 200:
                    # Kolla om företagsnamnet finns på sidan
                    content = response.text.lower()
                    name_parts = normalize_company_name(company_name).lower().split()

                    # Matcha om minst huvuddelen av namnet finns
                    main_name = name_parts[0] if name_parts else ''
                    if main_name and main_name in content:
                        return True, f"verified_{protocol}"
                    else:
                        # Sidan finns men namnet hittades inte
                        return True, f"exists_no_match_{protocol}"

            except requests.exceptions.SSLError:
                continue  # Prova nästa protokoll
            except requests.exceptions.RequestException:
                continue

        return False, "connection_failed"

    except Exception as e:
        return False, f"error_{type(e).__name__}"


def find_website_for_company(company_id, company_name):
    """
    Försök hitta hemsida för ett företag.

    Returns:
        dict: {
            'id': company_id,
            'name': company_name,
            'website': found_website or '',
            'status': status_message,
            'confidence': confidence_score
        }
    """
    print(f"\n🔍 Söker efter hemsida för: {company_name}")

    # Generera domänvarianter
    variants = generate_domain_variants(company_name)
    print(f"   Genererade {len(variants)} namnvarianter: {variants[:3]}{'...' if len(variants) > 3 else ''}")

    results = []

    # Testa varje variant med olika TLDs
    for variant in variants:
        for tld in TLDS:
            domain = f"{variant}{tld}"

            # HTTP verifiering (testar både DNS och tillgänglighet)
            success, status = verify_website(domain, company_name)

            confidence = 0
            if success:
                if 'verified' in status:
                    confidence = 95  # Hög confidence - namnet finns på sidan
                    print(f"   ✓✓ VERIFIERAD: {domain} - företagsnamnet hittades på sidan!")
                elif 'exists_no_match' in status:
                    confidence = 60  # Medel confidence - sidan finns men namn saknas
                    print(f"   ⚠ OKLAR: {domain} - sidan finns men namnet hittades inte")

                results.append({
                    'domain': domain,
                    'confidence': confidence,
                    'status': status
                })

                # Om vi hittat en verifierad match, avbryt sökningen
                if confidence >= 95:
                    break

        # Om vi hittat en verifierad match, avbryt
        if results and max(r['confidence'] for r in results) >= 95:
            break

    # Returnera bästa resultatet
    if results:
        best = max(results, key=lambda x: x['confidence'])
        return {
            'id': company_id,
            'name': company_name,
            'website': best['domain'],
            'status': best['status'],
            'confidence': best['confidence']
        }
    else:
        print(f"   ✗ Ingen hemsida hittades")
        return {
            'id': company_id,
            'name': company_name,
            'website': '',
            'status': 'no_match_found',
            'confidence': 0
        }


def main():
    parser = argparse.ArgumentParser(description='Hitta företagshemsidor via smart domängissning')
    parser.add_argument('--db', default='databases/ai_companies.db', help='Sökväg till databas')
    parser.add_argument('--limit', type=int, help='Begränsa antal företag att söka (för test)')
    parser.add_argument('--output', default='results/found_websites.csv', help='Output CSV-fil')
    args = parser.parse_args()

    # Skapa results-mapp om den inte finns
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🌐 FÖRETAGSHEMSIDOR - SMART DOMÄNGISSNING")
    print("=" * 70)

    # Anslut till databas
    print(f"\n📂 Läser från databas: {args.db}")
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    # Hämta företag utan website
    query = """
        SELECT id, name, type, location_country
        FROM companies
        WHERE website IS NULL OR website = ''
        ORDER BY id
    """

    if args.limit:
        query += f" LIMIT {args.limit}"

    cursor.execute(query)
    companies = cursor.fetchall()

    print(f"✓ Hittade {len(companies)} företag utan hemsida")

    if args.limit:
        print(f"⚠ TESTLÄGE: Begränsat till {args.limit} företag")

    # Sök efter hemsidor
    results = []
    for i, (company_id, name, company_type, country) in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}] " + "=" * 60)
        print(f"ID: {company_id} | Typ: {company_type} | Land: {country}")

        result = find_website_for_company(company_id, name)
        results.append(result)

    # Exportera resultat
    print("\n" + "=" * 70)
    print("📊 EXPORTERAR RESULTAT")
    print("=" * 70)

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'name', 'website', 'status', 'confidence'])
        writer.writeheader()
        writer.writerows(results)

    # Statistik
    found = sum(1 for r in results if r['website'])
    verified = sum(1 for r in results if r['confidence'] >= 95)
    unclear = sum(1 for r in results if r['confidence'] > 0 and r['confidence'] < 95)
    not_found = sum(1 for r in results if not r['website'])

    print(f"\n✅ Exporterat till: {args.output}")
    print(f"\n📈 RESULTAT:")
    print(f"   ✓ Verifierade hemsidor (95%+ confidence): {verified}")
    print(f"   ⚠ Oklara träffar (behöver granskning): {unclear}")
    print(f"   ✗ Inga träffar: {not_found}")
    print(f"   📊 Total: {len(results)}")
    print(f"   🎯 Träffsäkerhet: {(found/len(results)*100):.1f}%")

    conn.close()

    print("\n" + "=" * 70)
    print("✓ KLART!")
    print("=" * 70)


if __name__ == '__main__':
    main()

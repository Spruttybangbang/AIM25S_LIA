#!/usr/bin/env python3
"""
Script för att importera genererade descriptions till databasen.

Läser CSV med granskade descriptions och uppdaterar databasen.

Användning:
    python3 scripts/import_generated_descriptions.py --input results/generated_descriptions.csv
    python3 scripts/import_generated_descriptions.py --input results/generated_descriptions.csv --dry-run
"""

import sqlite3
import csv
import argparse
import sys
from pathlib import Path
from datetime import datetime


def preview_changes(cursor, updates):
    """
    Visa förhandsgranskning av ändringar.
    """
    print("\n" + "=" * 70)
    print("🔍 FÖRHANDSGRANSKNING AV ÄNDRINGAR")
    print("=" * 70)

    for i, update in enumerate(updates[:5], 1):  # Visa max 5 exempel
        company_id = update['id']

        # Hämta nuvarande description
        cursor.execute('SELECT name, description FROM companies WHERE id = ?', (company_id,))
        result = cursor.fetchone()

        if result:
            name, current_desc = result
            new_desc = update['description']

            print(f"\n[{i}] {name} (ID: {company_id})")
            print("-" * 70)

            if current_desc:
                print(f"NUVARANDE ({len(current_desc)} tecken):")
                print(f'  "{current_desc[:150]}..."' if len(current_desc) > 150 else f'  "{current_desc}"')
            else:
                print("NUVARANDE: (tom)")

            print(f"\nNY ({len(new_desc)} tecken):")
            print(f'  "{new_desc[:150]}..."' if len(new_desc) > 150 else f'  "{new_desc}"')

    if len(updates) > 5:
        print(f"\n... och {len(updates) - 5} till")


def import_descriptions(cursor, csv_file, dry_run=False):
    """
    Importera descriptions från CSV.
    """
    print(f"\n📂 Läser från: {csv_file}")

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"✓ Läste {len(rows)} rader från CSV")

    # Filtrera ut bara lyckade genereringar med text
    valid_updates = []
    for row in rows:
        if (row.get('status') == 'success' and
            row.get('generated_description') and
            len(row.get('generated_description', '').strip()) > 50):
            valid_updates.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['generated_description'].strip()
            })

    print(f"✓ {len(valid_updates)} giltiga beskrivningar att importera")

    if not valid_updates:
        print("❌ Inga beskrivningar att importera!")
        return 0

    # Förhandsgranskning
    preview_changes(cursor, valid_updates)

    if dry_run:
        print("\n" + "=" * 70)
        print("🔵 DRY RUN - Inga ändringar genomförda")
        print("=" * 70)
        return 0

    # Bekräftelse
    print("\n" + "=" * 70)
    print("⚠️  VARNING: Du är på väg att uppdatera databasen!")
    print("=" * 70)
    print(f"Antal företag som kommer uppdateras: {len(valid_updates)}")

    response = input("\nFortsätta? (skriv 'ja' för att bekräfta): ")

    if response.lower() != 'ja':
        print("\n❌ Avbrutet av användaren")
        return 0

    # Uppdatera databasen
    print("\n🔄 Uppdaterar databasen...")

    updated_count = 0
    for update in valid_updates:
        try:
            cursor.execute('''
                UPDATE companies
                SET description = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (update['description'], update['id']))

            updated_count += 1

        except Exception as e:
            print(f"   ✗ Fel vid uppdatering av {update['name']} (ID: {update['id']}): {e}")

    return updated_count


def main():
    parser = argparse.ArgumentParser(description='Importera genererade descriptions till databasen')
    parser.add_argument('--input', required=True, help='Input CSV från generate_descriptions.py')
    parser.add_argument('--db', default='databases/ai_companies.db', help='Sökväg till databas')
    parser.add_argument('--dry-run', action='store_true', help='Visa vad som skulle hända utan att ändra något')
    args = parser.parse_args()

    print("=" * 70)
    print("📥 IMPORT GENERATED DESCRIPTIONS")
    print("=" * 70)

    # Kolla att input-filen finns
    if not Path(args.input).exists():
        print(f"\n❌ Fel: Filen {args.input} finns inte!")
        sys.exit(1)

    # Anslut till databas
    print(f"\n📂 Ansluter till databas: {args.db}")
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    # Importera
    updated_count = import_descriptions(cursor, args.input, dry_run=args.dry_run)

    if updated_count > 0:
        # Committa ändringar
        conn.commit()
        print(f"\n✅ Uppdaterade {updated_count} företag i databasen")

        # Backup-påminnelse
        print("\n💡 TIP: Kontrollera ändringarna med:")
        print("   python3 scripts/export/export_companies_to_csv.py")

    conn.close()

    print("\n" + "=" * 70)
    print("✓ KLART!")
    print("=" * 70)


if __name__ == '__main__':
    main()

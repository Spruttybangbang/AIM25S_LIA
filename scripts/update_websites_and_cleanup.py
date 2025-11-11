#!/usr/bin/env python3
"""
Script för att uppdatera websites och radera tomma företag från databasen.

Läser CSV med manuellt granskade websiteträffar och:
1. Uppdaterar website för företag som har en hemsida
2. Raderar företag som saknar website och andra viktiga uppgifter

Användning:
    python3 scripts/update_websites_and_cleanup.py --input results/found_websites_clean.csv --dry-run
    python3 scripts/update_websites_and_cleanup.py --input results/found_websites_clean.csv
"""

import sqlite3
import csv
import argparse
import sys
from pathlib import Path
from datetime import datetime


def analyze_csv(csv_file):
    """
    Analysera CSV:n och dela upp i uppdateringar vs raderingar.
    """
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Hantera både ; och , som delimiter
        reader = csv.DictReader(f, delimiter=';')
        rows = list(reader)

    updates = []
    deletions = []

    for row in rows:
        company_id = row.get('id', '').strip()
        website = row.get('website', '').strip()

        if not company_id:
            continue

        # Om företaget har en website -> uppdatering
        if website:
            updates.append({
                'id': company_id,
                'name': row.get('name', ''),
                'website': website
            })
        else:
            # Om företaget saknar website och andra uppgifter -> radering
            # Kolla om det finns något annat ifyllt (status, confidence, etc)
            has_other_data = any(
                row.get(col, '').strip()
                for col in row.keys()
                if col not in ['id', 'name', 'website']
            )

            if not has_other_data or row.get('status') == 'no_match_found':
                deletions.append({
                    'id': company_id,
                    'name': row.get('name', '')
                })

    return updates, deletions


def check_company_has_data(cursor, company_id):
    """
    Kolla om ett företag har viktig data utöver namn.

    Returnerar False om företaget kan raderas säkert.
    """
    cursor.execute('''
        SELECT description, logo_url, owner, maturity,
               location_city, accepts_interns, data_quality_score
        FROM companies
        WHERE id = ?
    ''', (company_id,))

    result = cursor.fetchone()
    if not result:
        return False

    # Om något av dessa fält har värde, behåll företaget
    description, logo_url, owner, maturity, city, interns, quality = result

    has_important_data = (
        (description and len(description) > 50) or
        logo_url or
        owner or
        maturity or
        city or
        interns is not None or
        (quality and quality > 50)
    )

    return has_important_data


def preview_changes(cursor, updates, deletions):
    """
    Visa förhandsgranskning av ändringar.
    """
    print("\n" + "=" * 70)
    print("🔍 FÖRHANDSGRANSKNING")
    print("=" * 70)

    if updates:
        print(f"\n📝 UPPDATERINGAR ({len(updates)} företag):")
        print("-" * 70)
        for i, update in enumerate(updates[:10], 1):
            cursor.execute('SELECT name, website FROM companies WHERE id = ?', (update['id'],))
            result = cursor.fetchone()
            if result:
                current_name, current_website = result
                print(f"\n[{i}] {current_name} (ID: {update['id']})")
                print(f"    Nuvarande: {current_website or '(tom)'}")
                print(f"    Ny:        {update['website']}")

        if len(updates) > 10:
            print(f"\n    ... och {len(updates) - 10} till")

    if deletions:
        print(f"\n🗑️  RADERINGAR ({len(deletions)} företag):")
        print("-" * 70)
        for i, deletion in enumerate(deletions[:10], 1):
            cursor.execute('''
                SELECT name, description, logo_url, owner,
                       location_city, data_quality_score
                FROM companies
                WHERE id = ?
            ''', (deletion['id'],))
            result = cursor.fetchone()

            if result:
                name, desc, logo, owner, city, quality = result
                print(f"\n[{i}] {name} (ID: {deletion['id']})")

                info_parts = []
                if desc:
                    info_parts.append(f"description ({len(desc)} tecken)")
                if logo:
                    info_parts.append("logo")
                if owner:
                    info_parts.append(f"owner: {owner}")
                if city:
                    info_parts.append(f"city: {city}")
                if quality:
                    info_parts.append(f"quality: {quality}")

                if info_parts:
                    print(f"    Har data: {', '.join(info_parts)}")
                else:
                    print(f"    Har data: (inget)")

        if len(deletions) > 10:
            print(f"\n    ... och {len(deletions) - 10} till")


def update_websites(cursor, updates):
    """
    Uppdatera websites i databasen.
    """
    updated_count = 0

    for update in updates:
        try:
            cursor.execute('''
                UPDATE companies
                SET website = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (update['website'], update['id']))

            updated_count += 1

        except Exception as e:
            print(f"   ✗ Fel vid uppdatering av {update['name']} (ID: {update['id']}): {e}")

    return updated_count


def delete_companies(cursor, deletions, force=False):
    """
    Radera företag från databasen.

    Om force=False, kontrollera att företaget inte har viktig data först.
    """
    deleted_count = 0
    skipped_count = 0

    for deletion in deletions:
        company_id = deletion['id']

        # Säkerhetskontroll: har företaget viktig data?
        if not force and check_company_has_data(cursor, company_id):
            print(f"   ⚠ Skippar {deletion['name']} (ID: {company_id}) - har viktig data")
            skipped_count += 1
            continue

        try:
            # Radera från alla relaterade tabeller först
            cursor.execute('DELETE FROM company_sectors WHERE company_id = ?', (company_id,))
            cursor.execute('DELETE FROM company_domains WHERE company_id = ?', (company_id,))
            cursor.execute('DELETE FROM company_dimensions WHERE company_id = ?', (company_id,))
            cursor.execute('DELETE FROM company_ai_capabilities WHERE company_id = ?', (company_id,))
            cursor.execute('DELETE FROM scb_matches WHERE company_id = ?', (company_id,))
            cursor.execute('DELETE FROM scb_enrichment WHERE company_id = ?', (company_id,))

            # Radera företaget
            cursor.execute('DELETE FROM companies WHERE id = ?', (company_id,))

            deleted_count += 1

        except Exception as e:
            print(f"   ✗ Fel vid radering av {deletion['name']} (ID: {company_id}): {e}")

    return deleted_count, skipped_count


def main():
    parser = argparse.ArgumentParser(
        description='Uppdatera websites och radera tomma företag från databasen'
    )
    parser.add_argument('--input', required=True, help='Input CSV med granskade websites')
    parser.add_argument('--db', default='databases/ai_companies.db', help='Sökväg till databas')
    parser.add_argument('--dry-run', action='store_true', help='Visa vad som skulle hända utan att ändra något')
    parser.add_argument('--force-delete', action='store_true', help='Radera även företag med data (FARLIGT!)')
    parser.add_argument('--yes', action='store_true', help='Hoppa över bekräftelse (automatiskt ja)')
    args = parser.parse_args()

    print("=" * 70)
    print("🔧 UPDATE WEBSITES & CLEANUP DATABASE")
    print("=" * 70)

    # Kolla att input-filen finns
    if not Path(args.input).exists():
        print(f"\n❌ Fel: Filen {args.input} finns inte!")
        sys.exit(1)

    # Analysera CSV
    print(f"\n📂 Analyserar: {args.input}")
    updates, deletions = analyze_csv(args.input)

    print(f"\n✓ Hittade {len(updates)} företag att uppdatera")
    print(f"✓ Hittade {len(deletions)} företag att radera")

    if not updates and not deletions:
        print("\n❌ Ingenting att göra!")
        sys.exit(0)

    # Anslut till databas
    print(f"\n📂 Ansluter till databas: {args.db}")
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    # Förhandsgranskning
    preview_changes(cursor, updates, deletions)

    if args.dry_run:
        print("\n" + "=" * 70)
        print("🔵 DRY RUN - Inga ändringar genomförda")
        print("=" * 70)
        conn.close()
        return

    # Bekräftelse
    print("\n" + "=" * 70)
    print("⚠️  VARNING: Du är på väg att ändra databasen!")
    print("=" * 70)

    if updates:
        print(f"✏️  Uppdatera {len(updates)} företag med nya websites")
    if deletions:
        print(f"🗑️  Radera {len(deletions)} företag från databasen")
        if args.force_delete:
            print("   ⚠️  FORCE DELETE aktiverat - raderar även företag med data!")

    if not args.yes:
        response = input("\nFortsätta? (skriv 'ja' för att bekräfta): ")
        if response.lower() != 'ja':
            print("\n❌ Avbrutet av användaren")
            conn.close()
            return
    else:
        print("\n✓ --yes flagga satt, fortsätter automatiskt...")

    # Genomför ändringar
    print("\n" + "=" * 70)
    print("🔄 GENOMFÖR ÄNDRINGAR")
    print("=" * 70)

    if updates:
        print(f"\n📝 Uppdaterar websites...")
        updated_count = update_websites(cursor, updates)
        print(f"   ✓ Uppdaterade {updated_count} företag")

    if deletions:
        print(f"\n🗑️  Raderar företag...")
        deleted_count, skipped_count = delete_companies(
            cursor,
            deletions,
            force=args.force_delete
        )
        print(f"   ✓ Raderade {deleted_count} företag")
        if skipped_count > 0:
            print(f"   ⚠ Skippade {skipped_count} företag (har viktig data)")

    # Committa
    conn.commit()
    print("\n✅ Ändringar sparade i databasen")

    # Statistik
    cursor.execute('SELECT COUNT(*) FROM companies')
    total_companies = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM companies WHERE website IS NOT NULL AND website != ""')
    with_website = cursor.fetchone()[0]

    print("\n" + "=" * 70)
    print("📊 DATABAS-STATISTIK")
    print("=" * 70)
    print(f"Total antal företag: {total_companies}")
    print(f"Företag med hemsida: {with_website} ({with_website/total_companies*100:.1f}%)")

    conn.close()

    print("\n" + "=" * 70)
    print("✓ KLART!")
    print("=" * 70)


if __name__ == '__main__':
    main()

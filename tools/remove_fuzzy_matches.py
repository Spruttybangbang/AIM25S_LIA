#!/usr/bin/env python3
"""
Ta bort fuzzy matches från databasen

Detta script kan användas för att:
1. Ta bort ALLA bulk-importerade fuzzy matches
2. Ta bort specifika company_ids från en CSV-fil
"""

import argparse
import pandas as pd
import sqlite3
from pathlib import Path


def remove_bulk_fuzzy_matches(db_path: Path, dry_run: bool = False):
    """
    Ta bort alla matchningar som importerades från bulk fuzzy matching
    (identifieras via imported_from_bulk flag i payload)
    """
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Hitta alla bulk-importerade fuzzy matches
    cur.execute("""
        SELECT id, company_id, score, city, payload
        FROM scb_matches
        WHERE payload LIKE '%"imported_from_bulk"%'
           OR payload LIKE '%"manually_approved"%'
    """)

    matches = cur.fetchall()

    print(f"🔍 Hittade {len(matches)} bulk-importerade fuzzy matches\n")

    if len(matches) == 0:
        print("✓ Inga bulk-importerade matchningar att ta bort")
        conn.close()
        return 0

    # Visa vad som kommer tas bort
    print("Följande matchningar kommer tas bort:")
    print("=" * 70)
    for match_id, company_id, score, city, payload in matches:
        print(f"  ID: {match_id} | Company ID: {company_id} | Score: {score} | City: {city}")

    print("=" * 70)

    if dry_run:
        print(f"\n🔍 DRY RUN - Skulle ta bort {len(matches)} matchningar")
    else:
        confirm = input(f"\n⚠️  Ta bort dessa {len(matches)} matchningar? (ja/nej): ")
        if confirm.lower() in ['ja', 'j', 'yes', 'y']:
            cur.execute("""
                DELETE FROM scb_matches
                WHERE payload LIKE '%"imported_from_bulk"%'
                   OR payload LIKE '%"manually_approved"%'
            """)
            conn.commit()
            print(f"✅ Tog bort {len(matches)} matchningar")
        else:
            print("❌ Avbrutet - inga matchningar togs bort")

    conn.close()
    return len(matches)


def remove_specific_matches(db_path: Path, csv_path: Path, dry_run: bool = False):
    """
    Ta bort matchningar för specifika company_ids från en CSV-fil
    CSV måste innehålla kolumnen 'company_id'
    """
    # Läs CSV
    df = pd.read_csv(csv_path)

    if 'company_id' not in df.columns:
        print("❌ CSV måste innehålla kolumnen 'company_id'")
        return 1

    company_ids = df['company_id'].tolist()

    print(f"🔍 Kommer ta bort matchningar för {len(company_ids)} företag från CSV\n")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Hitta matchningar för dessa company_ids
    placeholders = ','.join('?' * len(company_ids))
    cur.execute(f"""
        SELECT id, company_id, score, city
        FROM scb_matches
        WHERE company_id IN ({placeholders})
    """, company_ids)

    matches = cur.fetchall()

    if len(matches) == 0:
        print("✓ Inga matchningar hittades för dessa company_ids")
        conn.close()
        return 0

    print(f"Hittade {len(matches)} matchningar att ta bort:")
    print("=" * 70)
    for match_id, company_id, score, city in matches[:10]:  # Visa max 10
        print(f"  ID: {match_id} | Company ID: {company_id} | Score: {score} | City: {city}")

    if len(matches) > 10:
        print(f"  ... och {len(matches) - 10} till")

    print("=" * 70)

    if dry_run:
        print(f"\n🔍 DRY RUN - Skulle ta bort {len(matches)} matchningar")
    else:
        confirm = input(f"\n⚠️  Ta bort dessa {len(matches)} matchningar? (ja/nej): ")
        if confirm.lower() in ['ja', 'j', 'yes', 'y']:
            cur.execute(f"""
                DELETE FROM scb_matches
                WHERE company_id IN ({placeholders})
            """, company_ids)
            conn.commit()
            print(f"✅ Tog bort {len(matches)} matchningar")
        else:
            print("❌ Avbrutet - inga matchningar togs bort")

    conn.close()
    return len(matches)


def main():
    parser = argparse.ArgumentParser(
        description="Ta bort felaktiga bulk fuzzy matches från databasen"
    )
    parser.add_argument(
        "--db",
        required=True,
        help="Databas"
    )
    parser.add_argument(
        "--all-bulk",
        action="store_true",
        help="Ta bort ALLA bulk-importerade fuzzy matches"
    )
    parser.add_argument(
        "--csv",
        help="CSV med company_ids att ta bort matchningar för"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Testkörning - visa vad som skulle tas bort"
    )

    args = parser.parse_args()

    # Validera DB
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        print(f"✗ Databas hittades inte: {db_path}")
        return 1

    print(f"💾 Databas: {db_path}")
    print(f"🔍 Dry-run: {args.dry_run}")
    print()

    if args.all_bulk:
        # Ta bort alla bulk-importerade matches
        print("📋 Tar bort ALLA bulk-importerade fuzzy matches\n")
        remove_bulk_fuzzy_matches(db_path, dry_run=args.dry_run)
    elif args.csv:
        # Ta bort specifika matches från CSV
        csv_path = Path(args.csv).expanduser().resolve()
        if not csv_path.exists():
            print(f"✗ CSV hittades inte: {csv_path}")
            return 1

        print(f"📂 CSV: {csv_path}")
        print(f"📋 Tar bort matchningar för företag listade i CSV\n")
        remove_specific_matches(db_path, csv_path, dry_run=args.dry_run)
    else:
        print("❌ Du måste ange antingen --all-bulk eller --csv")
        print("\nExempel:")
        print("  # Ta bort alla bulk-importerade matchningar:")
        print("  python3 remove_fuzzy_matches.py --db ai_companies.db --all-bulk")
        print()
        print("  # Ta bort matchningar för specifika företag:")
        print("  python3 remove_fuzzy_matches.py --db ai_companies.db --csv felaktiga.csv")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

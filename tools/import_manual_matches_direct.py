#!/usr/bin/env python3
"""
Importerar manuella matchningar direkt från CSV till databasen
UTAN att göra nya SCB API-anrop (använder data från CSV)
"""

import argparse
import json
import pandas as pd
import sqlite3
from datetime import datetime
from pathlib import Path


def import_manual_matches(
    csv_path: Path,
    db_path: Path,
    dry_run: bool = False
) -> None:
    """
    Läser manuella matchningar från CSV och importerar till databasen
    """
    # Läs CSV
    df = pd.read_csv(csv_path)
    print(f"✓ Läste {len(df)} manuella matchningar från {csv_path.name}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    imported = 0
    skipped = 0

    for idx, row in df.iterrows():
        company_id = int(row['original_id'])
        original_name = row['original_name']
        correct_scb_name = row['correct_scb_name']
        city = row['city']
        org_nummer = str(row['org_nummer']) if pd.notna(row['org_nummer']) else None

        print(f"\n[{idx+1}/{len(df)}] {original_name}")
        print(f"  → {correct_scb_name}")
        print(f"  → {city}, Org.nr: {org_nummer}")

        # Kolla om matchning redan finns
        cur.execute("SELECT id FROM scb_matches WHERE company_id = ?", (company_id,))
        existing = cur.fetchone()

        if existing:
            print(f"  ⊘ Matchning finns redan, skippar")
            skipped += 1
            continue

        # Skapa SCB-payload som liknar API-svaret
        scb_payload = {
            "Företagsnamn": correct_scb_name.split('(')[0].strip(),  # Ta bort URL i parentes
            "PostOrt": city,
            "Organisationsnummer": org_nummer,
            "manual_match": True,  # Markera att detta är en manuell matchning
            "imported_from": csv_path.name,
            "imported_at": datetime.now().isoformat()
        }

        # Score sätts till 100 för manuella matchningar (perfekt match)
        score = 100

        if dry_run:
            print(f"  [DRY RUN] Skulle importera med score={score}")
        else:
            cur.execute(
                """INSERT INTO scb_matches
                   (company_id, matched, score, city, payload)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    company_id,
                    1,  # matched = True
                    score,
                    city,
                    json.dumps(scb_payload, ensure_ascii=False)
                )
            )
            print(f"  ✓ Importerad med score={score}")
            imported += 1

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'='*80}")
    print(f"RESULTAT:")
    print(f"  ✓ Importerade: {imported}")
    print(f"  ⊘ Skippade (finns redan): {skipped}")
    print(f"  Total: {len(df)}")
    print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(description="Importera manuella matchningar direkt från CSV")
    parser.add_argument("--csv", default="manual_matches_20251109_184431../results/.csv", help="CSV med manuella matchningar")
    parser.add_argument("--db", default="../ai_companies.db", help="Databas")
    parser.add_argument("--dry-run", action="store_true", help="Testkörning utan att skriva till DB")

    args = parser.parse_args()

    # Validera CSV
    csv_path = Path(args.csv).expanduser().resolve()
    if not csv_path.exists():
        print(f"✗ CSV hittades inte: {csv_path}")
        return 1

    # Validera DB
    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        print(f"✗ Databas hittades inte: {db_path}")
        return 1

    print(f"CSV: {csv_path}")
    print(f"DB: {db_path}")
    print(f"Dry-run: {args.dry_run}")
    print()

    # Importera
    import_manual_matches(csv_path, db_path, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

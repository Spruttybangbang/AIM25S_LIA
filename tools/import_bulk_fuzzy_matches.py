#!/usr/bin/env python3
"""
Importerar granskade fuzzy matches från bulk-matchning till databasen

CSV-formatet förväntas vara:
company_id,company_name,matched_name,score,match_type,orgnr,status,city,jurform,sni,payload

Du kan:
1. Öppna CSV:n i Excel/Numbers
2. Radera rader med felaktiga matchningar
3. Spara och importera endast de korrekta matchningarna
"""

import argparse
import json
import pandas as pd
import sqlite3
from datetime import datetime
from pathlib import Path


def import_bulk_fuzzy_matches(
    csv_path: Path,
    db_path: Path,
    dry_run: bool = False,
    min_score: int = 85
) -> None:
    """
    Läser granskade fuzzy matches från CSV och importerar till databasen
    """
    # Läs CSV
    df = pd.read_csv(csv_path)
    print(f"✓ Läste {len(df)} fuzzy matches från {csv_path.name}")

    # Filtrera på min_score om specificerat
    if min_score > 85:
        original_count = len(df)
        df = df[df['score'] >= min_score]
        print(f"  → Filtrerade till {len(df)} matches med score >= {min_score}")
        if len(df) < original_count:
            print(f"  → Skippar {original_count - len(df)} matches med lägre score")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    imported = 0
    skipped = 0
    errors = 0

    for idx, row in df.iterrows():
        company_id = int(row['company_id'])
        company_name = row['company_name']
        matched_name = row['matched_name']
        score = int(row['score'])
        city = row['city']
        orgnr = row['orgnr']

        print(f"\n[{idx+1}/{len(df)}] {company_name}")
        print(f"  → Matchad med: {matched_name}")
        print(f"  → Score: {score} | Org.nr: {orgnr} | Stad: {city}")

        # Kolla om matchning redan finns
        cur.execute("SELECT id FROM scb_matches WHERE company_id = ?", (company_id,))
        existing = cur.fetchone()

        if existing:
            print(f"  ⊘ Matchning finns redan, skippar")
            skipped += 1
            continue

        try:
            # Använd payload från CSV:n (innehåller full SCB-data)
            payload_str = row['payload']

            # Verifiera att payload är giltig JSON
            payload_data = json.loads(payload_str)

            # Lägg till metadata om importen
            payload_data['imported_from_bulk'] = True
            payload_data['bulk_csv_source'] = csv_path.name
            payload_data['manually_approved'] = True
            payload_data['approved_at'] = datetime.now().isoformat()

            if dry_run:
                print(f"  [DRY RUN] Skulle importera med score={score}")
            else:
                cur.execute(
                    """INSERT INTO scb_matches
                       (company_id, matched, score, city, payload, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        company_id,
                        1,  # matched = True
                        score,
                        city,
                        json.dumps(payload_data, ensure_ascii=False),
                        datetime.now().isoformat()
                    )
                )
                print(f"  ✓ Importerad med score={score}")
                imported += 1

        except json.JSONDecodeError as e:
            print(f"  ✗ FEL: Kunde inte läsa payload - {e}")
            errors += 1
        except Exception as e:
            print(f"  ✗ FEL: {e}")
            errors += 1

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'='*80}")
    print(f"RESULTAT:")
    print(f"  ✓ Importerade: {imported}")
    print(f"  ⊘ Skippade (finns redan): {skipped}")
    print(f"  ✗ Fel: {errors}")
    print(f"  Total: {len(df)}")
    print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(
        description="Importera granskade fuzzy matches från bulk-matchning"
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="CSV med granskade fuzzy matches"
    )
    parser.add_argument(
        "--db",
        default="ai_companies.db",
        help="Databas (default: ai_companies.db)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Testkörning utan att skriva till DB"
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=85,
        help="Minsta score för import (default: 85)"
    )

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

    print(f"📂 CSV: {csv_path}")
    print(f"💾 DB: {db_path}")
    print(f"🔍 Dry-run: {args.dry_run}")
    print(f"📊 Min score: {args.min_score}")
    print()

    # Importera
    import_bulk_fuzzy_matches(
        csv_path,
        db_path,
        dry_run=args.dry_run,
        min_score=args.min_score
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

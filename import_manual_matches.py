#!/usr/bin/env python3
"""
Importerar manuella matchningar från CSV till databasen
Söker i SCB med correct_scb_name för att hämta fullständig data
"""

import argparse
import json
import pandas as pd
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional

# Importera funktioner från retry_scb_search.py
sys.path.insert(0, str(Path(__file__).parent))
from retry_scb_search import (
    scb_search_api,
    validate_cert,
    validate_db_path,
    logger,
    find_best_match,
    save_scb_match
)


def import_manual_matches(
    csv_path: Path,
    db_path: Path,
    cert,
    dry_run: bool = False
) -> None:
    """
    Läser manuella matchningar från CSV och importerar till databasen
    """
    # Läs CSV
    df = pd.read_csv(csv_path)
    logger.info(f"Läste {len(df)} manuella matchningar från {csv_path}")

    imported = 0
    skipped = 0
    errors = 0

    for idx, row in df.iterrows():
        company_id = int(row['original_id'])
        original_name = row['original_name']
        correct_scb_name = row['correct_scb_name']

        logger.info(f"\n[{idx+1}/{len(df)}] {original_name} -> {correct_scb_name}")

        # Extrahera SCB-namnet (ta bort URL om det finns i parenteser)
        scb_name = correct_scb_name.split('(')[0].strip()

        # Sök i SCB med det korrekta namnet
        logger.info(f"  Söker i SCB med: '{scb_name}'")
        api_result = scb_search_api(scb_name, cert=cert)

        if not api_result.ok:
            logger.error(f"  ✗ API-fel: {api_result.status_code}")
            errors += 1
            continue

        if not api_result.data:
            logger.warning(f"  ⚠ Inga resultat hittades för '{scb_name}'")
            skipped += 1
            continue

        # Hitta bästa match
        match, score = find_best_match(scb_name, api_result.data)

        if match:
            matched_name = match.get("Företagsnamn", "")
            city = match.get("PostOrt", "")
            logger.info(f"  ✓ Matchning: score={score} -> '{matched_name}' ({city})")

            # Spara till databasen
            save_scb_match(db_path, company_id, True, score, match, dry_run=dry_run)
            imported += 1
        else:
            logger.warning(f"  ⚠ Ingen match hittades")
            skipped += 1

        # Rate limiting
        time.sleep(0.5)

    logger.info(f"\n{'='*80}")
    logger.info(f"RESULTAT:")
    logger.info(f"  Importerade: {imported}")
    logger.info(f"  Skippade: {skipped}")
    logger.info(f"  Fel: {errors}")
    logger.info(f"  Total: {len(df)}")
    logger.info(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(description="Importera manuella matchningar till databasen")
    parser.add_argument("--csv", default="manual_matches_20251109_184431.csv", help="CSV med manuella matchningar")
    parser.add_argument("--db", default="ai_companies.db", help="Databas")
    parser.add_argument("--cert", default="../SCB/certifikat/Certifikat_SokPaVar_A00592_2025-10-29_09-27-36Z.pem", help="Certifikat")
    parser.add_argument("--dry-run", action="store_true", help="Testkörning utan att skriva till DB")
    parser.add_argument("--verbose", action="store_true", help="Verbose loggning")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel("DEBUG")

    # Validera cert
    cert = None
    if args.cert:
        if "," in args.cert:
            cert = tuple(s.strip() for s in args.cert.split(",", 1))
        else:
            cert = args.cert
        cert = validate_cert(cert)

    # Validera DB
    db_path = validate_db_path(args.db)

    # Validera CSV
    csv_path = Path(args.csv).expanduser().resolve()
    if not csv_path.exists():
        logger.error(f"CSV hittades inte: {csv_path}")
        return 1

    logger.info(f"Dry-run: {args.dry_run}")

    # Importera
    import_manual_matches(csv_path, db_path, cert, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

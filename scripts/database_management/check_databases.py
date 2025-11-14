#!/usr/bin/env python3
"""
Kontrollera antal företag i databaser

Unified script som kan visa:
- Endast ai_companies.db
- Endast ai_others.db
- Båda databaser (default)
"""

import argparse
import sqlite3
import os
from pathlib import Path


def check_database(db_path: Path, name: str) -> int:
    """Räkna företag i en databas"""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM companies")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"✗ Fel vid läsning av {name}: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Kontrollera antal företag i databaser")
    parser.add_argument("--companies", action="store_true", help="Visa endast ai_companies.db")
    parser.add_argument("--others", action="store_true", help="Visa endast ai_others.db")

    args = parser.parse_args()

    # Hitta project root (2 nivåer upp från detta script)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    # Databas-sökvägar
    companies_db = project_root / "databases" / "ai_companies.db"
    others_db = project_root / "databases" / "ai_others.db"

    # Om inga flags angivna, visa båda (default)
    show_both = not (args.companies or args.others)

    counts = {}

    if args.companies or show_both:
        if companies_db.exists():
            count = check_database(companies_db, "ai_companies.db")
            counts['companies'] = count
            print(f"ai_companies.db: {count} företag")
        else:
            print(f"✗ ai_companies.db hittades inte: {companies_db}")

    if args.others or show_both:
        if others_db.exists():
            count = check_database(others_db, "ai_others.db")
            counts['others'] = count
            print(f"ai_others.db: {count} företag")
        else:
            print(f"✗ ai_others.db hittades inte: {others_db}")

    # Visa total om båda visas
    if show_both and len(counts) == 2:
        total = counts.get('companies', 0) + counts.get('others', 0)
        print(f"\nTotalt: {total} företag")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

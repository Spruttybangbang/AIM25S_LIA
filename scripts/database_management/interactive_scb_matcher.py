#!/usr/bin/env python3
"""
Interaktiv SCB-matchning
========================

Läser CSV med company_ids och låter användaren interaktivt matcha företag mot SCB.

Usage:
    python3 interactive_scb_matcher.py input.csv

CSV-format (input.csv):
    company_id
    123
    456
    789
"""

import configparser
import csv
import json
import requests
import sqlite3
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    from fuzzywuzzy import fuzz
except ImportError as e:
    raise SystemExit("Saknar 'fuzzywuzzy'. Installera: pip install fuzzywuzzy python-Levenshtein") from e

# =============================================================================
# KONFIGURATION
# =============================================================================

API_URL = 'https://privateapi.scb.se/nv0101/v1/sokpavar/api/je/HamtaForetag'

def load_config():
    """Load configuration from config.ini or use defaults"""
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent.parent / "config.ini"

    # Defaults (relativa paths från scripts/database_management/)
    default_db = "../../databases/ai_companies.db"
    default_cert = "../../SCB/certifikat/Certifikat_SokPaVar_A00592_2025-10-29_09-27-36Z.pem"

    if config_path.exists():
        config.read(config_path)
        db_path = config.get('SCB', 'database_path', fallback=default_db)
        cert_path = config.get('SCB', 'cert_path', fallback=default_cert)
    else:
        db_path = default_db
        cert_path = default_cert

    # Konvertera till absoluta paths
    script_dir = Path(__file__).parent
    db_path = (script_dir / db_path).resolve()
    cert_path = (script_dir / cert_path).resolve()

    return str(db_path), str(cert_path)

def validate_paths(db_path: str, cert_path: str):
    """Validera att databas och certifikat finns"""
    db = Path(db_path)
    cert = Path(cert_path)

    if not db.exists():
        raise FileNotFoundError(f"Databas hittades inte: {db}")

    if not cert.exists():
        raise FileNotFoundError(f"Certifikat hittades inte: {cert}")

# Ladda konfiguration
DB_PATH, CERT_PATH = load_config()

# =============================================================================
# SCB API
# =============================================================================

def search_scb(search_term: str) -> List[Dict]:
    """Sök företag i SCB"""
    payload = {
        "Företagsstatus": "1",
        "Registreringsstatus": "1",
        "variabler": [
            {
                "Varde1": search_term,
                "Varde2": "",
                "Operator": "Innehaller",
                "Variabel": "Namn"
            }
        ]
    }

    try:
        response = requests.post(API_URL, json=payload, cert=CERT_PATH, timeout=30)
        response.raise_for_status()
        results = response.json()
        return results
    except Exception as e:
        print(f"  ❌ API-fel: {e}")
        return []

def normalize_name(name: str) -> str:
    """Normalisera företagsnamn för fuzzy matching"""
    if not name:
        return ""

    name = name.lower().strip()

    # Ta bort domännamn
    for domain in ['.com', '.se', '.ai', '.io', '.org', '.net']:
        name = name.replace(domain, '')

    # Ta bort suffix
    suffixes = [
        ' ab', ' aktiebolag', ' ltd', ' limited', ' inc', ' incorporated',
        ' i stockholm', ' i göteborg', ' i malmö',
        ' sweden', ' sverige'
    ]

    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    return name.strip()

def rank_candidates(our_name: str, scb_results: List[Dict]) -> List[Tuple[Dict, int]]:
    """
    Rankar SCB-kandidater baserat på fuzzy score

    Returns:
        Lista av (scb_company, fuzzy_score) sorterad fallande efter score
    """
    if not scb_results:
        return []

    our_normalized = normalize_name(our_name)

    ranked = []
    for company in scb_results:
        scb_name = company.get('Företagsnamn', '')
        scb_normalized = normalize_name(scb_name)
        score = fuzz.ratio(our_normalized, scb_normalized)
        ranked.append((company, score))

    # Sortera efter score (högst först)
    ranked.sort(key=lambda x: x[1], reverse=True)

    return ranked

# =============================================================================
# DATABAS
# =============================================================================

def get_company_by_id(company_id: int) -> Optional[Dict]:
    """Hämta företag från databas"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, website, type, location_city, owner
        FROM companies
        WHERE id = ?
    """, [company_id])

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'id': row[0],
        'name': row[1],
        'website': row[2],
        'type': row[3],
        'location_city': row[4],
        'owner': row[5]
    }

# =============================================================================
# CSV
# =============================================================================

def read_company_ids(csv_path: str) -> List[int]:
    """Läs company_ids från CSV"""
    ids = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                company_id = int(row['company_id'])
                ids.append(company_id)
            except (ValueError, KeyError) as e:
                print(f"⚠️  Hoppar över ogiltig rad: {row}")
    return ids

def flatten_scb_result(scb_company: Dict) -> Dict:
    """
    Platta ut SCB-resultat till separata kolumner istället för JSON-klump
    """
    return {
        'scb_företagsnamn': scb_company.get('Företagsnamn', ''),
        'scb_orgnr': scb_company.get('OrgNr', ''),
        'scb_postort': scb_company.get('PostOrt', ''),
        'scb_kommun': scb_company.get('Kommun', ''),
        'scb_län': scb_company.get('Län', ''),
        'scb_adress': scb_company.get('Adress', ''),
        'scb_postnr': scb_company.get('PostNr', ''),
        'scb_telefon': scb_company.get('Telefon', ''),
        'scb_sni_kod': scb_company.get('SNI2007Kod', ''),
        'scb_sni_text': scb_company.get('SNI2007Text', ''),
        'scb_juridisk_form': scb_company.get('JuridiskFormKod', ''),
        'scb_antal_anställda': scb_company.get('AntalAnstallda', ''),
        'scb_omsättning': scb_company.get('Omsattning', ''),
    }

def save_matches_to_csv(matches: List[Dict], output_path: str):
    """Spara bekräftade matcher till CSV"""
    if not matches:
        print("⚠️  Inga matcher att spara")
        return

    # Kombinera alla möjliga kolumner från både company och SCB
    fieldnames = [
        'company_id',
        'company_name',
        'company_type',
        'company_website',
        'company_location_city',
        'company_owner',
        'fuzzy_score',
        'scb_företagsnamn',
        'scb_orgnr',
        'scb_postort',
        'scb_kommun',
        'scb_län',
        'scb_adress',
        'scb_postnr',
        'scb_telefon',
        'scb_sni_kod',
        'scb_sni_text',
        'scb_juridisk_form',
        'scb_antal_anställda',
        'scb_omsättning',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)

    print(f"\n✅ Sparade {len(matches)} matcher till: {output_path}")

# =============================================================================
# INTERAKTIV MATCHNING
# =============================================================================

def display_candidates(candidates: List[Tuple[Dict, int]], our_name: str):
    """Visa kandidater för användaren"""
    print(f"\n{'='*70}")
    print(f"Sökresultat för: {our_name}")
    print('='*70)

    if not candidates:
        print("❌ Inga resultat hittades")
        return

    # Visa top 10
    for i, (company, score) in enumerate(candidates[:10], 1):
        name = company.get('Företagsnamn', '')
        city = company.get('PostOrt', '')
        orgnr = company.get('OrgNr', '')

        print(f"\n[{i}] {name}")
        print(f"    Ort: {city}")
        print(f"    Org.nr: {orgnr}")
        print(f"    Score: {score}/100")

    if len(candidates) > 10:
        print(f"\n... och {len(candidates) - 10} fler träffar")

def get_user_choice(num_candidates: int) -> Tuple[str, Optional[int]]:
    """
    Få användarens val

    Returns:
        (action, choice_number)
        action: 'select', 'skip', 'new_search', 'quit'
        choice_number: 1-N om action='select', annars None
    """
    print(f"\n{'='*70}")
    print("Välj alternativ:")
    print(f"  [1-{min(num_candidates, 10)}] - Välj en kandidat")
    print("  [s] - Skip (ingen stämmer, gå vidare)")
    print("  [n] - Ny sökning (ange egen sökterm)")
    print("  [q] - Quit (spara och avbryt)")
    print('='*70)

    while True:
        choice = input("\nDitt val: ").strip().lower()

        if choice == 's':
            return ('skip', None)
        elif choice == 'n':
            return ('new_search', None)
        elif choice == 'q':
            return ('quit', None)
        elif choice.isdigit():
            num = int(choice)
            if 1 <= num <= min(num_candidates, 10):
                return ('select', num)
            else:
                print(f"❌ Ogiltigt val. Välj 1-{min(num_candidates, 10)}")
        else:
            print("❌ Ogiltigt val. Försök igen.")

def process_company(company: Dict, confirmed_matches: List[Dict]) -> bool:
    """
    Processa ett företag interaktivt

    Returns:
        True om vi ska fortsätta, False om användaren vill avbryta
    """
    print(f"\n\n{'#'*70}")
    print(f"# FÖRETAG {company['id']}: {company['name']}")
    print(f"# Type: {company['type']} | Website: {company.get('website', 'N/A')}")
    print('#'*70)

    current_search_term = company['name']

    while True:
        # Sök i SCB
        print(f"\n🔍 Söker i SCB efter: '{current_search_term}'...")
        scb_results = search_scb(current_search_term)

        if not scb_results:
            print("\n❌ Inga resultat från SCB")
            print("\nVad vill du göra?")
            print("  [s] - Skip (gå vidare till nästa företag)")
            print("  [n] - Ny sökning (försök med annan term)")
            print("  [q] - Quit (spara och avbryt)")

            choice = input("\nDitt val: ").strip().lower()

            if choice == 's':
                return True
            elif choice == 'n':
                new_term = input("\nAnge ny sökterm: ").strip()
                if new_term:
                    current_search_term = new_term
                    continue
                else:
                    print("❌ Tom sökterm, använder original")
                    current_search_term = company['name']
                    continue
            elif choice == 'q':
                return False
            else:
                continue

        # Ranka kandidater
        candidates = rank_candidates(current_search_term, scb_results)

        # Visa kandidater
        display_candidates(candidates, current_search_term)

        # Få användarens val
        action, choice_num = get_user_choice(len(candidates))

        if action == 'select':
            # Användaren valde en kandidat
            selected = candidates[choice_num - 1]
            scb_company, score = selected

            # Bekräfta valet
            print(f"\n✅ Du valde: {scb_company.get('Företagsnamn')}")
            confirm = input("Bekräfta? (y/n): ").strip().lower()

            if confirm == 'y':
                # Platta ut SCB-data
                scb_flat = flatten_scb_result(scb_company)

                # Skapa matchad rad
                match = {
                    'company_id': company['id'],
                    'company_name': company['name'],
                    'company_type': company['type'],
                    'company_website': company.get('website', ''),
                    'company_location_city': company.get('location_city', ''),
                    'company_owner': company.get('owner', ''),
                    'fuzzy_score': score,
                    **scb_flat
                }

                confirmed_matches.append(match)
                print(f"\n✅ Match sparad! (Totalt: {len(confirmed_matches)} bekräftade)")
                return True  # Gå vidare till nästa företag
            else:
                print("❌ Val ej bekräftat, försök igen")
                continue

        elif action == 'skip':
            print("⏭️  Hoppar över detta företag")
            return True

        elif action == 'new_search':
            new_term = input("\nAnge ny sökterm: ").strip()
            if new_term:
                current_search_term = new_term
            else:
                print("❌ Tom sökterm, använder original")
                current_search_term = company['name']
            continue

        elif action == 'quit':
            print("\n🛑 Användaren valde att avbryta")
            return False

# =============================================================================
# MAIN
# =============================================================================

def main():
    # Validera paths
    try:
        validate_paths(DB_PATH, CERT_PATH)
    except FileNotFoundError as e:
        print(f"❌ Fel: {e}")
        print(f"\nFörväntade paths:")
        print(f"  Databas: {DB_PATH}")
        print(f"  Certifikat: {CERT_PATH}")
        sys.exit(1)

    # Kolla argument
    if len(sys.argv) < 2:
        print("""
Användning:
    python3 interactive_scb_matcher.py input.csv

CSV-format (input.csv):
    company_id
    123
    456
    789

Output:
    Sparar bekräftade matcher till: scb_matches_confirmed_TIMESTAMP.csv
""")
        sys.exit(0)

    csv_path = sys.argv[1]

    # Läs company IDs
    if not Path(csv_path).exists():
        print(f"❌ Filen hittades inte: {csv_path}")
        sys.exit(1)

    print(f"📖 Läser företags-ID:n från: {csv_path}")
    company_ids = read_company_ids(csv_path)

    if not company_ids:
        print("❌ Inga giltiga company_id hittades i CSV:n")
        sys.exit(1)

    print(f"✅ Hittade {len(company_ids)} företag att processa")

    # Bekräfta start
    response = input(f"\nVill du börja matcha {len(company_ids)} företag? (y/n): ").strip().lower()
    if response != 'y':
        print("Avbryter...")
        sys.exit(0)

    # Lista för bekräftade matcher
    confirmed_matches = []

    # Processa varje företag
    for i, company_id in enumerate(company_ids, 1):
        print(f"\n\n{'='*70}")
        print(f"Progress: {i}/{len(company_ids)}")
        print('='*70)

        # Hämta företag från DB
        company = get_company_by_id(company_id)

        if not company:
            print(f"⚠️  Företag med ID {company_id} hittades inte i databasen")
            continue

        # Processa företaget
        should_continue = process_company(company, confirmed_matches)

        if not should_continue:
            # Användaren valde quit
            break

        # Rate limiting mellan företag
        if i < len(company_ids):
            time.sleep(0.5)

    # Spara resultat
    if confirmed_matches:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"scb_matches_confirmed_{timestamp}.csv"
        save_matches_to_csv(confirmed_matches, output_path)

        print(f"\n{'='*70}")
        print("SAMMANFATTNING")
        print('='*70)
        print(f"Totalt företag: {len(company_ids)}")
        print(f"Bekräftade matcher: {len(confirmed_matches)}")
        print(f"Output: {output_path}")
    else:
        print("\n⚠️  Inga matcher bekräftades")

    print("\n✅ Klart!")

if __name__ == "__main__":
    main()

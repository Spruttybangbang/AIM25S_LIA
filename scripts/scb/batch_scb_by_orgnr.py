#!/usr/bin/env python3
"""
Batch SCB Matcher - Automatisk version av interactive_scb_matcher
=================================================================

Läser CSV med företagsnamn och hämtar automatiskt SCB-data för varje företag.
Tar första (bästa) matchningen baserat på fuzzy score.

Usage:
    python3 batch_scb_by_orgnr.py input.csv

Input CSV-format:
    company_name
    Spotify AB
    Lexplore AB
    ...

Output:
    - scb_success_TIMESTAMP.csv: Alla lyckade matcher med SCB-data
    - scb_failed_TIMESTAMP.csv: Alla misslyckade matcher med felmeddelanden
"""

import configparser
import csv
import json
import requests
import sys
import time
from datetime import datetime
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
RATE_LIMIT_DELAY = 0.5  # Sekunder mellan anrop
FUZZY_THRESHOLD = 85  # Minsta fuzzy score för automatisk matchning

def load_config():
    """Load configuration from config.ini or use defaults"""
    config = configparser.ConfigParser()

    # Leta efter config.ini i olika platser
    possible_paths = [
        Path(__file__).parent.parent / "config.ini",
        Path(__file__).parent / "config.ini",
    ]

    # Default cert path
    default_cert = "../../../SCB/certifikat/Certifikat_SokPaVar_A00592_2025-10-29_09-27-36Z.pem"
    cert_path = default_cert

    for config_path in possible_paths:
        if config_path.exists():
            config.read(config_path)
            cert_path = config.get('SCB', 'cert_path', fallback=default_cert)
            break

    # Konvertera till absolut path
    script_dir = Path(__file__).parent
    cert_path = (script_dir / cert_path).resolve()

    return str(cert_path)

def validate_cert_path(cert_path: str):
    """Validera att certifikat finns"""
    cert = Path(cert_path)
    if not cert.exists():
        raise FileNotFoundError(f"Certifikat hittades inte: {cert}")

# Ladda konfiguration
CERT_PATH = load_config()

# =============================================================================
# SCB API (kopierat från interactive_scb_matcher.py)
# =============================================================================

def search_scb(search_term: str) -> List[Dict]:
    """
    Sök företag i SCB
    Exakt samma som i interactive_scb_matcher.py
    """
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

        if not isinstance(results, list):
            print(f"  ⚠️  SCB returnerade oväntat format: {type(results)}")
            return []

        return results
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Nätverksfel: {e}")
        return []
    except ValueError as e:
        print(f"  ❌ JSON-parsningsfel: {e}")
        return []
    except Exception as e:
        print(f"  ❌ Oväntat fel: {e}")
        return []

def normalize_name(name: str) -> str:
    """
    Normalisera företagsnamn för fuzzy matching
    Exakt samma som i interactive_scb_matcher.py
    """
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
    Exakt samma som i interactive_scb_matcher.py
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

def flatten_scb_result(scb_company: Dict) -> Dict:
    """
    Platta ut SCB-resultat till separata kolumner
    Exakt samma som i interactive_scb_matcher.py
    """
    return {
        'organization_number': scb_company.get('OrgNr', ''),
        'scb_company_name': scb_company.get('Företagsnamn', ''),
        'co_address': scb_company.get('COAdress', ''),
        'post_address': scb_company.get('PostAdress', ''),
        'post_code': scb_company.get('PostNr', ''),
        'post_city': scb_company.get('PostOrt', ''),
        'municipality_code': scb_company.get('Säteskommun, kod', ''),
        'municipality': scb_company.get('Säteskommun', ''),
        'county_code': scb_company.get('Säteslän, kod', ''),
        'county': scb_company.get('Säteslän', ''),
        'num_workplaces': scb_company.get('Antal arbetsställen', ''),
        'employee_size_code': scb_company.get('Stkl, kod', ''),
        'employee_size': scb_company.get('Storleksklass', ''),
        'company_status_code': scb_company.get('Företagsstatus, kod', ''),
        'company_status': scb_company.get('Företagsstatus', ''),
        'legal_form_code': scb_company.get('Juridisk form, kod', ''),
        'legal_form': scb_company.get('Juridisk form', ''),
        'start_date': scb_company.get('Startdatum', ''),
        'registration_date': scb_company.get('Registreringsdatum', ''),
        'industry_1_code': scb_company.get('Bransch_1, kod', ''),
        'industry_1': scb_company.get('Bransch_1', ''),
        'industry_2_code': scb_company.get('Bransch_2, kod', ''),
        'industry_2': scb_company.get('Bransch_2', ''),
        'revenue_year': scb_company.get('Omsättning, år', ''),
        'revenue_size_code': scb_company.get('Stkl, oms, kod', ''),
        'revenue_size': scb_company.get('Storleksklass, oms', ''),
        'phone': scb_company.get('Telefon', ''),
        'email': scb_company.get('E-post', ''),
        'employer_status_code': scb_company.get('Arbetsgivarstatus, kod', ''),
        'employer_status': scb_company.get('Arbetsgivarstatus', ''),
        'vat_status_code': scb_company.get('Momsstatus, kod', ''),
        'vat_status': scb_company.get('Momsstatus', ''),
        'export_import': scb_company.get('Export/Importmarkering', ''),
    }

# =============================================================================
# CSV
# =============================================================================

def read_company_names(csv_path: str) -> List[str]:
    """Läs företagsnamn från CSV"""
    names = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                name = row['company_name'].strip()
                if name:
                    names.append(name)
            except KeyError:
                print(f"⚠️  CSV måste ha kolumnen 'company_name'. Hittade: {list(row.keys())}")
                sys.exit(1)
    return names

def save_success_to_csv(success_data: List[Dict], output_path: str):
    """Spara lyckade matcher till CSV (samma format som interactive_scb_matcher)"""
    if not success_data:
        print("⚠️  Inga lyckade matcher att spara")
        return

    # Samma kolumner som interactive_scb_matcher
    fieldnames = [
        'company_name',
        'fuzzy_score',
        'organization_number',
        'scb_company_name',
        'co_address',
        'post_address',
        'post_code',
        'post_city',
        'municipality_code',
        'municipality',
        'county_code',
        'county',
        'num_workplaces',
        'employee_size_code',
        'employee_size',
        'company_status_code',
        'company_status',
        'legal_form_code',
        'legal_form',
        'start_date',
        'registration_date',
        'industry_1_code',
        'industry_1',
        'industry_2_code',
        'industry_2',
        'revenue_year',
        'revenue_size_code',
        'revenue_size',
        'phone',
        'email',
        'employer_status_code',
        'employer_status',
        'vat_status_code',
        'vat_status',
        'export_import',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(success_data)

    print(f"\n✅ Sparade {len(success_data)} lyckade matcher till: {output_path}")

def save_failed_to_csv(failed_data: List[Dict], output_path: str):
    """Spara misslyckade matcher till CSV"""
    if not failed_data:
        print("✅ Inga misslyckade matcher!")
        return

    fieldnames = ['company_name', 'reason', 'timestamp']

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failed_data)

    print(f"⚠️  Sparade {len(failed_data)} misslyckade matcher till: {output_path}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    # Validera certifikat
    try:
        validate_cert_path(CERT_PATH)
    except FileNotFoundError as e:
        print(f"❌ Fel: {e}")
        print(f"\nFörväntad certifikat-path: {CERT_PATH}")
        sys.exit(1)

    # Kolla argument
    if len(sys.argv) < 2:
        print("""
Användning:
    python3 batch_scb_by_orgnr.py input.csv

Input CSV-format:
    company_name
    Spotify AB
    Lexplore AB
    Mavenoid AB

Output:
    - scb_success_TIMESTAMP.csv: Lyckade matcher med all SCB-data
    - scb_failed_TIMESTAMP.csv: Misslyckade matcher med felmeddelanden

Observera: Tar automatiskt första (bästa) matchningen med fuzzy score >= 85
""")
        sys.exit(0)

    csv_path = sys.argv[1]

    # Läs företagsnamn
    if not Path(csv_path).exists():
        print(f"❌ Filen hittades inte: {csv_path}")
        sys.exit(1)

    print(f"📖 Läser företagsnamn från: {csv_path}")
    company_names = read_company_names(csv_path)

    if not company_names:
        print("❌ Inga giltiga företagsnamn hittades i CSV:n")
        sys.exit(1)

    print(f"✅ Hittade {len(company_names)} företag att processa")

    # Skapa output-filer
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    success_path = f"scb_success_{timestamp}.csv"
    failed_path = f"scb_failed_{timestamp}.csv"

    print(f"\n💾 Lyckade matcher sparas till: {success_path}")
    print(f"💾 Misslyckade matcher sparas till: {failed_path}")
    print(f"🎯 Fuzzy threshold: {FUZZY_THRESHOLD}% (tar automatiskt bästa matchningen)")

    # Bekräfta start
    response = input(f"\nVill du börja hämta data för {len(company_names)} företag? (y/n): ").strip().lower()
    if response != 'y':
        print("Avbryter...")
        sys.exit(0)

    # Listor för resultat
    success_data = []
    failed_data = []

    # Processa varje företag
    print(f"\n{'='*70}")
    print("STARTAR BATCH-KÖRNING")
    print('='*70)

    start_time = time.time()

    for i, company_name in enumerate(company_names, 1):
        print(f"\n[{i}/{len(company_names)}] {company_name}")

        # Sök i SCB
        scb_results = search_scb(company_name)

        if not scb_results:
            failed_data.append({
                'company_name': company_name,
                'reason': 'Inga resultat från SCB',
                'timestamp': datetime.now().isoformat()
            })
            print(f"  ❌ Inga resultat från SCB")
            if i < len(company_names):
                time.sleep(RATE_LIMIT_DELAY)
            continue

        # Ranka kandidater
        candidates = rank_candidates(company_name, scb_results)

        if not candidates:
            failed_data.append({
                'company_name': company_name,
                'reason': 'Kunde inte ranka resultat',
                'timestamp': datetime.now().isoformat()
            })
            print(f"  ❌ Kunde inte ranka resultat")
            if i < len(company_names):
                time.sleep(RATE_LIMIT_DELAY)
            continue

        # Ta första (bästa) matchningen
        best_match, score = candidates[0]

        # Kontrollera om score är över threshold
        if score < FUZZY_THRESHOLD:
            failed_data.append({
                'company_name': company_name,
                'reason': f'Låg fuzzy score: {score} < {FUZZY_THRESHOLD}. Bästa kandidat: {best_match.get("Företagsnamn", "N/A")}',
                'timestamp': datetime.now().isoformat()
            })
            print(f"  ⚠️  Låg score: {score} < {FUZZY_THRESHOLD}")
            print(f"      Bästa kandidat: {best_match.get('Företagsnamn', 'N/A')}")
            if i < len(company_names):
                time.sleep(RATE_LIMIT_DELAY)
            continue

        # Platta ut SCB-data
        scb_flat = flatten_scb_result(best_match)

        # Skapa matchad rad
        match = {
            'company_name': company_name,
            'fuzzy_score': score,
            **scb_flat
        }

        success_data.append(match)

        scb_name = best_match.get('Företagsnamn', 'N/A')
        city = best_match.get('PostOrt', 'N/A')
        print(f"  ✅ {scb_name} - {city} (score: {score})")

        # Rate limiting
        if i < len(company_names):
            time.sleep(RATE_LIMIT_DELAY)

    end_time = time.time()
    duration = end_time - start_time

    # Spara resultat
    print(f"\n{'='*70}")
    print("SPARAR RESULTAT")
    print('='*70)

    save_success_to_csv(success_data, success_path)
    save_failed_to_csv(failed_data, failed_path)

    # Statistik
    print(f"\n{'='*70}")
    print("SAMMANFATTNING")
    print('='*70)
    print(f"Totalt företag: {len(company_names)}")
    print(f"Lyckade matcher: {len(success_data)} ({len(success_data)/len(company_names)*100:.1f}%)")
    print(f"Misslyckade matcher: {len(failed_data)} ({len(failed_data)/len(company_names)*100:.1f}%)")
    print(f"Körtid: {duration:.1f} sekunder ({duration/60:.1f} minuter)")
    print(f"Genomsnittlig tid per request: {duration/len(company_names):.2f} sekunder")
    print(f"\n✅ Klart!")

if __name__ == "__main__":
    main()

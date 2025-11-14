#!/usr/bin/env python3
"""
Batch SCB API Query by Organization Number
==========================================

Läser CSV med organisationsnummer och företagsnamn, hämtar alla tillgängliga
variabler från SCB. Söker på företagsnamn och validerar organisationsnummer.

Usage:
    python3 batch_scb_by_orgnr.py input.csv

Input CSV-format:
    organization_number,company_name
    5567037485,Spotify AB
    5590691811,Lexplore AB
    ...

Output:
    - scb_success_TIMESTAMP.csv: Alla lyckade requests med SCB-data
    - scb_failed_TIMESTAMP.csv: Alla misslyckade requests med felmeddelanden
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

# =============================================================================
# KONFIGURATION
# =============================================================================

API_URL = 'https://privateapi.scb.se/nv0101/v1/sokpavar/api/je/HamtaForetag'
RATE_LIMIT_DELAY = 0.5  # Sekunder mellan anrop (SCB rekommenderar max 2 req/s)

def load_config():
    """Load configuration from config.ini or use defaults"""
    config = configparser.ConfigParser()

    # Leta efter config.ini i olika platser
    possible_paths = [
        Path(__file__).parent.parent / "config.ini",  # scripts/config.ini
        Path(__file__).parent / "config.ini",  # scripts/scb/config.ini
    ]

    # Defaults (relativa paths från scripts/scb/)
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
# SCB API
# =============================================================================

def search_scb_by_orgnr(org_nr: str, company_name: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Sök företag i SCB med företagsnamn och validera organisationsnummer

    SCB API stödjer inte direktsökning på org.nr, så vi söker på företagsnamn
    och validerar sedan att rätt org.nr hittades i resultatet.

    Returns:
        (success: bool, scb_data: Dict or None, error_message: str or None)
    """
    # Normalisera organisationsnummer (ta bort bindestreck)
    org_nr_clean = org_nr.replace('-', '').strip()

    # Sök på företagsnamn (det enda som fungerar i SCB API)
    payload = {
        "Företagsstatus": "1",  # Verksamma företag
        "Registreringsstatus": "1",  # Registrerade
        "variabler": [
            {
                "Varde1": company_name,
                "Varde2": "",
                "Operator": "Innehaller",  # Partiell matchning
                "Variabel": "Namn"
            }
        ]
    }

    try:
        response = requests.post(API_URL, json=payload, cert=CERT_PATH, timeout=30)
        response.raise_for_status()
        results = response.json()

        # Validera att results är en lista
        if not isinstance(results, list):
            return False, None, f"Oväntat format från SCB: {type(results)}"

        # Om inga resultat
        if len(results) == 0:
            return False, None, f"Inget företag hittades för '{company_name}'"

        # Sök efter rätt org.nr i resultaten
        for result in results:
            result_orgnr = result.get('OrgNr', '').replace('-', '').strip()
            if result_orgnr == org_nr_clean:
                # Hittade rätt företag!
                return True, result, None

        # Om vi kommer hit fanns inga matchande org.nr
        result_orgnrs = [r.get('OrgNr', 'N/A') for r in results[:5]]
        return False, None, f"Hittade {len(results)} företag med namnet '{company_name}' men inget med org.nr {org_nr}. Hittade org.nr: {', '.join(result_orgnrs)}"

    except requests.exceptions.HTTPError as e:
        return False, None, f"HTTP-fel: {e.response.status_code} - {e.response.text[:200]}"
    except requests.exceptions.RequestException as e:
        return False, None, f"Nätverksfel: {str(e)[:200]}"
    except ValueError as e:
        return False, None, f"JSON-parsningsfel: {str(e)[:200]}"
    except Exception as e:
        return False, None, f"Oväntat fel: {str(e)[:200]}"

def flatten_scb_result(scb_company: Dict) -> Dict:
    """
    Platta ut SCB-resultat till separata kolumner
    Samma format som scb_matches_confirmed CSV
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

def read_company_data(csv_path: str) -> List[Tuple[str, str]]:
    """Läs organisationsnummer och företagsnamn från CSV"""
    companies = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                org_nr = row['organization_number'].strip()
                company_name = row['company_name'].strip()
                if org_nr and company_name:
                    companies.append((org_nr, company_name))
                else:
                    print(f"⚠️  Hoppar över rad med tom data: {row}")
            except KeyError as e:
                print(f"⚠️  CSV måste ha kolumnerna 'organization_number' och 'company_name'. Hittade: {list(row.keys())}")
                sys.exit(1)
    return companies

def save_success_to_csv(success_data: List[Dict], output_path: str):
    """Spara lyckade requests till CSV"""
    if not success_data:
        print("⚠️  Inga lyckade requests att spara")
        return

    # Alla SCB-kolumner (samma som scb_enrichment-tabellen)
    fieldnames = [
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

    print(f"\n✅ Sparade {len(success_data)} lyckade requests till: {output_path}")

def save_failed_to_csv(failed_data: List[Dict], output_path: str):
    """Spara misslyckade requests till CSV"""
    if not failed_data:
        print("✅ Inga misslyckade requests!")
        return

    fieldnames = ['organization_number', 'error_message', 'timestamp']

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failed_data)

    print(f"⚠️  Sparade {len(failed_data)} misslyckade requests till: {output_path}")

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
    organization_number,company_name
    5567037485,Spotify AB
    5590691811,Lexplore AB
    5592675952,LINKAI Technologies AB

Output:
    - scb_success_TIMESTAMP.csv: Lyckade requests med all SCB-data
    - scb_failed_TIMESTAMP.csv: Misslyckade requests med felmeddelanden
""")
        sys.exit(0)

    csv_path = sys.argv[1]

    # Läs företagsdata
    if not Path(csv_path).exists():
        print(f"❌ Filen hittades inte: {csv_path}")
        sys.exit(1)

    print(f"📖 Läser företagsdata från: {csv_path}")
    companies = read_company_data(csv_path)

    if not companies:
        print("❌ Inga giltiga företag hittades i CSV:n")
        sys.exit(1)

    print(f"✅ Hittade {len(companies)} företag att processa")

    # Skapa output-filer
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    success_path = f"scb_success_{timestamp}.csv"
    failed_path = f"scb_failed_{timestamp}.csv"

    print(f"\n💾 Lyckade requests sparas till: {success_path}")
    print(f"💾 Misslyckade requests sparas till: {failed_path}")

    # Bekräfta start
    response = input(f"\nVill du börja hämta data för {len(companies)} företag? (y/n): ").strip().lower()
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

    for i, (org_nr, company_name) in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}] {company_name} ({org_nr})")

        # Sök i SCB
        success, scb_data, error_msg = search_scb_by_orgnr(org_nr, company_name)

        if success and scb_data:
            # Platta ut SCB-data
            flat_data = flatten_scb_result(scb_data)
            success_data.append(flat_data)

            scb_name = scb_data.get('Företagsnamn', 'N/A')
            city = scb_data.get('PostOrt', 'N/A')
            print(f"  ✅ {scb_name} - {city}")
        else:
            # Spara fel
            failed_data.append({
                'organization_number': org_nr,
                'error_message': error_msg or 'Okänt fel',
                'timestamp': datetime.now().isoformat()
            })
            print(f"  ❌ {error_msg}")

        # Rate limiting (utom på sista)
        if i < len(companies):
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
    print(f"Totalt företag: {len(companies)}")
    print(f"Lyckade requests: {len(success_data)} ({len(success_data)/len(companies)*100:.1f}%)")
    print(f"Misslyckade requests: {len(failed_data)} ({len(failed_data)/len(companies)*100:.1f}%)")
    print(f"Körtid: {duration:.1f} sekunder ({duration/60:.1f} minuter)")
    print(f"Genomsnittlig tid per request: {duration/len(companies):.2f} sekunder")
    print(f"\n✅ Klart!")

if __name__ == "__main__":
    main()

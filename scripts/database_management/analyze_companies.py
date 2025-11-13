#!/usr/bin/env python3
"""
Analysera specifika företag från PRAKTIKJAKT-databasen
Används för att testa om specifika IDs eller kategorie av företag
"""

import requests
import sqlite3
import time
import json
from fuzzywuzzy import fuzz
from typing import List, Dict, Tuple

# =============================================================================
# KONFIGURATION
# =============================================================================

API_URL = 'https://privateapi.scb.se/nv0101/v1/sokpavar/api/je/HamtaForetag'
CERT_PATH = 'certifikat/Certifikat_SokPaVar_A00592_2025-10-29_09-27-36Z.pem'
DB_PATH = 'ai_companies.db'

# =============================================================================
# SCB API-FUNKTIONER
# =============================================================================

def search_scb(company_name: str, verbose: bool = True) -> List[Dict]:
    """Sök företag i SCB"""
    payload = {
        "Företagsstatus": "1",
        "Registreringsstatus": "1",
        "variabler": [
            {
                "Varde1": company_name,
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
        
        if verbose:
            print(f"  API Status: {response.status_code}")
            print(f"  Träffar: {len(results)}")
            
            if len(results) > 100:
                print(f"  ⚠️  MÅNGA TRÄFFAR! ({len(results)}) - Risk för 2000-radgräns")
        
        return results
    
    except Exception as e:
        print(f"  ✗ API-fel: {e}")
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

def find_best_match(our_name: str, scb_results: List[Dict]) -> Tuple[Dict, int, str]:
    """Hitta bästa match med fuzzy score"""
    if not scb_results:
        return None, 0, "no_results"
    
    our_normalized = normalize_name(our_name)
    
    best_match = None
    best_score = 0
    
    for company in scb_results:
        scb_name = company.get('Företagsnamn', '')
        scb_normalized = normalize_name(scb_name)
        
        score = fuzz.ratio(our_normalized, scb_normalized)
        
        if score > best_score:
            best_score = score
            best_match = company
    
    if best_score >= 85:
        status = "match"
    elif best_score >= 70:
        status = "low_score"
    else:
        status = "very_low_score"
    
    return best_match, best_score, status

# =============================================================================
# DATABAS-FUNKTIONER
# =============================================================================

def get_companies_by_ids(db_path: str, company_ids: List[int]) -> List[Tuple]:
    """Hämta företag baserat på ID-lista"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(company_ids))
    query = f"""
        SELECT id, name, website, type, location_city
        FROM companies 
        WHERE id IN ({placeholders})
        ORDER BY id
    """
    
    cursor.execute(query, company_ids)
    companies = cursor.fetchall()
    conn.close()
    
    return companies

def get_companies_by_category(db_path: str, category: str) -> List[Tuple]:
    """
    Hämta företag baserat på kategori
    
    Categories:
    - 'low_score': Företag med fuzzy score 70-84
    - 'api_error': Företag med API-fel
    - 'no_results': Företag utan resultat
    - 'no_city': Företag utan location_city
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if category == 'low_score':
        query = """
            SELECT c.id, c.name, c.website, c.type, c.location_city,
                   s.fuzzy_score, s.best_candidate
            FROM companies c
            JOIN scb_matches s ON c.id = s.company_id
            WHERE s.matched = 0 
            AND s.fuzzy_score BETWEEN 70 AND 84
            ORDER BY s.fuzzy_score DESC
        """
    
    elif category == 'api_error':
        query = """
            SELECT c.id, c.name, c.website, c.type, c.location_city
            FROM companies c
            JOIN scb_matches s ON c.id = s.company_id
            WHERE s.status = 'api_error'
            ORDER BY c.name
        """
    
    elif category == 'no_results':
        query = """
            SELECT c.id, c.name, c.website, c.type, c.location_city
            FROM companies c
            JOIN scb_matches s ON c.id = s.company_id
            WHERE s.status = 'no_results'
            AND c.type IN ('startup', 'corporation', 'supplier', 'ngo')
            ORDER BY c.name
        """
    
    elif category == 'no_city':
        query = """
            SELECT id, name, website, type, location_city
            FROM companies
            WHERE location_city IS NULL
            AND type IN ('startup', 'corporation', 'supplier', 'ngo')
            ORDER BY name
        """
    
    else:
        print(f"Okänd kategori: {category}")
        conn.close()
        return []
    
    cursor.execute(query)
    companies = cursor.fetchall()
    conn.close()
    
    return companies

# =============================================================================
# ANALYS-FUNKTIONER
# =============================================================================

def analyze_company(company_id: int, name: str, verbose: bool = True):
    """Analysera ett specifikt företag"""
    print(f"\n{'='*70}")
    print(f"[ID {company_id}] {name}")
    print('='*70)
    
    # Sök i SCB
    results = search_scb(name, verbose=verbose)
    
    if not results:
        print("  ✗ Inga resultat från SCB")
        return None
    
    # Visa topp 5 träffar
    print(f"\n  Topp 5 träffar:")
    for i, company in enumerate(results[:5], 1):
        scb_name = company.get('Företagsnamn', '')
        city = company.get('PostOrt', '')
        org_nr = company.get('OrgNr', '')
        
        # Beräkna fuzzy score
        our_normalized = normalize_name(name)
        scb_normalized = normalize_name(scb_name)
        score = fuzz.ratio(our_normalized, scb_normalized)
        
        print(f"  {i}. {scb_name}")
        print(f"     Ort: {city}")
        print(f"     Org.nr: {org_nr}")
        print(f"     Fuzzy score: {score}")
        print()
    
    # Bästa match
    best_match, best_score, status = find_best_match(name, results)
    
    print(f"  Bästa match:")
    print(f"  ├─ Företag: {best_match.get('Företagsnamn')}")
    print(f"  ├─ Stad: {best_match.get('PostOrt')}")
    print(f"  ├─ Score: {best_score}")
    print(f"  └─ Status: {status}")
    
    if len(results) > 10:
        print(f"\n  💡 Tips: {len(results)} träffar totalt - kan behöva mer specifik sökning")
    
    return {
        'id': company_id,
        'name': name,
        'scb_name': best_match.get('Företagsnamn'),
        'city': best_match.get('PostOrt'),
        'score': best_score,
        'status': status,
        'total_results': len(results)
    }

def analyze_batch(companies: List[Tuple], rate_limit: float = 0.5):
    """Analysera en batch av företag"""
    print(f"\n{'='*70}")
    print(f"BATCH-ANALYS: {len(companies)} företag")
    print('='*70)
    
    results = []
    
    for i, company in enumerate(companies, 1):
        company_id = company[0]
        name = company[1]
        
        print(f"\n[{i}/{len(companies)}]", end=" ")
        result = analyze_company(company_id, name, verbose=False)
        
        if result:
            results.append(result)
        
        # Rate limiting
        if i < len(companies):
            time.sleep(rate_limit)
    
    # Sammanfattning
    print(f"\n{'='*70}")
    print("SAMMANFATTNING")
    print('='*70)
    
    matches = sum(1 for r in results if r['status'] == 'match')
    low_scores = sum(1 for r in results if r['status'] == 'low_score')
    very_low = sum(1 for r in results if r['status'] == 'very_low_score')
    
    print(f"Total: {len(results)}")
    print(f"Matches (≥85): {matches} ({matches/len(results)*100:.1f}%)")
    print(f"Low score (70-84): {low_scores} ({low_scores/len(results)*100:.1f}%)")
    print(f"Very low (<70): {very_low} ({very_low/len(results)*100:.1f}%)")
    
    # Företag med många träffar
    many_hits = [r for r in results if r['total_results'] > 50]
    if many_hits:
        print(f"\n⚠️  Företag med många träffar (>50):")
        for r in many_hits:
            print(f"  - {r['name']}: {r['total_results']} träffar")
    
    return results

# =============================================================================
# MAIN
# =============================================================================

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("""
Användning:

  # Analysera specifika IDs
  python analyze_companies.py ids 123 456 789
  
  # Analysera kategori
  python analyze_companies.py category low_score
  python analyze_companies.py category api_error
  python analyze_companies.py category no_results
  python analyze_companies.py category no_city
  
  # Analysera ett företag interaktivt
  python analyze_companies.py single "Företagsnamn AB"

Kategorier:
  low_score  - Företag med fuzzy score 70-84
  api_error  - Företag med API-fel
  no_results - Företag utan resultat från SCB
  no_city    - Alla företag utan location_city
""")
        sys.exit(0)
    
    mode = sys.argv[1]
    
    if mode == 'ids':
        # Specifika IDs
        company_ids = [int(x) for x in sys.argv[2:]]
        print(f"Hämtar {len(company_ids)} företag från databas...")
        companies = get_companies_by_ids(DB_PATH, company_ids)
        
        if not companies:
            print("Inga företag hittades med dessa IDs")
            sys.exit(1)
        
        analyze_batch(companies)
    
    elif mode == 'category':
        if len(sys.argv) < 3:
            print("Ange kategori: low_score, api_error, no_results, no_city")
            sys.exit(1)
        
        category = sys.argv[2]
        print(f"Hämtar företag i kategori '{category}'...")
        companies = get_companies_by_category(DB_PATH, category)
        
        if not companies:
            print(f"Inga företag i kategori '{category}'")
            sys.exit(1)
        
        # Begränsa till max 50 företag för säkerhets skull
        if len(companies) > 50:
            print(f"Hittade {len(companies)} företag. Vill du verkligen analysera alla?")
            response = input("Analysera alla? (ja/nej): ")
            if response.lower() not in ['ja', 'j', 'yes', 'y']:
                print("Avbryter...")
                sys.exit(0)
        
        analyze_batch(companies)
    
    elif mode == 'single':
        if len(sys.argv) < 3:
            print("Ange företagsnamn: python analyze_companies.py single 'Spotify AB'")
            sys.exit(1)
        
        name = " ".join(sys.argv[2:])
        analyze_company(0, name, verbose=True)
    
    else:
        print(f"Okänt läge: {mode}")
        sys.exit(1)

if __name__ == "__main__":
    main()

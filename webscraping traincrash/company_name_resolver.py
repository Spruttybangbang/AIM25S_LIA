#!/usr/bin/env python3
"""
Company Name Resolver
=====================

PROBLEMET:
- Vi har företagsnamn i vår databas som "Arlaplast"
- Men i SCB heter det "Arla Plast AB"
- SCB API ger ingen träff

LÖSNINGEN:
- Gå in på företagets egen webbsajt
- Hitta deras OFFICIELLA företagsnamn (juridiskt namn)
- Hitta deras organisationsnummer (om det finns på sajten)
- Använd det för korrekt SCB-sökning

STRATEGI:
1. Kolla företagets webbsajt (footer, Om oss, Kontakt)
2. Leta efter org.nr (vanligt i footer)
3. Leta efter officiellt företagsnamn (ofta "© 2024 Företag AB")
4. Exportera mappning: ditt_namn → officiellt_namn + org.nr
"""

import argparse
import csv
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ============================================================================
# KONFIGURATION
# ============================================================================

DB_PATH = Path(__file__).parent.parent / "databases" / "ai_companies.db"
RATE_LIMIT_DELAY = 1.0
TIMEOUT = 10

# Sidor att kolla (i prioritetsordning)
PAGES_TO_CHECK = [
    "",  # Huvudsida
    "/om-oss",
    "/about",
    "/about-us",
    "/kontakt",
    "/contact",
    "/foretaget",
    "/company",
]

# ============================================================================
# ORG.NR EXTRAKTION
# ============================================================================

def extract_orgnr_from_text(text: str) -> Optional[str]:
    """
    Hitta org.nr i text
    
    Vanliga format på företags egna sajter:
    - Organisationsnummer: 556498-5025
    - Org.nr: 556498-5025
    - Org nr 5564985025
    - © 2024 Företag AB (556498-5025)
    """
    if not text:
        return None

    patterns = [
        # Med label "Organisationsnummer" eller "Org.nr"
        r'[Oo]rg(?:anisations)?\.?\s*[Nn]r\.?\s*[:\-]?\s*(\d{6}[-\s]?\d{4})',
        # I parentes (vanligt i footer)
        r'\((\d{6}[-\s]?\d{4})\)',
        # Standard format
        r'\b(\d{6}-\d{4})\b',
        # 10 siffror i rad (börjar med 5)
        r'\b(5\d{9})\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            orgnr = match.group(1).replace(' ', '').replace('-', '')
            if len(orgnr) == 10 and orgnr[0] == '5':
                return f"{orgnr[:6]}-{orgnr[6:]}"
    
    return None


# ============================================================================
# FÖRETAGSNAMN EXTRAKTION
# ============================================================================

def extract_official_company_name(soup: BeautifulSoup, url: str) -> List[str]:
    """
    Försök hitta företagets officiella namn på sajten
    
    Strategier:
    1. Copyright text i footer (© 2024 Företag AB)
    2. "Om oss" headings
    3. Meta tags (og:site_name, etc)
    4. Address/vCard markup
    
    Returns:
        Lista med kandidater (kan vara flera)
    """
    candidates = []
    
    # 1. COPYRIGHT I FOOTER
    # Leta efter © följt av företagsnamn
    copyright_patterns = [
        r'©\s*\d{4}\s+([^.\n]+?(?:AB|Aktiebolag|HB|KB))',
        r'[Cc]opyright\s*\d{4}\s+([^.\n]+?(?:AB|Aktiebolag|HB|KB))',
    ]
    
    footer = soup.find('footer')
    if footer:
        footer_text = footer.get_text()
        for pattern in copyright_patterns:
            matches = re.findall(pattern, footer_text)
            candidates.extend(matches)
    
    # 2. META TAGS
    meta_tags = [
        ('property', 'og:site_name'),
        ('name', 'og:site_name'),
        ('property', 'twitter:site'),
    ]
    
    for attr_name, attr_value in meta_tags:
        meta = soup.find('meta', {attr_name: attr_value})
        if meta and meta.get('content'):
            candidates.append(meta['content'])
    
    # 3. STRUCTURED DATA (JSON-LD)
    # Leta efter Organization schema
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            import json
            data = json.loads(script.string)
            if isinstance(data, dict):
                if data.get('@type') == 'Organization':
                    if data.get('legalName'):
                        candidates.append(data['legalName'])
                    elif data.get('name'):
                        candidates.append(data['name'])
        except:
            pass
    
    # 4. HEADINGS PÅ "OM OSS"-SIDA
    # Om URL:en innehåller "om" eller "about"
    if any(word in url.lower() for word in ['/om', '/about', '/foretag', '/company']):
        h1 = soup.find('h1')
        if h1:
            candidates.append(h1.get_text(strip=True))
    
    # 5. COMPANY NAME I ADDRESS/VCARD
    # Leta efter mikroformat eller adresser
    addresses = soup.find_all(['address', 'div'], class_=re.compile('vcard|company|organization'))
    for addr in addresses:
        text = addr.get_text()
        # Leta efter något som slutar på AB, Aktiebolag etc
        match = re.search(r'([A-ZÅÄÖ][a-zåäö\s]+(?:AB|Aktiebolag|HB|KB))', text)
        if match:
            candidates.append(match.group(1))
    
    # Rensa och normalisera kandidater
    cleaned = []
    for c in candidates:
        c = c.strip()
        # Ta bort extra whitespace
        c = re.sub(r'\s+', ' ', c)
        # Måste innehålla minst 3 tecken
        if len(c) >= 3:
            # Ta bort vanliga suffixer som inte hör till namnet
            c = re.sub(r'\s*\|.*$', '', c)
            cleaned.append(c)
    
    # Ta bort dubbletter, behåll ordning
    seen = set()
    unique = []
    for c in cleaned:
        if c.lower() not in seen:
            seen.add(c.lower())
            unique.append(c)
    
    return unique


# ============================================================================
# WEB SCRAPING
# ============================================================================

def scrape_company_website(website: str) -> Dict[str, any]:
    """
    Scrapa företagets webbsajt för att hitta officiellt namn och org.nr

    Returns:
        {
            'official_names': [lista med kandidater],
            'orgnr': 'XXXXXX-XXXX' eller None,
            'found_on_page': 'URL där info hittades',
            'error': None eller felmeddelande
        }
    """
    result = {
        'official_names': [],
        'orgnr': None,
        'found_on_page': None,
        'error': None
    }

    # Normalisera URL
    if not website:
        result['error'] = "Ingen webbsajt angiven"
        return result

    if not website.startswith('http'):
        website = 'https://' + website

    # Ta bort trailing slash
    website = website.rstrip('/')

    # Skapa en session för att behålla cookies
    session = requests.Session()

    # Realistiska headers för att undvika blockering
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }

    # Försök olika sidor
    for page_path in PAGES_TO_CHECK:
        url = website + page_path

        try:
            response = session.get(
                url,
                timeout=TIMEOUT,
                headers=headers,
                allow_redirects=True
            )
            
            # Om 404, testa nästa sida
            if response.status_code == 404:
                continue
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Leta efter org.nr
            page_text = soup.get_text()
            orgnr = extract_orgnr_from_text(page_text)
            
            # Leta efter företagsnamn
            names = extract_official_company_name(soup, url)
            
            # Om vi hittade något, spara det
            if orgnr or names:
                if orgnr and not result['orgnr']:
                    result['orgnr'] = orgnr
                    result['found_on_page'] = url
                
                if names:
                    # Lägg till nya unika namn
                    for name in names:
                        if name not in result['official_names']:
                            result['official_names'].append(name)
                
                # Om vi hittade org.nr, sluta söka
                if result['orgnr']:
                    break
            
            # Vänta lite mellan sidorna
            time.sleep(0.3)
        
        except requests.exceptions.Timeout:
            result['error'] = f"Timeout vid hämtning av {url}"
            continue
        except requests.exceptions.ConnectionError:
            result['error'] = f"Kunde inte ansluta till {url}"
            continue
        except Exception as e:
            result['error'] = f"Fel vid scraping: {str(e)}"
            continue
    
    # Om vi inte hittade något alls
    if not result['official_names'] and not result['orgnr']:
        if not result['error']:
            result['error'] = "Hittade inget företagsnamn eller org.nr på webbsajten"
    
    return result


# ============================================================================
# DATABASE
# ============================================================================

def get_companies_without_scb(limit: Optional[int] = None) -> List[Tuple]:
    """Hämta företag som saknar SCB-data OCH har en webbsajt"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    query = """
        SELECT c.id, c.name, c.type, c.website
        FROM companies c
        LEFT JOIN scb_enrichment se ON c.id = se.company_id
        WHERE se.company_id IS NULL
        AND c.website IS NOT NULL
        AND c.website != ''
        ORDER BY c.name
    """

    if limit:
        query += " LIMIT ?"
        cursor.execute(query, [limit])
    else:
        cursor.execute(query)
    
    results = cursor.fetchall()
    conn.close()

    return results


def process_company(company_id: int, name: str, company_type: str, website: str) -> Dict:
    """Processa ett företag"""
    print(f"\n{'='*70}")
    print(f"🏢 {name}")
    print(f"   Webbsajt: {website}")
    
    # Scrapa webbsajten
    scrape_result = scrape_company_website(website)
    
    result = {
        'company_id': company_id,
        'company_name': name,
        'company_type': company_type,
        'website': website,
        'found_orgnr': scrape_result['orgnr'] or '',
        'official_name_1': '',
        'official_name_2': '',
        'official_name_3': '',
        'found_on_page': scrape_result['found_on_page'] or '',
        'error': scrape_result['error'] or '',
        'notes': ''
    }
    
    # Fyll i upp till 3 namnkandidater
    names = scrape_result['official_names']
    if len(names) >= 1:
        result['official_name_1'] = names[0]
    if len(names) >= 2:
        result['official_name_2'] = names[1]
    if len(names) >= 3:
        result['official_name_3'] = names[2]
    
    # Skriv ut resultat
    if scrape_result['orgnr']:
        print(f"   ✅ Org.nr: {scrape_result['orgnr']}")
    
    if scrape_result['official_names']:
        print(f"   📝 Officiella namn hittade:")
        for i, n in enumerate(scrape_result['official_names'][:3], 1):
            print(f"      {i}. {n}")
    
    if scrape_result['error']:
        print(f"   ⚠️  {scrape_result['error']}")
    
    return result


def export_to_csv(results: List[Dict], output_path: Path):
    """Exportera resultat till CSV"""
    if not results:
        print("⚠️  Inga resultat att exportera")
        return

    fieldnames = [
        'company_id',
        'company_name',
        'company_type',
        'website',
        'found_orgnr',
        'official_name_1',
        'official_name_2',
        'official_name_3',
        'found_on_page',
        'error',
        'notes'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Exporterat till: {output_path}")


# ============================================================================
# MAIN
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Hitta företags officiella namn genom att scrapa deras egna webbsajter"
    )
    parser.add_argument("--limit", type=int, help="Max antal företag att processa")
    parser.add_argument("--output", type=str, help="Output CSV-fil")
    parser.add_argument("--yes", "-y", action="store_true", help="Hoppa över bekräftelse")
    return parser.parse_args()


def main():
    args = parse_args()

    print("="*70)
    print("🔍 COMPANY NAME RESOLVER")
    print("="*70)
    print("\nHittar företagens OFFICIELLA namn från deras egna webbsajter")
    print("Detta hjälper dig matcha mot SCB:s databas korrekt!\n")

    # Hämta företag
    companies = get_companies_without_scb(limit=args.limit)
    
    print(f"📊 Hittade {len(companies)} företag med webbsajt men utan SCB-data")
    
    if not companies:
        print("\nInga företag att processa.")
        return

    # Bekräftelse
    if not args.yes:
        estimated_time = len(companies) * 3  # ~3 sekunder per företag
        print(f"\n⏱️  Uppskattat tid: ~{estimated_time / 60:.0f} minuter")
        
        response = input("\nFortsätta? (y/n): ")
        if response.lower() != 'y':
            print("Avbryter.")
            return

    print(f"\n🚀 Startar scraping av {len(companies)} webbsajter...\n")

    # Processa varje företag
    results = []
    for i, (company_id, name, company_type, website) in enumerate(companies, 1):
        print(f"[{i}/{len(companies)}]", end=" ")
        
        try:
            result = process_company(company_id, name, company_type, website)
            results.append(result)
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Avbrutet av användaren")
            break
        except Exception as e:
            print(f"\n❌ Oväntat fel: {e}")
            continue

    # Exportera
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path(args.output or f"company_names_resolved_{timestamp}.csv")
        export_to_csv(results, output_path)

        # Statistik
        with_orgnr = sum(1 for r in results if r['found_orgnr'])
        with_names = sum(1 for r in results if r['official_name_1'])
        
        print(f"\n📊 Statistik:")
        print(f"   Totalt processade: {len(results)}")
        print(f"   Hittade org.nr: {with_orgnr} ({with_orgnr/len(results)*100:.0f}%)")
        print(f"   Hittade officiellt namn: {with_names} ({with_names/len(results)*100:.0f}%)")
        
        print(f"\n💡 Nästa steg:")
        print(f"   1. Öppna {output_path}")
        print(f"   2. Granska 'official_name_1/2/3' kolumnerna")
        print(f"   3. Välj rätt officiellt namn för varje företag")
        print(f"   4. Använd det namnet för att söka i SCB API")

    print("\n✅ Klart!")


if __name__ == "__main__":
    main()

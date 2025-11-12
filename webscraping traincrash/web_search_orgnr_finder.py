#!/usr/bin/env python3
"""
Web Search Org.nr Finder
Söker efter organisationsnummer via DuckDuckGo och exporterar till CSV för manuell verifiering

Strategi:
1. Hämta företag utan SCB-data
2. Sök på DuckDuckGo med flera variabler
3. Extrahera org.nr från sökresultaten
4. Gör en kvalificerad gissning på rätt org.nr
5. Exportera till CSV för manuell kontroll

Usage:
    python3 web_search_orgnr_finder.py --limit 10
    python3 web_search_orgnr_finder.py --only-type startup
"""

import argparse
import csv
import json
import re
import sqlite3
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

try:
    from fuzzywuzzy import fuzz
except ImportError:
    # Fallback om fuzzywuzzy inte finns installerad
    class fuzz:
        @staticmethod
        def ratio(a, b):
            # Enkel likhetsmatchning baserad på gemensamma ord
            a_lower = a.lower()
            b_lower = b.lower()
            if a_lower in b_lower or b_lower in a_lower:
                return 90
            return 50

# ============================================================================
# KONFIGURATION
# ============================================================================

DB_PATH = Path(__file__).parent.parent / "databases" / "ai_companies.db"
RATE_LIMIT_DELAY = 1.5  # Sekunder mellan sökningar
TIMEOUT = 15

# Sökvariabler att använda (fokusera på de sajter som faktiskt fungerar)
SEARCH_TERMS = [
    "site:allabolag.se",
    "site:bolagsfakta.se"
]

# ============================================================================
# ORG.NR REGEX
# ============================================================================

def extract_orgnr_candidates(text: str) -> List[str]:
    """
    Hitta alla potentiella org.nr i text

    Specialformat som prioriteras:
    - Allabolag: "Företag AB - Org.nr 556498-5025 - Ort"
    - Bolagsfakta URL: "bolagsfakta.se/5569631913-Foretagsnamn"

    Standard format:
    - XXXXXX-XXXX (standard)
    - XXXXXXXXXX (10 siffror)
    - 16XXXXXXXXXX (12 siffror med 16-prefix)
    """
    if not text:
        return []

    candidates = []

    # PRIORITET 1: Allabolag format "Org.nr XXXXXX-XXXX"
    allabolag_pattern = r'[Oo]rg\.?\s*[Nn]r\.?\s*[:\-]?\s*(\d{6}-\d{4})'
    allabolag_matches = re.findall(allabolag_pattern, text)
    candidates.extend(allabolag_matches)

    # PRIORITET 2: Bolagsfakta URL format "/XXXXXXXXXX-Foretagsnamn"
    bolagsfakta_pattern = r'bolagsfakta\.se[^\d]*(\d{10})'
    bolagsfakta_matches = re.findall(bolagsfakta_pattern, text)
    candidates.extend([f"{m[:6]}-{m[6:]}" for m in bolagsfakta_matches])

    # Pattern 3: Standard XXXXXX-XXXX
    pattern1 = r'\b(\d{6}-\d{4})\b'
    matches1 = re.findall(pattern1, text)
    candidates.extend(matches1)

    # Pattern 4: 10 siffror i rad (börjar med 5 för aktiebolag)
    pattern2 = r'\b(5\d{9})\b'
    matches2 = re.findall(pattern2, text)
    # Formatera till XXXXXX-XXXX
    candidates.extend([f"{m[:6]}-{m[6:]}" for m in matches2])

    # Pattern 5: 16XXXXXXXXXX (12 siffror)
    pattern3 = r'\b(16\d{10})\b'
    matches3 = re.findall(pattern3, text)
    # Ta bort 16-prefix och formatera
    candidates.extend([f"{m[2:8]}-{m[8:]}" for m in matches3])

    # Ta bort dubbletter, behåll ordning
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    return unique


def extract_company_name_from_result(text: str, url: str) -> Optional[str]:
    """
    Försök extrahera företagsnamn från sökresultat

    Prioriterar:
    - Allabolag format: "Företagsnamn AB - Org.nr..."
    - Bolagsfakta URL: "...5569631913-AIxDesign_Global_AB"
    """
    if not text and not url:
        return None

    # Allabolag titel format: "Decerno Aktiebolag - Org.nr 556498-5025 - Stockholm"
    allabolag_match = re.search(r'^([^-]+?)\s*-\s*[Oo]rg\.?\s*[Nn]r', text)
    if allabolag_match:
        return allabolag_match.group(1).strip()

    # Bolagsfakta URL format: "bolagsfakta.se/5569631913-AIxDesign_Global_AB"
    bolagsfakta_match = re.search(r'bolagsfakta\.se[^\d]*\d{10}-([^/\s]+)', text + " " + url)
    if bolagsfakta_match:
        # Ersätt understreck med mellanslag
        name = bolagsfakta_match.group(1).replace('_', ' ')
        return name.strip()

    return None


# ============================================================================
# DUCKDUCKGO SEARCH
# ============================================================================

def duckduckgo_search(query: str, searched_name: str) -> Tuple[str, str, str, str]:
    """
    Sök på DuckDuckGo och returnera BÄSTA träffen baserat på namnmatchning

    Args:
        query: Sökfråga
        searched_name: Det företagsnamn vi söker efter (för matchning)

    Returns:
        (best_result_url, best_result_text, best_company_name, best_orgnr)
    """
    try:
        with DDGS() as ddgs:
            # Hämta 10 resultat för att komma förbi annonser
            results = list(ddgs.text(query, region='se-sv', max_results=10))

            if not results:
                return "", "[Inga resultat hittades]", "", ""

            # Filtrera bort annonser och irrelevanta resultat
            organic_results = []
            for result in results:
                url = result.get('href', '')
                title = result.get('title', '')
                body = result.get('body', '')

                # Filtrera bort annonser och irrelevanta sajter
                skip_domains = [
                    'ad.doubleclick', 'googleads', 'adservice',
                    'adroll', 'facebook.com/ads', 'linkedin.com/ads',
                    'allabolag.se/sök-',  # Söksida, inte företag
                    'allabolag.se/befattning/',  # Personprofiler, inte företag
                    '/listor',  # Listor
                    '/bransch/',  # Branschöversikter
                ]

                if any(domain in url.lower() for domain in skip_domains):
                    continue

                # Måste vara från allabolag eller bolagsfakta
                if 'allabolag.se' not in url and 'bolagsfakta.se' not in url:
                    continue

                text = f"{title} {body} {url}"

                # Extrahera företagsnamn
                company_name = extract_company_name_from_result(text, url)

                # Extrahera org.nr
                orgnr_list = extract_orgnr_candidates(text)
                orgnr = orgnr_list[0] if orgnr_list else ""

                # Skippa om vi inte hittar företagsnamn ELLER org.nr
                if not company_name and not orgnr:
                    continue

                organic_results.append({
                    'url': url,
                    'text': text[:500],
                    'company_name': company_name or "",
                    'orgnr': orgnr,
                })

            if not organic_results:
                return "", "[Inga organiska resultat hittades]", "", ""

            # Hitta BÄSTA matchningen genom namnlikhet
            searched_normalized = normalize_company_name(searched_name)
            best_match = None
            best_similarity = 0

            for candidate in organic_results:
                if not candidate['company_name']:
                    continue

                candidate_normalized = normalize_company_name(candidate['company_name'])
                similarity = fuzz.ratio(searched_normalized, candidate_normalized)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = candidate

            # Om vi hittade en bra matchning (>60% likhet), använd den
            if best_match and best_similarity >= 60:
                return (
                    best_match['url'],
                    best_match['text'],
                    best_match['company_name'],
                    best_match['orgnr']
                )

            # Annars: ta första resultatet med org.nr
            for candidate in organic_results:
                if candidate['orgnr']:
                    return (
                        candidate['url'],
                        candidate['text'],
                        candidate['company_name'],
                        candidate['orgnr']
                    )

            # Sista utväg: första resultatet
            first = organic_results[0]
            return (
                first['url'],
                first['text'],
                first['company_name'],
                first['orgnr']
            )

    except Exception as e:
        return "", f"[ERROR: {str(e)}]", "", ""


# ============================================================================
# KVALIFICERAD GISSNING
# ============================================================================

def normalize_company_name(name: str) -> str:
    """Normalisera företagsnamn för matchning"""
    if not name:
        return ""

    # Ta bort vanliga suffix
    name = name.upper()
    for suffix in [' AB', ' AKTIEBOLAG', ' HB', ' KB', ' EK. FÖR.']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    return name.strip()


def suggest_best_orgnr(
    orgnr_name_pairs: List[Tuple[str, str]],
    searched_company_name: str,
    owner: Optional[str]
) -> Tuple[Optional[str], float, str]:
    """
    Gör en kvalificerad gissning på vilket org.nr som är rätt baserat på namnmatchning

    Args:
        orgnr_name_pairs: Lista av (org.nr, extraherat_namn) par
        searched_company_name: Det företagsnamn vi söker på
        owner: Owner-information om tillgängligt

    Returns:
        (orgnr, confidence_score, reason)
    """
    if not orgnr_name_pairs:
        return None, 0.0, "Inga org.nr hittades"

    # Om bara ett org.nr hittades
    if len(orgnr_name_pairs) == 1:
        orgnr, name = orgnr_name_pairs[0]
        return orgnr, 0.9, f"Endast ett org.nr hittades: {name}"

    # Normalisera det sökta namnet
    searched_normalized = normalize_company_name(searched_company_name)

    # Beräkna likhet mellan sökt namn och varje extraherat namn
    best_match = None
    best_score = 0
    best_orgnr = None

    for orgnr, extracted_name in orgnr_name_pairs:
        if not extracted_name:
            continue

        extracted_normalized = normalize_company_name(extracted_name)

        # Fuzzy matching
        similarity = fuzz.ratio(searched_normalized, extracted_normalized)

        if similarity > best_score:
            best_score = similarity
            best_match = extracted_name
            best_orgnr = orgnr

    # Om vi hittade en bra matchning (>70% likhet)
    if best_score >= 70:
        confidence = min(0.95, best_score / 100.0)
        return best_orgnr, confidence, f"Bästa namnmatchning: '{best_match}' ({best_score}% likhet)"

    # Fallback: Om vi inte kunde matcha på namn, ta första från allabolag
    # (antar att första paret är från allabolag om vi har det)
    if orgnr_name_pairs:
        orgnr, name = orgnr_name_pairs[0]
        return orgnr, 0.5, f"Första hittade: {name or orgnr} (låg namnlikhet)"

    return None, 0.0, "Kunde inte bestämma rätt org.nr"


# ============================================================================
# HUVUDLOGIK
# ============================================================================

def get_companies_without_scb(
    limit: Optional[int] = None,
    only_types: Optional[List[str]] = None
) -> List[Tuple]:
    """Hämta företag utan SCB-data"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    query = """
        SELECT c.id, c.name, c.type, c.owner, c.website
        FROM companies c
        LEFT JOIN scb_enrichment se ON c.id = se.company_id
        WHERE se.company_id IS NULL
    """

    params = []

    if only_types:
        placeholders = ",".join("?" for _ in only_types)
        query += f" AND c.type IN ({placeholders})"
        params.extend(only_types)

    query += " ORDER BY c.type, c.name"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return results


def search_company(
    company_id: int,
    name: str,
    company_type: str,
    owner: Optional[str],
    website: Optional[str]
) -> Dict:
    """
    Sök efter ett företags org.nr på webben

    Returns:
        Dict med alla sökresultat och gissning
    """
    print(f"\n{'='*70}")
    print(f"🔍 Söker: {name} ({company_type})")
    if owner:
        print(f"   Owner: {owner}")

    result = {
        "company_id": company_id,
        "company_name": name,
        "company_type": company_type,
        "owner": owner or "",
        "website": website or "",
    }

    orgnr_name_pairs = []  # Lista av (org.nr, namn) par för matchning

    # Sök med varje sökterm (allabolag och bolagsfakta)
    for i, term in enumerate(SEARCH_TERMS, 1):
        # Enkel sökning utan title: (fungerar bättre med DuckDuckGo)
        query = f"{name} {term}"

        print(f"   [{i}/2] Söker: {query}")

        url, text, company_name_found, orgnr_found = duckduckgo_search(query, name)

        # Spara resultat i enkel format
        result[f"search_query_{i}"] = query
        result[f"best_match_{i}"] = company_name_found
        result[f"found_orgnr_{i}"] = orgnr_found

        # Koppla ihop org.nr med namn för matchning
        if orgnr_found and company_name_found:
            orgnr_name_pairs.append((orgnr_found, company_name_found))

        print(f"      → Namn: {company_name_found or '(inget)'}")
        print(f"      → Org.nr: {orgnr_found or '(inget)'}")

        # Rate limiting
        if i < len(SEARCH_TERMS):
            time.sleep(RATE_LIMIT_DELAY)

    # Gör kvalificerad gissning baserat på namnmatchning
    suggested, confidence, reason = suggest_best_orgnr(
        orgnr_name_pairs, name, owner
    )

    result["suggested_orgnr"] = suggested or ""
    result["confidence_score"] = f"{confidence:.2f}"
    result["suggestion_reason"] = reason
    result["verified_orgnr"] = ""  # Tom för manuell input
    result["notes"] = ""  # Tom för anteckningar

    print(f"   ✅ Förslag: {suggested or '(inget)'} (confidence: {confidence:.0%})")
    if reason:
        print(f"      Anledning: {reason}")

    return result


def export_to_csv(results: List[Dict], output_path: Path):
    """Exportera resultat till CSV"""
    if not results:
        print("⚠️  Inga resultat att exportera")
        return

    # Definiera kolumnordning (förenklad struktur)
    fieldnames = [
        # Företagsinfo
        "company_id",
        "company_name",

        # Sökresultat 1: allabolag
        "search_query_1",
        "best_match_1",
        "found_orgnr_1",

        # Sökresultat 2: bolagsfakta
        "search_query_2",
        "best_match_2",
        "found_orgnr_2",

        # Scriptets gissning
        "suggested_orgnr",
        "confidence_score",
        "suggestion_reason",

        # Manuell verifiering
        "verified_orgnr",
        "notes"
    ]

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Exporterat till: {output_path}")
    print(f"   Rader: {len(results)}")


# ============================================================================
# CLI
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Sök efter organisationsnummer via DuckDuckGo"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Max antal företag att söka"
    )
    parser.add_argument(
        "--only-type",
        type=str,
        help="Kommaseparerad lista av företagstyper (ex: startup,corporation)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV-fil (default: orgnr_search_TIMESTAMP.csv)"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Hoppa över bekräftelse"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("="*70)
    print("🔍 WEB SEARCH ORG.NR FINDER")
    print("="*70)
    print("\nDetta script söker efter organisationsnummer via DuckDuckGo")
    print("och exporterar resultaten till CSV för manuell verifiering.\n")

    # Parse types
    only_types = None
    if args.only_type:
        only_types = [t.strip() for t in args.only_type.split(",")]
        print(f"📋 Filtrerar på typer: {', '.join(only_types)}")

    # Hämta företag
    companies = get_companies_without_scb(limit=args.limit, only_types=only_types)

    print(f"📊 Hittade {len(companies)} företag utan SCB-data")

    if not companies:
        print("Inga företag att bearbeta. Avslutar.")
        return

    # Fråga om bekräftelse (om inte --yes)
    if not args.yes:
        searches_per_company = 2  # allabolag + bolagsfakta (+ owner om det finns)
        print(f"\n⚠️  Detta kommer göra ~{len(companies) * searches_per_company} sökningar på DuckDuckGo")
        print(f"   Med {RATE_LIMIT_DELAY}s delay = ~{len(companies) * searches_per_company * RATE_LIMIT_DELAY / 60:.0f} minuter")

        response = input("\nFortsätta? (y/n): ")
        if response.lower() != 'y':
            print("Avbryter.")
            return
    else:
        print(f"\n🚀 Startar sökning på {len(companies)} företag...")

    # Sök efter varje företag
    results = []
    for i, (company_id, name, company_type, owner, website) in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}]", end=" ")

        try:
            result = search_company(
                company_id, name, company_type, owner, website
            )
            results.append(result)
        except KeyboardInterrupt:
            print("\n\n⚠️  Avbrutet av användaren")
            break
        except Exception as e:
            print(f"\n❌ Fel vid sökning: {e}")
            # Fortsätt med nästa företag

    # Exportera resultat
    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = args.output or f"orgnr_search_{timestamp}.csv"
        output_path = Path(output_path)

        export_to_csv(results, output_path)

        # Statistik
        found_count = sum(1 for r in results if r.get("suggested_orgnr"))
        print(f"\n📊 Statistik:")
        print(f"   Sökta företag: {len(results)}")
        print(f"   Med förslag på org.nr: {found_count} ({found_count/len(results)*100:.0f}%)")
        print(f"\n💡 Nästa steg:")
        print(f"   1. Öppna {output_path} i Excel/Google Sheets")
        print(f"   2. Granska kolumnen 'suggested_orgnr'")
        print(f"   3. Fyll i 'verified_orgnr' med korrekt org.nr")
        print(f"   4. Använd import-script för att lägga in i databasen")

    print("\n✅ Klart!")


if __name__ == "__main__":
    main()

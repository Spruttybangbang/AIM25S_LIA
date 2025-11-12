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

from duckduckgo_search import DDGS

# ============================================================================
# KONFIGURATION
# ============================================================================

DB_PATH = Path(__file__).parent.parent.parent / "databases" / "ai_companies.db"
RATE_LIMIT_DELAY = 1.5  # Sekunder mellan sökningar
TIMEOUT = 15

# Sökvariabler att använda
SEARCH_TERMS = [
    "organisationsnummer",
    "juridiskt namn",
    "allabolag",
    "bolagsfakta"
]

# ============================================================================
# ORG.NR REGEX
# ============================================================================

def extract_orgnr_candidates(text: str) -> List[str]:
    """
    Hitta alla potentiella org.nr i text

    Format:
    - XXXXXX-XXXX (standard)
    - XXXXXXXXXX (10 siffror)
    - 16XXXXXXXXXX (12 siffror med 16-prefix, juridiska personer)
    """
    if not text:
        return []

    candidates = []

    # Pattern 1: XXXXXX-XXXX
    pattern1 = r'\b(\d{6}-\d{4})\b'
    matches1 = re.findall(pattern1, text)
    candidates.extend(matches1)

    # Pattern 2: 10 siffror i rad (men inte datum eller telefonnummer)
    pattern2 = r'\b(5\d{9})\b'  # Börjar oftast med 5 för aktiebolag
    matches2 = re.findall(pattern2, text)
    # Formatera till XXXXXX-XXXX
    candidates.extend([f"{m[:6]}-{m[6:]}" for m in matches2])

    # Pattern 3: 16XXXXXXXXXX (12 siffror)
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


# ============================================================================
# DUCKDUCKGO SEARCH
# ============================================================================

def duckduckgo_search(query: str) -> Tuple[str, str]:
    """
    Sök på DuckDuckGo och returnera första träffens text

    Returns:
        (url, text)
    """
    try:
        with DDGS() as ddgs:
            # Hämta första 3 resultaten (ger mer kontext)
            results = list(ddgs.text(query, region='se-sv', max_results=3))

            if not results:
                return "", "[Inga resultat hittades]"

            # Sammanställ text från första 3 resultaten
            # (ökar chansen att hitta org.nr)
            combined_text = []
            urls = []

            for result in results:
                title = result.get('title', '')
                body = result.get('body', '')
                url = result.get('href', '')

                combined_text.append(f"{title} {body}")
                if url and url not in urls:
                    urls.append(url)

            text = " ".join(combined_text).strip()
            primary_url = urls[0] if urls else ""

            return primary_url, text

    except Exception as e:
        return "", f"[ERROR: {str(e)}]"


# ============================================================================
# KVALIFICERAD GISSNING
# ============================================================================

def suggest_best_orgnr(
    all_orgnr: List[str],
    company_name: str,
    owner: Optional[str],
    search_results: Dict[str, str]
) -> Tuple[Optional[str], float, str]:
    """
    Gör en kvalificerad gissning på vilket org.nr som är rätt

    Returns:
        (orgnr, confidence_score, reason)
    """
    if not all_orgnr:
        return None, 0.0, "Inga org.nr hittades"

    # Om bara ett org.nr hittades
    if len(all_orgnr) == 1:
        return all_orgnr[0], 0.9, "Endast ett org.nr hittades"

    # Räkna frekvens
    counter = Counter(all_orgnr)
    most_common = counter.most_common(1)[0]
    most_common_orgnr = most_common[0]
    frequency = most_common[1]

    # Om ett org.nr förekommer flera gånger
    if frequency > 1:
        confidence = min(0.95, 0.7 + (frequency * 0.1))
        return most_common_orgnr, confidence, f"Förekommer {frequency} gånger i sökresultaten"

    # Annars: Flera olika org.nr, välj första från "allabolag" eller "bolagsfakta"
    for term in ["allabolag", "bolagsfakta"]:
        result_text = search_results.get(term, "")
        orgnr_in_result = extract_orgnr_candidates(result_text)
        if orgnr_in_result:
            return orgnr_in_result[0], 0.6, f"Första org.nr från {term}-sökning"

    # Fallback: första hittade org.nr
    return all_orgnr[0], 0.5, "Första hittade org.nr (osäker)"


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

    search_results = {}
    all_orgnr = []

    # Sök med varje sökterm
    for i, term in enumerate(SEARCH_TERMS, 1):
        query = f"{name} {term}"

        print(f"   [{i}/4] Söker: '{query}'")

        url, text = duckduckgo_search(query)

        # Spara resultat
        result[f"search_query_{i}"] = query
        result[f"result_url_{i}"] = url
        result[f"result_text_{i}"] = text[:500]  # Begränsa längd för CSV

        search_results[term] = text

        # Extrahera org.nr
        orgnr_found = extract_orgnr_candidates(text)
        result[f"found_orgnr_{i}"] = ", ".join(orgnr_found) if orgnr_found else ""

        all_orgnr.extend(orgnr_found)

        print(f"      → Hittade: {len(orgnr_found)} org.nr")

        # Rate limiting
        if i < len(SEARCH_TERMS):
            time.sleep(RATE_LIMIT_DELAY)

    # Om vi har owner, sök på det också
    if owner and owner.strip():
        query = f"{owner} organisationsnummer"
        print(f"   [5/5] Söker på owner: '{query}'")

        url, text = duckduckgo_search(query)
        result["search_query_owner"] = query
        result["result_url_owner"] = url
        result["result_text_owner"] = text[:500]

        orgnr_found = extract_orgnr_candidates(text)
        result["found_orgnr_owner"] = ", ".join(orgnr_found) if orgnr_found else ""
        all_orgnr.extend(orgnr_found)

        print(f"      → Hittade: {len(orgnr_found)} org.nr")

        time.sleep(RATE_LIMIT_DELAY)

    # Sammanställ alla unika org.nr
    unique_orgnr = list(dict.fromkeys(all_orgnr))  # Behåll ordning
    result["all_found_orgnr"] = ", ".join(unique_orgnr)

    # Gör kvalificerad gissning
    suggested, confidence, reason = suggest_best_orgnr(
        unique_orgnr, name, owner, search_results
    )

    result["suggested_orgnr"] = suggested or ""
    result["confidence_score"] = f"{confidence:.2f}"
    result["suggestion_reason"] = reason
    result["verified_orgnr"] = ""  # Tom för manuell input
    result["notes"] = ""  # Tom för anteckningar

    print(f"   ✅ Resultat: {len(unique_orgnr)} unika org.nr hittades")
    if suggested:
        print(f"   💡 Förslag: {suggested} (confidence: {confidence:.0%})")
        print(f"      Anledning: {reason}")

    return result


def export_to_csv(results: List[Dict], output_path: Path):
    """Exportera resultat till CSV"""
    if not results:
        print("⚠️  Inga resultat att exportera")
        return

    # Definiera kolumnordning
    fieldnames = [
        # Företagsinfo
        "company_id", "company_name", "company_type", "owner", "website",

        # Sökresultat 1: organisationsnummer
        "search_query_1", "result_url_1", "result_text_1", "found_orgnr_1",

        # Sökresultat 2: juridiskt namn
        "search_query_2", "result_url_2", "result_text_2", "found_orgnr_2",

        # Sökresultat 3: allabolag
        "search_query_3", "result_url_3", "result_text_3", "found_orgnr_3",

        # Sökresultat 4: bolagsfakta
        "search_query_4", "result_url_4", "result_text_4", "found_orgnr_4",

        # Owner-sökning (om tillämpligt)
        "search_query_owner", "result_url_owner", "result_text_owner", "found_orgnr_owner",

        # Sammanställning
        "all_found_orgnr",

        # Scriptets gissning
        "suggested_orgnr", "confidence_score", "suggestion_reason",

        # Manuell verifiering
        "verified_orgnr", "notes"
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
        print(f"\n⚠️  Detta kommer göra {len(companies) * 4} sökningar på DuckDuckGo")
        print(f"   Med {RATE_LIMIT_DELAY}s delay = ~{len(companies) * 4 * RATE_LIMIT_DELAY / 60:.0f} minuter")

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

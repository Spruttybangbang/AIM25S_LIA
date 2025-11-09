#!/usr/bin/env python3
"""
Script för att försöka hitta matchningar för företag som inte hade några kandidater.
Använder alternativa söknamn och mer aggressiv fuzzy matching.
"""

import pandas as pd
import sqlite3
import re
from typing import List, Dict, Tuple

def load_no_candidates():
    """Laddar företag utan kandidater"""
    no_candidates_df = pd.read_csv('analysis_no_candidates.csv')

    conn = sqlite3.connect('ai_companies.db')
    companies_df = pd.read_sql_query("""
        SELECT id, name, website, description, location_city
        FROM companies
    """, conn)
    conn.close()

    # Merge
    merged = no_candidates_df.merge(
        companies_df, left_on='id', right_on='id', how='left'
    )

    return merged

def is_likely_foreign(company_name: str, website: str = None) -> Tuple[bool, str]:
    """
    Identifierar om ett företag troligen är utländskt
    Returnerar (True/False, anledning)
    """
    name_lower = company_name.lower()

    # Kända utländska företag
    foreign_companies = [
        'google', 'meta', 'facebook', 'nvidia', 'amd', 'deepmind',
        'microsoft', 'amazon', 'aws', 'openai', 'anthropic',
        'hugging face', 'stability ai', 'openai', 'tesla',
        'intel', 'apple', 'ibm', 'oracle', 'salesforce',
        'spacex', 'x.ai', 'perplexity', 'cohere'
    ]

    for foreign in foreign_companies:
        if foreign in name_lower:
            return True, f"Känt utländskt företag: {foreign}"

    # Internationella organisationer
    intl_orgs = [
        'oecd', 'unesco', 'world economic forum', 'european union',
        'nato', 'un ', 'united nations', 'world bank'
    ]

    for org in intl_orgs:
        if org in name_lower:
            return True, f"Internationell organisation: {org}"

    # Webbadresser som tyder på utländskt
    if website:
        website_lower = website.lower()
        non_swedish_tlds = ['.com', '.io', '.ai', '.org', '.net']
        swedish_indicators = ['.se', 'sweden', 'stockholm', 'göteborg', 'malmö']

        has_non_swedish = any(tld in website_lower for tld in non_swedish_tlds)
        has_swedish = any(ind in website_lower for ind in swedish_indicators)

        if has_non_swedish and not has_swedish:
            return True, "Webbadress tyder på utländskt företag"

    # Namn som innehåller "LLC", "Inc", "Ltd", "GmbH", "Pte", "Corp"
    foreign_suffixes = ['llc', ' inc', ' ltd', ' gmbh', ' pte', ' corp', ' limited']
    for suffix in foreign_suffixes:
        if suffix in name_lower:
            return True, f"Utländsk företagsform: {suffix}"

    return False, ""

def is_likely_non_company(company_name: str) -> Tuple[bool, str]:
    """
    Identifierar om namnet troligen inte är ett företag

    OBS: Vi filtrerar INTE bort organisationer/föreningar längre
    eftersom de kan ha kontor och vara intressanta praktikplatser!
    """
    name_lower = company_name.lower()

    # Endast filtrera bort personer (förnamn + efternamn utan AB eller andra markörer)
    if len(company_name.split()) == 2 and not any(char in company_name for char in ['.', 'AB', 'ab']):
        # Dubbelkolla att det inte innehåller organisation-ord
        org_keywords = ['consulting', 'group', 'tech', 'analytics', 'labs']
        if not any(keyword in name_lower for keyword in org_keywords):
            return True, "Troligen privatperson"

    return False, ""

def generate_search_variants(company_name: str) -> List[str]:
    """
    Genererar alternativa söknamn för ett företag

    Mer aggressiv variant-generering för att öka chansen att hitta företag i SCB.
    """
    variants = [company_name]
    name = company_name.strip()

    # Ta bort AB/Aktiebolag
    if name.endswith(' AB'):
        variants.append(name[:-3].strip())
    if name.endswith(' Aktiebolag'):
        variants.append(name[:-11].strip())
    if ' AB' in name:
        variants.append(name.replace(' AB', '').strip())

    # Lägg till AB om det inte finns
    if not name.endswith(' AB') and not 'AB' in name:
        variants.append(f"{name} AB")
        variants.append(f"{name} Aktiebolag")

    # Ta bort domänändar (.ai, .se, etc.)
    if '.' in name:
        base_name = re.sub(r'\.[a-z]+$', '', name, flags=re.IGNORECASE)
        variants.append(base_name)
        variants.append(f"{base_name} AB")
        variants.append(f"{base_name} Aktiebolag")

    # Ta bort specialtecken
    clean_name = re.sub(r'[^\w\s]', ' ', name)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    if clean_name != name:
        variants.append(clean_name)
        variants.append(f"{clean_name} AB")

    # Ta bort ord inom parentes
    if '(' in name and ')' in name:
        without_parens = re.sub(r'\([^)]*\)', '', name).strip()
        variants.append(without_parens)
        variants.append(f"{without_parens} AB")

    # Konvertera akronymer
    if name.isupper() and len(name) <= 6:
        # T.ex. "CEVT" -> "CEVT AB"
        variants.append(f"{name} AB")
        variants.append(f"{name} Aktiebolag")

    # NYT: Sök på första ordet (för sammansatta namn)
    words = name.split()
    if len(words) >= 2:
        first_word = words[0]
        # Bara om första ordet är tillräckligt långt för att vara meningsfullt
        if len(first_word) >= 4:
            variants.append(first_word)
            variants.append(f"{first_word} AB")
            variants.append(f"{first_word} Aktiebolag")

    # NYT: För namn med bindestreck, prova utan bindestreck
    if '-' in name:
        no_dash = name.replace('-', ' ')
        variants.append(no_dash)
        variants.append(f"{no_dash} AB")
        no_dash_compact = name.replace('-', '')
        variants.append(no_dash_compact)
        variants.append(f"{no_dash_compact} AB")

    # Ta bort dubbletter och returnera
    return list(set([v for v in variants if v and len(v) > 1]))

def categorize_no_candidates(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Kategoriserar företag utan kandidater
    """
    categories = {
        'foreign': [],
        'non_company': [],
        'likely_swedish': [],
        'need_review': []
    }

    for idx, row in df.iterrows():
        name = row['name_x']
        website = row.get('website', None)

        # Kolla om utländskt
        is_foreign, foreign_reason = is_likely_foreign(name, website)
        if is_foreign:
            categories['foreign'].append({
                'id': row['id'],
                'name': name,
                'reason': foreign_reason,
                'website': website
            })
            continue

        # Kolla om inte företag
        is_non_company, non_company_reason = is_likely_non_company(name)
        if is_non_company:
            categories['non_company'].append({
                'id': row['id'],
                'name': name,
                'reason': non_company_reason,
                'website': website
            })
            continue

        # Svenska företag med .se domän eller location_city
        website_lower = str(website).lower() if website else ''
        has_se_domain = '.se' in website_lower
        has_location = pd.notna(row.get('location_city'))

        if has_se_domain or has_location:
            categories['likely_swedish'].append({
                'id': row['id'],
                'name': name,
                'website': website,
                'location_city': row.get('location_city'),
                'search_variants': generate_search_variants(name)
            })
        else:
            categories['need_review'].append({
                'id': row['id'],
                'name': name,
                'website': website,
                'search_variants': generate_search_variants(name)
            })

    return {
        k: pd.DataFrame(v) if v else pd.DataFrame()
        for k, v in categories.items()
    }

def print_summary(categories: Dict[str, pd.DataFrame]):
    """
    Skriver ut sammanfattning
    """
    print("\n" + "="*80)
    print("📊 KATEGORISERING AV FÖRETAG UTAN KANDIDATER")
    print("="*80)

    total = sum(len(df) for df in categories.values())

    print(f"\n🌍 UTLÄNDSKA FÖRETAG: {len(categories['foreign'])} st")
    if len(categories['foreign']) > 0:
        print("   (Dessa behöver troligen inte sökas i SCB)")
        for idx, row in categories['foreign'].head(10).iterrows():
            print(f"   • {row['name']} - {row['reason']}")
        if len(categories['foreign']) > 10:
            print(f"   ... och {len(categories['foreign']) - 10} till")

    print(f"\n🏛️  ORGANISATIONER/ICKE-FÖRETAG: {len(categories['non_company'])} st")
    if len(categories['non_company']) > 0:
        print("   (Stiftelser, föreningar, organisationer)")
        for idx, row in categories['non_company'].head(10).iterrows():
            print(f"   • {row['name']} - {row['reason']}")
        if len(categories['non_company']) > 10:
            print(f"   ... och {len(categories['non_company']) - 10} till")

    print(f"\n🇸🇪 TROLIGA SVENSKA FÖRETAG: {len(categories['likely_swedish'])} st")
    if len(categories['likely_swedish']) > 0:
        print("   (Företag med .se-domän eller location_city)")
        print("   → HÖGSTA PRIORITET för manuell sökning!")

    print(f"\n❓ BEHÖVER GRANSKNING: {len(categories['need_review'])} st")
    if len(categories['need_review']) > 0:
        print("   (Oklara fall som kan vara svenska företag)")

    print(f"\n📈 TOTALT: {total} företag kategoriserade")

def export_categories(categories: Dict[str, pd.DataFrame]):
    """
    Exporterar kategorier till CSV-filer
    """
    print("\n" + "="*80)
    print("💾 EXPORTERAR KATEGORIER")
    print("="*80)

    for category_name, df in categories.items():
        if len(df) > 0:
            filename = f"no_candidates_{category_name}.csv"
            df.to_csv(filename, index=False)
            print(f"✅ {filename} ({len(df)} st)")

    print("\n📋 Rekommenderade nästa steg:")
    print("   1. Fokusera på 'no_candidates_likely_swedish.csv'")
    print("   2. Använd kolumnen 'search_variants' för manuell sökning i SCB")
    print("   3. Granska 'no_candidates_need_review.csv' om tid finns")
    print("   4. Ignorera 'no_candidates_foreign.csv' och 'no_candidates_non_company.csv'")

def create_priority_search_list(categories: Dict[str, pd.DataFrame]):
    """
    Skapar en prioriterad söklista
    """
    priority_list = []

    # Högsta prioritet: Svenska företag
    if len(categories['likely_swedish']) > 0:
        for idx, row in categories['likely_swedish'].iterrows():
            priority_list.append({
                'priority': 1,
                'id': row['id'],
                'name': row['name'],
                'search_variants': ', '.join(row['search_variants'][:3]),
                'reason': 'Har .se-domän eller location'
            })

    # Medel prioritet: Behöver granskning
    if len(categories['need_review']) > 0:
        for idx, row in categories['need_review'].head(50).iterrows():
            priority_list.append({
                'priority': 2,
                'id': row['id'],
                'name': row['name'],
                'search_variants': ', '.join(row['search_variants'][:3]),
                'reason': 'Oklart, kan vara svenskt'
            })

    priority_df = pd.DataFrame(priority_list)
    priority_df.to_csv('no_candidates_priority_search.csv', index=False)

    print("\n✨ PRIORITERAD SÖKLISTA SKAPAD")
    print(f"   Fil: no_candidates_priority_search.csv")
    print(f"   Innehåll: {len(priority_df)} företag att söka efter")
    print(f"   - Prioritet 1: {len(priority_df[priority_df['priority'] == 1])} st")
    print(f"   - Prioritet 2: {len(priority_df[priority_df['priority'] == 2])} st")

def main():
    print("\n" + "="*80)
    print("🔍 ANALYS AV FÖRETAG UTAN KANDIDATER")
    print("="*80)
    print("\nLaddar data...")

    # Ladda data
    df = load_no_candidates()
    print(f"✅ Laddat {len(df)} företag utan kandidater")

    # Kategorisera
    print("\nKategoriserar företag...")
    categories = categorize_no_candidates(df)

    # Visa sammanfattning
    print_summary(categories)

    # Exportera
    export_categories(categories)

    # Skapa prioriterad söklista
    create_priority_search_list(categories)

    print("\n" + "="*80)
    print("✅ KLART!")
    print("="*80)

if __name__ == "__main__":
    main()

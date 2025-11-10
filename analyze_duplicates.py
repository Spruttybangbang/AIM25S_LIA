#!/usr/bin/env python3
"""
Analysera potentiella dubbletter i companies-tabellen.
Letar efter företag som kan vara samma företag men duplicerade.
"""

import sqlite3
import pandas as pd
from difflib import SequenceMatcher
import json

def connect_db():
    return sqlite3.connect('ai_companies.db')

def similarity(a, b):
    """Calculate similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def analyze_duplicates():
    conn = connect_db()

    print("="*80)
    print("DUBBLETTANALYS: SVENSKA AI-FÖRETAG")
    print("="*80)

    # Load data
    companies = pd.read_sql_query("SELECT * FROM companies", conn)
    scb_enrichment = pd.read_sql_query("SELECT company_id, organization_number, scb_company_name FROM scb_enrichment", conn)

    print(f"\nTotalt antal företag: {len(companies)}")
    print(f"Företag med SCB-data: {len(scb_enrichment)}")

    # Merge to see which have SCB
    companies = companies.merge(scb_enrichment, left_on='id', right_on='company_id', how='left')

    duplicates = []

    # 1. Check for exact name matches
    print("\n" + "="*80)
    print("1. EXAKTA NAMNMATCHNINGAR")
    print("="*80)

    name_counts = companies['name'].value_counts()
    exact_duplicates = name_counts[name_counts > 1]

    if len(exact_duplicates) > 0:
        print(f"\n⚠️  Hittade {len(exact_duplicates)} namn som förekommer flera gånger:")
        for name, count in exact_duplicates.items():
            print(f"\n  '{name}' förekommer {count} gånger:")
            dupes = companies[companies['name'] == name]
            for idx, row in dupes.iterrows():
                has_scb = "JA" if pd.notna(row['organization_number']) else "NEJ"
                website = row['website'] if pd.notna(row['website']) else "Ingen"
                print(f"    ID {row['id']:4d}: SCB={has_scb:3s}, Type={row['type']:15s}, Website={website}")
                duplicates.append({
                    'type': 'exact_name',
                    'name': name,
                    'ids': dupes['id'].tolist()
                })
    else:
        print("\n✅ Inga exakta namnmatchningar hittades")

    # 2. Check for same website
    print("\n" + "="*80)
    print("2. SAMMA WEBBSIDA")
    print("="*80)

    companies_with_website = companies[companies['website'].notna() & (companies['website'] != '')]
    website_counts = companies_with_website['website'].value_counts()
    website_duplicates = website_counts[website_counts > 1]

    if len(website_duplicates) > 0:
        print(f"\n⚠️  Hittade {len(website_duplicates)} webbsidor som förekommer flera gånger:")
        for website, count in website_duplicates.items():
            print(f"\n  '{website}' förekommer {count} gånger:")
            dupes = companies[companies['website'] == website]
            for idx, row in dupes.iterrows():
                has_scb = "JA" if pd.notna(row['organization_number']) else "NEJ"
                print(f"    ID {row['id']:4d}: Name='{row['name']}', SCB={has_scb:3s}, Type={row['type']}")
                duplicates.append({
                    'type': 'same_website',
                    'website': website,
                    'ids': dupes['id'].tolist()
                })
    else:
        print("\n✅ Inga webbsidor förekommer flera gånger")

    # 3. Check for same organization number
    print("\n" + "="*80)
    print("3. SAMMA ORGANISATIONSNUMMER")
    print("="*80)

    companies_with_orgnum = companies[companies['organization_number'].notna()]
    orgnum_counts = companies_with_orgnum['organization_number'].value_counts()
    orgnum_duplicates = orgnum_counts[orgnum_counts > 1]

    if len(orgnum_duplicates) > 0:
        print(f"\n⚠️  Hittade {len(orgnum_duplicates)} organisationsnummer som förekommer flera gånger:")
        for orgnum, count in orgnum_duplicates.items():
            print(f"\n  Orgnr '{orgnum}' förekommer {count} gånger:")
            dupes = companies[companies['organization_number'] == orgnum]
            for idx, row in dupes.iterrows():
                print(f"    ID {row['id']:4d}: Name='{row['name']}', Type={row['type']}, Website={row['website']}")
                duplicates.append({
                    'type': 'same_orgnum',
                    'orgnum': orgnum,
                    'ids': dupes['id'].tolist()
                })
    else:
        print("\n✅ Inga organisationsnummer förekommer flera gånger")

    # 4. Check for similar names (fuzzy matching)
    print("\n" + "="*80)
    print("4. LIKNANDE NAMN (FUZZY MATCHING)")
    print("="*80)
    print("\nSöker efter namn med >85% likhet...")

    similar_pairs = []
    threshold = 0.85

    # Only check names, skip if already found as exact duplicate
    unique_names = companies[~companies['name'].isin(exact_duplicates.index)]['name'].unique()

    for i, name1 in enumerate(unique_names):
        for name2 in unique_names[i+1:]:
            sim = similarity(name1, name2)
            if sim >= threshold:
                companies1 = companies[companies['name'] == name1]
                companies2 = companies[companies['name'] == name2]
                similar_pairs.append({
                    'name1': name1,
                    'name2': name2,
                    'similarity': sim,
                    'ids1': companies1['id'].tolist(),
                    'ids2': companies2['id'].tolist()
                })

    if similar_pairs:
        print(f"\n⚠️  Hittade {len(similar_pairs)} par med liknande namn:")
        for pair in sorted(similar_pairs, key=lambda x: x['similarity'], reverse=True)[:20]:  # Show top 20
            print(f"\n  Likhet: {pair['similarity']:.1%}")
            print(f"    '{pair['name1']}' (ID: {pair['ids1']})")
            print(f"    '{pair['name2']}' (ID: {pair['ids2']})")
    else:
        print("\n✅ Inga liknande namn hittades")

    # 5. Companies with and without SCB data (same name pattern)
    print("\n" + "="*80)
    print("5. SAMMA FÖRETAG MED OCH UTAN SCB-DATA?")
    print("="*80)

    # Group by name and check if some have SCB and some don't
    potential_issues = []

    for name in companies['name'].unique():
        name_group = companies[companies['name'] == name]
        if len(name_group) > 1:
            has_scb = name_group['organization_number'].notna().sum()
            no_scb = len(name_group) - has_scb
            if has_scb > 0 and no_scb > 0:
                potential_issues.append({
                    'name': name,
                    'total': len(name_group),
                    'with_scb': has_scb,
                    'without_scb': no_scb,
                    'ids': name_group['id'].tolist()
                })

    if potential_issues:
        print(f"\n⚠️  Hittade {len(potential_issues)} namn där vissa har SCB-data och vissa inte:")
        for issue in potential_issues:
            print(f"\n  '{issue['name']}':")
            print(f"    Med SCB: {issue['with_scb']}, Utan SCB: {issue['without_scb']}")
            print(f"    IDs: {issue['ids']}")
    else:
        print("\n✅ Inga misstänkta fall där samma namn har olika SCB-status")

    # Summary
    print("\n" + "="*80)
    print("SAMMANFATTNING")
    print("="*80)

    total_duplicate_groups = (len(exact_duplicates) + len(website_duplicates) +
                              len(orgnum_duplicates) + len(similar_pairs) + len(potential_issues))

    print(f"\nTotalt antal potentiella dubblettgrupper: {total_duplicate_groups}")
    print(f"  - Exakta namnmatchningar: {len(exact_duplicates)}")
    print(f"  - Samma webbsida: {len(website_duplicates)}")
    print(f"  - Samma organisationsnummer: {len(orgnum_duplicates)}")
    print(f"  - Liknande namn (>85%): {len(similar_pairs)}")
    print(f"  - Samma namn, olika SCB-status: {len(potential_issues)}")

    if total_duplicate_groups > 0:
        print(f"\n⚠️  Totalt antal företag som kan vara dubbletter: [beräknas...]")
        print(f"\n➡️  Använd 'python interactive_deduplication.py' för att granska och åtgärda")
    else:
        print(f"\n✅ Inga dubbletter hittades i databasen!")

    conn.close()

    return {
        'exact_name': exact_duplicates,
        'same_website': website_duplicates,
        'same_orgnum': orgnum_duplicates,
        'similar_names': similar_pairs,
        'mixed_scb': potential_issues
    }

if __name__ == '__main__':
    analyze_duplicates()

#!/usr/bin/env python3
"""
Detailed pattern analysis for missing data by company type and SCB matches.
"""

import sqlite3
import pandas as pd
import numpy as np

def connect_db(db_path='ai_companies.db'):
    """Connect to the database."""
    return sqlite3.connect(db_path)

def analyze_patterns_by_type(conn):
    """Analyze missing data patterns by company type."""
    print(f"\n{'='*80}")
    print("FÖRDJUPAD ANALYS: SAKNAD DATA PER FÖRETAGSTYP")
    print(f"{'='*80}")

    # Load companies
    companies = pd.read_sql_query("SELECT * FROM companies", conn)

    # Analyze by type
    types = companies['type'].unique()

    print(f"\nFördelning av företag per typ:")
    type_counts = companies['type'].value_counts()
    for typ, count in type_counts.items():
        pct = (count / len(companies) * 100)
        print(f"  {typ}: {count:,} ({pct:.1f}%)")

    # Key fields to analyze
    key_fields = ['website', 'description', 'logo_url', 'location_city',
                  'owner', 'maturity', 'accepts_interns']

    print(f"\n{'-'*80}")
    print("SAKNAD DATA PER FÖRETAGSTYP OCH KOLUMN:")
    print(f"{'-'*80}")

    for field in key_fields:
        print(f"\n{field.upper()}:")
        for typ in types:
            type_companies = companies[companies['type'] == typ]
            missing = type_companies[field].isna().sum()
            total = len(type_companies)
            pct = (missing / total * 100) if total > 0 else 0
            print(f"  {typ:20s}: {missing:4d}/{total:4d} ({pct:5.1f}%) saknas")

    # Companies with/without websites by type
    print(f"\n{'-'*80}")
    print("WEBBSIDA-TÄCKNING PER FÖRETAGSTYP:")
    print(f"{'-'*80}")

    for typ in types:
        type_companies = companies[companies['type'] == typ]
        has_website = type_companies['website'].notna().sum()
        total = len(type_companies)
        pct = (has_website / total * 100) if total > 0 else 0
        print(f"  {typ:20s}: {has_website:4d}/{total:4d} ({pct:5.1f}%) har webbsida")

def analyze_scb_matches(conn):
    """Analyze SCB matches table in detail."""
    import json

    print(f"\n{'='*80}")
    print("FÖRDJUPAD ANALYS: SCB MATCHES (ORGANISATIONSNUMMER)")
    print(f"{'='*80}")

    scb = pd.read_sql_query("SELECT * FROM scb_matches", conn)
    companies = pd.read_sql_query("SELECT id, name, type, website FROM companies", conn)

    print(f"\nAntal företag med SCB-matchning: {len(scb):,}")
    print(f"Antal totala företag: {len(companies):,}")
    print(f"Täckningsgrad: {len(scb)/len(companies)*100:.1f}%")

    # Parse JSON payload to extract organization numbers
    def extract_orgnum(payload):
        if pd.isna(payload):
            return None
        try:
            data = json.loads(payload)
            return data.get('organizationNumber', data.get('orgnr', None))
        except:
            return None

    scb['organization_number'] = scb['payload'].apply(extract_orgnum)

    # Merge to see which companies have org numbers
    companies_with_orgnum = companies.merge(scb[['company_id', 'organization_number', 'matched']],
                                             left_on='id', right_on='company_id', how='left')

    print(f"\n{'-'*80}")
    print("SCB-MATCHNING PER FÖRETAGSTYP:")
    print(f"{'-'*80}")

    for typ in sorted(companies['type'].unique()):
        type_companies = companies_with_orgnum[companies_with_orgnum['type'] == typ]
        has_match = type_companies['matched'].notna().sum()
        total = len(type_companies)
        pct = (has_match / total * 100) if total > 0 else 0
        print(f"  {typ:20s}: {has_match:4d}/{total:4d} ({pct:5.1f}%) har SCB-matchning")

    # Analyze completeness of SCB data
    print(f"\n{'-'*80}")
    print("KOMPLETTERING AV SCB-DATA (för företag med SCB-matchning):")
    print(f"{'-'*80}")

    # Parse payload to extract key fields
    def extract_field(payload, field):
        if pd.isna(payload):
            return None
        try:
            data = json.loads(payload)
            return data.get(field, None)
        except:
            return None

    # Extract common fields from payload
    scb['company_name'] = scb['payload'].apply(lambda x: extract_field(x, 'name'))
    scb['status'] = scb['payload'].apply(lambda x: extract_field(x, 'status'))

    scb_info_fields = ['matched', 'score', 'city', 'organization_number', 'company_name', 'status']
    for field in scb_info_fields:
        if field in scb.columns:
            missing = scb[field].isna().sum()
            total = len(scb)
            pct = (missing / total * 100) if total > 0 else 0
            filled = total - missing
            print(f"  {field:30s}: {filled:4d}/{total:4d} ifyllda ({100-pct:5.1f}%)")

    # Companies without SCB matches - what types are they?
    print(f"\n{'-'*80}")
    print("FÖRETAG UTAN SCB-MATCHNING:")
    print(f"{'-'*80}")

    without_match = companies_with_orgnum[companies_with_orgnum['matched'].isna()]
    print(f"\nTotalt antal utan SCB-matchning: {len(without_match):,}")

    print(f"\nFördelning per typ:")
    type_counts = without_match['type'].value_counts()
    for typ, count in type_counts.items():
        pct = (count / len(without_match) * 100)
        print(f"  {typ}: {count:,} ({pct:.1f}%)")

    print(f"\nExempel på företag utan SCB-matchning (10 slumpmässiga):")
    sample = without_match.sample(min(10, len(without_match)))
    for _, row in sample.iterrows():
        website_str = f", {row['website']}" if pd.notna(row['website']) else ""
        print(f"  - {row['name']} (typ: {row['type']}{website_str})")

def cross_reference_analysis(conn):
    """Cross-reference data availability across tables."""
    print(f"\n{'='*80}")
    print("KORSREFERENS-ANALYS: DATA ÖVER FLERA TABELLER")
    print(f"{'='*80}")

    # Load all relevant data
    companies = pd.read_sql_query("SELECT * FROM companies", conn)
    scb = pd.read_sql_query("SELECT * FROM scb_matches", conn)
    company_sectors = pd.read_sql_query("SELECT * FROM company_sectors", conn)
    company_domains = pd.read_sql_query("SELECT * FROM company_domains", conn)
    company_ai = pd.read_sql_query("SELECT * FROM company_ai_capabilities", conn)
    company_dimensions = pd.read_sql_query("SELECT * FROM company_dimensions", conn)

    # Count relationships per company
    sector_counts = company_sectors.groupby('company_id').size()
    domain_counts = company_domains.groupby('company_id').size()
    ai_counts = company_ai.groupby('company_id').size()
    dimension_counts = company_dimensions.groupby('company_id').size()

    print(f"\nAntal företag med data i respektive tabell:")
    print(f"  Företag totalt: {len(companies):,}")
    print(f"  Med SCB-matchning: {len(scb):,}")
    print(f"  Med sektorer: {len(sector_counts):,}")
    print(f"  Med domains: {len(domain_counts):,}")
    print(f"  Med AI capabilities: {len(ai_counts):,}")
    print(f"  Med dimensions: {len(dimension_counts):,}")

    # Companies with no additional data
    companies_with_scb = set(scb['company_id'].unique())
    companies_with_sectors = set(company_sectors['company_id'].unique())
    companies_with_domains = set(company_domains['company_id'].unique())
    companies_with_ai = set(company_ai['company_id'].unique())
    companies_with_dimensions = set(company_dimensions['company_id'].unique())

    all_company_ids = set(companies['id'].unique())

    # Companies with no enrichment data at all
    no_enrichment = all_company_ids - (companies_with_scb | companies_with_sectors |
                                       companies_with_domains | companies_with_ai |
                                       companies_with_dimensions)

    print(f"\n{'-'*80}")
    print(f"Företag UTAN någon berikningsdata: {len(no_enrichment):,}")

    if no_enrichment:
        no_enrich_companies = companies[companies['id'].isin(no_enrichment)]
        print(f"\nFördelning per typ:")
        type_counts = no_enrich_companies['type'].value_counts()
        for typ, count in type_counts.items():
            pct = (count / len(no_enrich_companies) * 100)
            print(f"  {typ}: {count:,} ({pct:.1f}%)")

        print(f"\nExempel (10 första):")
        for _, row in no_enrich_companies.head(10).iterrows():
            print(f"  - {row['name']} (typ: {row['type']})")

    # Companies with all types of enrichment
    all_enrichment = (companies_with_scb & companies_with_sectors &
                      companies_with_domains & companies_with_ai &
                      companies_with_dimensions)

    print(f"\n{'-'*80}")
    print(f"Företag MED all berikningsdata: {len(all_enrichment):,}")

    # Distribution of enrichment levels
    print(f"\n{'-'*80}")
    print("FÖRDELNING AV BERIKNINGSNIVÅ:")
    print(f"{'-'*80}")

    enrichment_levels = []
    for company_id in all_company_ids:
        level = 0
        if company_id in companies_with_scb:
            level += 1
        if company_id in companies_with_sectors:
            level += 1
        if company_id in companies_with_domains:
            level += 1
        if company_id in companies_with_ai:
            level += 1
        if company_id in companies_with_dimensions:
            level += 1
        enrichment_levels.append(level)

    enrichment_df = pd.DataFrame({
        'company_id': list(all_company_ids),
        'enrichment_level': enrichment_levels
    })

    level_counts = enrichment_df['enrichment_level'].value_counts().sort_index()
    for level, count in level_counts.items():
        pct = (count / len(enrichment_df) * 100)
        print(f"  Nivå {level}/5: {count:,} företag ({pct:.1f}%)")

def main():
    """Main function."""
    conn = connect_db()

    analyze_patterns_by_type(conn)
    analyze_scb_matches(conn)
    cross_reference_analysis(conn)

    conn.close()

    print(f"\n{'#'*80}")
    print("# FÖRDJUPAD ANALYS SLUTFÖRD")
    print(f"{'#'*80}\n")

if __name__ == '__main__':
    main()

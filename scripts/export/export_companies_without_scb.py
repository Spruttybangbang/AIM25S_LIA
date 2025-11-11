#!/usr/bin/env python3
"""
Exportera alla företag UTAN SCB-data till CSV.
Varje företag = en rad, all tillgänglig data i respektive kolumner.
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os

def connect_db():
    # Path relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, '..', '..')
    db_path = os.path.join(project_root, 'databases', 'ai_companies.db')
    return sqlite3.connect(db_path)

def export_companies_without_scb():
    """Export all companies without SCB data to CSV."""
    conn = connect_db()

    print("="*80)
    print("EXPORT: FÖRETAG UTAN SCB-DATA")
    print("="*80)

    # Get all companies
    companies = pd.read_sql_query("SELECT * FROM companies", conn)

    # Get companies with SCB
    scb_companies = pd.read_sql_query("SELECT DISTINCT company_id FROM scb_enrichment", conn)
    scb_company_ids = set(scb_companies['company_id'].values)

    # Filter to only those WITHOUT SCB
    companies_without_scb = companies[~companies['id'].isin(scb_company_ids)].copy()

    print(f"\nAntal företag utan SCB-data: {len(companies_without_scb)}")
    print(f"Kolumner från companies-tabellen: {len(companies_without_scb.columns)}")

    # Add related data from other tables
    print("\nHämtar relaterad data från andra tabeller...")

    # Get sectors for each company
    print("  - Sektorer...")
    sectors_query = """
        SELECT cs.company_id, GROUP_CONCAT(s.name, '; ') as sectors
        FROM company_sectors cs
        JOIN sectors s ON cs.sector_id = s.id
        GROUP BY cs.company_id
    """
    sectors_df = pd.read_sql_query(sectors_query, conn)
    companies_without_scb = companies_without_scb.merge(sectors_df, left_on='id', right_on='company_id', how='left')
    companies_without_scb.drop('company_id', axis=1, inplace=True)

    # Get domains
    print("  - Domains...")
    domains_query = """
        SELECT cd.company_id, GROUP_CONCAT(d.name, '; ') as domains
        FROM company_domains cd
        JOIN domains d ON cd.domain_id = d.id
        GROUP BY cd.company_id
    """
    domains_df = pd.read_sql_query(domains_query, conn)
    companies_without_scb = companies_without_scb.merge(domains_df, left_on='id', right_on='company_id', how='left')
    companies_without_scb.drop('company_id', axis=1, inplace=True)

    # Get AI capabilities
    print("  - AI Capabilities...")
    ai_cap_query = """
        SELECT cac.company_id, GROUP_CONCAT(ac.name, '; ') as ai_capabilities
        FROM company_ai_capabilities cac
        JOIN ai_capabilities ac ON cac.capability_id = ac.id
        GROUP BY cac.company_id
    """
    ai_cap_df = pd.read_sql_query(ai_cap_query, conn)
    companies_without_scb = companies_without_scb.merge(ai_cap_df, left_on='id', right_on='company_id', how='left')
    companies_without_scb.drop('company_id', axis=1, inplace=True)

    # Get dimensions
    print("  - Dimensions...")
    dimensions_query = """
        SELECT cd.company_id, GROUP_CONCAT(d.name, '; ') as dimensions
        FROM company_dimensions cd
        JOIN dimensions d ON cd.dimension_id = d.id
        GROUP BY cd.company_id
    """
    dimensions_df = pd.read_sql_query(dimensions_query, conn)
    companies_without_scb = companies_without_scb.merge(dimensions_df, left_on='id', right_on='company_id', how='left')
    companies_without_scb.drop('company_id', axis=1, inplace=True)

    # Reorder columns for better readability
    column_order = [
        'id',
        'name',
        'type',
        'website',
        'description',
        'location_city',
        'location_country',
        'location_greater_stockholm',
        'logo_url',
        'owner',
        'maturity',
        'accepts_interns',
        'is_swedish',
        'source',
        'metadata_source_url',
        'data_quality_score',
        'last_updated',
        'sectors',
        'domains',
        'ai_capabilities',
        'dimensions'
    ]

    # Make sure all columns exist
    for col in column_order:
        if col not in companies_without_scb.columns:
            companies_without_scb[col] = None

    companies_without_scb = companies_without_scb[column_order]

    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'companies_without_scb_{timestamp}.csv'

    # Export to CSV
    companies_without_scb.to_csv(filename, index=False, encoding='utf-8-sig')

    print(f"\n✅ Export slutförd!")
    print(f"📄 Fil: {filename}")
    print(f"📊 Antal rader: {len(companies_without_scb)}")
    print(f"📊 Antal kolumner: {len(companies_without_scb.columns)}")

    # Show statistics
    print(f"\n{'='*80}")
    print("STATISTIK")
    print("="*80)

    print(f"\nFördelning per företagstyp:")
    type_counts = companies_without_scb['type'].value_counts()
    for typ, count in type_counts.items():
        pct = (count / len(companies_without_scb) * 100)
        print(f"  {typ:20s}: {count:4d} ({pct:5.1f}%)")

    print(f"\nData-täckning:")
    print(f"  Med webbsida: {companies_without_scb['website'].notna().sum()} ({companies_without_scb['website'].notna().sum()/len(companies_without_scb)*100:.1f}%)")
    print(f"  Med beskrivning: {companies_without_scb['description'].notna().sum()} ({companies_without_scb['description'].notna().sum()/len(companies_without_scb)*100:.1f}%)")
    print(f"  Med stad: {companies_without_scb['location_city'].notna().sum()} ({companies_without_scb['location_city'].notna().sum()/len(companies_without_scb)*100:.1f}%)")
    print(f"  Med sektorer: {companies_without_scb['sectors'].notna().sum()} ({companies_without_scb['sectors'].notna().sum()/len(companies_without_scb)*100:.1f}%)")
    print(f"  Med domains: {companies_without_scb['domains'].notna().sum()} ({companies_without_scb['domains'].notna().sum()/len(companies_without_scb)*100:.1f}%)")
    print(f"  Med AI capabilities: {companies_without_scb['ai_capabilities'].notna().sum()} ({companies_without_scb['ai_capabilities'].notna().sum()/len(companies_without_scb)*100:.1f}%)")
    print(f"  Med dimensions: {companies_without_scb['dimensions'].notna().sum()} ({companies_without_scb['dimensions'].notna().sum()/len(companies_without_scb)*100:.1f}%)")

    # Show sample
    print(f"\n{'='*80}")
    print("EXEMPEL (5 första raderna):")
    print("="*80)
    print("\nKolumner:")
    for i, col in enumerate(companies_without_scb.columns, 1):
        print(f"  {i:2d}. {col}")

    print(f"\nSample data (5 första företagen):")
    sample = companies_without_scb.head(5)
    for idx, row in sample.iterrows():
        print(f"\n{'-'*80}")
        print(f"ID: {row['id']} - {row['name']} ({row['type']})")
        print(f"  Website: {row['website'] if pd.notna(row['website']) else 'Saknas'}")
        print(f"  Stad: {row['location_city'] if pd.notna(row['location_city']) else 'Saknas'}")
        print(f"  Beskrivning: {row['description'][:100] + '...' if pd.notna(row['description']) and len(str(row['description'])) > 100 else row['description'] if pd.notna(row['description']) else 'Saknas'}")
        print(f"  Sektorer: {row['sectors'] if pd.notna(row['sectors']) else 'Inga'}")
        print(f"  Domains: {row['domains'] if pd.notna(row['domains']) else 'Inga'}")

    conn.close()

    print(f"\n{'='*80}")
    print(f"✅ CSV-fil skapad: {filename}")
    print("="*80)
    print(f"\nFilen innehåller alla {len(companies_without_scb)} företag utan SCB-data.")
    print(f"Varje rad = ett företag, varje kolumn = ett datafält.")
    print(f"\nRelationer (sectors, domains, etc.) är separerade med '; '")
    print(f"Exempel: 'Technology; AI; Software Development'")

    return filename

if __name__ == '__main__':
    export_companies_without_scb()

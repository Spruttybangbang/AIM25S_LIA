#!/usr/bin/env python3
"""
Exportera alla företag från ai_companies.db till en komplett CSV-fil.
Inkluderar all grunddata, SCB-berikning (där tillgänglig) och relationer.
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os

def connect_db():
    """Connect to ai_companies.db"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, '..', '..')
    db_path = os.path.join(project_root, 'databases', 'ai_companies.db')
    return sqlite3.connect(db_path)

def get_relational_data(conn):
    """Get all relational data from junction tables."""
    # Sectors
    sectors_query = """
        SELECT cs.company_id, GROUP_CONCAT(s.name, '; ') as sectors
        FROM company_sectors cs
        JOIN sectors s ON cs.sector_id = s.id
        GROUP BY cs.company_id
    """
    sectors_df = pd.read_sql_query(sectors_query, conn)

    # Domains
    domains_query = """
        SELECT cd.company_id, GROUP_CONCAT(d.name, '; ') as domains
        FROM company_domains cd
        JOIN domains d ON cd.domain_id = d.id
        GROUP BY cd.company_id
    """
    domains_df = pd.read_sql_query(domains_query, conn)

    # AI Capabilities
    ai_cap_query = """
        SELECT cac.company_id, GROUP_CONCAT(ac.name, '; ') as ai_capabilities
        FROM company_ai_capabilities cac
        JOIN ai_capabilities ac ON cac.capability_id = ac.id
        GROUP BY cac.company_id
    """
    ai_cap_df = pd.read_sql_query(ai_cap_query, conn)

    # Dimensions
    dimensions_query = """
        SELECT cd.company_id, GROUP_CONCAT(d.name, '; ') as dimensions
        FROM company_dimensions cd
        JOIN dimensions d ON cd.dimension_id = d.id
        GROUP BY cd.company_id
    """
    dimensions_df = pd.read_sql_query(dimensions_query, conn)

    return {
        'sectors': sectors_df,
        'domains': domains_df,
        'ai_capabilities': ai_cap_df,
        'dimensions': dimensions_df
    }

def add_relational_data(df, relational_data):
    """Add relational data to dataframe."""
    # Sectors
    df = df.merge(relational_data['sectors'], left_on='id', right_on='company_id', how='left')
    if 'company_id' in df.columns:
        df.drop('company_id', axis=1, inplace=True)

    # Domains
    df = df.merge(relational_data['domains'], left_on='id', right_on='company_id', how='left')
    if 'company_id' in df.columns:
        df.drop('company_id', axis=1, inplace=True)

    # AI Capabilities
    df = df.merge(relational_data['ai_capabilities'], left_on='id', right_on='company_id', how='left')
    if 'company_id' in df.columns:
        df.drop('company_id', axis=1, inplace=True)

    # Dimensions
    df = df.merge(relational_data['dimensions'], left_on='id', right_on='company_id', how='left')
    if 'company_id' in df.columns:
        df.drop('company_id', axis=1, inplace=True)

    return df

def export_all_companies(conn, relational_data, output_path):
    """Export ALL companies (with and without SCB, SCB data where available)."""
    print("\n" + "="*80)
    print("EXPORTERAR ALLA FÖRETAG")
    print("="*80)

    # Get all companies
    companies = pd.read_sql_query("SELECT * FROM companies", conn)

    # Get SCB enrichment data
    scb_enrichment = pd.read_sql_query("SELECT * FROM scb_enrichment", conn)

    # Left join to include all companies
    df = companies.merge(scb_enrichment, left_on='id', right_on='company_id', how='left')

    # Drop duplicate id column from scb_enrichment
    if 'id_y' in df.columns:
        df.drop('id_y', axis=1, inplace=True)
        df.rename(columns={'id_x': 'id'}, inplace=True)

    # Drop company_id (redundant with id)
    if 'company_id' in df.columns:
        df.drop('company_id', axis=1, inplace=True)

    print(f"Antal företag: {len(df)}")
    scb_count = df['organization_number'].notna().sum()
    print(f"  - Med SCB-berikning: {scb_count} ({scb_count/len(df)*100:.1f}%)")
    print(f"  - Utan SCB-berikning: {len(df) - scb_count} ({(len(df)-scb_count)/len(df)*100:.1f}%)")

    # Add relational data
    df = add_relational_data(df, relational_data)

    # Add has_scb indicator column
    df['has_scb_enrichment'] = df['organization_number'].notna().astype(int)

    # Column order - companies fields first, then SCB fields, then relations
    column_order = [
        # Companies table
        'id', 'name', 'type', 'website', 'description',
        'location_city', 'location_country', 'location_greater_stockholm',
        'logo_url', 'owner', 'maturity', 'accepts_interns',
        'is_swedish', 'source', 'metadata_source_url',
        'data_quality_score', 'last_updated',
        # SCB indicator
        'has_scb_enrichment',
        # SCB enrichment (will be null for companies without SCB)
        'organization_number', 'scb_company_name',
        'co_address', 'post_address', 'post_code', 'post_city',
        'municipality_code', 'municipality', 'county_code', 'county',
        'num_workplaces', 'employee_size_code', 'employee_size',
        'company_status_code', 'company_status',
        'legal_form_code', 'legal_form',
        'start_date', 'registration_date',
        'industry_1_code', 'industry_1', 'industry_2_code', 'industry_2',
        'revenue_year', 'revenue_size_code', 'revenue_size',
        'phone', 'email',
        'employer_status_code', 'employer_status',
        'vat_status_code', 'vat_status',
        'export_import',
        # Relations
        'sectors', 'domains', 'ai_capabilities', 'dimensions'
    ]

    # Ensure all columns exist
    for col in column_order:
        if col not in df.columns:
            df[col] = None

    df = df[column_order]

    # Export
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"\n✅ Exporterad: {output_path}")
    print(f"   Rader: {len(df):,}, Kolumner: {len(df.columns)}")

    # Get file size
    file_size = os.path.getsize(output_path)
    if file_size > 1024*1024:
        print(f"   Storlek: {file_size/(1024*1024):.1f} MB")
    else:
        print(f"   Storlek: {file_size/1024:.1f} KB")

    print(f"\n📋 Innehåll:")
    print(f"   - Grunddata: 17 kolumner från companies-tabellen")
    print(f"   - SCB-indikator: has_scb_enrichment (1=med, 0=utan)")
    print(f"   - SCB-data: 33 kolumner (tomma för företag utan berikning)")
    print(f"   - Relationer: 4 kolumner (sectors, domains, ai_capabilities, dimensions)")

    print("\n" + "="*80)

    return df

def main():
    """Main export function."""
    print("="*80)
    print("EXPORT: SVENSKA AI-FÖRETAG TILL CSV")
    print("="*80)

    conn = connect_db()

    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Determine output path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, '..', '..')
    exports_dir = os.path.join(project_root, 'exports')

    # Create exports directory if it doesn't exist
    os.makedirs(exports_dir, exist_ok=True)

    output_path = os.path.join(exports_dir, f'ai_companies_{timestamp}.csv')

    # Get relational data
    print("\n📊 Hämtar relationsdata...")
    relational_data = get_relational_data(conn)

    # Export all companies
    df = export_all_companies(conn, relational_data, output_path)

    conn.close()

    print("\n✅ Export slutförd!\n")

if __name__ == '__main__':
    main()

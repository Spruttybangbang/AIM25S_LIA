#!/usr/bin/env python3
"""
Exportera företag till CSV baserat på SCB-berikningsstatus.
Skapar 3 filer:
1. Företag UTAN SCB-berikning
2. Företag MED SCB-berikning (inkl. all SCB-data)
3. ALLA företag (komplett export)
"""

import sqlite3
import pandas as pd
from datetime import datetime

def connect_db():
    return sqlite3.connect('ai_companies.db')

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

def export_companies_without_scb(conn, relational_data, timestamp):
    """Export companies WITHOUT SCB enrichment."""
    print("\n" + "="*80)
    print("1. EXPORTERAR FÖRETAG UTAN SCB-BERIKNING")
    print("="*80)

    # Get all companies
    companies = pd.read_sql_query("SELECT * FROM companies", conn)

    # Get companies with SCB
    scb_companies = pd.read_sql_query("SELECT DISTINCT company_id FROM scb_enrichment", conn)
    scb_company_ids = set(scb_companies['company_id'].values)

    # Filter to only those WITHOUT SCB
    df = companies[~companies['id'].isin(scb_company_ids)].copy()

    print(f"Antal företag: {len(df)}")

    # Add relational data
    df = add_relational_data(df, relational_data)

    # Column order
    column_order = [
        'id', 'name', 'type', 'website', 'description',
        'location_city', 'location_country', 'location_greater_stockholm',
        'logo_url', 'owner', 'maturity', 'accepts_interns',
        'is_swedish', 'source', 'metadata_source_url',
        'data_quality_score', 'last_updated',
        'sectors', 'domains', 'ai_capabilities', 'dimensions'
    ]

    # Ensure all columns exist
    for col in column_order:
        if col not in df.columns:
            df[col] = None

    df = df[column_order]

    # Export
    filename = f'companies_without_scb_{timestamp}.csv'
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    print(f"✅ Exporterad: {filename}")
    print(f"   Rader: {len(df)}, Kolumner: {len(df.columns)}")

    return filename, df

def export_companies_with_scb(conn, relational_data, timestamp):
    """Export companies WITH SCB enrichment (including all SCB data)."""
    print("\n" + "="*80)
    print("2. EXPORTERAR FÖRETAG MED SCB-BERIKNING")
    print("="*80)

    # Get all companies
    companies = pd.read_sql_query("SELECT * FROM companies", conn)

    # Get SCB enrichment data
    scb_enrichment = pd.read_sql_query("SELECT * FROM scb_enrichment", conn)

    # Merge companies with SCB data
    df = companies.merge(scb_enrichment, left_on='id', right_on='company_id', how='inner')

    # Drop duplicate id column from scb_enrichment
    if 'id_y' in df.columns:
        df.drop('id_y', axis=1, inplace=True)
        df.rename(columns={'id_x': 'id'}, inplace=True)

    # Drop company_id (redundant with id)
    if 'company_id' in df.columns:
        df.drop('company_id', axis=1, inplace=True)

    print(f"Antal företag: {len(df)}")

    # Add relational data
    df = add_relational_data(df, relational_data)

    # Column order - companies fields first, then SCB fields, then relations
    column_order = [
        # Companies table
        'id', 'name', 'type', 'website', 'description',
        'location_city', 'location_country', 'location_greater_stockholm',
        'logo_url', 'owner', 'maturity', 'accepts_interns',
        'is_swedish', 'source', 'metadata_source_url',
        'data_quality_score', 'last_updated',
        # SCB enrichment
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
    filename = f'companies_with_scb_{timestamp}.csv'
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    print(f"✅ Exporterad: {filename}")
    print(f"   Rader: {len(df)}, Kolumner: {len(df.columns)}")

    return filename, df

def export_all_companies(conn, relational_data, timestamp):
    """Export ALL companies (with and without SCB, SCB data where available)."""
    print("\n" + "="*80)
    print("3. EXPORTERAR ALLA FÖRETAG (KOMPLETT)")
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
    print(f"  - Med SCB-berikning: {scb_count}")
    print(f"  - Utan SCB-berikning: {len(df) - scb_count}")

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
    filename = f'companies_all_{timestamp}.csv'
    df.to_csv(filename, index=False, encoding='utf-8-sig')

    print(f"✅ Exporterad: {filename}")
    print(f"   Rader: {len(df)}, Kolumner: {len(df.columns)}")

    return filename, df

def print_summary(without_file, with_file, all_file, df_without, df_with, df_all):
    """Print summary of exports."""
    print("\n" + "="*80)
    print("SAMMANFATTNING AV EXPORT")
    print("="*80)

    print(f"\n📄 3 CSV-filer skapade:")
    print(f"\n1. {without_file}")
    print(f"   Företag UTAN SCB-berikning")
    print(f"   Rader: {len(df_without):,}, Kolumner: {len(df_without.columns)}")

    print(f"\n2. {with_file}")
    print(f"   Företag MED SCB-berikning (inkl. alla SCB-kolumner)")
    print(f"   Rader: {len(df_with):,}, Kolumner: {len(df_with.columns)}")

    print(f"\n3. {all_file}")
    print(f"   ALLA företag (komplett export)")
    print(f"   Rader: {len(df_all):,}, Kolumner: {len(df_all.columns)}")

    print(f"\n📊 Statistik:")
    print(f"   Totalt antal företag: {len(df_all):,}")
    print(f"   Med SCB: {len(df_with):,} ({len(df_with)/len(df_all)*100:.1f}%)")
    print(f"   Utan SCB: {len(df_without):,} ({len(df_without)/len(df_all)*100:.1f}%)")

    print(f"\n💡 Kolumnöversikt:")
    print(f"   Företag utan SCB: {len(df_without.columns)} kolumner")
    print(f"     - Grunddata (17) + Relationer (4)")
    print(f"   Företag med SCB: {len(df_with.columns)} kolumner")
    print(f"     - Grunddata (17) + SCB-data (33) + Relationer (4)")
    print(f"   Alla företag: {len(df_all.columns)} kolumner")
    print(f"     - Grunddata (17) + SCB-indikator (1) + SCB-data (33) + Relationer (4)")
    print(f"     - SCB-kolumner är tomma för företag utan SCB-berikning")

    print(f"\n📋 Användning:")
    print(f"   - Öppna i Excel/Google Sheets för granskning")
    print(f"   - Använd i Python med pandas: df = pd.read_csv('filename.csv')")
    print(f"   - Filtrera i 'companies_all' med kolumnen 'has_scb_enrichment':")
    print(f"     df[df['has_scb_enrichment'] == 1]  # Bara med SCB")
    print(f"     df[df['has_scb_enrichment'] == 0]  # Bara utan SCB")

    print("\n" + "="*80)

def main():
    """Main export function."""
    print("="*80)
    print("EXPORT: SVENSKA AI-FÖRETAG TILL CSV")
    print("="*80)
    print("\nDetta script exporterar 3 CSV-filer:")
    print("  1. Företag UTAN SCB-berikning")
    print("  2. Företag MED SCB-berikning (inkl. all SCB-data)")
    print("  3. ALLA företag (komplett export)")

    conn = connect_db()

    # Generate timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Get relational data (used by all exports)
    print("\n📊 Hämtar relationsdata...")
    relational_data = get_relational_data(conn)

    # Export 1: Without SCB
    without_file, df_without = export_companies_without_scb(conn, relational_data, timestamp)

    # Export 2: With SCB
    with_file, df_with = export_companies_with_scb(conn, relational_data, timestamp)

    # Export 3: All companies
    all_file, df_all = export_all_companies(conn, relational_data, timestamp)

    # Print summary
    print_summary(without_file, with_file, all_file, df_without, df_with, df_all)

    conn.close()

    print("\n✅ Export slutförd!\n")

if __name__ == '__main__':
    main()

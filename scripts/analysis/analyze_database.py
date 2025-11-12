#!/usr/bin/env python3
"""
Comprehensive database analysis script for Swedish AI companies database.
Analyzes data completeness, missing values, and provides enrichment recommendations.
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import json

def connect_db(db_path='ai_companies.db'):
    """Connect to the database."""
    return sqlite3.connect(db_path)

def get_all_tables(conn):
    """Get all table names in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]

def analyze_table(conn, table_name):
    """Analyze a single table comprehensively."""
    print(f"\n{'='*80}")
    print(f"TABELL: {table_name}")
    print(f"{'='*80}")

    # Load the table
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)

    total_rows = len(df)
    total_cols = len(df.columns)

    print(f"\nAntal rader: {total_rows:,}")
    print(f"Antal kolumner: {total_cols}")

    # Column info
    print(f"\n{'-'*80}")
    print("KOLUMNER OCH DATATYPER:")
    print(f"{'-'*80}")
    for col in df.columns:
        dtype = df[col].dtype
        print(f"  {col}: {dtype}")

    # Missing values analysis
    print(f"\n{'-'*80}")
    print("SAKNAD DATA (NaN/NULL):")
    print(f"{'-'*80}")

    missing_data = []
    for col in df.columns:
        null_count = df[col].isna().sum()
        empty_string_count = (df[col] == '').sum() if df[col].dtype == 'object' else 0
        none_count = (df[col].isnull()).sum()

        total_missing = null_count + empty_string_count
        missing_pct = (total_missing / total_rows * 100) if total_rows > 0 else 0

        missing_data.append({
            'kolumn': col,
            'saknade': total_missing,
            'procent': missing_pct,
            'ifyllda': total_rows - total_missing
        })

    missing_df = pd.DataFrame(missing_data).sort_values('procent', ascending=False)

    print(missing_df.to_string(index=False))

    # Top 10 columns with most missing data
    print(f"\n{'-'*80}")
    print("TOPP 10 KOLUMNER MED MEST SAKNAD DATA:")
    print(f"{'-'*80}")
    top_missing = missing_df.head(10)
    for _, row in top_missing.iterrows():
        print(f"  {row['kolumn']}: {row['saknade']:,} ({row['procent']:.1f}%) saknas")

    # Data completeness score per row
    print(f"\n{'-'*80}")
    print("DATAKOMPLETTERING PER RAD:")
    print(f"{'-'*80}")

    # Calculate completeness score for each row
    completeness_scores = []
    for idx, row in df.iterrows():
        non_null = row.notna().sum()
        empty_strings = (row == '').sum() if any(df.dtypes == 'object') else 0
        completeness = ((non_null - empty_strings) / total_cols * 100)
        completeness_scores.append(completeness)

    df['completeness_score'] = completeness_scores

    print(f"Genomsnittlig komplettering: {np.mean(completeness_scores):.1f}%")
    print(f"Median komplettering: {np.median(completeness_scores):.1f}%")
    print(f"Min komplettering: {np.min(completeness_scores):.1f}%")
    print(f"Max komplettering: {np.max(completeness_scores):.1f}%")

    # Distribution of completeness
    print(f"\nFördelning av datakomplettering:")
    bins = [0, 25, 50, 75, 90, 100]
    labels = ['0-25%', '25-50%', '50-75%', '75-90%', '90-100%']
    df['completeness_bin'] = pd.cut(df['completeness_score'], bins=bins, labels=labels, include_lowest=True)
    distribution = df['completeness_bin'].value_counts().sort_index()
    for label, count in distribution.items():
        pct = (count / total_rows * 100)
        print(f"  {label}: {count:,} företag ({pct:.1f}%)")

    # Identify patterns in missing data
    print(f"\n{'-'*80}")
    print("MÖNSTER I SAKNAD DATA:")
    print(f"{'-'*80}")

    # Find rows with lowest completeness
    worst_rows = df.nsmallest(10, 'completeness_score')
    print(f"\n10 företag med lägst datakomplettering:")

    # Determine which identifier columns to show
    id_cols = []
    for col in ['company_name', 'name', 'organization_number', 'orgNr', 'id']:
        if col in df.columns:
            id_cols.append(col)

    if id_cols:
        for _, row in worst_rows.iterrows():
            identifiers = " | ".join([f"{col}: {row[col]}" for col in id_cols if pd.notna(row[col])])
            print(f"  {identifiers} - Komplettering: {row['completeness_score']:.1f}%")

    # Unique values in key columns
    print(f"\n{'-'*80}")
    print("UNIKA VÄRDEN I NYCKELKOLUMNER:")
    print(f"{'-'*80}")

    for col in df.columns[:20]:  # First 20 columns
        unique_count = df[col].nunique()
        if unique_count < 50 and df[col].dtype == 'object':  # Show distribution for categorical columns
            print(f"\n{col}: {unique_count} unika värden")
            value_counts = df[col].value_counts().head(10)
            for val, count in value_counts.items():
                print(f"  {val}: {count:,}")

    return df, missing_df

def generate_recommendations(missing_df, df, table_name):
    """Generate data enrichment recommendations."""
    print(f"\n{'='*80}")
    print(f"REKOMMENDATIONER FÖR DATABERIKNING - {table_name}")
    print(f"{'='*80}")

    print("\n🔵 ENKLA ÅTGÄRDER (Snabba wins):")
    print("-" * 80)

    # Identify columns that could be enriched easily
    easy_enrichment = []

    # Check for organization number - can be used to fetch data from public APIs
    if 'organization_number' in df.columns or 'orgNr' in df.columns:
        org_col = 'organization_number' if 'organization_number' in df.columns else 'orgNr'
        if df[org_col].notna().any():
            print("✓ Organisationsnummer finns - kan användas för att hämta data från:")
            print("  - Bolagsverket API (företagsinformation, styrelse, aktiekapital)")
            print("  - SCB (statistik, branschkoder)")
            print("  - Allabolag.se (offentliga uppgifter)")
            print("  - UC (kreditupplysning, om tillgängligt)")

    # Check for company names - can be used for web scraping
    if 'company_name' in df.columns or 'name' in df.columns:
        name_col = 'company_name' if 'company_name' in df.columns else 'name'
        if df[name_col].notna().any():
            print("\n✓ Företagsnamn finns - kan användas för:")
            print("  - Google/Bing search för webbsida")
            print("  - LinkedIn företagssidor (anställda, beskrivning)")
            print("  - Crunchbase (finansiering, grundare)")
            print("  - Twitter/sociala medier")

    # Check for websites - can be scraped
    website_cols = [col for col in df.columns if 'website' in col.lower() or 'url' in col.lower() or 'web' in col.lower()]
    if website_cols:
        for col in website_cols:
            non_null = df[col].notna().sum()
            if non_null > 0:
                print(f"\n✓ {col} finns ({non_null:,} företag) - kan skrapas för:")
                print("  - Kontaktinformation")
                print("  - Produktbeskrivningar")
                print("  - Teamstorlek")
                print("  - Teknologier som används")

    print("\n\n🟡 MEDELSVÅRA ÅTGÄRDER (Kräver mer arbete):")
    print("-" * 80)

    # Email pattern matching
    email_cols = [col for col in df.columns if 'email' in col.lower() or 'mail' in col.lower()]
    if email_cols:
        print("✓ Email-baserad berikning:")
        print("  - Clearbit/Hunter.io för att hitta fler kontakter")
        print("  - Domänanalys för att hitta företagets webbsida")
        print("  - Email-verifiering för att rensa bort ogiltiga adresser")

    # Geographic data
    geo_cols = [col for col in df.columns if any(geo in col.lower() for geo in ['address', 'city', 'postal', 'location', 'stad', 'ort'])]
    if geo_cols:
        print("\n✓ Geografisk berikning:")
        print("  - Geocoding (lat/long från adresser)")
        print("  - Regionala statistik och demografisk data")
        print("  - Närhet till universitet/tech hubs")
        print("  - Kartvisualisering")

    # Financial data
    financial_cols = [col for col in df.columns if any(fin in col.lower() for fin in ['revenue', 'funding', 'valuation', 'omsättning', 'intäkt'])]
    if financial_cols:
        print("\n✓ Finansiell berikning:")
        print("  - Årsredovisningar från Bolagsverket")
        print("  - Finansieringsinformation från Crunchbase/dealroom")
        print("  - Investerar-nätverk")

    print("\n\n🔴 KOMPLEXA ÅTGÄRDER (Kräver signifikant arbete):")
    print("-" * 80)

    print("✓ AI-baserad analys:")
    print("  - NLP-analys av företagsbeskrivningar för att kategorisera AI-typ")
    print("  - Sentiment-analys av nyhetsartiklar")
    print("  - Automatisk klassificering av bransch/sektor")

    print("\n✓ Nätverksanalys:")
    print("  - Mapping av styrelseledamöter mellan företag")
    print("  - Identifiera partners/kunder genom webbskrapning")
    print("  - LinkedIn-nätverksanalys")

    print("\n✓ Tidsseridata:")
    print("  - Historisk tracking av finansiella metrics")
    print("  - Anställdsutveckling över tid")
    print("  - Produktlanserings-timeline")

    print("\n✓ Konkurrensintelligens:")
    print("  - Produktjämförelser")
    print("  - Marknadspositionering")
    print("  - Teknologistack-analys")

    # Specific recommendations based on missing data
    print("\n\n📊 SPECIFIKA REKOMMENDATIONER BASERAT PÅ SAKNAD DATA:")
    print("-" * 80)

    high_missing = missing_df[missing_df['procent'] > 70]
    if not high_missing.empty:
        print(f"\nKolumner med >70% saknad data (överväg att ta bort eller prioritera berikning):")
        for _, row in high_missing.iterrows():
            print(f"  - {row['kolumn']}: {row['procent']:.1f}% saknas")

    medium_missing = missing_df[(missing_df['procent'] > 30) & (missing_df['procent'] <= 70)]
    if not medium_missing.empty:
        print(f"\nKolumner med 30-70% saknad data (goda kandidater för berikning):")
        for _, row in medium_missing.iterrows():
            print(f"  - {row['kolumn']}: {row['procent']:.1f}% saknas")

def main():
    """Main analysis function."""
    db_path = 'databases/ai_companies.db'

    print(f"\n{'#'*80}")
    print(f"# DATABAS-GENOMLYSNING: SVENSKA AI-FÖRETAG")
    print(f"# Databas: {db_path}")
    print(f"{'#'*80}")

    conn = connect_db(db_path)

    # Get all tables
    tables = get_all_tables(conn)
    print(f"\nTabeller i databasen: {', '.join(tables)}")

    # Analyze each table
    all_results = {}
    for table in tables:
        df, missing_df = analyze_table(conn, table)
        all_results[table] = {'df': df, 'missing_df': missing_df}
        generate_recommendations(missing_df, df, table)

    # Summary across all tables
    print(f"\n\n{'='*80}")
    print("SAMMANFATTNING")
    print(f"{'='*80}")

    for table, results in all_results.items():
        df = results['df']
        missing_df = results['missing_df']
        print(f"\n{table}:")
        print(f"  - Antal företag: {len(df):,}")
        print(f"  - Antal kolumner: {len(df.columns)}")
        print(f"  - Genomsnittlig datakomplettering: {df['completeness_score'].mean():.1f}%")
        print(f"  - Kolumner med >50% saknad data: {len(missing_df[missing_df['procent'] > 50])}")

    conn.close()

    print(f"\n{'#'*80}")
    print("# ANALYS SLUTFÖRD")
    print(f"{'#'*80}\n")

if __name__ == '__main__':
    main()

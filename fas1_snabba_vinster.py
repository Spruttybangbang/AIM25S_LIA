#!/usr/bin/env python3
"""
Fas 1: Snabba vinster för databerikning
Extraherar SCB-data från payload och synkar location_city.

Detta script kan köras DIREKT för att förbättra databasen betydligt.
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime

DB_PATH = 'ai_companies.db'

def connect_db():
    """Connect to database."""
    return sqlite3.connect(DB_PATH)

def backup_database():
    """Create backup before making changes."""
    import shutil
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'ai_companies_backup_{timestamp}.db'
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ Backup skapad: {backup_path}")
    return backup_path

def extract_scb_data(conn):
    """Extract structured data from SCB payload JSON."""
    print("\n" + "="*80)
    print("STEG 1: EXTRAHERA SCB-DATA FRÅN PAYLOAD")
    print("="*80)

    # Get all SCB matches
    query = "SELECT id, company_id, payload FROM scb_matches WHERE payload IS NOT NULL"
    scb_df = pd.read_sql_query(query, conn)

    print(f"\nAntal SCB-matchningar att bearbeta: {len(scb_df)}")

    # Define fields to extract
    scb_fields = {
        'organization_number': 'OrgNr',
        'scb_company_name': 'Företagsnamn',
        'co_address': 'COAdress',
        'post_address': 'PostAdress',
        'post_code': 'PostNr',
        'post_city': 'PostOrt',
        'municipality_code': 'Säteskommun, kod',
        'municipality': 'Säteskommun',
        'county_code': 'Sätesl än, kod',
        'county': 'Sätesl än',
        'num_workplaces': 'Antal arbetsställen',
        'employee_size_code': 'Stkl, kod',
        'employee_size': 'Storleksklass',
        'company_status_code': 'Företagsstatus, kod',
        'company_status': 'Företagsstatus',
        'legal_form_code': 'Juridisk form, kod',
        'legal_form': 'Juridisk form',
        'start_date': 'Startdatum',
        'registration_date': 'Registreringsdatum',
        'industry_1_code': 'Bransch_1, kod',
        'industry_1': 'Bransch_1',
        'industry_2_code': 'Bransch_2, kod',
        'industry_2': 'Bransch_2',
        'revenue_year': 'Omsättning, år',
        'revenue_size_code': 'Stkl, oms, kod',
        'revenue_size': 'Storleksklass, oms',
        'phone': 'Telefon',
        'email': 'E-post',
        'employer_status_code': 'Arbetsgivarstatus, kod',
        'employer_status': 'Arbetsgivarstatus',
        'vat_status_code': 'Momsstatus, kod',
        'vat_status': 'Momsstatus',
        'export_import': 'Export/Importmarkering'
    }

    # Extract data
    extracted_data = []
    for idx, row in scb_df.iterrows():
        try:
            payload_dict = json.loads(row['payload'])
            extracted = {'id': row['id'], 'company_id': row['company_id']}

            for field_name, json_key in scb_fields.items():
                value = payload_dict.get(json_key, '')
                # Clean whitespace
                if isinstance(value, str):
                    value = value.strip()
                    if value == '':
                        value = None
                extracted[field_name] = value

            extracted_data.append(extracted)
        except Exception as e:
            print(f"Varning: Kunde inte parsa payload för ID {row['id']}: {e}")

    extracted_df = pd.DataFrame(extracted_data)

    print(f"\nExtraherade fält: {len(scb_fields)}")
    print(f"Framgångsrikt bearbetade rader: {len(extracted_df)}")

    # Show sample
    print(f"\nExempel på extraherad data (första 3 raderna):")
    sample_fields = ['company_id', 'organization_number', 'scb_company_name',
                     'post_city', 'employee_size', 'industry_1', 'phone', 'email']
    print(extracted_df[sample_fields].head(3).to_string())

    return extracted_df

def create_scb_enrichment_table(conn, extracted_df):
    """Create new table with extracted SCB data."""
    print("\n" + "="*80)
    print("STEG 2: SKAPA NY TABELL FÖR SCB-BERIKNINGSDATA")
    print("="*80)

    # Drop table if exists
    conn.execute("DROP TABLE IF EXISTS scb_enrichment")

    # Create table
    create_table_sql = """
    CREATE TABLE scb_enrichment (
        id INTEGER PRIMARY KEY,
        company_id INTEGER NOT NULL,
        organization_number TEXT,
        scb_company_name TEXT,
        co_address TEXT,
        post_address TEXT,
        post_code TEXT,
        post_city TEXT,
        municipality_code TEXT,
        municipality TEXT,
        county_code TEXT,
        county TEXT,
        num_workplaces TEXT,
        employee_size_code TEXT,
        employee_size TEXT,
        company_status_code TEXT,
        company_status TEXT,
        legal_form_code TEXT,
        legal_form TEXT,
        start_date TEXT,
        registration_date TEXT,
        industry_1_code TEXT,
        industry_1 TEXT,
        industry_2_code TEXT,
        industry_2 TEXT,
        revenue_year TEXT,
        revenue_size_code TEXT,
        revenue_size TEXT,
        phone TEXT,
        email TEXT,
        employer_status_code TEXT,
        employer_status TEXT,
        vat_status_code TEXT,
        vat_status TEXT,
        export_import TEXT,
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )
    """
    conn.execute(create_table_sql)
    conn.commit()

    print("✅ Tabell 'scb_enrichment' skapad")

    # Insert data
    extracted_df.to_sql('scb_enrichment', conn, if_exists='append', index=False)
    print(f"✅ {len(extracted_df)} rader inserterade i 'scb_enrichment'")

    return True

def sync_location_city(conn):
    """Sync location_city from SCB data to companies table."""
    print("\n" + "="*80)
    print("STEG 3: SYNKA LOCATION_CITY FRÅN SCB-DATA")
    print("="*80)

    # Count companies without location_city
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*)
        FROM companies
        WHERE location_city IS NULL OR location_city = ''
    """)
    count_without = cursor.fetchone()[0]
    print(f"\nFöretag utan location_city: {count_without}")

    # Update from SCB enrichment
    update_sql = """
    UPDATE companies
    SET location_city = (
        SELECT post_city
        FROM scb_enrichment
        WHERE scb_enrichment.company_id = companies.id
        AND post_city IS NOT NULL
        AND post_city != ''
    )
    WHERE id IN (
        SELECT company_id
        FROM scb_enrichment
        WHERE post_city IS NOT NULL
        AND post_city != ''
    )
    AND (location_city IS NULL OR location_city = '')
    """

    cursor.execute(update_sql)
    rows_updated = cursor.rowcount
    conn.commit()

    print(f"✅ {rows_updated} företag fick location_city uppdaterad från SCB-data")

    # Count remaining
    cursor.execute("""
        SELECT COUNT(*)
        FROM companies
        WHERE location_city IS NULL OR location_city = ''
    """)
    count_remaining = cursor.fetchone()[0]
    print(f"Företag som fortfarande saknar location_city: {count_remaining}")

    return rows_updated

def analyze_improvements(conn):
    """Analyze improvements after enrichment."""
    print("\n" + "="*80)
    print("STEG 4: ANALYS AV FÖRBÄTTRINGAR")
    print("="*80)

    # Count new data availability
    queries = {
        'Organisationsnummer': "SELECT COUNT(*) FROM scb_enrichment WHERE organization_number IS NOT NULL",
        'Fullständig adress': "SELECT COUNT(*) FROM scb_enrichment WHERE post_address IS NOT NULL AND post_city IS NOT NULL",
        'Telefonnummer': "SELECT COUNT(*) FROM scb_enrichment WHERE phone IS NOT NULL AND phone != ''",
        'E-post': "SELECT COUNT(*) FROM scb_enrichment WHERE email IS NOT NULL AND email != ''",
        'Antal anställda': "SELECT COUNT(*) FROM scb_enrichment WHERE employee_size IS NOT NULL",
        'Bransch': "SELECT COUNT(*) FROM scb_enrichment WHERE industry_1 IS NOT NULL",
        'Omsättning': "SELECT COUNT(*) FROM scb_enrichment WHERE revenue_size IS NOT NULL",
        'Startdatum': "SELECT COUNT(*) FROM scb_enrichment WHERE start_date IS NOT NULL"
    }

    print("\nNy data tillgänglig:")
    for description, query in queries.items():
        cursor = conn.cursor()
        cursor.execute(query)
        count = cursor.fetchone()[0]
        print(f"  {description:25s}: {count:4d} företag")

    # Email and phone stats
    print("\n" + "-"*80)
    print("Kontaktinformation från SCB:")
    print("-"*80)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 ELSE 0 END) as with_phone,
            SUM(CASE WHEN email IS NOT NULL AND email != '' THEN 1 ELSE 0 END) as with_email,
            SUM(CASE WHEN (phone IS NOT NULL AND phone != '') OR (email IS NOT NULL AND email != '') THEN 1 ELSE 0 END) as with_either
        FROM scb_enrichment
    """)
    stats = cursor.fetchone()
    total, with_phone, with_email, with_either = stats

    print(f"Totalt företag i SCB: {total}")
    print(f"Med telefon: {with_phone} ({with_phone/total*100:.1f}%)")
    print(f"Med e-post: {with_email} ({with_email/total*100:.1f}%)")
    print(f"Med minst en kontaktmetod: {with_either} ({with_either/total*100:.1f}%)")

def generate_summary_report(conn, backup_path):
    """Generate summary report."""
    print("\n" + "="*80)
    print("SAMMANFATTNING: FAS 1 GENOMFÖRD")
    print("="*80)

    print(f"\n✅ Backup: {backup_path}")
    print(f"✅ Ny tabell skapad: scb_enrichment")
    print(f"✅ Nya kolumner tillgängliga: 33")
    print(f"✅ location_city synkad från SCB")

    # Count total improvements
    cursor = conn.cursor()

    # Companies with SCB enrichment
    cursor.execute("SELECT COUNT(DISTINCT company_id) FROM scb_enrichment")
    companies_enriched = cursor.fetchone()[0]

    # Companies with location_city
    cursor.execute("SELECT COUNT(*) FROM companies WHERE location_city IS NOT NULL AND location_city != ''")
    with_city = cursor.fetchone()[0]

    # Total companies
    cursor.execute("SELECT COUNT(*) FROM companies")
    total_companies = cursor.fetchone()[0]

    print(f"\n📊 Resultat:")
    print(f"  Totalt företag: {total_companies}")
    print(f"  Företag med SCB-berikning: {companies_enriched} ({companies_enriched/total_companies*100:.1f}%)")
    print(f"  Företag med stad: {with_city} ({with_city/total_companies*100:.1f}%)")

    print(f"\n🎯 Nästa steg:")
    print(f"  - Granska ny data i scb_enrichment-tabellen")
    print(f"  - Fortsätt med Fas 2: Öka SCB-täckning och web scraping")
    print(f"  - Validera kontaktinformation (telefon, e-post)")

    print(f"\n💾 Backup sparad som: {backup_path}")
    print(f"   (Återställ med: mv {backup_path} {DB_PATH})")

def main():
    """Main execution."""
    print("="*80)
    print("FAS 1: SNABBA VINSTER - DATABERIKNING")
    print("="*80)
    print("\nDetta script kommer att:")
    print("1. Skapa backup av databasen")
    print("2. Extrahera SCB-data från JSON-payload")
    print("3. Skapa ny tabell 'scb_enrichment' med strukturerad data")
    print("4. Synka location_city från SCB till companies")
    print("5. Generera sammanfattningsrapport")

    # Confirm
    response = input("\nVill du fortsätta? (ja/nej): ").strip().lower()
    if response not in ['ja', 'j', 'yes', 'y']:
        print("Avbruten.")
        return

    conn = connect_db()

    try:
        # Step 0: Backup
        backup_path = backup_database()

        # Step 1: Extract SCB data
        extracted_df = extract_scb_data(conn)

        # Step 2: Create enrichment table
        create_scb_enrichment_table(conn, extracted_df)

        # Step 3: Sync location_city
        sync_location_city(conn)

        # Step 4: Analyze improvements
        analyze_improvements(conn)

        # Step 5: Summary
        generate_summary_report(conn, backup_path)

        print("\n" + "="*80)
        print("✅ FAS 1 SLUTFÖRD!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ FEL: {e}")
        print(f"Återställ databasen från backup: mv {backup_path} {DB_PATH}")
        raise

    finally:
        conn.close()

if __name__ == '__main__':
    main()

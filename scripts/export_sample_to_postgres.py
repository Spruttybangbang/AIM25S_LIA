#!/usr/bin/env python3
"""
Export 30 sample companies from SQLite to PostgreSQL test database
"""
import sqlite3
import psycopg2
from psycopg2 import sql
import json
import os
import getpass
from datetime import datetime

# SQLite database path
SQLITE_DB = 'databases/ai_companies.db'

# PostgreSQL connection settings
# On Mac with Homebrew, use your system username instead of 'postgres'
# You can override with environment variables
PG_CONFIG = {
    'dbname': os.getenv('PGDATABASE', 'ai_companies_test'),
    'user': os.getenv('PGUSER', getpass.getuser()),
    'password': os.getenv('PGPASSWORD', ''),
    'host': os.getenv('PGHOST', 'localhost'),
    'port': int(os.getenv('PGPORT', '5432'))
}

# Remove password from config if empty (for local trust auth)
if not PG_CONFIG['password']:
    del PG_CONFIG['password']

def get_sample_companies(sqlite_conn, limit=30):
    """Get sample companies from SQLite"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM companies LIMIT {limit}")
    companies = cursor.fetchall()

    # Get column names
    cursor.execute("PRAGMA table_info(companies)")
    columns = [col[1] for col in cursor.fetchall()]

    return [dict(zip(columns, company)) for company in companies]

def get_related_data(sqlite_conn, company_ids):
    """Get all related data for the sample companies"""
    cursor = sqlite_conn.cursor()
    company_ids_str = ','.join(map(str, company_ids))

    related_data = {}

    # Get sectors
    cursor.execute(f"""
        SELECT cs.company_id, s.id, s.name
        FROM company_sectors cs
        JOIN sectors s ON cs.sector_id = s.id
        WHERE cs.company_id IN ({company_ids_str})
    """)
    related_data['sectors'] = cursor.fetchall()

    # Get domains
    cursor.execute(f"""
        SELECT cd.company_id, d.id, d.name
        FROM company_domains cd
        JOIN domains d ON cd.domain_id = d.id
        WHERE cd.company_id IN ({company_ids_str})
    """)
    related_data['domains'] = cursor.fetchall()

    # Get AI capabilities
    cursor.execute(f"""
        SELECT cac.company_id, ac.id, ac.name
        FROM company_ai_capabilities cac
        JOIN ai_capabilities ac ON cac.capability_id = ac.id
        WHERE cac.company_id IN ({company_ids_str})
    """)
    related_data['ai_capabilities'] = cursor.fetchall()

    # Get dimensions
    cursor.execute(f"""
        SELECT cd.company_id, d.id, d.name
        FROM company_dimensions cd
        JOIN dimensions d ON cd.dimension_id = d.id
        WHERE cd.company_id IN ({company_ids_str})
    """)
    related_data['dimensions'] = cursor.fetchall()

    # Get SCB matches
    cursor.execute(f"""
        SELECT * FROM scb_matches
        WHERE company_id IN ({company_ids_str})
    """)
    cursor.execute("PRAGMA table_info(scb_matches)")
    scb_match_cols = [col[1] for col in cursor.fetchall()]
    cursor.execute(f"""
        SELECT * FROM scb_matches
        WHERE company_id IN ({company_ids_str})
    """)
    related_data['scb_matches'] = [dict(zip(scb_match_cols, row)) for row in cursor.fetchall()]

    # Get SCB enrichment
    cursor.execute(f"""
        SELECT * FROM scb_enrichment
        WHERE company_id IN ({company_ids_str})
    """)
    cursor.execute("PRAGMA table_info(scb_enrichment)")
    scb_enrich_cols = [col[1] for col in cursor.fetchall()]
    cursor.execute(f"""
        SELECT * FROM scb_enrichment
        WHERE company_id IN ({company_ids_str})
    """)
    related_data['scb_enrichment'] = [dict(zip(scb_enrich_cols, row)) for row in cursor.fetchall()]

    return related_data

def create_postgres_schema(pg_conn):
    """Create PostgreSQL schema matching SQLite structure"""
    cursor = pg_conn.cursor()

    # Drop existing tables (cascade to drop foreign keys)
    cursor.execute("""
        DROP TABLE IF EXISTS company_dimensions CASCADE;
        DROP TABLE IF EXISTS company_ai_capabilities CASCADE;
        DROP TABLE IF EXISTS company_domains CASCADE;
        DROP TABLE IF EXISTS company_sectors CASCADE;
        DROP TABLE IF EXISTS scb_enrichment CASCADE;
        DROP TABLE IF EXISTS scb_matches CASCADE;
        DROP TABLE IF EXISTS dimensions CASCADE;
        DROP TABLE IF EXISTS ai_capabilities CASCADE;
        DROP TABLE IF EXISTS domains CASCADE;
        DROP TABLE IF EXISTS sectors CASCADE;
        DROP TABLE IF EXISTS companies CASCADE;
    """)

    # Create companies table
    cursor.execute("""
        CREATE TABLE companies (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            website TEXT,
            type TEXT,
            logo_url TEXT,
            description TEXT,
            owner TEXT,
            location_city TEXT,
            location_greater_stockholm BOOLEAN,
            last_updated TIMESTAMP,
            data_quality_score INTEGER,
            source_url TEXT
        )
    """)

    # Create lookup tables
    cursor.execute("""
        CREATE TABLE sectors (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE domains (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE ai_capabilities (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE dimensions (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # Create junction tables
    cursor.execute("""
        CREATE TABLE company_sectors (
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            sector_id INTEGER REFERENCES sectors(id) ON DELETE CASCADE,
            PRIMARY KEY (company_id, sector_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE company_domains (
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            domain_id INTEGER REFERENCES domains(id) ON DELETE CASCADE,
            PRIMARY KEY (company_id, domain_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE company_ai_capabilities (
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            capability_id INTEGER REFERENCES ai_capabilities(id) ON DELETE CASCADE,
            PRIMARY KEY (company_id, capability_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE company_dimensions (
            company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            dimension_id INTEGER REFERENCES dimensions(id) ON DELETE CASCADE,
            PRIMARY KEY (company_id, dimension_id)
        )
    """)

    # Create SCB tables
    cursor.execute("""
        CREATE TABLE scb_matches (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            matched INTEGER NOT NULL,
            score INTEGER,
            city TEXT,
            payload TEXT,
            created_at TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE scb_enrichment (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
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
            export_import TEXT
        )
    """)

    pg_conn.commit()
    print("✓ PostgreSQL schema created")

def insert_companies(pg_conn, companies):
    """Insert companies into PostgreSQL"""
    cursor = pg_conn.cursor()

    # Map old IDs to new IDs
    id_mapping = {}

    for company in companies:
        old_id = company['id']
        cursor.execute("""
            INSERT INTO companies (
                name, website, type, logo_url, description, owner,
                location_city, location_greater_stockholm, last_updated,
                data_quality_score, source_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            company['name'],
            company['website'],
            company['type'],
            company['logo_url'],
            company['description'],
            company['owner'],
            company['location_city'],
            company['location_greater_stockholm'],
            company['last_updated'],
            company['data_quality_score'],
            company['source_url']
        ))
        new_id = cursor.fetchone()[0]
        id_mapping[old_id] = new_id

    pg_conn.commit()
    print(f"✓ Inserted {len(companies)} companies")
    return id_mapping

def insert_related_data(pg_conn, related_data, id_mapping):
    """Insert all related data into PostgreSQL"""
    cursor = pg_conn.cursor()

    # Insert sectors and create mapping
    sector_mapping = {}
    for company_id, sector_id, sector_name in related_data['sectors']:
        if sector_id not in sector_mapping:
            cursor.execute("""
                INSERT INTO sectors (name) VALUES (%s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (sector_name,))
            sector_mapping[sector_id] = cursor.fetchone()[0]

    # Insert company_sectors
    for company_id, sector_id, _ in related_data['sectors']:
        if company_id in id_mapping:
            cursor.execute("""
                INSERT INTO company_sectors (company_id, sector_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (id_mapping[company_id], sector_mapping[sector_id]))

    print(f"✓ Inserted sectors")

    # Insert domains and create mapping
    domain_mapping = {}
    for company_id, domain_id, domain_name in related_data['domains']:
        if domain_id not in domain_mapping:
            cursor.execute("""
                INSERT INTO domains (name) VALUES (%s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (domain_name,))
            domain_mapping[domain_id] = cursor.fetchone()[0]

    # Insert company_domains
    for company_id, domain_id, _ in related_data['domains']:
        if company_id in id_mapping:
            cursor.execute("""
                INSERT INTO company_domains (company_id, domain_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (id_mapping[company_id], domain_mapping[domain_id]))

    print(f"✓ Inserted domains")

    # Insert AI capabilities and create mapping
    capability_mapping = {}
    for company_id, capability_id, capability_name in related_data['ai_capabilities']:
        if capability_id not in capability_mapping:
            cursor.execute("""
                INSERT INTO ai_capabilities (name) VALUES (%s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (capability_name,))
            capability_mapping[capability_id] = cursor.fetchone()[0]

    # Insert company_ai_capabilities
    for company_id, capability_id, _ in related_data['ai_capabilities']:
        if company_id in id_mapping:
            cursor.execute("""
                INSERT INTO company_ai_capabilities (company_id, capability_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (id_mapping[company_id], capability_mapping[capability_id]))

    print(f"✓ Inserted AI capabilities")

    # Insert dimensions and create mapping
    dimension_mapping = {}
    for company_id, dimension_id, dimension_name in related_data['dimensions']:
        if dimension_id not in dimension_mapping:
            cursor.execute("""
                INSERT INTO dimensions (name) VALUES (%s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (dimension_name,))
            dimension_mapping[dimension_id] = cursor.fetchone()[0]

    # Insert company_dimensions
    for company_id, dimension_id, _ in related_data['dimensions']:
        if company_id in id_mapping:
            cursor.execute("""
                INSERT INTO company_dimensions (company_id, dimension_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (id_mapping[company_id], dimension_mapping[dimension_id]))

    print(f"✓ Inserted dimensions")

    # Insert SCB matches
    for match in related_data['scb_matches']:
        if match['company_id'] in id_mapping:
            cursor.execute("""
                INSERT INTO scb_matches (
                    company_id, matched, score, city, payload, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                id_mapping[match['company_id']],
                match['matched'],
                match['score'],
                match['city'],
                match['payload'],
                match['created_at']
            ))

    print(f"✓ Inserted {len(related_data['scb_matches'])} SCB matches")

    # Insert SCB enrichment
    for enrich in related_data['scb_enrichment']:
        if enrich['company_id'] in id_mapping:
            cursor.execute("""
                INSERT INTO scb_enrichment (
                    company_id, organization_number, scb_company_name,
                    co_address, post_address, post_code, post_city,
                    municipality_code, municipality, county_code, county,
                    num_workplaces, employee_size_code, employee_size,
                    company_status_code, company_status, legal_form_code,
                    legal_form, start_date, registration_date,
                    industry_1_code, industry_1, industry_2_code, industry_2,
                    revenue_year, revenue_size_code, revenue_size,
                    phone, email, employer_status_code, employer_status,
                    vat_status_code, vat_status, export_import
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                id_mapping[enrich['company_id']],
                enrich['organization_number'],
                enrich['scb_company_name'],
                enrich['co_address'],
                enrich['post_address'],
                enrich['post_code'],
                enrich['post_city'],
                enrich['municipality_code'],
                enrich['municipality'],
                enrich['county_code'],
                enrich['county'],
                enrich['num_workplaces'],
                enrich['employee_size_code'],
                enrich['employee_size'],
                enrich['company_status_code'],
                enrich['company_status'],
                enrich['legal_form_code'],
                enrich['legal_form'],
                enrich['start_date'],
                enrich['registration_date'],
                enrich['industry_1_code'],
                enrich['industry_1'],
                enrich['industry_2_code'],
                enrich['industry_2'],
                enrich['revenue_year'],
                enrich['revenue_size_code'],
                enrich['revenue_size'],
                enrich['phone'],
                enrich['email'],
                enrich['employer_status_code'],
                enrich['employer_status'],
                enrich['vat_status_code'],
                enrich['vat_status'],
                enrich['export_import']
            ))

    print(f"✓ Inserted {len(related_data['scb_enrichment'])} SCB enrichment records")

    pg_conn.commit()

def main():
    print("Starting migration of 30 sample companies from SQLite to PostgreSQL...\n")

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    print("✓ Connected to SQLite database")

    # Get sample companies
    companies = get_sample_companies(sqlite_conn, 30)
    company_ids = [c['id'] for c in companies]
    print(f"✓ Retrieved {len(companies)} companies")

    # Get related data
    related_data = get_related_data(sqlite_conn, company_ids)
    print("✓ Retrieved related data")

    sqlite_conn.close()

    # Connect to PostgreSQL
    try:
        pg_conn = psycopg2.connect(**PG_CONFIG)
        print("✓ Connected to PostgreSQL database")
    except psycopg2.OperationalError as e:
        print(f"\n✗ Could not connect to PostgreSQL: {e}")
        print("\nPlease ensure:")
        print("1. PostgreSQL is running")
        print("2. Database 'ai_companies_test' exists (or will be created)")
        print("3. User has proper permissions")
        return

    # Create schema
    create_postgres_schema(pg_conn)

    # Insert data
    id_mapping = insert_companies(pg_conn, companies)
    insert_related_data(pg_conn, related_data, id_mapping)

    # Verify
    cursor = pg_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM companies")
    company_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM sectors")
    sector_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM scb_enrichment")
    scb_count = cursor.fetchone()[0]

    print("\n" + "="*50)
    print("Migration complete!")
    print("="*50)
    print(f"Companies: {company_count}")
    print(f"Sectors: {sector_count}")
    print(f"SCB enrichment records: {scb_count}")
    print("\nSample companies migrated to 'ai_companies_test' database")

    pg_conn.close()

if __name__ == '__main__':
    main()

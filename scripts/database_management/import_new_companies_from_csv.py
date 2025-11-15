#!/usr/bin/env python3
"""
Importera nya företag från CSV till ai_companies.db.
Dessa företag har INGET company_id och skapas från grunden.
CSV:n innehåller både grunddata och komplett SCB-berikning.
"""

import sqlite3
import csv
import os
from datetime import datetime

def connect_db():
    """Connect to ai_companies.db"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, '..', '..')
    db_path = os.path.join(project_root, 'databases', 'ai_companies.db')
    return sqlite3.connect(db_path)

def get_current_max_id(conn):
    """Get the highest company_id currently in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM companies")
    result = cursor.fetchone()[0]
    return result if result else 0

def import_companies(csv_path):
    """Import new companies from CSV"""
    conn = connect_db()
    cursor = conn.cursor()

    # Get starting ID
    max_id = get_current_max_id(conn)
    next_id = max_id + 1

    print("="*80)
    print("IMPORT: NYA FÖRETAG FRÅN CSV")
    print("="*80)
    print(f"\nNuvarande max company_id: {max_id}")
    print(f"Nya företag börjar på id: {next_id}\n")

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')

        companies_inserted = 0
        scb_enrichment_inserted = 0
        scb_matches_inserted = 0

        for row in reader:
            company_id = next_id

            # Insert into companies table
            cursor.execute('''
                INSERT INTO companies (
                    id, name, type, website, description,
                    location_city, source_url, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id,
                row['company_name'].strip(),
                row['type'].strip(),
                row['website'].strip() if row['website'] else None,
                row['description'].strip() if row['description'] else None,
                row['post_city'].strip() if row['post_city'] else None,
                'manual_import_2025-11-15',  # source_url
                datetime.now().isoformat()
            ))
            companies_inserted += 1

            # Insert into scb_enrichment if organization_number exists
            if row['organization_number'] and row['organization_number'].strip():
                cursor.execute('''
                    INSERT INTO scb_enrichment (
                        company_id, organization_number, scb_company_name,
                        co_address, post_address, post_code, post_city,
                        municipality_code, municipality, county_code, county,
                        num_workplaces, employee_size_code, employee_size,
                        company_status_code, company_status,
                        legal_form_code, legal_form,
                        start_date, registration_date,
                        industry_1_code, industry_1, industry_2_code, industry_2,
                        revenue_year, revenue_size_code, revenue_size,
                        phone, email,
                        employer_status_code, employer_status,
                        vat_status_code, vat_status,
                        export_import
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_id,
                    row['organization_number'].strip(),
                    row['scb_company_name'].strip() if row['scb_company_name'] else None,
                    row['co_address'].strip() if row['co_address'] else None,
                    row['post_address'].strip() if row['post_address'] else None,
                    row['post_code'].strip() if row['post_code'] else None,
                    row['post_city'].strip() if row['post_city'] else None,
                    row['municipality_code'].strip() if row['municipality_code'] else None,
                    row['municipality'].strip() if row['municipality'] else None,
                    row['county_code'].strip() if row['county_code'] else None,
                    row['county'].strip() if row['county'] else None,
                    row['num_workplaces'].strip() if row['num_workplaces'] else None,
                    row['employee_size_code'].strip() if row['employee_size_code'] else None,
                    row['employee_size'].strip() if row['employee_size'] else None,
                    row['company_status_code'].strip() if row['company_status_code'] else None,
                    row['company_status'].strip() if row['company_status'] else None,
                    row['legal_form_code'].strip() if row['legal_form_code'] else None,
                    row['legal_form'].strip() if row['legal_form'] else None,
                    row['start_date'].strip() if row['start_date'] else None,
                    row['registration_date'].strip() if row['registration_date'] else None,
                    row['industry_1_code'].strip() if row['industry_1_code'] else None,
                    row['industry_1'].strip() if row['industry_1'] else None,
                    row['industry_2_code'].strip() if row['industry_2_code'] else None,
                    row['industry_2'].strip() if row['industry_2'] else None,
                    row['revenue_year'].strip() if row['revenue_year'] else None,
                    row['revenue_size_code'].strip() if row['revenue_size_code'] else None,
                    row['revenue_size'].strip() if row['revenue_size'] else None,
                    row['phone'].strip() if row['phone'] else None,
                    row['email'].strip() if row['email'] else None,
                    row['employer_status_code'].strip() if row['employer_status_code'] else None,
                    row['employer_status'].strip() if row['employer_status'] else None,
                    row['vat_status_code'].strip() if row['vat_status_code'] else None,
                    row['vat_status'].strip() if row['vat_status'] else None,
                    row['export_import'].strip() if row['export_import'] else None
                ))
                scb_enrichment_inserted += 1

                # Insert into scb_matches
                fuzzy_score = int(row['fuzzy_score']) if row['fuzzy_score'] and row['fuzzy_score'].strip() else 100
                cursor.execute('''
                    INSERT INTO scb_matches (
                        company_id, matched, score, city
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    company_id,
                    1,  # matched = True
                    fuzzy_score,
                    row['post_city'].strip() if row['post_city'] else None
                ))
                scb_matches_inserted += 1

            print(f"✓ #{company_id}: {row['company_name'][:60]}")
            next_id += 1

        # Commit all changes
        conn.commit()

        print("\n" + "="*80)
        print("SAMMANFATTNING")
        print("="*80)
        print(f"✅ Företag tillagda i 'companies': {companies_inserted}")
        print(f"✅ SCB-berikningar tillagda i 'scb_enrichment': {scb_enrichment_inserted}")
        print(f"✅ SCB-matchningar tillagda i 'scb_matches': {scb_matches_inserted}")
        print(f"\nNya företag: id {max_id + 1} → {next_id - 1}")

    conn.close()

    return companies_inserted, scb_enrichment_inserted, scb_matches_inserted

def main():
    csv_path = '/tmp/new_input_to_database_final_final.csv'

    if not os.path.exists(csv_path):
        print(f"❌ Fel: CSV-filen finns inte på {csv_path}")
        return

    import_companies(csv_path)
    print("\n✅ Import slutförd!\n")

if __name__ == '__main__':
    main()

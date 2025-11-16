#!/usr/bin/env python3
"""
Example script showing how to query the test database from another project
"""
import psycopg2
import psycopg2.extras
import os
import getpass
import json

# Connection settings
DB_CONFIG = {
    'dbname': os.getenv('PGDATABASE', 'ai_companies_test'),
    'user': os.getenv('PGUSER', getpass.getuser()),
    'host': os.getenv('PGHOST', 'localhost'),
    'port': int(os.getenv('PGPORT', '5432'))
}

def get_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)

def get_all_companies():
    """Get all companies with basic info"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT
            id, name, website, type, location_city,
            location_greater_stockholm, description
        FROM companies
        ORDER BY name
    """)

    companies = cursor.fetchall()
    conn.close()
    return companies

def get_company_with_details(company_id):
    """Get company with all related data"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get company info
    cursor.execute("""
        SELECT * FROM companies WHERE id = %s
    """, (company_id,))
    company = cursor.fetchone()

    if not company:
        conn.close()
        return None

    # Get sectors
    cursor.execute("""
        SELECT s.name
        FROM sectors s
        JOIN company_sectors cs ON s.id = cs.sector_id
        WHERE cs.company_id = %s
    """, (company_id,))
    company['sectors'] = [row['name'] for row in cursor.fetchall()]

    # Get domains
    cursor.execute("""
        SELECT d.name
        FROM domains d
        JOIN company_domains cd ON d.id = cd.domain_id
        WHERE cd.company_id = %s
    """, (company_id,))
    company['domains'] = [row['name'] for row in cursor.fetchall()]

    # Get dimensions
    cursor.execute("""
        SELECT d.name
        FROM dimensions d
        JOIN company_dimensions cd ON d.id = cd.dimension_id
        WHERE cd.company_id = %s
    """, (company_id,))
    company['dimensions'] = [row['name'] for row in cursor.fetchall()]

    # Get SCB enrichment
    cursor.execute("""
        SELECT * FROM scb_enrichment WHERE company_id = %s
    """, (company_id,))
    company['scb_data'] = cursor.fetchone()

    conn.close()
    return company

def search_companies(query):
    """Search companies by name or city"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT
            c.id, c.name, c.website, c.location_city,
            se.employee_size, se.revenue_size
        FROM companies c
        LEFT JOIN scb_enrichment se ON c.id = se.company_id
        WHERE
            c.name ILIKE %s OR
            c.location_city ILIKE %s
        ORDER BY c.name
    """, (f'%{query}%', f'%{query}%'))

    results = cursor.fetchall()
    conn.close()
    return results

def get_companies_by_city(city):
    """Get all companies in a specific city"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT
            c.id, c.name, c.website,
            se.employee_size, se.organization_number
        FROM companies c
        LEFT JOIN scb_enrichment se ON c.id = se.company_id
        WHERE c.location_city = %s
        ORDER BY c.name
    """, (city,))

    results = cursor.fetchall()
    conn.close()
    return results

def get_statistics():
    """Get database statistics"""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    stats = {}

    # Count companies
    cursor.execute("SELECT COUNT(*) as count FROM companies")
    stats['total_companies'] = cursor.fetchone()['count']

    # Count by city
    cursor.execute("""
        SELECT location_city, COUNT(*) as count
        FROM companies
        WHERE location_city IS NOT NULL
        GROUP BY location_city
        ORDER BY count DESC
    """)
    stats['by_city'] = cursor.fetchall()

    # Count sectors
    cursor.execute("SELECT COUNT(*) as count FROM sectors")
    stats['total_sectors'] = cursor.fetchone()['count']

    # Count domains
    cursor.execute("SELECT COUNT(*) as count FROM domains")
    stats['total_domains'] = cursor.fetchone()['count']

    conn.close()
    return stats


if __name__ == '__main__':
    print("=== Test Database Query Examples ===\n")

    # Example 1: Get all companies
    print("1. All companies:")
    companies = get_all_companies()
    for company in companies[:5]:  # Show first 5
        print(f"  - {company['name']} ({company['location_city']})")
    print(f"  ... and {len(companies) - 5} more\n")

    # Example 2: Get company with full details
    print("2. Company details (ID=1):")
    company = get_company_with_details(1)
    if company:
        print(f"  Name: {company['name']}")
        print(f"  Website: {company['website']}")
        print(f"  Sectors: {', '.join(company['sectors'])}")
        print(f"  Dimensions: {', '.join(company['dimensions'])}")
        if company['scb_data']:
            print(f"  Employees: {company['scb_data']['employee_size']}")
            print(f"  Revenue: {company['scb_data']['revenue_size']}")
    print()

    # Example 3: Search
    print("3. Search results for 'Stockholm':")
    results = search_companies('Stockholm')
    for result in results[:3]:
        print(f"  - {result['name']} | {result['employee_size']}")
    print()

    # Example 4: Companies by city
    print("4. Companies in STOCKHOLM:")
    stockholm_companies = get_companies_by_city('STOCKHOLM')
    print(f"  Found {len(stockholm_companies)} companies")
    print()

    # Example 5: Statistics
    print("5. Database statistics:")
    stats = get_statistics()
    print(f"  Total companies: {stats['total_companies']}")
    print(f"  Total sectors: {stats['total_sectors']}")
    print(f"  Total domains: {stats['total_domains']}")
    print(f"  Companies by city:")
    for city_stat in stats['by_city'][:3]:
        print(f"    - {city_stat['location_city']}: {city_stat['count']}")

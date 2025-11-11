#!/usr/bin/env python3
"""
Script to move companies from ai_companies.db to ai_others.db.
This creates a new database, copies all data for specified companies, and removes them from the source.
"""

import sqlite3
from datetime import datetime

def connect_db(db_path):
    """Connect to a database."""
    return sqlite3.connect(db_path)

def get_table_schema(cursor, table_name):
    """Get the CREATE TABLE statement for a table."""
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    result = cursor.fetchone()
    return result[0] if result else None

def create_target_database(source_db_path='ai_companies.db', target_db_path='ai_others.db'):
    """Create target database with the same schema as source."""
    source_conn = connect_db(source_db_path)
    target_conn = connect_db(target_db_path)

    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    # Get all tables
    source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in source_cursor.fetchall()]

    print(f"Creating tables in {target_db_path}...")

    for table in tables:
        schema = get_table_schema(source_cursor, table)
        if schema:
            # Drop table if it exists
            target_cursor.execute(f"DROP TABLE IF EXISTS {table}")
            # Create table
            target_cursor.execute(schema)
            print(f"  ✓ Created table: {table}")

    target_conn.commit()
    source_conn.close()
    target_conn.close()

    print(f"\n✓ Database {target_db_path} created with schema from {source_db_path}")

def copy_companies_to_target(company_ids, source_db_path='ai_companies.db', target_db_path='ai_others.db'):
    """Copy companies and all related data to target database."""
    source_conn = connect_db(source_db_path)
    target_conn = connect_db(target_db_path)

    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()

    placeholders = ','.join('?' * len(company_ids))

    print(f"\n{'='*80}")
    print("COPYING COMPANIES TO ai_others.db")
    print(f"{'='*80}")

    # Check which IDs exist
    source_cursor.execute(f"SELECT id FROM companies WHERE id IN ({placeholders})", company_ids)
    existing_ids = [row[0] for row in source_cursor.fetchall()]

    print(f"\nIDs to move: {len(company_ids)}")
    print(f"IDs found in source database: {len(existing_ids)}")

    if len(existing_ids) < len(company_ids):
        missing_ids = set(company_ids) - set(existing_ids)
        print(f"Warning: IDs not found: {sorted(missing_ids)[:20]}...")  # Show first 20

    if not existing_ids:
        print("\nNo companies to move.")
        source_conn.close()
        target_conn.close()
        return

    placeholders = ','.join('?' * len(existing_ids))

    # Show sample of companies being moved
    print(f"\nSample of companies being moved (first 10):")
    source_cursor.execute(f"""
        SELECT c.id, c.name
        FROM companies c
        WHERE c.id IN ({placeholders})
        ORDER BY c.id
        LIMIT 10
    """, existing_ids)

    for row in source_cursor.fetchall():
        print(f"  ID: {row[0]:4d} | {row[1][:60]}")

    print(f"\n{'-'*80}")
    print("Copying data...")
    print(f"{'-'*80}")

    # 1. Copy companies
    source_cursor.execute(f"SELECT * FROM companies WHERE id IN ({placeholders})", existing_ids)
    companies = source_cursor.fetchall()

    # Get column names
    columns = [desc[0] for desc in source_cursor.description]
    placeholders_values = ','.join('?' * len(columns))

    target_cursor.executemany(
        f"INSERT INTO companies ({','.join(columns)}) VALUES ({placeholders_values})",
        companies
    )
    print(f"  ✓ Copied {len(companies)} companies")

    # 2. Copy company_sectors
    placeholders = ','.join('?' * len(existing_ids))
    source_cursor.execute(f"SELECT * FROM company_sectors WHERE company_id IN ({placeholders})", existing_ids)
    company_sectors = source_cursor.fetchall()
    if company_sectors:
        target_cursor.executemany(
            "INSERT INTO company_sectors (company_id, sector_id) VALUES (?, ?)",
            company_sectors
        )
        print(f"  ✓ Copied {len(company_sectors)} sector associations")

        # Copy referenced sectors
        source_cursor.execute(f"""
            SELECT DISTINCT s.* FROM sectors s
            JOIN company_sectors cs ON s.id = cs.sector_id
            WHERE cs.company_id IN ({placeholders})
        """, existing_ids)
        sectors = source_cursor.fetchall()
        if sectors:
            # Check which sectors already exist in target
            target_cursor.execute("SELECT id FROM sectors")
            existing_sector_ids = {row[0] for row in target_cursor.fetchall()}

            new_sectors = [s for s in sectors if s[0] not in existing_sector_ids]
            if new_sectors:
                target_cursor.executemany(
                    "INSERT INTO sectors (id, name) VALUES (?, ?)",
                    new_sectors
                )
                print(f"  ✓ Copied {len(new_sectors)} new sectors")

    # 3. Copy company_domains
    source_cursor.execute(f"SELECT * FROM company_domains WHERE company_id IN ({placeholders})", existing_ids)
    company_domains = source_cursor.fetchall()
    if company_domains:
        target_cursor.executemany(
            "INSERT INTO company_domains (company_id, domain_id) VALUES (?, ?)",
            company_domains
        )
        print(f"  ✓ Copied {len(company_domains)} domain associations")

        # Copy referenced domains
        source_cursor.execute(f"""
            SELECT DISTINCT d.* FROM domains d
            JOIN company_domains cd ON d.id = cd.domain_id
            WHERE cd.company_id IN ({placeholders})
        """, existing_ids)
        domains = source_cursor.fetchall()
        if domains:
            target_cursor.execute("SELECT id FROM domains")
            existing_domain_ids = {row[0] for row in target_cursor.fetchall()}

            new_domains = [d for d in domains if d[0] not in existing_domain_ids]
            if new_domains:
                target_cursor.executemany(
                    "INSERT INTO domains (id, name) VALUES (?, ?)",
                    new_domains
                )
                print(f"  ✓ Copied {len(new_domains)} new domains")

    # 4. Copy company_ai_capabilities
    source_cursor.execute(f"SELECT * FROM company_ai_capabilities WHERE company_id IN ({placeholders})", existing_ids)
    company_capabilities = source_cursor.fetchall()
    if company_capabilities:
        target_cursor.executemany(
            "INSERT INTO company_ai_capabilities (company_id, capability_id) VALUES (?, ?)",
            company_capabilities
        )
        print(f"  ✓ Copied {len(company_capabilities)} AI capability associations")

        # Copy referenced capabilities
        source_cursor.execute(f"""
            SELECT DISTINCT ac.* FROM ai_capabilities ac
            JOIN company_ai_capabilities cac ON ac.id = cac.capability_id
            WHERE cac.company_id IN ({placeholders})
        """, existing_ids)
        capabilities = source_cursor.fetchall()
        if capabilities:
            target_cursor.execute("SELECT id FROM ai_capabilities")
            existing_cap_ids = {row[0] for row in target_cursor.fetchall()}

            new_capabilities = [c for c in capabilities if c[0] not in existing_cap_ids]
            if new_capabilities:
                target_cursor.executemany(
                    "INSERT INTO ai_capabilities (id, name) VALUES (?, ?)",
                    new_capabilities
                )
                print(f"  ✓ Copied {len(new_capabilities)} new AI capabilities")

    # 5. Copy company_dimensions
    source_cursor.execute(f"SELECT * FROM company_dimensions WHERE company_id IN ({placeholders})", existing_ids)
    company_dimensions = source_cursor.fetchall()
    if company_dimensions:
        target_cursor.executemany(
            "INSERT INTO company_dimensions (company_id, dimension_id) VALUES (?, ?)",
            company_dimensions
        )
        print(f"  ✓ Copied {len(company_dimensions)} dimension associations")

        # Copy referenced dimensions
        source_cursor.execute(f"""
            SELECT DISTINCT dim.* FROM dimensions dim
            JOIN company_dimensions cd ON dim.id = cd.dimension_id
            WHERE cd.company_id IN ({placeholders})
        """, existing_ids)
        dimensions = source_cursor.fetchall()
        if dimensions:
            target_cursor.execute("SELECT id FROM dimensions")
            existing_dim_ids = {row[0] for row in target_cursor.fetchall()}

            new_dimensions = [d for d in dimensions if d[0] not in existing_dim_ids]
            if new_dimensions:
                target_cursor.executemany(
                    "INSERT INTO dimensions (id, name) VALUES (?, ?)",
                    new_dimensions
                )
                print(f"  ✓ Copied {len(new_dimensions)} new dimensions")

    # 6. Copy scb_matches
    source_cursor.execute(f"SELECT * FROM scb_matches WHERE company_id IN ({placeholders})", existing_ids)
    scb_matches = source_cursor.fetchall()
    if scb_matches:
        columns = [desc[0] for desc in source_cursor.description]
        placeholders_values = ','.join('?' * len(columns))
        target_cursor.executemany(
            f"INSERT INTO scb_matches ({','.join(columns)}) VALUES ({placeholders_values})",
            scb_matches
        )
        print(f"  ✓ Copied {len(scb_matches)} SCB matches")

    # 7. Copy scb_enrichment
    source_cursor.execute(f"SELECT * FROM scb_enrichment WHERE company_id IN ({placeholders})", existing_ids)
    scb_enrichment = source_cursor.fetchall()
    if scb_enrichment:
        columns = [desc[0] for desc in source_cursor.description]
        placeholders_values = ','.join('?' * len(columns))
        target_cursor.executemany(
            f"INSERT INTO scb_enrichment ({','.join(columns)}) VALUES ({placeholders_values})",
            scb_enrichment
        )
        print(f"  ✓ Copied {len(scb_enrichment)} SCB enrichment records")

    # Commit changes to target
    target_conn.commit()

    print(f"\n✓ All data copied to {target_db_path}")

    source_conn.close()
    target_conn.close()

    return existing_ids

def delete_companies_from_source(company_ids, source_db_path='ai_companies.db'):
    """Delete companies and all related data from source database."""
    conn = connect_db(source_db_path)
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(company_ids))

    print(f"\n{'='*80}")
    print("DELETING COMPANIES FROM ai_companies.db")
    print(f"{'='*80}")

    # Delete from related tables first
    print(f"\nDeleting related data...")

    cursor.execute(f"DELETE FROM company_sectors WHERE company_id IN ({placeholders})", company_ids)
    print(f"  ✓ Deleted {cursor.rowcount} sector associations")

    cursor.execute(f"DELETE FROM company_domains WHERE company_id IN ({placeholders})", company_ids)
    print(f"  ✓ Deleted {cursor.rowcount} domain associations")

    cursor.execute(f"DELETE FROM company_ai_capabilities WHERE company_id IN ({placeholders})", company_ids)
    print(f"  ✓ Deleted {cursor.rowcount} AI capability associations")

    cursor.execute(f"DELETE FROM company_dimensions WHERE company_id IN ({placeholders})", company_ids)
    print(f"  ✓ Deleted {cursor.rowcount} dimension associations")

    cursor.execute(f"DELETE FROM scb_matches WHERE company_id IN ({placeholders})", company_ids)
    print(f"  ✓ Deleted {cursor.rowcount} SCB matches")

    cursor.execute(f"DELETE FROM scb_enrichment WHERE company_id IN ({placeholders})", company_ids)
    print(f"  ✓ Deleted {cursor.rowcount} SCB enrichment records")

    # Delete companies
    cursor.execute(f"DELETE FROM companies WHERE id IN ({placeholders})", company_ids)
    deleted_count = cursor.rowcount
    print(f"\n  ✓ Deleted {deleted_count} companies")

    # Commit changes
    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM companies")
    remaining_count = cursor.fetchone()[0]

    conn.close()

    return deleted_count, remaining_count

def main():
    """Main function."""
    # IDs to move
    ids_to_move = [
        1121, 1131, 1136, 1141, 1148, 1155, 1156, 1171, 1183, 1196,
        1198, 1221, 1228, 1250, 1252, 1274, 1288, 1294, 1298, 1315,
        1369, 1420, 1436, 1456, 1463, 1470, 1481, 1486, 1489, 1512,
        1519, 1524, 1543, 1591, 1613, 1622, 1628, 1633, 1649, 1668,
        1685, 1690, 1713, 1739, 1747, 1775, 1793, 1799, 1805, 1843,
        1859, 1952, 1999, 2000, 2044, 2088, 2103, 2104, 2118, 2128,
        2132, 2140, 2155, 2203, 2208, 2258, 2264, 2291, 1300, 1317,
        1372, 1386, 1397, 1448, 1476, 1482, 1544, 1587, 1590, 1593,
        1650, 1663, 1812, 1821, 1834, 1857, 1872, 1931, 2030, 2039,
        2162, 1342, 1343, 1344, 1723, 1740, 1861, 1126, 1223, 1341,
        1348, 1349, 1400, 1553, 1592, 1210, 1779, 1175, 1841, 1267,
        2297, 2323, 1687, 2322, 1206, 1203, 2169, 2324, 1139, 1244,
        1479, 1170, 1132, 1403, 1370, 1185, 1467, 1477, 1844, 1983,
        1, 2056, 1835, 1371, 2285, 1521, 1509, 2093, 1786, 1527,
        1314, 2216, 1356, 1699, 1335, 1241, 1990, 1571, 1454, 2119,
        1447, 2206, 2230, 1752, 1617, 1554, 1665, 1997, 1769, 1694,
        1716, 1421, 1451, 1845, 2236, 1429, 1363, 1231, 2035, 1418,
        2255, 1514, 1804
    ]

    print(f"\n{'#'*80}")
    print(f"# MOVING COMPANIES TO ai_others.db")
    print(f"# Total IDs to process: {len(ids_to_move)}")
    print(f"# Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}")

    # Step 1: Create target database
    create_target_database()

    # Step 2: Copy companies to target
    existing_ids = copy_companies_to_target(ids_to_move)

    if not existing_ids:
        print("\nNo companies were moved.")
        return

    # Step 3: Delete from source
    deleted_count, remaining_count = delete_companies_from_source(existing_ids)

    # Final summary
    print(f"\n{'='*80}")
    print("OPERATION COMPLETED SUCCESSFULLY")
    print(f"{'='*80}")
    print(f"  Companies moved: {len(existing_ids)}")
    print(f"  Remaining companies in ai_companies.db: {remaining_count}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()

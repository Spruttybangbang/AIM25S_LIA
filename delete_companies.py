#!/usr/bin/env python3
"""
Script to permanently delete companies from the database by their IDs.
"""

import sqlite3
from pathlib import Path

def connect_db(db_path='ai_companies.db'):
    """Connect to the database."""
    return sqlite3.connect(db_path)

def inspect_database():
    """Inspect database structure."""
    conn = connect_db()
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"Tables in database: {tables}")

    # Get schema for each table
    for table in tables:
        print(f"\nSchema for {table}:")
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

        # Count rows
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  Total rows: {count}")

    conn.close()

def delete_companies_by_ids(ids_to_delete, table_name='companies'):
    """Delete companies from the database by their IDs."""
    conn = connect_db()
    cursor = conn.cursor()

    # Convert IDs to list if needed
    if isinstance(ids_to_delete, (list, tuple)):
        id_list = ids_to_delete
    else:
        id_list = [ids_to_delete]

    # First, check which IDs exist
    placeholders = ','.join('?' * len(id_list))
    cursor.execute(f"SELECT id FROM {table_name} WHERE id IN ({placeholders})", id_list)
    existing_ids = [row[0] for row in cursor.fetchall()]

    print(f"\nIDs to delete: {len(id_list)}")
    print(f"IDs found in database: {len(existing_ids)}")

    if len(existing_ids) < len(id_list):
        missing_ids = set(id_list) - set(existing_ids)
        print(f"IDs not found in database: {sorted(missing_ids)}")

    if not existing_ids:
        print("\nNo IDs to delete.")
        conn.close()
        return

    # Show companies that will be deleted
    print("\nCompanies to be deleted:")
    cursor.execute(f"""
        SELECT c.id, c.name, se.organization_number
        FROM {table_name} c
        LEFT JOIN scb_enrichment se ON c.id = se.company_id
        WHERE c.id IN ({placeholders})
        ORDER BY c.id
    """, existing_ids)

    for row in cursor.fetchall():
        print(f"  ID: {row[0]:4d} | {row[1][:50]:50s} | OrgNr: {row[2] or 'N/A'}")

    # Confirm deletion
    print(f"\n{'='*80}")
    print(f"WARNING: About to PERMANENTLY delete {len(existing_ids)} companies from the database!")
    print(f"{'='*80}")

    response = input("\nType 'DELETE' to confirm (or anything else to cancel): ")

    if response != 'DELETE':
        print("\nDeletion cancelled.")
        conn.close()
        return

    # Perform deletion
    cursor.execute(f"DELETE FROM {table_name} WHERE id IN ({placeholders})", existing_ids)
    deleted_count = cursor.rowcount

    # Commit changes
    conn.commit()

    print(f"\n✓ Successfully deleted {deleted_count} companies from the database.")

    # Verify deletion
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    remaining_count = cursor.fetchone()[0]
    print(f"✓ Remaining companies in database: {remaining_count}")

    conn.close()

def main():
    """Main function."""
    print("Database inspection:")
    print("="*80)
    inspect_database()

    # IDs to delete
    ids_to_delete = [
        1153, 1432, 1962, 1200, 1401, 1272, 1469, 2107, 1879, 1182,
        1316, 2281, 1384, 2185, 1273, 1826, 1618, 1820, 2012, 2175,
        1528, 1965, 1624, 1352, 1449, 1749, 1770, 1818, 1721, 1508,
        1532, 1814, 2021, 2188
    ]

    print(f"\n\n{'='*80}")
    print("DELETION OPERATION")
    print(f"{'='*80}")

    delete_companies_by_ids(ids_to_delete)

if __name__ == '__main__':
    main()

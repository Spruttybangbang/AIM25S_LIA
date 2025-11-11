#!/usr/bin/env python3
"""
Script to permanently delete specific companies from the database.
This version performs the deletion without interactive confirmation.
"""

import sqlite3
from datetime import datetime

def connect_db(db_path='ai_companies.db'):
    """Connect to the database."""
    return sqlite3.connect(db_path)

def delete_companies_by_ids(ids_to_delete):
    """Delete companies and all related data from the database by their IDs."""
    conn = connect_db()
    cursor = conn.cursor()

    # Convert IDs to list if needed
    if isinstance(ids_to_delete, (list, tuple)):
        id_list = ids_to_delete
    else:
        id_list = [ids_to_delete]

    # First, check which IDs exist
    placeholders = ','.join('?' * len(id_list))
    cursor.execute(f"SELECT id FROM companies WHERE id IN ({placeholders})", id_list)
    existing_ids = [row[0] for row in cursor.fetchall()]

    print(f"{'='*80}")
    print(f"PERMANENT DELETION OF COMPANIES")
    print(f"{'='*80}")
    print(f"\nIDs requested for deletion: {len(id_list)}")
    print(f"IDs found in database: {len(existing_ids)}")

    if len(existing_ids) < len(id_list):
        missing_ids = set(id_list) - set(existing_ids)
        print(f"\nWarning: IDs not found in database: {sorted(missing_ids)}")

    if not existing_ids:
        print("\nNo IDs to delete.")
        conn.close()
        return

    # Show companies that will be deleted
    print(f"\n{'-'*80}")
    print("Companies to be deleted:")
    print(f"{'-'*80}")
    cursor.execute(f"""
        SELECT c.id, c.name, se.organization_number
        FROM companies c
        LEFT JOIN scb_enrichment se ON c.id = se.company_id
        WHERE c.id IN ({placeholders})
        ORDER BY c.id
    """, existing_ids)

    companies_to_delete = cursor.fetchall()
    for row in companies_to_delete:
        print(f"  ID: {row[0]:4d} | {row[1][:50]:50s} | OrgNr: {row[2] or 'N/A'}")

    # Delete from related tables first (foreign key constraints)
    print(f"\n{'-'*80}")
    print("Deleting related data...")
    print(f"{'-'*80}")

    # Delete from company_sectors
    cursor.execute(f"DELETE FROM company_sectors WHERE company_id IN ({placeholders})", existing_ids)
    deleted_sectors = cursor.rowcount
    print(f"  ✓ Deleted {deleted_sectors} sector associations")

    # Delete from company_domains
    cursor.execute(f"DELETE FROM company_domains WHERE company_id IN ({placeholders})", existing_ids)
    deleted_domains = cursor.rowcount
    print(f"  ✓ Deleted {deleted_domains} domain associations")

    # Delete from company_ai_capabilities
    cursor.execute(f"DELETE FROM company_ai_capabilities WHERE company_id IN ({placeholders})", existing_ids)
    deleted_capabilities = cursor.rowcount
    print(f"  ✓ Deleted {deleted_capabilities} AI capability associations")

    # Delete from company_dimensions
    cursor.execute(f"DELETE FROM company_dimensions WHERE company_id IN ({placeholders})", existing_ids)
    deleted_dimensions = cursor.rowcount
    print(f"  ✓ Deleted {deleted_dimensions} dimension associations")

    # Delete from scb_matches
    cursor.execute(f"DELETE FROM scb_matches WHERE company_id IN ({placeholders})", existing_ids)
    deleted_matches = cursor.rowcount
    print(f"  ✓ Deleted {deleted_matches} SCB matches")

    # Delete from scb_enrichment
    cursor.execute(f"DELETE FROM scb_enrichment WHERE company_id IN ({placeholders})", existing_ids)
    deleted_enrichment = cursor.rowcount
    print(f"  ✓ Deleted {deleted_enrichment} SCB enrichment records")

    # Finally, delete from companies table
    print(f"\n{'-'*80}")
    print("Deleting companies...")
    print(f"{'-'*80}")
    cursor.execute(f"DELETE FROM companies WHERE id IN ({placeholders})", existing_ids)
    deleted_companies = cursor.rowcount

    # Commit all changes
    conn.commit()

    print(f"  ✓ Deleted {deleted_companies} companies")

    # Verify deletion
    cursor.execute("SELECT COUNT(*) FROM companies")
    remaining_count = cursor.fetchone()[0]

    print(f"\n{'='*80}")
    print("DELETION COMPLETED SUCCESSFULLY")
    print(f"{'='*80}")
    print(f"  Companies deleted: {deleted_companies}")
    print(f"  Remaining companies in database: {remaining_count}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    conn.close()

def main():
    """Main function."""
    # IDs to delete (provided by user)
    ids_to_delete = [
        1153, 1432, 1962, 1200, 1401, 1272, 1469, 2107, 1879, 1182,
        1316, 2281, 1384, 2185, 1273, 1826, 1618, 1820, 2012, 2175,
        1528, 1965, 1624, 1352, 1449, 1749, 1770, 1818, 1721, 1508,
        1532, 1814, 2021, 2188
    ]

    delete_companies_by_ids(ids_to_delete)

if __name__ == '__main__':
    main()

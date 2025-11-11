#!/usr/bin/env python3
"""Quick verification of database counts."""
import sqlite3

def count_companies(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM companies")
    count = cursor.fetchone()[0]
    conn.close()
    return count

print("Database verification:")
print(f"ai_companies.db: {count_companies('ai_companies.db')} companies")
print(f"ai_others.db: {count_companies('ai_others.db')} companies")

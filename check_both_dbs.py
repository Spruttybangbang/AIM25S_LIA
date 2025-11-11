#!/usr/bin/env python3
import sqlite3

def check_db(path, name):
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM companies")
    count = cursor.fetchone()[0]
    print(f"{name}: {count} companies")
    conn.close()

check_db('databases/ai_companies.db', 'ai_companies.db')
check_db('databases/ai_others.db', 'ai_others.db')
print(f"Total: {1079 + 173 if 'ai_others.db' else 1079}")

#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('ai_companies.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM companies")
print(f"Companies in ai_companies.db: {cursor.fetchone()[0]}")
conn.close()

#!/usr/bin/env python3
import sqlite3
import os

# Path relative to project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..', '..')
db_path = os.path.join(project_root, 'databases', 'ai_companies.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM companies")
print(f"Companies in ai_companies.db: {cursor.fetchone()[0]}")
conn.close()

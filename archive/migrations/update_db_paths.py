#!/usr/bin/env python3
"""
Update all scripts to use correct database paths after reorganization.
"""

import os
import re

def update_file(filepath):
    """Update database path in a Python file."""
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    # Pattern 1: Simple connect
    pattern1 = r"sqlite3\.connect\('ai_companies\.db'\)"
    replacement1 = """sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'databases', 'ai_companies.db'))"""

    # Pattern 2: With variable
    pattern2 = r"db_path\s*=\s*['\"]ai_companies\.db['\"]"
    replacement2 = """db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'databases', 'ai_companies.db')"""

    content = re.sub(pattern1, replacement1, content)
    content = re.sub(pattern2, replacement2, content)

    # Add import os if not present and content changed
    if content != original and 'import os' not in content:
        # Find where to insert import
        import_match = re.search(r'^import \w+', content, re.MULTILINE)
        if import_match:
            pos = import_match.start()
            content = content[:pos] + 'import os\n' + content[pos:]

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Update all scripts."""
    scripts_dir = 'scripts'
    updated = []

    for root, dirs, files in os.walk(scripts_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if update_file(filepath):
                    updated.append(filepath)
                    print(f"✓ Updated: {filepath}")

    print(f"\nTotal files updated: {len(updated)}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Interaktivt verktyg för att granska och hantera dubbletter i databasen.
Låter användaren se all data för varje dublett och välja åtgärd.
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime
from difflib import SequenceMatcher

def connect_db():
    return sqlite3.connect('ai_companies.db')

def backup_database():
    """Create backup before making changes."""
    import shutil
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'ai_companies_backup_dedup_{timestamp}.db'
    shutil.copy2('ai_companies.db', backup_path)
    print(f"✅ Backup skapad: {backup_path}")
    return backup_path

def similarity(a, b):
    """Calculate similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def get_all_company_data(conn, company_id):
    """Get all data for a company from all tables."""
    data = {}

    # Companies table
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
    columns = [description[0] for description in cursor.description]
    row = cursor.fetchone()
    if row:
        data['companies'] = dict(zip(columns, row))
    else:
        data['companies'] = None

    # SCB enrichment
    cursor.execute("SELECT * FROM scb_enrichment WHERE company_id = ?", (company_id,))
    columns = [description[0] for description in cursor.description]
    row = cursor.fetchone()
    if row:
        data['scb_enrichment'] = dict(zip(columns, row))
    else:
        data['scb_enrichment'] = None

    # Sectors
    cursor.execute("""
        SELECT s.name
        FROM company_sectors cs
        JOIN sectors s ON cs.sector_id = s.id
        WHERE cs.company_id = ?
    """, (company_id,))
    data['sectors'] = [row[0] for row in cursor.fetchall()]

    # Domains
    cursor.execute("""
        SELECT d.name
        FROM company_domains cd
        JOIN domains d ON cd.domain_id = d.id
        WHERE cd.company_id = ?
    """, (company_id,))
    data['domains'] = [row[0] for row in cursor.fetchall()]

    # AI Capabilities
    cursor.execute("""
        SELECT ac.name
        FROM company_ai_capabilities cac
        JOIN ai_capabilities ac ON cac.ai_capability_id = ac.id
        WHERE cac.company_id = ?
    """, (company_id,))
    data['ai_capabilities'] = [row[0] for row in cursor.fetchall()]

    # Dimensions
    cursor.execute("""
        SELECT d.name
        FROM company_dimensions cd
        JOIN dimensions d ON cd.dimension_id = d.id
        WHERE cd.company_id = ?
    """, (company_id,))
    data['dimensions'] = [row[0] for row in cursor.fetchall()]

    return data

def display_company_comparison(conn, company_ids):
    """Display detailed comparison of companies side by side."""
    companies_data = [get_all_company_data(conn, cid) for cid in company_ids]

    print("\n" + "="*120)
    print("JÄMFÖRELSE AV FÖRETAG")
    print("="*120)

    # Companies basic info
    print("\n" + "-"*120)
    print("GRUNDDATA (companies-tabellen):")
    print("-"*120)

    fields_to_show = ['id', 'name', 'website', 'type', 'description', 'location_city',
                      'location_country', 'source', 'is_swedish', 'data_quality_score']

    for field in fields_to_show:
        values = []
        for i, data in enumerate(companies_data):
            if data['companies']:
                value = data['companies'].get(field, 'N/A')
                # Truncate long strings
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + "..."
                values.append(str(value))
            else:
                values.append("N/A")

        print(f"\n{field:20s}:", end="")
        for i, val in enumerate(values):
            col_width = 50
            print(f" [{i+1}] {val:<{col_width}}", end="")
        print()

    # SCB data
    print("\n" + "-"*120)
    print("SCB-DATA (scb_enrichment-tabellen):")
    print("-"*120)

    scb_fields = ['organization_number', 'scb_company_name', 'post_city', 'post_address',
                  'employee_size', 'industry_1', 'revenue_size', 'phone', 'email', 'company_status']

    has_scb = [data['scb_enrichment'] is not None for data in companies_data]

    if any(has_scb):
        for field in scb_fields:
            values = []
            for i, data in enumerate(companies_data):
                if data['scb_enrichment']:
                    value = data['scb_enrichment'].get(field, 'N/A')
                    if isinstance(value, str) and len(value) > 40:
                        value = value[:37] + "..."
                    values.append(str(value) if value else "—")
                else:
                    values.append("INGEN SCB")

            print(f"\n{field:20s}:", end="")
            for i, val in enumerate(values):
                col_width = 50
                indicator = "✅" if has_scb[i] else "❌"
                print(f" [{i+1}] {indicator} {val:<{col_width}}", end="")
            print()
    else:
        print("\n  ❌ Ingen av företagen har SCB-data")

    # Relationships
    print("\n" + "-"*120)
    print("RELATIONER (sectors, domains, AI capabilities, dimensions):")
    print("-"*120)

    for i, data in enumerate(companies_data):
        print(f"\n[{i+1}] ID {company_ids[i]}:")
        print(f"  Sektorer ({len(data['sectors'])}): {', '.join(data['sectors'][:5]) if data['sectors'] else 'Inga'}")
        if len(data['sectors']) > 5:
            print(f"    ... och {len(data['sectors']) - 5} till")

        print(f"  Domains ({len(data['domains'])}): {', '.join(data['domains'][:5]) if data['domains'] else 'Inga'}")
        if len(data['domains']) > 5:
            print(f"    ... och {len(data['domains']) - 5} till")

        print(f"  AI Capabilities ({len(data['ai_capabilities'])}): {', '.join(data['ai_capabilities'][:5]) if data['ai_capabilities'] else 'Inga'}")
        if len(data['ai_capabilities']) > 5:
            print(f"    ... och {len(data['ai_capabilities']) - 5} till")

        print(f"  Dimensions ({len(data['dimensions'])}): {', '.join(data['dimensions'][:5]) if data['dimensions'] else 'Inga'}")
        if len(data['dimensions']) > 5:
            print(f"    ... och {len(data['dimensions']) - 5} till")

    return companies_data

def merge_companies(conn, keep_id, remove_id, companies_data):
    """Merge two companies - keep the best data from both."""
    print(f"\n🔄 Mergar företag {remove_id} → {keep_id}...")

    cursor = conn.cursor()

    # Get data for both
    keep_data = None
    remove_data = None
    for data in companies_data:
        if data['companies']['id'] == keep_id:
            keep_data = data
        elif data['companies']['id'] == remove_id:
            remove_data = data

    # Merge companies table data
    updates = {}

    # Keep non-null values from remove_id if keep_id has null
    fields_to_merge = ['website', 'logo_url', 'description', 'location_city', 'owner', 'maturity']

    for field in fields_to_merge:
        keep_val = keep_data['companies'].get(field)
        remove_val = remove_data['companies'].get(field)

        # If keep is null/empty but remove has value, use remove's value
        if (not keep_val or keep_val == '') and remove_val and remove_val != '':
            updates[field] = remove_val
            print(f"  📝 Uppdaterar {field}: '{remove_val}'")

    # Apply updates to keep_id
    if updates:
        update_sql = "UPDATE companies SET " + ", ".join([f"{k} = ?" for k in updates.keys()]) + " WHERE id = ?"
        cursor.execute(update_sql, list(updates.values()) + [keep_id])
        print(f"  ✅ {len(updates)} fält uppdaterade")

    # Merge relationships (sectors, domains, ai_capabilities, dimensions)
    # Add any from remove_id that don't exist in keep_id

    # Sectors
    if remove_data['sectors']:
        for sector in remove_data['sectors']:
            # Get sector_id
            cursor.execute("SELECT id FROM sectors WHERE name = ?", (sector,))
            sector_id = cursor.fetchone()
            if sector_id:
                sector_id = sector_id[0]
                # Check if relationship exists
                cursor.execute("SELECT 1 FROM company_sectors WHERE company_id = ? AND sector_id = ?",
                              (keep_id, sector_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO company_sectors (company_id, sector_id) VALUES (?, ?)",
                                  (keep_id, sector_id))
                    print(f"  ➕ Lade till sektor: {sector}")

    # Domains
    if remove_data['domains']:
        for domain in remove_data['domains']:
            cursor.execute("SELECT id FROM domains WHERE name = ?", (domain,))
            domain_id = cursor.fetchone()
            if domain_id:
                domain_id = domain_id[0]
                cursor.execute("SELECT 1 FROM company_domains WHERE company_id = ? AND domain_id = ?",
                              (keep_id, domain_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO company_domains (company_id, domain_id) VALUES (?, ?)",
                                  (keep_id, domain_id))
                    print(f"  ➕ Lade till domain: {domain}")

    # AI Capabilities
    if remove_data['ai_capabilities']:
        for ai_cap in remove_data['ai_capabilities']:
            cursor.execute("SELECT id FROM ai_capabilities WHERE name = ?", (ai_cap,))
            ai_cap_id = cursor.fetchone()
            if ai_cap_id:
                ai_cap_id = ai_cap_id[0]
                cursor.execute("SELECT 1 FROM company_ai_capabilities WHERE company_id = ? AND ai_capability_id = ?",
                              (keep_id, ai_cap_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO company_ai_capabilities (company_id, ai_capability_id) VALUES (?, ?)",
                                  (keep_id, ai_cap_id))
                    print(f"  ➕ Lade till AI capability: {ai_cap}")

    # Dimensions
    if remove_data['dimensions']:
        for dim in remove_data['dimensions']:
            cursor.execute("SELECT id FROM dimensions WHERE name = ?", (dim,))
            dim_id = cursor.fetchone()
            if dim_id:
                dim_id = dim_id[0]
                cursor.execute("SELECT 1 FROM company_dimensions WHERE company_id = ? AND dimension_id = ?",
                              (keep_id, dim_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO company_dimensions (company_id, dimension_id) VALUES (?, ?)",
                                  (keep_id, dim_id))
                    print(f"  ➕ Lade till dimension: {dim}")

    # Delete relationships for remove_id
    cursor.execute("DELETE FROM company_sectors WHERE company_id = ?", (remove_id,))
    cursor.execute("DELETE FROM company_domains WHERE company_id = ?", (remove_id,))
    cursor.execute("DELETE FROM company_ai_capabilities WHERE company_id = ?", (remove_id,))
    cursor.execute("DELETE FROM company_dimensions WHERE company_id = ?", (remove_id,))

    # Delete SCB data for remove_id
    cursor.execute("DELETE FROM scb_enrichment WHERE company_id = ?", (remove_id,))
    cursor.execute("DELETE FROM scb_matches WHERE company_id = ?", (remove_id,))

    # Delete the company
    cursor.execute("DELETE FROM companies WHERE id = ?", (remove_id,))

    conn.commit()
    print(f"  ✅ Företag {remove_id} borttaget och data mergad till {keep_id}")

def delete_company(conn, company_id):
    """Delete a company and all its relationships."""
    print(f"\n🗑️  Tar bort företag {company_id}...")

    cursor = conn.cursor()

    # Delete relationships
    cursor.execute("DELETE FROM company_sectors WHERE company_id = ?", (company_id,))
    cursor.execute("DELETE FROM company_domains WHERE company_id = ?", (company_id,))
    cursor.execute("DELETE FROM company_ai_capabilities WHERE company_id = ?", (company_id,))
    cursor.execute("DELETE FROM company_dimensions WHERE company_id = ?", (company_id,))

    # Delete SCB data
    cursor.execute("DELETE FROM scb_enrichment WHERE company_id = ?", (company_id,))
    cursor.execute("DELETE FROM scb_matches WHERE company_id = ?", (company_id,))

    # Delete company
    cursor.execute("DELETE FROM companies WHERE id = ?", (company_id,))

    conn.commit()
    print(f"  ✅ Företag {company_id} borttaget")

def find_duplicates(conn):
    """Find all potential duplicates."""
    companies = pd.read_sql_query("SELECT * FROM companies", conn)
    scb_enrichment = pd.read_sql_query("SELECT company_id, organization_number FROM scb_enrichment", conn)

    companies = companies.merge(scb_enrichment, left_on='id', right_on='company_id', how='left')

    duplicates = []

    # 1. Exact name matches
    name_counts = companies['name'].value_counts()
    for name, count in name_counts[name_counts > 1].items():
        dupes = companies[companies['name'] == name]
        duplicates.append({
            'type': 'exact_name',
            'reason': f"Exakt samma namn: '{name}'",
            'ids': dupes['id'].tolist(),
            'confidence': 'HIGH'
        })

    # 2. Same website
    companies_with_website = companies[companies['website'].notna() & (companies['website'] != '')]
    website_counts = companies_with_website['website'].value_counts()
    for website, count in website_counts[website_counts > 1].items():
        dupes = companies[companies['website'] == website]
        # Skip if already in exact_name
        if not any(set(dupes['id'].tolist()).issubset(set(d['ids'])) for d in duplicates):
            duplicates.append({
                'type': 'same_website',
                'reason': f"Samma webbsida: {website}",
                'ids': dupes['id'].tolist(),
                'confidence': 'HIGH'
            })

    # 3. Same organization number
    companies_with_orgnum = companies[companies['organization_number'].notna()]
    orgnum_counts = companies_with_orgnum['organization_number'].value_counts()
    for orgnum, count in orgnum_counts[orgnum_counts > 1].items():
        dupes = companies[companies['organization_number'] == orgnum]
        duplicates.append({
            'type': 'same_orgnum',
            'reason': f"Samma orgnr: {orgnum}",
            'ids': dupes['id'].tolist(),
            'confidence': 'VERY HIGH'
        })

    # 4. Similar names (>90% similarity for interactive review)
    threshold = 0.90
    unique_names = companies['name'].unique()
    checked_pairs = set()

    for i, name1 in enumerate(unique_names):
        for name2 in unique_names[i+1:]:
            pair = tuple(sorted([name1, name2]))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)

            sim = similarity(name1, name2)
            if sim >= threshold:
                companies1 = companies[companies['name'] == name1]
                companies2 = companies[companies['name'] == name2]
                all_ids = companies1['id'].tolist() + companies2['id'].tolist()

                # Skip if already covered by exact match
                if not any(set(all_ids).issubset(set(d['ids'])) for d in duplicates):
                    duplicates.append({
                        'type': 'similar_name',
                        'reason': f"Liknande namn ({sim:.1%}): '{name1}' ↔ '{name2}'",
                        'ids': all_ids,
                        'confidence': 'MEDIUM'
                    })

    return duplicates

def interactive_review():
    """Interactive review of duplicates."""
    print("="*120)
    print("INTERAKTIV DUBBLETTGRANSKNING")
    print("="*120)

    conn = connect_db()

    # Find duplicates
    print("\n🔍 Söker efter dubbletter...")
    duplicates = find_duplicates(conn)

    print(f"\n✅ Hittade {len(duplicates)} dubblettgrupper att granska")

    if not duplicates:
        print("\n🎉 Inga dubbletter hittades!")
        conn.close()
        return

    # Ask if user wants to create backup
    print("\n" + "="*120)
    response = input("Vill du skapa en backup innan du fortsätter? (ja/nej): ").strip().lower()
    if response in ['ja', 'j', 'yes', 'y']:
        backup_path = backup_database()
    else:
        backup_path = None

    # Track changes
    changes = {
        'merged': 0,
        'deleted': 0,
        'kept': 0
    }

    # Review each duplicate group
    for i, dup in enumerate(duplicates):
        print("\n" + "="*120)
        print(f"DUBBLETTGRUPP {i+1}/{len(duplicates)}")
        print("="*120)
        print(f"Typ: {dup['type']}")
        print(f"Anledning: {dup['reason']}")
        print(f"Säkerhet: {dup['confidence']}")
        print(f"Antal företag: {len(dup['ids'])}")

        # Show comparison
        companies_data = display_company_comparison(conn, dup['ids'])

        # Ask user what to do
        print("\n" + "-"*120)
        print("VAD VILL DU GÖRA?")
        print("-"*120)
        print("  m [id1] [id2] - Merga företag (behåll [id1], ta bort [id2])")
        print("  d [id]        - Ta bort företag [id]")
        print("  k             - Behåll båda (fortsätt till nästa)")
        print("  s             - Hoppa över resten")
        print("  q             - Avsluta och spara")

        while True:
            action = input("\nDitt val: ").strip().lower()

            if action == 's':
                print("⏭️  Hoppar över resten")
                break
            elif action == 'q':
                print("💾 Avslutar...")
                conn.close()
                print(f"\n📊 Sammanfattning:")
                print(f"  Mergade: {changes['merged']}")
                print(f"  Borttagna: {changes['deleted']}")
                print(f"  Behöll båda: {changes['kept']}")
                if backup_path:
                    print(f"\n💾 Backup: {backup_path}")
                return
            elif action == 'k':
                changes['kept'] += 1
                print("✅ Behåller båda företagen")
                break
            elif action.startswith('m '):
                try:
                    parts = action.split()
                    if len(parts) != 3:
                        print("❌ Fel format. Använd: m [id1] [id2]")
                        continue
                    keep_id = int(parts[1])
                    remove_id = int(parts[2])

                    if keep_id not in dup['ids'] or remove_id not in dup['ids']:
                        print(f"❌ IDs måste vara från gruppen: {dup['ids']}")
                        continue

                    merge_companies(conn, keep_id, remove_id, companies_data)
                    changes['merged'] += 1
                    break
                except ValueError:
                    print("❌ IDs måste vara nummer")
            elif action.startswith('d '):
                try:
                    parts = action.split()
                    if len(parts) != 2:
                        print("❌ Fel format. Använd: d [id]")
                        continue
                    delete_id = int(parts[1])

                    if delete_id not in dup['ids']:
                        print(f"❌ ID måste vara från gruppen: {dup['ids']}")
                        continue

                    confirm = input(f"⚠️  Är du säker på att du vill ta bort företag {delete_id}? (ja/nej): ")
                    if confirm.lower() in ['ja', 'j', 'yes', 'y']:
                        delete_company(conn, delete_id)
                        changes['deleted'] += 1
                        break
                    else:
                        print("❌ Avbruten")
                except ValueError:
                    print("❌ ID måste vara ett nummer")
            else:
                print("❌ Ogiltigt kommando. Använd: m [id1] [id2], d [id], k, s, eller q")

        if action == 's':
            break

    # Summary
    print("\n" + "="*120)
    print("GRANSKNING SLUTFÖRD")
    print("="*120)
    print(f"\n📊 Sammanfattning:")
    print(f"  Mergade företag: {changes['merged']}")
    print(f"  Borttagna företag: {changes['deleted']}")
    print(f"  Behöll båda: {changes['kept']}")
    print(f"  Total förändring: -{changes['deleted'] + changes['merged']} företag")

    if backup_path:
        print(f"\n💾 Backup: {backup_path}")
        print(f"   Återställ med: mv {backup_path} ai_companies.db")

    conn.close()

if __name__ == '__main__':
    interactive_review()

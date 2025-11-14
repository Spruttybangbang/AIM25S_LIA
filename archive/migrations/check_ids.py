#!/usr/bin/env python3
"""
Kontrollera om specifika ID:n finns i ai_companies.db eller ai_others.db
"""
import sqlite3

# ID:n att kontrollera
ids_to_check = [
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

def check_ids_in_db(db_path, ids):
    """Kontrollera vilka ID:n som finns i en databas."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(ids))
    cursor.execute(f"SELECT id, name FROM companies WHERE id IN ({placeholders}) ORDER BY id", ids)
    found = cursor.fetchall()

    conn.close()
    return found

print("="*80)
print("KONTROLLERA ID:N I DATABASER")
print("="*80)
print(f"\nAntal ID:n att kontrollera: {len(ids_to_check)}")

# Kontrollera ai_companies.db
print(f"\n{'-'*80}")
print("Kontrollerar databases/ai_companies.db...")
print(f"{'-'*80}")
found_in_companies = check_ids_in_db('databases/ai_companies.db', ids_to_check)

if found_in_companies:
    print(f"\n⚠️  VARNING: {len(found_in_companies)} ID:n finns fortfarande i ai_companies.db!\n")
    print("Första 10 företag:")
    for company_id, name in found_in_companies[:10]:
        print(f"  ID {company_id:4d}: {name}")
    if len(found_in_companies) > 10:
        print(f"  ... och {len(found_in_companies) - 10} fler")
else:
    print("\n✓ Inga av dessa ID:n finns i ai_companies.db")

# Kontrollera ai_others.db
print(f"\n{'-'*80}")
print("Kontrollerar databases/ai_others.db...")
print(f"{'-'*80}")
found_in_others = check_ids_in_db('databases/ai_others.db', ids_to_check)

if found_in_others:
    print(f"\n✓ {len(found_in_others)} ID:n finns i ai_others.db (som förväntat)\n")
    print("Första 10 företag:")
    for company_id, name in found_in_others[:10]:
        print(f"  ID {company_id:4d}: {name}")
    if len(found_in_others) > 10:
        print(f"  ... och {len(found_in_others) - 10} fler")
else:
    print("\n⚠️  VARNING: Inga av dessa ID:n finns i ai_others.db!")

# Sammanfattning
print(f"\n{'='*80}")
print("SAMMANFATTNING")
print(f"{'='*80}")
print(f"Total ID:n att kontrollera: {len(ids_to_check)}")
print(f"Finns i ai_companies.db: {len(found_in_companies)}")
print(f"Finns i ai_others.db: {len(found_in_others)}")

found_ids = set([id for id, _ in found_in_companies] + [id for id, _ in found_in_others])
missing = len(ids_to_check) - len(found_ids)
if missing > 0:
    missing_ids = set(ids_to_check) - found_ids
    print(f"Saknas i båda databaserna: {missing}")
    print(f"Saknade ID:n: {sorted(list(missing_ids))[:20]}...")
print(f"{'='*80}\n")

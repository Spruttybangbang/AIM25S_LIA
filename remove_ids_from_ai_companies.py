#!/usr/bin/env python3
"""
Ta bort specifika ID:n från ai_companies.db (finns redan i ai_others.db)
"""
import sqlite3

ids_to_remove = [
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

def delete_from_ai_companies(ids):
    """Ta bort företag och all relaterad data från ai_companies.db"""
    conn = sqlite3.connect('databases/ai_companies.db')
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(ids))

    print("="*80)
    print("TA BORT FÖRETAG FRÅN ai_companies.db")
    print("="*80)
    print(f"\nAntal ID:n att ta bort: {len(ids)}")

    # Visa några exempel
    cursor.execute(f"SELECT id, name FROM companies WHERE id IN ({placeholders}) ORDER BY id LIMIT 10", ids)
    examples = cursor.fetchall()
    print("\nExempel på företag som tas bort:")
    for company_id, name in examples:
        print(f"  ID {company_id:4d}: {name}")
    print("  ...")

    # Ta bort från relaterade tabeller
    print(f"\n{'-'*80}")
    print("Tar bort relaterad data...")
    print(f"{'-'*80}")

    cursor.execute(f"DELETE FROM company_sectors WHERE company_id IN ({placeholders})", ids)
    print(f"  ✓ Raderade {cursor.rowcount} sector associations")

    cursor.execute(f"DELETE FROM company_domains WHERE company_id IN ({placeholders})", ids)
    print(f"  ✓ Raderade {cursor.rowcount} domain associations")

    cursor.execute(f"DELETE FROM company_ai_capabilities WHERE company_id IN ({placeholders})", ids)
    print(f"  ✓ Raderade {cursor.rowcount} AI capability associations")

    cursor.execute(f"DELETE FROM company_dimensions WHERE company_id IN ({placeholders})", ids)
    print(f"  ✓ Raderade {cursor.rowcount} dimension associations")

    cursor.execute(f"DELETE FROM scb_matches WHERE company_id IN ({placeholders})", ids)
    print(f"  ✓ Raderade {cursor.rowcount} SCB matches")

    cursor.execute(f"DELETE FROM scb_enrichment WHERE company_id IN ({placeholders})", ids)
    print(f"  ✓ Raderade {cursor.rowcount} SCB enrichment records")

    # Ta bort företagen
    print(f"\n{'-'*80}")
    print("Tar bort företag...")
    print(f"{'-'*80}")

    cursor.execute(f"DELETE FROM companies WHERE id IN ({placeholders})", ids)
    deleted = cursor.rowcount
    print(f"  ✓ Raderade {deleted} företag")

    # Commit
    conn.commit()

    # Verifiera
    cursor.execute("SELECT COUNT(*) FROM companies")
    remaining = cursor.fetchone()[0]

    print(f"\n{'='*80}")
    print("KLART!")
    print(f"{'='*80}")
    print(f"Företag raderade: {deleted}")
    print(f"Kvarvarande företag i ai_companies.db: {remaining}")
    print(f"{'='*80}\n")

    conn.close()

if __name__ == '__main__':
    delete_from_ai_companies(ids_to_remove)

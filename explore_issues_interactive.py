#!/usr/bin/env python3
"""
Interaktivt script för att utforska misslyckade matchningar
Använd detta i en Python REPL eller Jupyter Notebook
"""

import pandas as pd
import sqlite3

# Ladda all data
print("Laddar data...")
issues_df = pd.read_csv('scb_issues.csv')
low_score_df = pd.read_csv('analysis_low_scores.csv')
no_candidates_df = pd.read_csv('analysis_no_candidates.csv')

# Anslut till databasen
conn = sqlite3.connect('ai_companies.db')

print(f"""
✅ Data inladdad!

Tillgängliga dataframes:
  • issues_df         - Alla {len(issues_df)} misslyckade matchningar
  • low_score_df      - {len(low_score_df)} matchningar med låg poäng (sorterade)
  • no_candidates_df  - {len(no_candidates_df)} företag utan kandidater

Användbara funktioner:
""")

def show_high_score_matches(min_score=85):
    """Visa matchningar över en viss poäng"""
    matches = low_score_df[low_score_df['score'] >= min_score]
    print(f"\n🎯 Matchningar med poäng ≥ {min_score}: {len(matches)} st\n")
    for idx, row in matches.iterrows():
        print(f"{row['name']}")
        print(f"  Score: {row['score']} | Kandidat: {row['best_candidate']} | Ort: {row['PostOrt']}")
    return matches

def search_company(search_term):
    """Sök efter ett företag i issues"""
    results = issues_df[issues_df['name'].str.contains(search_term, case=False, na=False)]
    print(f"\n🔍 Hittade {len(results)} resultat för '{search_term}':\n")
    for idx, row in results.iterrows():
        print(f"{row['name']} (ID: {row['id']})")
        print(f"  Anledning: {row['reason']}")
        if pd.notna(row['score']):
            print(f"  Score: {row['score']}")
            print(f"  Bästa kandidat: {row['best_candidate']} ({row['PostOrt']})")
    return results

def get_company_info(company_id):
    """Hämta fullständig info om ett företag från databasen"""
    query = f"""
    SELECT *
    FROM companies
    WHERE id = {company_id}
    """
    result = pd.read_sql_query(query, conn)
    if len(result) > 0:
        print(f"\n📋 Information om företag ID {company_id}:\n")
        for col in result.columns:
            val = result.iloc[0][col]
            if pd.notna(val) and val != '':
                print(f"  {col}: {val}")
    else:
        print(f"⚠️  Inget företag hittat med ID {company_id}")
    return result

def analyze_name_similarity(company_name, candidate_name):
    """Jämför två företagsnamn"""
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, company_name.lower(), candidate_name.lower()).ratio()
    print(f"\nNamnlikhet mellan:")
    print(f"  '{company_name}'")
    print(f"  '{candidate_name}'")
    print(f"  → {ratio*100:.1f}%")
    return ratio

def show_stats_by_score_range():
    """Visa statistik uppdelat i poängintervall"""
    print("\n📊 Fördelning av low_score matchningar:\n")
    ranges = [
        (89, 100, "Mycket bra"),
        (85, 88, "Bra"),
        (80, 84, "OK"),
        (0, 79, "Tveksam")
    ]
    for min_s, max_s, label in ranges:
        count = len(low_score_df[(low_score_df['score'] >= min_s) &
                                  (low_score_df['score'] <= max_s)])
        if count > 0:
            print(f"  {min_s}-{max_s} ({label:12s}): {count:3d} st")

def find_swedish_companies_in_no_candidates():
    """Hitta svenska företag bland no_candidates som kanske borde matchas"""
    # Merge med företagsinformation
    conn_temp = sqlite3.connect('ai_companies.db')
    companies = pd.read_sql_query("SELECT id, name, website FROM companies", conn_temp)
    conn_temp.close()

    merged = no_candidates_df.merge(companies, left_on='id', right_on='id', how='left')

    # Filtrera bort kända utländska företag
    foreign_keywords = ['google', 'meta', 'nvidia', 'amd', 'deepmind', 'microsoft',
                       'amazon', 'openai', 'anthropic', 'hugging face', 'stability ai']

    def is_likely_swedish(row):
        name = str(row['name_x']).lower()
        return not any(keyword in name for keyword in foreign_keywords)

    swedish = merged[merged.apply(is_likely_swedish, axis=1)]
    print(f"\n🇸🇪 Potentiellt svenska företag utan kandidater: {len(swedish)} st")
    print("\nTopp 20:")
    for idx, row in swedish.head(20).iterrows():
        print(f"  • {row['name_x']} (ID: {row['id']})")

    return swedish

# Exempel på användning
print("""
Exempel:

  # Visa alla matchningar med hög poäng (≥85)
  show_high_score_matches(85)

  # Sök efter ett företag
  search_company('volvo')

  # Få info om ett specifikt företag (använd ID från issues)
  get_company_info(1322)

  # Jämför namnlikhet
  analyze_name_similarity('Volvo Group', 'VOLVO GROUP MEXICO')

  # Visa statistik
  show_stats_by_score_range()

  # Hitta svenska företag
  find_swedish_companies_in_no_candidates()

  # Filtrera dataframes
  high_confidence = low_score_df[low_score_df['score'] >= 88]
  stockholm_companies = low_score_df[low_score_df['PostOrt'] == 'STOCKHOLM']
""")

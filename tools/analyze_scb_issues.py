#!/usr/bin/env python3
"""
Analysscript för SCB-matchningar
Detta script analyserar misslyckade matchningar från SCB API och hjälper till att
identifiera potentiella matchningar bland de som inte lyckats automatiskt.
"""

import pandas as pd
import sqlite3
from collections import Counter

def load_data():
    """Laddar alla relevanta data"""
    print("📊 Laddar data...\n")

    # Ladda issues
    issues_df = pd.read_csv('scb_issues.csv')

    # Ladda lyckade matchningar för jämförelse
    matches_df = pd.read_csv('scb_matches.csv', nrows=100)  # Bara för att se strukturen

    # Ladda företagsinformation från databasen
    conn = sqlite3.connect('../ai_companies.db')
    companies_df = pd.read_sql_query("""
        SELECT id, name, website, location_city, location_country
        FROM companies
    """, conn)
    conn.close()

    return issues_df, matches_df, companies_df

def analyze_issues(issues_df):
    """Analyserar de misslyckade matchningarna"""
    print("=" * 80)
    print("🔍 ÖVERGRIPANDE ANALYS AV MISSLYCKADE MATCHNINGAR")
    print("=" * 80)

    total_issues = len(issues_df)
    print(f"\n📈 Totalt antal misslyckade matchningar: {total_issues}")

    # Analys per anledning
    print("\n📊 Fördelning per anledning:")
    reason_counts = issues_df['reason'].value_counts()
    for reason, count in reason_counts.items():
        percentage = (count / total_issues) * 100
        print(f"  • {reason}: {count} st ({percentage:.1f}%)")

    return reason_counts

def analyze_low_scores(issues_df):
    """Analyserar företag med låga matchningspoäng"""
    low_score_df = issues_df[issues_df['reason'] == 'low_score'].copy()

    if len(low_score_df) == 0:
        print("\n⚠️  Inga företag med low_score hittades")
        return low_score_df

    print("\n" + "=" * 80)
    print("🎯 ANALYS AV LOW SCORE MATCHNINGAR (potentiella kandidater!)")
    print("=" * 80)

    print(f"\nTotalt: {len(low_score_df)} företag")

    # Statistik om poäng
    print(f"\n📊 Poängstatistik:")
    print(f"  • Medel: {low_score_df['score'].mean():.1f}")
    print(f"  • Median: {low_score_df['score'].median():.0f}")
    print(f"  • Min: {low_score_df['score'].min()}")
    print(f"  • Max: {low_score_df['score'].max()}")

    # Gruppera efter poäng
    print(f"\n📈 Fördelning efter poäng:")
    score_ranges = [
        (89, 100, "89-100 (mycket bra)"),
        (85, 88, "85-88 (bra)"),
        (80, 84, "80-84 (OK)")
    ]

    for min_score, max_score, label in score_ranges:
        count = len(low_score_df[(low_score_df['score'] >= min_score) &
                                  (low_score_df['score'] <= max_score)])
        if count > 0:
            print(f"  • {label}: {count} st")

    # Topplista med högst poäng
    print(f"\n🏆 TOPP 20 MED HÖGST MATCHNINGSPOÄNG:")
    print("-" * 80)
    top_scores = low_score_df.nlargest(20, 'score')[
        ['name', 'score', 'best_candidate', 'PostOrt']
    ]

    for idx, row in top_scores.iterrows():
        print(f"\n{row['name']}")
        print(f"  ├─ Poäng: {row['score']}")
        print(f"  ├─ SCB-kandidat: {row['best_candidate']}")
        print(f"  └─ Ort: {row['PostOrt']}")

    return low_score_df

def analyze_no_candidates(issues_df, companies_df):
    """Analyserar företag utan kandidater"""
    no_candidates_df = issues_df[issues_df['reason'] == 'no_candidates'].copy()

    if len(no_candidates_df) == 0:
        print("\n⚠️  Inga företag med no_candidates hittades")
        return no_candidates_df

    print("\n" + "=" * 80)
    print("❌ ANALYS AV FÖRETAG UTAN KANDIDATER")
    print("=" * 80)

    print(f"\nTotalt: {len(no_candidates_df)} företag")

    # Merge med företagsinformation
    no_candidates_with_info = no_candidates_df.merge(
        companies_df, left_on='id', right_on='id', how='left'
    )

    # Analysera namnen
    print(f"\n🔤 NAMNANALYS:")

    # Kategorisera baserat på namnmönster
    utländska = []
    kortnamn = []
    specialtecken = []
    akronymer = []
    normalnamn = []

    for _, row in no_candidates_with_info.iterrows():
        name = row['name_x']

        # Utländska företag
        if any(keyword in name.lower() for keyword in ['google', 'meta', 'nvidia', 'amd', 'deepmind', 'microsoft', 'amazon']):
            utländska.append(name)
        # Kortnamn eller akronymer
        elif len(name) <= 4 or (name.isupper() and len(name) <= 6):
            akronymer.append(name)
        # Specialtecken i namnet
        elif any(char in name for char in ['.', '-', '_']) or name.islower():
            specialtecken.append(name)
        # Väldigt korta namn
        elif len(name.replace(' ', '')) <= 5:
            kortnamn.append(name)
        else:
            normalnamn.append(name)

    print(f"  • Utländska företag: {len(utländska)} st")
    if utländska[:5]:
        print(f"    Exempel: {', '.join(utländska[:5])}")

    print(f"  • Akronymer/kortnamn: {len(akronymer)} st")
    if akronymer[:5]:
        print(f"    Exempel: {', '.join(akronymer[:5])}")

    print(f"  • Namn med specialtecken: {len(specialtecken)} st")
    if specialtecken[:5]:
        print(f"    Exempel: {', '.join(specialtecken[:5])}")

    print(f"  • Mycket korta namn: {len(kortnamn)} st")
    if kortnamn[:5]:
        print(f"    Exempel: {', '.join(kortnamn[:5])}")

    print(f"  • Normalnamn: {len(normalnamn)} st")

    # Lista alla normalnamn som kanske borde ha matchats
    if normalnamn:
        print(f"\n📋 NORMALNAMN SOM KANSKE BORDE MATCHAS:")
        print(f"    (Dessa kan vara värda att undersöka manuellt)")
        for name in sorted(normalnamn):
            print(f"    • {name}")

    return no_candidates_with_info

def generate_recommendations(low_score_df, no_candidates_df):
    """Genererar rekommendationer baserat på analysen"""
    print("\n" + "=" * 80)
    print("💡 REKOMMENDATIONER")
    print("=" * 80)

    print("\n1. LOW SCORE MATCHNINGAR:")
    high_score_count = len(low_score_df[low_score_df['score'] >= 85])
    if high_score_count > 0:
        print(f"   ✅ Det finns {high_score_count} företag med poäng ≥ 85")
        print(f"      Dessa är troligen korrekta matchningar!")
        print(f"      Rekommendation: Godkänn dessa manuellt")

    medium_score_count = len(low_score_df[(low_score_df['score'] >= 80) &
                                          (low_score_df['score'] < 85)])
    if medium_score_count > 0:
        print(f"   ⚠️  Det finns {medium_score_count} företag med poäng 80-84")
        print(f"      Dessa behöver manuell granskning")

    print("\n2. NO CANDIDATES:")
    print(f"   📊 {len(no_candidates_df)} företag hittades inte alls")
    print(f"   💡 Möjliga orsaker:")
    print(f"      • Utländska företag (ej registrerade i SCB)")
    print(f"      • Fel företagsnamn eller stavfel i databasen")
    print(f"      • Företag som bytt namn")
    print(f"      • Startups som inte registrerats ännu")
    print(f"      • Underleverantörer eller dotterbolag")

    print("\n3. NÄSTA STEG:")
    print(f"   📝 Skapa ett script för att:")
    print(f"      a) Automatiskt godkänna matchningar med poäng ≥ 85")
    print(f"      b) Granska poäng 80-84 manuellt")
    print(f"      c) Söka manuellt efter företag utan kandidater")
    print(f"      d) Kolla om företag har alternativa namn i Bolagsverket")

def export_dataframes(low_score_df, no_candidates_df):
    """Exporterar separata dataframes för vidare analys"""
    print("\n" + "=" * 80)
    print("💾 EXPORT AV DATA")
    print("=" * 80)

    # Sortera low_score efter poäng
    low_score_sorted = low_score_df.sort_values('score', ascending=False)

    # Exportera till CSV
    low_score_sorted.to_csv('analysis_low_scores.csv', index=False)
    print(f"\n✅ Exporterade low_score matchningar till: analysis_low_scores../results/.csv")

    no_candidates_df.to_csv('analysis_no_candidates.csv', index=False)
    print(f"✅ Exporterade no_candidates till: analysis_no_candidates../results/.csv")

    # Skapa en sammanfattning
    summary = {
        'Kategori': ['Low Score (>=85)', 'Low Score (80-84)', 'Low Score (<80)',
                     'No Candidates', 'Totalt'],
        'Antal': [
            len(low_score_df[low_score_df['score'] >= 85]),
            len(low_score_df[(low_score_df['score'] >= 80) & (low_score_df['score'] < 85)]),
            len(low_score_df[low_score_df['score'] < 80]),
            len(no_candidates_df),
            len(low_score_df) + len(no_candidates_df)
        ]
    }
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv('analysis_summary.csv', index=False)
    print(f"✅ Exporterade sammanfattning till: analysis_summary../results/.csv")

    return low_score_sorted, no_candidates_df

def main():
    """Huvudfunktion"""
    print("\n" + "=" * 80)
    print("🤖 SCB MATCHNINGS-ANALYS")
    print("=" * 80)
    print("\nAnalyserar misslyckade matchningar från SCB API...")

    # Ladda data
    issues_df, matches_df, companies_df = load_data()

    # Övergripande analys
    analyze_issues(issues_df)

    # Analys av low scores
    low_score_df = analyze_low_scores(issues_df)

    # Analys av no candidates
    no_candidates_with_info = analyze_no_candidates(issues_df, companies_df)

    # Rekommendationer
    generate_recommendations(low_score_df, no_candidates_with_info)

    # Export
    low_score_sorted, no_candidates_df = export_dataframes(low_score_df, no_candidates_with_info)

    print("\n" + "=" * 80)
    print("✅ ANALYS KLAR!")
    print("=" * 80)
    print("\nDu har nu följande dataframes tillgängliga i Python:")
    print("  • issues_df - Alla misslyckade matchningar")
    print("  • low_score_df - Matchningar med låg poäng")
    print("  • no_candidates_df - Företag utan kandidater")
    print("\nExporterade filer:")
    print("  • analysis_low_scores../results/.csv")
    print("  • analysis_no_candidates../results/.csv")
    print("  • analysis_summary../results/.csv")

    return issues_df, low_score_sorted, no_candidates_with_info

if __name__ == "__main__":
    issues_df, low_score_df, no_candidates_df = main()

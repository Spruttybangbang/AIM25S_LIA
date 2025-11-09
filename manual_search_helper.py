#!/usr/bin/env python3
"""
Hjälpverktyg för manuell sökning av företag i SCB
Visar företag ett i taget med sökförslag och låter dig mata in resultatet
"""

import pandas as pd
import sqlite3
import json
from datetime import datetime
import sys

def load_companies_to_search():
    """Laddar företag att söka efter"""
    # Ladda need_review (136 företag)
    need_review = pd.read_csv('no_candidates_need_review.csv')

    # Sortera på namn för bättre översikt
    need_review = need_review.sort_values('name')

    return need_review

def get_company_details(company_id):
    """Hämtar detaljer om företag från databasen"""
    conn = sqlite3.connect('ai_companies.db')
    query = f"""
    SELECT id, name, website, description, location_city, type, maturity
    FROM companies
    WHERE id = {company_id}
    """
    result = pd.read_sql_query(query, conn)
    conn.close()
    return result.iloc[0] if len(result) > 0 else None

def show_company_card(row):
    """Visar företagskort med information"""
    print("\n" + "="*80)
    print(f"🏢 FÖRETAG: {row['name']}")
    print("="*80)

    # Hämta detaljer från databasen
    details = get_company_details(row['id'])

    if details is not None:
        if pd.notna(details.get('website')):
            print(f"🌐 Webbplats: {details['website']}")
        if pd.notna(details.get('description')) and details['description']:
            desc = details['description']
            if len(desc) > 200:
                desc = desc[:200] + "..."
            print(f"📝 Beskrivning: {desc}")
        if pd.notna(details.get('type')):
            print(f"🏷️  Typ: {details['type']}")
        if pd.notna(details.get('maturity')):
            print(f"📊 Mognad: {details['maturity']}")

    print(f"\n💡 SÖKFÖRSLAG FÖR SCB:")
    print("-" * 80)

    # Visa sökvariant efter sökvariant
    variants = eval(row['search_variants']) if isinstance(row['search_variants'], str) else row['search_variants']
    for i, variant in enumerate(variants[:5], 1):
        print(f"  {i}. {variant}")

    if len(variants) > 5:
        print(f"  ... och {len(variants) - 5} fler varianter")

    print()

def search_interactive(companies_df):
    """Interaktiv sökning genom företag"""
    print("\n" + "="*80)
    print("🔍 MANUELL SCB-SÖKNING")
    print("="*80)
    print(f"\nAntal företag att söka efter: {len(companies_df)}")
    print("\nInstruktioner:")
    print("  1. För varje företag, kopiera sökförslagen och sök i SCB")
    print("  2. Om du hittar en matchning, mata in informationen")
    print("  3. Om ingen matchning: tryck 'n'")
    print("  4. För att skippa: tryck 's'")
    print("  5. För att avsluta: tryck 'q'")

    results = []
    skipped = []
    not_found = []

    start_from = 0
    if len(companies_df) > 10:
        choice = input(f"\nVill du börja från början eller hoppa över några? (Enter = börja från 0, eller ange nummer): ").strip()
        if choice.isdigit():
            start_from = int(choice)

    for idx, row in companies_df.iloc[start_from:].iterrows():
        show_company_card(row)

        while True:
            action = input("Hittade du en matchning? (y/n/s/q/i): ").lower().strip()

            if action == 'y':
                # Användaren hittade en matchning
                print("\n📝 MATA IN MATCHNINGSINFORMATION:")
                print("-" * 80)

                scb_name = input("SCB företagsnamn: ").strip()
                if not scb_name:
                    print("❌ Du måste ange företagsnamn")
                    continue

                city = input("Ort (valfritt): ").strip()
                org_nr = input("Organisationsnummer (valfritt): ").strip()
                score = input("Hur säker är du? (1-100, Enter för 100): ").strip()
                score = int(score) if score.isdigit() else 100
                comment = input("Kommentar (valfritt): ").strip()

                results.append({
                    'company_id': row['id'],
                    'company_name': row['name'],
                    'scb_name': scb_name,
                    'city': city if city else None,
                    'org_nummer': org_nr if org_nr else None,
                    'score': score,
                    'comment': comment if comment else None,
                    'found_at': datetime.now().isoformat(),
                    'method': 'manual_search'
                })

                print(f"✅ Matchning sparad!")
                break

            elif action == 'n':
                not_found.append({
                    'company_id': row['id'],
                    'company_name': row['name'],
                    'searched_at': datetime.now().isoformat()
                })
                print("❌ Ingen matchning")
                break

            elif action == 's':
                skipped.append({
                    'company_id': row['id'],
                    'company_name': row['name']
                })
                print("⏭️  Skippad")
                break

            elif action == 'q':
                print("\n🛑 Avslutar sökning...")
                return results, skipped, not_found

            elif action == 'i':
                # Visa webbplatsen om den finns
                details = get_company_details(row['id'])
                if details is not None and pd.notna(details.get('website')):
                    print(f"\n🌐 Öppna: {details['website']}")
                else:
                    print("\n⚠️  Ingen webbplats registrerad")
            else:
                print("Ogiltigt val, försök igen")

        # Visa progress
        current = idx - start_from + 1
        total = len(companies_df) - start_from
        print(f"\n📊 Progress: {current}/{total} ({len(results)} hittade, {len(not_found)} ej hittade, {len(skipped)} skippade)")

    return results, skipped, not_found

def save_results(results, skipped, not_found):
    """Sparar resultat till filer"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print("\n" + "="*80)
    print("💾 SPARAR RESULTAT")
    print("="*80)

    if results:
        results_df = pd.DataFrame(results)
        filename = f'manual_search_found_{timestamp}.csv'
        results_df.to_csv(filename, index=False)
        print(f"\n✅ Hittade matchningar: {filename}")
        print(f"   {len(results)} st matchningar")

        # Visa sammanfattning
        print(f"\n   Fördelning per ort:")
        if 'city' in results_df.columns:
            city_counts = results_df['city'].value_counts().head(5)
            for city, count in city_counts.items():
                if pd.notna(city):
                    print(f"     • {city}: {count} st")

    if not_found:
        not_found_df = pd.DataFrame(not_found)
        filename = f'manual_search_not_found_{timestamp}.csv'
        not_found_df.to_csv(filename, index=False)
        print(f"\n❌ Ej hittade: {filename}")
        print(f"   {len(not_found)} st företag")

    if skipped:
        skipped_df = pd.DataFrame(skipped)
        filename = f'manual_search_skipped_{timestamp}.csv'
        skipped_df.to_csv(filename, index=False)
        print(f"\n⏭️  Skippade: {filename}")
        print(f"   {len(skipped)} st företag")

    # Skapa importerbart format för databasen
    if results:
        print(f"\n💡 Nästa steg:")
        print(f"   Använd 'manual_search_found_{timestamp}.csv' för att:")
        print(f"   1. Importera till databasen")
        print(f"   2. Uppdatera location_city för företagen")

def show_statistics(companies_df):
    """Visar statistik innan sökning"""
    print("\n" + "="*80)
    print("📊 STATISTIK")
    print("="*80)

    print(f"\nTotalt antal företag: {len(companies_df)}")

    # Analysera namnlängder
    name_lengths = companies_df['name'].str.len()
    print(f"\nNamnlängd:")
    print(f"  • Medel: {name_lengths.mean():.1f} tecken")
    print(f"  • Kortaste: {name_lengths.min()} tecken - {companies_df.loc[name_lengths.idxmin(), 'name']}")
    print(f"  • Längsta: {name_lengths.max()} tecken - {companies_df.loc[name_lengths.idxmax(), 'name'][:50]}...")

    # Företag med AB i namnet
    has_ab = companies_df['name'].str.contains(' AB', case=False, na=False).sum()
    print(f"\nFöretag med 'AB' i namnet: {has_ab} st ({has_ab/len(companies_df)*100:.1f}%)")

def filter_companies(companies_df):
    """Låt användaren filtrera vilka företag att söka efter"""
    print("\n" + "="*80)
    print("🎯 FILTRERA FÖRETAG")
    print("="*80)

    print("\nVilka företag vill du söka efter?")
    print("  1. Alla 136 företag")
    print("  2. Endast företag med 'AB' i namnet")
    print("  3. Endast kortnamn (≤15 tecken)")
    print("  4. De första 20 företagen (för test)")
    print("  5. Företag 20-50")

    choice = input("\nVal (1-5): ").strip()

    if choice == '2':
        filtered = companies_df[companies_df['name'].str.contains(' AB', case=False, na=False)]
        print(f"\n✅ Filtrerat till {len(filtered)} företag med 'AB' i namnet")
        return filtered
    elif choice == '3':
        filtered = companies_df[companies_df['name'].str.len() <= 15]
        print(f"\n✅ Filtrerat till {len(filtered)} företag med kort namn")
        return filtered
    elif choice == '4':
        filtered = companies_df.head(20)
        print(f"\n✅ De första 20 företagen")
        return filtered
    elif choice == '5':
        filtered = companies_df.iloc[20:50]
        print(f"\n✅ Företag 20-50")
        return filtered
    else:
        print(f"\n✅ Alla {len(companies_df)} företag")
        return companies_df

def main():
    print("\n" + "="*80)
    print("🔎 MANUELL SCB-SÖK ASSISTENT")
    print("="*80)

    # Ladda företag
    companies_df = load_companies_to_search()

    # Visa statistik
    show_statistics(companies_df)

    # Låt användaren filtrera
    filtered_df = filter_companies(companies_df)

    # Starta interaktiv sökning
    results, skipped, not_found = search_interactive(filtered_df)

    # Spara resultat
    if results or skipped or not_found:
        save_results(results, skipped, not_found)

    # Sammanfattning
    print("\n" + "="*80)
    print("📊 SAMMANFATTNING")
    print("="*80)
    print(f"✅ Hittade matchningar: {len(results)}")
    print(f"❌ Ej hittade: {len(not_found)}")
    print(f"⏭️  Skippade: {len(skipped)}")
    print("\n✅ Klart!")

if __name__ == "__main__":
    main()

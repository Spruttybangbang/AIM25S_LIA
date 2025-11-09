#!/usr/bin/env python3
"""
Script för att godkänna och lägga till bra matchningar från low_score till databasen

Detta script:
1. Identifierar matchningar över en viss poäng-tröskel
2. Visar dem för manuell granskning
3. Lägger till godkända matchningar i databasen
"""

import pandas as pd
import sqlite3
import json
from datetime import datetime

def load_data():
    """Laddar data och ansluter till databasen"""
    low_score_df = pd.read_csv('analysis_low_scores.csv')
    conn = sqlite3.connect('ai_companies.db')
    return low_score_df, conn

def get_high_confidence_matches(df, min_score=85):
    """Hämtar matchningar över en viss poäng"""
    return df[df['score'] >= min_score].copy()

def show_match_details(row):
    """Visar detaljer om en matchning"""
    print(f"\n{'='*80}")
    print(f"Företag: {row['name']}")
    print(f"ID: {row['id']}")
    print(f"Score: {row['score']}")
    print(f"SCB-kandidat: {row['best_candidate']}")
    print(f"Ort: {row['PostOrt']}")
    print(f"{'='*80}")

def review_matches(matches_df, conn):
    """Interaktiv granskning av matchningar"""
    print(f"\n🎯 Granskar {len(matches_df)} matchningar med hög poäng\n")

    approved = []
    rejected = []
    skipped = []
    manual_matches = []

    for idx, row in matches_df.iterrows():
        show_match_details(row)

        while True:
            choice = input("\nGodkänn? (y=ja, n=nej, m=manuell matchning, s=skippa, i=info, q=avsluta): ").lower().strip()

            if choice == 'y':
                approved.append(row)
                print("✅ Godkänd!")
                break
            elif choice == 'n':
                rejected.append(row)
                print("❌ Nekad")
                break
            elif choice == 'm':
                # Manuell matchning - användaren har hittat rätt företag själv
                print("\n📝 MANUELL MATCHNING")
                print("Ange information om det rätta företaget:")
                print("-" * 80)

                manual_info = {
                    'original_id': row['id'],
                    'original_name': row['name'],
                    'suggested_candidate': row['best_candidate'],
                    'suggested_score': row['score'],
                    'suggested_ort': row['PostOrt']
                }

                # Samla in information
                correct_name = input("Rätt företagsnamn (SCB): ").strip()
                if correct_name:
                    manual_info['correct_scb_name'] = correct_name

                website = input("Hemsida (valfritt): ").strip()
                if website:
                    manual_info['website'] = website

                org_nr = input("Organisationsnummer (valfritt): ").strip()
                if org_nr:
                    manual_info['org_nummer'] = org_nr

                city = input("Ort (valfritt): ").strip()
                if city:
                    manual_info['city'] = city

                comment = input("Kommentar/anteckningar (valfritt): ").strip()
                if comment:
                    manual_info['comment'] = comment

                manual_info['added_at'] = datetime.now().isoformat()

                manual_matches.append(manual_info)
                print("✍️  Manuell matchning sparad!")
                break
            elif choice == 's':
                skipped.append(row)
                print("⏭️  Skippad")
                break
            elif choice == 'i':
                # Visa mer info från databasen
                company_info = pd.read_sql_query(
                    f"SELECT * FROM companies WHERE id = {row['id']}", conn
                )
                print("\n📋 Fullständig företagsinformation:")
                for col in ['name', 'website', 'location_city', 'description']:
                    if col in company_info.columns:
                        val = company_info.iloc[0][col]
                        if pd.notna(val):
                            print(f"  {col}: {val}")
            elif choice == 'q':
                print("\n🛑 Avbryter granskning...")
                return approved, rejected, skipped, manual_matches
            else:
                print("Ogiltigt val, försök igen")

    return approved, rejected, skipped, manual_matches

def auto_approve_high_confidence(matches_df, threshold=89):
    """Automatiskt godkänn matchningar över en viss tröskel"""
    auto_approved = matches_df[matches_df['score'] >= threshold]
    manual_review = matches_df[matches_df['score'] < threshold]

    print(f"\n🤖 AUTO-GODKÄNNANDE (score ≥ {threshold})")
    print(f"Automatiskt godkända: {len(auto_approved)} st")
    print(f"Kräver manuell granskning: {len(manual_review)} st\n")

    if len(auto_approved) > 0:
        print("Automatiskt godkända matchningar:")
        for idx, row in auto_approved.iterrows():
            print(f"  ✅ {row['name']} → {row['best_candidate']} (Score: {row['score']})")

    return auto_approved.to_dict('records'), manual_review

def add_matches_to_database(approved_matches, conn, dry_run=True):
    """Lägger till godkända matchningar i databasen"""
    if len(approved_matches) == 0:
        print("\n⚠️  Inga matchningar att lägga till")
        return

    print(f"\n{'='*80}")
    print(f"💾 LÄGGER TILL {len(approved_matches)} MATCHNINGAR I DATABASEN")
    print(f"{'='*80}")

    if dry_run:
        print("\n⚠️  DRY RUN MODE - Inga ändringar kommer att sparas!\n")

    cursor = conn.cursor()
    added_count = 0
    error_count = 0

    for match in approved_matches:
        try:
            company_id = int(match['id'])
            score = int(match['score'])
            city = str(match['PostOrt']) if pd.notna(match['PostOrt']) else None
            best_candidate = str(match['best_candidate']) if pd.notna(match['best_candidate']) else None

            # Skapa payload med matchningsinformation
            payload = json.dumps({
                'scb_name': best_candidate,
                'original_name': match['name'],
                'match_score': score,
                'approved_by': 'manual_review',
                'approved_at': datetime.now().isoformat()
            })

            # Kolla om matchning redan finns
            cursor.execute("""
                SELECT id FROM scb_matches
                WHERE company_id = ?
            """, (company_id,))

            existing = cursor.fetchone()

            if existing:
                print(f"  ⚠️  {match['name']} (ID: {company_id}) - Matchning finns redan")
                continue

            if not dry_run:
                # Lägg till i scb_matches
                cursor.execute("""
                    INSERT INTO scb_matches (company_id, matched, score, city, payload)
                    VALUES (?, 1, ?, ?, ?)
                """, (company_id, score, city, payload))

                # Uppdatera location_city i companies om den inte finns
                if city and city != 'UTLANDET':
                    cursor.execute("""
                        UPDATE companies
                        SET location_city = ?
                        WHERE id = ? AND (location_city IS NULL OR location_city = '')
                    """, (city, company_id))

            print(f"  ✅ {match['name']} → {best_candidate} (Ort: {city})")
            added_count += 1

        except Exception as e:
            print(f"  ❌ Fel vid {match.get('name', 'okänt företag')}: {str(e)}")
            error_count += 1

    if not dry_run:
        conn.commit()
        print(f"\n✅ Lagt till {added_count} matchningar i databasen")
    else:
        print(f"\n📋 Skulle ha lagt till {added_count} matchningar (DRY RUN)")

    if error_count > 0:
        print(f"⚠️  {error_count} fel uppstod")

    return added_count, error_count

def save_review_results(approved, rejected, skipped, manual_matches):
    """Sparar granskningsresultat till filer"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if approved:
        pd.DataFrame(approved).to_csv(f'approved_matches_{timestamp}.csv', index=False)
        print(f"💾 Godkända matchningar sparade till: approved_matches_{timestamp}.csv")

    if rejected:
        pd.DataFrame(rejected).to_csv(f'rejected_matches_{timestamp}.csv', index=False)
        print(f"💾 Nekade matchningar sparade till: rejected_matches_{timestamp}.csv")

    if skipped:
        pd.DataFrame(skipped).to_csv(f'skipped_matches_{timestamp}.csv', index=False)
        print(f"💾 Skippade matchningar sparade till: skipped_matches_{timestamp}.csv")

    if manual_matches:
        pd.DataFrame(manual_matches).to_csv(f'manual_matches_{timestamp}.csv', index=False)
        print(f"💾 Manuella matchningar sparade till: manual_matches_{timestamp}.csv")
        print(f"    → Dessa kan användas för manuell uppföljning och sökning i SCB")

def main():
    """Huvudfunktion"""
    print("\n" + "="*80)
    print("🔍 GODKÄNNANDE AV SCB-MATCHNINGAR")
    print("="*80)

    # Ladda data
    low_score_df, conn = load_data()

    # Välj vilka matchningar att granska
    print("\n📊 Tillgängliga matchningar:")
    print(f"  • Totalt: {len(low_score_df)} st")
    print(f"  • Score ≥ 85: {len(low_score_df[low_score_df['score'] >= 85])} st")
    print(f"  • Score 80-84: {len(low_score_df[(low_score_df['score'] >= 80) & (low_score_df['score'] < 85)])} st")
    print(f"  • Score < 80: {len(low_score_df[low_score_df['score'] < 80])} st")

    print("\nVilka matchningar vill du granska?")
    print("  1. Endast score ≥ 85 (15 st - rekommenderat)")
    print("  2. Alla 31 matchningar")
    print("  3. Score ≥ 80 (23 st)")

    filter_choice = input("\nVal (1-3): ").strip()

    if filter_choice == '1':
        min_score = 85
        high_confidence_df = get_high_confidence_matches(low_score_df, min_score)
    elif filter_choice == '2':
        high_confidence_df = low_score_df.copy()
    elif filter_choice == '3':
        high_confidence_df = low_score_df[low_score_df['score'] >= 80].copy()
    else:
        print("❌ Ogiltigt val")
        conn.close()
        return

    print(f"\n📊 Granskar {len(high_confidence_df)} matchningar")

    # Välj metod
    print("\nVälj granskningsmetod:")
    print("  1. Auto-godkänn score ≥ 89, granska resten manuellt")
    print("  2. Granska alla manuellt")
    print("  3. Auto-godkänn alla ≥ 85 (ej rekommenderat)")
    print("  4. Endast visa lista, inga ändringar")

    choice = input("\nVal (1-4): ").strip()

    approved = []
    rejected = []
    skipped = []
    manual_matches = []

    if choice == '1':
        auto_approved, manual_review = auto_approve_high_confidence(high_confidence_df, threshold=89)
        approved.extend(auto_approved)

        if len(manual_review) > 0:
            print(f"\n📋 Granska {len(manual_review)} matchningar manuellt:")
            manual_approved, manual_rejected, manual_skipped, manual_manual = review_matches(manual_review, conn)
            approved.extend([m.to_dict() for m in manual_approved])
            rejected.extend([m.to_dict() for m in manual_rejected])
            skipped.extend([m.to_dict() for m in manual_skipped])
            manual_matches.extend(manual_manual)

    elif choice == '2':
        manual_approved, manual_rejected, manual_skipped, manual_manual = review_matches(high_confidence_df, conn)
        approved.extend([m.to_dict() for m in manual_approved])
        rejected.extend([m.to_dict() for m in manual_rejected])
        skipped.extend([m.to_dict() for m in manual_skipped])
        manual_matches.extend(manual_manual)

    elif choice == '3':
        approved = high_confidence_df.to_dict('records')
        print(f"✅ Auto-godkänner alla {len(approved)} matchningar")

    elif choice == '4':
        print("\n📋 Lista över matchningar:")
        for idx, row in high_confidence_df.iterrows():
            print(f"  • {row['name']} → {row['best_candidate']} (Score: {row['score']}, Ort: {row['PostOrt']})")
        conn.close()
        return

    else:
        print("❌ Ogiltigt val")
        conn.close()
        return

    # Sammanfattning
    print("\n" + "="*80)
    print("📊 SAMMANFATTNING")
    print("="*80)
    print(f"✅ Godkända: {len(approved)}")
    print(f"❌ Nekade: {len(rejected)}")
    print(f"✍️  Manuella matchningar: {len(manual_matches)}")
    print(f"⏭️  Skippade: {len(skipped)}")

    # Spara granskningsresultat om det finns något att spara
    if len(approved) > 0 or len(rejected) > 0 or len(skipped) > 0 or len(manual_matches) > 0:
        save_review_results(approved, rejected, skipped, manual_matches)

    if len(approved) > 0:

        # Fråga om databas-uppdatering
        print("\n" + "="*80)
        print("Vill du lägga till de godkända matchningarna i databasen?")
        db_choice = input("(y=ja, n=nej, d=dry run): ").lower().strip()

        if db_choice == 'y':
            add_matches_to_database(approved, conn, dry_run=False)
        elif db_choice == 'd':
            add_matches_to_database(approved, conn, dry_run=True)
        else:
            print("Ingen databas-uppdatering genomförd")

    conn.close()
    print("\n✅ Klart!")

if __name__ == "__main__":
    main()

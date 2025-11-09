#!/usr/bin/env python3
"""
Hjälpscript för att granska företag med high low scores (80-84)
Visar suggested match och låter dig välja rätt SCB-namn
"""

import pandas as pd
import sqlite3
from datetime import datetime

def review_high_low_scores():
    # Läs CSV
    df = pd.read_csv('review_high_low_scores.csv')

    print("="*80)
    print("GRANSKA HIGH LOW SCORES (80-84)")
    print("="*80)
    print(f"\nTotalt {len(df)} företag att granska")
    print()

    approved = []
    rejected = []

    for idx, row in df.iterrows():
        print(f"\n{'='*80}")
        print(f"[{idx+1}/{len(df)}] {row['name']} (ID: {row['id']})")
        print(f"{'='*80}")
        print(f"Score: {row['score']}")
        print(f"Suggested: {row['best_candidate']}")
        print(f"Ort: {row['PostOrt']}")
        print(f"Variant: {row['variant_used']}")
        print()

        while True:
            choice = input("Är detta RÄTT företag? (y/n/s=skip/q=quit): ").lower().strip()

            if choice == 'y':
                # Godkänn matchningen
                approved.append({
                    'id': row['id'],
                    'name': row['name'],
                    'scb_name': row['best_candidate'],
                    'score': row['score'],
                    'city': row['PostOrt'],
                    'variant': row['variant_used']
                })
                print("✓ Godkänd")
                break
            elif choice == 'n':
                # Avvisa matchningen
                rejected.append({
                    'id': row['id'],
                    'name': row['name'],
                    'reason': 'Fel företag'
                })
                print("✗ Avvisad")
                break
            elif choice == 's':
                print("⊘ Skippas")
                break
            elif choice == 'q':
                print("\nAvslutar...")
                save_results(approved, rejected)
                return
            else:
                print("Ogiltig input, försök igen.")

    save_results(approved, rejected)

def save_results(approved, rejected):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if approved:
        approved_df = pd.DataFrame(approved)
        filename = f'approved_high_low_scores_{timestamp}.csv'
        approved_df.to_csv(filename, index=False)
        print(f"\n✓ {len(approved)} godkända matchningar sparade i {filename}")

    if rejected:
        rejected_df = pd.DataFrame(rejected)
        filename = f'rejected_high_low_scores_{timestamp}.csv'
        rejected_df.to_csv(filename, index=False)
        print(f"✗ {len(rejected)} avvisade matchningar sparade i {filename}")

    print(f"\nTotalt granskat: {len(approved) + len(rejected)}")

if __name__ == "__main__":
    review_high_low_scores()

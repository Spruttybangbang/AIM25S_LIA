#!/usr/bin/env python3
"""
Bulk SCB Matcher
Matchar företag utan SCB-data mot SCB:s bulk-fil (1.8M företag)

Usage:
    python3 bulk_scb_matcher.py --bulk /path/to/scb_bulk.txt --db ai_companies.db
"""

import sqlite3
import json
import argparse
from datetime import datetime
from fuzzywuzzy import fuzz
import sys

class BulkSCBMatcher:
    def __init__(self, bulk_file_path, db_path):
        self.bulk_file_path = bulk_file_path
        self.db_path = db_path
        self.bulk_index = {}
        self.stats = {
            'total_companies': 0,
            'perfect_matches': 0,
            'fuzzy_matches': 0,
            'no_match': 0,
            'skipped': 0
        }

    def load_bulk_file(self):
        """Ladda bulk-filen och bygg en lookup-index."""
        print(f"📂 Läser bulk-fil: {self.bulk_file_path}")
        print("   Detta kan ta någon minut för 1.8M rader...")

        # Två separata index för effektivare sökning
        self.orgnr_index = {}  # org.nr -> company_data
        self.name_index = {}   # first_3_chars -> [company_data]

        with open(self.bulk_file_path, 'r', encoding='latin-1') as f:
            # Läs header
            header = f.readline().strip().split('\t')

            # Hitta kolumn-index
            col_idx = {}
            for i, col_name in enumerate(header):
                col_idx[col_name] = i

            print(f"   Kolumner: {len(header)}")

            # Läs alla rader och bygg index
            line_count = 0
            for line in f:
                line_count += 1
                if line_count % 100000 == 0:
                    print(f"   Läst {line_count:,} rader...")

                parts = line.strip().split('\t')
                if len(parts) < len(header):
                    continue

                # Extrahera nyckeldata
                peorgnr = parts[col_idx['PeOrgNr']]
                namn = parts[col_idx['Namn']].strip()
                foretagsnamn = parts[col_idx['Foretagsnamn']].strip()

                # Skip om inget namn
                if not namn and not foretagsnamn:
                    continue

                # Använd företagsnamn om det finns, annars namn
                company_name = foretagsnamn if foretagsnamn else namn

                # Skapa företagsobjekt
                company_data = {
                    'PeOrgNr': peorgnr,
                    'Namn': namn,
                    'Foretagsnamn': foretagsnamn,
                    'FtgStat': parts[col_idx['FtgStat']],
                    'JEStat': parts[col_idx['JEStat']],
                    'JurForm': parts[col_idx['JurForm']],
                    'Gatuadress': parts[col_idx['Gatuadress']].strip(),
                    'PostNr': parts[col_idx['PostNr']].strip(),
                    'PostOrt': parts[col_idx['PostOrt']].strip(),
                    'COAdress': parts[col_idx['COAdress']].strip(),
                    'RegDatKtid': parts[col_idx['RegDatKtid']],
                    'Ng1': parts[col_idx['Ng1']],
                    'Ng2': parts[col_idx['Ng2']],
                    'Ng3': parts[col_idx['Ng3']],
                    'Ng4': parts[col_idx['Ng4']],
                    'Ng5': parts[col_idx['Ng5']],
                    'Reklamsparrtyp': parts[col_idx['Reklamsparrtyp']]
                }

                # Index 1: org.nr (ta bort 16-prefix för juridiska personer)
                orgnr_10 = peorgnr[2:] if peorgnr.startswith('16') else peorgnr
                self.orgnr_index[orgnr_10] = company_data

                # Index 2: Första 3 bokstäver i namnet (för snabbare fuzzy search)
                name_normalized = company_name.upper().strip()
                if len(name_normalized) >= 3:
                    prefix = name_normalized[:3]
                    if prefix not in self.name_index:
                        self.name_index[prefix] = []
                    self.name_index[prefix].append({
                        'name': name_normalized,
                        'data': company_data
                    })

            print(f"✅ Läst {line_count:,} rader")
            print(f"   Org.nr index: {len(self.orgnr_index):,} företag")
            print(f"   Namn prefix index: {len(self.name_index):,} prefix")

    def extract_orgnr_from_text(self, text):
        """Försök extrahera org.nr från text."""
        if not text:
            return None

        # Vanliga format: XXXXXX-XXXX, XXXXXXXXXX
        import re
        patterns = [
            r'\b(\d{6}-?\d{4})\b',  # 6-4 format
            r'\b(\d{10})\b',         # 10 siffror
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                orgnr = match.group(1).replace('-', '')
                if len(orgnr) == 10:
                    return orgnr

        return None

    def normalize_name(self, name):
        """Normalisera företagsnamn för bättre matchning."""
        if not name:
            return ""

        name = name.upper().strip()
        # Ta bort vanliga suffix
        for suffix in [' AB', ' AKTIEBOLAG', ' HB', ' KB', ' EK. FÖR.', ' EK FÖR']:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()

        return name

    def find_bulk_match(self, company_name, website=None):
        """Hitta matchning i bulk-filen."""

        # 1. Försök hitta org.nr i website eller namn
        orgnr = self.extract_orgnr_from_text(website)
        if orgnr and orgnr in self.orgnr_index:
            return self.orgnr_index[orgnr], 100, 'orgnr'

        # 2. Normalisera söknamnet
        normalized_name = self.normalize_name(company_name)
        if not normalized_name or len(normalized_name) < 3:
            return None, 0, 'no_name'

        # 3. Sök i prefix-index (endast företag med samma 3 första bokstäver)
        prefix = normalized_name[:3]

        if prefix not in self.name_index:
            return None, 0, 'no_match'

        # 4. Fuzzy match endast mot företag med samma prefix
        candidates = self.name_index[prefix]
        best_match = None
        best_score = 0

        for candidate in candidates:
            candidate_name = candidate['name']

            # Exakt matchning
            if normalized_name == candidate_name:
                return candidate['data'], 100, 'exact_name'

            # Fuzzy matchning
            score = fuzz.ratio(normalized_name, candidate_name)
            if score > best_score and score >= 85:
                best_score = score
                best_match = candidate['data']

        if best_match:
            return best_match, best_score, 'fuzzy'

        return None, 0, 'no_match'

    def process_companies(self, dry_run=False, limit=None):
        """Bearbeta alla företag utan SCB-matchning."""
        import pandas as pd
        import os

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Hämta företag utan SCB-matchning
        query = '''
            SELECT c.id, c.name, c.website, c.is_swedish
            FROM companies c
            LEFT JOIN scb_matches sm ON c.id = sm.company_id
            WHERE sm.id IS NULL AND c.is_swedish = 1
        '''

        if limit:
            query += f' LIMIT {limit}'

        cursor.execute(query)
        companies = cursor.fetchall()

        self.stats['total_companies'] = len(companies)

        print(f"\n🔍 Bearbetar {len(companies)} företag...")
        print("=" * 70)

        perfect_matches = []  # 100% score - läggs direkt i DB
        fuzzy_matches = []    # 85-99% score - exporteras till CSV

        for i, (company_id, name, website, is_swedish) in enumerate(companies, 1):
            # Skip icke-svenska företag
            if not is_swedish:
                self.stats['skipped'] += 1
                continue

            # Hitta matchning
            match_data, score, match_type = self.find_bulk_match(name, website)

            if match_data and score >= 85:
                # Vi har en matchning!
                if score == 100:
                    # PERFEKT matchning - lägg direkt i databasen
                    self.stats['perfect_matches'] += 1
                    emoji = '✅'

                    print(f"{emoji} [{i}/{len(companies)}] {name}")
                    print(f"   Matchad med: {match_data['Foretagsnamn'] or match_data['Namn']}")
                    print(f"   Score: {score} | Type: {match_type}")
                    print(f"   Org.nr: {match_data['PeOrgNr']} | Status: {match_data['FtgStat']}")
                    print(f"   → AUTO-GODKÄND (perfekt match)")
                    print()

                    # Förbered för insättning i databas
                    payload = json.dumps(match_data, ensure_ascii=False)
                    perfect_matches.append((
                        company_id,
                        1,  # matched
                        score,
                        match_data['PostOrt'],
                        payload,
                        datetime.now().isoformat()
                    ))
                else:
                    # FUZZY matchning - exportera till CSV för granskning
                    self.stats['fuzzy_matches'] += 1
                    emoji = '🔶'

                    print(f"{emoji} [{i}/{len(companies)}] {name}")
                    print(f"   Matchad med: {match_data['Foretagsnamn'] or match_data['Namn']}")
                    print(f"   Score: {score} | Type: {match_type}")
                    print(f"   Org.nr: {match_data['PeOrgNr']} | Status: {match_data['FtgStat']}")
                    print(f"   → Behöver granskas (fuzzy match)")
                    print()

                    # Lägg till i CSV-export
                    fuzzy_matches.append({
                        'company_id': company_id,
                        'company_name': name,
                        'matched_name': match_data['Foretagsnamn'] or match_data['Namn'],
                        'score': score,
                        'match_type': match_type,
                        'orgnr': match_data['PeOrgNr'],
                        'status': match_data['FtgStat'],
                        'city': match_data['PostOrt'],
                        'jurform': match_data['JurForm'],
                        'sni': match_data['Ng1'],
                        'payload': json.dumps(match_data, ensure_ascii=False)
                    })
            else:
                self.stats['no_match'] += 1
                if i % 50 == 0:  # Visa bara var 50:e no-match
                    print(f"❌ [{i}/{len(companies)}] {name} - Ingen matchning")

        print("\n" + "=" * 70)
        print("📊 MATCHNINGSRESULTAT")
        print("=" * 70)
        print(f"Totalt företag:      {self.stats['total_companies']}")
        print(f"Perfect matches:     {self.stats['perfect_matches']} (100% score) → AUTO-GODKÄNDA")
        print(f"Fuzzy matches:       {self.stats['fuzzy_matches']} (85-99% score) → KRÄVER GRANSKNING")
        print(f"Ingen matchning:     {self.stats['no_match']}")
        print(f"Skippade:            {self.stats['skipped']}")
        print("=" * 70)

        # Spara perfekta matchningar till databasen
        if not dry_run and perfect_matches:
            print(f"\n💾 Sparar {len(perfect_matches)} perfekta matchningar till databasen...")

            cursor.executemany('''
                INSERT INTO scb_matches (company_id, matched, score, city, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', perfect_matches)

            conn.commit()
            print("✅ Sparat!")

        # Exportera fuzzy matches till CSV
        if fuzzy_matches:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_path = f'results/bulk_fuzzy_matches_{timestamp}.csv'

            # Skapa results-mappen om den inte finns
            os.makedirs('results', exist_ok=True)

            df = pd.DataFrame(fuzzy_matches)
            df.to_csv(csv_path, index=False, encoding='utf-8')

            print(f"\n📋 Exporterade {len(fuzzy_matches)} fuzzy matches till:")
            print(f"   {csv_path}")
            print(f"\n⚠️  VIKTIGT: Granska dessa manuellt innan import!")
            print(f"   Använd sedan: tools/import_manual_matches_direct.py")

        if dry_run:
            print("\n🔍 DRY RUN - Ingen data sparad till databasen")
            if fuzzy_matches:
                print("   (CSV hade exporterats i en riktig körning)")

        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Match companies against SCB bulk file')
    parser.add_argument('--bulk', required=True, help='Path to SCB bulk file')
    parser.add_argument('--db', default='ai_companies.db', help='Path to database')
    parser.add_argument('--dry-run', action='store_true', help='Do not write to database')
    parser.add_argument('--limit', type=int, help='Limit number of companies to process')

    args = parser.parse_args()

    print("🚀 Bulk SCB Matcher")
    print("=" * 70)

    matcher = BulkSCBMatcher(args.bulk, args.db)

    # Ladda bulk-filen
    matcher.load_bulk_file()

    # Bearbeta företag
    matcher.process_companies(dry_run=args.dry_run, limit=args.limit)

    print("\n✅ Klart!")


if __name__ == '__main__':
    main()

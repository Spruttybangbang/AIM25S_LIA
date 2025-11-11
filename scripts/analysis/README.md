# Analysskript

Scripts för att analysera databas och datakvalitet.

## Scripts

### analyze_database.py
Omfattande databasanalys som visar:
- Tabellstruktur och schema
- Saknad data per kolumn
- Datakompletteringsgrad
- Rekommendationer för databerikning

**Användning:**
```bash
python scripts/analysis/analyze_database.py
```

### analyze_duplicates.py
Identifierar potentiella dubbletter i databasen baserat på:
- Företagsnamn
- Organisationsnummer
- Webbadresser

### analyze_improvements.py
Analyserar förbättringsmöjligheter och datakvalitet.

### detailed_pattern_analysis.py
Detaljerad mönsteranalys av data för att hitta samband och avvikelser.

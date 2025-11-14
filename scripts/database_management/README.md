# Databashantering

Scripts för hantering, underhåll och export av databaser.

## Scripts

### export_companies_to_csv.py
Exporterar företag till 3 CSV-filer:
- Alla företag (komplett export)
- Företag med SCB-data (inkl. alla SCB-kolumner)
- Företag utan SCB-data

**Användning:**
```bash
python scripts/database_management/export_companies_to_csv.py
```

**Output:** 3 timestamped CSV-filer i current directory.

**Flyttad från:** `scripts/export/` (2025-11-14)

### interactive_scb_matcher.py
Interaktivt verktyg för manuell SCB-matchning från CSV.
- Läser CSV med company_ids
- Söker i SCB och visar max 5 resultat
- Användaren väljer rätt match
- Auto-save var 5:e företag
- Sparar till timestamped CSV

**AKTIVT ANVÄND** för manuell SCB-granskning.

### move_companies_to_others.py
Flyttar företag från ai_companies.db till ai_others.db.
- Kopierar all data till måldatabas
- Tar bort från källdatabas
- Bevarar alla relationer

**Användning:**
```bash
python scripts/database_management/move_companies_to_others.py
```

### verify_databases.py
Verifierar antal företag i båda databaser.

**Användning:**
```bash
python scripts/database_management/verify_databases.py
```

### check_databases.py
Kontrollera antal företag i databaser.
- Default: Visar båda databaser + total
- `--companies`: Endast ai_companies.db
- `--others`: Endast ai_others.db

**Användning:**
```bash
python scripts/database_management/check_databases.py
python scripts/database_management/check_databases.py --companies
```

**Ersätter:** `check_db.py` och `check_both_dbs.py` (2025-11-14)

### interactive_deduplication.py
Interaktivt verktyg för att identifiera och hantera dubbletter.

### fas1_snabba_vinster.py
Fas 1-script för snabba förbättringar av datakvalitet.

## Arkiverade Scripts

**delete_companies.py** har flyttats till `/archive/migrations/` (2025-11-14) - engångsscript för radering av specifika company_ids.

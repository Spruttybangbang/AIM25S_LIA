# Scripts Guide - AIM25S_LIA

Omfattande guide till alla Python-scripts i projektet. Scripts är organiserade efter funktionalitet och användningsfrekvens.

---

## 🌟 CORE SCRIPTS (Mest använda)

### SCB Integration

#### `scripts/scb/scb_integration_v2.py` ⭐⭐⭐
**Syfte:** Huvudscript för SCB API-integration

**Funktionalitet:**
- Söker företag i SCB API baserat på företagsnamn och stad
- Robust felhantering med retries och exponential backoff
- Fuzzy matching (threshold: 85%)
- Sparar matchningar i `scb_matches` tabell
- Exporterar problemfall till CSV

**Input:** ai_companies.db (företag utan SCB-data)
**Output:** scb_matches tabell + CSV-exports av problem

**Användning:**
```bash
cd /home/user/AIM25S_LIA
python scripts/scb/scb_integration_v2.py
```

**Beroenden:** SCB certifikat, fuzzywuzzy, requests

---

#### `scripts/database_management/interactive_scb_matcher.py` ⭐⭐⭐
**Syfte:** Interaktiv manuell SCB-matchning från CSV

**Funktionalitet:**
- Läser CSV med company_ids som behöver granskas
- Söker i SCB API och visar max 5 resultat
- Användaren väljer rätt match manuellt (1-5 eller S för skip)
- Auto-save var 5:e företag (säkerhetsåtgärd)
- Sparar bekräftade matches till timestamped CSV

**Input:** CSV med kolumnen `company_id`
**Output:** `scb_matches_confirmed_YYYYMMDD_HHMMSS.csv`

**Användning:**
```bash
cd /home/user/AIM25S_LIA/scripts/database_management
python interactive_scb_matcher.py
# Följ instruktionerna
```

**Status:** AKTIVT ANVÄND - huvudverktyg för manuell SCB-granskning

**Beroenden:** SCB certifikat, fuzzywuzzy

---

#### `tools/bulk_scb_matcher.py` ⭐⭐
**Syfte:** Matcha mot 1.8M SCB bulk-fil (offline-matchning)

**Funktionalitet:**
- Laddar SCB bulk-fil (scb_bulk.txt) i minnet
- Dual-index: organisationsnummer + företagsnamn prefix
- Perfect matches (100%) → auto-godkänd och sparad direkt i DB
- Fuzzy matches (85-99%) → exporteras till CSV för manuell granskning

**Input:** scb_bulk.txt + ai_companies.db
**Output:**
- Perfect matches direkt i scb_enrichment
- Fuzzy matches → `bulk_fuzzy_matches_TIMESTAMP.csv`

**Användning:**
```bash
cd /home/user/AIM25S_LIA/tools
python bulk_scb_matcher.py
```

**Komplettering:** Används tillsammans med API-matchning för maximal täckning

---

### Description Generation Workflow

#### `scripts/scrape_company_websites.py` ⭐⭐
**Syfte:** Skrapa text från företagshemsidor

**Funktionalitet:**
- Läser företag med hemsidor från databasen
- BeautifulSoup-baserad scraping
- Extraherar meta descriptions och huvudtext
- Timeouts och error handling

**Input:** ai_companies.db (företag med website)
**Output:** `results/scraped_websites.csv`

**Användning:**
```bash
cd /home/user/AIM25S_LIA
python scripts/scrape_company_websites.py
```

**Nästa steg:** Kör generate_descriptions.py

---

#### `scripts/generate_descriptions.py` ⭐⭐
**Syfte:** Generera 3-menings företagsbeskrivningar med Claude AI

**Funktionalitet:**
- Läser skrapad hemsidetext från CSV
- Använder Claude Haiku API för att generera koncisa beskrivningar
- Batch-processing med progress tracking
- Rate limiting och error handling

**Input:** `results/scraped_websites.csv`
**Output:** `results/generated_descriptions.csv`

**Användning:**
```bash
cd /home/user/AIM25S_LIA
export ANTHROPIC_API_KEY="din-nyckel"
python scripts/generate_descriptions.py
```

**Beroenden:** anthropic library, ANTHROPIC_API_KEY

**Nästa steg:** Granska CSV manuellt, kör sedan import_generated_descriptions.py

---

#### `scripts/import_generated_descriptions.py` ⭐
**Syfte:** Importera granskade AI-beskrivningar till databasen

**Funktionalitet:**
- Läser granskad CSV med beskrivningar
- Preview innan import
- Bekräftelse krävs
- Batch update till companies-tabellen

**Input:** `results/generated_descriptions.csv` (granskad)
**Output:** Uppdaterad ai_companies.db

**Användning:**
```bash
cd /home/user/AIM25S_LIA
python scripts/import_generated_descriptions.py
```

---

### Database Export

#### `scripts/database_management/export_companies_to_csv.py` ⭐⭐
**Syfte:** Exportera alla företag till 3 CSV-filer

**Funktionalitet:**
- Exporterar alla företag med komplett data
- Skapar 3 filer:
  1. `companies_without_scb_TIMESTAMP.csv` - Företag utan SCB
  2. `companies_with_scb_TIMESTAMP.csv` - Företag med SCB (alla SCB-kolumner)
  3. `companies_all_TIMESTAMP.csv` - Alla företag (komplett)
- Inkluderar relationsdata: sectors, domains, ai_capabilities, dimensions

**Output:** 3 timestamped CSV-filer

**Användning:**
```bash
cd /home/user/AIM25S_LIA
python scripts/database_management/export_companies_to_csv.py
```

---

## 🛠️ HELPER TOOLS

### SCB Helpers (tools/)

#### `tools/import_manual_matches_direct.py`
Import av manuella SCB-matchningar från CSV till scb_enrichment tabell

**Funktionalitet:**
- Importerar DIREKT från CSV utan nya SCB API-anrop
- Snabb offline-import av bekräftade matchningar
- Sätter score=100 för manuella matchningar
- Används efter interactive_scb_matcher.py

**Notering:** `import_manual_matches.py` (som gjorde nya API-anrop) har tagits bort (2025-11-14) - redundant eftersom interactive_scb_matcher.py redan validerar via API.

#### `tools/import_bulk_fuzzy_matches.py`
Import av granskade fuzzy matches från bulk matcher

#### `tools/approve_good_matches.py`
Auto-godkännande av högkvalitativa SCB-matches (>95% fuzzy score)

#### `tools/analyze_scb_issues.py`
Analysera SCB-matchningsproblem och identifiera mönster

#### `tools/explore_issues_interactive.py`
Interaktiv utforskning av SCB-problemfall

#### `tools/review_high_low_scores_helper.py`
Granska fuzzy scores för kvalitetskontroll

#### `tools/manual_search_helper.py`
Hjälpverktyg för manuell SCB-sökning

#### `tools/remove_fuzzy_matches.py`
Ta bort dåliga fuzzy matches från databasen

---

### SCB Retry Scripts (scripts/scb/)

#### `scripts/scb/retry_scb_search.py`
Retry för företag som tidigare misslyckats i SCB API med förbättrade strategier

#### `scripts/scb/retry_no_candidates.py`
Specifikt för företag utan kandidater - alternativa sökstrategier

---

### Database Analysis (scripts/analysis/)

#### `scripts/analysis/analyze_database.py`
Omfattande databasanalys: schema, saknad data, kompletteringsgrad

#### `scripts/analysis/analyze_duplicates.py`
Identifiera dubbletter baserat på namn, organisationsnummer, webbadress

#### `scripts/analysis/analyze_improvements.py`
Analysera förbättringsmöjligheter i datakvalitet

#### `scripts/analysis/detailed_pattern_analysis.py`
Detaljerad mönsteranalys för samband och avvikelser

---

### Database Maintenance (scripts/database_management/)

#### `scripts/database_management/interactive_deduplication.py`
Interaktivt verktyg för att hantera dubbletter

#### `scripts/database_management/move_companies_to_others.py`
Flytta företag från ai_companies.db till ai_others.db

#### `scripts/database_management/verify_databases.py`
Verifiera antal företag och dataintegritet i båda databaser

#### `scripts/database_management/check_databases.py`
Flexibel räkning av företag i databaser

**Funktionalitet:**
- Default: Visar båda databaser + totalt antal
- `--companies`: Endast ai_companies.db
- `--others`: Endast ai_others.db

**Användning:**
```bash
python scripts/database_management/check_databases.py
python scripts/database_management/check_databases.py --companies
```

**Ersätter:** check_db.py och check_both_dbs.py (2025-11-14)

#### `scripts/database_management/fas1_snabba_vinster.py`
Fas 1-förbättringar av datakvalitet

---

### Website Discovery

#### `scripts/find_company_websites.py`
**Syfte:** Hitta hemsidor via smart domängissning

**Funktionalitet:**
- Genererar domänvarianter baserat på företagsnamn
- DNS + HTTP-verifiering
- Fuzzy matching för validering
- Exporterar till CSV för manuell granskning

**Output:** `results/found_websites.csv`

**Nästa steg:** Granska, rensa, spara som found_websites_clean.csv

---

#### `scripts/update_websites_and_cleanup.py`
**Syfte:** Uppdatera websites OCH radera tomma företag

**Funktionalitet:**
- Importerar granskade hemsidor från CSV
- Smart deletion med säkerhetskontroller
- Kräver `--force-delete` för riskabla operationer

**Input:** `results/found_websites_clean.csv`

**Användning:**
```bash
cd /home/user/AIM25S_LIA
python scripts/update_websites_and_cleanup.py
```

**VARNING:** Kraftfullt verktyg - kan radera företag. Läs prompten noga!

---

## 📦 ARKIVERADE SCRIPTS

Se `/archive/` för scripts som inte längre används aktivt:

### Migrations (archive/migrations/)
- `update_db_paths.py` - Uppdatering av databassökvägar (färdig)
- `remove_ids_from_ai_companies.py` - Borttagning av 173 ID:n (färdig)
- `check_ids.py` - Verifiering av borttagning (färdig)
- `delete_companies.py` - Radering av 34 ID:n (färdig)

**⚠️ Varning:** Kör INTE dessa scripts igen! De innehåller hårdkodade ID-listor för specifika tidpunkter.

---

## 🔗 WORKFLOWS

### Complete SCB Enrichment Workflow

```
1. API-baserad automatisk matchning
   scb_integration_v2.py → scb_matches tabell

2. Bulk-matchning offline
   bulk_scb_matcher.py + scb_bulk.txt
   → Perfect matches direkt i DB
   → Fuzzy matches till CSV

3. Manuell granskning av fuzzy matches
   Granska bulk_fuzzy_matches CSV
   → Spara som bulk_fuzzy_cleaned.csv

4. Import av granskade bulk matches
   import_bulk_fuzzy_matches.py → scb_enrichment

5. Identifiera kvarvarande problemfall
   analyze_scb_issues.py → CSV med företag att granska

6. Interaktiv manuell matchning
   interactive_scb_matcher.py + problemfall CSV
   → scb_matches_confirmed_TIMESTAMP.csv

7. Import av manuella matchningar
   import_manual_matches_direct.py → scb_enrichment

8. Verifiera resultat
   analyze_database.py
```

---

### Complete Description Generation Workflow

```
1. Identifiera företag utan hemsidor
   find_company_websites.py → found_websites.csv

2. Granska och rensa
   Manuell granskning → found_websites_clean.csv

3. Uppdatera databasen med hemsidor
   update_websites_and_cleanup.py

4. Skrapa hemsidor
   scrape_company_websites.py → scraped_websites.csv

5. Generera AI-beskrivningar
   generate_descriptions.py → generated_descriptions.csv

6. Granska beskrivningar manuellt
   Kvalitetskontroll i Excel/CSV

7. Importera till databasen
   import_generated_descriptions.py
```

---

## 💾 DATABASER

**Huvuddatabas:** `/databases/ai_companies.db` (2.9MB)
- Ca 724 fokuserade AI-företag

**Sekundär databas:** `/databases/ai_others.db` (352KB)
- Universitet, forskningsinstitut, stödjande organisationer

---

## 📁 VIKTIGA MAPPAR

### `/results/`
Innehåller alla arbets-CSV:er från olika scripts:
- SCB-matchningsresultat
- Skrapade hemsidor
- Genererade beskrivningar
- Analysresultat

### `/exports/`
Officiella CSV-exports av databasen för distribution

### `/tools/`
Helper-scripts för SCB-matchning och kvalitetskontroll

### `/archive/`
Arkiverade scripts och gamla exports

---

## 🔑 BEROENDEN

### Python Libraries
```bash
pip install sqlite3 pandas anthropic fuzzywuzzy requests beautifulsoup4
```

### SCB API
- Kräver certifikat för HTTPS-anrop
- Används av: scb_integration_v2.py, interactive_scb_matcher.py, analyze_companies.py

### Claude AI API
- Kräver ANTHROPIC_API_KEY
- Används av: generate_descriptions.py

---

## 📝 NAMNKONVENTIONER

### CSV Output Files
- `{beskrivning}_{YYYYMMDD_HHMMSS}.csv` - Timestamped arbetsfiler
- `{beskrivning}_cleaned.csv` - Manuellt granskade filer

### Database Tables
- `companies` - Företagsinformation
- `scb_matches` - SCB API-matchningar (med fuzzy scores)
- `scb_enrichment` - Berikad SCB-data (endast bekräftade matchningar)
- `company_{relation}` - Junction tables för relationsdata

---

## ⚡ SNABBKOMMANDON

### Export hela databasen
```bash
cd /home/user/AIM25S_LIA
python scripts/database_management/export_companies_to_csv.py
```

### Manuell SCB-matchning
```bash
cd /home/user/AIM25S_LIA/scripts/database_management
python interactive_scb_matcher.py
```

### Analysera datakvalitet
```bash
cd /home/user/AIM25S_LIA
python scripts/analysis/analyze_database.py
```

---

## 🚨 VIKTIGA NOTERINGAR

### ALDRIG Köra Igen
- Scripts i `/archive/migrations/` - Engångsmigreringar
- `update_websites_and_cleanup.py` utan granskning - Kan radera företag

### Alltid Granska Först
- AI-genererade beskrivningar innan import
- Bulk fuzzy matches innan import
- found_websites.csv innan uppdatering

### Backup Före Kritiska Operationer
- Ta backup av databaser innan mass-delete
- Testa på en kopia först vid osäkerhet

---

## 📞 SUPPORT

För frågor eller problem:
1. Kolla README-filer i respektive mapp
2. Läs docstrings i Python-scripten
3. Kontrollera git-historiken för tidigare användning

---

**Senast uppdaterad:** 2025-11-14
**Projektversion:** AIM25S LIA

# Batch SCB Matcher - Automatisk version

Automatisk batch-version av interactive_scb_matcher.py. Läser CSV med företagsnamn och hämtar automatiskt SCB-data.

## Översikt

Detta script är en **exakt kopia** av interactive_scb_matcher.py fast utan manuellt godkännande:
- ✅ Läser CSV med bara företagsnamn
- ✅ Använder samma fuzzy matching-logik
- ✅ Tar automatiskt första (bästa) matchningen
- ✅ Samma SCB API-sökning och normalisering
- ✅ Samma CSV-output-format

## Installation

```bash
pip install fuzzywuzzy python-Levenshtein requests
```

## Användning

### 1. Skapa input-CSV

Bara en kolumn - företagsnamn:

**input.csv:**
```csv
company_name
Spotify AB
Lexplore AB
Mavenoid AB
```

### 2. Kör scriptet

```bash
cd scripts/scb
python3 batch_scb_by_orgnr.py input.csv
```

### 3. Output

**scb_success_TIMESTAMP.csv:**
- Samma format som interactive_scb_matcher skapar
- Alla kolumner från SCB + fuzzy_score

**scb_failed_TIMESTAMP.csv:**
- Företag som inte hittades eller hade för låg fuzzy score

## Exempel-körning

```bash
$ python3 batch_scb_by_orgnr.py companies.csv

📖 Läser företagsnamn från: companies.csv
✅ Hittade 10 företag att processa

💾 Lyckade matcher sparas till: scb_success_20251114_120000.csv
💾 Misslyckade matcher sparas till: scb_failed_20251114_120000.csv
🎯 Fuzzy threshold: 85% (tar automatiskt bästa matchningen)

Vill du börja hämta data för 10 företag? (y/n): y

======================================================================
STARTAR BATCH-KÖRNING
======================================================================

[1/10] Spotify AB
  ✅ Spotify AB - STOCKHOLM (score: 100)

[2/10] Lexplore AB
  ✅ Lexplore AB - STOCKHOLM (score: 100)

...

======================================================================
SAMMANFATTNING
======================================================================
Totalt företag: 10
Lyckade matcher: 9 (90.0%)
Misslyckade matcher: 1 (10.0%)
Körtid: 5.2 sekunder (0.1 minuter)
```

## Tekniska detaljer

### Fuzzy Matching

- Samma `normalize_name()` som interactive_scb_matcher
- Tar bort .com, .se, AB, aktiebolag etc.
- Fuzzy score threshold: **85%** (samma som interactive)
- Tar **första (bästa)** matchningen automatiskt

### Rate Limiting

- 0.5 sekunder mellan varje request
- ~2 requests/sekund (SCB rekommenderat)

### Output-format

Exakt samma som interactive_scb_matcher:
- `company_name` - Ditt input-namn
- `fuzzy_score` - Hur bra matchningen är (0-100)
- `organization_number` - Org.nr från SCB
- `scb_company_name` - Officiellt namn från SCB
- Alla andra SCB-variabler...

## Vanliga frågor

### Vad är skillnaden mot interactive_scb_matcher.py?

| Feature | interactive_scb_matcher | batch_scb_by_orgnr |
|---------|------------------------|-------------------|
| Input | company_id från databas | company_name från CSV |
| Matchning | Användaren väljer | Automatiskt första träffen |
| Godkännande | Manuellt per företag | Helt automatiskt |
| Output | Samma format | Samma format |

### Varför heter det batch_scb_by_orgnr?

Historiska skäl - scriptet hette tidigare något annat men omskrevs. Namnet kvarstår men det tar nu bara företagsnamn.

### Hur justerar jag fuzzy threshold?

Ändra i scriptet:
```python
FUZZY_THRESHOLD = 85  # Ändra till önskat värde
```

## Relaterade scripts

- **interactive_scb_matcher.py** - Manuell version med användar-godkännande
- **scb_integration_v2.py** - Bulk enrichment från databas

---

**Baserat på:** interactive_scb_matcher.py
**Version:** 2.0

# SCB Integration för AI Companies Database

Detta projekt integrerar svenska AI-företag med SCB:s företagsregister för att berika företagsinformation med officiella uppgifter.

## 📊 Resultat

**Total matchningar:** 360 företag
- Automatiska matchningar: 357 (99.2% med score ≥ 85)
- Manuella godkännanden: 3 (high low scores 80-84)

**Av 158 "no candidates" företag:**
- 11 matchades automatiskt (7%)
- 32 low score (20%)
- 115 inga kandidater (73% - mestadels utländska företag/startups)

## 📁 Projektstruktur

```
AIM25S_LIA/
├── ai_companies.db           # Huvuddatabas med företagsdata
├── README.md                 # Denna fil
│
├── scripts/                  # Huvudscripts
│   ├── scb_integration_v2.py # Original SCB-integration
│   ├── retry_scb_search.py   # Retry-sökning med search_variants
│   └── retry_no_candidates.py # Kategorisering av no-candidates
│
├── tools/                    # Hjälpscripts
│   ├── analyze_scb_issues.py
│   ├── approve_good_matches.py
│   ├── explore_issues_interactive.py
│   ├── import_manual_matches.py
│   ├── import_manual_matches_direct.py
│   ├── manual_search_helper.py
│   └── review_high_low_scores_helper.py
│
├── results/                  # Alla CSV-resultat
│   ├── scb_matches.csv      # Huvudresultat (alla matchningar)
│   ├── scb_issues.csv       # Problem från första körningen
│   ├── retry_scb_issues.csv # Problem från retry
│   └── ... (övriga CSV-filer)
│
├── logs/                     # Terminal-feedback från körningar
│   ├── snippet_manual_matches_terminal_feedback.txt
│   └── snippet_twenty_tests_terminal_feedback.txt
│
└── docs/                     # Dokumentation
    ├── SCB_INTEGRATION_V2_GUIDE.md
    └── SCB_ANALYS_README.md
```

## 🚀 Snabbstart

### 1. Grundläggande SCB-integration

```bash
cd scripts
python3 scb_integration_v2.py --limit 100
```

### 2. Retry-sökning med förbättrade varianter

```bash
cd scripts
python3 retry_scb_search.py --input ../results/no_candidates_need_review.csv --limit 20
```

### 3. Importera manuella matchningar

```bash
cd tools
python3 import_manual_matches_direct.py --csv ../results/manual_matches_20251109_184431.csv
```

## 🔧 Viktiga förbättringar

### search_variants
Scriptet genererar nu flera söknamn-varianter:
- Med/utan "AB" och "Aktiebolag"
- Första ordet (t.ex. "Layke" från "Layke Analytics")
- Utan domännamn (.ai, .se, etc.)
- Bindestreck-varianter

### Threshold-justering
- Sänkt från 92/88 till **85** för korta namn
- Accepterar nu fler legitima matchningar (scores 86-91)

### Exact matching
- När `correct_scb_name` finns, prioriterar exact match
- Förhindrar felaktiga matchningar (t.ex. IBM USA → IBM Svenska)

## 📈 Statistik per körning

### Manuella matchningar (14 företag)
- ✓ **11 lyckades** (79%)
- ⚠ **3 low score** (Saab 84, Preem 82, Stena 76)

### Retry på 158 företag
- ✓ **11 matchningar** (7%)
- ⚠ **32 low score** (20%)
- ✗ **115 no candidates** (73%)

### High low scores granskning (9 företag, score 80-84)
- ✓ **3 godkända**: Dell Technologies, Fotanofe AB, Ledarna
- ✗ **6 avvisade**: Felaktiga fuzzy matches

## 🛠 Krav

```bash
pip install pandas fuzzywuzzy python-Levenshtein requests --break-system-packages
```

## 📝 Certifikat

SCB API kräver klientcertifikat. Standard path:
```
../../SCB/certifikat/Certifikat_SokPaVar_A00592_2025-10-29_09-27-36Z.pem
```

Ändra med `--cert` flaggan om nödvändigt.

## 🗄 Databas

**Tabell: scb_matches**
- `company_id` - FK till companies.id
- `matched` - 1/0
- `score` - Fuzzy match score (0-100)
- `city` - PostOrt från SCB
- `payload` - Fullständig SCB-data (JSON)

## 📚 Dokumentation

Se `docs/` för detaljerad dokumentation:
- `SCB_INTEGRATION_V2_GUIDE.md` - Guide för SCB-integration
- `SCB_ANALYS_README.md` - Analys av resultat

## 🎯 Nästa steg

1. Importera de 3 godkända high-low scores:
   ```bash
   cd scripts
   python3 retry_scb_search.py --input ../results/approved_high_low_for_import.csv
   ```

2. Granska "no candidates" (115 st) manuellt vid behov

3. Exportera slutgiltig rapport över alla matchningar

## 📊 Exempel-output

```
=== SLUTSTATISTIK ===
Uppdaterade: 11
Låg score: 3
Inget resultat: 0
API-fel: 0
Total: 14
```

## 🤝 Contributors

- Linus Lord (Spruttybangbang)
- Claude Code (AI-assistent)

## 📜 Licens

Internt projekt för AIM25S LIA.

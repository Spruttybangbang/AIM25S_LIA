# SCB Integration för AI Companies Database

Detta projekt integrerar svenska AI-företag med SCB:s företagsregister för att berika företagsinformation med officiella uppgifter.

## 📊 Resultat

**Total matchningar:** 360 företag av 1113 (32.3%)

**Kvalitetsfördelning:**
- ✅ Perfekta matchningar (100%): 311 företag
- 🟢 Mycket bra (95-99%): 14 företag
- 🟡 Bra (90-94%): 22 företag
- 🟠 Godkända (85-89%): 10 företag
- 🔴 Låga (<85%): 3 företag

**Matchningskällor:**
- SCB API-integration: 330 företag (ursprunglig körning)
- Bulk-matchning: 30 företag (från 1.8M företagsdataset)

**Omatchade företag (753):**
- Mestadels myndigheter, universitet och utländska företag
- Företag utan organisationsnummer i SCB:s register

## 📁 Projektstruktur

```
AIM25S_LIA/
├── README.md                          # Denna fil
├── config.example.ini                 # Exempelkonfiguration
│
├── databases/                         # SQLite-databaser
│   ├── ai_companies.db               # Huvuddatabas (906 företag)
│   └── ai_others.db                  # Sekundär databas (173 org)
│
├── scripts/                          # Alla Python-scripts
│   ├── analysis/                     # Dataanalys
│   │   ├── analyze_database.py
│   │   ├── analyze_duplicates.py
│   │   ├── analyze_improvements.py
│   │   └── detailed_pattern_analysis.py
│   ├── database_management/          # Databashantering
│   │   ├── delete_companies.py
│   │   ├── move_companies_to_others.py
│   │   ├── verify_databases.py
│   │   ├── check_db.py
│   │   ├── interactive_deduplication.py
│   │   └── fas1_snabba_vinster.py
│   ├── export/                       # Export till CSV
│   │   ├── export_companies_to_csv.py
│   │   └── export_companies_without_scb.py
│   └── scb/                          # SCB-integration
│       ├── scb_integration_v2.py
│       ├── retry_scb_search.py
│       └── retry_no_candidates.py
│
├── tools/                            # SCB-hjälpverktyg
│   ├── analyze_scb_issues.py
│   ├── approve_good_matches.py
│   ├── bulk_scb_matcher.py
│   ├── explore_issues_interactive.py
│   ├── import_bulk_fuzzy_matches.py
│   ├── import_manual_matches.py
│   ├── import_manual_matches_direct.py
│   ├── manual_search_helper.py
│   ├── remove_fuzzy_matches.py
│   └── review_high_low_scores_helper.py
│
├── exports/                          # CSV-exports
│   ├── companies_all_*.csv
│   ├── companies_with_scb_*.csv
│   └── companies_without_scb_*.csv
│
├── results/                          # SCB-matchningsresultat
│   ├── scb_matches.csv
│   ├── scb_issues.csv
│   └── ... (övriga resultatfiler)
│
├── logs/                             # Loggfiler
│
└── docs/                             # Dokumentation
    ├── BULK_MATCHER_GUIDE.md
    ├── BULK_MATCHING_QUICKSTART.md
    ├── DATABAS_GENOMLYSNING_RAPPORT.md
    ├── DEDUPLICATION_GUIDE.md
    ├── FAS1_RESULTATRAPPORT.md
    ├── SCB_ANALYS_README.md
    └── SCB_INTEGRATION_V2_GUIDE.md
```

## ⚙️ Konfiguration

**Första gången:** Kopiera exempel-konfigurationen och uppdatera med dina sökvägar:

```bash
cp config.example.ini config.ini
# Redigera config.ini med din faktiska certifikatsökväg
```

**config.ini** (gitignored - innehåller känsliga sökvägar):
```ini
[SCB]
cert_path = /path/to/your/scb_certificate.pem
database_path = databases/ai_companies.db
```

**Säkerhet:** `config.ini` är redan tillagd i `.gitignore` och kommer aldrig att commitas. Certifikatsökvägen delas inte publikt.

## 🚀 Snabbstart

### 1. Grundläggande SCB-integration

```bash
python3 scripts/scb/scb_integration_v2.py --limit 100
```

### 2. Retry-sökning med förbättrade varianter

```bash
python3 scripts/scb/retry_scb_search.py --input results/no_candidates_need_review.csv --limit 20
```

### 3. Importera manuella matchningar

```bash
python3 tools/import_manual_matches_direct.py --csv results/manual_matches_20251109_184431.csv
```

### 4. Bulk-matchning (1.8M SCB-företag)

**Ny funktion!** Matcha mot hela SCB:s företagsregister (1.8 miljoner företag):

```bash
python3 tools/bulk_scb_matcher.py \
    --bulk /path/to/scb_bulk.txt \
    --db databases/ai_companies.db
```

**Säkerhetsdesign:**
- ✅ Perfekta matchningar (100%) → Auto-godkända till databasen
- 🔍 Fuzzy matchningar (85-99%) → Exporteras till CSV för manuell granskning
- 📋 Granska och importera: `import_bulk_fuzzy_matches.py`

Se `BULK_MATCHING_QUICKSTART.md` för detaljerad guide!

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

### SCB API-integration (ursprunglig)
- ✓ **330 matchningar** från API-anrop
- Kombinerar automatisk fuzzy matching med manuell granskning
- Använder search_variants för förbättrad träffsäkerhet

### Bulk-matchning (ny!)
- ✓ **30 nya matchningar** från 1.8M företagsdataset
- 🎯 Hög precision genom granskning av fuzzy matches
- 📊 Totalt 360 företag berikade (32.3% av databasen)

### Kvalitetssäkring
- Manuella matchningar: 14 företag granskade
- High-score fuzzy matches: 9 företag granskade, 3 godkända
- Bulk fuzzy matches: Alla granskade innan import

## 🛠 Krav

```bash
pip install pandas fuzzywuzzy python-Levenshtein requests --break-system-packages
```

## 📝 Certifikat

SCB API kräver klientcertifikat från SCB. Konfigurera sökvägen i `config.ini`:

```ini
[SCB]
cert_path = /your/path/to/scb_certificate.pem
```

Alternativt, ändra med `--cert` flaggan vid körning.

## 🗄 Databas

**Tabell: scb_matches**
- `company_id` - FK till companies.id
- `matched` - 1/0
- `score` - Fuzzy match score (0-100)
- `city` - PostOrt från SCB
- `payload` - Fullständig SCB-data (JSON)

## 📚 Dokumentation

Se `docs/` för detaljerad dokumentation:
- `SCB_INTEGRATION_V2_GUIDE.md` - Guide för SCB API-integration
- `SCB_ANALYS_README.md` - Analys av resultat
- `BULK_MATCHER_GUIDE.md` - Komplett guide för bulk-matchning
- `BULK_MATCHING_QUICKSTART.md` - Snabbstart för bulk-matchning

## 🎯 Projektets status

**✅ Slutfört:**
- SCB API-integration med 330 matchningar
- Bulk-matchning mot 1.8M företag med 30 nya matchningar
- Total matchningsgrad: 32.3% (360 av 1113 företag)
- Alla tools dokumenterade och testade

**Kvarvarande omatchade företag (753):**
- Mestadels myndigheter, universitet och utländska företag
- Företag som inte finns i SCB:s företagsregister
- Möjlig framtida förbättring: Internationella företagsregister

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

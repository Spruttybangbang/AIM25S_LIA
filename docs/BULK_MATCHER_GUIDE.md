# Bulk SCB Matcher Guide

Detta script matchar företag utan SCB-data mot SCB:s bulk-fil (1.8M företag).

## 🎯 Syfte

- Matcha de 753 företag som saknar SCB-data
- Berika databasen med grundläggande SCB-information
- Fokusera på svenska företag som finns i bulk-filen

## 📋 Förberedelser

### 1. Kopiera filer till din Mac

```bash
# Skapa en arbetsmapp
mkdir -p ~/scb_matching
cd ~/scb_matching

# Kopiera databasen (från din project location)
cp /path/to/AIM25S_LIA/ai_companies.db .

# Bulk-filen har du redan på:
# /Users/linuslord/python/AIM25S/Discord/bulk/scb_bulk.txt
```

### 2. Installera dependencies

```bash
pip install fuzzywuzzy python-Levenshtein
```

## 🚀 Användning

### Test-körning (dry-run, 20 företag)

```bash
python3 tools/bulk_scb_matcher.py \
    --bulk /Users/linuslord/python/AIM25S/Discord/bulk/scb_bulk.txt \
    --db ai_companies.db \
    --limit 20 \
    --dry-run
```

**Detta kommer att:**
- Läsa bulk-filen (tar ~1-2 minuter för 1.8M rader)
- Testa matchning på 20 företag
- Visa resultat utan att spara till databasen

### Full körning

```bash
python3 tools/bulk_scb_matcher.py \
    --bulk /Users/linuslord/python/AIM25S/Discord/bulk/scb_bulk.txt \
    --db ai_companies.db
```

**Detta kommer att:**
- Matcha alla 753 företag utan SCB-data
- Spara matchningar till databasen
- Generera statistik

### Endast svenska företag

Scriptet filtrerar automatiskt på `is_swedish = 1` eftersom utländska företag inte finns i SCB:s register.

## 📊 Vad händer?

### Matchningsstrategier

1. **Org.nr-matchning (100% score)** → Auto-godkänd
   - Försöker extrahera org.nr från website/metadata
   - Matchar direkt mot PeOrgNr i bulk-filen
   - Läggs direkt i databasen

2. **Exakt namnmatchning (100% score)** → Auto-godkänd
   - Normaliserar namn (tar bort "AB", "Aktiebolag", etc.)
   - Matchar exakt mot företagsnamn
   - Läggs direkt i databasen

3. **Fuzzy namnmatchning (85-99% score)** → Kräver granskning
   - Använder Levenshtein-distans
   - Tröskelvärde: 85
   - Exporteras till CSV för manuell granskning
   - **VIKTIGT:** Kan innehålla felaktiga matchningar!

### Data som läggs till

För varje matchning läggs följande information till i `scb_matches`:

```json
{
  "PeOrgNr": "165591305098",
  "Namn": "Företagsnamnet AB",
  "FtgStat": "1",  // 0=aldrig verksam, 1=verksam, 9=ej verksam
  "JurForm": "49",  // Juridisk form kod
  "Gatuadress": "Företagsgatan 1",
  "PostNr": "123 45",
  "PostOrt": "Stockholm",
  "RegDatKtid": "20200101",  // Registreringsdatum
  "Ng1": "62010",  // SNI-kod näringsgren 1
  "Ng2": "",       // SNI-kod näringsgren 2
  "Ng3": "",       // etc.
  "Ng4": "",
  "Ng5": ""
}
```

## 📈 Förväntat resultat

Baserat på tidigare körningar:

- **Perfekta matchningar (100%)**: ~100-200 företag → Auto-godkända
- **Fuzzy matchningar (85-99%)**: ~100-200 företag → CSV för granskning
- **Ingen matchning**: ~400-500 företag
  - Myndigheter/Universitet (finns ej i företagsregistret)
  - Utländska företag (finns ej i svenska registret)
  - Företag utan orgnr eller extremt annorlunda namn

**Total förväntat berikande**: ~200-400 företag efter granskning

## ⚠️ Viktigt

### Performance

- **Första gången**: Långsamt (1-2 minuter att läsa bulk-filen)
- **Memory**: ~500MB RAM för index
- **Fuzzy matching**: Kan ta 5-10 sekunder per företag

### Efter körning

#### Steg 1: Perfekta matchningar
Dessa är redan i databasen - ingen åtgärd krävs!

#### Steg 2: Granska fuzzy matches

```bash
# Öppna CSV:n för granskning
open results/bulk_fuzzy_matches_YYYYMMDD_HHMMSS.csv
```

**Granskningsprocess:**
1. Öppna CSV:n i Excel/Numbers/Google Sheets
2. Granska varje rad:
   - Jämför `company_name` med `matched_name`
   - Kolla `score` (högre = säkrare)
   - Verifiera `city` och `orgnr` om möjligt
3. **Radera felaktiga matchningar** från CSV:n
4. Spara den granskade filen

#### Steg 3: Importera godkända fuzzy matches

```bash
python3 tools/import_bulk_fuzzy_matches.py \
    --csv results/bulk_fuzzy_matches_YYYYMMDD_HHMMSS.csv \
    --db ai_companies.db
```

**Flaggor:**
- `--dry-run` - Test utan att spara till databasen
- `--min-score 90` - Importera endast matches med score >= 90

#### Steg 4: Kopiera tillbaka databasen (om du jobbar med kopia)

```bash
cp ai_companies.db /path/to/AIM25S_LIA/
```

## 🔍 Exempel på output

```
📂 Läser bulk-fil: /Users/linuslord/.../scb_bulk.txt
   Läst 100,000 rader...
   Läst 200,000 rader...
   ...
✅ Läst 1,802,936 rader
   Org.nr index: 1,654,321 företag
   Namn prefix index: 8,432 prefix

🔍 Bearbetar 753 företag...
======================================================================
✅ [1/753] Layke Analytics
   Matchad med: LAYKE ANALYTICS AB
   Score: 100 | Type: exact_name
   Org.nr: 165591234567 | Status: 1
   → AUTO-GODKÄND (perfekt match)

🔶 [2/753] Knowing Company
   Matchad med: KNOWING COMPANY AB
   Score: 95 | Type: fuzzy
   Org.nr: 165598765432 | Status: 1
   → Behöver granskas (fuzzy match)

❌ [50/753] NVIDIA - Ingen matchning
...

======================================================================
📊 MATCHNINGSRESULTAT
======================================================================
Totalt företag:      753
Perfect matches:     187 (100% score) → AUTO-GODKÄNDA
Fuzzy matches:       124 (85-99% score) → KRÄVER GRANSKNING
Ingen matchning:     442
Skippade:            0
======================================================================

💾 Sparar 187 perfekta matchningar till databasen...
✅ Sparat!

📋 Exporterade 124 fuzzy matches till:
   results/bulk_fuzzy_matches_20251110_143022.csv

⚠️  VIKTIGT: Granska dessa manuellt innan import!
   Använd sedan: tools/import_bulk_fuzzy_matches.py
```

## 🐛 Troubleshooting

### "File not found"
- Kontrollera att sökvägen till bulk-filen är korrekt
- Använd absolut sökväg

### "Memory error"
- Bulk-filen är stor (250 MB)
- Kräver ~500 MB RAM
- Stäng andra program

### "Slow fuzzy matching"
- Detta är normalt för stora datamängder
- Använd `--limit` för att testa först

## 📚 Nästa steg

Efter matchningen:
1. Granska resultat i `scb_matches` tabell
2. Exportera rapport med nya matchningar
3. Uppdatera dokumentation
4. Commit och push till git

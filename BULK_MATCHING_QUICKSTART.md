# 🚀 Snabbstart: Bulk-matchning

Detta är en enkel guide för att köra bulk-matchningen på din Mac.

## ⚡ Quick Steps

### 1. Förbered miljön

```bash
# Gå till projektet
cd ~/python/AIM25S/Discord/bulk  # eller var du har bulk-filen

# Kontrollera att bulk-filen finns
ls -lh scb_bulk.txt
# Du bör se en fil på ~250 MB
```

### 2. Kör scriptet (dry-run först)

Det enklaste sättet är att köra scriptet direkt från din Mac:

```bash
# Test med 20 företag (ingen databas-uppdatering)
python3 /path/to/AIM25S_LIA/tools/bulk_scb_matcher.py \
    --bulk scb_bulk.txt \
    --db /path/to/AIM25S_LIA/ai_companies.db \
    --limit 20 \
    --dry-run
```

**Tips:** Byt ut `/path/to/AIM25S_LIA` med den faktiska sökvägen där du har projektet.

### 3. Kör full matchning

Om test-körningen ser bra ut:

```bash
# Full körning på alla 753 företag
python3 /path/to/AIM25S_LIA/tools/bulk_scb_matcher.py \
    --bulk scb_bulk.txt \
    --db /path/to/AIM25S_LIA/ai_companies.db
```

## 📊 Vad händer?

1. **Läsning (1-2 min):** Scriptet läser 1.8M företag från bulk-filen
2. **Indexering:** Bygger snabba lookup-index
3. **Matchning:** Matchar dina 753 företag mot bulk-filen
4. **Sparar:** Uppdaterar databasen med nya matchningar

## ✅ Förväntat resultat

Scriptet delar upp matchningar i två kategorier:

### 🟢 Perfekta matchningar (100% score)
- Läggs **automatiskt** i databasen
- Org.nr-matchning eller exakt namnmatchning
- Förväntad mängd: ~100-200 företag

### 🟡 Fuzzy matchningar (85-99% score)
- Exporteras till **CSV för manuell granskning**
- Förväntad mängd: ~100-200 företag
- **VIKTIGT:** Granska dessa innan import!

### ❌ Ingen matchning
- Myndigheter/universitet (finns ej i företagsregistret)
- Utländska företag
- Förväntad mängd: ~400-500 företag

## 🔧 Alternativ: Kopiera databas först

Om du föredrar att jobba med en kopia:

```bash
# Skapa arbetsmapp
mkdir -p ~/scb_work
cd ~/scb_work

# Kopiera databas
cp /path/to/AIM25S_LIA/ai_companies.db .

# Kör matchning
python3 /path/to/AIM25S_LIA/tools/bulk_scb_matcher.py \
    --bulk ~/python/AIM25S/Discord/bulk/scb_bulk.txt \
    --db ai_companies.db

# Kopiera tillbaka när du är nöjd
cp ai_companies.db /path/to/AIM25S_LIA/
```

## ❓ Problem?

**"command not found: python3"**
- Försök med `python` istället

**"No module named 'fuzzywuzzy'"**
```bash
pip install fuzzywuzzy python-Levenshtein
```

**"File not found"**
- Använd absoluta sökvägar
- Kontrollera att bulk_scb.txt ligger där du tror

## 📝 Efter matchningen

### Steg 1: Granska fuzzy matches

Om scriptet exporterade fuzzy matches:

```bash
# Öppna CSV:n i Excel/Numbers
open results/bulk_fuzzy_matches_YYYYMMDD_HHMMSS.csv
```

Granska varje rad:
- **Korrekt matchning?** Behåll raden
- **Felaktig matchning?** Radera raden

### Steg 2: Importera godkända matchningar

```bash
python3 /path/to/AIM25S_LIA/tools/import_bulk_fuzzy_matches.py \
    --csv results/bulk_fuzzy_matches_YYYYMMDD_HHMMSS.csv \
    --db /path/to/AIM25S_LIA/ai_companies.db
```

**Flaggor:**
- `--dry-run` - Test utan att spara
- `--min-score 90` - Importera endast matches med score >= 90

### Steg 3: Klart!

1. Perfekta matchningar är redan i databasen
2. Granskade fuzzy matches är importerade
3. Databasen är berikad med SCB-data! 🎉

---

Se `docs/BULK_MATCHER_GUIDE.md` för detaljerad dokumentation.

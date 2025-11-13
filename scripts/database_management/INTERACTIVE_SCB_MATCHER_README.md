# Interaktiv SCB Matcher

Ett interaktivt script för att matcha företag från din databas mot SCB:s företagsregister.

## Funktioner

✅ **Läser CSV med företags-ID:n**
- En company_id per rad

✅ **Interaktiv matchning**
- Visar best match + övriga kandidater sorterade efter fuzzy score
- Låter dig välja rätt match
- Möjlighet att söka med egen term om ingen stämmer
- Spara och avbryt när som helst

✅ **Exporterar komplett SCB-data**
- Alla SCB-variabler i separata kolumner (inte JSON-klump)
- Innehåller org.nr, adress, SNI-kod, antal anställda, etc.

## Installation

```bash
# Installera dependencies (om du inte redan har dem)
pip install fuzzywuzzy python-Levenshtein requests
```

## Användning

### 1. Skapa en input-CSV

Skapa en CSV-fil med företags-ID:n du vill matcha:

**input.csv:**
```csv
company_id
123
456
789
```

### 2. Kör scriptet

```bash
cd scripts/database_management
python3 interactive_scb_matcher.py input.csv
```

### 3. Interaktiv matchning

För varje företag visas:

```
======================================================================
# FÖRETAG 123: Spotify AB
# Type: corporation | Website: https://spotify.com
======================================================================

🔍 Söker i SCB efter: 'Spotify AB'...

======================================================================
Sökresultat för: Spotify AB
======================================================================

[1] Spotify AB
    Ort: Stockholm
    Org.nr: 556703-7495
    Score: 100/100

[2] Spotify Sweden AB
    Ort: Stockholm
    Org.nr: 559067-9071
    Score: 89/100

... och 3 fler träffar

======================================================================
Välj alternativ:
  [1-10] - Välj en kandidat
  [s] - Skip (ingen stämmer, gå vidare)
  [n] - Ny sökning (ange egen sökterm)
  [q] - Quit (spara och avbryt)
======================================================================

Ditt val: _
```

### 4. Alternativ

**Välj en kandidat (1-10):**
```
Ditt val: 1

✅ Du valde: Spotify AB
Bekräfta? (y/n): y

✅ Match sparad! (Totalt: 1 bekräftade)
```

**Skip (ingen stämmer):**
```
Ditt val: s
⏭️  Hoppar över detta företag
```

**Ny sökning (egen sökterm):**
```
Ditt val: n

Ange ny sökterm: Spotify Sweden

🔍 Söker i SCB efter: 'Spotify Sweden'...
[Visar nya resultat...]
```

**Quit (spara och avbryt):**
```
Ditt val: q
🛑 Användaren valde att avbryta

✅ Sparade 5 matcher till: scb_matches_confirmed_20251113_010000.csv
```

## Output-format

Scriptet sparar bekräftade matcher i en CSV med följande kolumner:

### Företagsinformation (från din databas):
- `company_id`
- `company_name`
- `company_type`
- `company_website`
- `company_location_city`
- `company_owner`

### Matchningsinformation:
- `fuzzy_score` - Hur bra matchningen är (0-100)

### SCB-data (alla i separata kolumner):
- `scb_företagsnamn`
- `scb_orgnr`
- `scb_postort`
- `scb_kommun`
- `scb_län`
- `scb_adress`
- `scb_postnr`
- `scb_telefon`
- `scb_sni_kod`
- `scb_sni_text`
- `scb_juridisk_form`
- `scb_antal_anställda`
- `scb_omsättning`

## Exempel på output

**scb_matches_confirmed_20251113_010000.csv:**
```csv
company_id,company_name,fuzzy_score,scb_företagsnamn,scb_orgnr,scb_postort,scb_kommun,...
123,Spotify AB,100,Spotify AB,556703-7495,Stockholm,Stockholm,Drottninggatan 1,...
456,Klarna AB,95,Klarna Bank AB,556737-0431,Stockholm,Stockholm,Sveavägen 46,...
```

## Tips

### Hantera många träffar
Om SCB returnerar många träffar (>100), överväg att:
- Lägg till "AB" i söktermen: `Företagsnamn AB`
- Lägg till stad: `Företagsnamn Stockholm`
- Använd alternativet "n" för ny sökning

### Best practices
1. Börja med ett litet test (5-10 företag)
2. Använd "s" (skip) för företag du är osäker på
3. Använd "q" (quit) för att spara progress och ta paus
4. Granska output-CSV:n innan du importerar till databasen

## Felsökning

### "Certifikat hittades inte"
Du behöver SCB-certifikatet i mappen: `SCB/certifikat/`

### "Databas hittades inte"
Scriptet förväntar sig databasen i: `databases/ai_companies.db`

### Anpassa paths med config.ini
Skapa `scripts/config.ini`:
```ini
[SCB]
database_path = /custom/path/to/ai_companies.db
cert_path = /custom/path/to/cert.pem
```

## Relaterade scripts

- **analyze_companies.py** - Analysera specifika företag (icke-interaktivt)
- **scb_integration_v2.py** - Bulk SCB-enrichment (automatisk matchning)

---

**Skapad:** 2025-11-13
**Version:** 1.0

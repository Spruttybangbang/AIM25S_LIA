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

✅ **AUTO-SAVE funktionalitet** 💾
- Sparar automatiskt efter VARJE bekräftad match
- Data går aldrig förlorad vid crash eller avbrott
- CSV uppdateras kontinuerligt

✅ **Robust felhantering**
- Hanterar oväntade API-responses graciöst
- Skippar problematiska företag istället för att krascha
- Fortsätter arbeta även vid nätverksfel

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
  [1-5] - Välj en kandidat
  [s] - Skip (ingen stämmer, gå vidare)
  [n] - Ny sökning (ange egen sökterm)
  [q] - Quit (spara och avbryt)
======================================================================

Ditt val: _
```

**OBS:** Scriptet begränsar SCB API-anropet till **max 5 resultat** (via `MaxRowLimit`-parameter). Detta förhindrar överbelastning av SCB API och håller sökningarna snabba. Om de 5 resultaten inte innehåller rätt företag, använd alternativet [n] för att söka med mer specifikt namn (t.ex. lägg till "AB" eller stad).

### 4. Alternativ

**Välj en kandidat (1-5):**
```
Ditt val: 1

✅ Match sparad: Spotify AB (Totalt: 1 bekräftade)
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

### SCB-data (alla i separata kolumner - samma som scb_enrichment-tabellen):
- `organization_number` - Organisationsnummer
- `scb_company_name` - Officiellt företagsnamn från SCB
- `co_address` - C/o-adress
- `post_address` - Postadress
- `post_code` - Postnummer
- `post_city` - Postort
- `municipality_code` - Kommunkod
- `municipality` - Kommun
- `county_code` - Länskod
- `county` - Län
- `num_workplaces` - Antal arbetsställen
- `employee_size_code` - Storleksklasskkod (anställda)
- `employee_size` - Storleksklass (anställda)
- `company_status_code` - Företagsstatuskod
- `company_status` - Företagsstatus
- `legal_form_code` - Juridisk formkod
- `legal_form` - Juridisk form
- `start_date` - Startdatum
- `registration_date` - Registreringsdatum
- `industry_1_code` - SNI-kod 1
- `industry_1` - SNI-text 1
- `industry_2_code` - SNI-kod 2
- `industry_2` - SNI-text 2
- `revenue_year` - Omsättningsår
- `revenue_size_code` - Omsättningsklasskkod
- `revenue_size` - Omsättningsklass
- `phone` - Telefon
- `email` - E-post
- `employer_status_code` - Arbetsgivarstatuskod
- `employer_status` - Arbetsgivarstatus
- `vat_status_code` - Momsstatuskod
- `vat_status` - Momsstatus
- `export_import` - Export/Import (J/N)

## Exempel på output

**scb_matches_confirmed_20251113_010000.csv:**
```csv
company_id,company_name,fuzzy_score,organization_number,scb_company_name,post_city,municipality,employee_size,industry_1,...
123,Spotify AB,100,556703-7495,Spotify AB,STOCKHOLM,Stockholm,1000-1499 anställda,62010 Dataprogrammering,...
456,Klarna AB,95,556737-0431,Klarna Bank AB,STOCKHOLM,Stockholm,500-999 anställda,64190 Banker,...
```

## Tips

### Om de 5 resultaten inte räcker
Scriptet begränsar till max 5 resultat från SCB. Om rätt företag inte finns bland dessa:
- Använd alternativet [n] för ny sökning med mer specifikt namn
- Lägg till "AB" i söktermen: `Företagsnamn AB`
- Lägg till stad: `Företagsnamn Stockholm`
- Lägg till org.nr om känt: `Företagsnamn 556123-4567`

### Data-säkerhet 💾
- **Auto-save:** Varje match sparas OMEDELBART till CSV
- **Ingen data-förlust:** Vid crash finns alla tidigare matchningar i CSV:n
- **Säkert avbrott:** Tryck Ctrl+C eller [q] - data är redan sparad!
- **Kontinuerlig uppdatering:** CSV:n uppdateras efter varje match

### Best practices
1. Börja med ett litet test (5-10 företag)
2. Använd "s" (skip) för företag du är osäker på
3. Använd "q" (quit) för att spara progress och ta paus
4. Granska output-CSV:n innan du importerar till databasen
5. Vid crash: CSV:n innehåller alla tidigare matchningar!

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

# Batch SCB API Query by Organization Number

Ett automatiserat script för att hämta företagsinformation från SCB:s API baserat på organisationsnummer och företagsnamn.

## Översikt

Detta script:
- ✅ Läser en CSV-fil med organisationsnummer OCH företagsnamn
- ✅ Söker i SCB:s API på företagsnamn (namnet är sökbart i API:et)
- ✅ Validerar att rätt organisationsnummer hittades i resultatet
- ✅ Hämtar alla tillgängliga variabler (adress, anställda, SNI-koder, etc.)
- ✅ Sparar lyckade requests i en CSV-fil
- ✅ Sparar misslyckade requests i en separat CSV-fil
- ✅ Inget manuellt godkännande behövs (helt automatiskt)

## ⚠️ Viktigt: Varför behövs företagsnamn?

SCB:s API stödjer **inte** direktsökning på organisationsnummer. Variabeln "OrgNr" finns bara i **response-data**, inte som sökbar variabel.

Scriptet löser detta genom att:
1. Söka på företagsnamn (variabel "Namn" som fungerar i API:et)
2. Validera att rätt organisationsnummer finns i resultatet
3. Returnera företaget om org.nr matchar, annars fel

## Installation

```bash
# Installera dependencies
pip install requests

# Inga ytterligare dependencies behövs (använder standard library)
```

## Användning

### 1. Skapa input-CSV

Skapa en CSV-fil med organisationsnummer OCH företagsnamn:

**input_orgnr.csv:**
```csv
organization_number,company_name
5567037485,Spotify AB
5590691811,Lexplore AB
5592675952,LINKAI Technologies AB
5592462591,Maigon AB
```

**Format:**
- Kolumnnamn: `organization_number,company_name`
- Bindestreck i org.nr är valfritt (scriptet hanterar båda: `556703-7485` och `5567037485`)
- Företagsnamnet används för att söka i SCB API
- Org.nr används för att validera rätt företag hittades

**Tips: Exportera från databas**

Om du har org.nr i din databas kan du exportera CSV direkt:

```sql
-- Från scb_enrichment tabell
SELECT organization_number,
       COALESCE(scb_company_name, '') as company_name
FROM scb_enrichment
WHERE organization_number IS NOT NULL
ORDER BY organization_number;
```

Eller från confirmed matches CSV:

```python
import pandas as pd
df = pd.read_csv('scb_matches_confirmed_20251114_105204.csv')
df[['organization_number', 'scb_company_name']].rename(
    columns={'scb_company_name': 'company_name'}
).to_csv('input_orgnr.csv', index=False)
```

### 2. Kör scriptet

```bash
cd scripts/scb
python3 batch_scb_by_orgnr.py input_orgnr.csv
```

### 3. Output

Scriptet skapar två filer med tidsstämpel:

**scb_success_YYYYMMDD_HHMMSS.csv** - Lyckade requests:
```csv
organization_number,scb_company_name,post_city,municipality,employee_size,industry_1,...
5567037485,Spotify AB,STOCKHOLM,Stockholm,1000-1499,62010 Dataprogrammering,...
5590691811,Lexplore AB,STOCKHOLM,Stockholm,5-9 anställda,85600 Stödverksamhet för utbildningsväsendet,...
```

**scb_failed_YYYYMMDD_HHMMSS.csv** - Misslyckade requests:
```csv
organization_number,error_message,timestamp
9999999999,Inget företag hittades med detta organisationsnummer,2025-11-14T10:30:00
```

## Output-kolumner

### Lyckade requests (success CSV)

Alla SCB-variabler i separata kolumner:

**Företagsinformation:**
- `organization_number` - Organisationsnummer
- `scb_company_name` - Företagsnamn från SCB
- `company_status` - Företagsstatus (Verksam/Avvecklad)
- `legal_form` - Juridisk form (t.ex. "Övriga aktiebolag")

**Adress:**
- `co_address` - C/o-adress
- `post_address` - Postadress
- `post_code` - Postnummer
- `post_city` - Postort
- `municipality_code` - Kommunkod
- `municipality` - Kommun
- `county_code` - Länskod
- `county` - Län

**Storlek:**
- `num_workplaces` - Antal arbetsställen
- `employee_size_code` - Storleksklasskkod (anställda)
- `employee_size` - Storleksklass (t.ex. "5-9 anställda", "100-199")
- `revenue_year` - Omsättningsår
- `revenue_size_code` - Omsättningsklasskkod
- `revenue_size` - Omsättningsklass

**Bransch:**
- `industry_1_code` - SNI-kod 1 (t.ex. "62010")
- `industry_1` - SNI-text 1 (t.ex. "Dataprogrammering")
- `industry_2_code` - SNI-kod 2 (sekundär bransch)
- `industry_2` - SNI-text 2

**Datum:**
- `start_date` - Startdatum
- `registration_date` - Registreringsdatum

**Kontakt:**
- `phone` - Telefonnummer
- `email` - E-postadress

**Status:**
- `employer_status_code` - Arbetsgivarstatuskod
- `employer_status` - Arbetsgivarstatus
- `vat_status_code` - Momsstatuskod
- `vat_status` - Momsstatus
- `export_import` - Export/Import-markering (J/N)

### Misslyckade requests (failed CSV)

- `organization_number` - Organisationsnumret som misslyckades
- `error_message` - Beskrivning av felet
- `timestamp` - När felet inträffade

## Exempel-körning

```bash
$ python3 batch_scb_by_orgnr.py companies_orgnr.csv

📖 Läser företagsdata från: companies_orgnr.csv
✅ Hittade 150 företag att processa

💾 Lyckade requests sparas till: scb_success_20251114_103000.csv
💾 Misslyckade requests sparas till: scb_failed_20251114_103000.csv

Vill du börja hämta data för 150 företag? (y/n): y

======================================================================
STARTAR BATCH-KÖRNING
======================================================================

[1/150] Spotify AB (5567037485)
  ✅ Spotify AB - STOCKHOLM

[2/150] Lexplore AB (5590691811)
  ✅ Lexplore AB - STOCKHOLM

[3/150] Fel Företag AB (9999999999)
  ❌ Hittade 0 företag med namnet 'Fel Företag AB' men inget med org.nr 9999999999

...

======================================================================
SPARAR RESULTAT
======================================================================

✅ Sparade 148 lyckade requests till: scb_success_20251114_103000.csv
⚠️  Sparade 2 misslyckade requests till: scb_failed_20251114_103000.csv

======================================================================
SAMMANFATTNING
======================================================================
Totalt organisationsnummer: 150
Lyckade requests: 148 (98.7%)
Misslyckade requests: 2 (1.3%)
Körtid: 76.5 sekunder (1.3 minuter)
Genomsnittlig tid per request: 0.51 sekunder

✅ Klart!
```

## Tekniska detaljer

### Rate Limiting

- Scriptet väntar **0.5 sekunder** mellan varje API-anrop
- SCB rekommenderar max 2 requests/sekund
- För 150 organisationsnummer tar det ca 75 sekunder (1.25 minuter)
- För 1000 organisationsnummer tar det ca 500 sekunder (8.3 minuter)

### API-sökning

Scriptet söker i SCB med följande payload:

```json
{
  "Företagsstatus": "1",
  "Registreringsstatus": "1",
  "variabler": [
    {
      "Varde1": "Spotify AB",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "Namn"
    }
  ]
}
```

- `Företagsstatus: "1"` = Endast verksamma företag
- `Registreringsstatus: "1"` = Endast registrerade
- `Operator: "Innehaller"` = Partiell matchning på företagsnamn
- `Variabel: "Namn"` = Sök på företagsnamn (OrgNr är **inte** en sökbar variabel!)

**Validering av org.nr:**
Efter att SCB returnerar resultat, loopar scriptet igenom alla träffar och letar efter en som har matchande organisationsnummer.

### Felhantering

Scriptet hanterar följande fel graciöst:

- **HTTP-fel** (401, 403, 500, etc.) - Sparas i failed CSV
- **Nätverksfel** (timeout, connection error) - Sparas i failed CSV
- **Inga resultat** - Sparas i failed CSV med meddelande "Inget företag hittades"
- **JSON-parsningsfel** - Sparas i failed CSV
- **Oväntat API-format** - Sparas i failed CSV

Scriptet fortsätter alltid att processa nästa organisationsnummer även vid fel.

## Konfiguration

### Certifikat-path

Scriptet letar efter SCB-certifikatet i följande ordning:

1. `config.ini` i `scripts/` eller `scripts/scb/`
2. Default path: `../../../SCB/certifikat/Certifikat_SokPaVar_*.pem`

**Skapa config.ini** (valfritt):
```ini
[SCB]
cert_path = /custom/path/to/certificate.pem
```

### Rate Limit

Ändra `RATE_LIMIT_DELAY` i scriptet:

```python
RATE_LIMIT_DELAY = 0.5  # Sekunder mellan anrop
```

- Rekommenderat: 0.5 sekunder (2 req/s)
- Snabbare: 0.3 sekunder (3.3 req/s) - risk för rate limiting
- Långsammare: 1.0 sekund (1 req/s) - säkrare

## Vanliga frågor

### Vad är skillnaden mot interactive_scb_matcher.py?

| Feature | interactive_scb_matcher.py | batch_scb_by_orgnr.py |
|---------|---------------------------|----------------------|
| Input | company_id (från databas) | organization_number + company_name (CSV) |
| Sökning | Fuzzy matching på företagsnamn | Sökning på namn + validering av org.nr |
| Användare | Manuellt godkännande per företag | Helt automatiskt |
| Output | Bekräftade matcher med fuzzy score | Alla funna företag med validerat org.nr |
| Use case | Kvalitetssäkrad matchning | Bulk data-hämtning med org.nr-validering |

### Varför behöver jag företagsnamn OCH org.nr?

SCB API stödjer **inte** sökning direkt på organisationsnummer. Endast företagsnamn är en sökbar variabel.

Scriptet använder företagsnamnet för att söka, och validerar sedan att rätt org.nr finns i resultatet.

### Vad händer om företagsnamnet ger många träffar?

Scriptet loopar igenom alla träffar från SCB och letar efter den som har matchande org.nr. Om inget företag med rätt org.nr hittas sparas det som misslyckat.

### Vad händer om ett org.nr inte finns i SCB?

Det sparas i `scb_failed_*.csv` med ett felmeddelande som visar vilka org.nr som hittades för företagsnamnet.

### Kan jag använda org.nr med bindestreck?

Ja! Scriptet hanterar båda formaten:
- `556703-7485` ✅
- `5567037485` ✅

### Hur importerar jag resultatet till databasen?

Se `scripts/database_management/import_scb_to_db.py` (om den finns) eller använd:

```sql
-- Importera från CSV till tabell
COPY scb_enrichment (
    organization_number, scb_company_name, post_city, ...
)
FROM '/path/to/scb_success_20251114_103000.csv'
DELIMITER ',' CSV HEADER;
```

## Relaterade scripts

- **interactive_scb_matcher.py** - Interaktiv matchning med fuzzy search
- **scb_integration_v2.py** - Bulk enrichment från databas
- **analyze_companies.py** - Analysera specifika företag

## Felsökning

### "Certifikat hittades inte"

```
❌ Fel: Certifikat hittades inte: /path/to/cert.pem
```

**Lösning:**
1. Kontrollera att certifikatet finns i `SCB/certifikat/`
2. Eller skapa `config.ini` med rätt path

### "CSV måste ha kolumnerna 'organization_number' och 'company_name'"

```
⚠️  CSV måste ha kolumnerna 'organization_number' och 'company_name'. Hittade: ['orgnr', 'company']
```

**Lösning:**
Döp om CSV-kolumnerna till exakt `organization_number` och `company_name`.

### Många "Inget företag hittades"

**Möjliga orsaker:**
- Organisationsnumret är felaktigt
- Företaget är avregistrerat (scriptet söker endast verksamma)
- Organisationsnumret finns inte i SCB:s register

**Lösning:**
Kontrollera organisationsnumren manuellt på [Bolagsverket](https://bolagsverket.se/).

---

**Skapad:** 2025-11-14
**Version:** 1.0
**Baserat på:** SCB_INTEGRATION_COMPLETE_GUIDE.md, interactive_scb_matcher.py

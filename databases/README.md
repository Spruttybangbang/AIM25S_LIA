# Databaser

Denna mapp innehåller projektets SQLite-databaser.

## Filer

- **ai_companies.db** - Huvuddatabas med fokuserade AI-företag (ca 906 företag)
- **ai_others.db** - Sekundär databas med universitet, forskningsinstitut och stödjande organisationer (ca 173 företag)

## Schema

Båda databaserna delar samma schema:
- `companies` - Företagsinformation
- `sectors` - Sektorer/branscher
- `company_sectors` - Koppling mellan företag och sektorer
- `domains` - Domäner/områden
- `company_domains` - Koppling mellan företag och domäner
- `ai_capabilities` - AI-kompetenser
- `company_ai_capabilities` - Koppling mellan företag och AI-kompetenser
- `dimensions` - Dimensioner
- `company_dimensions` - Koppling mellan företag och dimensioner
- `scb_matches` - SCB-matchningar
- `scb_enrichment` - Berikad data från SCB

## SCB-berikning - Status och historik

### Senaste uppdatering: 2025-11-14

**Uppdatering med 117 nya SCB-enrichments (scb_matches_confirmed_20251114_105204.csv):**
- 72 nya insättningar i `scb_enrichment`
- 45 uppdateringar av befintliga enrichments
- Total SCB-täckning: 74.86% → 84.81% (+9.95 pp)

**Täckning per typ efter senaste uppdatering:**
- corporation: 85.03% → 85.03% (+0.00 pp)
- publicsector: 84.52% → 84.52% (+0.00 pp)
- startup: 64.26% → 85.89% (+21.63 pp)
- supplier: 82.50% → 82.50% (+0.00 pp)

**Kumulativ förbättring sedan 2025-11-13:**
- Totalt: 60.22% → 84.81% (+24.59 pp)
- 542 → 614 företag med SCB-data
- Bearbetade 305 företag från 5 CSV-filer
- 178 nya insättningar, 127 uppdateringar

### Genomgångsstatus

**Genomgångna company_ids: 1-2410**
Alla company_ids från 1 till och med 2410 har granskats manuellt i kronologisk ordning för SCB-matchning.

**Återstående: company_ids 2411+**
Planeras att genomföras nästa dag.

### Rensning av företag utan SCB-data

**VIKTIGT:** Företag som inte har SCB-data efter manuell granskning kommer behöva tas bort från databasen i framtiden (INTE NU). Detta gäller företag som är:
- Irrelevanta för projektet
- Inte längre aktiva/existerar

**UNDANTAG - Företag med & i namnet:**
Ett fåtal företag (max en handfull) har & i företagsnamnet vilket skapar problem i SCB API-sökningen. För dessa behövs en lösning:
- Alternativ sökstrategi i SCB API
- Sökning direkt på organisationsnummer istället för företagsnamn

## Backup

Säkerhetskopiera dessa filer regelbundet!

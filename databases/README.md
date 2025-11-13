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

### Senaste uppdatering: 2025-11-13/14

**Uppdatering med 106 nya SCB-enrichments:**
- Bearbetade 188 företag från 4 nya CSV-filer
- 106 nya insättningar i `scb_enrichment`
- 82 uppdateringar av befintliga enrichments
- Total SCB-täckning: 60.22% → 74.86% (+14.64 pp)

**Täckning per typ:**
- corporation: 73.47% → 85.03% (+11.56 pp)
- publicsector: 59.52% → 84.52% (+25.00 pp)
- startup: 48.95% → 64.26% (+15.31 pp)
- supplier: 71.88% → 82.50% (+10.62 pp)

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

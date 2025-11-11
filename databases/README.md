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

## Backup

Säkerhetskopiera dessa filer regelbundet!

# Gamla CSV-Exports - Arkiv

Denna mapp innehåller äldre CSV-exports från databasen. De senaste exporterna finns i `/exports/` och `/results/`.

## Innehåll

### Exports från 2025-11-11
Exporterade från ai_companies.db:
- `companies_all_20251111_073002.csv` - Alla företag
- `companies_with_scb_20251111_073002.csv` - Företag med SCB-data
- `companies_without_scb_20251111_073002.csv` - Företag utan SCB-data

### Exports från 2025-11-12
Exporterade från ai_companies.db:
- `companies_all_20251112_*.csv` - Alla företag
- `companies_with_scb_20251112_*.csv` - Företag med SCB-data
- `companies_without_scb_20251112_*.csv` - Företag utan SCB-data

## Användning

Dessa filer är arkiverade och används normalt inte. För aktuell data, använd:
- De senaste exporterna i `/exports/`
- Kör export-scriptet på nytt: `python scripts/database_management/export_companies_to_csv.py`

## Radering

Dessa filer kan raderas när diskutrymme behövs. All data finns i databaserna och kan exporteras på nytt när som helst.

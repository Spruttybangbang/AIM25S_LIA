# Exports

Denna mapp innehåller exporterade CSV-filer från databasen.

## Filnamnkonvention

Filer namnges med timestamp: `companies_[kategori]_YYYYMMDD_HHMMSS.csv`

Exempel:
- `companies_all_20251111_073002.csv` - Alla företag
- `companies_with_scb_20251111_073002.csv` - Företag med SCB-data
- `companies_without_scb_20251111_073002.csv` - Företag utan SCB-data

## Generera nya exports

Använd export-scripts i `scripts/export/`:

```bash
# Exportera alla kategorier
python scripts/export/export_companies_to_csv.py

# Exportera endast företag utan SCB
python scripts/export/export_companies_without_scb.py
```

## .gitignore

CSV-filer i denna mapp kan vara stora och bör övervägas för `.gitignore` om de genereras ofta.

# Export-scripts

Scripts för att exportera data från databasen till olika format.

## Scripts

### export_companies_to_csv.py
Exporterar företag till CSV-filer:
- Alla företag
- Företag med SCB-data
- Företag utan SCB-data

**Användning:**
```bash
python scripts/export/export_companies_to_csv.py
```

**Output:** Filer sparas i `exports/` mappen med timestamp.

### export_companies_without_scb.py
Exporterar enbart företag utan SCB-matchning till CSV.

**Användning:**
```bash
python scripts/export/export_companies_without_scb.py
```

## CSV-format

Exporterade filer innehåller:
- Företagsinformation
- SCB-berikad data (om tillgänglig)
- Sektorer och domäner
- AI-kompetenser

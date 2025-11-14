# Migration Scripts - Arkiv

Denna mapp innehåller one-time migration scripts som användes för engångsuppgifter under projektets utveckling.

## Scripts

### update_db_paths.py
- **Syfte:** Uppdatera databassökvägar i alla Python-scripts efter mapomorganisering
- **Använd:** Vid en omorganisering av projektstrukturen
- **Status:** Färdigkörd, ej längre relevant för nuvarande struktur

### remove_ids_from_ai_companies.py
- **Syfte:** Ta bort 173 specifika company_ids från ai_companies.db
- **Funktionalitet:** Flyttade företag till ai_others.db
- **Hårdkodad lista:** 173 company_ids
- **Status:** Färdigkörd, migrering slutförd

### check_ids.py
- **Syfte:** Verifiera att company_ids flyttades korrekt
- **Funktionalitet:** Kontrollera vilken databas specifika ID:n finns i
- **Hårdkodad lista:** Samma 173 company_ids som ovan
- **Status:** Verifiering slutförd

### delete_companies.py
- **Syfte:** Permanent radera 34 specifika company_ids
- **Funktionalitet:** Visar företag och kräver 'DELETE' som bekräftelse
- **Hårdkodad lista:** 34 company_ids
- **Status:** Färdigkörd (antagligen)

## Varning

⚠️ **Kör INTE dessa scripts igen!** De innehåller hårdkodade ID-listor som gällde för specifika tidpunkter under projektets utveckling. Att köra dem nu skulle kunna skada databasen.

Dessa scripts bevaras endast för historik och dokumentation.

# Arkiv

Denna mapp innehåller arkiverade filer som inte längre används aktivt i projektet, men som bevaras för historik och referens.

## Undermappar

### migrations/
Innehåller one-time migration scripts som användes för engångsmigreringar och uppdateringar:
- `update_db_paths.py` - Uppdaterade databassökvägar efter omorganisering
- `remove_ids_from_ai_companies.py` - Tog bort 173 specifika company_ids från ai_companies.db
- `check_ids.py` - Verifiering av borttagning av company_ids
- `delete_companies.py` - Raderade 34 specifika company_ids

Dessa scripts är färdigkörda och behövs inte längre för den dagliga driften.

### old_exports/
Innehåller äldre CSV-exports från databasen. Endast de senaste exporterna behålls i `/exports/` och `/results/`.

Filer här är från:
- 2025-11-11 (från exports/)
- 2025-11-12 (från results/)

Kan raderas när diskutrymme behövs.

## Varför arkivera istället för att radera?

Dessa filer arkiveras istället för att raderas helt för att:
- Bevara projekthistorik
- Möjliggöra referens till gamla migreringar
- Kunna återskapa tidigare tillstånd om behov uppstår

Om diskutrymme blir ett problem kan dessa filer raderas permanent - all viktigt kod finns i git-historiken.

# SCB Matchnings-analys

## Översikt

Detta är en samling script för att analysera och hantera matchningar mellan din AI-företagsdatabas och SCB:s företagsregister.

## Filer som skapats

### Analysscript
- **`analyze_scb_issues.py`** - Huvudanalysscript som skapar en översikt
- **`explore_issues_interactive.py`** - Interaktivt script för djupare utforskning
- **`approve_good_matches.py`** - Script för att godkänna och lägga till matchningar i databasen

### Genererade datafiler
- **`analysis_low_scores.csv`** - Matchningar med låg poäng (sorterade)
- **`analysis_no_candidates.csv`** - Företag utan kandidater
- **`analysis_summary.csv`** - Sammanfattning av analysen

### Ursprungliga datafiler
- **`scb_issues.csv`** - Misslyckade matchningar från SCB API
- **`scb_matches.csv`** - Lyckade matchningar

## Snabbstart

### 1. Kör huvudanalysen
```bash
python3 analyze_scb_issues.py
```

Detta ger dig en översikt över:
- Totalt antal misslyckade matchningar
- Fördelning mellan "low_score" och "no_candidates"
- Top 20 matchningar med högst poäng
- Analys av företag utan kandidater
- Rekommendationer för nästa steg

### 2. Utforska data interaktivt
```bash
python3 -i explore_issues_interactive.py
```

Detta startar en Python REPL med förladdad data. Användbara funktioner:

```python
# Visa matchningar med hög poäng
show_high_score_matches(85)

# Sök efter ett företag
search_company('volvo')

# Få detaljerad info om ett företag
get_company_info(1322)

# Jämför namnlikhet
analyze_name_similarity('Volvo Group', 'VOLVO GROUP MEXICO')

# Visa statistik
show_stats_by_score_range()

# Hitta svenska företag bland no_candidates
swedish = find_swedish_companies_in_no_candidates()
```

### 3. Godkänn bra matchningar
```bash
python3 approve_good_matches.py
```

Detta script hjälper dig att:
- Auto-godkänna matchningar med mycket hög poäng (≥89)
- Manuellt granska matchningar med bra poäng (85-88)
- Lägga till godkända matchningar i databasen
- Uppdatera location_city för företagen

## Analysresultat

### Low Score Matchningar (31 st)

**Poängfördelning:**
- 89-100 (mycket bra): 3 st
- 85-88 (bra): 12 st
- 80-84 (OK): 8 st
- <80 (tveksam): 8 st

**Rekommendation:**
- ✅ **15 företag med poäng ≥ 85** är troligen korrekta matchningar
- ⚠️ **8 företag med poäng 80-84** behöver manuell granskning
- ❌ **8 företag med poäng <80** är tveksamma

#### Topp-kandidater för auto-godkännande:
1. **Saco** → SACON AKTIEBOLAG (91)
2. **Alstom** → Alstom Rail Sweden AB (91)
3. **NATO** → Naton AB (91)
4. **Smartr** → Smartrun AB (88)
5. **IDC** → IDCL INC AB (88)

### No Candidates (228 st)

**Kategorier:**
- 🌍 Utländska företag: 5 st (Google, Meta, DeepMind, etc.)
- 🔤 Akronymer/kortnamn: 7 st
- ⚡ Specialtecken i namnet: 38 st (rek.ai, rebase.energy, etc.)
- 📝 Normalnamn: 176 st

**Möjliga orsaker:**
1. Utländska företag (ej i SCB-registret)
2. Fel stavning eller företagsnamn i databasen
3. Företag som bytt namn
4. Nya startups som inte registrerats
5. Dotterbolag eller underleverantörer

## Arbetsflöde

### Steg 1: Auto-godkänn säkra matchningar
```bash
python3 approve_good_matches.py
# Välj alternativ 1: Auto-godkänn ≥89
```

### Steg 2: Manuell granskning
Granska matchningar med poäng 85-88 manuellt:
- Jämför företagsnamn
- Kolla webbplats/beskrivning
- Verifiera ort/location

### Steg 3: Undersök no_candidates
För "normalnamn" bland no_candidates:
1. Sök i [Bolagsverket](https://www.bolagsverket.se/)
2. Kolla om företaget har alternativa namn
3. Sök manuellt i SCB:s databas med andra söktermer

### Steg 4: Manuell sökning
För viktiga företag utan matchningar:
- Använd företagets organisationsnummer
- Sök på webbplats-domän
- Kolla företagets LinkedIn-sida

## Tips & Tricks

### Filtrera data i Python
```python
import pandas as pd

# Ladda data
low_scores = pd.read_csv('analysis_low_scores.csv')

# Matchningar i Stockholm
stockholm = low_scores[low_scores['PostOrt'] == 'STOCKHOLM']

# Höga poäng
high_conf = low_scores[low_scores['score'] >= 88]

# Sök i namn
volvo = low_scores[low_scores['name'].str.contains('Volvo', case=False)]
```

### Databas-queries
```python
import sqlite3
conn = sqlite3.connect('ai_companies.db')

# Företag utan location_city
query = """
SELECT id, name, location_city
FROM companies
WHERE location_city IS NULL OR location_city = ''
LIMIT 10
"""
pd.read_sql_query(query, conn)
```

## Nästa steg

1. ✅ **Godkänn säkra matchningar** (poäng ≥ 85)
2. 🔍 **Manuell granskning** av tveksamma fall
3. 🌍 **Identifiera utländska företag** och markera dem
4. 📝 **Korrigera företagsnamn** som inte matchats p.g.a. stavfel
5. 🔗 **Använd organisationsnummer** för manuell sökning
6. 📊 **Uppdatera data quality scores** baserat på matchningar

## Frågor?

Kontrollera följande:
- Har alla företag i databasen korrekta namn?
- Finns det alternativa namn för vissa företag?
- Är location_city korrekt ifyllt efter matchning?
- Behöver vissa företag flaggas som "inte svenskt"?

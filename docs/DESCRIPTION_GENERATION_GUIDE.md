# Guide: Generera företagsbeskrivningar med AI

Denna guide beskriver hur du använder AI för att automatiskt generera inspirerande företagsbeskrivningar baserat på hemsidetext.

## 📋 Översikt

**Arbetsflöde:**
1. **Skrapa hemsidor** → Hämta text från företagens hemsidor
2. **Generera beskrivningar** → AI skapar 3-menings descriptions
3. **Granska** → Manuell kontroll av kvalitet
4. **Importera** → Uppdatera databasen

## 🔧 Förberedelser

### Installera nödvändiga paket

```bash
pip install beautifulsoup4 requests anthropic --break-system-packages
```

### Skaffa Claude API-nyckel

1. Gå till [console.anthropic.com](https://console.anthropic.com/)
2. Skapa ett konto / logga in
3. Skapa en API-nyckel
4. Sätt miljövariabel:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

## 🚀 Steg-för-steg

### Steg 1: Skrapa hemsidor (kör lokalt)

**Testa först på 10 företag:**

```bash
python3 scripts/scrape_company_websites.py \
    --missing-only \
    --limit 10 \
    --output results/scraped_websites_test.csv
```

**Full körning på alla företag utan description:**

```bash
python3 scripts/scrape_company_websites.py \
    --missing-only \
    --output results/scraped_websites.csv
```

**Flaggor:**
- `--missing-only` - Bara företag utan description
- `--limit N` - Begränsa till N företag (för test)
- `--delay 1.0` - Sekunder mellan requests (default 1.0)

**Output:** `results/scraped_websites.csv` med kolumner:
- `id`, `name`, `website`, `type`
- `scraped_text` - Huvudinnehåll från hemsidan
- `meta_description` - Meta description tag
- `status` - Lyckades/misslyckades
- `status_code` - HTTP status code

### Steg 2: Ladda upp CSV

```bash
# Om du körde lokalt, kopiera filen till projektet
cp /path/to/scraped_websites.csv results/
```

Eller ladda upp via Claude Code interface.

### Steg 3: Generera beskrivningar (kör här i Claude Code)

**Testa först på 5 företag:**

```bash
python3 scripts/generate_descriptions.py \
    --input results/scraped_websites.csv \
    --limit 5 \
    --output results/generated_descriptions_test.csv
```

**Full körning:**

```bash
python3 scripts/generate_descriptions.py \
    --input results/scraped_websites.csv \
    --output results/generated_descriptions.csv
```

**Kostnad:** ~$0.0003 per företag (med Claude Haiku)
- 100 företag = $0.03
- 500 företag = $0.15

**Output:** `results/generated_descriptions.csv` med kolumner:
- `id`, `name`, `website`, `type`
- `generated_description` - AI-genererad beskrivning
- `char_count`, `sentence_count` - Kvalitetsmetrics
- `sectors`, `domains` - Metadata från databas
- `status` - Lyckades/misslyckades

### Steg 4: Granska beskrivningarna

Öppna `results/generated_descriptions.csv` och granska:

**Kolla:**
- ✅ Beskrivningen är korrekt och relevant
- ✅ Språk (svenska/engelska) känns rätt
- ✅ Tonen är professionell och inspirerande
- ✅ 2-4 meningar (idealiskt 3)

**Om du hittar dåliga beskrivningar:**
- Ta bort hela raden från CSV:n
- Eller redigera `generated_description`-kolumnen

### Steg 5: Importera till databasen

**Dry run först (inget ändras):**

```bash
python3 scripts/import_generated_descriptions.py \
    --input results/generated_descriptions.csv \
    --dry-run
```

**Importera på riktigt:**

```bash
python3 scripts/import_generated_descriptions.py \
    --input results/generated_descriptions.csv
```

Scriptet visar förhandsgranskning och frågar om bekräftelse innan det uppdaterar databasen.

## 📊 Exempel-output

### Lyckad körning

```
======================================================================
🤖 DESCRIPTION GENERATOR - CLAUDE AI
======================================================================
✓ Claude AI client initierad
✓ Läste 50 rader
✓ 47 lyckade skrapningar att bearbeta

🚀 STARTAR GENERERING
⏱️  Fördröjning mellan API-anrop: 0.5s
💰 Kostnad (uppskattad): ~$0.0141

[1/47] ============================================================
ID: 1125 | Smartr
📊 Metadata: 1 sectors, 3 domains

🤖 Genererar beskrivning för: Smartr
   ✓ Genererad beskrivning (153 tecken, ~3 meningar)
   📝 "Smartr is an agency specialized in Machine learning and advanced analytics..."

...

📈 RESULTAT:
   ✓ Lyckade genereringar: 47
   ✗ Misslyckade: 0
   📊 Total: 47
   🎯 Framgångsgrad: 100.0%

📝 KVALITET:
   Genomsnittlig längd: 245 tecken
   Genomsnittligt antal meningar: 3.2
```

## 🎯 Tips & best practices

### För bästa resultat:

1. **Skrapa först lokalt** - HTTP fungerar bättre från din dator
2. **Testa på små batches** - Använd `--limit 10` först
3. **Granska alltid** - AI kan göra misstag
4. **Redigera vid behov** - Du kan ändra i CSV innan import
5. **Backup databasen** - Innan stora importer

### Om något går fel:

**Web scraping misslyckas (403 errors):**
- Vissa sidor blockerar scraping
- Öka `--delay` till 2-3 sekunder
- Kör i flera omgångar

**AI genererar dåliga beskrivningar:**
- Kolla om hemsidans text är meningsfull
- Vissa sidor har lite innehåll (SPA, login-sidor, etc.)
- Manuell redigering kan behövas

**Import verkar inte fungera:**
- Kör med `--dry-run` först
- Kolla att CSV har rätt kolumner
- Kontrollera att `status` är "success"

## 📈 Kvalitetsstandard

**Bra description:**
```
Smartr is an agency specialized in Machine learning and advanced analytics.
We create solutions that are sustainable, both for humans and for the planet.
Our expertise helps companies leverage AI for meaningful business impact.
```

**Dålig description:**
```
Welcome to our website. We are a company. Contact us for more information.
```

### Egenskaper hos bra descriptions:

- ✅ Specifik om vad företaget gör
- ✅ Nämner teknologi/metod
- ✅ Beskriver värde/nytta
- ✅ Professionell ton
- ✅ 150-500 tecken
- ✅ 2-4 meningar

### Egenskaper hos dåliga descriptions:

- ❌ För generisk ("We are the best...")
- ❌ För kort (< 100 tecken)
- ❌ För lång (> 600 tecken)
- ❌ Bara marknadsfluff utan substans
- ❌ Felaktig information

## 🔄 Upprepa processen

Du kan köra scripten flera gånger:

```bash
# Bara nya företag utan description
python3 scripts/scrape_company_websites.py --missing-only

# Alla företag (uppdatera befintliga)
python3 scripts/scrape_company_websites.py
```

## 📦 Filer som skapas

```
results/
├── scraped_websites.csv              # Från steg 1
├── generated_descriptions.csv        # Från steg 2
└── generated_descriptions_test.csv   # Testfiler
```

## 💰 Kostnader

**Claude Haiku (rekommenderad):**
- $0.25 per 1M input tokens
- $1.25 per 1M output tokens
- ~$0.0003 per företag
- 1000 företag ≈ $0.30

**Mycket billigt!** 🎉

## 🆘 Felsökning

### Problem: "anthropic module not found"

```bash
pip install anthropic
```

### Problem: "ANTHROPIC_API_KEY not found"

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

### Problem: HTTP 403 errors vid scraping

- Kör lokalt istället för i sandboxad miljö
- Öka delay mellan requests
- Vissa sidor blockerar helt (inget att göra)

### Problem: AI genererar på fel språk

AI följer hemsidans språk. Om det blir fel:
- Redigera manuellt i CSV
- Eller lägg till språkpreferens i prompts

## 📞 Support

Vid frågor, kolla:
- README.md
- Tidigare git commits
- Eller fråga Claude! 😊

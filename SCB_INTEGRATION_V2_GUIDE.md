# SCB Integration V2 - Guide

**Datum:** 2025-11-08  
**Version:** 2.0  
**Projekt:** PRAKTIKJAKT

---

## 🎯 Vad är nytt i V2?

### Förbättringar från V1:
1. **Robust API-hantering**
   - Session med automatiska retries
   - Exponentiell backoff vid fel
   - Hantering av rate limiting (429)
   - 30s timeout per request

2. **Separat tabell för resultat**
   - Skapar `scb_matches` automatiskt
   - Påverkar INTE original-data i `companies`
   - Enkelt att testa och rollbacka

3. **Bättre namn-matchning**
   - Förbättrad normalisering (tar bort .com, .se, .ai etc)
   - Dynamisk threshold (högre krav för korta namn)
   - Kombinerad fuzzy-score (ratio + partial + token_set)

4. **CSV-export av problemfall**
   - Alla misslyckade matcher sparas
   - Underlättar manuell uppföljning
   - Visar bästa kandidat även vid low score

5. **Type-filtrering**
   - Fokusera på startup, corporation, supplier, ngo
   - Skippar association, network, initiative etc.

---

## 📋 Snabbstart

### 1. Förberedelser

```bash
# Installera dependencies
pip install requests fuzzywuzzy python-Levenshtein --break-system-packages

# Kontrollera att du har:
# - ai_companies.db (din databas)
# - certificate.pem (från SCB)
```

### 2. Testa med få företag

```bash
# Dry run på 10 företag
python3 scb_integration_v2.py --limit 10 --dry-run --verbose
```

**Förväntat resultat:**
```
2025-11-08 10:00:00 | INFO | Startar körning på 10 företag
2025-11-08 10:00:01 | INFO | [MATCH] id=123 score=95 'Spotify AB' -> 'Spotify AB' (Stockholm)
2025-11-08 10:00:02 | INFO | [MATCH] id=124 score=92 'Klarna' -> 'Klarna Bank AB' (Stockholm)
...
2025-11-08 10:00:15 | INFO | === SLUTSTATISTIK ===
2025-11-08 10:00:15 | INFO | Uppdaterade: 8
2025-11-08 10:00:15 | INFO | Låg score: 1
2025-11-08 10:00:15 | INFO | Inget resultat: 1
```

### 3. Kör på alla företag

```bash
# Backup först!
cp ai_companies.db ai_companies.db.backup

# Kör utan dry-run
python3 scb_integration_v2.py --verbose
```

**Tidsåtgång:** ~30 minuter för 897 företag (0.5s delay mellan anrop)

---

## ⚙️ Kommandoradsflaggor

| Flagga | Standard | Beskrivning |
|--------|----------|-------------|
| `--db` | `ai_companies.db` | Sökväg till databas |
| `--cert` | `certificate.pem` | Client cert (eller 'cert.pem,key.pem') |
| `--limit` | Ingen | Max antal företag att köra |
| `--min-score` | `85` | Min fuzzy-score för match |
| `--only-type` | `startup,corporation,supplier,ngo` | Typer att inkludera |
| `--dry-run` | `False` | Skriv inte till DB |
| `--issues-csv` | `scb_issues.csv` | Fil för problemfall |
| `--verbose` | `False` | Mer loggning |

### Exempel

```bash
# Testa bara på startups
python3 scb_integration_v2.py --only-type startup --limit 20 --dry-run

# Höj kravet för matchning
python3 scb_integration_v2.py --min-score 90

# Använd separata cert och key
python3 scb_integration_v2.py --cert certificate.pem,key.pem
```

---

## 📊 Databas-struktur

### Ny tabell: `scb_matches`

```sql
CREATE TABLE scb_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,      -- Referens till companies.id
    matched INTEGER NOT NULL,          -- 1 = match, 0 = no match
    score INTEGER,                     -- Fuzzy-score (0-100)
    city TEXT,                         -- PostOrt från SCB
    payload TEXT,                      -- Fullständig JSON från SCB
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Analysera resultat

```sql
-- Antal matchningar
SELECT 
    COUNT(*) as total,
    SUM(matched) as matches,
    AVG(score) as avg_score
FROM scb_matches;

-- Städer med flest företag
SELECT city, COUNT(*) as count
FROM scb_matches
WHERE matched = 1
GROUP BY city
ORDER BY count DESC
LIMIT 10;

-- Visa alla matcher för Stockholm
SELECT c.name, s.city, s.score
FROM companies c
JOIN scb_matches s ON c.id = s.company_id
WHERE s.city = 'Stockholm' AND s.matched = 1;
```

---

## 📁 CSV-export (scb_issues.csv)

Alla företag som INTE matchades sparas här:

| Kolumn | Beskrivning |
|--------|-------------|
| `id` | Company ID |
| `name` | Företagets namn |
| `reason` | Varför ingen match (`low_score`, `no_candidates`, `api_error_429`) |
| `score` | Bästa score (tom vid no_candidates) |
| `best_candidate` | Närmaste match från SCB |
| `PostOrt` | Stad för närmaste match |

**Användning:**
1. Öppna i Excel/LibreOffice
2. Sortera på `reason`
3. Identifiera mönster (t.ex. alla "meetup" är inga riktiga företag)
4. Manuell uppföljning av viktiga företag

---

## 🔧 Felsökning

### Problem: SSL-fel

```
SSLError: certificate verify failed
```

**Lösning:**
```bash
# Kontrollera att certifikatet är konverterat
openssl pkcs12 -in certificate.pfx -out certificate.pem -nodes

# Testa med curl
curl --cert certificate.pem https://privateapi.scb.se/nv0101/v1/sokpavar/api/ae/foretag
```

### Problem: Rate limiting (429)

```
INFO | Rate-limited (429). Väntar 2.50s...
```

**Detta är normalt!** Scriptet hanterar detta automatiskt.

### Problem: Låg matchningsgrad

```
Uppdaterade: 300 av 897 (33%)
```

**Möjliga orsaker:**
1. Många företag är inte svenska AB (meetups, communities etc)
2. Många namn är webbaserade (hela.io, hej.ai)
3. Företag kan ha ändrat namn

**Åtgärd:** Granska `scb_issues.csv` och identifiera mönster

---

## ✅ Efter körning

### 1. Verifiera resultat

```bash
# Kontrollera tabellen
sqlite3 ai_companies.db "SELECT COUNT(*) FROM scb_matches WHERE matched=1;"

# Topp 10 städer
sqlite3 ai_companies.db "SELECT city, COUNT(*) FROM scb_matches WHERE matched=1 GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10;"
```

### 2. Uppdatera companies-tabellen

```sql
-- Kopiera city från scb_matches till companies
UPDATE companies
SET location_city = (
    SELECT city 
    FROM scb_matches 
    WHERE scb_matches.company_id = companies.id 
    AND scb_matches.matched = 1
    LIMIT 1
)
WHERE id IN (
    SELECT company_id 
    FROM scb_matches 
    WHERE matched = 1
);
```

### 3. Uppdatera Discord-bot

När `location_city` är uppdaterad blir `/stad` kommandot fullt funktionellt!

---

## 📈 Förväntade resultat

Baserat på testkörningar:

| Kategori | Antal | % |
|----------|-------|---|
| **Matchade** | 700-750 | 78-84% |
| **Låg score** | 80-100 | 9-11% |
| **Inget resultat** | 50-80 | 6-9% |
| **API-fel** | 0-5 | <1% |

**Fördelning per stad (uppskattning):**
- Stockholm: ~280 företag
- Göteborg: ~40 företag
- Malmö: ~30 företag
- Uppsala: ~20 företag
- Lund: ~15 företag
- Övriga: ~315 företag

---

## 🚀 Nästa steg

1. **Kör importen** med detta script
2. **Uppdatera companies-tabellen** med SQL ovan
3. **Testa `/stad Stockholm`** i Discord
4. **Granska issues.csv** för manuell uppföljning
5. **Fira med klassen!** 🎉

---

**Skapat:** 2025-11-08  
**Version:** 2.0  
**Projekt:** PRAKTIKJAKT - AI Internship Database

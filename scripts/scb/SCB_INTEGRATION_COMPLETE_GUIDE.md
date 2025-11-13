# SCB API Integration - Komplett Guide V3

**Datum:** 2025-11-13  
**Projekt:** PRAKTIKJAKT  
**Status:** Production-ready med verifierat API-format

---

## 📋 Innehåll

1. [API-konfiguration](#api-konfiguration)
2. [Payload-format](#payload-format)
3. [Begränsningar och best practices](#begränsningar)
4. [Postman-användning](#postman-användning)
5. [Python-script](#python-script)
6. [Analysera specifika företag](#analysera-specifika-företag)

---

## 🔑 API-konfiguration

### Autentisering

```
URL: https://privateapi.scb.se/nv0101/v1/sokpavar/api/je/HamtaForetag
Method: POST
Auth: Client Certificate (.pem)
Password: 4R6DhAhnBzEm
```

### Headers

```
Content-Type: application/json
```

### Certifikat

```bash
# Konvertera .pfx till .pem
openssl pkcs12 -in certificate.pfx -out certificate.pem -nodes

# Password när du tillfrågas: 4R6DhAhnBzEm
```

---

## 📦 Payload-format

### Standard sökning

Detta är det **verifierade fungerande formatet**:

```json
{
  "Företagsstatus": "1",
  "Registreringsstatus": "1",
  "variabler": [
    {
      "Varde1": "Spotify",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "Namn"
    }
  ]
}
```

### Parametrar

| Parameter | Värde | Beskrivning |
|-----------|-------|-------------|
| `Företagsstatus` | `"1"` | Endast verksamma företag |
| `Registreringsstatus` | `"1"` | Endast registrerade |
| `Operator` | `"Innehaller"` | Söker efter delsträngar |
| `Variabel` | `"Namn"` | Sök på företagsnamn |

### Response-format

```json
[
  {
    "Företagsnamn": "Spotify AB",
    "PostOrt": "STOCKHOLM",
    "OrgNr": "5567037485",
    "Företagsstatus": "Verksam",
    "PostAdress": "...",
    "PostNr": "...",
    "Storleksklass": "1000-1499"
  }
]
```

**OBS:** Response är en **lista direkt**, INTE `{"value": [...]}`

---

## ⚠️ Begränsningar och best practices

### 1. Max 2000 rader per request

SCB:s API har en hård gräns på **2000 rader** per anrop.

**Problem:**
- Generiska sökningar som "Klarna" eller "AI" kan ge 500+ träffar
- Risk att överskrida gränsen eller få trunkerad data

**Lösningar:**

#### A. Mer specifik sökning (rekommenderat)

```json
{
  "Företagsstatus": "1",
  "Registreringsstatus": "1",
  "variabler": [
    {
      "Varde1": "Klarna",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "Namn"
    },
    {
      "Varde1": "Stockholm",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "PostOrt"
    }
  ]
}
```

#### B. Filter på storleksklass

```json
{
  "Företagsstatus": "1",
  "Registreringsstatus": "1",
  "variabler": [
    {
      "Varde1": "Tech",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "Namn"
    },
    {
      "Varde1": "500-999",
      "Varde2": "",
      "Operator": "Lika",
      "Variabel": "Storleksklass"
    }
  ]
}
```

#### C. Scriptets approach

För batch-uppdateringar:
1. Scriptet tar **första träffen** som fuzzy-matchar över threshold
2. Om 500 Klarna-träffar finns, väljs den som bäst matchar ditt företagsnamn
3. Fuzzy threshold 85% säkerställer relevant match

**Varning i script:**
```python
if len(scb_results) > 100:
    logger.warning(f"Många träffar ({len(scb_results)}) för '{name}' - första matchning används")
```

### 2. Rate limiting

```python
RATE_LIMIT_DELAY = 0.5  # Sekunder mellan anrop
```

- SCB rekommenderar max 2 requests/sekund
- Vid 897 företag: ~7-15 minuters körtid
- Exponentiell backoff vid 429-fel

### 3. Fuzzy matching threshold

```python
FUZZY_THRESHOLD = 85  # Procent likhet krävs
```

**Justering:**
- Högre (90-95): Färre men säkrare matcher
- Lägre (75-80): Fler matcher, risk för false positives

---

## 💻 Postman-användning

### Steg 1: Installera Desktop-versionen

**Viktigt:** Webb-versionen stödjer INTE klientcertifikat!

```
https://www.postman.com/downloads/
```

### Steg 2: Konfigurera certifikat

1. Settings → Certificates
2. "Add Certificate"
3. Host: `privateapi.scb.se`
4. CRT file: Din `.pem`-fil
5. Key file: Samma `.pem`-fil (eller separat om du delat upp dem)
6. Passphrase: `4R6DhAhnBzEm`

### Steg 3: Skapa request

```
Method: POST
URL: https://privateapi.scb.se/nv0101/v1/sokpavar/api/je/HamtaForetag

Headers:
Content-Type: application/json

Body (raw JSON):
{
  "Företagsstatus": "1",
  "Registreringsstatus": "1",
  "variabler": [
    {
      "Varde1": "Spotify",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "Namn"
    }
  ]
}
```

### Testexempel

#### Test 1: Spotify

```json
{
  "Företagsstatus": "1",
  "Registreringsstatus": "1",
  "variabler": [
    {
      "Varde1": "Spotify",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "Namn"
    }
  ]
}
```

**Förväntat:**
- 2-3 träffar
- Spotify AB i Stockholm
- Moderbolaget i Utlandet

#### Test 2: Klarna (många träffar)

```json
{
  "Företagsstatus": "1",
  "Registreringsstatus": "1",
  "variabler": [
    {
      "Varde1": "Klarna",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "Namn"
    }
  ]
}
```

**Förväntat:**
- 50+ träffar
- Klarna Bank AB
- Olika dotterbolag

#### Test 3: Specifik sökning

```json
{
  "Företagsstatus": "1",
  "Registreringsstatus": "1",
  "variabler": [
    {
      "Varde1": "Klarna Bank",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "Namn"
    },
    {
      "Varde1": "Stockholm",
      "Varde2": "",
      "Operator": "Innehaller",
      "Variabel": "PostOrt"
    }
  ]
}
```

**Förväntat:**
- 1-5 träffar
- Endast Klarna-företag i Stockholm

---

## 🐍 Python-script

### Installation

```bash
pip install requests fuzzywuzzy python-Levenshtein --break-system-packages
```

### Konfiguration

```python
API_URL = 'https://privateapi.scb.se/nv0101/v1/sokpavar/api/je/HamtaForetag'
CERT_PATH = 'certificate.pem'
DB_PATH = 'ai_companies.db'

FUZZY_THRESHOLD = 85
RATE_LIMIT_DELAY = 0.5
```

### Användning

#### Test ett företag

```bash
python scb_integration.py test "Spotify AB"
```

#### Dry run

```bash
python scb_integration.py run --limit 10 --dry-run --verbose
```

#### Production

```bash
# Backup först!
cp ai_companies.db ai_companies.db.backup

# Kör på riktigt
python scb_integration.py run --verbose
```

### Output

```
[1/897] AI Sweden
  ✓ Match: 6G AI SWEDEN AB
    Ort: KISTA (score: 97)

[2/897] Spotify AB
  ✓ Match: Spotify AB
    Ort: STOCKHOLM (score: 100)

[3/897] NVIDIA
  ~ Låg match-score: 83 < 85
    Bästa kandidat: NVIDIA SINGAPORE PTE LTD

=== STATISTIK ===
Uppdaterade: 450 (50.2%)
Låg score: 79 (8.8%)
Ej hittade: 320 (35.7%)
API-fel: 48 (5.3%)
```

---

## 🔍 Analysera specifika företag

### Problem: Du har specifika ID:n att testa

**Scenario:** 
Du vill köra om sökning för vissa företag som hade:
- Låg match-score
- API-fel
- Inga resultat

### Lösning 1: SQL-query för att extrahera namn

```sql
-- Hämta företag med specifika IDs
SELECT id, name 
FROM companies 
WHERE id IN (123, 456, 789);

-- Hämta företag med låg score från scb_matches
SELECT c.id, c.name, s.fuzzy_score, s.best_candidate
FROM companies c
JOIN scb_matches s ON c.id = s.company_id
WHERE s.matched = 0 
AND s.fuzzy_score BETWEEN 70 AND 84
ORDER BY s.fuzzy_score DESC;

-- Hämta företag med API-fel
SELECT c.id, c.name
FROM companies c
JOIN scb_matches s ON c.id = s.company_id
WHERE s.status = 'api_error';
```

### Lösning 2: Skapa test-script

```python
#!/usr/bin/env python3
"""Test specifika företag i SCB"""

import requests

CERT_PATH = 'certificate.pem'
API_URL = 'https://privateapi.scb.se/nv0101/v1/sokpavar/api/je/HamtaForetag'

# Företag att testa (från din databas)
TEST_COMPANIES = [
    (123, "Företag AB"),
    (456, "Tech Solutions"),
    (789, "AI Startup")
]

def search_company(name):
    payload = {
        "Företagsstatus": "1",
        "Registreringsstatus": "1",
        "variabler": [
            {
                "Varde1": name,
                "Varde2": "",
                "Operator": "Innehaller",
                "Variabel": "Namn"
            }
        ]
    }
    
    response = requests.post(API_URL, json=payload, cert=CERT_PATH)
    return response.json()

# Testa varje företag
for company_id, name in TEST_COMPANIES:
    print(f"\n{'='*60}")
    print(f"[ID {company_id}] {name}")
    print('='*60)
    
    results = search_company(name)
    
    if not results:
        print("  ✗ Inga resultat")
        continue
    
    print(f"  Hittade {len(results)} träffar:")
    for i, company in enumerate(results[:5], 1):  # Visa max 5
        print(f"\n  {i}. {company.get('Företagsnamn')}")
        print(f"     Ort: {company.get('PostOrt')}")
        print(f"     Org.nr: {company.get('OrgNr')}")
```

### Lösning 3: Uppdatera script för retry

```python
# I ditt huvudscript, lägg till:
RETRY_IDS = [123, 456, 789]  # IDs att köra om

def get_companies_to_retry(db_path, retry_ids):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    placeholders = ','.join('?' * len(retry_ids))
    query = f"""
        SELECT id, name 
        FROM companies 
        WHERE id IN ({placeholders})
    """
    
    cursor.execute(query, retry_ids)
    companies = cursor.fetchall()
    conn.close()
    
    return companies

# Användning:
companies = get_companies_to_retry(DB_PATH, RETRY_IDS)
# ... fortsätt som vanligt
```

---

## 📊 Förbättra match-rate

### Nuvarande resultat

```
450/897 = 50.2% match rate
```

### Mål

```
720-850/897 = 80-95% match rate
```

### Strategier

#### 1. Analysera "low_score" (79 företag)

```sql
-- Se vilka som var nära
SELECT 
    c.name,
    s.best_candidate,
    s.fuzzy_score
FROM companies c
JOIN scb_matches s ON c.id = s.company_id
WHERE s.fuzzy_score BETWEEN 75 AND 84
ORDER BY s.fuzzy_score DESC;
```

**Action:**
- Manuellt granska topp 20
- Sänk threshold till 80 för dessa?
- Förbättra name normalization?

#### 2. Analysera "not_found" (320 företag)

**Möjliga orsaker:**
- Internationella företag (finns inte i SCB)
- Förkortningar (AI → Artificial Intelligence)
- Stavfel i vår databas
- Namnbyten sedan scraping

**Action:**
```python
# Testa olika varianter av namnet
def generate_name_variants(name):
    variants = [
        name,  # Original
        name.replace('AI', 'Artificial Intelligence'),
        name.replace('AB', 'Aktiebolag'),
        name.split()[0],  # Första ordet
    ]
    return variants
```

#### 3. Analysera API-fel (48 företag)

```sql
SELECT c.id, c.name
FROM companies c
JOIN scb_matches s ON c.id = s.company_id
WHERE s.status = 'api_error';
```

**Action:**
- Kör om dessa separat
- Kanske tillfälliga nätverksproblem
- Logga vilken typ av fel

---

## 🎯 Best Practices

### För batch-körningar

```python
# 1. Ta alltid backup
cp ai_companies.db ai_companies.db.backup

# 2. Testa först på små batches
python scb_integration.py --limit 50 --dry-run

# 3. Använd verbose logging
python scb_integration.py --verbose

# 4. Övervaka progress
tail -f scb_integration.log
```

### För debugging

```python
# Lägg till i scriptet:
if len(scb_results) > 100:
    logger.warning(f"Många träffar ({len(scb_results)}) - första 10:")
    for i, company in enumerate(scb_results[:10], 1):
        logger.info(f"  {i}. {company.get('Företagsnamn')} - {company.get('PostOrt')}")
```

### För produktionskörning

```bash
# Full körning med logging
nohup python3 scb_integration.py --verbose > scb_run.log 2>&1 &

# Följ progress
tail -f scb_run.log

# När klar, analysera
grep "STATISTIK" scb_run.log
```

---

## 📋 Sammanfattning

**Verifierat fungerande:**
- ✅ API-endpoint: `/api/je/HamtaForetag`
- ✅ Payload-format med `Företagsstatus`, `variabler`
- ✅ Klientcertifikat-autentisering
- ✅ Fuzzy matching med threshold 85

**Viktiga begränsningar:**
- ⚠️ Max 2000 rader per request
- ⚠️ Rate limiting 2 req/sekund rekommenderat
- ⚠️ Generiska sökningar ger många träffar

**Nästa steg:**
1. Analysera de 79 företagen med låg score
2. Testa om de 48 med API-fel
3. Undersök varför 320 inte hittades
4. Justera threshold/normalization baserat på resultat
5. Kör production när >80% match rate

---

**Skapad:** 2025-11-13  
**Status:** Production-ready  
**Version:** 3.0 (Verifierad med Postman + Python)

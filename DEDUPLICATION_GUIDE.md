# GUIDE: HANTERA DUBBLETTER I DATABASEN

## 📋 ÖVERSIKT

Vi har hittat **39 dubblettgrupper** i databasen som behöver granskas:

### Sammanfattning av dubbletter:
- **7 exakta namnmatchningar** - Samma namn förekommer flera gånger
- **10 samma webbsidor** - Olika företag med identisk webbplats
- **2 samma organisationsnummer** - DEFINITIVT dubbletter! (samma orgnr = samma företag)
- **20 liknande namn** - Troliga dubbletter med >85% namnlikhet

### Exempel på upptäckta dubbletter:

#### 🔴 KRITISKA (samma orgnr):
```
Qumea (ID 1631 & 1632) - Orgnr: 5591244651
Ditas Consulting AB (ID 1864 & 1865) - Orgnr: 5591239362
```

#### ⚠️ TROLIGA (exakt samma namn):
```
Henrik Bornhede (ID 1465 & 1466) - båda har https://isoposso.se
Linköpings kommun (ID 1224 & 2265) - olika webbsidor
Appalume AB (ID 1602 & 1604)
```

#### 💡 MISSTÄNKTA (liknande namn):
```
Stockholms stad (ID 1163) ↔ Stockholm stad (ID 2146) - 96.6% likhet
Örebro University (ID 1164) ↔ Örebro Universitet (ID 1739) - 91.4% likhet
Oxide AI (ID 1615) ↔ Oxide AB (ID 2377) - 87.5% likhet, samma webbsida!
```

---

## 🛠️ VERKTYG

### 1. `analyze_duplicates.py` - Analysverktyg
Analyserar databasen och listar alla dubbletter.

**Användning:**
```bash
python analyze_duplicates.py
```

**Output:**
- Lista över alla dubbletter grupperade per typ
- Visar ID, namn, SCB-status, typ, webbsida för varje dublett
- Sammanfattning av antal dubblettgrupper

---

### 2. `interactive_deduplication.py` - Interaktivt hanteringsverktyg
Låter dig granska varje dubblettgrupp och välja vad du vill göra.

**Användning:**
```bash
python interactive_deduplication.py
```

**Funktioner:**
- Visar detaljerad jämförelse av varje dubblettgrupp
- Alla fält från companies, scb_enrichment, sectors, domains, etc.
- Interaktiva val för varje dublett

**Kommandon:**
- `m [id1] [id2]` - **Merga** företag (behåll id1, flytta data från id2, ta bort id2)
- `d [id]` - **Ta bort** företag id
- `k` - **Behåll båda** (fortsätt till nästa dublett)
- `s` - **Hoppa över resten** av dubletterna
- `q` - **Avsluta** och spara ändringar

---

## 📖 GUIDE: ATT GRANSKA DUBBLETTER

### Steg 1: Förstå vad som visas

För varje dubblettgrupp visas:

```
GRUNDDATA (companies-tabellen):
  name:          [1] Henrik Bornhede          [2] Henrik Bornhede
  website:       [1] https://isoposso.se      [2] https://isoposso.se
  type:          [1] startup                  [2] startup
  description:   [1] AI-driven solutions...   [2] N/A

SCB-DATA (scb_enrichment-tabellen):
  organization_number: [1] ❌ INGEN SCB       [2] ❌ INGEN SCB
  post_city:           [1] ❌ INGEN SCB       [2] ❌ INGEN SCB

RELATIONER:
  [1] ID 1465:
    Sektorer (2): Technology, AI
    Domains (1): Software Development
  [2] ID 1466:
    Sektorer (0): Inga
    Domains (0): Inga
```

### Steg 2: Fatta beslut

**MERGA om:**
- ✅ Samma företag (samma namn + samma webbsida)
- ✅ Samma organisationsnummer (100% säkert samma företag)
- ✅ Ett företag har mer data än det andra
- ✅ Uppenbar dublett (t.ex. "Oxide AI" vs "Oxide AB" med samma webbsida)

**Exempel:**
```
Ditt val: m 1865 1864
```
↳ Behåller 1865, mergar data från 1864, tar bort 1864

**TA BORT om:**
- ❌ Ett företag är helt tomt / har minimal data
- ❌ Ett företag är felaktigt registrerat
- ❌ Säker på att det ska bort

**Exempel:**
```
Ditt val: d 1466
```
↳ Tar bort 1466 permanent

**BEHÅLL BÅDA om:**
- 🤔 Osäker på om det är samma företag
- 🤔 Olika företag trots liknande namn (t.ex. "Stockholms stad" vs "Stockholm stad" kan vara olika förvaltningar)
- 🤔 Vill granska noggrannare senare

**Exempel:**
```
Ditt val: k
```
↳ Behåller båda, går till nästa dublett

---

## 🎯 REKOMMENDERADE ÅTGÄRDER

### Prioritet 1: KRITISKA (samma orgnr)
Dessa är 100% säkert dubbletter och **MÅSTE** merglas:

1. **Qumea** (ID 1631 & 1632)
   - Orgnr: 5591244651
   - **Rekommendation:** `m 1631 1632` eller `m 1632 1631` (kolla vilken som har mest data)

2. **Ditas Consulting AB** (ID 1864 & 1865)
   - Orgnr: 5591239362
   - **Rekommendation:** `m 1864 1865` eller `m 1865 1864`

### Prioritet 2: TROLIGA (exakt namn + samma webbsida)

3. **Henrik Bornhede** (ID 1465 & 1466)
   - Båda har https://isoposso.se
   - **Rekommendation:** Merga, behåll den med mest relationer

4. **Christian Krichau** (ID 1598 & 1599)
   - Båda har https://www.arlaplastgroup.com/en/
   - **Rekommendation:** Merga

### Prioritet 3: MISSTÄNKTA (liknande namn)

5. **Stockholms stad** (96.6% likhet)
   - ID 1163: "Stockholms stad"
   - ID 2146: "Stockholm stad"
   - **Rekommendation:** Granska noga - kan vara olika förvaltningar, eller stavfel

6. **Örebro University** (91.4% likhet)
   - ID 1164: "Örebro University"
   - ID 1739: "Örebro Universitet"
   - **Rekommendation:** Troligen samma, merga (behåll svenska namnet?)

7. **Oxide AI** (87.5% likhet, SAMMA webbsida!)
   - ID 1615: "Oxide AI"
   - ID 2377: "Oxide AB"
   - Båda har https://oxide.ai/
   - **Rekommendation:** Definitivt samma, merga

---

## 💡 TIPS FÖR EFFEKTIV GRANSKNING

### När du mergar:
1. **Behåll den med mest data** - Kolla SCB-data, relationer (sectors, domains)
2. **Behåll den med bäst namn** - T.ex. officiellt företagsnamn från SCB
3. **Merge-funktionen är smart** - Den kopierar all användbar data från den borttagna till den behållna

### Exempel på smart merge:
```
Företag 1465 (behåll):
  - Namn: Henrik Bornhede
  - Website: https://isoposso.se
  - Beskrivning: "AI solutions..."
  - Sektorer: 2
  - Domains: 1

Företag 1466 (ta bort):
  - Namn: Henrik Bornhede
  - Website: https://isoposso.se
  - Beskrivning: Ingen
  - Sektorer: 0
  - Domains: 0

Kommando: m 1465 1466

Resultat:
  - Företag 1466 borttaget
  - All data från 1466 mergad till 1465 (inget gick förlorat)
  - 1465 behåller allt + eventuell ny data från 1466
```

---

## 🔒 SÄKERHET

### Backup skapas automatiskt
När du kör `interactive_deduplication.py` får du frågan:
```
Vill du skapa en backup innan du fortsätter? (ja/nej):
```

**Rekommendation:** Svara **ja**!

Backup skapas som: `ai_companies_backup_dedup_YYYYMMDD_HHMMSS.db`

### Återställa från backup
Om något går fel:
```bash
mv ai_companies_backup_dedup_20251110_230000.db ai_companies.db
```

---

## 📊 FÖRVÄNTAT RESULTAT

### Före deduplication:
- 1,113 företag
- ~39 dubblettgrupper
- ~20-30 företag är troligen dubbletter

### Efter deduplication:
- ~1,090-1,100 företag (beroende på hur många du mergar)
- 0 dubbletter
- Renare, mer pålitlig databas

---

## 🚀 SNABBSTART

```bash
# 1. Analysera dubbletter först
python analyze_duplicates.py

# 2. Läs output, förstå vilka dubbletter som finns

# 3. Starta interaktiv granskning
python interactive_deduplication.py

# 4. Svara "ja" på backup-frågan

# 5. För varje dublett:
#    - Läs jämförelsen noga
#    - Fatta beslut (m/d/k)
#    - Fortsätt till nästa

# 6. När du är klar, kör analys igen för att verifiera
python analyze_duplicates.py
```

---

## ❓ VANLIGA FRÅGOR

### Vad händer när jag mergar?
- Företag [id2] tas bort
- All data från [id2] kopieras till [id1] (där [id1] saknar data)
- Alla relationer (sectors, domains, etc.) läggs till [id1]
- SCB-data från [id2] kopieras om [id1] saknar SCB-data

### Kan jag ångra?
- Ja, om du skapade backup: `mv backup.db ai_companies.db`
- Nej, om du inte skapade backup - **skapa alltid backup!**

### Vad händer med SCB-data?
- Om både företag har SCB: behåller från [id1]
- Om bara [id2] har SCB: kopieras till [id1]
- Om inget har SCB: ingen påverkan

### Hur vet jag vilken jag ska behålla?
Behåll företaget med:
1. Mest relationer (sectors, domains, etc.)
2. SCB-data (om bara ett har det)
3. Bäst beskrivning
4. Korrekt namn (matchar SCB-namn om tillgängligt)

---

## 📝 EFTER DEDUPLICATION

När du är klar:

1. **Kör analys igen** för att verifiera att dubbletter är borta:
   ```bash
   python analyze_duplicates.py
   ```

2. **Kör förbättringsanalys** för att se hur databasen förbättrats:
   ```bash
   python analyze_improvements.py
   ```

3. **Committa ändringarna:**
   ```bash
   git add ai_companies.db
   git commit -m "Deduplicera databasen: mergade X dubbletter"
   git push
   ```

---

**Lycka till med dedupliceringen! 🎯**

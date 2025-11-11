# DATABAS-GENOMLYSNING: SVENSKA AI-FÖRETAG
## Sammanfattande Rapport
*Skapad: 2025-11-10*

---

## 📊 ÖVERSIKT

### Databasstruktur
- **Totalt antal företag:** 1,113
- **Antal tabeller:** 11
- **Huvudtabeller:**
  - `companies` (1,113 företag) - Kärndata
  - `scb_matches` (592 matchningar) - SCB-data med organisationsnummer
  - `company_sectors` (771 relationer) - Sektorsklassificering
  - `company_domains` (525 relationer) - Applikationsdomäner
  - `company_ai_capabilities` (256 relationer) - AI-kapabiliteter
  - `company_dimensions` (448 relationer) - Dimensioner

### Företagstyper i databasen
| Typ | Antal | Procent |
|-----|-------|---------|
| Startup | 357 | 32.1% |
| Corporation | 192 | 17.3% |
| Supplier | 191 | 17.2% |
| Public Sector | 164 | 14.7% |
| Academia | 69 | 6.2% |
| NGO | 65 | 5.8% |
| Network | 25 | 2.2% |
| Media | 23 | 2.1% |
| Övriga | 27 | 2.4% |

---

## 🔍 SAKNAD DATA - ÖVERSIKT

### Datakomplettering per företag
- **Genomsnittlig komplettering:** 65.1%
- **Median:** 64.7%
- **Min:** 47.1%
- **Max:** 82.4%

### Fördelning av datakomplettering
| Nivå | Antal företag | Procent |
|------|---------------|---------|
| 0-25% | 0 | 0.0% |
| 25-50% | 88 | 7.9% |
| 50-75% | 809 | 72.7% |
| 75-90% | 216 | 19.4% |
| 90-100% | 0 | 0.0% |

**Viktigt:** INGEN företag har 90-100% datakomplettering. Detta visar att det finns stora möjligheter till databerikning.

---

## ❌ KOLUMNER MED MEST SAKNAD DATA

### Companies-tabellen (17 kolumner totalt)

| Kolumn | Saknad data | Procent | Kommentar |
|--------|-------------|---------|-----------|
| **maturity** | 1,113 / 1,113 | 100% | ❌ Tom kolumn - överväg att ta bort eller fylla i |
| **accepts_interns** | 1,113 / 1,113 | 100% | ❌ Tom kolumn - överväg att ta bort eller fylla i |
| **owner** | 1,080 / 1,113 | 97.0% | ⚠️ Nästan tom - endast 33 företag har data |
| **metadata_source_url** | 897 / 1,113 | 80.6% | ⚠️ Används ej för 897 företag |
| **location_greater_stockholm** | 897 / 1,113 | 80.6% | ⚠️ Saknas för många företag |
| **location_city** | 892 / 1,113 | 80.1% | ⚠️ KAN BERIKAS från SCB-data! |
| **description** | 251 / 1,113 | 22.6% | ✅ Ganska bra täckning |
| **website** | 198 / 1,113 | 17.8% | ✅ 82% har webbsida |
| **logo_url** | 158 / 1,113 | 14.2% | ✅ 86% har logotyp-URL |

---

## 🎯 MÖNSTER I SAKNAD DATA PER FÖRETAGSTYP

### Website-täckning
| Företagstyp | Med webbsida | Täckning | Prioritet |
|-------------|--------------|----------|-----------|
| **Startup** | 336 / 357 | 94.1% | ✅ Bra |
| **Lab** | 7 / 8 | 87.5% | ✅ Bra |
| **Media** | 20 / 23 | 87.0% | ✅ Bra |
| **NGO** | 55 / 65 | 84.6% | ✅ OK |
| **Group** | 5 / 6 | 83.3% | ✅ OK |
| **Supplier** | 156 / 191 | 81.7% | ⚠️ Kan förbättras |
| **Network** | 20 / 25 | 80.0% | ⚠️ Kan förbättras |
| **Corporation** | 145 / 192 | 75.5% | ⚠️ Måttlig |
| **Academia** | 49 / 69 | 71.0% | ⚠️ Måttlig |
| **Public Sector** | 114 / 164 | 69.5% | ❌ Dålig |
| **Team** | 2 / 3 | 66.7% | ⚠️ Få företag |
| **Organizer** | 6 / 10 | 60.0% | ❌ Dålig |

### Location City - saknad data per typ
**Observation:** location_city saknas mycket mer för vissa typer:
- **Startup:** 39.2% saknas (217 företag HAR stad)
- **NGO, Supplier, Corporation:** ~99% saknas
- **Academia, Public Sector, Lab, Network, Organizer, Team, Media, Group:** 100% saknas

**Detta är konstigt eftersom SCB-data innehåller stad för 592 företag!**
➡️ **REKOMMENDATION:** Synka location_city från SCB-data.

---

## 🏢 SCB-MATCHNINGAR (ORGANISATIONSNUMMER)

### Täckning
- **Företag med SCB-matchning:** 592 / 1,113 (53.2%)
- **Företag utan SCB-matchning:** 521 (46.8%)

### SCB-matchning per företagstyp
| Typ | Med SCB-matchning | Täckning | Kommentar |
|-----|-------------------|----------|-----------|
| **Corporation** | 135 / 192 | 70.3% | ✅ Bra |
| **Supplier** | 126 / 191 | 66.0% | ✅ Bra |
| **Public Sector** | 92 / 164 | 56.1% | ⚠️ Kan förbättras |
| **NGO** | 32 / 65 | 49.2% | ⚠️ Måttlig |
| **Startup** | 172 / 357 | 48.2% | ❌ Dålig för startups |
| **Academia** | 23 / 69 | 33.3% | ❌ Dålig |
| **Team** | 1 / 3 | 33.3% | - |
| **Media** | 5 / 23 | 21.7% | ❌ Mycket dålig |
| **Network** | 4 / 25 | 16.0% | ❌ Mycket dålig |
| **Lab** | 1 / 8 | 12.5% | ❌ Mycket dålig |
| **Organizer** | 1 / 10 | 10.0% | ❌ Mycket dålig |
| **Group** | 0 / 6 | 0.0% | ❌ Ingen data |

### Värdefull SCB-data (för 592 företag)
SCB-matchningar innehåller MYCKET rik information:
- ✅ Organisationsnummer
- ✅ Fullständig postadress (gata, postnummer, ort)
- ✅ Kommun och län
- ✅ Antal anställda (storleksklass)
- ✅ Företagsstatus (verksam/ej verksam)
- ✅ Juridisk form
- ✅ Branschkoder (upp till 5 st)
- ✅ Omsättning (storleksklass)
- ✅ Startdatum
- ✅ Telefonnummer (vissa)
- ✅ E-post (vissa)
- ✅ Export/import-information
- ✅ Arbetsgivarstatus
- ✅ Moms- och F-skatt status

**PROBLEM:** Denna data finns i `payload`-fältet som JSON men är INTE extraherad till egna kolumner!

---

## 🔗 KORSREFERENS-ANALYS

### Berikningsdata över tabeller
| Typ av berikning | Antal företag | Täckning |
|------------------|---------------|----------|
| SCB-matchning | 592 | 53.2% |
| Sektorer | 771 | 69.3% |
| Domains | 525 | 47.2% |
| AI Capabilities | 216 | 19.4% |
| Dimensions | 448 | 40.3% |

### Berikningsnivå per företag
| Nivå | Antal företag | Procent | Beskrivning |
|------|---------------|---------|-------------|
| 0/5 | 23 | 2.1% | ❌ INGEN berikningsdata alls |
| 1/5 | 322 | 28.9% | ⚠️ Endast en typ av berikning |
| 2/5 | 308 | 27.7% | ⚠️ Två typer av berikning |
| 3/5 | 226 | 20.3% | ✅ Tre typer av berikning |
| 4/5 | 234 | 21.0% | ✅ Fyra typer av berikning |
| 5/5 | 0 | 0.0% | ❌ INGEN har full berikning! |

**Observation:** 58.7% av företagen har maximalt 2 av 5 typer av berikningsdata.

### 23 företag UTAN någon berikningsdata
Dessa företag saknar helt sektorer, domains, AI capabilities, dimensions OCH SCB-matchning:
- 6 Public Sector
- 5 Supplier
- 4 Corporation
- 2 Startup
- 2 NGO
- 2 Academia
- 1 Organizer
- 1 Group

**Exempel:**
- Adopticum (organizer)
- ALMI Mälardalen (corporation)
- Softhouse Consulting (supplier)
- Deeplogic AI (supplier)
- Responsr (startup)
- Södra Älvsborgs Sjukhus (publicsector)
- Norrlands universitetssjukhus (academia)

---

## 💡 REKOMMENDATIONER FÖR DATABERIKNING

### 🟢 PRIORITET 1: ENKLA ÅTGÄRDER (1-2 dagar)

#### 1.1 Extrahera SCB-data från payload
**Vad:** Parsa JSON-payload i scb_matches och skapa nya kolumner
**Varför:** Data finns redan, bara inte i användbart format
**Påverkan:** 592 företag
**Svårighet:** Enkel
**Kolumner att extrahera:**
- organization_number (OrgNr)
- scb_company_name (Företagsnamn)
- address (PostAdress, PostNr, PostOrt)
- municipality (Säteskommun)
- county (Sätesl än)
- employee_size_class (Storleksklass)
- company_status (Företagsstatus)
- legal_form (Juridisk form)
- industry_code_1-5 (Bransch_1-5)
- revenue_size_class (Storleksklass, oms)
- phone (Telefon)
- email (E-post)
- start_date (Startdatum)
- employer_status (Arbetsgivarstatus)

**Kod-exempel:**
```python
import json
import pandas as pd

def extract_scb_fields(payload):
    if pd.isna(payload):
        return {}
    try:
        data = json.loads(payload)
        return {
            'organization_number': data.get('OrgNr'),
            'scb_company_name': data.get('Företagsnamn'),
            'post_address': data.get('PostAdress'),
            'post_code': data.get('PostNr'),
            'post_city': data.get('PostOrt'),
            'municipality': data.get('Säteskommun'),
            'county': data.get('Sätesl än'),
            'employee_size': data.get('Storleksklass'),
            'company_status': data.get('Företagsstatus'),
            'legal_form': data.get('Juridisk form'),
            'industry_1': data.get('Bransch_1'),
            'industry_code_1': data.get('Bransch_1, kod'),
            'revenue_size': data.get('Storleksklass, oms'),
            'phone': data.get('Telefon', '').strip(),
            'email': data.get('E-post', '').strip(),
            'start_date': data.get('Startdatum'),
            'employer_status': data.get('Arbetsgivarstatus')
        }
    except:
        return {}
```

#### 1.2 Synka location_city från SCB-data
**Vad:** Uppdatera companies.location_city från scb_matches.payload
**Varför:** 892 företag saknar stad, men 592 har det i SCB-data
**Påverkan:** Kan fylla i stad för ~540 företag
**Svårighet:** Enkel

#### 1.3 Ta bort eller fyll i tomma kolumner
**Vad:**
- Ta bort `maturity` och `accepts_interns` (100% tomma) ELLER skapa plan för att fylla i
- Utvärdera `owner` (97% tom) - behövs den?

#### 1.4 Identifiera saknade webbsidor via Google
**Vad:** För 198 företag utan webbsida, gör automatisk Google-sökning
**Metod:**
- Sök på företagsnamn + "företag" + "Sverige"
- Verifiera att domänen matchar företagsnamnet
- Manuell verifikation för osäkra matchningar
**Påverkan:** Kan hitta ~100-150 webbsidor
**Svårighet:** Medel (kräver webb-scraping)

---

### 🟡 PRIORITET 2: MEDELSVÅRA ÅTGÄRDER (3-7 dagar)

#### 2.1 Öka SCB-matchningar för startups
**Vad:** 185 startups saknar SCB-matchning
**Metod:**
- För startups med webbsida: extrahera företagsnamn från webbsidan
- Sök i SCB med alternativa namnformat
- Använd fuzzy matching med högre tolerans
**Påverkan:** Kan matcha ytterligare 50-100 startups
**Svårighet:** Medel

#### 2.2 Komplettera SCB-matchningar för andra typer
**Fokus på:**
- 72 Public Sector utan matchning
- 46 Academia utan matchning
- 18 Media utan matchning
- 21 Network utan matchning

**Utmaning:** Många av dessa är inte traditionella företag med organisationsnummer (t.ex. utländska universitet, nätverk, medier)

#### 2.3 Web scraping för företag med webbsidor
**Vad:** Skrapa 915 webbsidor för att extrahera:
- Kontaktinformation (telefon, e-post, adress)
- Företagsbeskrivningar (förbättra description)
- Teamstorlek / antal anställda
- LinkedIn-länk
- Produkter/tjänster
**Påverkan:** Kan berika 800+ företag
**Svårighet:** Medel till Hög
**Tekniker:**
- BeautifulSoup / Scrapy för HTML-parsing
- Selenium för JavaScript-tunga sajter
- Rate limiting för att inte överbelasta

#### 2.4 LinkedIn-berikning
**Vad:** Hämta data från LinkedIn företagssidor
**Data att samla:**
- Antal anställda (mer aktuellt än SCB)
- Huvudkontor / location
- Bransch
- Företagsbeskrivning
- Specialiseringar
**Påverkan:** Kan berika 700+ företag
**Svårighet:** Medel
**Metod:** LinkedIn API (kräver auktorisering) eller försiktig scraping

#### 2.5 Crunchbase-berikning (för startups)
**Vad:** Hämta startup-data från Crunchbase
**Data att samla:**
- Finansieringsrundor och belopp
- Investerare
- Grundare
- Antal anställda
- Valuation
**Påverkan:** Kan berika 200-300 startups
**Svårighet:** Medel
**Metod:** Crunchbase API (kräver betalning) eller scraping

---

### 🔴 PRIORITET 3: KOMPLEXA ÅTGÄRDER (1-4 veckor)

#### 3.1 AI-klassificering av företagsbeskrivningar
**Vad:** Använd NLP/LLM för att analysera beskrivningar
**Mål:**
- Klassificera typ av AI (NLP, Computer Vision, Robotics, etc.)
- Identifiera användningsområden
- Extrahera teknologier (TensorFlow, PyTorch, etc.)
- Kategorisera bransch mer detaljerat
**Påverkan:** Alla 862 företag med beskrivningar
**Svårighet:** Hög
**Tekniker:**
- OpenAI GPT-4 API
- Claude API
- Open-source LLMs (Llama, Mistral)
- Custom NER-modeller

#### 3.2 Automatisk maturity/tillväxtfas-klassificering
**Vad:** Fylla i `maturity`-kolumnen baserat på:
- Antal anställda
- Omsättning
- Startdatum (ålder)
- Finansieringsrundor
- Webbplatsens mognad
**Klasser:**
- Pre-seed
- Seed
- Early stage
- Growth
- Mature
- Enterprise
**Påverkan:** Alla 1,113 företag
**Svårighet:** Hög

#### 3.3 Nätverksanalys
**Vad:** Kartlägga relationer mellan företag
**Metod:**
- Dela gemensamma styrelseledamöter (från Bolagsverket)
- Partner-mentions på webbsidor
- Gemensamma investerare
- LinkedIn-kopplingar
**Output:** Graf-databas med relationer
**Påverkan:** Nya insikter om ekosystemet
**Svårighet:** Mycket hög

#### 3.4 Tidsserie-tracking
**Vad:** Historisk data över tid
**Data att tracka:**
- Anställdutveckling
- Omsättningsutveckling
- Produktlansering
- Finansieringsevent
- Nyhetsartiklar
**Svårighet:** Mycket hög
**Kräver:** Kontinuerlig datainsamling framöver

---

## 📋 PRIORITERAD HANDLINGSPLAN

### Fas 1: Snabba vinster (Vecka 1)
1. ✅ Extrahera SCB-data från payload → Nya kolumner
2. ✅ Synka location_city från SCB
3. ✅ Ta bort/utvärdera tomma kolumner (maturity, accepts_interns, owner)
4. ✅ Identifiera saknade webbsidor (Google-sökning för 50-100 företag)

**Resultat efter Fas 1:**
- ~15 nya användbara kolumner
- ~540 företag får stad/kommun
- ~100 företag får webbsida
- Renare databasstruktur

### Fas 2: Öka täckning (Vecka 2-3)
1. ✅ Öka SCB-matchningar (fokus på startups)
2. ✅ Web scraping för 500+ webbsidor (kontaktinfo, beskrivningar)
3. ✅ LinkedIn-berikning för 300 företag
4. ✅ Crunchbase för 100 startups

**Resultat efter Fas 2:**
- 100+ nya SCB-matchningar
- 500+ företag med förbättrad kontaktinfo
- 300+ företag med LinkedIn-data
- 100 startups med finansieringsinfo

### Fas 3: AI & automatisering (Vecka 4-6)
1. ✅ AI-klassificering av företagsbeskrivningar
2. ✅ Automatisk maturity-klassificering
3. ✅ Fortsatt web scraping (resterande 400 företag)
4. ✅ Validering och kvalitetskontroll

**Resultat efter Fas 3:**
- Alla företag klassificerade efter AI-typ
- Maturity-fält ifyllt för alla
- 90%+ har webbsida
- Hög datakvalitet

---

## 🎯 FÖRVÄNTADE RESULTAT

### Innan berikning (nuläge)
- Genomsnittlig datakomplettering: 65.1%
- Företag med 0 berikningsdata: 23 (2.1%)
- Företag med full berikning: 0 (0%)
- SCB-täckning: 53.2%
- Webbsida-täckning: 82.2%

### Efter Fas 1 (Snabba vinster)
- Genomsnittlig datakomplettering: ~72%
- Nya kolumner: +15
- Företag med stad: +540
- Företag med webbsida: +100

### Efter Fas 2 (Öka täckning)
- Genomsnittlig datakomplettering: ~80%
- SCB-täckning: ~60%
- Företag med kontaktinfo: +500
- Företag med LinkedIn: +300

### Efter Fas 3 (AI & automatisering)
- Genomsnittlig datakomplettering: ~88%
- Alla företag klassificerade
- Maturity fylld: 100%
- Webbsida-täckning: 90%+

---

## 🚨 VARNINGAR & RISKER

### Dataskydd
- ⚠️ Web scraping: Respektera robots.txt och använd rate limiting
- ⚠️ GDPR: Personuppgifter (telefon, e-post) kräver laglig grund
- ⚠️ LinkedIn: Strikt mot scraping - använd officiell API

### Datakvalitet
- ⚠️ SCB-data kan vara föråldrad (uppdateringsfrekvens?)
- ⚠️ Företag kan ha bytt namn, fusionerat, lagts ner
- ⚠️ Webbsidor kan ge felaktig information
- ⚠️ AI-klassificering kan göra fel - kräver validering

### Tekniska risker
- ⚠️ API-kostnader (Crunchbase, OpenAI, etc.)
- ⚠️ Web scraping kan blockeras
- ⚠️ Stort antal requests kan överbelasta system

---

## 📝 SAMMANFATTNING

### Nuvarande tillstånd
Databasen har en **solid grund** med 1,113 svenska AI-företag och **mycket värdefull SCB-data** för 592 företag. Däremot finns betydande **luckor i datakomplettering** (genomsnitt 65%) och **ingen företag har full berikning**.

### Största problemområden
1. **Oanvänd SCB-data** - Rik information finns i JSON-payload men används inte
2. **Tomma kolumner** - maturity (100%), accepts_interns (100%), owner (97%)
3. **Låg SCB-täckning för vissa typer** - Särskilt startups (48%), academia (33%), media (22%)
4. **location_city inte synkad** - 892 saknar stad trots att 592 har det i SCB
5. **Ingen full berikning** - Inte ett enda företag har alla 5 typer av berikningsdata

### Största möjligheterna
1. **Extrahera SCB-data** → 592 företag får 10-15 nya datafält OMEDELBART
2. **Synka location_city** → ~540 företag får stad
3. **Web scraping** → 915 webbsidor kan ge kontaktinfo, teamstorlek, produkter
4. **LinkedIn-berikning** → Aktuell anställdsdata för 700+ företag
5. **AI-klassificering** → Automatisk kategorisering av 862 företagsbeskrivningar

### Rekommenderad väg framåt
**Starta med Fas 1** (Snabba vinster) för att få omedelbar effekt. Extrahera SCB-data och synka location_city kan göras **på några timmar** och ger **massiv förbättring**.

Sedan fortsätta med **Fas 2** för att öka täckning och kvalitet genom web scraping och externa APIs.

Avsluta med **Fas 3** för att lägga till AI-driven klassificering och automatisering för framtida underhåll.

---

## 📧 KONTAKT

För frågor eller implementation av dessa rekommendationer, kontakta databasansvarig.

**Rapport skapad av:** Databas-analysverktyg
**Datum:** 2025-11-10
**Version:** 1.0

# Web Scraping Train Crash - Post Mortem

## Projektets Målsättning

**Huvudmål:** Hitta organisationsnummer (org.nr) för 437 svenska företag i AI-databasen som saknar SCB-berikningsdata.

**Specifika krav:**
- Hitta FLER matchningar, inte ge upp på svåra företag
- Använda web scraping via DuckDuckGo för att söka på allabolag.se och bolagsfakta.se
- Exportera resultat till CSV för manuell verifiering
- Målet var att uppnå minst 60% träffsäkerhet
- Endast svenska företag som finns i SCB-databasen

**Bakgrund:**
- Databas: ai_companies.db med 724 företag totalt
- 287 företag hade redan SCB-berikningsdata
- 437 företag saknade SCB-data och behövde organisationsnummer
- API-nyckeln saknar tillgång till "publicsector"-typ i SCB

---

## Teknisk Grund

### Datakällor
- **allabolag.se** - Format: "Decerno Aktiebolag - Org.nr 556498-5025 - Stockholm"
- **bolagsfakta.se** - URL-format: "bolagsfakta.se/5569631913-AIxDesign_Global_AB"

### Teknologier
- Python 3 med ddgs library (DuckDuckGo Search)
- fuzzywuzzy för fuzzy string matching
- SQLite-databas
- Rate limiting: 1.5 sekunder mellan sökningar
- CSV-export för manuell verifiering

### Org.nr Format
- Standard: XXXXXX-XXXX (6 siffror, bindestreck, 4 siffror)
- 10-siffror: XXXXXXXXXX
- 12-siffror med 16-prefix: 16XXXXXXXXXX

---

## Kronologisk Redovisning av Försök

### Version 1: Initial Implementation (Tidigt i projektet)

**Approach:**
- 4 söktermer per företag:
  1. `företagsnamn organisationsnummer`
  2. `företagsnamn juridiskt namn`
  3. `företagsnamn site:allabolag.se`
  4. `företagsnamn site:bolagsfakta.se`
- Hämtade 3 resultat per sökning
- Tog första organiska resultatet med org.nr

**Resultat:**
- **Träffsäkerhet: 30% (3/10)**
- Problem identifierade:
  - Konstiga sökningar gjordes
  - Många resultat hade rätt företagsnamn men inget org.nr
  - Icke-svenska resultat dök upp
  - Vissa korrekta träffar i sökresultat 2 missades

**CSV-struktur:** Omfattande med 30+ kolumner för alla 4 sökningar

---

### Version 2: Förenkling Efter Användarfeedback

**Ändringar:**
- Reducerade till 2 söktermer:
  1. `företagsnamn + site:allabolag.se`
  2. `företagsnamn + site:bolagsfakta.se`
- Förenklad CSV till 14 kolumner:
  - company_id, company_name
  - search_query_1, best_match_1, found_orgnr_1
  - search_query_2, best_match_2, found_orgnr_2
  - suggested_orgnr, confidence_score, suggestion_reason
  - verified_orgnr, notes
- Ökade antal resultat från 3 till 5 per sökning
- La till fuzzy matching för namnkontroll
- Förbättrade org.nr-extraktion med prioriterade mönster för allabolag/bolagsfakta
- La till företagsnamnextraktion från både titel och URL

**Kod-förbättringar:**
```python
# Ad filtering
skip_domains = ['google.', 'bing.', 'yahoo.', 'wikipedia.', 'facebook.']

# Company name extraction
def extract_company_name_from_result(text: str, url: str) -> str:
    # From allabolag format: "CompanyName AB - Org.nr..."
    # From bolagsfakta URL: "bolagsfakta.se/5569631913-CompanyName_AB"
```

**Resultat:**
- Bättre än version 1, men fortfarande inte tillräckligt bra
- Exakt träffsäkerhet ej dokumenterad

---

### Version 3: Title-operatorn Katastrof

**Ändringar:**
- La till `title:"{företagsnamn}"` prefix till sökfrågorna
- Tanken: Förbättra precision genom att matcha endast sidtitlar

**Kod:**
```python
queries = [
    f'title:"{name}" site:allabolag.se',
    f'title:"{name}" site:bolagsfakta.se'
]
```

**Resultat:**
- **KATASTROF: Träffsäkerhet sjönk från ~60% till 10% (1/10)**
- Användarens feedback: "nej det är fortfarande alldeles för dåligt"
- Problem: DuckDuckGos title:-operator var för strikt
- För många giltiga resultat filtrerades bort

**Åtgärd:**
- Omedelbart återställd (reverterad title:-operatorn)

**Testfil:** `orgnr_search_20251112_230507.csv` (1/10 lyckades)

---

### Version 4: Första Resultatet Utan Validering

**Approach:**
- Tog bort title:-operatorn
- Ökade till 10 resultat per sökning (för att komma förbi annonser)
- Filtrera bort annonser baserat på URL-mönster
- **KRITISK BRIST:** Tog första organiska resultatet utan att validera företagsnamnet

**Kod (problemet):**
```python
for result in results:
    # Filter out ads
    if any(domain in url for domain in skip_domains):
        continue

    # Extract org.nr
    orgnr = extract_orgnr_candidates(text)
    if orgnr:
        return (url, text, orgnr)  # RETURNERAR FÖRSTA MED ORG.NR!
```

**Resultat:**
- **Träffsäkerhet: 10-20% (1-2/10)**
- **Allvarliga fel - Helt FELAKTIGA företag returnerades:**
  - "AI Coach Mikael Vilkas" → "Mabel AI AB" (FEL FÖRETAG)
  - "ALMI Mälardalen" → "BDO Malardalen Intressenter AB" (FEL FÖRETAG)
  - "Arlaplast" → Inget resultat (borde hitta "Arla Plast AB")
  - "Amazon (AWS)" → "Httpool AB" (FEL FÖRETAG)

**Problem:**
- Scriptet hittade rätt sökresultatsida men valde fel företag från sidan
- Ingen validering att företagsnamnet i resultatet matchade det sökta namnet
- BDO Mälardalen ≠ ALMI Mälardalen (helt olika företag!)

**Användarens feedback:** "det är fortfarande alldeles för dåligt. den matchar uppenbarligt dåligt och ger då fel org nummer. du kan läsa själv i orgnr_search_20251112_231116.csv"

**Testfil:** `orgnr_search_20251112_231116.csv`

---

### Version 5: Jämför ALLA Resultat (Slutlig Version i Traincrash)

**Approach - STORA ÄNDRINGAR:**
- Extrahera ALLA organiska resultat (inte bara första)
- Jämför varje kandidats företagsnamn med det sökta namnet
- Välj resultatet med HÖGST namnlikhet (fuzzy matching)
- Tröskel: >60% likhet för att accepteras
- Fallback till första med org.nr om ingen bra matchning

**Kod (förbättringen):**
```python
def duckduckgo_search(query: str, searched_name: str) -> Tuple[str, str, str, str]:
    """
    Sök på DuckDuckGo och returnera BÄSTA träffen baserat på namnmatchning
    """
    # Samla ALLA organiska resultat
    organic_results = []
    for result in results:
        # Filter ads...
        text = f"{title} {body} {url}"
        company_name = extract_company_name_from_result(text, url)
        orgnr_list = extract_orgnr_candidates(text)
        orgnr = orgnr_list[0] if orgnr_list else ""

        if not company_name and not orgnr:
            continue

        organic_results.append({
            'url': url,
            'text': text[:500],
            'company_name': company_name or "",
            'orgnr': orgnr,
        })

    # Hitta BÄSTA matchningen genom namnlikhet
    searched_normalized = normalize_company_name(searched_name)
    best_match = None
    best_similarity = 0

    for candidate in organic_results:
        if not candidate['company_name']:
            continue
        candidate_normalized = normalize_company_name(candidate['company_name'])
        similarity = fuzz.ratio(searched_normalized, candidate_normalized)

        if similarity > best_similarity:
            best_similarity = similarity
            best_match = candidate

    # Om vi hittade en bra matchning (>60% likhet), använd den
    if best_match and best_similarity >= 60:
        return (best_match['url'], best_match['text'],
                best_match['company_name'], best_match['orgnr'])

    # Fallback: första med org.nr
    for candidate in organic_results:
        if candidate['orgnr']:
            return (candidate['url'], candidate['text'],
                    candidate['company_name'], candidate['orgnr'])

    return ("", "[ERROR: No results found.]", "", "")
```

**Namnormalisering:**
```python
def normalize_company_name(name: str) -> str:
    """Normalisera företagsnamn för bättre matchning"""
    name = name.lower()
    name = re.sub(r'\b(ab|aktiebolag|aktiebolaget)\b', '', name)
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name
```

**Resultat:**
- **Träffsäkerhet: FORTFARANDE FÖR DÅLIG**
- Användarens feedback: "nej det funkar fortfarande inte. du kan läsa själv i filen orgnr_search_20251112_232814.csv"
- Trots alla förbättringar: Fungerade inte tillräckligt bra

**Testfil:** `orgnr_search_20251112_232814.csv`

**Commit:** `cfb28e4 - Fix: Jämför ALLA sökresultat och välj bästa namnmatchning`

---

## Sammanfattning av Resultat

| Version | Approach | Träffsäkerhet | Status |
|---------|----------|---------------|--------|
| V1 | 4 söktermer, 3 resultat, första med org.nr | 30% (3/10) | Dålig |
| V2 | 2 söktermer, 5 resultat, fuzzy matching | ~50-60%? | Bättre men ej tillräcklig |
| V3 | Med title:-operator | 10% (1/10) | **KATASTROF** |
| V4 | Utan title:, men tar första resultat | 10-20% (1-2/10) | **FEL FÖRETAG** |
| V5 | Jämför alla, välj bästa namn-match | Fortfarande dålig | **MISSLYCKADES** |

---

## Varför Det Misslyckades

### Grundläggande Problem

1. **DuckDuckGo-begränsningar:**
   - Sökresultat är inte optimerade för strukturerad datautvinning
   - Annonser och irrelevanta resultat förorenar träffarna
   - Sökmotorns ranking matchar inte våra behov

2. **Namnvariationer:**
   - Företagsnamn förekommer i många varianter:
     - "Arlaplast" vs "Arla Plast AB"
     - "ALMI Mälardalen" vs andra företag med "Mälardalen"
     - "AI Coach Mikael Vilkas" (personnamn + verksamhet)
   - Fuzzy matching räcker inte för att hantera alla variationer

3. **Strukturella utmaningar:**
   - Många företag har liknande namn (särskilt inom offentlig sektor)
   - Vissa företag är svåra att skilja från varandra
   - Personnamn + verksamhetsbeskrivning (inte officiellt företagsnamn)

4. **Web scraping inherent instabilitet:**
   - Sökmotorresultat varierar
   - HTML-struktur kan ändras
   - Rate limiting och IP-blockering risk
   - Ingen garanti för datakvalitet

### Tekniska Begränsningar

1. **Informationsutvinning:**
   - Svårt att extrahera företagsnamn korrekt från sökresultat
   - Org.nr finns inte alltid i snippet/preview-text
   - Måste ibland gå in på sidan för att få org.nr (gjordes ej)

2. **Matchningslogik:**
   - 60% likhet-tröskel kan vara för låg ELLER för hög beroende på fall
   - normalize_company_name() tar bort viktig information ibland
   - Fuzzy matching ger falska positiva när många företag har liknande namn

3. **Skalbarhet:**
   - 1.5 sekunders fördröjning × 437 företag × 2 sökningar = ~22 minuter per körning
   - Varje iteration kräver manuell verifiering av CSV
   - Långsam feedback-loop för förbättringar

---

## Vad Vi Lärde Oss

### Fungerade Bra
- CSV-export för manuell verifiering
- Grundläggande org.nr-extraktion med regex
- Ad filtering baserat på URL-mönster
- Rate limiting för att undvika IP-ban

### Fungerade INTE
- title:-operator i DuckDuckGo (för strikt)
- Att ta första resultatet utan validering (ger fel företag)
- Fuzzy matching ensamt för företagsnamn (för många false positives)
- Web scraping som primär metod för denna uppgift

### Insikter
1. **Web scraping är inte rätt verktyg för detta problem**
   - För opålitligt för strukturerad datautvinning
   - Kräver för mycket manuell validering
   - Skalerar dåligt

2. **Bättre alternativ skulle vara:**
   - Direktåtkomst till Bolagsverkets API/databas
   - SCB:s egna API med rätt behörigheter
   - Kommersiella datakällor (Bisnode, UC, etc.)
   - Manuell sökning i mindre batchar med mänsklig validering

3. **Strukturerad data > Osökstrukturerad webbsökning**
   - API:er med strukturerad data är mer tillförlitliga
   - Mindre risk för felaktiga matchningar
   - Snabbare och mer skalbart

---

## Slutsats

Efter 5 iterationer och omfattande felsökning uppnåddes aldrig målsättningen om 60% träffsäkerhet på ett tillförlitligt sätt. De huvudsakliga problemen var:

- **Felaktiga företagsmatchningar** (BDO istället för ALMI, Mabel AI istället för AI Coach, etc.)
- **Missade träffar** för företag som definitivt finns i källorna
- **Instabil prestanda** som varierade kraftigt mellan körningar

**Rekommendation:** Överge web scraping-metoden och använd istället:
1. Bolagsverkets öppna API
2. SCB API med utökade behörigheter
3. Kommersiell datakälla med verifierade organisationsnummer
4. Manuell sökning i mindre batchar med verifiering

Detta projekt arkiveras som "traincrash" för att dokumentera vad som prövades och varför det inte fungerade.

---

## Filer i Detta Arkiv

- `web_search_orgnr_finder.py` - Slutlig version av scriptet (V5)
- `README.md` - Denna dokumentation

## Relaterade Testfiler (i huvudprojektet)

- `orgnr_search_20251112_230507.csv` - Test med title:-operator (1/10)
- `orgnr_search_20251112_231116.csv` - Test utan title: men tar första resultat (många fel)
- `orgnr_search_20251112_232814.csv` - Test med jämförelse av alla resultat (fortfarande dåligt)

---

*Projekt avslutat: 2025-11-12*
*Status: Misslyckad - Metoden fungerar inte tillräckligt bra*
*Nästa steg: Utvärdera alternativa metoder för organisationsnummer-matchning*

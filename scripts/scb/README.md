# SCB Integration Scripts

Scripts för integration med SCB (Statistiska Centralbyrån) för att berika företagsdata.

## Scripts

### scb_integration_v2.py
Huvudscript för SCB-integration (version 2).
- Söker efter företag i SCB:s databas
- Matchar företag baserat på namn och stad
- Sparar berikad data i `scb_enrichment` tabellen

**Användning:**
```bash
python scripts/scb/scb_integration_v2.py
```

### retry_scb_search.py
Försöker matcha företag som tidigare misslyckats.
- Kör om sökningar för företag utan matchning
- Använder förbättrade sökalgorithmer

**Användning:**
```bash
python scripts/scb/retry_scb_search.py
```

### retry_no_candidates.py
Specifikt för företag där inga kandidater hittades.
- Försöker alternativa sökstrategier
- Justerar matchningskriterier

**Användning:**
```bash
python scripts/scb/retry_no_candidates.py
```

## SCB-data

Berikad data inkluderar:
- Organisationsnummer
- Adressinformation
- Kommun och län
- Antal anställda
- Företagsstatus
- Branschkoder (SNI)
- Omsättning
- Kontaktinformation

Se också: `docs/SCB_INTEGRATION_V2_GUIDE.md`

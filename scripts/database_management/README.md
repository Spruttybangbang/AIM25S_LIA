# Databashantering

Scripts för hantering och underhåll av databaser.

## Scripts

### delete_companies.py
Tar bort företag permanent från databasen baserat på ID:n.
- Visar företag som ska tas bort
- Tar bort all relaterad data (sektorer, domäner, SCB-data)
- Kräver bekräftelse

**Användning:**
```bash
python scripts/database_management/delete_companies.py
```

### move_companies_to_others.py
Flyttar företag från ai_companies.db till ai_others.db.
- Kopierar all data till måldatabas
- Tar bort från källdatabas
- Bevarar alla relationer

**Användning:**
```bash
python scripts/database_management/move_companies_to_others.py
```

### verify_databases.py
Verifierar antal företag i båda databaser.

**Användning:**
```bash
python scripts/database_management/verify_databases.py
```

### check_db.py
Snabb kontroll av antal företag i ai_companies.db.

### interactive_deduplication.py
Interaktivt verktyg för att identifiera och hantera dubbletter.

### fas1_snabba_vinster.py
Fas 1-script för snabba förbättringar av datakvalitet.

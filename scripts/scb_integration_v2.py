#!/usr/bin/env python3
"""
SCB-integration V2 för PRAKTIKJAKT
Hämtar location_city för företag från SCB:s företagsregister

Förbättringar från V1:
- Robust API-hantering (session, retries, backoff)
- Separat tabell scb_matches (påverkar inte original-data)
- CSV-export av problemfall
- Bättre namn-normalisering
- Dynamisk fuzzy-threshold
- Filtrering på type (startup/corporation/supplier/ngo)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from fuzzywuzzy import fuzz
except ImportError as e:
    raise SystemExit("Saknar 'fuzzywuzzy'. Installera: pip install fuzzywuzzy python-Levenshtein --break-system-packages") from e


# ============================================================================
# KONFIGURATION
# ============================================================================

DEFAULT_DB = "../ai_companies.db"
DEFAULT_CERT = "../../SCB/certifikat/Certifikat_SokPaVar_A00592_2025-10-29_09-27-36Z.pem"
API_URL = "https://privateapi.scb.se/nv0101/v1/sokpavar/api/je/HamtaForetag"
TIMEOUT_SEC = 30
RATE_LIMIT_DELAY = 0.5
MAX_TOTAL_RETRIES = 5
BACKOFF_FACTOR = 0.5
STATUS_FORCELIST = (429, 500, 502, 503, 504)
BASE_FUZZY_THRESHOLD = 85

# Logger setup
logger = logging.getLogger("scb_integration")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ============================================================================
# PATH VALIDATION
# ============================================================================

def validate_db_path(db_path: str) -> Path:
    p = Path(db_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Databas hittades inte: {p}")
    return p

def validate_cert(cert: Optional[str | Tuple[str,str]]) -> Optional[str | Tuple[str,str]]:
    if cert is None:
        return None
    if isinstance(cert, (tuple, list)):
        c, k = cert
        c, k = str(Path(c).expanduser()), str(Path(k).expanduser())
        if not Path(c).exists():
            raise FileNotFoundError(f"Certifikat saknas: {c}")
        if not Path(k).exists():
            raise FileNotFoundError(f"Nyckel saknas: {k}")
        return (c, k)
    c = str(Path(cert).expanduser())
    if not Path(c).exists():
        raise FileNotFoundError(f"Certifikat saknas: {c}")
    return c


# ============================================================================
# SESSION MED RETRY-LOGIK
# ============================================================================

def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=MAX_TOTAL_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=STATUS_FORCELIST,
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s

SESSION = make_session()
_query_cache: Dict[str, List[dict]] = {}


# ============================================================================
# NAMN-NORMALISERING & FUZZY MATCHING
# ============================================================================

def normalize_company_name(name: str) -> str:
    """Normalisera företagsnamn för bättre matchning"""
    if not name:
        return ""
    
    n = name.lower()
    # Hantera svenska tecken
    n = n.translate(str.maketrans({"å": "a", "ä": "a", "ö": "o"}))
    
    # Ta bort företagsformer och vanliga suffix
    kill_words = [
        r"\bab\b", r"\baktiebolag\b", r"\b(ltd|limited)\b", r"\b(inc|incorporated)\b",
        r"\bpubl\b", r"\bhb\b", r"\bkb\b", r"\bfilial\b",
        r"\bsverige\b", r"\bsweden\b", 
        r"\bi stockholm\b", r"\bi goteborg\b", r"\bi malmo\b",
        r"\bgroup\b", r"\bholding\b", r"\btech\b",
    ]
    n = re.sub("|".join(kill_words), " ", n)
    
    # Ta bort domännamn
    n = re.sub(r"\b[a-z0-9-]+\.(com|se|io|ai|org|net)\b", " ", n)
    
    # Behåll endast alfanumeriska tecken
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    n = re.sub(r"\s+", " ", n)
    
    return n

def score_names(a: str, b: str) -> int:
    """Kombinerad fuzzy-score för bättre matchning"""
    s1 = fuzz.ratio(a, b)
    s2 = fuzz.partial_ratio(a, b)
    s3 = fuzz.token_set_ratio(a, b)
    
    # Viktad kombination
    score = int(0.5 * s3 + 0.3 * s1 + 0.2 * s2)
    
    # Bonus för nästan perfekt match
    if s3 >= 95 and abs(len(a) - len(b)) <= 3:
        score = max(score, 97)
    
    return score

def dynamic_threshold(raw_name: str, base: int = BASE_FUZZY_THRESHOLD) -> int:
    """Högre krav för korta namn"""
    L = len(normalize_company_name(raw_name))
    if L <= 6:
        return max(base, 92)
    if L <= 10:
        return max(base, 88)
    return base


# ============================================================================
# API-KOMMUNIKATION
# ============================================================================

@dataclass
class ApiResult:
    ok: bool
    data: List[dict]
    status_code: int
    error: Optional[str] = None

def scb_search_api(company_name: str, cert) -> ApiResult:
    """Sök företag i SCB API med robust error handling"""
    
    # Cache-nyckel
    cache_key = normalize_company_name(company_name)
    if cache_key in _query_cache:
        logger.debug(f"Cache hit för '{company_name}'")
        return ApiResult(True, _query_cache[cache_key], 200)
    
    # SCB:s faktiska payload-format
    payload = {
        "Företagsstatus": "1",  # Verksamma företag
        "Registreringsstatus": "1",  # Registrerade företag
        "variabler": [
            {
                "Varde1": company_name,
                "Varde2": "",
                "Operator": "Innehaller",  # Innehåller namnet
                "Variabel": "Namn"
            }
        ]
    }
    
    logger.debug(f"API Request: {API_URL}")
    logger.debug(f"Payload: {payload}")
    logger.debug(f"Cert: {cert}")
    
    delay = RATE_LIMIT_DELAY
    
    for attempt in range(MAX_TOTAL_RETRIES):
        try:
            resp = SESSION.post(
                API_URL,
                json=payload,
                cert=cert,
                timeout=TIMEOUT_SEC
            )
            logger.debug(f"Response status: {resp.status_code}")
            if resp.status_code != 200:
                logger.debug(f"Response headers: {dict(resp.headers)}")
                logger.debug(f"Response body (first 500 chars): {resp.text[:500]}")
        except requests.RequestException as e:
            logger.warning(f"Nätverksfel (försök {attempt+1}/{MAX_TOTAL_RETRIES}): {e}")
            time.sleep(delay)
            delay *= (1.5 + BACKOFF_FACTOR)
            continue
        
        # Hantera rate limiting
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "1.0"))
            wait = max(delay, retry_after)
            logger.info(f"Rate-limited (429). Väntar {wait:.2f}s...")
            time.sleep(wait)
            delay *= (1.5 + BACKOFF_FACTOR)
            continue
        
        # Hantera server errors
        if resp.status_code >= 500:
            logger.warning(f"Serverfel {resp.status_code} (försök {attempt+1})")
            time.sleep(delay)
            delay *= (1.5 + BACKOFF_FACTOR)
            continue
        
        # Parse response
        try:
            data = resp.json()
        except ValueError:
            logger.error("Icke-JSON svar från API")
            return ApiResult(False, [], resp.status_code, "Non-JSON response")
        
        # SCB returnerar direkt en lista, inte {"value": [...]}
        result_data = []
        if isinstance(data, list):
            result_data = data
        elif isinstance(data, dict):
            # Fallback om de ändrar format
            result_data = data.get('value', [])
        
        _query_cache[cache_key] = result_data
        time.sleep(RATE_LIMIT_DELAY)
        return ApiResult(True, result_data, resp.status_code)
    
    return ApiResult(False, [], 599, "Max retries exceeded")


# ============================================================================
# MATCHNING
# ============================================================================

def find_best_match(our_name: str, scb_rows: List[dict]) -> Tuple[Optional[dict], int]:
    """Hitta bästa match från SCB-resultat"""
    our_norm = normalize_company_name(our_name)
    
    best, best_score = None, 0
    for candidate in scb_rows:
        # SCB använder Företagsnamn (med å/ä/ö)
        scb_name = candidate.get("Företagsnamn", "").strip()
        
        scb_norm = normalize_company_name(scb_name)
        score = score_names(our_norm, scb_norm)
        
        if score > best_score:
            best, best_score = candidate, score
    
    return best, best_score


# ============================================================================
# DATABAS-HANTERING
# ============================================================================

def get_companies_without_location(
    db_path: Path, 
    limit: Optional[int] = None, 
    only_types: Optional[List[str]] = None
) -> List[Tuple[int, str]]:
    """
    Hämta företag utan location_city
    Filtrerar på type om angivet
    """
    base = """
        SELECT id, name
        FROM companies
        WHERE (location_city IS NULL OR TRIM(location_city) = '')
    """
    params = []
    
    if only_types:
        norm = [t.strip().lower() for t in only_types if t.strip()]
        placeholders = ",".join("?" for _ in norm)
        base += f" AND LOWER(TRIM(type)) IN ({placeholders})"
        params.extend(norm)
    
    if limit:
        base += " LIMIT ?"
        params.append(limit)
    
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(base, params)
        return cur.fetchall()
    finally:
        conn.close()

def save_scb_match(
    db_path: Path, 
    company_id: int, 
    matched: bool, 
    match_score: int, 
    scb_data: dict, 
    dry_run: bool
) -> None:
    """
    Spara resultat i separat tabell scb_matches
    Skapar tabellen om den inte finns
    """
    if dry_run:
        city = scb_data.get("PostOrt") or scb_data.get("Postort") or "N/A"
        logger.info(f"DRY RUN: company_id={company_id} matched={matched} score={match_score} city={city}")
        return
    
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        
        # Skapa tabell om den inte finns
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scb_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                matched INTEGER NOT NULL,
                score INTEGER,
                city TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Extrahera stad från SCB-data (PostOrt)
        city = scb_data.get("PostOrt") or None
        
        # Spara match
        cur.execute(
            """INSERT INTO scb_matches 
               (company_id, matched, score, city, payload) 
               VALUES (?, ?, ?, ?, ?)""",
            (
                company_id, 
                1 if matched else 0, 
                int(match_score),
                city,
                json.dumps(scb_data, ensure_ascii=False)
            )
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# CSV-EXPORT
# ============================================================================

def export_issues(rows: List[Dict[str, str]], path: Path) -> None:
    """Exportera problemfall till CSV"""
    fieldnames = ["id", "name", "reason", "score", "best_candidate", "PostOrt"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# ============================================================================
# CLI
# ============================================================================

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SCB-integration V2 för PRAKTIKJAKT")
    p.add_argument("--db", default=DEFAULT_DB, help="Sökväg till SQLite-databas")
    p.add_argument("--cert", default=DEFAULT_CERT, help="Client cert path eller 'cert.pem,key.pem'")
    p.add_argument("--limit", type=int, default=None, help="Max antal företag att köra")
    p.add_argument("--min-score", type=int, default=BASE_FUZZY_THRESHOLD, help="Min fuzzy-score för match")
    p.add_argument("--only-type", type=str, default="startup,corporation,supplier,ngo", 
                   help="Kommaseparerad lista av type-värden")
    p.add_argument("--dry-run", action="store_true", help="Skriv inte till DB")
    p.add_argument("--issues-csv", type=str, default="scb_issues.csv", help="Exportera problemfall")
    p.add_argument("--verbose", action="store_true", help="Mer loggning")
    return p.parse_args(argv)


# ============================================================================
# MAIN
# ============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validera cert
    cert = None
    if args.cert:
        if "," in args.cert:
            cert = tuple(s.strip() for s in args.cert.split(",", 1))
        else:
            cert = args.cert
        cert = validate_cert(cert)
    
    # Validera DB
    db_path = validate_db_path(args.db)
    
    # Hämta företag
    only_types = [t.strip() for t in args.only_type.split(",")] if args.only_type else None
    companies = get_companies_without_location(db_path, limit=args.limit, only_types=only_types)
    
    logger.info(f"Startar körning på {len(companies)} företag")
    logger.info(f"Dry-run: {args.dry_run}")
    logger.info(f"Typer: {only_types or 'alla'}")
    
    # Statistik
    issues: List[Dict[str, str]] = []
    updated, low_score, not_found, api_errors = 0, 0, 0, 0
    
    for company_id, name in companies:
        # Sök i SCB
        api_result = scb_search_api(name, cert=cert)
        
        if not api_result.ok:
            api_errors += 1
            logger.error(f"[API ERROR] id={company_id} name='{name}' status={api_result.status_code}")
            issues.append({
                "id": str(company_id),
                "name": name,
                "reason": f"api_error_{api_result.status_code}",
                "score": "",
                "best_candidate": "",
                "PostOrt": "",
            })
            continue
        
        if not api_result.data:
            not_found += 1
            logger.info(f"[NO DATA] id={company_id} name='{name}'")
            issues.append({
                "id": str(company_id),
                "name": name,
                "reason": "no_candidates",
                "score": "",
                "best_candidate": "",
                "PostOrt": "",
            })
            continue
        
        # Hitta bästa match
        match, score = find_best_match(name, api_result.data)
        threshold = max(args.min_score, dynamic_threshold(name, base=args.min_score))
        
        if match and score >= threshold:
            updated += 1
            matched_name = match.get("Företagsnamn", "")
            city = match.get("PostOrt", "")
            logger.info(f"[MATCH] id={company_id} score={score} '{name}' -> '{matched_name}' ({city})")
            save_scb_match(db_path, company_id, True, score, match, dry_run=args.dry_run)
        else:
            low_score += 1
            cand_name = (match or {}).get("Företagsnamn", "")
            post_ort = (match or {}).get("PostOrt", "")
            logger.info(f"[LOW SCORE] id={company_id} score={score} thresh={threshold} '{name}' best='{cand_name}'")
            issues.append({
                "id": str(company_id),
                "name": name,
                "reason": "low_score",
                "score": str(score),
                "best_candidate": cand_name,
                "PostOrt": post_ort,
            })
    
    # Exportera problemfall
    issues_path = Path(args.issues_csv).expanduser().resolve()
    if issues:
        export_issues(issues, issues_path)
        logger.info(f"Issues exporterade till: {issues_path}")
    
    logger.info(f"")
    logger.info(f"=== SLUTSTATISTIK ===")
    logger.info(f"Uppdaterade: {updated}")
    logger.info(f"Låg score: {low_score}")
    logger.info(f"Inget resultat: {not_found}")
    logger.info(f"API-fel: {api_errors}")
    logger.info(f"Total: {len(companies)}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

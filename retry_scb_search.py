#!/usr/bin/env python3
"""
Retry SCB-sökning för företag utan kandidater
Använder samma API-metod som scb_integration_v2.py
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

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from fuzzywuzzy import fuzz
except ImportError as e:
    raise SystemExit("Saknar 'fuzzywuzzy'. Installera: pip install fuzzywuzzy python-Levenshtein --break-system-packages") from e

try:
    import ast
except ImportError:
    pass  # ast is in stdlib


# ============================================================================
# KONFIGURATION (SAMMA SOM scb_integration_v2.py)
# ============================================================================

DEFAULT_DB = "ai_companies.db"
DEFAULT_CERT = "../SCB/certifikat/Certifikat_SokPaVar_A00592_2025-10-29_09-27-36Z.pem"
API_URL = "https://privateapi.scb.se/nv0101/v1/sokpavar/api/je/HamtaForetag"
TIMEOUT_SEC = 30
RATE_LIMIT_DELAY = 0.5
MAX_TOTAL_RETRIES = 5
BACKOFF_FACTOR = 0.5
STATUS_FORCELIST = (429, 500, 502, 503, 504)
BASE_FUZZY_THRESHOLD = 85

# Logger setup
logger = logging.getLogger("retry_scb_search")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ============================================================================
# PATH VALIDATION (SAMMA SOM scb_integration_v2.py)
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
# SESSION MED RETRY-LOGIK (SAMMA SOM scb_integration_v2.py)
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
# NAMN-NORMALISERING & FUZZY MATCHING (SAMMA SOM scb_integration_v2.py)
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
# API-KOMMUNIKATION (SAMMA SOM scb_integration_v2.py)
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
# MATCHNING (SAMMA SOM scb_integration_v2.py)
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


def search_with_variants(
    company_id: int,
    name: str,
    search_variants: List[str],
    cert,
    min_score: int
) -> Tuple[Optional[dict], int, str]:
    """
    Sök med originalnamn först, sedan prova alla search_variants
    Returnerar (best_match, score, variant_used)
    """
    all_candidates = []
    variants_to_try = [name] + [v for v in search_variants if v != name]

    logger.info(f"  Söker med {len(variants_to_try)} varianter för '{name}'")

    for variant in variants_to_try:
        api_result = scb_search_api(variant, cert=cert)

        if not api_result.ok:
            logger.debug(f"    API-fel för variant '{variant}'")
            continue

        if api_result.data:
            logger.debug(f"    '{variant}' gav {len(api_result.data)} kandidater")
            # Tagga varje kandidat med vilken variant som hittade den
            for candidate in api_result.data:
                candidate['_search_variant'] = variant
            all_candidates.extend(api_result.data)
        else:
            logger.debug(f"    '{variant}' gav inga resultat")

    if not all_candidates:
        logger.info(f"  Inga kandidater hittades med någon variant")
        return None, 0, ""

    # Hitta bästa match över alla kandidater från alla varianter
    best_match, best_score = find_best_match(name, all_candidates)

    if best_match:
        variant_used = best_match.get('_search_variant', name)
        logger.info(f"  Bästa match: score={best_score}, variant='{variant_used}', företag='{best_match.get('Företagsnamn', '')}'")
        return best_match, best_score, variant_used

    return None, 0, ""


# ============================================================================
# DATABAS-HANTERING
# ============================================================================

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

        # Kolla om matchning redan finns
        cur.execute("SELECT id FROM scb_matches WHERE company_id = ?", (company_id,))
        existing = cur.fetchone()

        if existing:
            logger.info(f"Matchning finns redan för company_id={company_id}, skippar")
            return

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
    fieldnames = ["id", "name", "reason", "score", "best_candidate", "PostOrt", "variant_used"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


# ============================================================================
# MAIN
# ============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Retry SCB-sökning för företag utan kandidater")
    parser.add_argument("--db", default=DEFAULT_DB, help="Sökväg till SQLite-databas")
    parser.add_argument("--cert", default=DEFAULT_CERT, help="Client cert path eller 'cert.pem,key.pem'")
    parser.add_argument("--input", default="no_candidates_need_review.csv", help="CSV med företag att söka")
    parser.add_argument("--min-score", type=int, default=BASE_FUZZY_THRESHOLD, help="Min fuzzy-score för match")
    parser.add_argument("--dry-run", action="store_true", help="Skriv inte till DB")
    parser.add_argument("--issues-csv", type=str, default="retry_scb_issues.csv", help="Exportera problemfall")
    parser.add_argument("--verbose", action="store_true", help="Mer loggning")
    parser.add_argument("--limit", type=int, default=None, help="Max antal företag att köra")

    args = parser.parse_args(argv)

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

    # Ladda företag från CSV
    logger.info(f"Laddar företag från {args.input}")
    df = pd.read_csv(args.input)

    if args.limit:
        df = df.head(args.limit)

    logger.info(f"Startar körning på {len(df)} företag")
    logger.info(f"Dry-run: {args.dry_run}")

    # Statistik
    issues: List[Dict[str, str]] = []
    updated, low_score, not_found, api_errors = 0, 0, 0, 0

    for idx, row in df.iterrows():
        # Hantera både 'id' och 'original_id' kolumn
        if 'id' in row:
            company_id = int(row['id'])
        elif 'original_id' in row:
            company_id = int(row['original_id'])
        else:
            logger.error(f"Row saknar både 'id' och 'original_id': {row}")
            continue

        # Hantera både 'name' och 'original_name' kolumn
        if 'name' in row:
            name = row['name']
        elif 'original_name' in row:
            name = row['original_name']
        else:
            logger.error(f"Row saknar både 'name' och 'original_name': {row}")
            continue

        # Parsa search_variants från CSV (kan vara string eller redan lista)
        search_variants = []
        if 'search_variants' in row and pd.notna(row['search_variants']):
            variants_raw = row['search_variants']
            if isinstance(variants_raw, str):
                try:
                    search_variants = ast.literal_eval(variants_raw)
                except (ValueError, SyntaxError):
                    logger.warning(f"Kunde inte parsa search_variants för id={company_id}")
                    search_variants = []
            elif isinstance(variants_raw, list):
                search_variants = variants_raw
        elif 'correct_scb_name' in row and pd.notna(row['correct_scb_name']):
            # Fallback: använd correct_scb_name om search_variants saknas
            correct_name = row['correct_scb_name'].split('(')[0].strip()
            search_variants = [correct_name]

        logger.info(f"\n[{idx+1}/{len(df)}] Söker: id={company_id} name='{name}'")

        # Sök med alla varianter
        match, score, variant_used = search_with_variants(
            company_id, name, search_variants, cert, args.min_score
        )

        threshold = max(args.min_score, dynamic_threshold(name, base=args.min_score))

        if match and score >= threshold:
            updated += 1
            matched_name = match.get("Företagsnamn", "")
            city = match.get("PostOrt", "")
            logger.info(f"✓ [MATCH] id={company_id} score={score} variant='{variant_used}' -> '{matched_name}' ({city})")
            save_scb_match(db_path, company_id, True, score, match, dry_run=args.dry_run)
        elif match:
            low_score += 1
            cand_name = match.get("Företagsnamn", "")
            post_ort = match.get("PostOrt", "")
            logger.info(f"⚠ [LOW SCORE] id={company_id} score={score} thresh={threshold} '{name}' best='{cand_name}'")
            issues.append({
                "id": str(company_id),
                "name": name,
                "reason": "low_score",
                "score": str(score),
                "best_candidate": cand_name,
                "PostOrt": post_ort,
                "variant_used": variant_used,
            })
        else:
            not_found += 1
            logger.info(f"✗ [NO CANDIDATES] id={company_id} name='{name}'")
            issues.append({
                "id": str(company_id),
                "name": name,
                "reason": "no_candidates",
                "score": "",
                "best_candidate": "",
                "PostOrt": "",
                "variant_used": "",
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
    logger.info(f"Total: {len(df)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Script för att skrapa text från företagshemsidor.

Läser företag från ai_companies.db som har website och:
1. Besöker hemsidan
2. Extraherar huvudinnehåll (text)
3. Sparar till CSV för vidare bearbetning

Användning:
    python3 scripts/scrape_company_websites.py
    python3 scripts/scrape_company_websites.py --limit 10  # Testa på 10 företag först
    python3 scripts/scrape_company_websites.py --missing-only  # Bara företag utan description
"""

import sqlite3
import requests
import csv
from datetime import datetime
from bs4 import BeautifulSoup
import argparse
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
import re

# Timeout för HTTP requests
HTTP_TIMEOUT = 15

# Headers för att se ut som en riktig browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def clean_text(text):
    """
    Rensa och normalisera text.
    """
    # Ta bort extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Ta bort extra newlines
    text = re.sub(r'\n+', '\n', text)
    return text.strip()


def extract_meta_description(soup):
    """
    Försök hämta meta description från HTML.
    """
    meta_tags = [
        soup.find('meta', attrs={'name': 'description'}),
        soup.find('meta', attrs={'property': 'og:description'}),
        soup.find('meta', attrs={'name': 'twitter:description'})
    ]

    for tag in meta_tags:
        if tag and tag.get('content'):
            return clean_text(tag.get('content'))

    return None


def extract_main_content(soup):
    """
    Extrahera huvudinnehåll från HTML.
    Försöker hitta huvudtext och undvika navigation, footer, etc.
    """
    # Ta bort script, style, nav, footer
    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
        tag.decompose()

    # Prioritera main-taggar eller article-taggar
    main_content = soup.find('main') or soup.find('article')

    if main_content:
        text = main_content.get_text(separator=' ', strip=True)
    else:
        # Fallback: ta allt från body
        body = soup.find('body')
        if body:
            text = body.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)

    # Rensa texten
    text = clean_text(text)

    # Begränsa till rimlig längd (max 5000 tecken)
    if len(text) > 5000:
        text = text[:5000] + '...'

    return text


def scrape_website(url, company_name):
    """
    Skrapa text från en hemsida.

    Returns:
        dict: {
            'scraped_text': str,
            'meta_description': str or None,
            'status': str,
            'status_code': int or None
        }
    """
    print(f"\n🌐 Skrapar: {url}")

    # Säkerställ att URL har protokoll
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    result = {
        'scraped_text': '',
        'meta_description': None,
        'status': 'unknown',
        'status_code': None
    }

    try:
        # Försök först med HTTPS
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=HTTP_TIMEOUT,
            allow_redirects=True
        )

        result['status_code'] = response.status_code

        if response.status_code == 200:
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Hämta meta description
            meta_desc = extract_meta_description(soup)
            result['meta_description'] = meta_desc

            # Hämta huvudinnehåll
            main_text = extract_main_content(soup)
            result['scraped_text'] = main_text

            if main_text:
                word_count = len(main_text.split())
                print(f"   ✓ Lyckades! Skrapade {word_count} ord")
                if meta_desc:
                    print(f"   ✓ Meta description: {meta_desc[:80]}...")
                result['status'] = 'success'
            else:
                print(f"   ⚠ Lyckades besöka men ingen text hittades")
                result['status'] = 'no_content'

        elif response.status_code == 403:
            print(f"   ✗ Åtkomst nekad (403 Forbidden)")
            result['status'] = 'forbidden'

        elif response.status_code == 404:
            print(f"   ✗ Sidan hittades inte (404)")
            result['status'] = 'not_found'

        else:
            print(f"   ✗ HTTP {response.status_code}")
            result['status'] = f'http_{response.status_code}'

    except requests.exceptions.SSLError as e:
        print(f"   ✗ SSL-fel, försöker med HTTP...")
        # Försök med HTTP istället
        try:
            http_url = url.replace('https://', 'http://')
            response = requests.get(
                http_url,
                headers=HEADERS,
                timeout=HTTP_TIMEOUT,
                allow_redirects=True
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                result['meta_description'] = extract_meta_description(soup)
                result['scraped_text'] = extract_main_content(soup)
                result['status'] = 'success_http'
                print(f"   ✓ Lyckades med HTTP!")
            else:
                result['status'] = 'ssl_error_http_failed'
        except Exception:
            result['status'] = 'ssl_error'

    except requests.exceptions.Timeout:
        print(f"   ✗ Timeout efter {HTTP_TIMEOUT}s")
        result['status'] = 'timeout'

    except requests.exceptions.ConnectionError:
        print(f"   ✗ Anslutningsfel")
        result['status'] = 'connection_error'

    except Exception as e:
        print(f"   ✗ Fel: {type(e).__name__}")
        result['status'] = f'error_{type(e).__name__}'

    return result


def main():
    parser = argparse.ArgumentParser(description='Skrapa text från företagshemsidor')
    parser.add_argument('--db', default='databases/ai_companies.db', help='Sökväg till databas')
    parser.add_argument('--limit', type=int, help='Begränsa antal företag att skrapa (för test)')
    parser.add_argument('--missing-only', action='store_true', help='Bara företag utan description')
    parser.add_argument('--output', default='results/scraped_websites.csv', help='Output CSV-fil')
    parser.add_argument('--delay', type=float, default=1.0, help='Fördröjning mellan requests (sekunder)')
    args = parser.parse_args()

    # Skapa results-mapp om den inte finns
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🕷️  WEB SCRAPER - FÖRETAGSHEMSIDOR")
    print("=" * 70)

    # Anslut till databas
    print(f"\n📂 Läser från databas: {args.db}")
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    # Bygg query
    if args.missing_only:
        query = """
            SELECT id, name, website, type
            FROM companies
            WHERE website IS NOT NULL
            AND website != ''
            AND (description IS NULL OR description = '')
            ORDER BY id
        """
        print("🎯 Filtrerar: Bara företag utan description")
    else:
        query = """
            SELECT id, name, website, type
            FROM companies
            WHERE website IS NOT NULL
            AND website != ''
            ORDER BY id
        """
        print("🎯 Skrapar: Alla företag med hemsida")

    if args.limit:
        query += f" LIMIT {args.limit}"

    cursor.execute(query)
    companies = cursor.fetchall()

    print(f"✓ Hittade {len(companies)} företag att skrapa")

    if args.limit:
        print(f"⚠ TESTLÄGE: Begränsat till {args.limit} företag")

    print(f"⏱️  Fördröjning mellan requests: {args.delay}s")

    # Skrapa hemsidor
    results = []
    success_count = 0

    for i, (company_id, name, website, company_type) in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}] " + "=" * 60)
        print(f"ID: {company_id} | {name}")
        print(f"Typ: {company_type} | Website: {website}")

        scrape_result = scrape_website(website, name)

        results.append({
            'id': company_id,
            'name': name,
            'website': website,
            'type': company_type,
            'scraped_text': scrape_result['scraped_text'],
            'meta_description': scrape_result['meta_description'] or '',
            'status': scrape_result['status'],
            'status_code': scrape_result['status_code'] or ''
        })

        if scrape_result['status'] in ['success', 'success_http']:
            success_count += 1

        # Vänta lite mellan requests för att vara artig
        if i < len(companies):
            time.sleep(args.delay)

    # Exportera resultat
    print("\n" + "=" * 70)
    print("📊 EXPORTERAR RESULTAT")
    print("=" * 70)

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'name', 'website', 'type', 'scraped_text', 'meta_description', 'status', 'status_code']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # Statistik
    failed = len(results) - success_count
    success_rate = (success_count / len(results) * 100) if results else 0

    print(f"\n✅ Exporterat till: {args.output}")
    print(f"\n📈 RESULTAT:")
    print(f"   ✓ Lyckade skrapningar: {success_count}")
    print(f"   ✗ Misslyckade: {failed}")
    print(f"   📊 Total: {len(results)}")
    print(f"   🎯 Framgångsgrad: {success_rate:.1f}%")

    # Status breakdown
    status_counts = {}
    for result in results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    if len(status_counts) > 1:
        print(f"\n📋 STATUS BREAKDOWN:")
        for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
            print(f"   {status}: {count}")

    conn.close()

    print("\n" + "=" * 70)
    print("✓ KLART!")
    print("=" * 70)
    print(f"\n💡 Nästa steg: Ladda upp {args.output} och kör generate_descriptions.py")


if __name__ == '__main__':
    main()

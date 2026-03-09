import argparse
import json
import os
import random
import sys
import time
from typing import Optional

# Import requests from curl_cffi instead of the standard requests library
from curl_cffi import requests
from bs4 import BeautifulSoup

BASE_URL = "https://cardrush.media/onepiece/buying_prices?displayMode=リスト&limit=10000&name=&rarity=&model_number=&amount=&page=1&sort%5Bkey%5D=amount&sort%5Border%5D=desc&associations%5B%5D=ocha_product&to_json_option%5Bexcept%5D%5B%5D=original_image_source&to_json_option%5Bexcept%5D%5B%5D=created_at&to_json_option%5Binclude%5D%5Bocha_product%5D%5Bonly%5D%5B%5D=id&to_json_option%5Binclude%5D%5Bocha_product%5D%5Bmethods%5D%5B%5D=image_source&display_category%5B%5D=最新弾&display_category%5B%5D=通常弾"

def build_human_like_headers() -> dict[str, str]:
    # Use exact headers that match Chrome 124 behavior
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1"
    }

def parse_price_table_from_html(html_text: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html_text, "html.parser")
    rows = soup.select("table.PriceTable tbody tr")
    parsed_rows: list[dict[str, str]] = []

    for row in rows:
        name_cell = row.select_one("td.name")
        rarity_cell = row.select_one("td.rarity")
        model_number_cell = row.select_one("td.model_number")
        amount_cell = row.select_one("td.amount")

        if not (name_cell and rarity_cell and model_number_cell and amount_cell):
            continue

        parsed_rows.append(
            {
                "name": name_cell.get_text(strip=True),
                "rarity": rarity_cell.get_text(strip=True),
                "model_number": model_number_cell.get_text(strip=True),
                "amount": amount_cell.get_text(strip=True),
            }
        )
    return parsed_rows

class AccessBlockedError(RuntimeError):
    pass

def scrape_initial_table(
    base_url: str,
    timeout: int,
    wait_seconds: float,
) -> list[dict[str, str]]:
    
    # Use impersonate="chrome124" to generate the correct TLS fingerprint and HTTP/2 settings
    session = requests.Session(impersonate="chrome124")
    headers = build_human_like_headers()
    session.headers.update(headers)
    print(f"Using User-Agent: {headers['User-Agent']}")

    homepage_url = "https://cardrush.media/"
    try:
        # Hitting the homepage first helps establish session cookies naturally
        homepage_response = session.get(homepage_url, timeout=timeout)
        print(
            "Prefetch homepage status="
            f"{homepage_response.status_code} "
            f"server={homepage_response.headers.get('server', 'unknown')} "
        )
    except Exception as exc:
        raise AccessBlockedError(f"Connection failed: {exc}") from exc

    try:
        response = session.get(base_url, timeout=timeout)
    except Exception as exc:
        raise AccessBlockedError(f"Connection failed: {exc}") from exc

    print(f"Fetch status={response.status_code}")

    if response.status_code == 403:
        snippet = response.text[:400].replace("\n", " ")
        raise AccessBlockedError(
            f"Cardrush returned 403 Forbidden. snippet={snippet}"
        )
        
    response.raise_for_status()
    
    if wait_seconds > 0:
        print(f"Waiting {wait_seconds} seconds before parsing response...")
        time.sleep(wait_seconds)
        
    return parse_price_table_from_html(response.text)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape initial Cardrush One Piece buying prices table")
    parser.add_argument("--output", default="one_piece_scripts/cardrush_buying_prices.json")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--wait-seconds", type=float, default=2, help="Seconds to wait after fetch")
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        rows = scrape_initial_table(args.base_url, args.timeout, args.wait_seconds)
    except AccessBlockedError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(3) from exc

    with open(args.output, "w", encoding="utf-8") as file_obj:
        json.dump(rows, file_obj, ensure_ascii=False, indent=2)

    print(f"Saved {len(rows)} rows to {args.output}")
    

if __name__ == "__main__":
    main()

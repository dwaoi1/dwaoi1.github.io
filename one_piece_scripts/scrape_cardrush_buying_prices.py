import argparse
import json
import os
import sys
import time
from datetime import datetime
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo
from typing import Optional

from curl_cffi import requests
from bs4 import BeautifulSoup

# Cardrush uses Next.js, and the data is embedded in a __NEXT_DATA__ script tag.
# Using displayMode=リスト&limit=10000 ensures we get all prices in one go.
BASE_URL = "https://cardrush.media/onepiece/buying_prices?displayMode=リスト&limit=10000"

def get_default_output_path() -> str:
    """Generate a dated output path based on Asia/Tokyo time."""
    tz = zoneinfo.ZoneInfo("Asia/Tokyo")
    now = datetime.now(tz)
    month_year = now.strftime("%b %Y") # e.g., "Apr 2026"
    day_file = now.strftime("%Y-%m-%d.json") # e.g., "2026-04-01.json"
    return os.path.join("one_piece_scripts", "cardrush_buying_prices", month_year, day_file)

def build_human_like_headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

def scrape_cardrush_data(url: str, timeout: int) -> list[dict]:
    # Use impersonate to bypass potential TLS fingerprinting if needed
    # If curl_cffi is missing in some environments, fallback to requests
    try:
        from curl_cffi import requests as c_requests
        session = c_requests.Session(impersonate="chrome124")
    except ImportError:
        import requests as c_requests
        session = c_requests.Session()

    headers = build_human_like_headers()
    session.headers.update(headers)
    
    # Hit homepage first for cookies
    session.get("https://cardrush.media/", timeout=timeout)
    
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        raise RuntimeError("Could not find __NEXT_DATA__ script tag")
        
    data = json.loads(script.string)
    # The buying prices are typically in props.pageProps.buyingPrices
    buying_prices = data.get("props", {}).get("pageProps", {}).get("buyingPrices", [])
    
    results = []
    for bp in buying_prices:
        # Extract the fields we need
        ocha_product = bp.get("ocha_product", {})
        
        name = bp.get("name", "")
        extra = bp.get("extra_difference")
        if extra:
            name = f"{name}({extra})"

        amount = bp.get("amount")
        amount_str = ""
        if amount is not None:
            try:
                amount_str = f"¥{int(amount):,}"
            except (ValueError, TypeError):
                amount_str = str(amount)

        results.append({
            "name": name,
            "rarity": bp.get("rarity", ""),
            "model_number": bp.get("model_number", ""),
            "amount": amount_str,
            "image": ocha_product.get("image_source", "")
        })
    return results

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Cardrush One Piece buying prices with images")
    parser.add_argument("--output", default=get_default_output_path())
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        rows = scrape_cardrush_data(BASE_URL, args.timeout)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(rows)} rows to {args.output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

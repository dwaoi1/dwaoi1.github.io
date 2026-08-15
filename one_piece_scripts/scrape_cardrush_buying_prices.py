import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo
from typing import Optional

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

# Cardrush uses Next.js, and the data is embedded in a __NEXT_DATA__ script tag.
# Using displayMode=リスト&limit=10000 ensures we get all prices in one go.
BASE_URL = "https://cardrush.media/onepiece/buying_prices?displayMode=リスト&limit=10000"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_default_output_path() -> str:
    """Generate a dated output path based on Asia/Tokyo time."""
    tz = zoneinfo.ZoneInfo("Asia/Tokyo")
    now = datetime.now(tz)
    year_month = now.strftime("%Y-%m") # e.g., "2026-04"
    day_file = now.strftime("%Y-%m-%d.json") # e.g., "2026-04-01.json"
    return os.path.join(SCRIPT_DIR, "cardrush_buying_prices", year_month, day_file)

def build_human_like_headers() -> dict[str, str]:
    # curl_cffi's impersonation sets User-Agent, Accept, Accept-Language,
    # and Sec-CH-UA headers. Only add headers it does not set automatically.
    return {
        "Referer": "https://cardrush.media/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

def _do_scrape(url: str, timeout: int) -> list[dict]:
    proxies = None
    proxy_url = os.environ.get("PROXY_URL")
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

    session = cffi_requests.Session(impersonate="chrome142", proxies=proxies)
    session.headers.update(build_human_like_headers())

    # Visit homepage first to establish cookies
    home_resp = session.get("https://cardrush.media/", timeout=timeout)
    if home_resp.status_code == 403:
        raise RuntimeError("Homepage blocked (403)")

    # Small human-like pause before the data request
    time.sleep(1 + random.uniform(0.5, 1.5))

    # Fetch the actual data page
    response = session.get(url, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        raise RuntimeError("Could not find __NEXT_DATA__ script tag")

    data = json.loads(script.string)
    buying_prices = data.get("props", {}).get("pageProps", {}).get("buyingPrices", [])

    results = []
    for bp in buying_prices:
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


def scrape_cardrush_data(url: str, timeout: int, max_retries: int = 3) -> list[dict]:
    last_error = None
    for attempt in range(max_retries):
        try:
            return _do_scrape(url, timeout)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait:.1f}s...", file=sys.stderr)
                time.sleep(wait)
    raise last_error

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

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
from typing import Callable, Optional
from urllib.parse import parse_qs, urljoin, urlparse

from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup

# Cardrush uses Next.js, and the data is embedded in a __NEXT_DATA__ script tag.
# The listing is capped at 1000 rows per page, so we follow the pagination
# "next" arrow's href until it stops advancing the page.
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

def _build_session(timeout: int) -> cffi_requests.Session:
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
    return session

def _fetch_page(session: cffi_requests.Session, url: str, timeout: int):
    # Small human-like pause before each data request
    time.sleep(1 + random.uniform(0.5, 1.5))

    response = session.get(url, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        raise RuntimeError("Could not find __NEXT_DATA__ script tag")

    data = json.loads(script.string)
    page_props = data.get("props", {}).get("pageProps", {})
    return soup, page_props

def _to_row(bp: dict) -> dict:
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

    return {
        "name": name,
        "rarity": bp.get("rarity", ""),
        "model_number": bp.get("model_number", ""),
        "amount": amount_str,
        "image": ocha_product.get("image_source", "")
    }

def _page_number(url: str) -> Optional[int]:
    values = parse_qs(urlparse(url).query).get("page")
    if not values:
        return None
    try:
        return int(values[0])
    except ValueError:
        return None

def _find_next_url(soup: BeautifulSoup, current_page: int) -> Optional[str]:
    """Return the href of the "next page" arrow, or None when it stops advancing.

    The pagination block contains two arrow links (prev/next) plus page-number
    links. The arrows wrap a KunojiArrow image instead of a page number, and a
    disabled arrow (prev on page 1, next on the last page) has no page param.
    """
    for anchor in soup.select("div.Pagination a"):
        if "KunojiArrow" not in str(anchor):
            continue
        href = anchor.get("href")
        if not href:
            continue
        next_url = urljoin(BASE_URL, href)
        next_page = _page_number(next_url)
        if next_page is None or next_page <= current_page:
            continue
        return next_url
    return None

def _retry(fn: Callable[[], object], max_retries: int, what: str):
    last_error = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"Attempt {attempt + 1} failed ({what}): {e}. Retrying in {wait:.1f}s...", file=sys.stderr)
                time.sleep(wait)
    raise last_error

def scrape_cardrush_data(url: str, timeout: int, max_retries: int = 3, max_pages: int = 20) -> list[dict]:
    session = _retry(lambda: _build_session(timeout), max_retries, "session setup")

    rows: list[dict] = []
    seen_ids: set = set()
    current_url = url
    current_page = 1

    for _ in range(max_pages):
        soup, page_props = _retry(
            lambda: _fetch_page(session, current_url, timeout),
            max_retries,
            f"page {current_page}",
        )
        buying_prices = page_props.get("buyingPrices", [])
        last_page = page_props.get("lastPage")

        new_rows = 0
        for bp in buying_prices:
            product_id = bp.get("id")
            if product_id is not None:
                if product_id in seen_ids:
                    continue
                seen_ids.add(product_id)
            rows.append(_to_row(bp))
            new_rows += 1

        page_label = f"{current_page}/{last_page}" if last_page else str(current_page)
        print(f"Page {page_label}: {len(buying_prices)} fetched, {new_rows} new, {len(rows)} total")

        if last_page and current_page >= last_page:
            break
        if new_rows == 0:
            break

        next_url = _find_next_url(soup, current_page)
        if not next_url:
            break

        current_url = next_url
        current_page = _page_number(next_url) or current_page + 1
    else:
        print(f"Stopped at max_pages={max_pages} before the listing ran out of pages", file=sys.stderr)

    return rows

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

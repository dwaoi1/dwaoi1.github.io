import argparse
import json
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://cardrush.media/onepiece/buying_prices"
DEFAULT_IMPERSONATE_BROWSER = "chrome124"


def find_json_like_list(value: Any) -> list[dict[str, Any]] | None:
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            first = value[0]
            keys = set(first.keys())
            if {"name", "amount"}.issubset(keys) or {"model_number", "amount"}.issubset(keys):
                return value
        for item in value:
            found = find_json_like_list(item)
            if found is not None:
                return found
    elif isinstance(value, dict):
        for nested in value.values():
            found = find_json_like_list(nested)
            if found is not None:
                return found
    return None


def parse_price_table_from_html(html_text: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html_text, "html.parser")
    rows = soup.select("table.PriceTable tbody tr")
    parsed_rows: list[dict[str, Any]] = []

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


def parse_payload(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if not text:
        return []

    table_rows = parse_price_table_from_html(text)
    if table_rows:
        return table_rows

    if text[0] in "[{":
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            found = find_json_like_list(parsed)
            return found or []

    soup = BeautifulSoup(text, "html.parser")
    next_data = soup.select_one("script#__NEXT_DATA__")
    if next_data and next_data.string:
        parsed = json.loads(next_data.string)
        found = find_json_like_list(parsed)
        if found is not None:
            return found

    return []


def discover_max_page(html: str, current_url: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    max_page = 1
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "/onepiece/buying_prices" not in href:
            continue
        parsed = urlparse(urljoin(current_url, href))
        query = parse_qs(parsed.query)
        if "page" in query:
            try:
                max_page = max(max_page, int(query["page"][0]))
            except (ValueError, TypeError, IndexError):
                continue
    return max_page


def request_page(session: requests.Session, url: str, timeout: int, impersonate: str) -> requests.Response:
    try:
        response = session.get(url, timeout=timeout, impersonate=impersonate)
    except requests.exceptions.ProxyError as exc:
        raise RuntimeError(
            "Network proxy blocked access before reaching Cardrush (CONNECT tunnel failed with 403). "
            "This is a runner/network restriction, not a parser bug."
        ) from exc

    if response.status_code == 403:
        snippet = response.text[:600].replace("\n", " ")
        raise RuntimeError(
            "Cardrush returned 403 Forbidden. This usually means bot protection blocked the runner IP/fingerprint. "
            f"Try a different --impersonate value. URL={url} body_snippet={snippet}"
        )
    response.raise_for_status()
    return response


def scrape(base_url: str, delay_seconds: float, timeout: int, impersonate: str) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": "https://cardrush.media/",
            "Origin": "https://cardrush.media",
        }
    )

    base_params = {
        "displayMode": "リスト",
        "limit": "100",
        "name": "",
        "rarity": "",
        "model_number": "",
        "amount": "",
        "sort[key]": "amount",
        "sort[order]": "desc",
        "associations[]": "ocha_product",
        "to_json_option[except][]": ["original_image_source", "created_at"],
        "to_json_option[include][ocha_product][only][]": "id",
        "to_json_option[include][ocha_product][methods][]": "image_source",
        "display_category[]": ["最新弾", "通常弾"],
    }

    query = urlencode(base_params, doseq=True)
    first_url = f"{base_url}?{query}"
    first_response = request_page(session, first_url, timeout, impersonate)

    max_page = discover_max_page(first_response.text, first_response.url)

    all_rows: list[dict[str, Any]] = []
    for page in range(1, max_page + 1):
        page_params = dict(base_params)
        page_params["page"] = str(page)
        page_query = urlencode(page_params, doseq=True)
        page_url = f"{base_url}?{page_query}"

        response = request_page(session, page_url, timeout, impersonate)
        rows = parse_payload(response.text)

        for row in rows:
            row["source_page"] = page
        all_rows.extend(rows)

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return all_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Cardrush One Piece buying prices pages")
    parser.add_argument("--output", default="one_piece_scripts/cardrush_buying_prices.json")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--delay", type=float, default=0.6)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--impersonate", default=DEFAULT_IMPERSONATE_BROWSER)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = scrape(args.base_url, args.delay, args.timeout, args.impersonate)

    with open(args.output, "w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, ensure_ascii=False, indent=2)

    print(f"Saved {len(data)} rows to {args.output}")


if __name__ == "__main__":
    main()

import argparse
import json
import random
import sys
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://cardrush.media/onepiece/buying_prices"
DEFAULT_IMPERSONATE_BROWSER = "chrome124"
DEFAULT_IMPERSONATE_CANDIDATES = [
    "chrome124",
    "chrome123",
    "chrome120",
    "safari17_0",
    "edge101",
]


class AccessBlockedError(RuntimeError):
    pass


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


def warm_up_session(session: requests.Session, impersonate: str, timeout: int) -> None:
    warmup_urls = [
        "https://cardrush.media/",
        "https://cardrush.media/onepiece",
    ]
    for warmup_url in warmup_urls:
        try:
            session.get(warmup_url, timeout=timeout, impersonate=impersonate)
            time.sleep(random.uniform(0.2, 0.6))
        except Exception:
            return


def request_page(
    session: requests.Session,
    url: str,
    timeout: int,
    impersonates: list[str],
    retries_per_impersonate: int,
    retry_backoff_seconds: float,
) -> tuple[requests.Response, str]:
    last_block_reason: str | None = None

    for impersonate in impersonates:
        for attempt in range(1, retries_per_impersonate + 1):
            try:
                response = session.get(url, timeout=timeout, impersonate=impersonate)
            except requests.exceptions.ProxyError as exc:
                last_block_reason = (
                    "Network proxy blocked access before reaching Cardrush "
                    "(CONNECT tunnel failed with 403). This is a runner/network restriction."
                )
                if attempt < retries_per_impersonate:
                    time.sleep(retry_backoff_seconds * attempt)
                    continue
                break
            except Exception as exc:
                if attempt < retries_per_impersonate:
                    time.sleep(retry_backoff_seconds * attempt)
                    continue
                raise RuntimeError(f"Unexpected request failure for {url}: {exc}") from exc

            if response.status_code == 403:
                snippet = response.text[:400].replace("\n", " ")
                last_block_reason = (
                    "Cardrush returned 403 Forbidden; likely anti-bot/IP block. "
                    f"impersonate={impersonate} attempt={attempt} url={url} body_snippet={snippet}"
                )
                if attempt < retries_per_impersonate:
                    time.sleep(retry_backoff_seconds * attempt)
                    continue
                break

            response.raise_for_status()
            return response, impersonate

    raise AccessBlockedError(last_block_reason or "Access blocked for unknown reason.")


def scrape(
    base_url: str,
    delay_seconds: float,
    timeout: int,
    impersonates: list[str],
    retries_per_impersonate: int,
    retry_backoff_seconds: float,
) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://cardrush.media/",
            "Origin": "https://cardrush.media",
        }
    )

    warm_up_session(session, impersonates[0], timeout)

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
    first_response, first_impersonate = request_page(
        session,
        first_url,
        timeout,
        impersonates,
        retries_per_impersonate,
        retry_backoff_seconds,
    )
    print(f"Fetched first page with impersonate={first_impersonate}")

    max_page = discover_max_page(first_response.text, first_response.url)

    all_rows: list[dict[str, Any]] = []
    for page in range(1, max_page + 1):
        page_params = dict(base_params)
        page_params["page"] = str(page)
        page_query = urlencode(page_params, doseq=True)
        page_url = f"{base_url}?{page_query}"

        response, used_impersonate = request_page(
            session,
            page_url,
            timeout,
            impersonates,
            retries_per_impersonate,
            retry_backoff_seconds,
        )
        rows = parse_payload(response.text)

        for row in rows:
            row["source_page"] = page
            row["impersonate_profile"] = used_impersonate
        all_rows.extend(rows)

        if delay_seconds > 0:
            time.sleep(delay_seconds + random.uniform(0.0, 0.35))

    return all_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Cardrush One Piece buying prices pages")
    parser.add_argument("--output", default="one_piece_scripts/cardrush_buying_prices.json")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--delay", type=float, default=0.8)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--impersonate", default=DEFAULT_IMPERSONATE_BROWSER)
    parser.add_argument(
        "--impersonate-list",
        default=",".join(DEFAULT_IMPERSONATE_CANDIDATES),
        help="Comma-separated impersonation profiles to try in order",
    )
    parser.add_argument("--retries-per-impersonate", type=int, default=2)
    parser.add_argument("--retry-backoff", type=float, default=1.2)
    parser.add_argument("--skip-on-block", action="store_true", help="Exit successfully when access is blocked (keeps previous data)")
    return parser.parse_args()


def resolve_impersonates(args: argparse.Namespace) -> list[str]:
    raw = [x.strip() for x in args.impersonate_list.split(",") if x.strip()]
    if args.impersonate and args.impersonate not in raw:
        raw.insert(0, args.impersonate)
    return raw or [DEFAULT_IMPERSONATE_BROWSER]


def main() -> None:
    args = parse_args()
    impersonates = resolve_impersonates(args)

    try:
        data = scrape(
            args.base_url,
            args.delay,
            args.timeout,
            impersonates,
            args.retries_per_impersonate,
            args.retry_backoff,
        )
    except AccessBlockedError as exc:
        if args.skip_on_block:
            print(f"::warning::{exc}")
            print("Access blocked. Skipping scrape and leaving existing output unchanged.")
            return
        print(str(exc), file=sys.stderr)
        raise

    with open(args.output, "w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, ensure_ascii=False, indent=2)

    print(f"Saved {len(data)} rows to {args.output}")


if __name__ == "__main__":
    main()

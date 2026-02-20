import argparse
import json
import os
import sys
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://cardrush.media/onepiece/buying_prices?displayMode=リスト&limit=10000&name=&rarity=&model_number=&amount=&page=1&sort%5Bkey%5D=amount&sort%5Border%5D=desc&associations%5B%5D=ocha_product&to_json_option%5Bexcept%5D%5B%5D=original_image_source&to_json_option%5Bexcept%5D%5B%5D=created_at&to_json_option%5Binclude%5D%5Bocha_product%5D%5Bonly%5D%5B%5D=id&to_json_option%5Binclude%5D%5Bocha_product%5D%5Bmethods%5D%5B%5D=image_source&display_category%5B%5D=最新弾&display_category%5B%5D=通常弾"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


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


def scrape_initial_table(base_url: str, timeout: int, wait_seconds: float) -> list[dict[str, str]]:
    try:
        response = requests.get(
            base_url,
            timeout=timeout,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            },
        )
    except requests.exceptions.ProxyError as exc:
        raise AccessBlockedError(
            "Network proxy blocked access before reaching Cardrush (CONNECT tunnel failed with 403)."
        ) from exc
    if response.status_code == 403:
        snippet = response.text[:400].replace("\n", " ")
        raise AccessBlockedError(
            "Cardrush returned 403 Forbidden for initial page. "
            f"url={base_url} body_snippet={snippet}"
        )
    response.raise_for_status()
    if wait_seconds > 0:
        print(f"Waiting {wait_seconds} seconds before parsing response...")
        time.sleep(wait_seconds)
    return parse_price_table_from_html(response.text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape only the initial Cardrush One Piece buying prices table")
    parser.add_argument("--output", default="one_piece_scripts/cardrush_buying_prices.json")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--wait-seconds", type=float, default=30, help="Seconds to wait after fetch before parsing")
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
    preview_count = min(5, len(rows))
    if preview_count:
        print(f"Previewing first {preview_count} row(s):")
        for idx, row in enumerate(rows[:preview_count], start=1):
            print(
                f"{idx}. name={row['name']} | rarity={row['rarity']} | "
                f"model_number={row['model_number']} | amount={row['amount']}"
            )


if __name__ == "__main__":
    main()

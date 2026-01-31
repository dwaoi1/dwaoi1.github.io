import argparse
import glob
import json
import os
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ASIA_EN_SERIES_IDS = [
    '556302', '556301', '556203', '556202', '556201',
    '556114', '556113', '556112', '556111', '556110',
    '556109', '556108', '556107', '556106', '556105',
    '556104', '556103', '556102', '556101', '556029',
    '556028', '556027', '556026', '556025', '556024',
    '556023', '556022', '556021', '556020', '556019',
    '556018', '556017', '556016', '556015', '556014',
    '556013', '556012', '556011', '556010', '556009',
    '556008', '556007', '556006', '556005', '556004',
    '556003', '556002', '556001', '556701', '556901',
    '556801',
]

JAPAN_SERIES_IDS = [
    '550114',
]

ASIA_EN_URL = "https://asia-en.onepiece-cardgame.com/cardlist/"
JAPAN_URL = "https://www.onepiece-cardgame.com/cardlist/"
OUTPUT_DIR = "html_files"
USE_LIVE_SERIES_IDS = True
USE_LIVE_JAPAN_SERIES_IDS = True
OUTPUT_JSON = "../one_piece_app/src/data.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


def fetch_series_ids(source_url):
    response = requests.get(source_url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    series_select = soup.find('select', {'name': 'series'})
    if not series_select:
        return []
    ids = []
    for option in series_select.find_all('option'):
        value = option.get('value')
        if value and value.isdigit():
            ids.append(value)
    return list(dict.fromkeys(ids))

def scrape_card_data(html_content, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    cards_data = []

    card_elements = soup.find_all('dl', class_='modalCol')

    for card in card_elements:
        try:
            name_div = card.select_one('dt .cardName')
            character_name = name_div.get_text(strip=True) if name_div else "Unknown"

            color_div = card.select_one('.backCol .color')
            color = "Unknown"
            if color_div:
                color_text = color_div.get_text(strip=True)
                if color_text.startswith("Color"):
                    color = color_text[5:]
                else:
                    color = color_text

            img_tag = card.select_one('.frontCol img')
            picture_url = ""
            if img_tag:
                if 'data-src' in img_tag.attrs:
                    picture_url = img_tag['data-src']
                elif 'src' in img_tag.attrs:
                    picture_url = img_tag['src']

            if picture_url.startswith('..'):
                picture_url = picture_url.replace('..', base_url)
            elif picture_url.startswith('/'):
                picture_url = base_url + picture_url

            cards_data.append({
                "Character": character_name,
                "Color": color,
                "Picture": picture_url,
            })

        except Exception as exc:
            print(f"Error parsing a card: {exc}")
            continue

    return cards_data


def deduplicate_by_picture(cards):
    unique_cards = []
    seen_pictures = set()
    for card in cards:
        picture = card.get("Picture", "")
        picture_key = ""
        if picture:
            parsed_url = urlparse(picture)
            picture_key = os.path.basename(parsed_url.path)
        if picture_key and re.search(r"_r\\d+\\.", picture_key):
            continue
        if picture_key and picture_key in seen_pictures:
            continue
        seen_pictures.add(picture_key)
        unique_cards.append(card)
    return unique_cards


def parse_downloaded_html(output_dir):
    html_files = glob.glob(os.path.join(output_dir, "*.html"))
    if not html_files:
        print(f"No HTML files found to parse in {output_dir}.")
        return

    all_cards = []
    print(f"Parsing {len(html_files)} HTML files...")

    for file_path in html_files:
        print(f"Reading {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        filename = os.path.basename(file_path)
        if filename.startswith("japan_"):
            base_url = "https://www.onepiece-cardgame.com"
        else:
            base_url = "https://asia-en.onepiece-cardgame.com"
        data = scrape_card_data(content, base_url)
        all_cards.extend(data)
        print(f"Extracted {len(data)} cards from {file_path}")

    all_cards = deduplicate_by_picture(all_cards)

    try:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(all_cards, f, indent=2, ensure_ascii=False)
        print(f"Done. Saved {len(all_cards)} cards to {OUTPUT_JSON}")
    except FileNotFoundError:
        fallback_file = "one_piece_cards.json"
        print(f"Could not find {OUTPUT_JSON}. Saving to {fallback_file} instead.")
        with open(fallback_file, 'w', encoding='utf-8') as f:
            json.dump(all_cards, f, indent=2, ensure_ascii=False)
        print(f"Done. Saved {len(all_cards)} cards to {fallback_file}")

def download_series():
    output_dir = OUTPUT_DIR
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    sources = [
        {
            "name": "asia_en",
            "url": ASIA_EN_URL,
            "series_ids": ASIA_EN_SERIES_IDS,
            "use_live_series_ids": USE_LIVE_SERIES_IDS,
        },
        {
            "name": "japan",
            "url": JAPAN_URL,
            "series_ids": JAPAN_SERIES_IDS,
            "use_live_series_ids": USE_LIVE_JAPAN_SERIES_IDS,
        },
    ]

    total_series = 0
    for source in sources:
        series_ids = source["series_ids"]
        if source["use_live_series_ids"]:
            try:
                live_series_ids = fetch_series_ids(source["url"])
                if live_series_ids:
                    series_ids = live_series_ids
                else:
                    print("Fetched 0 series IDs; falling back to static list.")
            except Exception as exc:
                print(f"Failed to fetch series IDs ({exc}); falling back to static list.")
        source["resolved_series_ids"] = series_ids
        total_series += len(series_ids)

    print(f"Starting download of {total_series} card sets...")

    for source in sources:
        for s_id in source["resolved_series_ids"]:
            output_path = os.path.join(output_dir, f"{source['name']}_series_{s_id}.html")

            # Skip if already downloaded
            if os.path.exists(output_path):
                print(f"Skipping {source['name']} {s_id} (already exists)")
                continue

            print(f"Downloading {source['name']} Series ID: {s_id}...")

            try:
                payload = {'series': s_id, 'reprintsFlag': 'off'}
                response = requests.post(
                    source["url"],
                    headers={"User-Agent": USER_AGENT},
                    data=payload,
                    timeout=30,
                )
                if response.status_code == 200:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"  -> Saved to {output_path}")
                else:
                    print(f"  -> Failed: Status {response.status_code}")
            except Exception as e:
                print(f"  -> Error: {e}")

            # Be nice to the server
            time.sleep(1)

def parse_args():
    parser = argparse.ArgumentParser(description="Download and parse One Piece card data.")
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="Directory to store downloaded HTML files.",
    )
    parser.add_argument(
        "--output-json",
        default=OUTPUT_JSON,
        help="Path to write parsed JSON data.",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    OUTPUT_DIR = args.output_dir
    OUTPUT_JSON = args.output_json
    download_series()
    parse_downloaded_html(OUTPUT_DIR)

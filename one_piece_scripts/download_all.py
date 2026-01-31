import argparse
import glob
import json
import os
import time

import requests
from bs4 import BeautifulSoup

SERIES_IDS = [
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

URL = "https://asia-en.onepiece-cardgame.com/cardlist/"
OUTPUT_DIR = "html_files"
USE_LIVE_SERIES_IDS = True
OUTPUT_JSON = "../one_piece_app/src/data.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


def fetch_series_ids():
    response = requests.get(URL, headers={"User-Agent": USER_AGENT}, timeout=30)
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

def scrape_card_data(html_content):
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
                picture_url = picture_url.replace('..', 'https://asia-en.onepiece-cardgame.com')
            elif picture_url.startswith('/'):
                picture_url = 'https://asia-en.onepiece-cardgame.com' + picture_url

            cards_data.append({
                "Character": character_name,
                "Color": color,
                "Picture": picture_url,
            })

        except Exception as exc:
            print(f"Error parsing a card: {exc}")
            continue

    return cards_data


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
        data = scrape_card_data(content)
        all_cards.extend(data)
        print(f"Extracted {len(data)} cards from {file_path}")

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
        
    series_ids = SERIES_IDS
    if USE_LIVE_SERIES_IDS:
        try:
            live_series_ids = fetch_series_ids()
            if live_series_ids:
                series_ids = live_series_ids
            else:
                print("Fetched 0 series IDs; falling back to static list.")
        except Exception as exc:
            print(f"Failed to fetch series IDs ({exc}); falling back to static list.")

    print(f"Starting download of {len(series_ids)} card sets...")
    
    for s_id in series_ids:
        output_path = os.path.join(output_dir, f"series_{s_id}.html")
        
        # Skip if already downloaded
        if os.path.exists(output_path):
            print(f"Skipping {s_id} (already exists)")
            continue
            
        print(f"Downloading Series ID: {s_id}...")
        
        try:
            payload = {'series': s_id, 'reprintsFlag': 'off'}
            response = requests.post(
                URL,
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

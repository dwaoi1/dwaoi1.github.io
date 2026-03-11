#!/usr/bin/env python3
"""
Build compiled price data from raw Cardrush daily JSON files.

Reads:
  one_piece_scripts/cardrush_buying_prices/**/*.json   (daily price scrapes)
  one_piece_scripts/one_piece_cards.json               (card list with names and rarities)

Writes:
  one_piece_app/public/cardrush_price_history.json  -- price history per card (committed by scrape workflow)
  one_piece_scripts/unmatched_prices.json        -- diagnostic / rarity breakdown (copied to public/ by deploy.yml)
"""

import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
PRICE_DIR = os.path.join(SCRIPT_DIR, 'cardrush_buying_prices')
CARDS_JSON = os.path.join(SCRIPT_DIR, 'one_piece_cards.json')
PRICE_DATA_OUT = os.path.join(REPO_ROOT, 'one_piece_app', 'public', 'cardrush_price_history.json')
UNMATCHED_OUT = os.path.join(SCRIPT_DIR, 'unmatched_prices.json')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_amount(amount_str):
    if not amount_str:
        return None
    cleaned = re.sub(r'[¥,]', '', amount_str)
    try:
        return float(cleaned)
    except ValueError:
        return None


def get_card_code(url):
    if not url:
        return ''
    m = re.search(r'/([A-Z]+\d{2,}-\d{3})', url)
    return m.group(1) if m else ''


def find_json_files(directory):
    files = []
    for dirpath, _dirs, filenames in os.walk(directory):
        for fn in sorted(filenames):
            if fn.endswith('.json'):
                files.append(os.path.join(dirpath, fn))
    return sorted(files)


def price_group(entries):
    prices = [p for p in (parse_amount(e.get('amount')) for e in entries) if p is not None]
    if not prices:
        return None
    return {'minPrice': min(prices), 'maxPrice': max(prices), 'count': len(entries)}


def series_breakdown(codes):
    counts = {}
    for code in codes:
        m = re.match(r'^([A-Z]+\d*)', code)
        prefix = m.group(1) if m else (code.split('-')[0] if '-' in code else code)
        counts[prefix] = counts.get(prefix, 0) + 1
    return sorted(
        [{'series': s, 'count': c} for s, c in counts.items()],
        key=lambda x: -x['count'],
    )


def rarity_breakdown(codes, code_to_rarities):
    """Group cards-without-prices by their known rarities (a code may have multiple)."""
    counts = {}
    for code in codes:
        rarities = code_to_rarities.get(code, ['Unknown'])
        for rarity in rarities:
            counts[rarity] = counts.get(rarity, 0) + 1
    return sorted(
        [{'rarity': r, 'count': c} for r, c in counts.items()],
        key=lambda x: -x['count'],
    )


# ---------------------------------------------------------------------------
# Price history
# ---------------------------------------------------------------------------

def build_history_by_code(price_files):
    history_by_code = {}
    for file_path in price_files:
        date = os.path.splitext(os.path.basename(file_path))[0]
        try:
            with open(file_path, encoding='utf-8') as f:
                entries = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f'WARNING: Failed to parse {file_path}: {exc}')
            continue
        for entry in entries:
            code = entry.get('model_number', '')
            if not code:
                continue
            history_by_code.setdefault(code, {}).setdefault(date, []).append(entry)
    return history_by_code


def build_price_history(history_by_code):
    price_history = {}
    for code, date_map in history_by_code.items():
        history = []
        for date, entries in date_map.items():
            all_prices = [p for p in (parse_amount(e.get('amount')) for e in entries) if p is not None]
            if not all_prices:
                continue

            # Classify into base / sealed (未開封) / gold-text-only (金文字) / parallel (パラレル).
            # Each entry goes into the first matching category; groups are mutually exclusive.
            sealed_set = frozenset(
                id(e) for e in entries if e.get('name') and '未開封' in e['name']
            )
            sealed = [e for e in entries if id(e) in sealed_set]
            gold_text = [
                e for e in entries
                if id(e) not in sealed_set and e.get('name') and '金文字' in e['name']
            ]
            parallel = [
                e for e in entries
                if id(e) not in sealed_set and e.get('name') and 'パラレル' in e['name']
            ]
            parallel_set = frozenset(id(e) for e in parallel)
            base = [e for e in entries if id(e) not in sealed_set and id(e) not in parallel_set
                    and not (e.get('name') and '金文字' in e['name'])]

            base_group = price_group(base)
            if base_group:
                hist_entry = {
                    'date': date,
                    'minPrice': base_group['minPrice'],
                    'maxPrice': base_group['maxPrice'],
                    'count': base_group['count'],
                }
            else:
                # No pure-base entries: prefer non-parallel prices as fallback so
                # the chart's main line isn't polluted by parallel-only prices.
                non_parallel = [e for e in entries if id(e) not in parallel_set]
                non_parallel_prices = [p for p in (parse_amount(e.get('amount')) for e in non_parallel) if p is not None]
                fallback_prices = non_parallel_prices or all_prices
                hist_entry = {
                    'date': date,
                    'minPrice': min(fallback_prices),
                    'maxPrice': max(fallback_prices),
                    'count': len(non_parallel) if non_parallel_prices else len(entries),
                }

            sealed_group = price_group(sealed)
            gold_group = price_group(gold_text)
            parallel_group = price_group(parallel)
            if sealed_group:
                hist_entry['sealed'] = sealed_group
            if gold_group:
                hist_entry['goldText'] = gold_group
            if parallel_group:
                hist_entry['parallel'] = parallel_group

            history.append(hist_entry)

        history.sort(key=lambda x: x['date'])
        if history:
            price_history[code] = {'history': history}

    return price_history


# ---------------------------------------------------------------------------
# Rarity map (from cards.json)
# ---------------------------------------------------------------------------

def build_rarity_map():
    """Return a map of card_code -> list of unique rarities seen for that code."""
    code_to_rarities = {}
    if not os.path.isfile(CARDS_JSON):
        return code_to_rarities
    try:
        with open(CARDS_JSON, encoding='utf-8') as f:
            cards = json.load(f)
        for card in cards:
            code = get_card_code(card.get('Picture', ''))
            rarity = card.get('Rarity', '')
            if code and rarity:
                seen = code_to_rarities.setdefault(code, [])
                if rarity not in seen:
                    seen.append(rarity)
    except (json.JSONDecodeError, OSError) as exc:
        print(f'WARNING: Failed to build rarity map: {exc}')
    return code_to_rarities


# ---------------------------------------------------------------------------
# Unmatched / diagnostic data
# ---------------------------------------------------------------------------

NAME_PATTERNS = [
    ('パラレル', 'Parallel'),
    ('illust', 'Illust variant'),
    ('未開封', 'Sealed'),
    ('漫画', 'Manga art'),
    ('金文字', 'Gold text'),
    ('CS', 'CS event'),
    ('アニメ', 'Anime art'),
    ('シリアル', 'Serial numbered'),
    ('SP', 'SP variant'),
    ('開封品', 'Opened'),
]


def build_unmatched(history_by_code, price_files, code_to_rarities):
    card_codes = set()
    if os.path.isfile(CARDS_JSON):
        try:
            with open(CARDS_JSON, encoding='utf-8') as f:
                cards = json.load(f)
            for card in cards:
                code = get_card_code(card.get('Picture', ''))
                if code:
                    card_codes.add(code)
        except (json.JSONDecodeError, OSError) as exc:
            print(f'WARNING: Failed to parse {CARDS_JSON}: {exc}')

    all_price_codes = set(history_by_code.keys())

    latest_file = price_files[-1] if price_files else None
    latest_date = os.path.splitext(os.path.basename(latest_file))[0] if latest_file else ''
    latest_by_code = {}
    if latest_file:
        try:
            with open(latest_file, encoding='utf-8') as f:
                latest_entries = json.load(f)
            for entry in latest_entries:
                code = entry.get('model_number', '')
                latest_by_code.setdefault(code, []).append(entry)
        except (json.JSONDecodeError, OSError) as exc:
            print(f'WARNING: Failed to parse latest file {latest_file}: {exc}')

    multiple_prices = [
        {'cardCode': code, 'priceCount': len(entries), 'entries': entries}
        for code, entries in latest_by_code.items()
        if len(entries) > 1
    ]

    pattern_counts = {}
    for item in multiple_prices:
        for entry in item['entries']:
            name = entry.get('name', '')
            for key, label in NAME_PATTERNS:
                if key in name:
                    pattern_counts[label] = pattern_counts.get(label, 0) + 1
                    break

    multi_price_patterns = sorted(
        [{'pattern': p, 'count': c} for p, c in pattern_counts.items()],
        key=lambda x: -x['count'],
    )

    prices_without_cards = sorted(
        [
            {'modelNumber': code, 'latestEntries': latest_by_code.get(code, [])}
            for code in all_price_codes
            if code not in card_codes
        ],
        key=lambda x: x['modelNumber'],
    )

    cards_without_prices = sorted(card_codes - all_price_codes)

    return {
        'asOf': latest_date,
        'multiplePrices': multiple_prices,
        'multiPricePatterns': multi_price_patterns,
        'pricesWithoutCards': prices_without_cards,
        'pricesWithoutCardsBreakdown': series_breakdown([e['modelNumber'] for e in prices_without_cards]),
        'cardsWithoutPrices': cards_without_prices,
        'cardsWithoutPricesBreakdown': series_breakdown(cards_without_prices),
        'cardsWithoutPricesRarityBreakdown': rarity_breakdown(cards_without_prices, code_to_rarities),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    price_files = find_json_files(PRICE_DIR)
    if not price_files:
        print('WARNING: No price files found, skipping price data generation')
        return

    print(f'Processing {len(price_files)} price files...')

    history_by_code = build_history_by_code(price_files)
    price_history = build_price_history(history_by_code)

    with open(PRICE_DATA_OUT, 'w', encoding='utf-8') as f:
        json.dump(price_history, f, ensure_ascii=False)
    print(f'Wrote {PRICE_DATA_OUT} ({len(price_history)} card codes)')

    code_to_rarities = build_rarity_map()
    print(f'Loaded rarity data for {len(code_to_rarities)} card codes')

    unmatched = build_unmatched(history_by_code, price_files, code_to_rarities)
    with open(UNMATCHED_OUT, 'w', encoding='utf-8') as f:
        json.dump(unmatched, f, ensure_ascii=False, indent=2)
    print(f'Wrote {UNMATCHED_OUT}')
    print(f'  Multiple prices: {len(unmatched["multiplePrices"])}')
    print(f'  Prices without cards: {len(unmatched["pricesWithoutCards"])}')
    print(f'  Cards without prices: {len(unmatched["cardsWithoutPrices"])}')


if __name__ == '__main__':
    main()

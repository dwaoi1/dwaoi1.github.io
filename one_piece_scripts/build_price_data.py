#!/usr/bin/env python3
"""
Build compiled price data from raw Cardrush daily JSON files.

Reads:
  one_piece_scripts/cardrush_buying_prices/**/*.json   (daily price scrapes)
  one_piece_scripts/one_piece_cards.json               (card list with names and rarities)
  one_piece_scripts/card_price_overrides.json          (manual image-code → name-pattern mappings;
                                                        also receives auto-generated diagnostic data)

Writes:
  one_piece_app/public/cardrush_price_history.json  -- price history per card (committed by scrape workflow)
  one_piece_scripts/card_price_overrides.json       -- updated in-place: preserves 'mappings' and '_comment',
                                                        overwrites diagnostic sections (multiplePrices, etc.)
                                                        (copied to public/ as unmatched_prices.json by deploy.yml)
"""

import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
PRICE_DIR = os.path.join(SCRIPT_DIR, 'cardrush_buying_prices')
CARDS_JSON = os.path.join(SCRIPT_DIR, 'one_piece_cards.json')
PRICE_OVERRIDES_JSON = os.path.join(SCRIPT_DIR, 'card_price_overrides.json')
PRICE_DATA_OUT = os.path.join(REPO_ROOT, 'one_piece_app', 'public', 'cardrush_price_history.json')


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
    # Two alternates in the pattern:
    #   [A-Z]{2,}\d{2,}-\d{3}  – standard set codes, e.g. OP05-119, EB03-026
    #   [A-Z]-\d{3}             – promo codes,        e.g. P-105
    m = re.search(r'/([A-Z]{2,}\d{2,}-\d{3}|[A-Z]-\d{3})', url)
    return m.group(1) if m else ''


# Matches the base card code (no _p suffix) at the start of a string.
# Used both to extract base code from image codes and in get_image_code.
_BASE_CODE_PATTERN = re.compile(r'^([A-Z]{2,}\d{2,}-\d{3}|[A-Z]-\d{3})')


def get_image_code(url):
    """Extract the image filename stem from a card picture URL.

    E.g. 'https://.../card/OP01-051_p1.png?251219' -> 'OP01-051_p1'.
    The returned value always starts with a valid card code; any _p suffix is
    preserved.  Falls back to get_card_code() when no matching filename is found.
    """
    if not url:
        return ''
    # Match a card-code-shaped filename (with optional _p suffix) just before .ext
    m = re.search(r'/([A-Z]{2,}\d{2,}-\d{3}(?:_p\d*)?|[A-Z]-\d{3}(?:_p\d*)?)\.[^/]+(\?|$)', url)
    if m:
        return m.group(1)
    return get_card_code(url)


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

def strip_bracket_suffix(model_number):
    """Strip the set-annotation bracket from model numbers.

    Cardrush uses 'OP05-119[OP11]' to indicate a reprint of card OP05-119 that
    was included in the OP11 box set.  The bracket suffix is not part of the card
    code; stripping it lets us index the entry under the canonical code 'OP05-119'
    so it merges with other entries for that card.

    Recognised formats (letter prefix is 2-3 uppercase letters for set codes,
    or a single letter for promos):
      Standard  - 'OP05-119[OP11]'  -> 'OP05-119'  (2-3 letters + 2 digits + dash + 3 digits)
      Promo     - 'P-105[OP15]'     -> 'P-105'       (single letter + dash + 3 digits)

    If the model number does not match either format, the original string is
    returned unchanged.
    """
    m = re.match(r'^([A-Z]{2,3}\d{2}-\d{3}|[A-Z]-\d{3})', model_number)
    return m.group(1) if m else model_number


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
            raw = entry.get('model_number', '')
            if not raw:
                continue
            code = strip_bracket_suffix(raw)
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

            # Classify entries into mutually-exclusive groups using an index-based
            # tag so each entry is assigned to exactly one group.
            #   sealed    – name contains '未開封'
            #   gold_text – name contains '金文字' (and not sealed)
            #   parallel  – name contains 'パラレル' and not in any of the above
            #               (includes gold/silver bg, illust, manga parallels, etc.)
            #   base      – everything else
            SEALED, GOLD, PAR, BASE = range(4)

            def classify(e):
                name = e.get('name') or ''
                if '未開封' in name:
                    return SEALED
                if '金文字' in name:
                    return GOLD
                if 'パラレル' in name:
                    return PAR
                return BASE

            tagged = [(e, classify(e)) for e in entries]
            sealed    = [e for e, t in tagged if t == SEALED]
            gold_text = [e for e, t in tagged if t == GOLD]
            parallel  = [e for e, t in tagged if t == PAR]
            base      = [e for e, t in tagged if t == BASE]

            base_group = price_group(base)
            if base_group:
                hist_entry = {
                    'date': date,
                    'minPrice': base_group['minPrice'],
                    'maxPrice': base_group['maxPrice'],
                    'count': base_group['count'],
                }
            else:
                # No pure-base entries: leave root prices null so the frontend can
                # rely solely on variant subgroups (sealed/goldText/sp/parallel) for
                # display, and count=0 ensures no double-counting with subgroup counts.
                hist_entry = {
                    'date': date,
                    'minPrice': None,
                    'maxPrice': None,
                    'count': 0,
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
# Per-image-code price history (from card_price_overrides.json)
# ---------------------------------------------------------------------------

def load_price_overrides():
    """Load manual image-code → cardrush-name-pattern mappings and confidence scores.

    Returns a tuple of (mappings, confidence_mappings).
    """
    if not os.path.isfile(PRICE_OVERRIDES_JSON):
        return {}, {}
    try:
        with open(PRICE_OVERRIDES_JSON, encoding='utf-8') as f:
            data = json.load(f)
        mappings = data.get('mappings', {})
        confidences = data.get('confidence_mappings', {})
        if not isinstance(mappings, dict):
            print('WARNING: card_price_overrides.json "mappings" is not a dict, skipping')
            return {}, {}
        return mappings, confidences
    except (json.JSONDecodeError, OSError) as exc:
        print(f'WARNING: Failed to load {PRICE_OVERRIDES_JSON}: {exc}')
        return {}, {}


def build_image_code_history(history_by_code, price_files, overrides, confidence_mappings):
    """Build price-history entries keyed by image code using manual overrides.

    Includes the confidence score in the root of each image-code history entry
    if available in *confidence_mappings*.
    """
    if not overrides:
        return {}

    # Reuse the same variant-classification constants and logic as build_price_history.
    SEALED, GOLD, PAR, BASE = range(4)

    def classify(e):
        name = e.get('name') or ''
        if '未開封' in name:
            return SEALED
        if '金文字' in name:
            return GOLD
        if 'パラレル' in name:
            return PAR
        return BASE

    image_history = {}
    for image_code, name_pattern in overrides.items():
        # Derive the base card code from the image code (strip the _p suffix)
        m = _BASE_CODE_PATTERN.match(image_code)
        if not m:
            print(f'WARNING: Could not extract base code from image code "{image_code}", skipping')
            continue
        base_code = m.group(1)

        date_map = history_by_code.get(base_code, {})
        if not date_map:
            print(f'WARNING: No price data found for base code "{base_code}" (image code "{image_code}")')
            continue

        # Normalize name_pattern (str or list[str]) to a frozenset for O(1) lookup.
        # Every string is matched with exact equality against the Cardrush 'name' field.
        name_patterns = frozenset(
            name_pattern if isinstance(name_pattern, list) else [name_pattern]
        )

        # Determine if this is a base override (image code equals the base card code,
        # i.e. no _p suffix) or a variant override (_p suffix present).
        is_base_override = (image_code == base_code)

        history = []
        for date, entries in date_map.items():
            if is_base_override:
                # For base overrides: entries whose name is in the pattern set go to
                # BASE price; all other entries are classified for sealed/goldText/parallel
                # subgroups so variant toggles still work on the base card view.
                base = []
                tagged_non_base = []
                for e in entries:
                    if (e.get('name') or '') in name_patterns:
                        base.append(e)
                    else:
                        tagged_non_base.append((e, classify(e)))
                sealed    = [e for e, t in tagged_non_base if t == SEALED]
                gold_text = [e for e, t in tagged_non_base if t == GOLD]
                parallel  = [e for e, t in tagged_non_base if t == PAR]
            else:
                # For _p (variant) overrides: match entries whose name is in the pattern
                # set, then classify them normally into sealed/goldText/parallel/base.
                # Using a list of patterns lets you group multiple Cardrush entries
                # (e.g. regular + sealed variants of the same CS card) under one image.
                matching = [e for e in entries if (e.get('name') or '') in name_patterns]
                if not matching:
                    continue
                tagged = [(e, classify(e)) for e in matching]
                sealed    = [e for e, t in tagged if t == SEALED]
                gold_text = [e for e, t in tagged if t == GOLD]
                parallel  = [e for e, t in tagged if t == PAR]
                base      = [e for e, t in tagged if t == BASE]

            base_group = price_group(base)
            if base_group:
                hist_entry = {
                    'date': date,
                    'minPrice': base_group['minPrice'],
                    'maxPrice': base_group['maxPrice'],
                    'count': base_group['count'],
                }
            else:
                # No pure-base entries: leave root prices null so the frontend
                # relies solely on variant subgroups for display.
                hist_entry = {
                    'date': date,
                    'minPrice': None,
                    'maxPrice': None,
                    'count': 0,
                }

            sealed_group   = price_group(sealed)
            gold_group     = price_group(gold_text)
            parallel_group = price_group(parallel)
            if sealed_group:
                hist_entry['sealed'] = sealed_group
            if gold_group:
                hist_entry['goldText'] = gold_group
            if parallel_group:
                hist_entry['parallel'] = parallel_group

            # Only include the entry if there is at least one valid price
            all_prices = [p for p in (
                hist_entry.get('minPrice'),
                *(g['minPrice'] for g in [sealed_group, gold_group, parallel_group] if g),
            ) if p is not None]
            if not all_prices:
                continue

            history.append(hist_entry)

        history.sort(key=lambda x: x['date'])
        if history:
            image_history[image_code] = {'history': history}
            if image_code in confidence_mappings:
                image_history[image_code]['confidence'] = confidence_mappings[image_code]
            pat_display = (name_pattern if isinstance(name_pattern, str)
                           else f'[{", ".join(repr(p) for p in name_pattern)}]')
            print(f'  Override: {image_code} -> {len(history)} date entries (patterns: {pat_display})')

    return image_history

def build_rarity_map():
    """Return two maps: card_code -> list of rarities, and card_code -> list of image codes."""
    code_to_rarities = {}
    code_to_image_codes = {}
    if not os.path.isfile(CARDS_JSON):
        return code_to_rarities, code_to_image_codes
    try:
        with open(CARDS_JSON, encoding='utf-8') as f:
            cards = json.load(f)
        for card in cards:
            picture = card.get('Picture', '')
            code = get_card_code(picture)
            img_code = get_image_code(picture)
            rarity = card.get('Rarity', '')
            if code and rarity:
                seen = code_to_rarities.setdefault(code, [])
                if rarity not in seen:
                    seen.append(rarity)
            if code and img_code:
                imgs = code_to_image_codes.setdefault(code, [])
                if img_code not in imgs:
                    imgs.append(img_code)
    except (json.JSONDecodeError, OSError) as exc:
        print(f'WARNING: Failed to build rarity map: {exc}')
    return code_to_rarities, code_to_image_codes


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


def is_multiple_prices_matched(item, mappings):
    """Return True if this multiplePrices entry has been addressed in mappings.

    A card is considered matched once any of its image codes (including the base
    card code) appears as a key in the manual 'mappings' dict.  Matched entries
    are moved to the bottom of the multiplePrices list so unhandled cards stay
    visible at the top.
    """
    if item.get('cardCode', '') in mappings:
        return True
    for img_code in item.get('imageCodes', []):
        if img_code in mappings:
            return True
    return False


def merge_multiple_prices(existing_list, fresh_list, mappings):
    """Merge the existing multiplePrices list with a freshly-generated one.

    Rules:
    - Existing entries are updated with the latest scrape data where available,
      or kept unchanged if the card no longer appears in the latest scrape.
    - New entries (cards in fresh_list not yet in existing_list) are appended.
    - After merging, matched entries (any image code present in mappings) are
      moved to the bottom so unhandled cards remain at the top.
    - Relative order within the unmatched and matched groups is preserved.
    """
    fresh_by_code = {item['cardCode']: item for item in fresh_list}
    seen_codes = set()
    merged = []

    # Process existing entries first, updating data from the fresh list
    for item in existing_list:
        if not isinstance(item, dict) or 'cardCode' not in item:
            print(f'WARNING: Skipping invalid multiplePrices entry (missing cardCode): {item!r}')
            continue
        code = item['cardCode']
        seen_codes.add(code)
        merged.append(fresh_by_code.get(code, item))

    # Append brand-new cards not previously in the list
    for item in fresh_list:
        if item['cardCode'] not in seen_codes:
            merged.append(item)

    # Move matched entries to the bottom in one pass, preserving relative order
    unmatched, matched = [], []
    for item in merged:
        (matched if is_multiple_prices_matched(item, mappings) else unmatched).append(item)
    return unmatched + matched


def build_unmatched(history_by_code, price_files, code_to_rarities, code_to_image_codes):
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
                raw = entry.get('model_number', '')
                code = strip_bracket_suffix(raw) if raw else ''
                if code:
                    latest_by_code.setdefault(code, []).append(entry)
        except (json.JSONDecodeError, OSError) as exc:
            print(f'WARNING: Failed to parse latest file {latest_file}: {exc}')

    multiple_prices = [
        {
            'cardCode': code,
            'priceCount': len(entries),
            'imageCodes': code_to_image_codes.get(code, []),
            'entries': entries,
        }
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

    # Apply per-image-code overrides from card_price_overrides.json
    mappings, confidence_mappings = load_price_overrides()
    if mappings:
        print(f'Loaded {len(mappings)} price override(s), building per-image-code histories...')
        image_code_history = build_image_code_history(history_by_code, price_files, mappings, confidence_mappings)
        price_history.update(image_code_history)
        print(f'  Added {len(image_code_history)} image-code history entries')

    with open(PRICE_DATA_OUT, 'w', encoding='utf-8') as f:
        json.dump(price_history, f, ensure_ascii=False)
    print(f'Wrote {PRICE_DATA_OUT} ({len(price_history)} card codes)')

    code_to_rarities, code_to_image_codes = build_rarity_map()
    print(f'Loaded rarity data for {len(code_to_rarities)} card codes')

    unmatched = build_unmatched(history_by_code, price_files, code_to_rarities, code_to_image_codes)

    # Load the existing card_price_overrides.json to preserve '_comment' and 'multiplePrices'.
    # Use the already-validated 'mappings' dict (avoids a second type-check).
    existing_comment = None
    existing_multiple_prices = []
    if os.path.isfile(PRICE_OVERRIDES_JSON):
        try:
            with open(PRICE_OVERRIDES_JSON, encoding='utf-8') as f:
                existing = json.load(f)
            existing_comment = existing.get('_comment')
            raw_multiple_prices = existing.get('multiplePrices', [])
            existing_multiple_prices = raw_multiple_prices if isinstance(raw_multiple_prices, list) else []
        except (json.JSONDecodeError, OSError) as exc:
            print(f'WARNING: Failed to read existing {PRICE_OVERRIDES_JSON}: {exc}')

    # 'mappings' is already validated; reuse it here.
    # Merge multiplePrices incrementally: add new cards, update existing ones,
    # and move matched entries (image code present in mappings) to the bottom.
    merged_multiple_prices = merge_multiple_prices(
        existing_multiple_prices,
        unmatched['multiplePrices'],
        mappings,
    )
    matched_count = sum(
        1 for item in merged_multiple_prices
        if is_multiple_prices_matched(item, mappings)
    )
    print(f'  Multiple prices (merged): {len(merged_multiple_prices)} total, '
          f'{matched_count} matched (moved to bottom)')

    combined = {}
    if existing_comment is not None:
        combined['_comment'] = existing_comment
    combined['mappings'] = mappings
    combined['confidence_mappings'] = confidence_mappings
    combined['asOf'] = unmatched['asOf']
    combined['multiplePrices'] = merged_multiple_prices
    combined['multiPricePatterns'] = unmatched['multiPricePatterns']
    combined['pricesWithoutCards'] = unmatched['pricesWithoutCards']
    combined['pricesWithoutCardsBreakdown'] = unmatched['pricesWithoutCardsBreakdown']
    combined['cardsWithoutPrices'] = unmatched['cardsWithoutPrices']
    combined['cardsWithoutPricesBreakdown'] = unmatched['cardsWithoutPricesBreakdown']
    combined['cardsWithoutPricesRarityBreakdown'] = unmatched['cardsWithoutPricesRarityBreakdown']

    with open(PRICE_OVERRIDES_JSON, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f'Wrote {PRICE_OVERRIDES_JSON}')
    print(f'  Multiple prices: {len(merged_multiple_prices)} ({matched_count} matched at bottom)')
    print(f'  Prices without cards: {len(unmatched["pricesWithoutCards"])}')
    print(f'  Cards without prices: {len(unmatched["cardsWithoutPrices"])}')


if __name__ == '__main__':
    main()

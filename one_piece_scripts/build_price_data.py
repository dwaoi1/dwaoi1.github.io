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
    if amount_str is None:
        return None
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
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
        # Use relative path from PRICE_DIR to avoid collisions (e.g. Feb 2026/2026-02-14.json)
        # We'll use the filename as the date, but the full path ensures uniqueness in the map.
        rel_path = os.path.relpath(file_path, PRICE_DIR)
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
            # We use rel_path as the key internally to keep all historical points separate,
            # then flatten them to just the 'date' string in the final output.
            history_by_code.setdefault(code, {}).setdefault(rel_path, []).append(entry)
    return history_by_code


# Detailed classification logic using Cardrush name patterns
def classify_entry(e):
    """Classify a Cardrush entry into variant categories based on its name."""
    name = e.get('name') or ''
    
    # Classification order matters!
    if '未開封' in name:
        return 'sealed'
    if '金文字' in name:
        return 'goldText'
    
    # Specific parallel markings
    # 'パラレル' is the general term for Parallel
    # '漫画' indicates Manga art (a type of parallel)
    # 'SP' indicates Special variant
    # 'シリアル' indicates Serial numbered
    if any(sig in name for i, sig in enumerate(['パラレル', '漫画', 'SP', 'シリアル', 'illust', 'CS', 'アニメ'])):
        return 'parallel'
        
    return 'base'


def build_price_history(history_by_code, mappings=None):
    price_history = {}

    # Pre-process mappings: group all mapped names/URLs by their base card code.
    # This allows us to exclude variant entries from the base-card history.
    mapped_patterns_by_base = {}
    if mappings:
        for img_code, pattern in mappings.items():
            m = _BASE_CODE_PATTERN.match(img_code)
            if not m:
                continue
            base_code = m.group(1)
            patterns = pattern if isinstance(pattern, list) else [pattern]
            # Use a list of (image_code, pattern) so we can distinguish base from variant
            mapped_patterns_by_base.setdefault(base_code, []).extend((img_code, p) for p in patterns)

    for code, rel_path_map in history_by_code.items():
        history = []
        
        # Patterns belonging to variants of this code (e.g. OP01-016_p1)
        # which must be excluded from the base card history.
        all_mappings = mapped_patterns_by_base.get(code, [])
        exclude_patterns = [p for ic, p in all_mappings if ic != code]
        exclude_names = frozenset(p for p in exclude_patterns if not p.startswith('http'))
        exclude_images = frozenset(p for p in exclude_patterns if p.startswith('http'))
        
        # Patterns belonging specifically to the base card (e.g. OP01-016)
        # which should be included even if they appear in the exclusion list elsewhere.
        include_patterns = [p for ic, p in all_mappings if ic == code]
        include_names = frozenset(p for p in include_patterns if not p.startswith('http'))
        include_images = frozenset(p for p in include_patterns if p.startswith('http'))

        # Flatten the rel_path_map which might have multiple entries for the same date 
        # (though usually one per day). We group by actual date string for the final output.
        by_date = {}
        for rel_path, entries in rel_path_map.items():
            date_str = os.path.splitext(os.path.basename(rel_path))[0]
            by_date.setdefault(date_str, []).extend(entries)

        for date, entries in by_date.items():
            # Filter entries:
            # 1. ALWAYS exclude if specifically mapped to a variant (_p1 etc)
            # 2. ALWAYS include if specifically mapped to the base code
            # 3. If no mappings exist for this card at all, include everything (default)
            current_entries = []
            for e in entries:
                name = e.get('name') or ''
                image = e.get('image') or ''
                
                # Check if this entry is a known variant
                # We check both name and image for maximum compatibility with old/new scrapes
                is_variant = name in exclude_names or image in exclude_images
                # Check if this entry is the known base
                is_base = name in include_names or image in include_images
                
                if is_base:
                    current_entries.append(e)
                elif not is_variant:
                    # Not a known variant, so we keep it in the base pool
                    current_entries.append(e)

            if not current_entries:
                continue

            # Group entries by classification
            groups = {'sealed': [], 'goldText': [], 'parallel': [], 'base': []}
            for e in current_entries:
                groups[classify_entry(e)].append(e)

            base_group = price_group(groups['base'])
            if base_group:
                hist_entry = {
                    'date': date,
                    'minPrice': base_group['minPrice'],
                    'maxPrice': base_group['maxPrice'],
                    'count': base_group['count'],
                }
            else:
                hist_entry = {
                    'date': date,
                    'minPrice': None,
                    'maxPrice': None,
                    'count': 0,
                }

            for key in ['sealed', 'goldText', 'parallel']:
                g = price_group(groups[key])
                if g:
                    hist_entry[key] = g

            # Only include if there is some price data
            if any(hist_entry.get(k) is not None for k in ['minPrice', 'sealed', 'goldText', 'parallel']):
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

    Returns a tuple of (mappings, confidence_mappings, success).
    """
    if not os.path.isfile(PRICE_OVERRIDES_JSON):
        return {}, {}, True
    try:
        with open(PRICE_OVERRIDES_JSON, encoding='utf-8') as f:
            data = json.load(f)
        mappings = data.get('mappings', {})
        confidences = data.get('confidence_mappings', {})
        if not isinstance(mappings, dict):
            print('WARNING: card_price_overrides.json "mappings" is not a dict, skipping')
            return {}, {}, False
        return mappings, confidences, True
    except (json.JSONDecodeError, OSError) as exc:
        print(f'ERROR: Failed to load {PRICE_OVERRIDES_JSON}: {exc}')
        return {}, {}, False


def build_image_code_history(history_by_code, price_files, overrides, confidence_mappings):
    """Build price-history entries keyed by image code using manual overrides.

    Includes the confidence score in the root of each image-code history entry
    if available in *confidence_mappings*.
    """
    if not overrides:
        return {}

    image_history = {}
    for image_code, name_pattern in overrides.items():
        # Derive the base card code from the image code (strip the _p suffix)
        m = _BASE_CODE_PATTERN.match(image_code)
        if not m:
            print(f'WARNING: Could not extract base code from image code "{image_code}", skipping')
            continue
        base_code = m.group(1)

        rel_path_map = history_by_code.get(base_code, {})
        if not rel_path_map:
            print(f'WARNING: No price data found for base code "{base_code}" (image code "{image_code}")')
            continue

        # Flatten the rel_path_map
        by_date = {}
        for rel_path, entries in rel_path_map.items():
            date_str = os.path.splitext(os.path.basename(rel_path))[0]
            by_date.setdefault(date_str, []).extend(entries)

        # Normalize name_pattern (str or list[str]) to frozensets for O(1) lookup.
        # Strings starting with http are matched against the Cardrush 'image' field;
        # all others are matched with exact equality against the 'name' field.
        patterns = name_pattern if isinstance(name_pattern, list) else [name_pattern]
        name_patterns = frozenset(p for p in patterns if not p.startswith('http'))
        image_patterns = frozenset(p for p in patterns if p.startswith('http'))

        def is_match(e):
            if (e.get('name') or '') in name_patterns:
                return True
            if (e.get('image') or '') in image_patterns:
                return True
            return False

        # Determine if this is a base override ...
        is_base_override = (image_code == base_code)

        history = []
        for date, entries in by_date.items():
            if is_base_override:
                # For base overrides: entries whose name/URL is in the pattern set go to
                # BASE price; all other entries are classified for sealed/goldText/parallel
                # subgroups so variant toggles still work on the base card view.
                groups = {'sealed': [], 'goldText': [], 'parallel': [], 'base': []}
                for e in entries:
                    if is_match(e):
                        groups['base'].append(e)
                    else:
                        groups[classify_entry(e)].append(e)
            else:
                # For _p (variant) overrides: match entries whose name/URL is in the pattern
                # set, then classify them normally into sealed/goldText/parallel/base.
                matching = [e for e in entries if is_match(e)]
                if not matching:
                    continue
                groups = {'sealed': [], 'goldText': [], 'parallel': [], 'base': []}
                for e in matching:
                    groups[classify_entry(e)].append(e)

            base_group = price_group(groups['base'])
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

            for key in ['sealed', 'goldText', 'parallel']:
                g = price_group(groups[key])
                if g:
                    hist_entry[key] = g

            # Only include the entry if there is at least one valid price
            if any(hist_entry.get(k) is not None for k in ['minPrice', 'sealed', 'goldText', 'parallel']):
                history.append(hist_entry)

        history.sort(key=lambda x: x['date'])
        if history:
            image_history[image_code] = {'history': history}
            if image_code in confidence_mappings:
                image_history[image_code]['confidence'] = confidence_mappings[image_code]
            
            # Find a sample Cardrush image URL to use as a fallback in the frontend.
            # We take the first non-empty 'image' field from any matching entry.
            sample_image = None
            for rel_path, entries in rel_path_map.items():
                for e in entries:
                    if is_match(e) and e.get('image'):
                        sample_image = e['image']
                        break
                if sample_image: break
            if sample_image:
                image_history[image_code]['cardrushImage'] = sample_image

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


def atomic_write_json(file_path, data, **kwargs):
    """Write data to a temporary file and rename it to file_path to ensure atomicity."""
    tmp_path = file_path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, **kwargs)
        os.replace(tmp_path, file_path)
    except Exception as exc:
        print(f'ERROR: Failed to write to {file_path}: {exc}')
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


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

    # Apply per-image-code overrides from card_price_overrides.json.
    # We load them early so that build_price_history can exclude mapped variant names
    # from the shared/aggregate base-card price entries.
    mappings, confidence_mappings, initial_load_success = load_price_overrides()
    price_history = build_price_history(history_by_code, mappings)

    if mappings:
        print(f'Loaded {len(mappings)} price override(s), building per-image-code histories...')
        image_code_history = build_image_code_history(history_by_code, price_files, mappings, confidence_mappings)
        price_history.update(image_code_history)
        print(f'  Added {len(image_code_history)} image-code history entries')

    atomic_write_json(PRICE_DATA_OUT, price_history)
    print(f'Wrote {PRICE_DATA_OUT} ({len(price_history)} card codes)')

    code_to_rarities, code_to_image_codes = build_rarity_map()
    print(f'Loaded rarity data for {len(code_to_rarities)} card codes')

    unmatched = build_unmatched(history_by_code, price_files, code_to_rarities, code_to_image_codes)

    # Load the existing card_price_overrides.json to preserve '_comment' and 'multiplePrices'.
    existing_comment = None
    existing_multiple_prices = []
    reload_success = True
    if os.path.isfile(PRICE_OVERRIDES_JSON):
        try:
            with open(PRICE_OVERRIDES_JSON, encoding='utf-8') as f:
                existing = json.load(f)
            existing_comment = existing.get('_comment')
            raw_multiple_prices = existing.get('multiplePrices', [])
            existing_multiple_prices = raw_multiple_prices if isinstance(raw_multiple_prices, list) else []
            
            # RE-LOAD mappings and confidence_mappings from disk to ensure we don't 
            # overwrite any updates made (e.g. by visual_match.py) while this script 
            # was processing the price files.
            disk_mappings = existing.get('mappings', {})
            if isinstance(disk_mappings, dict):
                mappings.update(disk_mappings)
            
            disk_confidences = existing.get('confidence_mappings', {})
            if isinstance(disk_confidences, dict):
                confidence_mappings.update(disk_confidences)
        except (json.JSONDecodeError, OSError) as exc:
            print(f'ERROR: Failed to re-load {PRICE_OVERRIDES_JSON}: {exc}')
            reload_success = False

    if not initial_load_success or not reload_success:
        print(f'SKIPPING write-back to {PRICE_OVERRIDES_JSON} to avoid potential data loss due to load errors.')
        return

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

    atomic_write_json(PRICE_OVERRIDES_JSON, combined, indent=2)
    print(f'Wrote {PRICE_OVERRIDES_JSON}')
    print(f'  Multiple prices: {len(merged_multiple_prices)} ({matched_count} matched at bottom)')
    print(f'  Prices without cards: {len(unmatched["pricesWithoutCards"])}')
    print(f'  Cards without prices: {len(unmatched["cardsWithoutPrices"])}')


if __name__ == '__main__':
    main()

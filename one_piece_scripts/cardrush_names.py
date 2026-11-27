#!/usr/bin/env python3
"""Shared CardRush name parsing used by both the rematcher and the price builder.

A CardRush listing name has the form 'BASE(ann1/ann2/...)'.  This module
splits and classifies those annotations deterministically so that
remap_prices.py (mapping) and build_price_data.py (price grouping) always
agree on what an entry is.
"""

import re
import unicodedata
import collections


def split_name(name):
    """Split 'BASE(ann1/ann2)' -> ('BASE', 'ann1/ann2'), width-agnostic."""
    depth = 0
    start = None
    for i, ch in enumerate(name):
        if ch in '(（':
            if depth == 0:
                start = i
            depth += 1
        elif ch in ')）':
            depth -= 1
            if depth == 0 and start is not None:
                return name[:start].strip(), name[start + 1:i].strip()
    return name.strip(), ''


def canon(s):
    """Aggressive canonical form for official-vs-cardrush name comparison."""
    s = unicodedata.normalize('NFKC', s)
    s = s.replace('…', '...').replace('⋯', '...')
    s = re.sub(r'[“”"‘’\'「」『』]', '', s)
    s = re.sub(r'[\s　]+', '', s)
    return s


def canon_loose(s):
    """Canon form with parenthesised content removed (Mr.3(ギャルディーノ) cases)."""
    s = canon(s)
    s = re.sub(r'\([^)]*\)', '', s)
    return s


def parse_tokens(name):
    prefix, ann = split_name(name)
    parts = [p.strip() for p in re.split(r'[/／]', ann) if p.strip()]
    return prefix, parts


CONDITION_MARKERS = (
    '未開封', '開封', '付属品完備', '英語版', '中国版', '韓国版',
    'アジア', 'Asia', 'ASIA', 'BOX', 'カードのみ',
)
SEALED_MARKERS = ('未開封', '開封', '付属品完備')
LANGUAGE_MARKERS = ('英語版', '中国版', '韓国版', 'アジア', 'Asia', 'ASIA')
NORMAL_MARKERS = ('ノーマル仕様', '通常', '無印', 'ロゴ無し')


def token_kind(part):
    """'illust' | 'sealed' | 'language' | 'event' | 'variant' | 'other'"""
    if part.lower().startswith('illust'):
        return 'illust'
    if any(c in part for c in SEALED_MARKERS):
        return 'sealed'
    if any(c in part for c in LANGUAGE_MARKERS):
        return 'language'
    if re.match(r'^CS\d*([-\d]*)?$', part):
        return 'event'
    if any(m == part for m in NORMAL_MARKERS):
        return 'other'
    if any(c in part for c in CONDITION_MARKERS):
        return 'sealed'
    if part in ('Japan', 'japan'):
        return 'other'
    return 'variant'


def analyse_entry(name, official_name):
    """Classify a CardRush entry relative to its official card name."""
    prefix, parts = parse_tokens(name)
    canon_ok = canon(prefix) == official_name
    loose_ok = canon_loose(prefix) == canon_loose(official_name)
    kinds = collections.Counter(token_kind(p) for p in parts)
    illust = next((p for p in parts if token_kind(p) == 'illust'), '')
    variant_tokens = tuple(sorted(
        p for p in parts if token_kind(p) in ('variant', 'event')
    ))
    sealed_tokens = tuple(sorted(
        p for p in parts if token_kind(p) == 'sealed'
    ))
    return {
        'prefix': prefix,
        'parts': parts,
        'name_ok': 'exact' if canon_ok else ('loose' if loose_ok else None),
        'illust': illust,
        'variant_tokens': variant_tokens,
        'sealed_tokens': sealed_tokens,
        'is_variant': kinds['variant'] > 0 or kinds['event'] > 0,
        'is_sealed': kinds['sealed'] > 0,
        'is_language': kinds['language'] > 0,
        'is_base_clean': kinds['variant'] == 0 and kinds['event'] == 0
                         and kinds['sealed'] == 0 and kinds['language'] == 0,
    }


def classify_price_group(name, rarity=''):
    """Map a CardRush entry to a price-history subgroup.

    Returns one of: 'sealed', 'sealedAsia', 'goldText', 'parallel',
    'parallelAsia', 'asia', 'base'.  Mirrors the original classify_entry()
    contract used by build_price_data.py.
    """
    parts = parse_tokens(name)[1]
    kinds = collections.Counter(token_kind(p) for p in parts)
    is_asia = ('asia' in name.lower() or 'アジア' in name
               or any(token_kind(p) == 'language' for p in parts))

    if kinds['sealed'] > 0:
        return 'sealedAsia' if is_asia else 'sealed'
    if '金文字' in name:
        return 'goldText'
    if kinds['variant'] > 0 or kinds['event'] > 0 or '/P' in (rarity or ''):
        return 'parallelAsia' if is_asia else 'parallel'
    if is_asia:
        return 'asia'
    return 'base'

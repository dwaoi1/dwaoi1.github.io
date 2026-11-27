#!/usr/bin/env python3
"""Ground-up deterministic remapping of official card image codes to CardRush entries.

Rebuilds the image_code -> CardRush-entry links from scratch using only
deterministic evidence: card codes, normalized names, variant tokens, and
(perceptual-hash) image comparison.  No prior mappings are read.

Outputs (under one_piece_scripts/remap_out/):
  mappings.json     proposed mappings in the card_price_overrides schema
  queue.json        unresolved items for the manual matcher
  report.json       full provenance: rules applied, distances, orphans, stats

Stages:
  --stage text    text rules only (count-rule variant assignment)
  --stage phash   text rules + perceptual-hash art disambiguation (default)
  --commit        write mappings (+ manual_links.json) into card_price_overrides.json
"""

import argparse
import json
import os
import re
import sys
import time
import collections
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_price_data import (  # noqa: E402
    strip_bracket_suffix, phash, hamming_distance, atomic_write_json,
)
from cardrush_names import analyse_entry, canon  # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
CARDS_JSON = os.path.join(SCRIPT_DIR, 'one_piece_cards.json')
PRICE_DIR = os.path.join(SCRIPT_DIR, 'cardrush_buying_prices')
OVERRIDES_JSON = os.path.join(SCRIPT_DIR, 'card_price_overrides.json')
OFFICIAL_IMG_DIR = os.path.join(REPO_ROOT, 'one_piece_app', 'public', 'images', 'cards')
CR_CACHE_DIR = os.path.join(SCRIPT_DIR, '.image_cache')
HASH_CACHE = os.path.join(SCRIPT_DIR, '.phash_cache.json')
OUT_DIR = os.path.join(SCRIPT_DIR, 'remap_out')

T_ACCEPT = 24       # max hamming distance to accept an image match
MARGIN = 10         # required gap to the second-best candidate

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_official():
    with open(CARDS_JSON, encoding='utf-8') as f:
        cards = json.load(f)
    off = {}
    for c in cards:
        m = re.search(r'/([A-Z]+\d*-\d{3})(?:_p(\d+))?\.png', c.get('Picture', ''))
        if not m:
            continue
        base, suf = m.group(1), m.group(2)
        rec = off.setdefault(base, {'name': '', 'images': [], 'rarities': []})
        if suf is None and not rec['name']:
            rec['name'] = canon(c.get('Character', '').replace('(Parallel)', ''))
        code = base + (f'_p{suf}' if suf else '')
        if code not in rec['images']:
            rec['images'].append(code)
        rar = c.get('Rarity', '')
        if rar and rar not in rec['rarities']:
            rec['rarities'].append(rar)
    return off


def find_reference_snapshot():
    files = []
    for dirpath, _dirs, names in os.walk(PRICE_DIR):
        for fn in names:
            if fn.endswith('.json'):
                files.append(os.path.join(dirpath, fn))
    files.sort(key=lambda p: os.path.basename(p))
    for path in reversed(files):
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if len(data) > 2000:
            return path, data
    if not files:
        raise SystemExit('ERROR: no price snapshots found')
    with open(files[-1], encoding='utf-8') as f:
        return files[-1], json.load(f)


def group_entries_by_base(entries):
    grouped = collections.defaultdict(list)
    skipped = 0
    for e in entries:
        raw = e.get('model_number', '')
        if not raw or raw in ('-', 'P'):
            skipped += 1
            continue
        code = strip_bracket_suffix(raw)
        if not re.match(r'^[A-Z]+\d*-\d{3}$', code):
            skipped += 1
            continue
        grouped[code].append(e)
    return grouped, skipped


# ---------------------------------------------------------------------------
# Image hashing
# ---------------------------------------------------------------------------

class Hasher:
    def __init__(self, download=True, verbose=True):
        self.download = download
        self.verbose = verbose
        self.cache = {}
        self._official_memo = {}
        if os.path.isfile(HASH_CACHE):
            try:
                with open(HASH_CACHE, encoding='utf-8') as f:
                    self.cache = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        self.dirty = 0
        os.makedirs(CR_CACHE_DIR, exist_ok=True)

    def save(self):
        if self.dirty:
            atomic_write_json(HASH_CACHE, self.cache)

    @staticmethod
    def _bits_key(h):
        return ''.join('1' if b else '0' for b in h)

    @staticmethod
    def _key_bits(s):
        return [ch == '1' for ch in s]

    def official(self, image_code):
        if image_code in self._official_memo:
            return self._official_memo[image_code]
        bits = None
        for ext in ('.png', '.jpg'):
            path = os.path.join(OFFICIAL_IMG_DIR, image_code + ext)
            if os.path.isfile(path):
                bits = self._hash_file(path)
                break
        self._official_memo[image_code] = bits
        return bits

    def cardrush(self, url):
        if not url:
            return None
        key = 'cr:' + url
        if key in self.cache:
            return self._key_bits(self.cache[key])
        path = self._resolve_cardrush_image(url)
        if path is None:
            return None
        bits = self._hash_file(path)
        if bits is not None:
            self.cache[key] = self._bits_key(bits)
            self.dirty += 1
        return bits

    def _resolve_cardrush_image(self, url):
        img_id = re.sub(r'\D', '', os.path.basename(url.split('?')[0]))
        if img_id:
            existing = os.path.join(OFFICIAL_IMG_DIR, img_id + '.webp')
            if os.path.isfile(existing):
                return existing
        dest = os.path.join(CR_CACHE_DIR, (img_id or 'x') + '.webp')
        if os.path.isfile(dest):
            return dest
        if not self.download:
            return None
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            with open(dest + '.tmp', 'wb') as f:
                f.write(data)
            os.replace(dest + '.tmp', dest)
            time.sleep(0.05)
            return dest
        except Exception as exc:
            if self.verbose:
                print(f'  WARN: download failed {url}: {exc}')
            return None

    @staticmethod
    def _hash_file(path):
        try:
            import cv2
            img = cv2.imread(path)
            h = phash(img)
            return h
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def match_base_code(base, off_rec, entries, hasher, do_phash):
    """Return (mappings, queue_items, report) for one base card code."""
    mappings = {}
    queue = []
    rep = {'base': base}
    official_name = off_rec['name']
    official_images = off_rec['images']
    p_images = [i for i in official_images if '_p' in i]
    base_image = next((i for i in official_images if '_p' not in i), None)

    analysed = []
    foreign = []
    for e in entries:
        a = analyse_entry(e['name'], official_name)
        if a['name_ok'] is None:
            foreign.append((e, a))
        else:
            analysed.append((e, a))

    # --- base image code mapping -------------------------------------------
    base_clean = [(e, a) for e, a in analysed if not a['is_variant'] and a['is_base_clean']]
    base_cond = [(e, a) for e, a in analysed if not a['is_variant'] and not a['is_base_clean']]
    if not entries:
        rep['base_rule'] = 'no_cardrush_entries'
    elif base_image and base_clean:
        patterns = []
        for e, _a in base_clean:
            patterns.append(e['name'])
            if e.get('image'):
                patterns.append(e['image'])
        mappings[base_image] = patterns
        rep['base_rule'] = f'count={len(base_clean)}'
    elif base_image:
        rep['base_rule'] = 'no_clean_base_entry'
        rep['base_condition_entries'] = len(base_cond)

    # --- variant (art) groups ------------------------------------------------
    groups = collections.OrderedDict()
    for e, a in analysed:
        if not a['is_variant']:
            continue
        key = (a['variant_tokens'], a['illust'])
        groups.setdefault(key, []).append((e, a))

    rep['p_images'] = p_images
    rep['art_groups'] = [
        {'tokens': list(k[0]), 'illust': k[1], 'entries': len(v)}
        for k, v in groups.items()
    ]

    if not p_images or not groups:
        if p_images and not groups:
            rep['note'] = 'p_images_without_cardrush_variants'
        if groups and not p_images:
            rep['note'] = 'cardrush_variants_without_p_images'
        rep['orphans'] = []
        return mappings, queue, rep

    # --- assignment ----------------------------------------------------------
    group_keys = list(groups.keys())
    assigned = {}   # p_image -> group_key
    reason = {}
    dist_matrix = {}
    matched_entry = {}

    if len(p_images) == 1 and len(group_keys) == 1:
        assigned[p_images[0]] = group_keys[0]
        reason[p_images[0]] = {'rule': 'count', 'distance': None}
    elif do_phash:
        dist_matrix = {}
        matched_entry = {}
        for gk in group_keys:
            # Hash up to every image in the group and keep the closest one:
            # sealed-product photos often differ strongly from official scans.
            for e, _a in sorted(groups[gk], key=lambda ea: condition_rank(ea[0])):
                gh = hasher.cardrush(e.get('image', ''))
                if gh is None:
                    continue
                for pimg in p_images:
                    oh = hasher.official(pimg)
                    if oh is None:
                        continue
                    d = hamming_distance(oh, gh)
                    key = (pimg, gk)
                    if key not in dist_matrix or d < dist_matrix[key]:
                        dist_matrix[key] = d
                        matched_entry[key] = e.get('name', '')

        # greedy one-to-one over ascending distances
        pairs = sorted(dist_matrix.items(), key=lambda kv: kv[1])
        used_p = set()
        used_g = set()
        for (pimg, gk), d in pairs:
            if pimg in used_p or gk in used_g:
                continue
            if d > T_ACCEPT:
                continue
            others = sorted(
                dd for (pp, gg), dd in dist_matrix.items()
                if (pp == pimg or gg == gk) and (pp, gg) != (pimg, gk)
            )
            second = others[0] if others else None
            if second is not None and second - d < MARGIN:
                continue
            assigned[pimg] = gk
            used_p.add(pimg)
            used_g.add(gk)
            reason[pimg] = {
                'rule': 'phash',
                'distance': d,
                'second_best': second,
                'matched_entry': matched_entry[(pimg, gk)],
            }

        unassigned_p = [p for p in p_images if p not in assigned]
        unassigned_g = [g for g in group_keys if g not in used_g]
        if unassigned_p and unassigned_g:
            for pimg in unassigned_p:
                reason[pimg] = {'rule': 'unresolved', 'distance': None}
    else:
        for pimg in p_images:
            reason[pimg] = {'rule': 'queued_text_stage', 'distance': None}

    # --- emit mappings / queue ------------------------------------------------
    for pimg, gk in assigned.items():
        patterns = []
        for e, _a in groups[gk]:
            patterns.append(e['name'])
            if e.get('image'):
                patterns.append(e['image'])
        mappings[pimg] = patterns

    orphans = []
    for gk in group_keys:
        if gk not in assigned.values():
            orphans.append({
                'tokens': list(gk[0]),
                'illust': gk[1],
                'entries': [e['name'] for e, _a in groups[gk]],
            })

    unresolved_p = [p for p in p_images if p not in assigned]
    if unresolved_p or (orphans and len(assigned) < len(p_images)):
        hints = {}
        for pimg in unresolved_p:
            ranked = sorted(
                (
                    {'group': group_keys.index(gk), 'distance': d,
                     'entry': matched_entry.get((pimg, gk), '')}
                    for (pp, gk), d in dist_matrix.items() if pp == pimg
                ),
                key=lambda h: h['distance'],
            )
            if ranked:
                hints[pimg] = ranked[:3]
        queue.append({
            'type': 'variant',
            'base_code': base,
            'official_name': official_name,
            'official': [
                {
                    'image_code': p,
                    'local': f'{p}.png',
                    'image_code_base': base,
                }
                for p in p_images
            ],
            'candidates': [
                {
                    'tokens': list(gk[0]),
                    'illust': gk[1],
                    'entries': [
                        {
                            'name': e['name'],
                            'image': e.get('image', ''),
                            'amount': e.get('amount', ''),
                            'rarity': e.get('rarity', ''),
                        }
                        for e, _a in groups[gk]
                    ],
                }
                for gk in group_keys
            ],
            'assigned': {p: list(assigned[p][0]) + ([assigned[p][1]] if assigned[p][1] else [])
                         for p in assigned},
            'reason': reason,
            'phash_hints': hints,
        })

    for e, a in foreign:
        queue.append({
            'type': 'name_mismatch',
            'base_code': base,
            'official_name': official_name,
            'entry': {
                'name': e['name'],
                'image': e.get('image', ''),
                'amount': e.get('amount', ''),
                'model_number': e.get('model_number', ''),
            },
            'entry_prefix': a['prefix'],
        })

    rep['assigned'] = {p: reason.get(p, {}) for p in assigned}
    rep['orphans'] = orphans
    rep['foreign'] = len(foreign)
    return mappings, queue, rep


def condition_rank(entry):
    """Order entry images by likelihood of being a clean card scan."""
    name = entry.get('name', '')
    if not any(c in name for c in ('未開封', '付属品完備')):
        return 0
    if '開封' in name:
        return 1
    return 2


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args):
    print('Loading official card list...')
    off = load_official()
    print(f'  {len(off)} base codes')

    snap_path, snapshot = find_reference_snapshot()
    print(f'Reference snapshot: {os.path.relpath(snap_path, REPO_ROOT)} ({len(snapshot)} rows)')
    cr, skipped = group_entries_by_base(snapshot)
    print(f'  {len(cr)} base codes on Cardrush ({skipped} rows skipped)')

    hasher = Hasher(download=not args.no_download)
    all_mappings = {}
    all_queue = []
    reports = {}
    rules = collections.Counter()
    base_rules = collections.Counter()

    bases = sorted(set(off) | set(cr))
    if args.limit:
        bases = bases[:args.limit]

    for i, base in enumerate(bases, 1):
        if args.verbose and i % 200 == 0:
            print(f'  {i}/{len(bases)}...')
        if base not in off:
            continue
        mappings, queue, rep = match_base_code(
            base, off[base], cr.get(base, []), hasher, args.stage == 'phash',
        )
        all_mappings.update(mappings)
        all_queue.extend(queue)
        for r in (rep.get('assigned') or {}).values():
            rules[r.get('rule', '?')] += 1
        base_rules[rep.get('base_rule') or 'no_base_image'] += 1
        if queue or rep.get('note') or rep.get('orphans') or rep.get('foreign'):
            reports[base] = rep

    hasher.save()
    os.makedirs(OUT_DIR, exist_ok=True)
    atomic_write_json(os.path.join(OUT_DIR, 'mappings.json'), all_mappings, indent=2)
    atomic_write_json(os.path.join(OUT_DIR, 'queue.json'), all_queue, indent=2)

    stats = summarize(all_mappings, all_queue, reports, off, cr, rules, base_rules)
    atomic_write_json(os.path.join(OUT_DIR, 'report.json'),
                      {'stats': stats, 'codes': reports}, indent=2)
    print_stats(stats)

    if args.commit:
        commit_mappings(all_mappings)


def summarize(mappings, queue, reports, off, cr, rules, base_rules):
    queue_types = collections.Counter(q['type'] for q in queue)
    base_mapped = sum(1 for k in mappings if '_p' not in k)
    variant_mapped = sum(1 for k in mappings if '_p' in k)
    base_rule_buckets = collections.Counter()
    for k, v in base_rules.items():
        base_rule_buckets['mapped' if str(k).startswith('count=') else k] += v
    return {
        'total_mappings': len(mappings),
        'base_mappings': base_mapped,
        'variant_mappings': variant_mapped,
        'assignment_rules': dict(rules),
        'base_rules': dict(base_rule_buckets),
        'queue_total': len(queue),
        'queue_types': dict(queue_types),
        'codes_in_report': len(reports),
        'official_base_codes': len(off),
        'cardrush_base_codes': len(cr),
        'codes_official_without_cardrush': len(set(off) - set(cr)),
    }


def print_stats(s):
    print()
    print('=== remap stats ===')
    for k, v in s.items():
        print(f'  {k}: {v}')


def commit_mappings(mappings):
    """Replace mappings/confidence_mappings in card_price_overrides.json.

    manual_links.json (written by matcher/serve.py) has the shape
    {"links": {image_code: [pattern, ...]}, "resolved": [base_code, ...]};
    its links override deterministic assignments.  A legacy flat
    {image_code: [pattern, ...]} file is also accepted.
    """
    manual_path = os.path.join(SCRIPT_DIR, 'manual_links.json')
    final = dict(mappings)
    manual_links = {}
    if os.path.isfile(manual_path):
        with open(manual_path, encoding='utf-8') as f:
            manual = json.load(f)
        manual_links = manual.get('links', manual) if isinstance(manual, dict) else {}
        final.update(manual_links)

    if not os.path.isfile(OVERRIDES_JSON):
        raise SystemExit(f'ERROR: {OVERRIDES_JSON} not found')
    with open(OVERRIDES_JSON, encoding='utf-8') as f:
        overrides = json.load(f)
    overrides['mappings'] = final
    overrides['confidence_mappings'] = {}
    atomic_write_json(OVERRIDES_JSON, overrides, indent=2)
    print(f'Committed {len(final)} mappings '
          f'({len(mappings)} deterministic + {len(manual_links)} manual overrides) '
          f'to card_price_overrides.json')


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['text', 'phash'], default='phash')
    p.add_argument('--limit', type=int, default=0, help='only first N base codes')
    p.add_argument('--no-download', action='store_true',
                   help='use cached Cardrush images only')
    p.add_argument('--commit', action='store_true',
                   help='write results into card_price_overrides.json')
    p.add_argument('--verbose', action='store_true')
    return p.parse_args(argv)


if __name__ == '__main__':
    run(parse_args())

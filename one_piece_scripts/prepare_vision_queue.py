import os
import json
import re

# Load data
with open('one_piece_scripts/one_piece_cards.json', encoding='utf-8') as f:
    d_off = json.load(f)
with open('one_piece_scripts/cardrush_buying_prices.json', encoding='utf-8') as f:
    d_rush = json.load(f)

# Group official cards
off_groups = {}
for c in d_off:
    pic_url = c.get('Picture', '')
    m = re.search(r'([A-Z0-9]+-[0-9]+)(.*?)\.png', pic_url)
    if m:
        base = m.group(1)
        suffix = m.group(2)
        code = base + suffix
        if base not in off_groups: off_groups[base] = []
        off_groups[base].append({
            'code': code,
            'url': pic_url,
            'local': f'{code}.png'
        })

# Group rush cards
rush_groups = {}
for c in d_rush:
    base = c.get('model_number', '')
    if not base or base == '-': continue
    if base not in rush_groups: rush_groups[base] = []
    rush_groups[base].append({
        'name': c.get('name', ''),
        'url': c.get('image', ''),
        'local': c.get('image', '').split('/')[-1]
    })

# Find overlap
target_bases = {}
for base, off_cards in off_groups.items():
    if base in rush_groups and len(rush_groups[base]) > 1:
        # Check if local files actually exist for all cards to avoid agent errors
        all_off_exist = all(os.path.exists(f"one_piece_app/public/images/cards/{c['local']}") for c in off_cards)
        all_rush_exist = all(os.path.exists(f"one_piece_app/public/images/cards/{c['local']}") for c in rush_groups[base])
        if all_off_exist and all_rush_exist:
            target_bases[base] = {
                'official': off_cards,
                'cardrush': rush_groups[base]
            }

with open('one_piece_scripts/vision_queue.json', 'w', encoding='utf-8') as f:
    json.dump(target_bases, f, ensure_ascii=False, indent=2)

print(f"Dumped {len(target_bases)} batches into vision_queue.json")

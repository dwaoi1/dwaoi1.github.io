#!/usr/bin/env python3
"""Map ST cards to cardrush images."""
import json
import re
import os
from collections import defaultdict

# Read cardrush data
with open('one_piece_scripts/cardrush_buying_prices/2026-07/2026-07-16.json', 'r', encoding='utf-8') as f:
    cardrush_data = json.load(f)

# Read existing overrides
with open('one_piece_scripts/card_price_overrides.json', 'r', encoding='utf-8') as f:
    overrides = json.load(f)

# Get existing ST mappings
existing_mappings = {}
for key in overrides.get('mappings', {}):
    if key.startswith('ST'):
        existing_mappings[key] = overrides['mappings'][key]

# Get all ST cardrush entries
st_cardrush = defaultdict(list)
for item in cardrush_data:
    mn = item.get('model_number', '')
    base_mn = re.sub(r'\[.*?\]', '', mn)
    if base_mn.startswith('ST'):
        st_set = base_mn[:4]
        img_url = item.get('image', '')
        img_id = img_url.split('/')[-1].replace('.webp', '') if img_url else ''
        st_cardrush[st_set].append({
            'name': item.get('name', ''),
            'model_number': mn,
            'base_model': base_mn,
            'image': img_url,
            'img_id': img_id,
            'price': item.get('price', 0)
        })

# Get all ST official images
st_official = defaultdict(list)
cards_dir = 'one_piece_app/public/images/cards'
for filename in os.listdir(cards_dir):
    if filename.startswith('ST') and filename.endswith('.png'):
        match = re.match(r'(ST\d+-\d+)(?:_p\d+)?\.png', filename)
        if match:
            card_code = match.group(1)
            st_set = card_code[:4]
            st_official[st_set].append(filename)

# Create mapping data for each ST set
mapping_data = {}
for st_set in sorted(set(list(st_cardrush.keys()) + list(st_official.keys()))):
    # Group cardrush by base model
    cr_by_model = defaultdict(list)
    for entry in st_cardrush.get(st_set, []):
        cr_by_model[entry['base_model']].append(entry)
    
    # Group official by card code
    official_by_code = defaultdict(list)
    for f in st_official.get(st_set, []):
        match = re.match(r'(ST\d+-\d+)(?:_p\d+)?\.png', f)
        if match:
            official_by_code[match.group(1)].append(f)
    
    mapping_data[st_set] = {
        'cardrush_by_model': dict(cr_by_model),
        'official_by_code': dict(official_by_code),
        'existing': {k: v for k, v in existing_mappings.items() if k.startswith(st_set)}
    }

# Save mapping data
with open('one_piece_scripts/st_mapping_data.json', 'w', encoding='utf-8') as f:
    json.dump(mapping_data, f, ensure_ascii=False, indent=2)

print("Mapping data saved to one_piece_scripts/st_mapping_data.json")
print(f"Total ST sets: {len(mapping_data)}")
for st_set in sorted(mapping_data.keys()):
    data = mapping_data[st_set]
    print(f"{st_set}: {len(data['cardrush_by_model'])} cardrush models, {len(data['official_by_code'])} official codes, {len(data['existing'])} existing mappings")

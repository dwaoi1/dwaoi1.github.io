#!/usr/bin/env python3
"""Create initial ST card mappings based on model numbers and variant descriptions."""
import json
import re
from collections import defaultdict

# Read clean data
with open('one_piece_scripts/st_data_clean.json', 'r', encoding='utf-8') as f:
    st_data = json.load(f)

# Read existing overrides
with open('one_piece_scripts/card_price_overrides.json', 'r', encoding='utf-8') as f:
    overrides = json.load(f)

# Get existing ST mappings
existing_mappings = {}
for key in overrides.get('mappings', {}):
    if key.startswith('ST'):
        existing_mappings[key] = overrides['mappings'][key]

# Create mappings for each ST set
all_mappings = {}
uncertain_mappings = {}

for st_set in sorted(st_data.keys()):
    if st_set not in ['ST01', 'ST02', 'ST03', 'ST04', 'ST05', 'ST06', 'ST07']:
        continue
    
    cardrush_entries = st_data[st_set]['cardrush']
    official_images = st_data[st_set]['official']
    
    # Group cardrush by base model
    cr_by_model = defaultdict(list)
    for entry in cardrush_entries:
        cr_by_model[entry['base_model']].append(entry)
    
    # Group official by card code
    official_by_code = defaultdict(list)
    for img in official_images:
        match = re.match(r'(ST\d+-\d+)(?:_p\d+)?\.png', img)
        if match:
            official_by_code[match.group(1)].append(img)
    
    # Create mappings
    set_mappings = {}
    set_uncertain = []
    
    for card_code in sorted(official_by_code.keys()):
        cardrush_list = cr_by_model.get(card_code, [])
        
        if not cardrush_list:
            # No cardrush entries for this card
            continue
        
        # Get official images for this card
        official_imgs = official_by_code[card_code]
        
        # Try to match by variant type
        for entry in cardrush_list:
            name = entry['name']
            img_id = entry['img_id']
            img_url = entry['image']
            
            # Determine variant type from name
            variant = 'base'
            if '金文字' in name:
                variant = 'gold_text'
            elif 'foil' in name or '赤枠' in name:
                variant = 'foil'
            elif 'パラレル' in name:
                variant = 'parallel'
            elif 'フルアート' in name:
                variant = 'fullart'
            elif '漫画背景' in name:
                variant = 'manga_bg'
            elif '英語版' in name:
                variant = 'english'
            elif '中国版' in name:
                variant = 'chinese'
            elif '未開封' in name:
                variant = 'sealed'
            elif 'CS' in name:
                variant = 'championship'
            
            # Try to find matching official image
            target_code = card_code
            if variant == 'base':
                # Base card maps to image without _p suffix
                for img in official_imgs:
                    if img == f'{card_code}.png':
                        set_mappings[card_code] = [name, img_url]
                        break
            else:
                # Variant card maps to _p variant
                # For now, mark as uncertain
                set_uncertain.append({
                    'card_code': card_code,
                    'cardrush_name': name,
                    'cardrush_img_id': img_id,
                    'cardrush_img_url': img_url,
                    'variant': variant,
                    'official_imgs': official_imgs
                })
    
    all_mappings[st_set] = set_mappings
    uncertain_mappings[st_set] = set_uncertain

# Save results
output = {
    'all_mappings': all_mappings,
    'uncertain_mappings': uncertain_mappings,
    'existing_mappings': existing_mappings
}

with open('one_piece_scripts/st_initial_mappings.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# Print summary
print("Initial mappings created:")
for st_set in sorted(all_mappings.keys()):
    mapped = len(all_mappings[st_set])
    uncertain = len(uncertain_mappings[st_set])
    print(f"{st_set}: {mapped} mapped, {uncertain} uncertain")

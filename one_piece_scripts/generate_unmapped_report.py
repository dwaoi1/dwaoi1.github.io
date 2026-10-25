#!/usr/bin/env python3
"""Generate unmapped report for ST cards."""
import json
import re
from collections import defaultdict

# Read clean data
with open('one_piece_scripts/st_data_clean.json', 'r', encoding='utf-8') as f:
    st_data = json.load(f)

# Read current overrides
with open('one_piece_scripts/card_price_overrides.json', 'r', encoding='utf-8') as f:
    overrides = json.load(f)

# Get all ST mappings
st_mappings = {k: v for k, v in overrides.get('mappings', {}).items() if k.startswith('ST')}

# Generate unmapped report
report_lines = ["# Unmapped ST Card Rush Cards Report", ""]
report_lines.append(f"Generated: 2026-08-07")
report_lines.append(f"Total ST mappings: {len(st_mappings)}")
report_lines.append("")

# Group by ST set
for st_set in sorted(st_data.keys()):
    if not st_set.startswith('ST'):
        continue
    
    cardrush_entries = st_data[st_set]['cardrush']
    official_images = st_data[st_set]['official']
    
    # Find unmapped cardrush entries
    unmapped_cr = []
    for entry in cardrush_entries:
        # Check if this cardrush entry is mapped to any code
        is_mapped = False
        for code, mapping in st_mappings.items():
            if len(mapping) >= 2 and mapping[1] == entry['image']:
                is_mapped = True
                break
        if not is_mapped:
            unmapped_cr.append(entry)
    
    # Find unmapped official images
    unmapped_official = []
    for img in official_images:
        match = re.match(r'(ST\d+-\d+)(?:_p\d+)?\.png', img)
        if match:
            code = match.group(1)
            if code not in st_mappings:
                unmapped_official.append(img)
    
    if unmapped_cr or unmapped_official:
        report_lines.append(f"## {st_set}")
        report_lines.append(f"Cardrush entries: {len(cardrush_entries)}")
        report_lines.append(f"Official images: {len(official_images)}")
        report_lines.append(f"Mapped: {len(cardrush_entries) - len(unmapped_cr)}")
        report_lines.append(f"Unmapped cardrush: {len(unmapped_cr)}")
        report_lines.append(f"Unmapped official: {len(unmapped_official)}")
        report_lines.append("")
        
        if unmapped_cr:
            report_lines.append("### Unmapped Cardrush Entries:")
            for entry in unmapped_cr:
                report_lines.append(f"- {entry['name']} ({entry['model_number']}) -> {entry['img_id']}.webp")
            report_lines.append("")
        
        if unmapped_official:
            report_lines.append("### Unmapped Official Images:")
            for img in unmapped_official:
                report_lines.append(f"- {img}")
            report_lines.append("")

# Write report
with open('one_piece_scripts/unmapped_report.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print(f"Unmapped report generated: one_piece_scripts/unmapped_report.txt")
print(f"Total ST sets: {len([k for k in st_data.keys() if k.startswith('ST')])}")
print(f"Total ST mappings: {len(st_mappings)}")

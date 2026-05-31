import json
import os

with open('one_piece_scripts/vision_queue.json', 'r', encoding='utf-8') as f:
    queue = json.load(f)

# Take the first 50 codes
bases = list(queue.keys())[:50]
batches = [bases[i:i+10] for i in range(0, 50, 10)]

tasks = []
for batch_idx, batch in enumerate(batches):
    prompt = "I need you to map official One Piece card image codes to Cardrush image IDs based on visual artwork. Parallel cards (_p1, _p2) often have enlarged or borderless artwork.\n\n"
    
    for base in batch:
        data = queue[base]
        prompt += f"--- Base: {base} ---\n"
        prompt += "Official images:\n"
        for o in data['official']:
            prompt += f"- C:/Users/User/Desktop/dwaoi1.github.io/one_piece_app/public/images/cards/{o['local']} (Code: {o['code']})\n"
        prompt += "Cardrush images:\n"
        for r in data['cardrush']:
            prompt += f"- C:/Users/User/Desktop/dwaoi1.github.io/one_piece_app/public/images/cards/{r['local']} (ID: {r['local'].split('.')[0]})\n"
        prompt += "\n"
        
    prompt += "Your task:\n1. Use the 'read' tool to view these images.\n2. Visually match each official code to the correct Cardrush ID. If a Cardrush ID is missing for a variant, omit that variant.\n3. Output ONLY a raw JSON object containing the mappings for ALL cards in this batch. Example: {\"EB02-035\": \"7099\", \"EB02-035_p1\": \"7156\"}\n"
    
    tasks.append(prompt)

with open('one_piece_scripts/subagent_tasks.json', 'w', encoding='utf-8') as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

print(f"Generated {len(tasks)} tasks.")

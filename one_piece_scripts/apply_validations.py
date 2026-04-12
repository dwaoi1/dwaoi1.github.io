import json
import os
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OVERRIDES_JSON = os.path.join(SCRIPT_DIR, 'card_price_overrides.json')

def atomic_write_json(file_path, data, **kwargs):
    """Write data to a temporary file and rename it to file_path to ensure atomicity."""
    tmp_path = str(file_path) + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, **kwargs)
        os.replace(tmp_path, file_path)
    except Exception as exc:
        print(f'ERROR: Failed to write to {file_path}: {exc}')
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def main():
    url = 'https://firestore.googleapis.com/v1/projects/one-piece-card-game-index/databases/(default)/documents/price_matches/validations'
    
    print("Fetching validations from Firestore...")
    response = requests.get(url)
    if response.status_code != 200:
        if response.status_code == 404:
            print("No validations found in Firestore.")
            return
        print(f"Failed to fetch validations: {response.status_code} - {response.text}")
        return
        
    data = response.json()
    
    # Firestore REST API wraps maps in this specific structure
    matches = data.get('fields', {}).get('matches', {}).get('mapValue', {}).get('fields', {})
    
    incorrect_codes = []
    for code, value_obj in matches.items():
        status = value_obj.get('stringValue')
        if status == 'incorrect':
            incorrect_codes.append(code)
            
    if not incorrect_codes:
        print("No incorrect matches found to remove.")
        return
        
    print(f"Found {len(incorrect_codes)} cards marked as 'incorrect' in Firestore.")
    
    if not os.path.exists(OVERRIDES_JSON):
        print(f"Overrides file not found at {OVERRIDES_JSON}")
        return
        
    with open(OVERRIDES_JSON, 'r', encoding='utf-8') as f:
        overrides = json.load(f)
        
    mappings = overrides.get('mappings', {})
    confidence_mappings = overrides.get('confidence_mappings', {})
    
    removed_count = 0
    for code in incorrect_codes:
        if code in mappings:
            print(f"  Removing incorrect mapping: {code}")
            del mappings[code]
            removed_count += 1
        if code in confidence_mappings:
            del confidence_mappings[code]
            
    if removed_count > 0:
        overrides['mappings'] = mappings
        overrides['confidence_mappings'] = confidence_mappings
        # Use atomic writes as required by the project's GEMINI.md mandate
        atomic_write_json(OVERRIDES_JSON, overrides, indent=2)
        print(f"\nSuccessfully removed {removed_count} incorrect mappings from card_price_overrides.json.")
    else:
        print("\nAll incorrect mappings were already removed from the local overrides file.")

if __name__ == '__main__':
    main()

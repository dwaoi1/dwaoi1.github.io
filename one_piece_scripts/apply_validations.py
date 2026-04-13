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
    
    # Firestore REST API structure for maps
    matches_fields = data.get('fields', {}).get('matches', {}).get('mapValue', {}).get('fields', {})
    
    incorrect_codes = []
    correct_matches = {} # code -> status (we might want the actual match data if it was there, but for now we just know it's correct)
    
    # We also need to fetch the actual match data if we want to "harden" correct ones.
    # However, the 'validations' doc only stores the status. 
    # To truly sync 'correct' matches into overrides, we'd need the match info.
    # For now, let's focus on the user's immediate need and prune incorrect ones.
    
    for code, value_obj in matches_fields.items():
        status = value_obj.get('stringValue')
        if status == 'incorrect':
            incorrect_codes.append(code)
            
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
        atomic_write_json(OVERRIDES_JSON, overrides, indent=2)
        print(f"\nSuccessfully updated card_price_overrides.json.")
    else:
        print("\nNo local changes needed based on Firestore data.")

if __name__ == '__main__':
    main()

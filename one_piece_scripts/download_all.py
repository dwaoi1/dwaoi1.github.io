import os
import requests
import time

# List of Series IDs extracted from the official website
# (These correspond to OP-01, OP-02, Starters, etc.)
SERIES_IDS = [
    '556302', '556301', '556203', '556202', '556201', 
    '556114', '556113', '556112', '556111', '556110', 
    '556109', '556108', '556107', '556106', '556105', 
    '556104', '556103', '556102', '556101', '556029', 
    '556028', '556027', '556026', '556025', '556024', 
    '556023', '556022', '556021', '556020', '556019', 
    '556018', '556017', '556016', '556015', '556014', 
    '556013', '556012', '556011', '556010', '556009', 
    '556008', '556007', '556006', '556005', '556004', 
    '556003', '556002', '556001', '556701', '556901', 
    '556801'
]

URL = "https://asia-en.onepiece-cardgame.com/cardlist/"
OUTPUT_DIR = "html_files"

def download_series():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"Starting download of {len(SERIES_IDS)} card sets...")
    
    for s_id in SERIES_IDS:
        output_path = os.path.join(OUTPUT_DIR, f"series_{s_id}.html")
        
        # Skip if already downloaded
        if os.path.exists(output_path):
            print(f"Skipping {s_id} (already exists)")
            continue
            
        print(f"Downloading Series ID: {s_id}...")
        
        try:
            response = requests.post(URL, data={'series': s_id})
            if response.status_code == 200:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"  -> Saved to {output_path}")
            else:
                print(f"  -> Failed: Status {response.status_code}")
        except Exception as e:
            print(f"  -> Error: {e}")
            
        # Be nice to the server
        time.sleep(1)

if __name__ == "__main__":
    download_series()

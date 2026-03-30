import json
import os
import re
import requests
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from tqdm import tqdm

# Paths
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
CARDS_JSON = SCRIPT_DIR / 'one_piece_cards.json'
PRICE_OVERRIDES_JSON = SCRIPT_DIR / 'card_price_overrides.json'
LATEST_PRICES_JSON = SCRIPT_DIR / 'cardrush_buying_prices.json'
CACHE_DIR = SCRIPT_DIR / '.image_cache'

# Ensure cache dir exists
CACHE_DIR.mkdir(exist_ok=True)

def get_image_code(url: str) -> str:
    if not url: return ''
    m = re.search(r'/([A-Z]{2,}\d{2,}-\d{3}(?:_p\d*)?|[A-Z]-\d{3}(?:_p\d*)?)\.[^/]+(\?|$)', url)
    return m.group(1) if m else ''

def download_image(url: str) -> Optional[str]:
    if not url: return None
    name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', url.split('/')[-1])
    path = CACHE_DIR / name
    if path.exists():
        return str(path)
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(path, 'wb') as f:
            f.write(response.content)
        return str(path)
    except Exception:
        return None

def find_match_score(img1_path: str, img2_path: str) -> tuple[int, float]:
    """Compare two images using SIFT and RANSAC. Returns (inliers, confidence_percent)."""
    img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
    
    if img1 is None or img2 is None:
        return 0, 0.0

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    img1 = clahe.apply(img1)
    img2 = clahe.apply(img2)
    
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)
    
    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        return 0, 0.0
    
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    
    try:
        matches = flann.knnMatch(des1, des2, k=2)
    except:
        return 0, 0.0

    good_matches = []
    for match_pair in matches:
        if len(match_pair) == 2:
            m, n = match_pair
            if m.distance < 0.7 * n.distance:
                good_matches.append(m)
    
    if len(good_matches) > 10:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if mask is not None:
            inliers = int(np.sum(mask))
            confidence = (inliers / len(good_matches)) * 100
            return inliers, confidence
            
    return 0, 0.0

def match_worker(off_img_path, cr_entries_with_paths):
    """Worker function for parallel matching."""
    best_inliers = 0
    best_confidence = 0.0
    best_cr = None
    
    for cr_entry, cr_path in cr_entries_with_paths:
        if not cr_path: continue
        inliers, confidence = find_match_score(off_img_path, cr_path)
        if inliers > best_inliers:
            best_inliers = inliers
            best_confidence = confidence
            best_cr = cr_entry
            
    return best_inliers, best_confidence, best_cr

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
    if not LATEST_PRICES_JSON.exists():
        print("Prices not found. Run scraper first.")
        return

    load_success = True
    with open(LATEST_PRICES_JSON, 'r', encoding='utf-8') as f:
        cr_prices = json.load(f)
    with open(CARDS_JSON, 'r', encoding='utf-8') as f:
        official_cards = json.load(f)
    if PRICE_OVERRIDES_JSON.exists():
        try:
            with open(PRICE_OVERRIDES_JSON, 'r', encoding='utf-8') as f:
                overrides_data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"ERROR: Failed to load {PRICE_OVERRIDES_JSON}: {exc}")
            overrides_data = {}
            load_success = False
    else:
        overrides_data = {}
    
    if not load_success:
        print(f"SKIPPING write-back to {PRICE_OVERRIDES_JSON} to avoid data loss.")
        # We can still continue with matching if we want, but we won't save.
        # However, it's probably better to abort if we can't load the existing mappings.
        return

    mappings = overrides_data.get('mappings', {})
    confidence_mappings = overrides_data.get('confidence_mappings', {})
    
    # 1. Group Data
    official_by_code = {}
    for card in official_cards:
        code = re.search(r'/([A-Z]{2,}\d{2,}-\d{3}|[A-Z]-\d{3})', card['Picture'])
        if code:
            official_by_code.setdefault(code.group(1), []).append(card)

    def strip_bracket(m):
        match = re.match(r'^([A-Z]{2,3}\d{2}-\d{3}|[A-Z]-\d{3})', m)
        return match.group(1) if match else m
        
    cr_by_code = {}
    for p in cr_prices:
        code = strip_bracket(p['model_number'])
        cr_by_code.setdefault(code, []).append(p)

    # 2. Identify and Download required images
    urls_to_download = set()
    work_items = []
    
    for code, cr_entries in cr_by_code.items():
        if len(cr_entries) <= 1: continue
        off_entries = official_by_code.get(code, [])
        
        # Identify cards that need matching: 
        # - Either they are not in mappings yet
        # - Or they are mapped to a simple name (not a URL), which might be non-unique
        unmapped_off = []
        for off_card in off_entries:
            img_code = get_image_code(off_card['Picture'])
            current_mapping = mappings.get(img_code)
            
            needs_match = False
            if not current_mapping:
                needs_match = True
            elif isinstance(current_mapping, str) and not current_mapping.startswith('http'):
                # It's a name mapping. Check if this name is unique among cr_entries.
                # If multiple cr_entries have the same name, we should try to get a URL mapping instead.
                name_matches = [cr for cr in cr_entries if cr.get('name') == current_mapping]
                if len(name_matches) > 1:
                    needs_match = True
            
            if needs_match:
                unmapped_off.append(off_card)
        
        if not unmapped_off: continue
        
        for off_card in unmapped_off:
            urls_to_download.add(off_card['Picture'])
            for cr in cr_entries:
                if cr.get('image'): urls_to_download.add(cr['image'])
            work_items.append((code, off_card, cr_entries))

    if not work_items:
        print("No unmapped cards with multiple prices found.")
        return

    print(f"Downloading {len(urls_to_download)} unique images...")
    url_to_path = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(download_image, url): url for url in urls_to_download}
        for future in tqdm(as_completed(future_to_url), total=len(urls_to_download), desc="Downloading images"):
            url_to_path[future_to_url[future]] = future.result()

    # 3. Parallel Matching
    print(f"Starting parallel matching for {len(work_items)} cards...")
    matched_new = 0
    
    # Use ProcessPoolExecutor for CPU-bound SIFT matching
    with ProcessPoolExecutor() as executor:
        futures = []
        for code, off_card, cr_entries in work_items:
            off_path = url_to_path.get(off_card['Picture'])
            cr_entries_with_paths = [(cr, url_to_path.get(cr.get('image'))) for cr in cr_entries]
            
            img_code = get_image_code(off_card['Picture'])
            f = executor.submit(match_worker, off_path, cr_entries_with_paths)
            f.img_code = img_code
            futures.append(f)

        for future in tqdm(as_completed(futures), total=len(futures), desc="Matching cards"):
            inliers, confidence, best_cr = future.result()
            img_code = future.img_code
            
            if inliers >= 20: # Strong threshold
                # Store the Cardrush image URL instead of just the name if it's available.
                # This allows build_price_data.py to uniquely identify the entry even if 
                # multiple entries have the same name (common for different parallels).
                mapping_value = best_cr.get('image') or best_cr['name']
                print(f"  MATCH: {img_code} -> {mapping_value} ({confidence:.1f}%)")
                mappings[img_code] = mapping_value
                confidence_mappings[img_code] = round(confidence, 1)
                matched_new += 1
            else:
                # Optional: log if points were close
                if inliers > 5:
                    print(f"  Low confidence for {img_code} (Best: {confidence:.1f}%)")

    if matched_new > 0:
        overrides_data['mappings'] = mappings
        overrides_data['confidence_mappings'] = confidence_mappings
        atomic_write_json(PRICE_OVERRIDES_JSON, overrides_data, indent=2)
        print(f"\nAdded {matched_new} new mappings.")
    else:
        print("\nNo new matches found.")

if __name__ == "__main__":
    main()

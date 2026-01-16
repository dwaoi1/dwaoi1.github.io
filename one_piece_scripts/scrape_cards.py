import os
import glob
import json
from bs4 import BeautifulSoup

def scrape_card_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    cards_data = []

    # The cards seem to be contained in <dl class="modalCol"> elements
    card_elements = soup.find_all('dl', class_='modalCol')

    for card in card_elements:
        try:
            # Extract Character Name
            name_div = card.select_one('dt .cardName')
            character_name = name_div.get_text(strip=True) if name_div else "Unknown"

            # Extract Color
            # Color is inside a div with class 'color' inside 'backCol'
            color_div = card.select_one('.backCol .color')
            color = "Unknown"
            if color_div:
                # The text is like "ColorRed", "ColorGreen". We need to remove the "Color" label which is in an <h3>
                # Or just get the text of the div and remove "Color"
                # The structure is <div class="color"><h3>Color</h3>Red</div>
                # So getting text of the div will be "ColorRed". 
                # Better to get the text node after the h3 or just replace "Color"
                color_text = color_div.get_text(strip=True)
                if color_text.startswith("Color"):
                    color = color_text[5:] # Remove "Color" prefix
                else:
                    color = color_text

            # Extract Picture URL
            # Image is inside .frontCol > img
            img_tag = card.select_one('.frontCol img')
            picture_url = ""
            if img_tag:
                # Prefer data-src as src is often a dummy or placeholder
                if 'data-src' in img_tag.attrs:
                    picture_url = img_tag['data-src']
                elif 'src' in img_tag.attrs:
                    picture_url = img_tag['src']
            
            # Normalize path if it's relative
            if picture_url.startswith('..'):
                 # Assuming the base domain for relative paths. 
                 # The user might want the full URL. based on meta tags: https://asia-en.onepiece-cardgame.com/
                 # ../images... -> https://asia-en.onepiece-cardgame.com/images...
                 picture_url = picture_url.replace('..', 'https://asia-en.onepiece-cardgame.com')
            elif picture_url.startswith('/'):
                 picture_url = 'https://asia-en.onepiece-cardgame.com' + picture_url

            cards_data.append({
                "Character": character_name,
                "Color": color,
                "Picture": picture_url
            })

        except Exception as e:
            print(f"Error parsing a card: {e}")
            continue

    return cards_data

def main():
    # Look for all .html files in the current directory or a specific input directory
    # For this script, we'll look in the current directory where the script is run
    html_files = glob.glob("*.html")
    
    all_cards = []
    
    if not html_files:
        print("No HTML files found in the current directory.")
        # For testing purposes, we might want to allow specifying a path
        return

    print(f"Found {len(html_files)} HTML files. Processing...")

    for file_path in html_files:
        print(f"Reading {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            data = scrape_card_data(content)
            all_cards.extend(data)
            print(f"Extracted {len(data)} cards from {file_path}")

    # Deduplicate based on something unique if needed, e.g., Picture URL or Name+Color?
    # For now, we'll keep all entries.
    
    # Save directly to the React app's data file
    output_file = "../one_piece_app/src/data.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_cards, f, indent=2, ensure_ascii=False)
        print(f"Done. Saved {len(all_cards)} cards to {output_file}")
    except FileNotFoundError:
        # Fallback if the directory doesn't exist (e.g. running standalone)
        fallback_file = "one_piece_cards.json"
        print(f"Could not find {output_file}. Saving to {fallback_file} instead.")
        with open(fallback_file, 'w', encoding='utf-8') as f:
            json.dump(all_cards, f, indent=2, ensure_ascii=False)
        print(f"Done. Saved {len(all_cards)} cards to {fallback_file}")

if __name__ == "__main__":
    main()

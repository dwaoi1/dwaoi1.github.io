import os
import json
import base64
from google import genai
from google.genai import types
from io import BytesIO
from PIL import Image

def encode_image(img_path):
    # Try to compress the image if it's too large to save bandwidth, but retain quality
    try:
        with Image.open(img_path) as img:
            img.thumbnail((800, 800))
            buffer = BytesIO()
            # Convert webp to jpeg for better compatibility
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(buffer, format="JPEG", quality=85)
            return {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(buffer.getvalue()).decode("utf-8")
                }
            }
    except Exception as e:
        print(f"Error encoding {img_path}: {e}")
        return None

def process_vision_queue():
    # Attempt to load GEMINI_API_KEY from environment or from a local file if needed
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment!")
        return

    client = genai.Client(api_key=api_key)
    
    with open('one_piece_scripts/vision_queue.json', 'r', encoding='utf-8') as f:
        queue = json.load(f)

    print(f"Loaded {len(queue)} batches.")
    
    results = {}
    checkpoint_file = 'one_piece_scripts/vision_mappings_checkpoint.json'
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        print(f"Loaded {len(results)} previously mapped cards.")

    # Convert keys to list to process
    bases_to_process = [b for b in queue.keys() if b not in results]
    print(f"Need to process {len(bases_to_process)} batches.")

    # We will process a small batch first to make sure it works
    # Change the limit below to len(bases_to_process) to run all
    limit = 5
    bases_to_process = bases_to_process[:limit]

    system_instruction = """
    You are an expert One Piece Card Game authenticator.
    You will be given a set of official card images (labelled A1, A2, etc. with their codes) and a set of Cardrush store images (labelled B1, B2, etc. with their IDs).
    Your task is to match each official card code to its corresponding Cardrush ID based purely on the visual artwork.
    
    CRITICAL RULES:
    1. Base cards have borders. Parallel versions (e.g., _p1, _p2) often feature enlarged, borderless, or alternate artwork. Look very closely at the character's pose, the background, and whether there is a border.
    2. Cardrush might not have all the official variants. If an official card has no visual match among the Cardrush images provided, DO NOT map it.
    3. If multiple Cardrush images match the same official image (e.g. they are just duplicates on the site), map to the first one, or you can map both if you output a list, but we prefer just a single string ID.
    4. Output ONLY a valid JSON object where keys are the official card codes (like "OP01-029_p1") and values are the Cardrush IDs (like "4817").
    5. Do not include markdown formatting or any other text.
    """

    for i, base in enumerate(bases_to_process):
        print(f"Processing {i+1}/{len(bases_to_process)}: {base}")
        data = queue[base]
        
        contents = []
        off_text = "Official Images:\n"
        for idx, off in enumerate(data['official']):
            local_path = f"one_piece_app/public/images/cards/{off['local']}"
            img_data = encode_image(local_path)
            if img_data:
                off_text += f"A{idx+1}: {off['code']}\n"
                contents.append(img_data)
        
        rush_text = "Cardrush Images:\n"
        for idx, rush in enumerate(data['cardrush']):
            local_path = f"one_piece_app/public/images/cards/{rush['local']}"
            rush_id = rush['local'].split('.')[0]
            img_data = encode_image(local_path)
            if img_data:
                rush_text += f"B{idx+1}: {rush_id}\n"
                contents.append(img_data)
                
        prompt_text = off_text + "\n" + rush_text + "\nPlease provide the JSON mapping."
        contents.insert(0, prompt_text)
        
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            
            mapping = json.loads(response.text)
            print(f"  Result: {mapping}")
            
            # Save to results
            results[base] = mapping
            
            # Save checkpoint
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"  Failed on {base}: {e}")
            
    print("Batch complete.")

if __name__ == "__main__":
    process_vision_queue()

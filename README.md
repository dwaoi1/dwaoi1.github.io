# One Piece Card Game Indexer

This is a simple tool to index and display One Piece trading cards.

## How to Update the Website (Step-by-Step)

We have two ways to update the cards: **Automatic** (Recommended) or **Manual**.

### Option A: Automatic Download (Easiest)
This script will automatically download all known card sets from the website.

1. Open your terminal.
2. Navigate to the scripts folder:
   ```bash
   cd one_piece_scripts
   ```
3. Install the requirements (only need to do this once):
   ```bash
   pip install -r requirements.txt
   ```
4. Run the downloader:
   ```bash
   python3 download_all.py
   ```
   - This will take a minute to download all the HTML files into a folder named `html_files`.
5. Run the extractor:
   ```bash
   python3 scrape_cards.py
   ```
   - This reads all the downloaded files and updates the website data.

### Option B: Manual Save (If automatic fails)
If specific cards are missing or you want to save a specific page manually:

1. Go to the [Official One Piece Card List](https://asia-en.onepiece-cardgame.com/cardlist/).
2. Select the "Series" you want from the dropdown and click Search.
3. Right-click anywhere on the page and select **"Save As..."**.
4. Save the file into the `one_piece_scripts` folder.
5. Run `python3 scrape_cards.py`.

### Final Step: Update the Website
1. Go to the app folder:
   ```bash
   cd ../one_piece_app
   ```
2. Deploy the changes:
   ```bash
   npm run deploy
   ```

---
**Website Link:** https://dwaoi1.github.io/
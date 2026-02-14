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
   - This reads all the downloaded files and updates `one_piece_scripts/one_piece_cards.json` (used at build time).

### Option B: Manual Save (If automatic fails)
If specific cards are missing or you want to save a specific page manually:

1. Go to the [Official One Piece Card List](https://asia-en.onepiece-cardgame.com/cardlist/).
2. Select the "Series" you want from the dropdown and click Search.
3. Right-click anywhere on the page and select **"Save As..."**.
4. Save the file into the `one_piece_scripts` folder.
5. Run `python3 scrape_cards.py`.

### Final Step: Update the Website
1. Commit and push your changes to `main`.
2. GitHub Actions will automatically build and deploy the site to GitHub Pages.

### Wishlist Export + Shared Wishlist
The app loads `one_piece_app/public/wishlist.json` first (shared wishlist) and falls back to the
browser's local wishlist if the shared file is missing. Use the "Download wishlist JSON" button
to export your local edits, then replace `one_piece_app/public/wishlist.json` with that file and
commit + push to share the wishlist with everyone.

---
**Website Link:** https://dwaoi1.github.io/

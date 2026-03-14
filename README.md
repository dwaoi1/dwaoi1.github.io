# One Piece Card Game Indexer

A web app for browsing, tracking, and pricing One Piece trading cards.

**Live site:** https://dwaoi1.github.io/

## Features

- **Card browser** — search, filter by character / color / series, and sort your collection
- **Wishlist** — mark cards with a ❤️ and export / import your list as JSON; a shared wishlist committed to the repo is loaded automatically
- **Price history** — Cardrush buying-price charts for every card, updated daily via GitHub Actions
  - Separate price tracking for base, sealed (未開封), gold-text (金文字), and parallel (パラレル) variants
  - Parallel cards with no buying-price data clearly show "No price data available" instead of the base-card price
- **PWA-ready** — installable on mobile / desktop

---

## Repository Structure

```
dwaoi1.github.io/
├── one_piece_app/          # React front-end (Create React App)
│   ├── public/
│   │   ├── cards.json                    # Compiled card list (built from one_piece_cards.json)
│   │   ├── cardrush_price_history.json   # Daily buying prices per card
│   │   └── wishlist.json                 # Shared wishlist (committed to repo)
│   └── src/
│       ├── App.js
│       └── components/
│           ├── CardTable.js    # Card grid with filters, wishlist, and pagination
│           └── PriceModal.js   # Price-history chart modal
├── one_piece_scripts/      # Python data-pipeline scripts
│   ├── download_all.py                   # Downloads card HTML from the official site
│   ├── scrape_cards.py                   # Parses HTML → one_piece_cards.json
│   ├── scrape_cardrush_buying_prices.py  # Scrapes daily buying prices from Cardrush
│   ├── build_price_data.py               # Compiles daily JSONs → cardrush_price_history.json
│   ├── one_piece_cards.json              # Source card data (Japanese names + image URLs)
│   └── cardrush_buying_prices/           # Raw daily price snapshots (one file per day)
└── .github/workflows/      # CI/CD
    └── scrape-cardrush.yml               # Daily price scrape + site deploy
```

---

## How to Update the Card List

### Option A: Automatic Download (Recommended)

1. Open your terminal and navigate to the scripts folder:
   ```bash
   cd one_piece_scripts
   ```
2. Install Python dependencies (only needed once):
   ```bash
   pip install -r requirements.txt
   ```
3. Download all card pages from the official site:
   ```bash
   python3 download_all.py
   ```
   HTML files are saved into `html_files/`.
4. Parse the downloaded pages into the card data file:
   ```bash
   python3 scrape_cards.py
   ```
   This updates `one_piece_scripts/one_piece_cards.json`.

### Option B: Manual Save (If automatic fails)

1. Go to the [Official One Piece Card List](https://asia-en.onepiece-cardgame.com/cardlist/).
2. Select the series you want from the dropdown and click **Search**.
3. Right-click the page and choose **Save As…**, saving into `one_piece_scripts/`.
4. Run `python3 scrape_cards.py`.

### Deploying the Updated Site

Commit and push your changes to `main`.  
GitHub Actions will automatically build and deploy to GitHub Pages.

---

## How to Update Buying Prices (Manual)

```bash
cd one_piece_scripts
python3 scrape_cardrush_buying_prices.py   # saves today's prices to cardrush_buying_prices/
python3 build_price_data.py                # recompiles cardrush_price_history.json
```

Prices are also updated automatically every day by the `scrape-cardrush` workflow.

---

## Wishlist Export + Shared Wishlist

The app loads `one_piece_app/public/wishlist.json` on startup (shared wishlist) and falls back to
the browser's local storage if the file is missing.

To share your wishlist with everyone:
1. Click **Download wishlist JSON** in the app.
2. Replace `one_piece_app/public/wishlist.json` with the downloaded file.
3. Commit and push to `main`.

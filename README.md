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


## Wishlist Export + Shared Wishlist

The app loads `one_piece_app/public/wishlist.json` on startup (shared wishlist) and falls back to
the browser's local storage if the file is missing.

To share your wishlist with everyone:
1. Click **Download wishlist JSON** in the app.
2. Replace `one_piece_app/public/wishlist.json` with the downloaded file.
3. Commit and push to `main`.

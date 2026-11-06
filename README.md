# One Piece Card Game Tracker

A web app for browsing and tracking One Piece trading card prices.

**Live Site:** [https://dwaoi1.github.io/](https://dwaoi1.github.io/)

## Repository Structure

```text
dwaoi1.github.io/
├── one_piece_app/              # React 19 frontend (Create React App)
│   ├── src/
│   │   ├── components/
│   │   │   ├── CardTable.js    # Main grid, wishlist, image loading
│   │   │   ├── PriceModal.js   # SVG price history charts
│   │   │   └── PriceMatching.js # Human validation interface
│   │   ├── utils/imageUtils.js # Proxy URL & srcset helpers
│   │   ├── service-worker.js   # Workbox caching strategies
│   │   └── firebase.js         # Firebase/Firestore configuration
│   └── public/                 # cards.json, cardrush_price_history.json, images/cards/
├── one_piece_scripts/          # Python data pipeline
│   ├── download_all.py         # Official card list & image scraper
│   ├── scrape_cardrush_buying_prices.py # Cardrush buying price scraper
│   ├── build_price_data.py     # Snapshot aggregation, variant history, overrides
│   ├── apply_validations.py    # Pulls human validations from Firestore
│   ├── card_price_overrides.json # Manual mappings + auto-generated diagnostics
│   └── cardrush_buying_prices/ # Raw snapshots (YYYY-MM/YYYY-MM-DD.json)
├── .github/workflows/
│   ├── scrape-cardrush.yml     # Twice-daily scrape → build → commit → deploy
│   ├── scrape-cardlist.yml     # Manual official card list & image scrape
│   └── deploy.yml              # Frontend build & GitHub Pages deploy
└── gh-pages/                   # Static assets copied into the build
```

## Data Lifecycle

1. **Ingestion:** `scrape-cardrush.yml` runs at 02:22 and 13:22 UTC. It skips the scrape when today's snapshot already exists and parses as valid JSON, and uses `curl_cffi` with a proxy to reach Cardrush.
2. **Metadata:** `download_all.py` pulls official card data and images from onepiece-cardgame.com into `one_piece_scripts/one_piece_cards.json` and `one_piece_app/public/images/cards/`.
3. **Processing:** `build_price_data.py` aggregates snapshots into `one_piece_app/public/cardrush_price_history.json`, generating `_p` variant entries automatically and applying `card_price_overrides.json` mappings for ambiguous listings.
4. **Validation:** Unmatched listings can be corrected through the `PriceMatching` interface, which writes to Firestore; `apply_validations.py` pulls those decisions back into the overrides file.
5. **Deployment:** Each scrape commits its snapshot, compiled history, and overrides, then triggers `deploy.yml`, which builds the app and publishes it to GitHub Pages.

## Local Development

```bash
# Frontend
cd one_piece_app && npm ci && npm start

# Data pipeline
pip install -r one_piece_scripts/requirements.txt
```

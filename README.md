# One Piece Card Game Tracker

A comprehensive web application for browsing, tracking, and analyzing One Piece trading card prices.

**Live Site:** [https://dwaoi1.github.io/](https://dwaoi1.github.io/)

## Key Features

- **Advanced Card Browser:** Search and filter the entire card catalog by character, color, series, and rarity.
- **Real-time Shared Wishlist:** A global wishlist synchronized via Firebase Firestore. Track high-value cards collectively across devices.
- **Market Price History:** Detailed daily buying-price charts from Cardrush, updated every 3 hours.
  - Distinct tracking for base, sealed (未開封), gold-text (金文字), and parallel (パラレル) variants.
  - Clear "No price data" indicators for variants without active market listings.
- **Data Accuracy:** High-precision mapping using a hybrid of manual overrides and computer-vision (SIFT/OCR) matching.
- **PWA Support:** Installable on mobile and desktop for quick access.

## Repository Structure

```text
dwaoi1.github.io/
├── one_piece_app/          # React 19 Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── CardTable.js    # Main grid & Firestore wishlist logic
│   │   │   ├── PriceModal.js   # SVG-based price history charts
│   │   │   └── PriceMatching.js # Match validation interface
│   │   └── firebase.js         # Firebase/Firestore configuration
│   └── public/                 # Static assets and build targets
├── one_piece_scripts/      # Python Data Pipeline
│   ├── download_all.py         # Official card list scraper
│   ├── scrape_cardrush_buying_prices.py # Daily price scraper
│   ├── build_price_data.py     # Aggregator & core processing logic
│   ├── visual_match.py         # CV-based automated card mapping
│   └── apply_validations.py    # Syncs human validations from Firestore
├── .github/workflows/      # CI/CD & Automation
│   ├── scrape-cardrush.yml     # 3-hourly scraping & update job
│   └── deploy.yml              # Frontend build & deployment
├── cards.json              # Canonical card metadata
└── cardrush_price_history.json # Compiled historical price data
```

## Data Lifecycle

1. **Ingestion:** Prices are scraped from Cardrush every 3 hours using `curl_cffi` to ensure reliable access.
2. **Metadata:** Official card data and images are sourced directly from onepiece-cardgame.com.
3. **Processing:** `build_price_data.py` aggregates snapshots into a chronological history, applying `card_price_overrides.json` to resolve ambiguous listings.
4. **Validation:** New cards are automatically mapped via visual similarity; discrepancies can be corrected via the `PriceMatching` interface in the app, which feeds back into the pipeline via Firestore.
5. **Deployment:** Validated data is committed back to the repository and deployed to GitHub Pages.

## Mandates & Standards

This project adheres to strict data integrity and performance mandates (see `GEMINI.md` for full details):
- **Atomic Writes:** All data updates use a safe write-then-replace pattern to prevent corruption.
- **Image Proxying:** Official images are proxied via `wsrv.nl` with robust fallback chains to ensure availability.
- **Safe UI:** Optional chaining and null-safe rendering are mandatory for all data-driven components.

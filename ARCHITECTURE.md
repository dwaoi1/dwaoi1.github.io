# Architecture & Standards - One Piece Card Tracker

This document defines the foundational mandates and technical standards for the One Piece Card Tracker project. These rules take precedence over general workflows.

## Data Safety & Integrity

### Atomic Writes
- **Mandate:** All scripts that modify critical JSON data files (e.g., `card_price_overrides.json`, `one_piece_app/public/cardrush_price_history.json`, `one_piece_cards.json`) **MUST** use atomic write patterns.
- **Pattern:** Write the new data to a temporary file (e.g., `.tmp`) and then use `os.replace` (Python) or equivalent to overwrite the destination. This prevents file truncation or corruption if the script is interrupted.
- **Reference:** See `atomic_write_json` in `one_piece_scripts/build_price_data.py`.

### Load-Failure Protection
- **Mandate:** If a script fails to load a JSON file that it intends to update in-place, it **MUST** abort the write-back process immediately.
- **Rationale:** Failing to load an existing file (due to syntax errors, merge conflicts, or disk issues) and then proceeding to write will cause the loss of all pre-existing manual mappings or history.

### Firestore Security Rules
- **Mandate:** All Firestore access **MUST** be restricted to the specific documents used by the application (`wishlists/global`, `price_matches/validations`).
- **Mandate:** Security rules must include schema validation (e.g., checking field types and list/map sizes) to prevent database pollution.
- **Mandate:** Any new features requiring Firestore storage **MUST** have corresponding specific rules added for the documents they touch. Note that `firestore.rules` is gitignored: the live rules deployed to the Firebase project are the source of truth and are not versioned in this repository.

## Frontend Standards

### Image Loading: Proxying, Fallbacks, Responsiveness
- **Mandate:** Images sourced from official domains (e.g., `onepiece-cardgame.com` and its subdomains) **MUST** be proxied via `wsrv.nl` (primary) or `images.weserv.nl` (fallback). Build these URLs with `one_piece_app/src/utils/imageUtils.js` (`getProxiedImageUrl`, `getProxiedImageSrcset`) rather than assembling query strings inline.
- **Mandate:** All card images **MUST** implement the established fallback chain in their `onError` handler: wsrv.nl proxy → local `${PUBLIC_URL}/images/cards/<cardId>` → `cardrushImage` field from the price history data → `images.weserv.nl` proxy → `placehold.co` placeholder. See `CardTable.js` for the reference implementation.
- **Mandate:** Card images **MUST** ship responsive sources: `srcSet` from `getProxiedImageSrcset` (150/300/600 widths) with matching `sizes`, plus `loading="lazy"`, `decoding="async"`, and `referrerPolicy="no-referrer"`.
- **Mandate:** Keep the blur-up placeholder pattern: render the `<img>` with `data-blur`, set `data-loaded` on load, and let the existing `img[data-blur]` CSS clear the blur. New image components must follow the same attributes so the shared CSS applies.
- **Mandate:** **DO NOT** use `crossOrigin="anonymous"` on images from official domains, as it can trigger CORS/CORP blocking even through proxies.
- **Mandate:** All new components (e.g., modals) displaying images **MUST** re-use `imageUtils.js` and the shared fallback chain. Direct image loading from official domains is strictly prohibited.
- **Mandate:** To optimize performance, reuse URLs already used by the main grid in other components like modals, instead of generating new proxied URLs with different parameters, so browser and Service Worker caches stay warm.

### Caching (Service Worker)
- **Mandate:** Caching rules live in `one_piece_app/src/service-worker.js` (Workbox): stale-while-revalidate for `wsrv.nl` / `images.weserv.nl`, cache-first for `/images/cards/`, `files.cardrush.media` and `placehold.co`, network-first for `.json` payloads and navigations.
- **Mandate:** New cache routes **MUST** be added there with a `cacheWillUpdate` guard that only caches `200` responses, and must be named distinctly so they can be invalidated independently.
- **Mandate:** The worker is registered from `src/index.js` via `serviceWorkerRegistration.register()`. Cached-asset changes depend on `self.skipWaiting()` plus `cleanupOutdatedCaches()` to drop stale caches; do not remove either.
- **Mandate:** UI state that must survive Service-Worker-served pages (e.g., the price time range) is persisted in `localStorage`.

## Safe UI Component Implementation
- **Mandate:** Always guard array lookups and async state with null checks (optional chaining, guarded `useMemo`, `try-catch`).

## CI/CD & Build
- **`scrape-cardrush.yml`** (cron `22 2,13 * * *` UTC, plus manual dispatch): sparse checkout, skips the scrape when today's snapshot exists and parses as valid JSON, commits the snapshot, `one_piece_app/public/cardrush_price_history.json`, and `one_piece_scripts/card_price_overrides.json`, then triggers `deploy.yml`.
- **`scrape-cardlist.yml`** (manual only): refreshes `one_piece_scripts/one_piece_cards.json` and `one_piece_app/public/images/cards/`, then triggers `deploy.yml`.
- **`deploy.yml`** (push/PR to `main`, manual): copies `one_piece_scripts/one_piece_cards.json` to `public/cards.json` and `card_price_overrides.json` to `public/unmatched_prices.json`, copies the static assets in `gh-pages/`, removes any raw `public/cardrush_buying_prices/` directory, and builds with `PUBLIC_URL="."` for pull requests or `PUBLIC_URL="https://dwaoi1.github.io/"` otherwise.
- Raw snapshots under `one_piece_scripts/cardrush_buying_prices/` are excluded from both the Pages artifact and the deploy trigger paths; only the compiled history ships.

## Maintenance Guidelines

### Card Price Overrides
- `one_piece_scripts/card_price_overrides.json` is a hybrid file containing both manual mappings (critical) and auto-generated diagnostics (rebuildable).
- Always verify the integrity of the `mappings` section before committing changes.
- Avoid manual edits to the `multiplePrices` or `pricesWithoutCards` sections, as these are overwritten by `build_price_data.py`.

### Date Handling & Scraper Structure
- **Storage:** Cardrush buying price JSON files are stored in `one_piece_scripts/cardrush_buying_prices/YYYY-MM/YYYY-MM-DD.json`.
- **Formatting:** Dates displayed in the UI (charts, as-of labels) **MUST** use the numeric `YYYY/MM/DD` format (no month names like "Jan" or "Feb").

## Scraping Traffic: Looking Less Bot-Like

### Environment note
Standard HTTP request libraries (like Python's default requests) often return 403 Forbidden at the proxy/WAF layer (e.g., AWS WAF, Cloudflare) during research attempts. This is usually due to TLS and HTTP/2 fingerprinting rather than IP blocking.

### Practical guidance
1. Spoof TLS and HTTP/2 Fingerprints: Modern WAFs analyze the cryptographic handshake (JA3/JA4 fingerprinting). Standard HTTP libraries use OpenSSL, which has a distinct bot signature. Use TLS-impersonation libraries (like curl_cffi) to mimic a real browser's network signature.
2. Keep UA, headers, and TLS strictly consistent: Do not randomly rotate User-Agents if you are spoofing a specific TLS fingerprint. If your TLS fingerprint mimics Chrome 124, your User-Agent and sec-ch-ua headers must strictly match Windows/Mac Chrome 124. Mismatches trigger instant blocks.
3. Send a modern, realistic header set: Don't just send User-Agent. You must include modern Chromium-family headers that real browsers send:
   - Accept, Accept-Language, Accept-Encoding
   - sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform
   - sec-fetch-dest, sec-fetch-mode, sec-fetch-site
4. Persist sessions (cookies): Load the homepage or base domain first so your session establishes tracking cookies, making your request chain look like a legitimate user journey instead of stateless API hits.
5. Use human pacing: Add random jitter between requests, bound your concurrency, and implement exponential backoff on 403, 429, or 503 errors.
6. Avoid impossible navigation patterns: Don't fetch deep pagination or hidden API endpoints without first establishing a session on the parent listing pages.


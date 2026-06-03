# Architecture & Standards - One Piece Card Tracker

This document defines the foundational mandates and technical standards for the One Piece Card Tracker project. These rules take precedence over general workflows.

## Data Safety & Integrity

### Atomic Writes
- **Mandate:** All scripts that modify critical JSON data files (e.g., `card_price_overrides.json`, `cardrush_price_history.json`, `cards.json`) **MUST** use atomic write patterns.
- **Pattern:** Write the new data to a temporary file (e.g., `.tmp`) and then use `os.replace` (Python) or equivalent to overwrite the destination. This prevents file truncation or corruption if the script is interrupted.
- **Reference:** See `atomic_write_json` in `one_piece_scripts/build_price_data.py`.

### Load-Failure Protection
- **Mandate:** If a script fails to load a JSON file that it intends to update in-place, it **MUST** abort the write-back process immediately.
- **Rationale:** Failing to load an existing file (due to syntax errors, merge conflicts, or disk issues) and then proceeding to write will cause the loss of all pre-existing manual mappings or history.

### Firestore Security Rules
- **Mandate:** All Firestore access **MUST** be restricted to the specific documents used by the application (`wishlists/global`, `price_matches/validations`).
- **Mandate:** Security rules must include schema validation (e.g., checking field types and list/map sizes) to prevent database pollution.
- **Mandate:** Any new features requiring Firestore storage **MUST** have corresponding specific rules added to `firestore.rules`.

## Frontend Standards

### Image Proxying & Fallbacks
- **Mandate:** Images sourced from official domains (e.g., `onepiece-cardgame.com` and its subdomains) **MUST** be proxied via `wsrv.nl` or `images.weserv.nl`.
- **Mandate:** All card images **MUST** implement a fallback chain that includes the `cardrushImage` field from the price history data if the official/proxied image fails to load.
- **Mandate:** **DO NOT** use `crossOrigin="anonymous"` on images from official domains, as it can trigger CORS/CORP blocking even through proxies.
- **Mandate:** All new components (e.g., modals) displaying images **MUST** re-use established proxy and fallback patterns. Direct image loading from official domains is strictly prohibited.
- **Mandate:** To optimize performance, images should leverage browser caching by reusing URLs from the main grid in other components like modals, instead of generating new proxied URLs with different parameters.

## Safe UI Component Implementation
- **Mandate:** Always guard array lookups and async state with null checks (optional chaining, guarded `useMemo`, `try-catch`).

## Maintenance Guidelines

### Card Price Overrides
- `one_piece_scripts/card_price_overrides.json` is a hybrid file containing both manual mappings (critical) and auto-generated diagnostics (rebuildable).
- Always verify the integrity of the `mappings` section before committing changes.
- Avoid manual edits to the `multiplePrices` or `pricesWithoutCards` sections, as these are overwritten by `build_price_data.py`.

### Date Handling & Scraper Structure
- **Storage:** Cardrush buying price JSON files are stored in `one_piece_scripts/cardrush_buying_prices/YYYY-MM/YYYY-MM-DD.json`.
- **Formatting:** Dates displayed in the UI (charts, as-of labels) **MUST** use the numeric `YYYY/MM/DD` format (no month names like "Jan" or "Feb").
## Making scraping traffic look less bot-like (practical guidance)

## Environment note
Standard HTTP request libraries (like Python's default requests) often return 403 Forbidden at the proxy/WAF layer (e.g., AWS WAF, Cloudflare) during research attempts. This is usually due to TLS and HTTP/2 fingerprinting rather than IP blocking.

## Practical guidance
1. Spoof TLS and HTTP/2 Fingerprints: Modern WAFs analyze the cryptographic handshake (JA3/JA4 fingerprinting). Standard HTTP libraries use OpenSSL, which has a distinct bot signature. Use TLS-impersonation libraries (like curl_cffi) to mimic a real browser's network signature.
2. Keep UA, headers, and TLS strictly consistent: Do not randomly rotate User-Agents if you are spoofing a specific TLS fingerprint. If your TLS fingerprint mimics Chrome 124, your User-Agent and sec-ch-ua headers must strictly match Windows/Mac Chrome 124. Mismatches trigger instant blocks.
3. Send a modern, realistic header set: Don't just send User-Agent. You must include modern Chromium-family headers that real browsers send:
   - Accept, Accept-Language, Accept-Encoding
   - sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform
   - sec-fetch-dest, sec-fetch-mode, sec-fetch-site
4. Persist sessions (cookies): Load the homepage or base domain first so your session establishes tracking cookies, making your request chain look like a legitimate user journey instead of stateless API hits.
5. Use human pacing: Add random jitter between requests, bound your concurrency, and implement exponential backoff on 403, 429, or 503 errors.
6. Avoid impossible navigation patterns: Don't fetch deep pagination or hidden API endpoints without first establishing a session on the parent listing pages.


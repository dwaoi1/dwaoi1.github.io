# Gemini Mandates - One Piece Card Tracker

This document defines the foundational mandates and technical standards for the One Piece Card Tracker project. These rules take precedence over general workflows.

## Data Safety & Integrity

### Atomic Writes
- **Mandate:** All scripts that modify critical JSON data files (e.g., `card_price_overrides.json`, `cardrush_price_history.json`, `cards.json`) **MUST** use atomic write patterns.
- **Pattern:** Write the new data to a temporary file (e.g., `.tmp`) and then use `os.replace` (Python) or equivalent to overwrite the destination. This prevents file truncation or corruption if the script is interrupted.
- **Reference:** See `atomic_write_json` in `one_piece_scripts/build_price_data.py`.

### Load-Failure Protection
- **Mandate:** If a script fails to load a JSON file that it intends to update in-place, it **MUST** abort the write-back process immediately.
- **Rationale:** Failing to load an existing file (due to syntax errors, merge conflicts, or disk issues) and then proceeding to write will cause the loss of all pre-existing manual mappings or history.

## Frontend Standards

### Image Proxying & Fallbacks
- **Mandate:** Images sourced from official domains (e.g., `onepiece-cardgame.com` and its subdomains) **MUST** be proxied via `wsrv.nl` or `images.weserv.nl`.
- **Mandate:** All card images **MUST** implement a fallback chain that includes the `cardrushImage` field from the price history data if the official/proxied image fails to load.
- **Mandate:** **DO NOT** use `crossOrigin="anonymous"` on images from official domains, as it can trigger CORS/CORP blocking even through proxies.
- **Mandate:** All new components (e.g., modals) displaying images **MUST** re-use established proxy and fallback patterns. Direct image loading from official domains is strictly prohibited.
- **Mandate:** To optimize performance, images should leverage browser caching by reusing URLs from the main grid in other components like modals, instead of generating new proxied URLs with different parameters.

### Frontend Performance Standards
- **Mandate:** New features must maintain parity with existing performance levels.
- **Mandate:** Avoid adding heavy state dependencies or excessive re-renders when implementing interactive components like modals or data-analysis grids.
- **Mandate:** Test image loading after every feature implementation to ensure established proxy and fallback behaviors are not disrupted.


## Maintenance Guidelines

### Card Price Overrides
- `one_piece_scripts/card_price_overrides.json` is a hybrid file containing both manual mappings (critical) and auto-generated diagnostics (rebuildable).
- Always verify the integrity of the `mappings` section before committing changes.
- Avoid manual edits to the `multiplePrices` or `pricesWithoutCards` sections, as these are overwritten by `build_price_data.py`.

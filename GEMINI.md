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

### Image Proxying
- **Mandate:** Images sourced from official domains (e.g., `onepiece-cardgame.com` and its subdomains) **MUST** be proxied via `wsrv.nl` (or a similar service) to bypass hotlink protection.
- **Pattern:**
  ```javascript
  const proxiedUrl = `https://wsrv.nl/?url=${encodeURIComponent(originalUrl.split('?')[0])}&output=webp&default=https://via.placeholder.com/150?text=No+Image`;
  ```
- **Rationale:** Direct requests to official image servers often result in 403 Forbidden or broken images in a web browser environment.

## Maintenance Guidelines

### Card Price Overrides
- `one_piece_scripts/card_price_overrides.json` is a hybrid file containing both manual mappings (critical) and auto-generated diagnostics (rebuildable).
- Always verify the integrity of the `mappings` section before committing changes.
- Avoid manual edits to the `multiplePrices` or `pricesWithoutCards` sections, as these are overwritten by `build_price_data.py`.

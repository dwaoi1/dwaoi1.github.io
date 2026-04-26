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

## Safe UI Component Implementation
- **Mandate:** When adding new interactive components (modals, dropdowns) with local state, **MUST** use optional chaining and null-safe rendering to prevent runtime crashes.
- **Mandate:** **NEVER** perform expensive or data-dependent operations (like `find` in arrays) within `useMemo` without checking if the dependencies (`cardData`, `priceHistory`) are fully loaded and defined.
- **Pattern:**
  ```javascript
  // BAD: May crash if data is empty
  const match = cardData.find(c => ...); 
  
  // GOOD: Guarded lookup
  const match = useMemo(() => {
    if (!cardData || cardData.length === 0) return null;
    return cardData.find(c => ...);
  }, [cardData]);
  ```
- **Mandate:** Always verify that state updates do not trigger side effects that could disrupt parent components or global UI navigation.
- **Mandate:** Use `try-catch` blocks and `finally` blocks for all async data fetching to ensure state is properly initialized and errors are handled gracefully without blocking the rest of the application.



## Maintenance Guidelines

### Card Price Overrides
- `one_piece_scripts/card_price_overrides.json` is a hybrid file containing both manual mappings (critical) and auto-generated diagnostics (rebuildable).
- Always verify the integrity of the `mappings` section before committing changes.
- Avoid manual edits to the `multiplePrices` or `pricesWithoutCards` sections, as these are overwritten by `build_price_data.py`.

### UI Layout: Heart Icon
- **Location:** The wishlist heart icon is contained within `.heart-wrapper` in `CardTable.js` and styled in `CardTable.css`.
- **Adaptiveness:** The icon uses **flexbox-based relative positioning** (`justify-content: flex-end` and `padding-top`) inside an absolutely positioned wrapper to ensure it stays anchored to the top-right of the card image across all screen sizes.
- **Mandate:** **DO NOT** change the heart icon's position to `absolute` inside the wrapper. Use `padding` or `margin` on the wrapper or flex alignment to adjust its height, preserving its adaptive behavior. (Current preferred top padding: `6px`).

### Date Handling & Scraper Structure
- **Storage:** Cardrush buying price JSON files are stored in `one_piece_scripts/cardrush_buying_prices/YYYY-MM/YYYY-MM-DD.json`.
- **Formatting:** Dates displayed in the UI (charts, as-of labels) **MUST** use the numeric `YYYY/MM/DD` format (no month names like "Jan" or "Feb").
- **Sorting Mandate:** The `build_price_data.py` script **MUST** sort price files by their **basename** (filename) rather than their full path to ensure chronological processing across year/month folder boundaries.

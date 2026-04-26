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
# Making scraping traffic look less bot-like (practical guidance)

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

## Python example (requests)
```python
import random
import time
# Use curl_cffi to bypass JA3/JA4 TLS fingerprinting blocks
from curl_cffi import requests

# The User-Agent and sec-ch headers MUST exactly match the impersonated browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}

# impersonate="chrome124" mimics Chrome's exact TLS and HTTP/2 settings
s = requests.Session(impersonate="chrome124")
s.headers.update(headers)

# Establish session cookies by hitting the homepage first
try:
    s.get("https://example.com", timeout=20)
except Exception:
    pass

urls = ["https://example.com/page1", "https://example.com/page2"]

for url in urls:
    r = s.get(url, timeout=20)
    
    # Handle WAF blocks and rate limits
    if r.status_code in (403, 429, 503):
        print(f"Blocked or rate-limited: {r.status_code}")
        time.sleep(random.uniform(8, 20))
    else:
        # Normal human-like pacing between successful requests
        time.sleep(random.uniform(1.2, 4.7))
```

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

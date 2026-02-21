# Making scraping traffic look less bot-like (practical guidance)

## Environment note
External web requests from this environment returned `403 Forbidden` at the proxy layer during research attempts (`curl -I https://example.com`, `curl -I https://developer.mozilla.org/...`).

## Practical guidance
1. Use a **real, current browser User-Agent** string (matching a browser version that actually exists).
2. Keep UA and platform internally consistent (e.g., Windows UA should not be paired with Linux-only headers).
3. Send a realistic header set, not only `User-Agent`:
   - `Accept`, `Accept-Language`, `Accept-Encoding`, `Connection`
   - Chromium-family often sends `sec-ch-ua*` headers in browser contexts.
4. Persist sessions (cookies) so each request chain looks like one user journey instead of stateless hits.
5. Use human pacing: random jitter between requests, bounded concurrency, and backoff on 429/503.
6. Avoid impossible navigation patterns (e.g., deep URL fetches without first loading listing pages).
7. If detection is strict, use a browser automation stack that matches real browser behavior (JS execution, timing, TLS, HTTP2 fingerprints), not just UA spoofing.
8. Respect site Terms, robots policy, and legal boundaries.

## Python example (requests)
```python
import random, time, requests

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

s = requests.Session()
s.headers.update({
    "User-Agent": random.choice(UA_POOL),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
})

for url in urls:
    r = s.get(url, timeout=20)
    if r.status_code in (429, 503):
        time.sleep(random.uniform(8, 20))
    else:
        time.sleep(random.uniform(1.2, 4.7))
```

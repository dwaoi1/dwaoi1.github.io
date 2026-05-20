# Image Loading Performance Improvements

## Implemented Changes

### Current Approach (wsrv.nl first, local as fallback)
- Primary: wsrv.nl proxy (faster due to CDN and optimization)
- Fallback 1: Local images in `/images/cards/`
- Fallback 2: Cardrush image
- Fallback 3: Weserv proxy
- Fallback 4: Placeholder

### Wishlist Preloading
Added preload links for wishlist card images on page load to prioritize fetching.

## Remaining Improvements

### 1. Blur-Up Placeholders
Show a low-quality placeholder while images load (optional - skipped for now).

### 2. Responsive Images with srcset
Serve different sizes based on viewport.

### 3. Add Proper Caching Headers
In deploy.yml, add Cache-Control headers for better caching.

### 4. Image Optimization Pipeline
Generate webp versions and optimize images in the deploy workflow.

### 5. Service Worker for Caching
Add workbox for offline caching.

## Notes
- wsrv.nl is faster than local images despite the proxy overhead (CDN + optimization)
- Local images available but served slower from GitHub Pages
- GitHub Pages doesn't provide CDN - consider Cloudflare Pages for free CDN
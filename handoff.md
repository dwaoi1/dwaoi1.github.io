# Image Loading Performance Improvements

## Current Issues
- Images hosted on GitHub Pages (no CDN)
- Official site proxy (`wsrv.nl`) adds latency
- No preloading strategy for wishlist cards
- Large unoptimized image files

## Recommended Improvements

### 1. Image Preloading for Wishlist Cards
Add preload links for wishlist card images to prioritize loading:

```jsx
// In App.js or CardTable.js head
useEffect(() => {
  wishlist.forEach(cardId => {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.as = 'image';
    link.href = `/images/cards/${cardId}`;
    document.head.appendChild(link);
  });
}, [wishlist]);
```

Or add in `index.html`:
```html
<!-- For dynamic wishlist, load via useEffect above -->
```

### 2. Blur-Up Placeholders
Show a low-quality placeholder while images load:

```jsx
// Create a blur placeholder component
const BlurPlaceholder = ({ cardId }) => (
  <div
    style={{
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
      filter: 'blur(20px)',
      transform: 'scale(1.1)'
    }}
    className="blur-placeholder"
  />
);
```

Add CSS:
```css
.blur-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  transition: opacity 0.3s ease;
}

.blur-placeholder.loaded {
  opacity: 0;
}
```

### 3. Responsive Images with srcset
Serve different sizes based on viewport:

```jsx
<img
  srcSet={`/images/cards/${cardId}.png 1x, /images/cards/${cardId}@2x.png 2x`}
  src={`/images/cards/${cardId}.png`}
  alt={character}
/>
```

### 4. Add Proper Caching Headers
In deploy.yml, add Cache-Control headers:

```yaml
- name: Add Cache Headers
  run: |
    # Add .htaccess or _headers file for Cloudflare Pages
    echo "/* Cache-Control: public, max-age=31536000, immutable" >> _headers
```

Or use Cloudflare Pages which has better caching by default.

### 5. Image Optimization Pipeline
Consider adding an image optimization step in the deploy workflow:

```yaml
- name: Optimize Images
  run: |
    npm install -g sharp-cli
    sharp -i gh-pages/images/cards/*.png -o gh-pages/images/cards/ --format webp
```

### 6. Service Worker for Caching
Add workbox for offline caching:

```bash
npm install workbox-webpack-plugin
```

### Priority Order
1. **High** - Add preload for wishlist cards (quick win)
2. **High** - Add blur-up placeholders (perceived performance)
3. **Medium** - Implement srcset for responsive images
4. **Medium** - Add caching headers
5. **Low** - Image optimization pipeline
6. **Low** - Service worker

## Notes
- Current proxy-first approach (wsrv.nl) works but adds ~250ms per image
- Local images in `/images/cards/` are available but have path issues
- GitHub Pages doesn't provide CDN by default - consider Cloudflare Pages for free CDN
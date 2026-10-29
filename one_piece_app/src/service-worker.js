/* eslint-disable no-restricted-globals */
import { clientsClaim } from 'workbox-core';
import { precacheAndRoute, cleanupOutdatedCaches } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { StaleWhileRevalidate, CacheFirst, NetworkFirst } from 'workbox-strategies';

self.skipWaiting();

clientsClaim();
cleanupOutdatedCaches();

precacheAndRoute(self.__WB_MANIFEST);

// Cache card images from wsrv.nl proxy (stale-while-revalidate)
registerRoute(
  ({ url }) => url.origin === 'https://wsrv.nl' || url.origin === 'https://images.weserv.nl',
  new StaleWhileRevalidate({
    cacheName: 'card-images-proxy',
    plugins: [
      {
        cacheWillUpdate: async ({ response }) => {
          return response && response.status === 200 ? response : null;
        },
      },
    ],
  })
);

// Cache local card images (cache-first since they're static)
registerRoute(
  ({ url }) => url.pathname.includes('/images/cards/'),
  new CacheFirst({
    cacheName: 'card-images-local',
    plugins: [
      {
        cacheWillUpdate: async ({ response }) => {
          return response && response.status === 200 ? response : null;
        },
      },
    ],
  })
);

// Cache cardrush images (cache-first)
registerRoute(
  ({ url }) => url.hostname === 'files.cardrush.media',
  new CacheFirst({
    cacheName: 'cardrush-images',
    plugins: [
      {
        cacheWillUpdate: async ({ response }) => {
          return response && response.status === 200 ? response : null;
        },
      },
    ],
  })
);

// Cache JSON data files (network-first for freshness, fallback to cache)
registerRoute(
  ({ url }) => url.pathname.endsWith('.json'),
  new NetworkFirst({
    cacheName: 'app-data',
    networkTimeoutSeconds: 10,
    plugins: [
      {
        cacheWillUpdate: async ({ response }) => {
          return response && response.status === 200 ? response : null;
        },
      },
    ],
  })
);

// Cache placeholder images (cache-first)
registerRoute(
  ({ url }) => url.hostname === 'placehold.co',
  new CacheFirst({
    cacheName: 'placeholders',
  })
);

// Navigation requests: serve cached index.html when offline
registerRoute(
  ({ request }) => request.mode === 'navigate',
  new NetworkFirst({
    cacheName: 'pages',
  })
);

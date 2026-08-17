const CACHE_NAME = 'agrosmart-pwa-v2';
const OFFLINE_URL = '/offline.html';
const ASSETS_TO_CACHE = [
  '/index.html',
  '/login.html',
  '/signup.html',
  '/mfa-setup.html',
  '/farmer-dashboard.html',
  '/client-dashboard.html',
  '/community-services.html',
  '/marketplace.html',
  '/styles.css',
  '/app.js',
  '/manifest.json',
  '/offline.html'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
          return null;
        })
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return;
  }

  const requestUrl = new URL(event.request.url);

  if (requestUrl.origin === self.location.origin && requestUrl.pathname.startsWith('/')) {
    event.respondWith(
      fetch(event.request).then((response) => {
        if (response && response.ok && !response.bodyUsed) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseToCache));
        }
        return response;
      }).catch(() => caches.match(event.request)).then((cached) => cached || caches.match(OFFLINE_URL)).catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  if (requestUrl.origin === self.location.origin && (requestUrl.pathname.startsWith('/api/') || event.request.mode === 'navigate')) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(OFFLINE_URL))
    );
  }
});

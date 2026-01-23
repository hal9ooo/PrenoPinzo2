const CACHE_NAME = 'prenopinzo-v1';
const START_URL = '/?source=pwa';
const STATIC_PREFIX = '/static/';
const PRECACHE = [
  '/static/bookings/app.css',
  '/static/bookings/manifest.json',
  '/static/bookings/icon-192.png',
  '/static/bookings/icon-512.png',
  '/static/bookings/favicon.png',
  '/static/bookings/favicon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE))
      .catch(() => null)
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request));
    return;
  }
  const url = new URL(event.request.url);
  const isSameOrigin = url.origin === self.location.origin;
  const isStatic = url.pathname.startsWith(STATIC_PREFIX);

  if (isSameOrigin && isStatic) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        });
      })
    );
  }
});

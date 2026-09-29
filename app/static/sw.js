/* Platform-X — Service worker (Phase 30, Step 8) */
const CACHE = 'px-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/platform.css',
  '/static/css/platform-home.css',
  '/static/css/typography.css',
  '/static/js/px-core.js',
  '/static/icons/icon.svg',
  '/static/manifest.webmanifest'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // API calls: network first, no cache
  if (url.pathname.startsWith('/api/')) return;

  // Same-origin static: cache-first
  if (url.origin === location.origin) {
    e.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((resp) => {
        if (resp && resp.status === 200 && (url.pathname.startsWith('/static/') || url.pathname === '/')) {
          const clone = resp.clone();
          caches.open(CACHE).then((c) => c.put(req, clone));
        }
        return resp;
      }).catch(() => cached))
    );
  }
});

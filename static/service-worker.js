self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open('hameln-txt-cache').then(function(cache) {
      return cache.addAll([
        '/',
        '/static/icons/icon-192x192.png',
        '/static/icons/icon-512x512.png',
      ]);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    })
  );
});
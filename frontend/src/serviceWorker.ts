/// <reference lib="webworker" />
/* eslint-disable no-restricted-globals */

// This is the service worker with the Cache-first strategy.
// Add any other custom code that you want to be included in the service worker.
// For example, to enable push notifications, uncomment the lines below and add your custom code.

const CACHE_NAME = 'agri-advisory-cache-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.ico',
  '/logo192.png',
  '/logo512.png',
  // Add other static assets you want to cache
];

self.addEventListener('install', (event: ExtendableEvent) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', (event: FetchEvent) => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});

self.addEventListener('activate', (event: ExtendableEvent) => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
          return null; 
        }).filter(Boolean) as Promise<boolean>[] // Filter out nulls and assert type
      );
    })
  );
});

// Example: Push Notifications (uncomment and customize)
// self.addEventListener('push', (event: PushEvent) => {
//   const options = {
//     body: event.data?.text() || 'New notification',
//     icon: 'logo192.png',
//     vibrate: [100, 50, 100],
//     data: {
//       dateOfArrival: Date.now(),
//       primaryKey: '2'
//     }
//   };
//   event.waitUntil(
//     self.registration.showNotification('Agri-Advisory Alert', options)
//   );
// });

// self.addEventListener('notificationclick', (event: NotificationEvent) => {
//   event.notification.close();
//   event.waitUntil(
//     clients.openWindow('/')
//   );
// });

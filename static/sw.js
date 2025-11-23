// Service Worker for Panel PWA
// Provides offline functionality and caching

const CACHE_NAME = 'panel-v1.0.0';
const STATIC_CACHE = 'panel-static-v1.0.0';
const DYNAMIC_CACHE = 'panel-dynamic-v1.0.0';

// Resources to cache immediately
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/offline'
];

// API endpoints to cache (with short TTL)
const API_CACHE_PATTERNS = [
  /\/api\/health$/,
  /\/api\/user\/profile$/,
  /\/api\/servers$/,
];

// Don't cache these patterns
const NO_CACHE_PATTERNS = [
  /\/api\/.*\/export$/,
  /\/api\/.*\/delete$/,
  /\/admin\//,
  /\/login$/,
  /\/register$/,
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('[SW] Install event');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch(error => {
        console.error('[SW] Cache install failed:', error);
      })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[SW] Activate event');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip external requests
  if (!url.origin.includes(self.location.origin)) return;

  // Skip no-cache patterns
  if (NO_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname))) {
    return;
  }

  // Handle API requests with network-first strategy
  if (API_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname))) {
    event.respondWith(networkFirstStrategy(request));
    return;
  }

  // Handle static assets with cache-first strategy
  if (STATIC_ASSETS.includes(url.pathname) || url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirstStrategy(request));
    return;
  }

  // Default: network-first for dynamic content
  event.respondWith(networkFirstStrategy(request));
});

// Cache-first strategy (for static assets)
async function cacheFirstStrategy(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache-first strategy failed:', error);
    return new Response('Offline - Content not available', {
      status: 503,
      statusText: 'Service Unavailable'
    });
  }
}

// Network-first strategy (for dynamic content)
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', error);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      const offlineResponse = await caches.match('/offline');
      if (offlineResponse) {
        return offlineResponse;
      }
    }

    return new Response('Offline - Content not available', {
      status: 503,
      statusText: 'Service Unavailable'
    });
  }
}

// Push notification event
self.addEventListener('push', event => {
  console.log('[SW] Push received:', event);

  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/'
    },
    actions: [
      {
        action: 'view',
        title: 'View',
        icon: '/static/icons/view-icon.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click event
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification click:', event);

  event.notification.close();

  if (event.action === 'dismiss') return;

  const url = event.notification.data.url || '/';

  event.waitUntil(
    clients.openWindow(url)
  );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  console.log('[SW] Background sync:', event.tag);

  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  // Implement background sync logic here
  // This could sync offline actions like forum posts, etc.
  console.log('[SW] Performing background sync');
}

// Message event for communication with main thread
self.addEventListener('message', event => {
  console.log('[SW] Message received:', event.data);

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Periodic cleanup
self.addEventListener('periodicsync', event => {
  if (event.tag === 'cleanup-cache') {
    event.waitUntil(cleanupCache());
  }
});

async function cleanupCache() {
  const cache = await caches.open(DYNAMIC_CACHE);
  const keys = await cache.keys();

  // Remove old entries (older than 1 hour)
  const oneHourAgo = Date.now() - (60 * 60 * 1000);

  await Promise.all(
    keys.map(async request => {
      const response = await cache.match(request);
      if (response) {
        const date = response.headers.get('date');
        if (date && new Date(date).getTime() < oneHourAgo) {
          await cache.delete(request);
        }
      }
    })
  );

  console.log('[SW] Cache cleanup completed');
}
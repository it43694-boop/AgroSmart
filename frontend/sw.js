const CACHE_NAME = 'agrosmart-v1';
const STATIC_CACHE = 'agrosmart-static-v1';
const DYNAMIC_CACHE = 'agrosmart-dynamic-v1';

const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/farmer-dashboard.html',
    '/admin.html',
    '/bank-dashboard.html',
    '/client-dashboard.html',
    '/iot-dashboard.html',
    '/insurance-dashboard.html',
    '/styles.css',
    '/i18n.js',
    '/manifest.json'
];

const API_CACHE_DURATION = 5 * 60 * 1000;

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        Promise.all([
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((cacheName) => {
                            return cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE;
                        })
                        .map((cacheName) => {
                            return caches.delete(cacheName);
                        })
                );
            }),
            self.clients.claim()
        ])
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    if (url.pathname.startsWith('/api/')) {
        event.respondWith(handleApiRequest(event.request));
    } else if (url.pathname.startsWith('/')) {
        event.respondWith(handleStaticRequest(event.request));
    } else {
        event.respondWith(fetch(event.request));
    }
});

async function handleApiRequest(request) {
    const url = new URL(request.url);
    const cacheKey = `api-${url.pathname}${url.search}`;

    if (request.method === 'GET') {
        const cachedResponse = await caches.match(cacheKey);
        
        if (cachedResponse) {
            const cachedData = await cachedResponse.json();
            const cachedTime = cachedData._cachedAt || 0;
            
            if (Date.now() - cachedTime < API_CACHE_DURATION) {
                return cachedResponse;
            }
        }

        try {
            const networkResponse = await fetch(request);
            
            if (networkResponse.ok) {
                const clonedResponse = networkResponse.clone();
                const data = await clonedResponse.json();
                data._cachedAt = Date.now();
                
                const responseToCache = new Response(JSON.stringify(data), {
                    headers: clonedResponse.headers
                });
                
                const cache = await caches.open(DYNAMIC_CACHE);
                cache.put(cacheKey, responseToCache);
            }
            
            return networkResponse;
        } catch (error) {
            if (cachedResponse) {
                return cachedResponse;
            }
            
            return new Response(JSON.stringify({ error: 'Offline - No cached data' }), {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            });
        }
    } else {
        return fetch(request);
    }
}

async function handleStaticRequest(request) {
    const cachedResponse = await caches.match(request, { cacheName: STATIC_CACHE });
    
    if (cachedResponse) {
        return cachedResponse;
    }

    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        return new Response('Offline - Resource not available', {
            status: 503,
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-data') {
        event.waitUntil(syncData());
    }
});

async function syncData() {
    const offlineData = await getOfflineData();
    
    for (const item of offlineData) {
        try {
            await fetch(item.url, {
                method: item.method,
                headers: item.headers,
                body: item.body
            });
            await removeOfflineItem(item.id);
        } catch (error) {
            console.error('Sync failed for item:', item.id, error);
        }
    }
}

async function getOfflineData() {
    const cache = await caches.open(DYNAMIC_CACHE);
    const offlineRequests = await cache.match('offline-requests');
    return offlineRequests ? await offlineRequests.json() : [];
}

async function removeOfflineItem(id) {
    const offlineData = await getOfflineData();
    const filtered = offlineData.filter(item => item.id !== id);
    const cache = await caches.open(DYNAMIC_CACHE);
    await cache.put('offline-requests', new Response(JSON.stringify(filtered)));
}

self.addEventListener('push', (event) => {
    const options = {
        body: event.data ? event.data.text() : 'Nouvelle notification AgroSmart',
        icon: '/icons/icon-192x192.png',
        badge: '/icons/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'Explorer',
                icon: '/icons/explore.png'
            },
            {
                action: 'close',
                title: 'Fermer',
                icon: '/icons/close.png'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('AgroSmart', options)
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/index.html')
        );
    }
});

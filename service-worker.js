const CACHE='contratos-v033',FILES=['./','./index.html','./style.css','./app.js?v=033','./manifest.webmanifest','./assets/icon.svg'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(Promise.all([caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))),self.clients.claim()])));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;const u=new URL(e.request.url);if(u.origin!==location.origin)return;
// Network-first para dados e app shell: evita interface antiga com dados novos.
e.respondWith(fetch(e.request).then(res=>{if(res.ok&&u.pathname.startsWith(new URL('./',self.registration.scope).pathname))caches.open(CACHE).then(c=>c.put(e.request,res.clone()));return res}).catch(()=>caches.match(e.request)))});

/* 作業時間管理 Android版 — オフラインでも動くようにするための入れ物。
   版を上げたいときは CACHE の名前だけ変える（例 wta-v1 → wta-v2）。
   古い入れ物は activate のときに片づける。 */
const CACHE = "wta-v1";
const FILES = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icon/icon-192.png",
  "./icon/icon-512.png",
  "./icon/icon-maskable-512.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

/* 画面のファイルは「まず取りに行って、だめなら控えを出す」。
   これで新しい版を置いたときに気づける。取りに行けたら控えも入れ替える。 */
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  e.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(req).then((r) => r || caches.match("./index.html")))
  );
});

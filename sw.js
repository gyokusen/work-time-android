/* 作業時間管理 Android版 — オフラインでも動くようにするための入れ物。
   版を上げたいときは CACHE の名前だけ変える（例 wta-v2 → wta-v3）。
   古い入れ物は activate のときに片づける。 */
const CACHE = "wta-v2";
const FILES = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icon/icon-192.png",
  "./icon/icon-512.png",
  "./icon/icon-maskable-512.png"
];
/* 初期マスタ.csv はここに入れない。
   置いていない人もいるので、addAll が 404 で丸ごと失敗してしまう。
   下の fetch（まず取りに行く形）で自然に控えに入る。 */

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
   これで新しい版を置いたときに気づける。取りに行けたら控えも入れ替える。

   ただし GitHub Pages は HTML に「10分はキャッシュしてよい」を付けて配るので、
   ふつうに fetch すると**ブラウザの手元の控え**が返ってきて、
   置き場を新しくしてもアプリが古いままになる。
   そこで画面そのもの（ナビゲーション＝HTML）は cache:"no-store" で、
   毎回サーバに聞きに行く。中身は下でこの入れ物に控えるので、
   電波が無いときはそちらが出る。 */
function isDoc(req) {
  return req.mode === "navigate" || req.destination === "document";
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const go = isDoc(req) ? fetch(req.url, {cache: "no-store"}) : fetch(req);
  e.respondWith(
    go
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(req).then((r) => r || caches.match("./index.html")))
  );
});

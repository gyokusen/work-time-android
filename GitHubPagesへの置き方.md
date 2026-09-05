# GitHub Pages への置き方（作業時間管理 Android版）

PWA を「ホーム画面に追加」できるようにするには、**https:// のURL**が1つ要ります。
GitHub Pages は無料で、URLを教えるだけで誰でも入れられます。

> **先に確認**：GitHub Free では、**public（公開）リポジトリでないと Pages は使えません**。
> このアプリは職場固有の情報を持ちません（ターゲット＝案件名は最初は空、
> 作業の一覧も一般的な工程名だけ）が、公開してよいかは自分で判断してください。
> 公開したくない場合は「別の置き場」を見てください。

---

## 1. リポジトリを作る

1. GitHub で **New repository**
2. 名前：`work-time-android`（何でもよい）
3. **Public** を選ぶ
4. Create repository

## 2. ファイルを上げる

このフォルダの中身を、リポジトリの**いちばん上**に置きます。

```
index.html
manifest.webmanifest
sw.js
icon/icon-192.png
icon/icon-512.png
icon/icon-maskable-512.png
```

`.md` ファイルは上げても上げなくてもかまいません（アプリの動きには関係ありません）。

コマンドで上げるとき（Git Bash）：

```
cd /c/Users/Public/クロード/作業時間管理/android
git init
git add index.html manifest.webmanifest sw.js icon
git commit -m "作業時間管理 Android版 v1.0.1"
git branch -M main
git remote add origin https://github.com/自分のID/work-time-android.git
git push -u origin main
```

> **注意：`自分のID` の部分は、自分の GitHub のユーザー名に置き換えます。**
> `< >`（山かっこ）は付けません。Git Bash では `<` `>` が入出力の記号なので、
> `<自分のID>` と打つと `bash: 自分のID: No such file or directory` になります。
> IDが `gyokusen` なら `https://github.com/gyokusen/work-time-android.git` です。
> **手順1でリポジトリを作った直後の画面に出るURLをそのままコピーする**のが確実です。

うまくいったか確かめる：

```
git remote -v
```

`origin  https://github.com/…（fetch）` と `（push）` の2行が出れば設定できています。
初回の `git push` ではブラウザが開いて GitHub のログインを求められます
（Git Credential Manager）。許可すれば、以降は聞かれません。

`LF will be replaced by CRLF` という警告が出ますが、無視して大丈夫です。

## 3. Pages を有効にする

1. リポジトリの **Settings** → 左の **Pages**
2. Source：**Deploy from a branch**
3. Branch：**main** / フォルダ：**/ (root)** → Save
4. 1〜2分待つと、上に URL が出る

```
https://<自分のID>.github.io/work-time-android/
```

## 4. スマホで入れる

1. Chrome でそのURLを開く
2. 右上「⋮」→ **［ホーム画面に追加］**（または［アプリをインストール］）
3. ホーム画面の時計アイコンから開く

「ホーム画面に追加」が出ないときは、次を確かめてください。

- URL が `https://` になっているか（`http://` や `file://` ではだめ）
- `manifest.webmanifest` と `sw.js` が 404 になっていないか
  （Chrome の「⋮ →（PCで）デベロッパー ツール → Application」で見られます）
- `icon/` の3枚が上がっているか

## 5. 直したものを反映する

1. `index.html` を直して push する
2. スマホ側でアプリを一度閉じて、開き直す

アイコンや `manifest.webmanifest` を替えたときは、`sw.js` の

```js
const CACHE = "wta-v1";
```

を `"wta-v2"` のように書き換えてから push してください。古い控えが片づきます。

---

## 別の置き場

| 置き場 | 向き・不向き |
|---|---|
| **GitHub Pages（public）** | 無料・すぐ・URLを渡すだけ。ソースは公開になる |
| **社内のWebサーバー** | 社内だけに配れる。置ける場所があるかは要確認。https でないと PWA にできない |
| **file:// で開く** | 置き場が要らないが、**ホーム画面にアプリとして追加できず、記録も消えやすい**。試すだけなら可 |

社内サーバーに置く場合も、上げるファイルは同じ6つです。
`https://` で開けさえすれば、あとの手順は変わりません。

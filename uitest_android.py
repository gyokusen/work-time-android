# -*- coding: utf-8 -*-
"""作業時間管理 Android版（PWA）の回帰テスト。
   python -m http.server で配って、スマホの大きさの Chromium で通す。"""
import http.server, socketserver, threading, functools, os, sys, glob, json, time
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8931
DL = os.path.join(ROOT, "_dl")
os.makedirs(DL, exist_ok=True)
for f in glob.glob(os.path.join(DL, "*")):
    os.remove(f)

Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
class Q(socketserver.TCPServer):
    allow_reuse_address = True
    def handle_error(self, *a): pass
srv = Q(("127.0.0.1", PORT), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

OK, NG = [], []
def check(name, cond, extra=""):
    (OK if cond else NG).append(name + (("  … " + str(extra)) if extra else ""))
    print(("  OK  " if cond else "  NG  ") + name + (("  … " + str(extra)) if extra else ""))

with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium/chrome-linux/chrome"
                           if os.path.exists("/opt/pw-browsers/chromium/chrome-linux/chrome") else None)
    ctx = br.new_context(viewport={"width": 412, "height": 915}, device_scale_factor=2.6,
                         is_mobile=True, has_touch=True, locale="ja-JP",
                         timezone_id="Asia/Tokyo", accept_downloads=True)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
    pg.goto("http://127.0.0.1:%d/index.html" % PORT)
    pg.wait_for_timeout(900)

    # ① 立ち上がり（置き場の 初期マスタ.csv を読んでいるはず）
    check("版が出る", pg.inner_text("#ver").startswith("v"), pg.inner_text("#ver"))
    n = pg.locator("#workGrid .wbtn").count()
    check("初期マスタCSVから作業21件が入る", n == 21, n)
    src = pg.evaluate("async()=>{const a=await getAll('works');return a.find(w=>w.work_id==='W013').name;}")
    check("CSVの名前で入っている（W013＝結合テスト１）", src == "結合テスト１", src)
    check("最初は「何もしていません」", "何もしていません" in pg.inner_text("#nowWork"))
    # 入力欄の案内文が、欄の幅に収まっているか（切れて「…」にならないか）
    def fits(sel):
        return pg.evaluate("""(sel)=>{
          const el = document.querySelector(sel);
          const cs = getComputedStyle(el);
          const s = document.createElement('span');
          s.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap';
          s.style.fontFamily = cs.fontFamily; s.style.fontSize = cs.fontSize;
          s.style.fontWeight = cs.fontWeight; s.style.letterSpacing = cs.letterSpacing;
          s.textContent = el.placeholder;
          document.body.appendChild(s);
          const w = s.getBoundingClientRect().width; s.remove();
          const avail = el.clientWidth - parseFloat(cs.paddingLeft)
                                       - parseFloat(cs.paddingRight);
          return [Math.round(w), Math.round(avail), el.placeholder];
        }""", sel)
    for sel, nm in (("#nowNote", "ひとこと"), ("#pkFind", "作業名で絞り込む")):
        w, avail, ph = fits(sel)
        check("案内文が欄に収まる（" + nm + "）", w <= avail, (ph, w, avail))

    # ② 打刻（切替式）
    pg.get_by_role("button", name="コーディング", exact=False).first.click()
    pg.wait_for_timeout(400)
    check("打刻すると作業名が出る", "コーディング" in pg.inner_text("#nowWork"),
          pg.inner_text("#nowWork"))
    check("経過が 0:00 から数え始める", pg.inner_text("#nowElapsed") == "0:00",
          pg.inner_text("#nowElapsed"))
    # 同じ作業をもう一度 → 確認が出る。［キャンセル］なら何もしない
    msgs = []
    pg.once("dialog", lambda d: (msgs.append(d.message), d.dismiss()))
    pg.get_by_role("button", name="コーディング", exact=False).first.click()
    pg.wait_for_timeout(500)
    check("同じ作業で確認が出る", msgs and "すでに実行中" in msgs[0], msgs)
    check("確認の文に「もう一度同じ作業を始めますか」がある",
          msgs and "もう一度同じ作業を始めますか" in msgs[0], msgs)
    n0 = pg.evaluate("async()=>{const a=await getAll('entries');return a.length;}")
    check("キャンセルなら記録は増えない", n0 == 1, n0)
    # ［OK］なら、そこで区切って同じ作業を始め直す。ひとことは終わる区間に残る
    pg.fill("#nowNote", "p.10〜20")
    pg.fill("#nowProgress", "30")
    pg.once("dialog", lambda d: d.accept())
    pg.get_by_role("button", name="コーディング", exact=False).first.click()
    pg.wait_for_timeout(700)
    n1 = pg.evaluate("async()=>{const a=await getAll('entries');return a.length;}")
    check("OKなら区切られて2件になる", n1 == 2, n1)
    done = pg.evaluate("""async()=>{const a=await getAll('entries');
      const f=a.filter(r=>r.end_at).sort((x,y)=>x.id-y.id); const r=f[f.length-1];
      return [r.work_name, r.note, r.progress];}""")
    check("ひとことは終わった区間に残る", done[1] == "p.10〜20", done)
    check("進捗も終わった区間に残る", done[2] == 30, done)
    run = pg.evaluate("""async()=>{const a=await getAll('entries');
      const r=a.find(x=>!x.end_at); return [r.work_name, r.note, r.progress];}""")
    check("続きの区間は同じ作業で、ひとことは空", run[0] == "コーディング" and run[1] == "",
          run)
    check("画面のひとこと欄も空になる", pg.input_value("#nowNote") == "",
          pg.input_value("#nowNote"))
    check("始め直しの知らせが出る", "始め直しました" in pg.inner_text("#toast"),
          pg.inner_text("#toast"))
    # 切替
    pg.get_by_role("button", name="ドキュメント", exact=False).first.click()
    pg.wait_for_timeout(400)
    check("切り替えると前の作業が終わる",
          "終えました" in pg.inner_text("#toast") and "始めました" in pg.inner_text("#toast"),
          pg.inner_text("#toast"))

    # ③ ひとことが消えないか（PC版 v1.0.1 の不具合）
    pg.fill("#nowNote", "書きかけ")
    pg.wait_for_timeout(2500)
    pg.evaluate("refreshPunch()")
    pg.wait_for_timeout(300)
    check("書きかけの「ひとこと」が消えない", pg.input_value("#nowNote") == "書きかけ",
          pg.input_value("#nowNote"))
    pg.click("#bProgress"); pg.wait_for_timeout(300)

    # ④ 記録タブ
    pg.click("nav.tabs button[data-page='log']"); pg.wait_for_timeout(500)
    rows = pg.locator("#logBody .row").count()
    check("記録が3件ならぶ", rows == 3, rows)
    check("実行中の行に印が付く", pg.locator("#logBody .row.run").count() == 1)
    check("合計が出る", "作業" in pg.inner_text("#dTotal"), pg.inner_text("#dTotal"))

    # 記録を足す（過去の時刻）→ すき間の警告
    pg.click("#bAddRow"); pg.wait_for_timeout(300)
    today = pg.evaluate("businessDate()")
    pg.fill("#eStart", today + " 09:00")
    pg.fill("#eEnd", today + " 10:30")
    pg.select_option("#eWork", label=[o for o in pg.eval_on_selector_all(
        "#eWork option", "els=>els.map(e=>e.textContent)") if "保守作業" in o][0])
    pg.fill("#eNote", "テストで足した行")
    pg.get_by_role("button", name="保存").click()
    pg.wait_for_timeout(600)
    check("記録を足せる", pg.locator("#logBody .row").count() == 4,
          pg.locator("#logBody .row").count())
    check("すき間の注意が出る", pg.locator("#gapBox .gap").count() == 1,
          pg.inner_text("#gapBox") if pg.locator("#gapBox .gap").count() else "(なし)")

    # 編集
    pg.locator("#logBody .row").first.click(); pg.wait_for_timeout(300)
    check("行を押すと編集が開く", "記録を直す" in pg.inner_text("#dlgTitle"))
    pg.fill("#eNote", "直したメモ")
    pg.get_by_role("button", name="保存").click(); pg.wait_for_timeout(500)
    check("編集が反映される", "直したメモ" in pg.inner_text("#logBody"))

    # ⑤ マスタ
    pg.click("nav.tabs button[data-page='mst']"); pg.wait_for_timeout(400)
    pg.click("#mAddTarget"); pg.wait_for_timeout(300)
    pg.fill("#tName", "SMILe")
    pg.get_by_role("button", name="保存").click(); pg.wait_for_timeout(500)
    check("ターゲットを足せる（T001）", "T001" in pg.inner_text("#mstTarget"),
          pg.inner_text("#mstTarget")[:60])
    pg.click("#mAddWork"); pg.wait_for_timeout(300)
    pg.fill("#wName", "追加テスト作業")
    pg.get_by_role("button", name="保存").click(); pg.wait_for_timeout(500)
    check("作業を足すと W022 になる", "W022" in pg.inner_text("#mstWork"))
    # マスタの表に「並び」列があること
    hw = pg.eval_on_selector_all("#mstWork ~ *, table.t.mst th",
                                 "els=>els.map(e=>e.textContent.trim())")
    check("マスタの見出しに「並び」がある", hw.count("並び") == 2, hw)
    r1 = pg.eval_on_selector_all("#mstWork tr:first-child td",
                                 "els=>els.map(e=>e.textContent.trim())")
    check("作業の行が5列（ID/名称/区分/並び/使う）", len(r1) == 5, r1)
    check("並びの値が出る（W001は10）", r1[0] == "W001" and r1[3] == "10", r1)
    r2 = pg.eval_on_selector_all("#mstTarget tr:first-child td",
                                 "els=>els.map(e=>e.textContent.trim())")
    check("ターゲットの行が4列（ID/名称/並び/使う）", len(r2) == 4, r2)
    check("ターゲットの並びが出る（既定999）", r2[2] == "999", r2)
    # 幅：横スクロールが出ていないこと
    ov = pg.evaluate("()=>[document.documentElement.scrollWidth, window.innerWidth]")
    check("マスタ画面で横にはみ出さない", ov[0] <= ov[1], ov)

    # 打刻画面にターゲットが出る
    pg.click("nav.tabs button[data-page='punch']"); pg.wait_for_timeout(400)
    opts = pg.eval_on_selector_all("#pkTarget option", "els=>els.map(e=>e.textContent)")
    check("打刻画面のターゲット一覧に出る", "SMILe" in opts, opts)
    check("未選択の文言が「（ターゲット未選択）」", opts[0] == "（ターゲット未選択）", opts[0])
    # 行の形：ラベルを置かず、選ぶ欄の右に［＋ターゲット］
    bar = pg.eval_on_selector("#pkTarget", "el=>el.parentElement")
    lbl = pg.eval_on_selector_all("#pg-punch .bar label.f", "els=>els.map(e=>e.textContent)")
    check("打刻画面に「ターゲット」のラベルが無い", "ターゲット" not in lbl, lbl)
    order = pg.evaluate("""()=>{const b=document.getElementById('pkTarget').parentElement;
      return [...b.children].map(e=>e.id||e.tagName);}""")
    check("選ぶ欄の右に＋ターゲット", order == ["pkTarget", "bAddTarget"], order)
    sx = pg.evaluate("""()=>{const s=document.getElementById('pkTarget').getBoundingClientRect();
      const b=document.getElementById('bAddTarget').getBoundingClientRect();
      return [Math.round(s.left), Math.round(s.right), Math.round(b.left)];}""")
    check("＋ターゲットが選ぶ欄より右にある", sx[2] >= sx[1], sx)
    # ＋ターゲットで足すと、そのまま選ばれる
    pg.click("#bAddTarget"); pg.wait_for_timeout(400)
    check("＋ターゲットで登録画面が開く", "ターゲットを足す" in pg.inner_text("#dlgTitle"),
          pg.inner_text("#dlgTitle"))
    pg.fill("#tName", "その場で登録")
    pg.get_by_role("button", name="保存").click(); pg.wait_for_timeout(700)
    sel = pg.eval_on_selector("#pkTarget", "el=>el.options[el.selectedIndex].textContent")
    check("足したターゲットが自動で選ばれる", sel == "その場で登録", sel)
    ov2 = pg.evaluate("()=>[document.documentElement.scrollWidth, window.innerWidth]")
    check("打刻画面で横にはみ出さない", ov2[0] <= ov2[1], ov2)
    # 打刻すると、そのターゲットが記録に入る
    pg.get_by_role("button", name="保守作業", exact=False).first.click()
    pg.wait_for_timeout(500)
    check("選んだターゲットが打刻に付く", "その場で登録" in pg.inner_text("#nowTarget"),
          pg.inner_text("#nowTarget"))
    pg.fill("#pkFind", "テスト"); pg.wait_for_timeout(300)
    # 単体/結合1・2/システム/移行/運用テスト＋追加テスト作業 の7件
    check("作業名で絞り込める", pg.locator("#workGrid .wbtn").count() == 7,
          pg.locator("#workGrid .wbtn").count())
    pg.fill("#pkFind", "追加テスト"); pg.wait_for_timeout(300)
    check("絞り込みで1件まで絞れる", pg.locator("#workGrid .wbtn").count() == 1,
          pg.locator("#workGrid .wbtn").count())
    pg.fill("#pkFind", ""); pg.wait_for_timeout(200)

    # ⑥ 集計
    pg.click("nav.tabs button[data-page='sum']"); pg.wait_for_timeout(600)
    pg.click("#bSum"); pg.wait_for_timeout(600)
    check("合計カードが3つ出る", pg.locator("#sumTot .sum-card").count() == 3)
    check("作業別が出る", pg.locator("#sumWork tr").count() >= 2,
          pg.locator("#sumWork tr").count())
    check("日別が出る", pg.locator("#sumDay tr").count() >= 1)
    txt = pg.inner_text("#sumTot")
    check("休憩と作業が分かれている", "休憩" in txt and "作業" in txt)

    # ⑦ CSV 書き出し
    with pg.expect_download() as di:
        pg.click("#bCsvEntries")
    d = di.value
    path = os.path.join(DL, d.suggested_filename)
    d.save_as(path)
    raw = open(path, "rb").read()
    head = raw.decode("utf-8-sig").splitlines()[0]
    check("記録CSVが落ちる（名前）", d.suggested_filename.startswith("作業記録_"),
          d.suggested_filename)
    check("CSVにBOMが付く（Excel対策）", raw[:3] == b"\xef\xbb\xbf")
    check("CSVの見出しがPC版と同じ",
          head == "開始日時,終了日時,作業名称,作業ID,ターゲット名称,ターゲットID,作業時間,作業時間(分),進捗度,メモ",
          head)
    body = raw.decode("utf-8-sig").splitlines()
    nall = pg.evaluate("async()=>{const a=await getAll('entries');return a.length;}")
    check("CSVの行数が記録数と合う（見出し＋記録）", len(body) == nall + 1, (len(body), nall))

    with pg.expect_download() as di2:
        pg.click("#bCsvSummary")
    d2 = di2.value; p2 = os.path.join(DL, d2.suggested_filename); d2.save_as(p2)
    h2 = open(p2, encoding="utf-8-sig").read().splitlines()[0]
    check("集計CSVの見出し", h2 == "区分,ID,名称,時間,分,割合(%)", h2)

    # ⑧ 設定＋控え
    pg.click("#bCfg"); pg.wait_for_timeout(400)
    check("設定が開く", "設定" == pg.inner_text("#dlgTitle"))
    check("件数が出る", "記録" in pg.inner_text("#dlgBody"))
    # 記録を消されないようにする申請
    ps = pg.evaluate("()=>persistState")
    check("起動時に保護を申し込んでいる（true/false/null のどれか）",
          ps in (True, False, None), ps)
    body0 = pg.inner_text("#dlgBody")
    check("⚙にデータの保護の状態が出る", "データの保護：" in body0,
          [l for l in body0.splitlines() if "データの保護" in l])
    if ps is not True:
        check("通っていないときは申請ボタンが出る",
              pg.locator("#cPersist").count() == 1)
        real = pg.evaluate("""async()=>{
          if(!navigator.storage || !navigator.storage.persist) return "無し";
          return typeof (await navigator.storage.persisted());}""")
        check("ブラウザに申請の窓口がある", real in ("boolean", "無し"), real)
    else:
        check("通っているときは申請ボタンを出さない",
              pg.locator("#cPersist").count() == 0)
    with pg.expect_download() as di3:
        pg.click("#cBackup")
    d3 = di3.value; p3 = os.path.join(DL, d3.suggested_filename); d3.save_as(p3)
    js = json.load(open(p3, encoding="utf-8"))
    check("控えJSONにBOMが付かない", open(p3, "rb").read()[:1] != b"\xef")
    check("控えに記録が入る", len(js.get("entries", [])) == nall, (len(js.get("entries", [])), nall))
    check("控えに作業とターゲットが入る",
          len(js.get("works", [])) == 22 and len(js.get("targets", [])) == 2,
          (len(js.get("works", [])), len(js.get("targets", []))))
    # 一日の始まりを直す
    pg.fill("#cDay", "07:00")
    pg.fill("#cRound", "5")
    pg.get_by_role("button", name="保存").click(); pg.wait_for_timeout(600)
    v = pg.evaluate("CFG")
    check("設定が保存される", v["day_start"] == "07:00" and v["round_minutes"] == 5, v)

    # ⑨ 入れ直しても残る（IndexedDB）
    pg.reload(); pg.wait_for_timeout(1200)
    check("開き直しても設定が残る", pg.evaluate("CFG")["day_start"] == "07:00")
    check("開き直しても実行中の作業が残る", "保守作業" in pg.inner_text("#nowWork"),
          pg.inner_text("#nowWork"))
    pg.click("nav.tabs button[data-page='log']"); pg.wait_for_timeout(600)
    check("開き直しても記録が残る", pg.locator("#logBody .row").count() == nall,
          (pg.locator("#logBody .row").count(), nall))

    # ⑩ 終了する
    pg.click("nav.tabs button[data-page='punch']"); pg.wait_for_timeout(400)
    pg.click("#bStop"); pg.wait_for_timeout(500)
    check("終了すると空になる", "何もしていません" in pg.inner_text("#nowWork"))

    # ⑪ CSV 取り込み（PC版のCSVを読む想定）
    pg.click("#bCfg"); pg.wait_for_timeout(400)
    with pg.expect_file_chooser() as fc:
        pg.click("#cImport")
    fc.value.set_files(path)
    pg.wait_for_timeout(1000)
    check("同じCSVを入れても重複しない", "0 件" in pg.inner_text("#toast"),
          pg.inner_text("#toast"))
    imp = os.path.join(DL, "取り込みテスト.csv")
    open(imp, "w", encoding="utf-8-sig", newline="").write(
        "開始日時,終了日時,作業名称,作業ID,ターゲット名称,ターゲットID,作業時間,作業時間(分),進捗度,メモ\r\n"
        "2026-08-01 09:00:00,2026-08-01 10:00:00,会社PCの作業,W900,案件A,T900,1:00,60,50,PC版から\r\n")
    pg.click("#bCfg"); pg.wait_for_timeout(400)
    with pg.expect_file_chooser() as fc2:
        pg.click("#cImport")
    fc2.value.set_files(imp)
    pg.wait_for_timeout(1000)
    check("別のCSVは取り込まれる", "1 件" in pg.inner_text("#toast"), pg.inner_text("#toast"))
    pg.click("nav.tabs button[data-page='mst']"); pg.wait_for_timeout(500)
    check("CSVに出てくる作業が足される", "W900" in pg.inner_text("#mstWork"))
    check("CSVに出てくるターゲットが足される", "T900" in pg.inner_text("#mstTarget"))

    # ⑫b 初期マスタの読み込み直し（CSVを差し替えて押す）
    orig = open(os.path.join(ROOT, "初期マスタ.csv"), "rb").read().decode("utf-8-sig")
    try:
        # PC版が出すのと同じ cp932 で置き換える（実際の運用と同じ形）
        open(os.path.join(ROOT, "初期マスタ.csv"), "w", encoding="cp932", newline="").write(
            orig.replace("\r\n", "\n").rstrip("\n") + "\n"
            "作業,W021,検討（改称）,作業,215,1\n"
            "作業,W030,英語学習,作業,300,1\n"
            "ターゲット,T010,資格試験,,10,1\n"
            "ターゲット,T011,使わない案件,,20,0\n")
        pg.click("nav.tabs button[data-page='mst']"); pg.wait_for_timeout(300)
        pg.click("#bCfg"); pg.wait_for_timeout(400)
        pg.click("#cMaster"); pg.wait_for_timeout(1200)
        tm2 = pg.inner_text("#toast")
        check("cp932 の初期マスタも読み込める", "初期マスタを読みました" in tm2, tm2)
        w21 = pg.evaluate("async()=>{const a=await getAll('works');"
                          "return a.find(w=>w.work_id==='W021');}")
        check("既にあるIDは名前と並びが更新される",
              w21["name"] == "検討（改称）" and w21["sort_no"] == 215, w21)
        w30 = pg.evaluate("async()=>{const a=await getAll('works');"
                          "return a.find(w=>w.work_id==='W030');}")
        check("無いIDは追加される（W030 英語学習）", w30 and w30["name"] == "英語学習", w30)
        t10 = pg.evaluate("async()=>{const a=await getAll('targets');"
                          "return a.find(t=>t.target_id==='T010');}")
        check("ターゲットも追加される（T010 資格試験）", t10 and t10["name"] == "資格試験", t10)
        t11 = pg.evaluate("async()=>{const a=await getAll('targets');"
                          "return a.find(t=>t.target_id==='T011');}")
        check("使う=0 は「使わない」で入る", t11 and t11["enabled"] == 0, t11)
        nrec = pg.evaluate("async()=>{const a=await getAll('entries');return a.length;}")
        check("記録の件数は変わらない（マスタ読み込みで消えない）", nrec >= 3, nrec)
        # CSVに無いIDは消えない（画面から足した W022 が残るか）
        w22 = pg.evaluate("async()=>{const a=await getAll('works');"
                          "return a.find(w=>w.work_id==='W022');}")
        check("CSVに無いIDは消されない（W022が残る）",
              bool(w22) and w22["name"] == "追加テスト作業", w22)
    finally:
        # PC版が出すのと同じ cp932 で置き換える（実際の運用と同じ形）
        # 元（UTF-8 BOM付き）に戻す
        open(os.path.join(ROOT, "初期マスタ.csv"), "w", encoding="utf-8-sig", newline="").write(orig)

    # ⑫ PC版のCSV（cp932）を取り込む
    imp932 = os.path.join(DL, "作業記録_cp932.csv")
    open(imp932, "w", encoding="cp932", newline="").write(
        "開始日時,終了日時,作業名称,作業ID,ターゲット名称,ターゲットID,作業時間,作業時間(分),進捗度,メモ\r\n"
        "2026-07-15 09:00:00,2026-07-15 11:30:00,設計書の見直し,W950,案件ベータ,T950,2:30,150,80,PC版から（cp932）\r\n"
        "2026-07-15 11:30:00,,実行中だった作業,W951,案件ベータ,T950,0:00,0,0,終了日時が空\r\n")
    # こちらでも作業を動かしておく（実行中が2つにならないか見る）
    pg.click("nav.tabs button[data-page='punch']"); pg.wait_for_timeout(400)
    pg.get_by_role("button", name="保守作業", exact=False).first.click(); pg.wait_for_timeout(500)
    pg.click("#bCfg"); pg.wait_for_timeout(400)
    with pg.expect_file_chooser() as fc3:
        pg.click("#cImport")
    fc3.value.set_files(imp932)
    pg.wait_for_timeout(1100)
    tm = pg.inner_text("#toast")
    check("cp932 と見分けて取り込む", "cp932" in tm, tm)
    check("cp932 の2件が入る", "2 件" in tm, tm)
    got = pg.evaluate("""async()=>{const a=await getAll('entries');
        return a.filter(r=>String(r.start_at).startsWith('2026-07-15'))
                .map(r=>[r.work_name,r.note,r.target_name,r.end_at]);}""")
    check("日本語が化けない（作業名）", any(r[0] == "設計書の見直し" for r in got), got)
    check("日本語が化けない（メモ）", any(r[1] == "PC版から（cp932）" for r in got), got)
    check("日本語が化けない（ターゲット名称）", any(r[2] == "案件ベータ" for r in got), got)
    nrun = pg.evaluate("async()=>{const a=await getAll('entries');return a.filter(r=>!r.end_at).length;}")
    check("実行中は1つだけになる", nrun == 1, nrun)
    check("残る実行中は手元の作業", "保守作業" in pg.inner_text("#nowWork"), pg.inner_text("#nowWork"))
    # UTF-8（BOM無し）も読めること
    impu8 = os.path.join(DL, "utf8nobom.csv")
    open(impu8, "w", encoding="utf-8", newline="").write(
        "開始日時,終了日時,作業名称,作業ID,ターゲット名称,ターゲットID,作業時間,作業時間(分),進捗度,メモ\r\n"
        "2026-07-16 09:00:00,2026-07-16 10:00:00,BOM無しの行,W952,,,1:00,60,0,\r\n")
    pg.click("#bCfg"); pg.wait_for_timeout(400)
    with pg.expect_file_chooser() as fc4:
        pg.click("#cImport")
    fc4.value.set_files(impu8)
    pg.wait_for_timeout(1000)
    check("BOM無しのUTF-8も読める", "UTF-8" in pg.inner_text("#toast") and "1 件" in pg.inner_text("#toast"),
          pg.inner_text("#toast"))
    got2 = pg.evaluate("""async()=>{const a=await getAll('entries');
        return a.filter(r=>String(r.start_at).startsWith('2026-07-16')).map(r=>r.work_name);}""")
    check("BOM無しでも日本語が化けない", got2 == ["BOM無しの行"], got2)

    # ⑫ PWA の材料
    mf = pg.evaluate("""async()=>{const r=await fetch('manifest.webmanifest');return await r.json();}""")
    check("manifest が読める", mf.get("display") == "standalone", mf.get("display"))
    check("manifest にアイコン3つ", len(mf.get("icons", [])) == 3)
    sw = pg.evaluate("""async()=>{const r=await fetch('sw.js');return r.status;}""")
    check("sw.js が読める", sw == 200, sw)
    reg = pg.evaluate("""async()=>{const r=await navigator.serviceWorker.getRegistrations();
                                   return r.length;}""")
    check("service worker が登録される", reg >= 1, reg)
    src2 = pg.evaluate("""async()=>{const r=await fetch('index.html');return await r.text();}""")
    check("起動30秒後にもう一度確認する",
          "setTimeout(() => checkUpdate(true), 30000)" in src2)
    check("10分ごとに確認する", "if(++tick % 10 === 0) checkUpdate(true)" in src2)
    swtxt = pg.evaluate("""async()=>{const r=await fetch('sw.js');return await r.text();}""")
    check("入れ物の名前が wta-v2", 'const CACHE = "wta-v2"' in swtxt)
    check("画面のHTMLはキャッシュを通さない",
          'cache: "no-store"' in swtxt and "isDoc(req)" in swtxt)
    check("初期マスタ.csv は addAll に入れていない", "初期マスタ.csv" not in
          swtxt.split("self.addEventListener")[0].split("const FILES")[1].split("];")[0])
    # 置き場を新しくしたら、開き直しで新しい画面になるか（実際に index.html を差し替える）
    ip = os.path.join(ROOT, "index.html")
    html = open(ip, encoding="utf-8").read()
    try:
        open(ip, "w", encoding="utf-8", newline="").write(
            html.replace('const APP_VERSION = "', 'const APP_VERSION = "9.9.9"; //', 1))
        pg.reload(); pg.wait_for_timeout(1500)
        check("置き場を新しくすると開き直しで新版になる",
              pg.inner_text("#ver") == "v9.9.9", pg.inner_text("#ver"))
    finally:
        open(ip, "w", encoding="utf-8", newline="").write(html)
        pg.reload(); pg.wait_for_timeout(1500)
    ver0 = open(ip, encoding="utf-8").read().split('const APP_VERSION = "')[1].split('"')[0]
    check("元の版に戻せる", pg.inner_text("#ver") == "v" + ver0, pg.inner_text("#ver"))

    # ⑬ 新しい版のお知らせ
    ip2 = os.path.join(ROOT, "index.html")
    html2 = open(ip2, encoding="utf-8").read()
    ver_now = html2.split('const APP_VERSION = "')[1].split('"')[0]
    check("ふだんはお知らせが出ていない",
          not pg.locator("#upd").evaluate("el=>el.classList.contains('on')"))
    try:
        open(ip2, "w", encoding="utf-8", newline="").write(
            html2.replace('const APP_VERSION = "' + ver_now + '"',
                          'const APP_VERSION = "9.8.7"', 1))
        pg.evaluate("checkUpdate(true)"); pg.wait_for_timeout(800)
        on = pg.locator("#upd").evaluate("el=>el.classList.contains('on')")
        check("置き場が新しいとお知らせが出る", on, on)
        check("お知らせに新旧の版が出る",
              "v9.8.7" in pg.inner_text("#updText") and "v" + ver_now in pg.inner_text("#updText"),
              pg.inner_text("#updText"))
        # ［あとで］で消える／同じ版では出し直さない
        pg.click("#updNo"); pg.wait_for_timeout(300)
        check("［あとで］で消える",
              not pg.locator("#upd").evaluate("el=>el.classList.contains('on')"))
        pg.evaluate("checkUpdate(true)"); pg.wait_for_timeout(600)
        check("あとでを押した版は出し直さない",
              not pg.locator("#upd").evaluate("el=>el.classList.contains('on')"))
        # ⚙の［新しい版があるか確認する］でもう一度見に行ける
        pg.click("#bCfg"); pg.wait_for_timeout(400)
        body = pg.inner_text("#dlgBody")
        check("⚙に最後に確認した時刻が出る",
              "更新の確認：最後に見たのは" in body and "10分ごと" in body,
              [l for l in body.splitlines() if "更新の確認" in l])
        pg.click("#cUpd"); pg.wait_for_timeout(900)
        check("⚙から確認するとまた出る",
              pg.locator("#upd").evaluate("el=>el.classList.contains('on')"))
        # ［更新する］で読み直し、新しい版になる
        pg.click("#updGo"); pg.wait_for_timeout(2500)
        check("［更新する］で新しい版になる", pg.inner_text("#ver") == "v9.8.7",
              pg.inner_text("#ver"))
    finally:
        open(ip2, "w", encoding="utf-8", newline="").write(html2)
        pg.reload(); pg.wait_for_timeout(1500)
    check("元の版に戻る", pg.inner_text("#ver") == "v" + ver_now, pg.inner_text("#ver"))
    check("戻したあとはお知らせが出ない",
          not pg.locator("#upd").evaluate("el=>el.classList.contains('on')"))

    pg.screenshot(path=os.path.join(ROOT, "_shot_punch.png"))
    pg.click("nav.tabs button[data-page='log']"); pg.wait_for_timeout(500)
    pg.screenshot(path=os.path.join(ROOT, "_shot_log.png"))
    pg.click("nav.tabs button[data-page='sum']"); pg.wait_for_timeout(700)
    pg.screenshot(path=os.path.join(ROOT, "_shot_sum.png"))

    # ⑭ 広い画面（PCのブラウザ）で間延びしないか
    wide = ctx.new_page()
    wide.set_viewport_size({"width": 1280, "height": 900})
    wide.goto("http://127.0.0.1:%d/index.html" % PORT)
    wide.wait_for_timeout(1200)
    box = wide.evaluate("""()=>{
      const m = document.querySelector('main').getBoundingClientRect();
      const h = document.querySelector('header').getBoundingClientRect();
      const n = document.querySelector('nav.tabs').getBoundingClientRect();
      return {w: Math.round(m.width), left: Math.round(m.left),
              right: Math.round(window.innerWidth - m.right),
              hw: Math.round(h.width), nw: Math.round(n.width)};
    }""")
    check("広い画面で幅に上限がかかる（560px）", box["w"] <= 562, box)
    check("中央に寄る", abs(box["left"] - box["right"]) <= 2, box)
    check("ヘッダ・下タブも同じ幅", box["hw"] == box["w"] and box["nw"] == box["w"], box)
    check("広い画面でも横スクロールが出ない",
          wide.evaluate("()=>document.documentElement.scrollWidth <= window.innerWidth"))
    ncol = wide.evaluate("""()=>{
      const g = document.getElementById('workGrid');
      return getComputedStyle(g).gridTemplateColumns.split(' ').length;}""")
    check("作業ボタンが3列に収まる", 2 <= ncol <= 3, ncol)
    wide.close()
    # 狭い画面（スマホ）では今までどおり画面いっぱい
    narrow = pg.evaluate("""()=>{
      const m = document.querySelector('main').getBoundingClientRect();
      return [Math.round(m.width), window.innerWidth];}""")
    check("スマホの幅では今までどおり全幅", narrow[0] == narrow[1], narrow)

    check("画面のエラーが出ていない", not errs, errs[:3])
    br.close()

srv.shutdown()
print("\n通った: %d / だめ: %d" % (len(OK), len(NG)))
for x in NG: print("  NG  " + x)
sys.exit(1 if NG else 0)

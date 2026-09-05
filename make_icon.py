# -*- coding: utf-8 -*-
"""Android版のアイコンを作る。PC版（濃紺の角丸に生成りの時計）と同じ見た目。"""
from PIL import Image, ImageDraw
import math, os

NAVY = (31, 78, 121, 255)     # #1F4E79
CREAM = (246, 241, 228, 255)  # #F6F1E4

def clock(size, pad_ratio, radius_ratio, bg_full=False):
    """pad_ratio: 外周の余白（maskable 用に大きくする）"""
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if bg_full:
        d.rectangle([0, 0, S, S], fill=NAVY)
    else:
        r = int(S * radius_ratio)
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=r, fill=NAVY)
    # 時計の円
    p = int(S * pad_ratio)
    box = [p, p, S - p, S - p]
    w = max(2, int(S * 0.045))
    d.ellipse(box, outline=CREAM, width=w)
    cx = cy = S / 2.0
    rr = (S - 2 * p) / 2.0
    # 12/3/6/9 の目盛り
    tw = max(2, int(S * 0.035))
    for ang in (0, 90, 180, 270):
        a = math.radians(ang - 90)
        x1 = cx + math.cos(a) * rr * 0.80
        y1 = cy + math.sin(a) * rr * 0.80
        x2 = cx + math.cos(a) * rr * 0.62
        y2 = cy + math.sin(a) * rr * 0.62
        d.line([x1, y1, x2, y2], fill=CREAM, width=tw)
    # 針（10:10 ではなく 9:00 起点＝作業の始まり）
    hw = max(3, int(S * 0.050))
    a = math.radians(60 - 90)        # 短針 2時方向
    d.line([cx, cy, cx + math.cos(a) * rr * 0.42, cy + math.sin(a) * rr * 0.42],
           fill=CREAM, width=hw)
    a = math.radians(-90)            # 長針 12時方向
    d.line([cx, cy, cx + math.cos(a) * rr * 0.62, cy + math.sin(a) * rr * 0.62],
           fill=CREAM, width=max(2, int(S * 0.040)))
    d.ellipse([cx - S*0.030, cy - S*0.030, cx + S*0.030, cy + S*0.030], fill=CREAM)
    return im.resize((size, size), Image.LANCZOS)

os.makedirs("icon", exist_ok=True)
clock(192, 0.20, 0.22).save("icon/icon-192.png")
clock(512, 0.20, 0.22).save("icon/icon-512.png")
# maskable は端が丸く切られるので、中身を小さめにして背景を全面に
clock(512, 0.30, 0.0, bg_full=True).save("icon/icon-maskable-512.png")
# Windows 側と並べたいとき用
clock(512, 0.20, 0.22).save("icon/作業時間管理_android.png")
print("ok", [ (f, os.path.getsize("icon/"+f)) for f in sorted(os.listdir("icon")) ])

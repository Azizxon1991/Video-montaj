"""Animatsiyali yozuvlar (PNG ketma-ketligi) va light-leak (yorug'lik chaqnashi) qatlami."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
FONT_DIR = "/usr/share/fonts/opentype/inter"
GOLD = (232, 194, 122)
WHITE = (255, 255, 255)

# (boshlanish, tugash, kicker, asosiy matn, markaz y) - sekundlarda, yakuniy video vaqti
CAPTIONS = [
    (6.6, 10.9, "R E S T A U R A N T", "MARRAKESH", 1430),
    (12.45, 15.75, "JAMOA", "Loyiha muhokamasi", 1430),
    (20.45, 23.55, "NAZORAT OSTIDA", "Chorvachilik fermasi", 1430),
    (28.6, 33.8, "", "Sifat · Ishonch · Kelajak", 960),
]
BOX_H = 420  # har bir yozuv uchun kesma balandligi


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * x)


def tracked_layout(text, fnt, tracking):
    xs, x = [], 0.0
    for ch in text:
        xs.append(x)
        x += fnt.getlength(ch) + tracking
    return xs, x - tracking


def render_caption(kicker, main, t, dur, centered_title=False):
    """Bitta kadr (W x BOX_H RGBA). t - yozuv boshidan vaqt."""
    img = Image.new("RGBA", (W, BOX_H), (0, 0, 0, 0))
    txt = Image.new("RGBA", (W, BOX_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)

    out_p = ease_in_out((t - (dur - 0.45)) / 0.45)  # chiqish animatsiyasi
    global_a = 1 - out_p
    lift = -24 * out_p

    f_main = font("InterDisplay-SemiBold.otf", 84 if not centered_title else 64)
    f_kick = font("Inter-Medium.otf", 30)
    tr_main = 6 if main.isupper() else 1
    xs, wmain = tracked_layout(main, f_main, tr_main)
    x0 = (W - wmain) / 2
    base_y = BOX_H / 2 - 10

    # kicker (tepada, oltin rang)
    if kicker:
        kx, kw = tracked_layout(kicker, f_kick, 4)
        ka = ease_out((t - 0.05) / 0.5) * global_a
        ky = base_y - 92 + 16 * (1 - ease_out((t - 0.05) / 0.5)) + lift
        kx0 = (W - kw) / 2
        for ch, cx in zip(kicker, kx):
            d.text((kx0 + cx, ky), ch, font=f_kick, fill=GOLD + (int(255 * ka),))

    # asosiy matn: harflar ketma-ket pastdan chiqadi
    for i, (ch, cx) in enumerate(zip(main, xs)):
        lt = (t - 0.15 - i * 0.028) / 0.5
        a = ease_out(lt) * global_a
        if a <= 0:
            continue
        dy = 38 * (1 - ease_out(lt))
        d.text((x0 + cx, base_y - 40 + dy + lift), ch, font=f_main, fill=WHITE + (int(255 * a),))

    # ingichka chiziq markazdan ikki tomonga o'sadi
    lp = ease_in_out((t - 0.35) / 0.7)
    half = (min(wmain, 520) / 2) * lp * (1 - 0.3 * out_p)
    ly = base_y + (72 if not centered_title else 56) + lift
    if half > 1:
        d.rectangle([W / 2 - half, ly, W / 2 + half, ly + 3], fill=GOLD + (int(230 * global_a),))

    # matn orqasida yumshoq qorong'i fon (yorug' kadrlarda ham o'qilishi uchun)
    vis = ease_out(t / 0.4) * global_a
    if vis > 0:
        bd = Image.new("L", (W, BOX_H), 0)
        hw = min(wmain / 2 + 110, W / 2 - 10)
        ImageDraw.Draw(bd).ellipse([W / 2 - hw, base_y - 120, W / 2 + hw, base_y + 110], fill=int(120 * vis))
        backdrop = Image.new("RGBA", (W, BOX_H), (0, 0, 0, 0))
        backdrop.putalpha(bd.filter(ImageFilter.GaussianBlur(45)))
        img = Image.alpha_composite(img, backdrop)

    # yumshoq soya (o'qilishi uchun)
    alpha = txt.split()[3]
    shadow = Image.new("RGBA", (W, BOX_H), (0, 0, 0, 0))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.75)))
    img = Image.alpha_composite(img, shadow)
    shadow2 = Image.new("RGBA", (W, BOX_H), (0, 0, 0, 0))
    shadow2.putalpha(alpha.filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.5)))
    img = Image.alpha_composite(img, shadow2)
    return Image.alpha_composite(img, txt)


def write_captions(outdir):
    meta = []
    for k, (t0, t1, kicker, main, cy) in enumerate(CAPTIONS):
        d = os.path.join(outdir, f"cap{k}")
        os.makedirs(d, exist_ok=True)
        dur = t1 - t0
        n = int(round(dur * FPS))
        for f in range(n):
            render_caption(kicker, main, f / FPS, dur, centered_title=(cy < 1200)).save(os.path.join(d, f"{f:04d}.png"))
        meta.append((d, t0, cy - BOX_H // 2))
    return meta


# ------------------------------------------------------------ light leaks
LW, LH = 270, 480
LEAKS = [  # (markaz vaqt, yarim kenglik, kuch)
    (0.35, 1.0, 0.75),
    (4.0, 0.75, 0.85),
    (24.0, 0.9, 0.85),
    (33.0, 1.3, 0.55),
]
COLS = np.array([[255, 140, 50], [255, 85, 95], [255, 205, 130]], dtype=np.float32) / 255


def leak_frame(t, yy, xx):
    inten = 0.0
    for c, hw, p in LEAKS:
        x = (t - c) / hw
        if abs(x) < 1:
            inten = max(inten, p * (0.5 + 0.5 * np.cos(np.pi * x)))
    if inten <= 0:
        return None
    img = np.zeros((LH, LW, 3), np.float32)
    for k in range(3):
        cx = 0.5 + 0.55 * np.sin(0.7 * t + k * 2.1)
        cy = 0.3 + 0.45 * np.sin(0.45 * t + k * 1.3)
        r = 0.35 + 0.1 * np.sin(1.1 * t + k)
        g = np.exp(-(((xx - cx) / r) ** 2 + ((yy - cy) / (r * 1.2)) ** 2))
        img += g[..., None] * COLS[k]
    return np.clip(img * inten, 0, 1)


def write_leaks(path, total):
    yy, xx = np.mgrid[0:LH, 0:LW].astype(np.float32)
    yy /= LH
    xx /= LW
    blank = np.zeros((LH, LW, 3), np.uint8).tobytes()
    with open(path, "wb") as fh:
        for f in range(int(round(total * FPS))):
            fr = leak_frame(f / FPS, yy, xx)
            fh.write(blank if fr is None else (fr * 255).astype(np.uint8).tobytes())
    return LW, LH


if __name__ == "__main__":
    out = sys.argv[1]
    print(write_captions(out))
    print(write_leaks(os.path.join(out, "leaks.rgb"), 33.8))

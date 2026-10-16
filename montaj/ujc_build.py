"""UJC Qoʻqon ochilishi: 1 video + 11 rasmdan vertikal (1080x1920) professional rolik.

Ishlatish:
    python3 ujc_build.py <manba_papka> <chiqish.mp4> [ish_papka]

- Videoning asl ovozi butunlay olib tashlanadi, o'rniga ujc_music.py dagi original musiqa.
- Rasmlar: sub-pikselli Ken Burns / pan (perspective filtri), rang korreksiyasi.
- Intro: ochilish afishasi "karta" ko'rinishida; yakun: UJC logotipi animatsiyasi.
- xfade o'tishlar, beat-ga mos zoom-punch, light leak, vinyetka, grain, yozuvlar,
  burchakda kichik UJC logotipi.
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import overlays  # noqa: E402
import ujc_music  # noqa: E402
from build import HLG2SDR, shake_expr  # noqa: E402

FPS = 30
W, H = 1080, 1920
TOTAL = 41.0
FONT_DIR = "/usr/share/fonts/opentype/inter"
JP_FONT = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
ACCENT = (255, 112, 122)  # yapon qizili (yorug'roq, o'qilishi uchun)

VIDEO = "d4a7cad8-IMG_2394.mov"
POSTER = "192cb7de-image.jpg"
LOGO_CIRCLE = (695, 186, 158)  # afishadagi logotip: markaz x, y, radius

# (rasm, boshlang'ich oyna, yakuniy oyna) - oyna = (cx, cy, balandlik ulushi), normallashtirilgan
SHOTS = [
    ("d271c1f6-image.jpg", (0.30, 0.50, 1.00), (0.72, 0.52, 0.94)),  # aeroport, non bilan kutib olish
    ("4afd0e4d-image.jpg", (0.38, 0.50, 1.00), (0.62, 0.50, 1.00)),  # mehmonlar, ochilish marosimi
    ("5a0889f5-image.jpg", (0.42, 0.50, 1.00), (0.45, 0.56, 0.86)),  # nutq
    ("313b244b-image.jpg", (0.44, 0.55, 0.90), (0.56, 0.56, 0.86)),  # markaz bilan tanishuv
    ("d080e7c4-image.jpg", (0.46, 0.56, 0.96), (0.44, 0.60, 0.82)),  # zal
    ("ba769358-image.jpg", (0.50, 0.50, 1.00), (0.47, 0.52, 0.86)),  # muzokaralar stoli
    ("3e45d0f4-image.jpg", (0.33, 0.60, 0.80), (0.66, 0.60, 0.80)),  # sinf / taqdimot
    ("a18d74c7-image.jpg", (0.50, 0.58, 0.82), (0.36, 0.60, 0.70)),  # qo'l berib ko'rishish
    ("0a80687b-image.jpg", (0.34, 0.56, 0.84), (0.55, 0.56, 0.84)),  # esdalik surati
    ("ecc42251-image.jpg", (0.48, 0.57, 0.86), (0.50, 0.60, 0.78)),  # mehmonlar zali
]
# Klip tartibi: poster, 10 rasm, video, end card
TRANSITIONS = [  # (turi, davomiylik, kesim vaqti)
    ("hblur", 0.5, 4.0),
    ("smoothleft", 0.5, 8.0),
    ("fade", 0.4, 10.5),
    ("smoothup", 0.5, 13.0),
    ("hblur", 0.4, 15.0),
    ("fade", 0.5, 17.0),
    ("fadewhite", 0.4, 20.0),
    ("smoothleft", 0.4, 22.5),
    ("fade", 0.4, 24.5),
    ("hblur", 0.4, 26.5),
    ("fade", 0.5, 28.0),
    ("fadeblack", 0.8, 34.0),
]
CAPTIONS = [  # (boshi, oxiri, kicker, matn, markaz y)
    (4.45, 7.75, "XUSH KELIBSIZ", "Mehmonlar kutib olindi", 1450),
    (10.75, 12.80, "QOʻQON · 8-OKTABR", "Tantanali ochilish", 1450),
    (13.30, 16.75, "UJC QOʻQON", "Markaz bilan tanishuv", 1450),
    (17.30, 19.80, "OʻZBEKISTON · YAPONIYA", "Hamkorlik uchrashuvi", 1450),
    (20.35, 22.30, "UJC", "Yangi imkoniyatlar", 1450),
    (28.60, 31.90, "MATBUOT", "Jurnalistlar bilan suhbat", 1450),
]
LEAKS = [(0.4, 1.1, 0.7), (4.0, 0.7, 0.8), (20.0, 0.7, 0.8), (34.6, 1.2, 0.6)]


def run(cmd):
    print("$", " ".join(cmd)[:240], flush=True)
    subprocess.run(cmd, check=True)


def seg_durations():
    cuts = [0.0] + [c for _, _, c in TRANSITIONS] + [TOTAL]
    tds = [0.0] + [d for _, d, _ in TRANSITIONS] + [0.0]
    return [cuts[i + 1] - cuts[i] + tds[i] / 2 + tds[i + 1] / 2 for i in range(len(cuts) - 1)]


def enc(out):
    return ["-an", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p", "-r", str(FPS), out]


def window_rect(img_w, img_h, cx, cy, hf):
    """9:16 oyna (normallashtirilgan x0,y0,x1,y1), rasm chegarasida."""
    h = hf
    w = hf * img_h * 9 / 16 / img_w
    if w > 1:  # juda tor rasm: kenglik bo'yicha cheklash
        h, w = h / w, 1.0
    x0 = min(max(cx - w / 2, 0), 1 - w)
    y0 = min(max(cy - h / 2, 0), 1 - h)
    return x0, y0, x0 + w, y0 + h


def move_filter(r0, r1, dur, ease="linear"):
    """Oyna r0 -> r1 harakati, perspective orqali (sub-piksel, kubik)."""
    p = f"min(on/{dur * FPS:.2f},1)"
    if ease == "out":
        p = f"(1-pow(1-{p},3))"
    elif ease == "inout":
        p = f"(0.5-0.5*cos(PI*{p}))"

    def lerp(a, b):
        return f"({a:.5f}+({b - a:.5f})*{p})"
    xl, yt, xr, yb = (lerp(a, b) for a, b in zip(r0, r1))
    return (f"perspective=x0='W*{xl}':y0='H*{yt}':x1='W*{xr}':y1='H*{yt}':x2='W*{xl}':y2='H*{yb}'"
            f":x3='W*{xr}':y3='H*{yb}':interpolation=cubic:eval=frame")


PHOTO_GRADE = ("eq=contrast=1.05:saturation=1.07:gamma=0.99,"
               "colorbalance=rs=0.01:bs=-0.01:rm=0.015:bm=-0.015:rh=0.01:bh=-0.01,unsharp=5:5:0.4:5:5:0.0")


def render_photo(path, start, end, dur, out, ease="linear"):
    im = Image.open(path)
    iw, ih = im.size
    scale = min(1.0, 2400 / ih)
    sw, sh = int(iw * scale) // 2 * 2, int(ih * scale) // 2 * 2
    r0 = window_rect(iw, ih, *start)
    r1 = window_rect(iw, ih, *end)
    vf = ",".join([f"scale={sw}:{sh}:flags=lanczos", "format=yuv444p", move_filter(r0, r1, dur, ease),
                   f"scale={W}:{H}:flags=lanczos", PHOTO_GRADE, "format=yuv420p", "setsar=1"])
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", path,
         "-vf", vf] + enc(out))


def rounded_card(img, radius):
    mask = Image.new("L", (img.width * 3, img.height * 3), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, mask.width - 1, mask.height - 1], radius * 3, fill=255)
    return mask.resize(img.size, Image.LANCZOS)


def render_poster(src, dur, out, work):
    """Afisha: xira fon + soyali karta, 1.5x o'lchamda (keyin zoom-out harakat)."""
    s = 1.5
    cw, ch = int(W * s), int(H * s)
    poster = Image.open(src).convert("RGB")
    bg = poster.resize((int(poster.width * ch / poster.height), ch), Image.LANCZOS)
    bg = bg.crop(((bg.width - cw) // 2, 0, (bg.width - cw) // 2 + cw, ch))
    bg = bg.filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (40, 12, 18)), 0.35)
    card_w = int(960 * s)
    card = poster.resize((card_w, int(poster.height * card_w / poster.width)), Image.LANCZOS)
    mask = rounded_card(card, int(26 * s))
    x0, y0 = (cw - card.width) // 2, int(930 * s) - card.height // 2
    sh = Image.new("L", bg.size, 0)
    sh.paste(mask, (x0, y0 + int(24 * s)))
    sh = sh.filter(ImageFilter.GaussianBlur(int(30 * s))).point(lambda v: int(v * 0.7))
    bg = Image.composite(Image.new("RGB", bg.size, (0, 0, 0)), bg, sh)
    bg.paste(card, (x0, y0), mask)
    still = os.path.join(work, "poster_card.png")
    bg.save(still)
    z0 = 1.10  # zoom-out: kartaga "kirib kelish" hissi
    a = (1 - 1 / z0) / 2
    vf = ",".join(["format=yuv444p", move_filter((a, a, 1 - a, 1 - a), (0, 0, 1, 1), dur, "out"),
                   f"scale={W}:{H}:flags=lanczos", "format=yuv420p", "setsar=1"])
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", still,
         "-vf", vf] + enc(out))


def render_interview(src, dur, out, work):
    trf = os.path.join(work, "interview.trf")
    cut = ["-ss", "0.4", "-t", f"{dur + 0.1:.2f}", "-i", src]
    pre = f"fps={FPS},{HLG2SDR},scale={W}:{H}:flags=lanczos"
    run(["ffmpeg", "-v", "error", "-y"] + cut + ["-vf", f"{pre},vidstabdetect=shakiness=5:result={trf}",
                                                "-f", "null", "-"])
    vf = ",".join([pre, f"vidstabtransform=input={trf}:smoothing=20:zoom=3:interpol=bicubic",
                   "eq=brightness=0.015:contrast=1.06:saturation=1.08:gamma=1.06",
                   "colorbalance=rs=0.0:bs=0.01:rm=0.02:bm=-0.02",
                   "unsharp=5:5:0.5:5:5:0.0", f"trim=duration={dur}", "setsar=1"])
    run(["ffmpeg", "-v", "error", "-y"] + cut + ["-vf", vf] + enc(out))


# ------------------------------------------------------------- logotip va end card
def logo_image(src, size):
    poster = Image.open(src).convert("RGB")
    cx, cy, r = LOGO_CIRCLE
    crop = poster.crop((cx - r, cy - r, cx + r, cy + r)).resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
    out = crop.convert("RGBA")
    out.putalpha(m.resize((size, size), Image.LANCZOS))
    return out


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def text_center(draw, y, text, font, fill, tracking=0):
    widths = [font.getlength(c) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = (W - total) / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=font, fill=fill)
        x += w + tracking


def render_endcard(src_dir, dur, out):
    bg_src = Image.open(os.path.join(src_dir, "ba769358-image.jpg")).convert("RGB")
    k = max(W * 1.12 / bg_src.width, H * 1.12 / bg_src.height)  # kadrni to'liq qoplash
    bg_src = bg_src.resize((int(bg_src.width * k), int(bg_src.height * k)), Image.LANCZOS)
    bg_src = bg_src.filter(ImageFilter.GaussianBlur(26))
    bg_arr = np.asarray(bg_src).astype(np.float32)
    navy = np.array([10, 18, 40], np.float32)
    bg_arr = bg_arr * 0.32 + navy * 0.68
    yy, xx = np.mgrid[0:bg_arr.shape[0], 0:bg_arr.shape[1]].astype(np.float32)
    cxb, cyb = bg_arr.shape[1] / 2, bg_arr.shape[0] * 0.40
    glow = np.exp(-(((xx - cxb) / 520) ** 2 + ((yy - cyb) / 520) ** 2))[..., None]
    bg_arr = bg_arr + glow * np.array([120, 40, 50], np.float32) * 0.55
    bg_src = Image.fromarray(np.clip(bg_arr, 0, 255).astype(np.uint8))

    logo_size = 460
    logo = logo_image(os.path.join(src_dir, POSTER), logo_size)
    f_main = ImageFont.truetype(os.path.join(FONT_DIR, "InterDisplay-SemiBold.otf"), 60)
    f_kick = ImageFont.truetype(os.path.join(FONT_DIR, "Inter-Medium.otf"), 32)
    f_slog = ImageFont.truetype(os.path.join(FONT_DIR, "Inter-LightItalic.otf"), 33)
    f_jp = ImageFont.truetype(JP_FONT, 30) if os.path.exists(JP_FONT) else None
    logo_cy = 770

    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-"] + enc(out), stdin=subprocess.PIPE)
    n = int(round(dur * FPS))
    for f in range(n):
        t = f / FPS
        # fon: sekin zoom (afin, sub-piksel)
        z = 1.0 + 0.05 * t / dur
        sw, sh = W / z, H / z
        ox, oy = (bg_src.width - sw) / 2, (bg_src.height - sh) / 2
        frame = bg_src.transform((W, H), Image.AFFINE, (sw / W, 0, ox, 0, sh / H, oy), Image.BICUBIC)
        frame = frame.convert("RGBA")
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)

        # to'lqin halqalar
        for k, t0 in enumerate((0.45, 0.85)):
            rp = (t - t0) / 1.4
            if 0 < rp < 1:
                rr = logo_size / 2 + 20 + 260 * ease_out(rp)
                a = int(150 * (1 - rp))
                d.ellipse([W / 2 - rr, logo_cy - rr, W / 2 + rr, logo_cy + rr], outline=(255, 255, 255, a), width=3)
        frame = Image.alpha_composite(frame, lay)

        # logotip: masshtab + paydo bo'lish, oq halqa va soya
        lp = ease_out((t - 0.25) / 0.8)
        if lp > 0:
            s = int(logo_size * (0.82 + 0.18 * lp))
            lg = logo.resize((s, s), Image.LANCZOS)
            ring = Image.new("RGBA", (s + 16, s + 16), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse([0, 0, s + 15, s + 15], fill=(255, 255, 255, 255))
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).ellipse([W / 2 - s / 2 - 10, logo_cy - s / 2 + 8, W / 2 + s / 2 + 10,
                                            logo_cy + s / 2 + 34], fill=(0, 0, 0, int(160 * lp)))
            shadow = shadow.filter(ImageFilter.GaussianBlur(28))
            frame = Image.alpha_composite(frame, shadow)
            ring.alpha_composite(lg, (8, 8))
            ring.putalpha(ring.split()[3].point(lambda v: int(v * lp)))
            frame.alpha_composite(ring, (int(W / 2 - (s + 16) / 2), int(logo_cy - (s + 16) / 2)))

        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(txt)
        k_a = ease_out((t - 0.9) / 0.6)
        m_a = ease_out((t - 1.15) / 0.7)
        s_a = ease_out((t - 1.9) / 0.8)
        if m_a > 0:
            text_center(d, 1080 + 30 * (1 - m_a), "Oʻzbekiston–Yaponiya markazi", f_main,
                        (255, 255, 255, int(255 * m_a)), 1)
        if k_a > 0:
            text_center(d, 1170 + 20 * (1 - k_a), "QOʻQON  ·  8-OKTABR", f_kick, ACCENT + (int(255 * k_a),), 6)
            lw = 220 * ease_out((t - 1.0) / 0.8)
            d.rectangle([W / 2 - lw, 1236, W / 2 + lw, 1238], fill=(255, 255, 255, int(150 * k_a)))
        if s_a > 0:
            text_center(d, 1290, "Yangi imkoniyatlar yaratamiz,", f_slog, (235, 238, 245, int(220 * s_a)))
            text_center(d, 1336, "isteʼdodlarni birlashtiramiz.", f_slog, (235, 238, 245, int(220 * s_a)))
            if f_jp:
                text_center(d, 1420, "ウズベキスタン・日本センター", f_jp, (255, 255, 255, int(140 * s_a)), 2)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh.putalpha(txt.split()[3].filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.6)))
        frame = Image.alpha_composite(frame, sh)
        frame = Image.alpha_composite(frame, txt)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("endcard encode failed")


def logo_bug(src_dir, work):
    """Burchak uchun kichik logotip (oq halqa bilan) PNG."""
    size = 112
    lg = logo_image(os.path.join(src_dir, POSTER), size)
    canvas = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([16, 22, size + 26, size + 32], fill=(0, 0, 0, 120))
    canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(canvas).ellipse([15, 15, size + 24, size + 24], fill=(255, 255, 255, 255))
    canvas.alpha_composite(lg, (20, 20))
    p = os.path.join(work, "logo_bug.png")
    canvas.save(p)
    return p


# ------------------------------------------------------------- bosqichlar
def render_segments(src_dir, work):
    D = seg_durations()
    segs = []
    out = os.path.join(work, "u00.mp4")
    render_poster(os.path.join(src_dir, POSTER), D[0], out, work)
    segs.append(out)
    for i, (img, a, b) in enumerate(SHOTS):
        out = os.path.join(work, f"u{i + 1:02d}.mp4")
        render_photo(os.path.join(src_dir, img), a, b, D[i + 1], out)
        segs.append(out)
    out = os.path.join(work, "u11.mp4")
    render_interview(os.path.join(src_dir, VIDEO), D[11], out, work)
    segs.append(out)
    out = os.path.join(work, "u12.mp4")
    render_endcard(src_dir, D[12] + 0.2, out)
    segs.append(out)
    return segs


def render_audio(work):
    raw = os.path.join(work, "ujc_music_raw.wav")
    ujc_music.m.write_wav(raw, ujc_music.build())
    pre = "highpass=f=28,lowpass=f=15500,acompressor=threshold=-14dB:ratio=2.5:attack=15:release=180:makeup=1"
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af",
                        pre + ",loudnorm=I=-14:TP=-1.2:LRA=9:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    js = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.2:LRA=9:measured_I={js['input_i']}:measured_TP={js['input_tp']}"
          f":measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}"
          f":offset={js['target_offset']}:linear=true")
    out = os.path.join(work, "ujc_music.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", f"{pre},{ln},aresample=48000,atrim=0:{TOTAL}", out])
    return out


def compose(segs, audio, src_dir, work, out):
    overlays.GOLD = ACCENT
    overlays.CAPTIONS = CAPTIONS
    overlays.LEAKS = LEAKS
    caps = overlays.write_captions(os.path.join(work, "ujc_caps"))
    lw, lh = overlays.write_leaks(os.path.join(work, "ujc_leaks.rgb"), TOTAL)
    bug = logo_bug(src_dir, work)

    inputs = []
    for s in segs:
        inputs += ["-i", s]
    li = len(segs)
    inputs += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{lw}x{lh}", "-r", str(FPS),
               "-i", os.path.join(work, "ujc_leaks.rgb")]
    bi = li + 1
    inputs += ["-loop", "1", "-framerate", str(FPS), "-t", str(TOTAL), "-i", bug]
    cap_idx = []
    for d, _, _ in caps:
        cap_idx.append(bi + 1 + len(cap_idx))
        inputs += ["-framerate", str(FPS), "-i", os.path.join(d, "%04d.png")]
    ai = bi + 1 + len(caps)
    inputs += ["-i", audio]

    D = seg_durations()
    fc = [f"[{i}:v]settb=AVTB,fps={FPS},format=yuv420p,setsar=1[c{i}]" for i in range(len(segs))]
    prev, acc = "c0", D[0]
    for i, (kind, td, _) in enumerate(TRANSITIONS):
        off = acc - td
        fc.append(f"[{prev}][c{i + 1}]xfade=transition={kind}:duration={td}:offset={off:.3f}[x{i}]")
        prev, acc = f"x{i}", off + D[i + 1]
    shake = shake_expr(((120, 1.0), (600, 0.8)))
    fc.append(f"[{prev}]{shake},format=gbrp[base]")
    fc.append(f"[{li}:v]scale={W}:{H}:flags=bicubic,gblur=sigma=20,format=gbrp[leak]")
    fc.append("[base][leak]blend=all_mode=screen:all_opacity=0.8,format=yuv420p,"
              "vignette=angle=PI/5.5:mode=forward,noise=c0s=3:c0f=t+u[graded]")
    # burchakdagi logotip: 4.4 s dan 33.6 s gacha, yumshoq paydo bo'lish/yo'qolish
    fc.append(f"[{bi}:v]format=rgba,colorchannelmixer=aa=0.92,"
              f"fade=t=in:st=4.4:d=0.6:alpha=1,fade=t=out:st=33.2:d=0.5:alpha=1[bug]")
    fc.append(f"[graded][bug]overlay=x={W - 152 - 40}:y=96:format=auto[g2]")
    prev = "g2"
    for k, ((_, t0, y), ci) in enumerate(zip(caps, cap_idx)):
        fc.append(f"[{ci}:v]format=rgba,setpts=PTS-STARTPTS+{t0}/TB[cap{k}]")
        fc.append(f"[{prev}][cap{k}]overlay=x=0:y={y}:eof_action=pass:format=auto[o{k}]")
        prev = f"o{k}"
    fc.append(f"[{prev}]fade=t=in:st=0:d=0.5,fade=t=out:st={TOTAL - 1.2}:d=1.2,"
              f"trim=duration={TOTAL},format=yuv420p,setsar=1[vout]")

    run(["ffmpeg", "-v", "error", "-stats", "-y"] + inputs + [
        "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", f"{ai}:a",
        "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M",
        "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-r", str(FPS), "-g", "60", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart", "-t", str(TOTAL), out])


def main():
    src_dir, out = sys.argv[1], sys.argv[2]
    work = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(out)), "_work")
    os.makedirs(work, exist_ok=True)
    only = os.environ.get("ONLY", "segments,audio,compose").split(",")
    segs = [os.path.join(work, f"u{i:02d}.mp4") for i in range(13)]
    if "segments" in only:
        segs = render_segments(src_dir, work)
    audio = os.path.join(work, "ujc_music.wav")
    if "audio" in only:
        audio = render_audio(work)
    if "compose" in only:
        compose(segs, audio, src_dir, work, out)


if __name__ == "__main__":
    main()

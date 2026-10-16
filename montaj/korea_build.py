"""Oʻzbekiston–Koreya tajriba almashish uchrashuvi: 12 rasmdan vertikal (1080x1920) rolik.

Ishlatish:
    python3 korea_build.py <manba_papka> <chiqish.mp4> [ish_papka]

Syujet: kirish titri -> mehmonlar tashrifi -> hovlida suhbat -> Turon Odob-Ilm binosi
oldida esdalik surati -> maktab bilan tanishuv -> davra suhbati (Koreya metodikasi) ->
ishtirokchilar titri. Musiqa: korea_music.py (original).
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import korea_music  # noqa: E402
import overlays  # noqa: E402
from build import shake_expr  # noqa: E402
from ujc_build import FONT_DIR, ease_out, enc, render_photo, run, text_center  # noqa: E402

FPS = 30
W, H = 1080, 1920
TOTAL = 44.0
ACCENT = (125, 200, 255)  # och ko'k (o'qilishi uchun)
UZ_BLUE, UZ_GREEN = (0, 153, 181), (30, 181, 58)
KR_RED, KR_BLUE = (205, 46, 58), (0, 71, 160)

# (rasm, boshlang'ich oyna, yakuniy oyna, harakat egri chizig'i) - oyna = (cx, cy, balandlik ulushi)
SHOTS = [
    ("33ceabce", (0.40, 0.55, 0.86), (0.40, 0.58, 0.70), "linear"),  # darvozadan kirib kelish
    ("31d2d6bf", (0.43, 0.55, 0.90), (0.45, 0.57, 0.80), "linear"),  # yaqinroqdan
    ("30be8acf", (0.52, 0.55, 0.80), (0.55, 0.57, 0.72), "linear"),  # hovlida suhbat (keng)
    ("cb01065d", (0.36, 0.55, 0.95), (0.62, 0.55, 0.95), "linear"),  # hovlida suhbat (yaqin)
    ("c8c6327a", (0.50, 0.26, 0.55), (0.53, 0.50, 1.00), "inout"),   # maktab peshtoqidan guruhga
    ("633610a9", (0.42, 0.50, 0.85), (0.41, 0.55, 0.75), "linear"),  # sport maydoni
    ("e5f2e115", (0.25, 0.50, 1.00), (0.70, 0.50, 1.00), "linear"),  # foye, guruh
    ("b5fbf432", (0.50, 0.50, 1.00), (0.62, 0.55, 0.86), "linear"),  # koreyalik o'qituvchi so'zlamoqda
    ("043984f3", (0.35, 0.50, 1.00), (0.62, 0.50, 1.00), "linear"),  # sinfxona taqdimoti
    ("51ae6b6f", (0.30, 0.50, 1.00), (0.77, 0.50, 1.00), "linear"),  # davra suhbati
    ("bc9f2df8", (0.35, 0.62, 0.70), (0.60, 0.62, 0.70), "linear"),  # davra suhbati (portret)
    ("9ee35db7", (0.30, 0.50, 1.00), (0.62, 0.50, 1.00), "linear"),  # tinglovchilar
]
TRANSITIONS = [
    ("hblur", 0.5, 4.0),
    ("fade", 0.3, 7.0),
    ("smoothleft", 0.5, 9.0),
    ("fade", 0.4, 11.5),
    ("fadewhite", 0.4, 14.0),
    ("smoothup", 0.5, 17.0),
    ("hblur", 0.4, 19.0),
    ("fade", 0.4, 21.5),
    ("smoothleft", 0.4, 24.0),
    ("fade", 0.5, 26.5),
    ("smoothright", 0.4, 29.5),
    ("fade", 0.4, 32.0),
    ("fadeblack", 0.8, 34.0),
]
CAPTIONS = [
    (4.45, 8.70, "TASHRIF", "Mehmonlar tashrifi", 1450),
    (14.30, 16.75, "TURON ODOB-ILM", "Xususiy maktab", 1450),
    (19.35, 23.75, "TANISHUV", "Maktab bilan tanishuv", 1450),
    (26.85, 31.75, "KOREYA METODIKASI", "Tajriba va fikr almashish", 1450),
]
LEAKS = [(0.4, 1.1, 0.55), (4.0, 0.7, 0.8), (19.0, 0.7, 0.8), (34.4, 1.2, 0.45)]


def seg_durations():
    cuts = [0.0] + [c for _, _, c in TRANSITIONS] + [TOTAL]
    tds = [0.0] + [d for _, d, _ in TRANSITIONS] + [0.0]
    return [cuts[i + 1] - cuts[i] + tds[i] / 2 + tds[i + 1] / 2 for i in range(len(cuts) - 1)]


def normalize_images(src_dir, work):
    """EXIF yo'nalishini qo'llab, rasmlarni ish papkasiga saqlash."""
    out = {}
    d = os.path.join(work, "norm")
    os.makedirs(d, exist_ok=True)
    for key, *_ in SHOTS:
        p = os.path.join(d, f"{key}.jpg")
        if not os.path.exists(p):
            ImageOps.exif_transpose(Image.open(os.path.join(src_dir, f"{key}-image.jpg"))).convert("RGB").save(
                p, quality=96, subsampling=0)
        out[key] = p
    return out


# ------------------------------------------------------------- titr kadrlari
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def blurred_bg(path, darken=0.30, tint=(8, 16, 38)):
    im = Image.open(path).convert("RGB")
    k = max(W * 1.12 / im.width, H * 1.12 / im.height)
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(24))
    return Image.blend(Image.new("RGB", im.size, tint), im, darken)


def bg_frame(bg, t, dur, zoom=0.06):
    z = 1.0 + zoom * t / dur
    sw, sh = W / z, H / z
    ox, oy = (bg.width - sw) / 2, (bg.height - sh) / 2
    return bg.transform((W, H), Image.AFFINE, (sw / W, 0, ox, 0, sh / H, oy), Image.BICUBIC).convert("RGBA")


def color_bar(d, cy, half, alpha):
    """Oʻzbekiston (ko'k, yashil) va Koreya (qizil, ko'k) ranglaridagi chiziq, markazdan o'sadi."""
    if half < 2:
        return
    cols = (UZ_BLUE, UZ_GREEN, KR_RED, KR_BLUE)
    seg = 2 * half / 4
    for i, c in enumerate(cols):
        x0 = W / 2 - half + i * seg
        d.rectangle([x0, cy - 3, x0 + seg - 2, cy + 3], fill=c + (int(255 * alpha),))


def letters_rise(d, text, fnt, cy, t, t0, alpha=1.0, tracking=0, fill=(255, 255, 255)):
    widths = [fnt.getlength(c) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = (W - total) / 2
    for i, (c, w) in enumerate(zip(text, widths)):
        lt = (t - t0 - i * 0.025) / 0.5
        a = ease_out(lt) * alpha
        if a > 0:
            d.text((x, cy + 34 * (1 - ease_out(lt))), c, font=fnt, fill=fill + (int(255 * a),))
        x += w + tracking


def with_shadow(frame, txt, blur=10, strength=0.65):
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(txt.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * strength)))
    return Image.alpha_composite(Image.alpha_composite(frame, sh), txt)


def pipe_frames(out, n, draw_fn):
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-"] + enc(out), stdin=subprocess.PIPE)
    for f in range(n):
        proc.stdin.write(draw_fn(f / FPS).convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"encode failed: {out}")


def render_intro(img, dur, out):
    bg = blurred_bg(img, 0.42)
    f_kick, f_main = font("Inter-Medium.otf", 32), font("InterDisplay-SemiBold.otf", 92)
    f_sub = font("Inter-LightItalic.otf", 36)

    def draw(t):
        frame = bg_frame(bg, t, dur)
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(txt)
        color_bar(d, 800, 190 * ease_out((t - 0.15) / 0.8), 1.0)
        ka = ease_out((t - 0.35) / 0.6)
        if ka > 0:
            text_center(d, 840 + 16 * (1 - ka), "OʻZBEKISTON  ·  KOREYA", f_kick, (255, 255, 255, int(225 * ka)), 7)
        letters_rise(d, "Tajriba almashish", f_main, 905, t, 0.55)
        letters_rise(d, "uchrashuvi", f_main, 1010, t, 0.85)
        sa = ease_out((t - 1.5) / 0.7)
        if sa > 0:
            text_center(d, 1150, "Koreya taʼlim metodikasini oʻrganish", f_sub, (235, 240, 248, int(230 * sa)))
            text_center(d, 1198, "va fikr almashish", f_sub, (235, 240, 248, int(230 * sa)))
        return with_shadow(frame, txt)
    pipe_frames(out, int(round(dur * FPS)), draw)


PEOPLE = [
    ("Marufjon Usmonov", "Shahar hokimi"),
    ("Abduqodirxon Ahmedov", "Turon Odob-Ilm investori"),
    ("Koreyalik oʻqituvchilar", "Koreya taʼlim metodikasi"),
]


def render_credits(img, dur, out):
    bg = blurred_bg(img, 0.30)
    f_kick, f_name = font("Inter-Medium.otf", 30), font("InterDisplay-SemiBold.otf", 60)
    f_role = font("Inter-Regular.otf", 32)
    f_brand, f_brand2 = font("InterDisplay-Bold.otf", 84), font("Inter-Medium.otf", 34)
    switch = 6.2  # ishtirokchilardan brend kadriga o'tish

    def draw(t):
        frame = bg_frame(bg, t, dur, 0.05)
        txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(txt)
        out_a = 1 - ease_out((t - switch) / 0.5)
        if out_a > 0:
            color_bar(d, 600, 150 * ease_out((t - 0.2) / 0.7), out_a)
            ka = ease_out((t - 0.3) / 0.6) * out_a
            if ka > 0:
                text_center(d, 635, "ISHTIROKCHILAR", f_kick, (255, 255, 255, int(220 * ka)), 9)
            for i, (name, role) in enumerate(PEOPLE):
                t0 = 0.8 + i * 0.75
                a = ease_out((t - t0) / 0.7) * out_a
                if a <= 0:
                    continue
                y = 760 + i * 190 + 26 * (1 - ease_out((t - t0) / 0.7))
                text_center(d, y, name, f_name, (255, 255, 255, int(255 * a)), 1)
                text_center(d, y + 80, role, f_role, ACCENT + (int(240 * a),), 1)
        ba = ease_out((t - switch - 0.3) / 0.8)
        if ba > 0:
            color_bar(d, 870, 200 * ease_out((t - switch - 0.2) / 0.9), ba)
            letters_rise(d, "TURON ODOB-ILM", f_brand, 905, t, switch + 0.35, ba, tracking=8)
            text_center(d, 1035, "Oʻzbekiston  ·  Koreya", f_brand2, (235, 240, 248, int(230 * ba)), 3)
        return with_shadow(frame, txt)
    pipe_frames(out, int(round(dur * FPS)), draw)


def corner_tag(work):
    """Chap yuqori burchakdagi kichik belgi: 'OʻZBEKISTON · KOREYA' + rangli chiziq."""
    im = Image.new("RGBA", (420, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Inter-SemiBold.otf", 24)
    d.text((14, 14), "OʻZBEKISTON · KOREYA", font=f, fill=(255, 255, 255, 255))
    for i, c in enumerate((UZ_BLUE, UZ_GREEN, KR_RED, KR_BLUE)):
        d.rectangle([14 + i * 36, 52, 14 + i * 36 + 32, 56], fill=c + (255,))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.7)))
    im = Image.alpha_composite(sh, im)
    p = os.path.join(work, "korea_tag.png")
    im.save(p)
    return p


# ------------------------------------------------------------- bosqichlar
def render_segments(src_dir, work):
    D = seg_durations()
    imgs = normalize_images(src_dir, work)
    segs = [os.path.join(work, f"k{i:02d}.mp4") for i in range(len(SHOTS) + 2)]
    render_intro(imgs["c8c6327a"], D[0], segs[0])
    for i, (key, a, b, ease) in enumerate(SHOTS):
        render_photo(imgs[key], a, b, D[i + 1], segs[i + 1], ease)
    render_credits(imgs["51ae6b6f"], D[-1] + 0.2, segs[-1])
    return segs


def render_audio(work):
    raw = os.path.join(work, "korea_music_raw.wav")
    korea_music.m.write_wav(raw, korea_music.build())
    pre = "highpass=f=28,lowpass=f=15500,acompressor=threshold=-14dB:ratio=2.5:attack=15:release=180:makeup=1"
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af",
                        pre + ",loudnorm=I=-14:TP=-2.0:LRA=9:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    js = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-2.0:LRA=9:measured_I={js['input_i']}:measured_TP={js['input_tp']}"
          f":measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}"
          f":offset={js['target_offset']}:linear=true")
    out = os.path.join(work, "korea_music.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", f"{pre},{ln},aresample=48000,atrim=0:{TOTAL}", out])
    return out


def compose(segs, audio, work, out):
    overlays.GOLD = ACCENT
    overlays.CAPTIONS = CAPTIONS
    overlays.LEAKS = LEAKS
    caps = overlays.write_captions(os.path.join(work, "korea_caps"))
    lw, lh = overlays.write_leaks(os.path.join(work, "korea_leaks.rgb"), TOTAL)
    tag = corner_tag(work)

    inputs = []
    for s in segs:
        inputs += ["-i", s]
    li = len(segs)
    inputs += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{lw}x{lh}", "-r", str(FPS),
               "-i", os.path.join(work, "korea_leaks.rgb")]
    ti = li + 1
    inputs += ["-loop", "1", "-framerate", str(FPS), "-t", str(TOTAL), "-i", tag]
    cap_idx = [ti + 1 + k for k in range(len(caps))]
    for d, _, _ in caps:
        inputs += ["-framerate", str(FPS), "-i", os.path.join(d, "%04d.png")]
    ai = ti + 1 + len(caps)
    inputs += ["-i", audio]

    D = seg_durations()
    fc = [f"[{i}:v]settb=AVTB,fps={FPS},format=yuv420p,setsar=1[c{i}]" for i in range(len(segs))]
    prev, acc = "c0", D[0]
    for i, (kind, td, _) in enumerate(TRANSITIONS):
        off = acc - td
        fc.append(f"[{prev}][c{i + 1}]xfade=transition={kind}:duration={td}:offset={off:.3f}[x{i}]")
        prev, acc = f"x{i}", off + D[i + 1]
    fc.append(f"[{prev}]{shake_expr(((120, 1.0), (570, 0.8)))},format=gbrp[base]")
    fc.append(f"[{li}:v]scale={W}:{H}:flags=bicubic,gblur=sigma=20,format=gbrp[leak]")
    fc.append("[base][leak]blend=all_mode=screen:all_opacity=0.8,format=yuv420p,"
              "vignette=angle=PI/5.5:mode=forward,noise=c0s=3:c0f=t+u[graded]")
    fc.append(f"[{ti}:v]format=rgba,colorchannelmixer=aa=0.9,"
              f"fade=t=in:st=4.5:d=0.6:alpha=1,fade=t=out:st=33.2:d=0.5:alpha=1[tag]")
    fc.append("[graded][tag]overlay=x=34:y=104:format=auto[g2]")
    prev = "g2"
    for k, ((_, t0, y), ci) in enumerate(zip(caps, cap_idx)):
        fc.append(f"[{ci}:v]format=rgba,setpts=PTS-STARTPTS+{t0}/TB[cap{k}]")
        fc.append(f"[{prev}][cap{k}]overlay=x=0:y={y}:eof_action=pass:format=auto[o{k}]")
        prev = f"o{k}"
    fc.append(f"[{prev}]fade=t=in:st=0:d=0.5,fade=t=out:st={TOTAL - 1.3}:d=1.3,"
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
    segs = [os.path.join(work, f"k{i:02d}.mp4") for i in range(len(SHOTS) + 2)]
    if "segments" in only:
        segs = render_segments(src_dir, work)
    audio = os.path.join(work, "korea_music.wav")
    if "audio" in only:
        audio = render_audio(work)
    if "compose" in only:
        compose(segs, audio, work, out)


if __name__ == "__main__":
    main()

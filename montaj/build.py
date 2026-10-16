"""Professional montaj: 4 ta videodan vertikal (1080x1920) reel.

Ishlatish:
    python3 build.py <manba_papka> <chiqish.mp4> [ish_papka]

Bosqichlar:
  1. Har bir lavha alohida render: kesish, tezlik (slow-motion / speed-ramp),
     HDR->SDR, stabilizatsiya, rang korreksiyasi, Ken Burns harakati.
  2. Musiqa + SFX sintezi (music.py), loudness -14 LUFS.
  3. Yozuvlar va light-leak qatlami (overlays.py).
  4. Yig'ish: xfade o'tishlar, beat-ga mos zoom-punch/shake, light leak,
     vinyetka, film grain, fade in/out. Asl ovozlar butunlay o'chirilgan.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import music  # noqa: E402
import overlays  # noqa: E402

FPS = 30
W, H = 1080, 1920

SRC = {
    "meeting": "332975f6-6912133777181728649.mp4",
    "exterior": "4e0f1ece-IMG_2356.mov",
    "farm": "66804093-20261003185226272.mp4",
    "atrium": "c4e630f3-telegram_video.mp4",
}

# Har bir lavha davomiyligi (o'tishlar uchun zaxira bilan) va o'tishlar
# kesimlar: 4, 12, 16, 20, 24 s (120 BPM, har 2 takt)
TRANSITIONS = [  # (xfade turi, davomiylik, kesim vaqti)
    ("hblur", 0.5, 4.0),
    ("smoothleft", 0.5, 12.0),
    ("fade", 0.2, 16.0),
    ("fadewhite", 0.4, 20.0),
    ("smoothup", 0.6, 24.0),
]
TOTAL = 33.8

HLG2SDR = ("zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,format=gbrpf32le,"
           "zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def run(cmd):
    print("$", " ".join(cmd)[:300], flush=True)
    subprocess.run(cmd, check=True)


def ken_burns(z0, z1, dur, px0=0.0, px1=0.0, py0=0.0, py1=0.0):
    """Sub-pikselli silliq zoom/pan (perspective filtri, kubik interpolyatsiya)."""
    n = dur * FPS
    p = f"min(on/{n:.3f},1)"
    z = f"({z0}+({z1}-{z0})*{p})"
    a = f"((1-1/{z})/2)"
    px = f"({px0}+({px1}-{px0})*{p})"
    py = f"({py0}+({py1}-{py0})*{p})"
    xl, xr = f"W*({a}+{px})", f"W*(1-{a}+{px})"
    yt, yb = f"H*({a}+{py})", f"H*(1-{a}+{py})"
    return (f"perspective=x0='{xl}':y0='{yt}':x1='{xr}':y1='{yt}':x2='{xl}':y2='{yb}':x3='{xr}':y3='{yb}'"
            ":interpolation=cubic:eval=frame")


def encode_args(out):
    return ["-an", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p",
            "-r", str(FPS), out]


def seg_durations():
    cuts = [0.0] + [c for _, _, c in TRANSITIONS] + [TOTAL]
    tds = [0.0] + [d for _, d, _ in TRANSITIONS] + [0.0]
    return [cuts[i + 1] - cuts[i] + tds[i] / 2 + tds[i + 1] / 2 for i in range(len(cuts) - 1)]


def render_segments(src_dir, work):
    D = seg_durations()  # [4.25, 8.5, 4.35, 4.3, 4.5, 10.1]
    src = {k: os.path.join(src_dir, v) for k, v in SRC.items()}
    segs = []

    # 0) Atrium intro - 0.7x slow-motion (harakat interpolyatsiyasi), iliq oltin rang
    out = os.path.join(work, "s0.mp4")
    vf = ",".join([
        "setpts=(PTS-STARTPTS)/0.7",
        "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
        "scale=1080:-2:flags=lanczos", "crop=1080:1920",
        "eq=contrast=1.06:saturation=1.14:gamma=0.97",
        "colorbalance=rs=0.02:bs=-0.03:rm=0.03:bm=-0.03:rh=0.03:bh=-0.04",
        "unsharp=5:5:0.9:5:5:0.0",
        ken_burns(1.0, 1.10, D[0]),
        f"trim=duration={D[0]}", "setsar=1",
    ])
    run(["ffmpeg", "-v", "error", "-y", "-ss", "0", "-t", "3.1", "-i", src["atrium"], "-vf", vf] + encode_args(out))
    segs.append(out)

    # 1) Restoran tashqarisi - iPhone HDR (HLG) -> SDR, 120fps dan silliq speed-ramp (2x -> 0.85x)
    a, b, r1, r2 = 1.6, 2.8, 0.5, 1 / 0.85
    ramp = (f"setpts='if(lt(T,{a}),{r1}*T,if(lt(T,{b}),{r1}*T+({r2}-{r1})*(T-{a})*(T-{a})/(2*({b}-{a})),"
            f"{r1}*{b}+({r2}-{r1})*({b}-{a})/2+{r2}*(T-{b})))/TB'")
    out = os.path.join(work, "s1.mp4")
    vf = ",".join([
        "setpts=PTS-STARTPTS", ramp, f"fps={FPS}", HLG2SDR,
        "scale=1080:1920:flags=lanczos",
        "eq=brightness=0.02:contrast=1.07:saturation=1.12:gamma=1.10",
        "colorbalance=rs=-0.02:bs=0.03:rm=0.03:bm=-0.02:rh=0.02",
        ken_burns(1.02, 1.08, D[1]),
        f"trim=duration={D[1]}", "setsar=1",
    ])
    run(["ffmpeg", "-v", "error", "-y", "-ss", "0.3", "-i", src["exterior"], "-vf", vf] + encode_args(out))
    segs.append(out)

    # 2-3) Yig'ilish - ikki lavha, vid.stab bilan stabilizatsiya
    for idx, (start, dur) in ((2, (2.0, D[2])), (3, (15.5, D[3]))):
        trf = os.path.join(work, f"meet{idx}.trf")
        cut = ["-ss", str(start), "-t", f"{dur + 0.2:.2f}", "-i", src["meeting"]]
        run(["ffmpeg", "-v", "error", "-y"] + cut + ["-vf", f"vidstabdetect=shakiness=6:accuracy=15:result={trf}",
                                                    "-f", "null", "-"])
        out = os.path.join(work, f"s{idx}.mp4")
        vf = ",".join([
            f"vidstabtransform=input={trf}:smoothing=18:zoom=4:interpol=bicubic",
            "hqdn3d=1.5:1.5:3:3",
            "scale=1080:1920:flags=lanczos",
            "eq=contrast=1.08:saturation=1.10:gamma=0.98",
            "colorbalance=rs=0.01:bs=-0.02:rm=0.025:bm=-0.025:rh=0.02:bh=-0.01",
            "unsharp=5:5:0.7:5:5:0.0",
            ken_burns(1.0, 1.06, dur) if idx == 2 else ken_burns(1.06, 1.0, dur),
            f"trim=duration={dur}", "setsar=1",
        ])
        run(["ffmpeg", "-v", "error", "-y"] + cut + ["-vf", vf] + encode_args(out))
        segs.append(out)

    # 4) Ferma (CCTV, gorizontal) - vaqt/kamera yozuvlari kesib tashlanadi, yo'lakdan sigirlarga pan
    out = os.path.join(work, "s4.mp4")
    vf = ",".join([
        "crop=1500:1260:900:0", "hqdn3d=3:3:6:6", "scale=2286:1920:flags=lanczos", f"fps={FPS}",
        "eq=contrast=1.12:saturation=1.18:gamma=0.94",
        "curves=all='0/0 0.5/0.48 0.85/0.80 1/0.93'",
        "colorbalance=rs=0.03:bs=-0.03:rm=0.03:bm=-0.04",
        "unsharp=5:5:0.8:5:5:0.0",
        ken_burns(1.0, 1.0, D[4], 0.0, 991 / 2286),
        "crop=1080:1920:152:0",
        f"trim=duration={D[4]}", "setsar=1",
    ])
    run(["ffmpeg", "-v", "error", "-y", "-ss", "0.1", "-t", "4.7", "-i", src["farm"], "-vf", vf] + encode_args(out))
    segs.append(out)

    # 5) Final - atrium, 0.9x slow-motion, shiftga qarab ko'tarilish
    out = os.path.join(work, "s5.mp4")
    vf = ",".join([
        "setpts=(PTS-STARTPTS)/0.9",
        "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
        "scale=1080:-2:flags=lanczos", "crop=1080:1920",
        "eq=contrast=1.07:saturation=1.15:gamma=0.97",
        "colorbalance=rs=0.02:bs=-0.03:rm=0.03:bm=-0.03:rh=0.03:bh=-0.04",
        "unsharp=5:5:0.9:5:5:0.0",
        ken_burns(1.0, 1.07, D[5]),
        "tpad=stop_mode=clone:stop_duration=1",
        f"trim=duration={D[5]}", "setsar=1",
    ])
    run(["ffmpeg", "-v", "error", "-y", "-ss", "2.95", "-i", src["atrium"], "-vf", vf] + encode_args(out))
    segs.append(out)
    return segs


def render_audio(work):
    raw = os.path.join(work, "music_raw.wav")
    music.write_wav(raw, music.build())
    pre = "highpass=f=28,lowpass=f=15500,acompressor=threshold=-14dB:ratio=2.5:attack=15:release=180:makeup=1"
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af",
                        pre + ",loudnorm=I=-14:TP=-1.2:LRA=9:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    js = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.2:LRA=9:measured_I={js['input_i']}:measured_TP={js['input_tp']}"
          f":measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}"
          f":offset={js['target_offset']}:linear=true")
    out = os.path.join(work, "music.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
         f"{pre},{ln},aresample=48000,atrim=0:{TOTAL},afade=t=out:st={TOTAL - 1.0}:d=1.0", out])
    return out


def shake_expr(hits=((120, 1.0), (600, 0.7), (720, 0.9))):
    """Impact nuqtalarida (kadr raqami, kuch) zoom-punch + titrash, sub-pikselli."""
    env = "+".join(f"{s}*gte(on,{f})*exp(-(on-{f})/5)" for f, s in hits)
    m = f"(W*0.035*({env}))"            # zoom-punch (chetlar ichkariga)
    dx = f"(14*({env})*sin(on*2.3))"
    dy = f"(11*({env})*cos(on*1.9))"
    xl, xr = f"({m}+{dx})", f"(W-{m}+{dx})"
    yt, yb = f"({m}*H/W+{dy})", f"(H-{m}*H/W+{dy})"
    return (f"perspective=x0='{xl}':y0='{yt}':x1='{xr}':y1='{yt}':x2='{xl}':y2='{yb}':x3='{xr}':y3='{yb}'"
            ":interpolation=cubic:eval=frame")


def compose(segs, audio, work, out):
    caps = overlays.write_captions(work)
    lw, lh = overlays.write_leaks(os.path.join(work, "leaks.rgb"), TOTAL)

    inputs = []
    for s in segs:
        inputs += ["-i", s]
    li = len(segs)
    inputs += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{lw}x{lh}", "-r", str(FPS),
               "-i", os.path.join(work, "leaks.rgb")]
    cap_idx = []
    for d, _, _ in caps:
        cap_idx.append(li + 1 + len(cap_idx))
        inputs += ["-framerate", str(FPS), "-i", os.path.join(d, "%04d.png")]
    ai = li + 1 + len(caps)
    inputs += ["-i", audio]

    D = seg_durations()
    fc = []
    for i in range(len(segs)):
        fc.append(f"[{i}:v]settb=AVTB,fps={FPS},format=yuv420p[c{i}]")
    prev, acc = "c0", D[0]
    for i, (kind, td, _) in enumerate(TRANSITIONS):
        off = acc - td
        fc.append(f"[{prev}][c{i + 1}]xfade=transition={kind}:duration={td}:offset={off:.3f}[x{i}]")
        prev, acc = f"x{i}", off + D[i + 1]
    fc.append(f"[{prev}]{shake_expr()},format=gbrp[base]")
    fc.append(f"[{li}:v]scale={W}:{H}:flags=bicubic,gblur=sigma=20,format=gbrp[leak]")
    fc.append("[base][leak]blend=all_mode=screen:all_opacity=0.85,format=yuv420p,"
              "vignette=angle=PI/5:mode=forward,noise=c0s=4:c0f=t+u[graded]")
    prev = "graded"
    for k, ((_, t0, y), ci) in enumerate(zip(caps, cap_idx)):
        fc.append(f"[{ci}:v]format=rgba,setpts=PTS-STARTPTS+{t0}/TB[cap{k}]")
        fc.append(f"[{prev}][cap{k}]overlay=x=0:y={y}:eof_action=pass:format=auto[o{k}]")
        prev = f"o{k}"
    fc.append(f"[{prev}]fade=t=in:st=0:d=0.6,fade=t=out:st={TOTAL - 1.6}:d=1.6,"
              f"trim=duration={TOTAL},format=yuv420p,setsar=1[vout]")

    run(["ffmpeg", "-v", "error", "-stats", "-y"] + inputs + [
        "-filter_complex", ";".join(fc),
        "-map", "[vout]", "-map", f"{ai}:a",
        "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M", "-profile:v", "high", "-level", "4.2",
        "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-r", str(FPS), "-g", "60",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart", "-t", str(TOTAL), out])


def main():
    src_dir, out = sys.argv[1], sys.argv[2]
    work = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(out)), "_work")
    os.makedirs(work, exist_ok=True)
    only = os.environ.get("ONLY", "segments,audio,compose").split(",")
    segs = [os.path.join(work, f"s{i}.mp4") for i in range(6)]
    if "segments" in only:
        segs = render_segments(src_dir, work)
    audio = os.path.join(work, "music.wav")
    if "audio" in only:
        audio = render_audio(work)
    if "compose" in only:
        compose(segs, audio, work, out)


if __name__ == "__main__":
    main()

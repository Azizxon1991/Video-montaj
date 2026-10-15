"""Montaj uchun original musiqa va ovoz effektlari (SFX) sintezi.

120 BPM, A-minor (Am - F - C - G). Bo'limlar video kesimlariga moslangan:
  0-4 s   intro (pad + arpedjio, riser, snare roll)
  4 s     drop (impact + crash)
  4-24 s  asosiy groove (12 s dan boshlab melodiya)
  24-32 s final (to'liq aranjirovka)
  32 s    yakuniy akkord, dum (tail) 33.8 s gacha

Natija: stereo WAV (48 kHz, float32 -> int16).
"""
import sys
import wave

import numpy as np

SR = 48000
BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4
TOTAL = 33.8
N = int(SR * TOTAL)
RNG = np.random.default_rng(7)

# Video kesimlari (sekund) - transitionlar shu nuqtalarga to'g'ri keladi
CUTS = {"drop": 4.0, "meeting": 12.0, "meeting2": 16.0, "farm": 20.0, "finale": 24.0, "end": 32.0}


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def buf():
    return np.zeros((2, N), dtype=np.float64)


def place(dst, sig, t0, gain=1.0, pan=0.0):
    """Mono yoki stereo signalni t0 vaqtga joylash (equal-power pan)."""
    i0 = int(round(t0 * SR))
    if sig.ndim == 1:
        a = (pan + 1) * np.pi / 4
        sig = np.vstack([sig * np.cos(a), sig * np.sin(a)]) * np.sqrt(2)
    n = min(sig.shape[1], N - i0)
    if n <= 0:
        return
    dst[:, i0:i0 + n] += gain * sig[:, :n]


def fft_filter(x, lo=None, hi=None, order=2):
    """Oddiy chastota maskasi bilan filtr (offline, faza nol)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    if hi:
        g *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    return np.fft.irfft(X * g, len(x))


def tv_filter(x, center_fn, width=0.6, n_fft=2048, hop=512):
    """Vaqt bo'yicha o'zgaruvchan band-pass (STFT). center_fn(t)->Hz."""
    win = np.hanning(n_fft)
    pad = np.concatenate([np.zeros(n_fft), x, np.zeros(n_fft)])
    out = np.zeros_like(pad)
    norm = np.zeros_like(pad)
    f = np.fft.rfftfreq(n_fft, 1 / SR)
    lf = np.log2(np.maximum(f, 1.0))
    for i in range(0, len(pad) - n_fft, hop):
        t = (i - n_fft + n_fft / 2) / SR
        c = np.log2(max(center_fn(max(t, 0.0)), 20.0))
        g = np.exp(-0.5 * ((lf - c) / width) ** 2)
        seg = np.fft.irfft(np.fft.rfft(pad[i:i + n_fft] * win) * g, n_fft)
        out[i:i + n_fft] += seg * win
        norm[i:i + n_fft] += win ** 2
    out /= np.maximum(norm, 1e-6)
    return out[n_fft:n_fft + len(x)]


def env_adsr(n, a, d, s, r, sustain_len):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), 1.0)
    e = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / max(d, 1e-4), e)
    e = np.where((t >= a + d) & (t < sustain_len), s, e)
    rel = t >= sustain_len
    e = np.where(rel, s * np.exp(-(t - sustain_len) / max(r, 1e-4) * 4), e)
    if sustain_len < a + d:
        e = np.where(rel, e, e)
    return e


# ---------------------------------------------------------------- instruments
def supersaw(freq, dur, bright_fn, t0, detune=(-0.09, 0.0, 0.09), rel=0.7):
    """Additiv super-saw pad; bright_fn(abs_t) -> cutoff Hz (vaqtga bog'liq filtr)."""
    n = int((dur + rel) * SR)
    t = np.arange(n) / SR
    cutoff = bright_fn(t0 + t)
    out = np.zeros((2, n))
    for k, dt in enumerate(detune):
        f = freq * 2 ** (dt / 12)
        ph0 = RNG.uniform(0, 2 * np.pi)
        sig = np.zeros(n)
        nh = int(min(9000 / f, 60))
        for h in range(1, nh + 1):
            w = (1 / h) / np.sqrt(1 + (h * f / cutoff) ** 4)
            sig += w * np.sin(2 * np.pi * f * h * t + ph0 * h)
        pan = (-0.6, 0.0, 0.6)[k % 3]
        a = (pan + 1) * np.pi / 4
        out[0] += sig * np.cos(a)
        out[1] += sig * np.sin(a)
    e = env_adsr(n, 0.35, 0.4, 0.85, rel, dur)
    return out * e / len(detune)


def pluck(freq, t_len=0.6, bright=1.0):
    n = int(t_len * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for h in range(1, 14):
        if h * freq > 12000:
            break
        sig += (1 / h) * np.exp(-t * (6 + h * 4.5 / bright)) * np.sin(2 * np.pi * freq * h * t)
    att = np.minimum(t / 0.003, 1)
    return sig * att


def bell(freq, t_len=1.6):
    """FM qo'ng'iroqsimon lead."""
    n = int(t_len * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * 3.5 * t) * 2.2 * np.exp(-t * 3)
    car = np.sin(2 * np.pi * freq * t + mod)
    body = 0.5 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 4)
    att = np.minimum(t / 0.004, 1)
    return (car + body) * np.exp(-t * 2.2) * att


def bass_note(freq, dur):
    n = int((dur + 0.05) * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 2 * freq * t)
    sig = np.tanh(1.8 * sig) / np.tanh(1.8)
    e = np.minimum(t / 0.006, 1) * np.where(t < dur, np.exp(-t * 1.5), np.exp(-dur * 1.5) * np.exp(-(t - dur) * 60))
    return sig * e


def kick():
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = 44 + 120 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 6.5)
    click = fft_filter(RNG.standard_normal(n), lo=2000) * np.exp(-t * 300) * 0.25
    return np.tanh(1.6 * (body + click)) * 0.95


def clap():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    noise = fft_filter(RNG.standard_normal(n), lo=900, hi=6000)
    e = np.zeros(n)
    for k, off in enumerate((0.0, 0.011, 0.022)):
        tt = t - off
        e += np.where(tt >= 0, np.exp(-np.maximum(tt, 0) * (180 if k < 2 else 16)), 0)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.4
    return (noise * e * 0.5 + body) * 0.9


def hat(open_=False):
    n = int((0.35 if open_ else 0.08) * SR)
    t = np.arange(n) / SR
    noise = fft_filter(RNG.standard_normal(n), lo=7000, hi=12000)
    return noise * np.exp(-t * (12 if open_ else 70)) * 0.5


def crash(length=2.5):
    n = int(length * SR)
    t = np.arange(n) / SR
    noise = fft_filter(RNG.standard_normal(n), lo=3500, hi=11000)
    noise2 = fft_filter(RNG.standard_normal(n), lo=3500, hi=11000)
    e = np.exp(-t * 1.8) * np.minimum(t / 0.002, 1)
    return np.vstack([noise * e, noise2 * e]) * 0.35


def impact():
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    f = 30 + 55 * np.exp(-t * 5)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.0)
    thud = fft_filter(RNG.standard_normal(n), hi=400) * np.exp(-t * 9) * 0.6
    return np.tanh(1.4 * (boom + thud)) * 0.9


def riser(length):
    n = int(length * SR)
    t = np.arange(n) / SR
    noise = RNG.standard_normal(n)
    sig = tv_filter(noise, lambda tt: 300 * (40 ** (tt / length)), width=0.8)
    sig /= np.max(np.abs(sig)) + 1e-9
    tone_f = 200 * (8 ** (t / length))
    tone = np.sin(2 * np.pi * np.cumsum(tone_f) / SR) * 0.12
    e = (t / length) ** 2.2
    return (sig * 0.8 + tone) * e


def whoosh(length=0.9, direction=1):
    n = int(length * SR)
    t = np.arange(n) / SR
    noise = RNG.standard_normal(n)
    peak = length * 0.6
    sig = tv_filter(noise, lambda tt: 500 + 3500 * np.exp(-((tt - peak) / (length * 0.3)) ** 2), width=0.7)
    sig /= np.max(np.abs(sig)) + 1e-9
    e = np.exp(-((t - peak) / (length * 0.28)) ** 2)
    pan = np.clip(direction * (t / length * 2 - 1), -1, 1)
    a = (pan + 1) * np.pi / 4
    return np.vstack([sig * e * np.cos(a), sig * e * np.sin(a)]) * 0.9


def reverb_ir(length=2.8, decay=2.2, seed=3):
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = np.arange(n) / SR
    out = []
    for ch in range(2):
        noise = rng.standard_normal(n)
        lo = fft_filter(noise, hi=2500) * np.exp(-t * decay)
        hi = fft_filter(noise, lo=2500) * np.exp(-t * decay * 2.2)
        ir = lo + 0.5 * hi
        ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
        out.append(ir / np.sqrt(np.sum(ir ** 2)))
    return np.array(out)


def convolve_stereo(x, ir):
    n = x.shape[1] + ir.shape[1]
    nfft = 1 << (n - 1).bit_length()
    out = np.zeros((2, x.shape[1]))
    for ch in range(2):
        y = np.fft.irfft(np.fft.rfft(x[ch], nfft) * np.fft.rfft(ir[ch], nfft), nfft)
        out[ch] = y[: x.shape[1]]
    return out


def ping_pong(x, delay, fb=0.38, repeats=6):
    out = x.copy()
    d = int(delay * SR)
    mono = x.mean(axis=0)
    g = 1.0
    for k in range(1, repeats + 1):
        g *= fb
        ch = k % 2
        shifted = np.zeros(N)
        shifted[k * d:] = mono[: N - k * d]
        out[ch] += g * fft_filter(shifted, lo=250, hi=6000, order=1)
    return out


# ---------------------------------------------------------------- arrangement
CHORDS = [  # (bass midi, chord midis)
    (45, [57, 60, 64, 69]),  # Am
    (41, [53, 57, 60, 65]),  # F
    (48, [55, 60, 64, 67]),  # C
    (43, [55, 59, 62, 67]),  # G
]
MELODY = [  # (beat offset, beats, midi) - har bir akkord uchun
    [(0, 1.5, 76), (1.5, 0.5, 74), (2, 1, 72), (3, 1, 76)],
    [(0, 1.5, 77), (1.5, 0.5, 76), (2, 2, 72)],
    [(0, 1.5, 79), (1.5, 0.5, 76), (2, 1, 72), (3, 1, 74)],
    [(0, 2, 74), (2, 2, 71)],
]
END = CUTS["end"]
N_BARS = int(END / BAR)  # 16


def brightness(t):
    """Pad filtri: intro davomida ochiladi, drop dan keyin yorqin."""
    t = np.asarray(t, dtype=float)
    intro = 350 + (2600 - 350) * np.clip(t / 4.0, 0, 1) ** 2
    main = np.where(t < 24, 2600, 4200)
    return np.where(t < 4, intro, main)


def build():
    pad = buf()
    arp = buf()
    lead = buf()
    bass = buf()
    drums = buf()
    sfx = buf()

    # --- pad
    for b in range(N_BARS):
        t0 = b * BAR
        _, notes = CHORDS[b % 4]
        for m in notes[:3]:
            place(pad, supersaw(midi(m), BAR, brightness, t0), t0, 0.22)
        if b >= 12:  # final: oktava yuqori qatlam
            place(pad, supersaw(midi(notes[1] + 12), BAR, brightness, t0), t0, 0.10)
    # yakuniy akkord (Am) uzun
    for m in (45, 57, 60, 64, 69, 76):
        place(pad, supersaw(midi(m), 0.4, lambda t: np.full_like(t, 3000.0), END, rel=2.0), END, 0.20)

    # --- arpeggio (16-lik notalar)
    pattern = [0, 1, 2, 3, 2, 1, 2, 3]
    for b in range(N_BARS):
        _, notes = CHORDS[b % 4]
        for s in range(16):
            t = b * BAR + s * BEAT / 4
            m = notes[pattern[s % 8]] + 12
            vel = 0.55 + 0.45 * (s % 4 == 0)
            if t < 4:
                vel *= 0.4 + 0.6 * t / 4
            br = 0.6 if t < 4 else 1.0
            pan = 0.35 * np.sin(s * np.pi / 4)
            place(arp, pluck(midi(m), 0.5, br), t, 0.16 * vel, pan)

    # --- lead melodiya (12-20 va 24-32)
    for b in list(range(6, 10)) + list(range(12, 16)):
        for off, ln, m in MELODY[b % 4]:
            t = b * BAR + off * BEAT
            place(lead, bell(midi(m), max(ln * BEAT + 0.8, 1.0)), t, 0.16)
            if b >= 12:
                place(lead, bell(midi(m - 12), max(ln * BEAT + 0.8, 1.0)), t, 0.07)

    # --- bass (8-lik notalar) drop dan keyin
    for b in range(2, N_BARS):
        root, _ = CHORDS[b % 4]
        for e in range(8):
            t = b * BAR + e * BEAT / 2
            if 19.5 <= t < 20 or 23.5 <= t < 24:
                continue
            m = root + (12 if e in (3, 7) else 0)
            place(bass, bass_note(midi(m), BEAT / 2 * 0.85), t, 0.24)
    place(bass, bass_note(midi(33), 2.5), END, 0.35)

    # --- drums
    K, C, HC, HO = kick(), clap(), hat(), hat(True)
    kicks = []
    for b in range(2, N_BARS):
        for q in range(4):
            t = b * BAR + q * BEAT
            if (19.5 <= t < 20) or (23.5 <= t < 24):
                continue
            place(drums, K, t, 0.75)
            kicks.append(t)
            if q in (1, 3):
                place(drums, C, t, 0.42, 0.05)
            # hatlar: off-beat ochiq, 16-liklar yopiq
            place(drums, HO, t + BEAT / 2, 0.16, 0.25)
            for s16 in (1, 3):
                place(drums, HC, t + s16 * BEAT / 4, 0.10 + 0.04 * (s16 == 3), -0.3)
    # intro: yurak urishi kabi past kick (2-bar)
    for t in (2.0, 2.75, 3.0):
        place(drums, K, t, 0.25)
        kicks.append(t)
    # snare roll (3-4 s, 23-24 s, 19.5-20 s qisqa)
    for start, end_, base in ((3.0, 4.0, 0.08), (23.0, 24.0, 0.08), (19.5, 20.0, 0.15)):
        t = start
        k = 0
        while t < end_ - 1e-6:
            prog = (t - start) / (end_ - start)
            step = BEAT / 4 if prog < 0.5 else BEAT / 8
            place(drums, C, t, base + 0.35 * prog, (-1) ** k * 0.15)
            t += step
            k += 1

    # --- SFX: riser, impact, crash, whoosh
    for t_end, ln in ((4.0, 3.5), (24.0, 3.8)):
        place(sfx, riser(ln), t_end - ln, 0.30)
    for t in (4.0, 20.0, 24.0):
        place(sfx, impact(), t, 0.4 if t != 20.0 else 0.28)
        place(drums, crash(), t, 0.55)
    place(sfx, impact(), END, 0.45)
    place(drums, crash(3.5), END, 0.6)
    for t, ln, d in ((CUTS["meeting"], 0.8, 1), (CUTS["meeting2"], 0.5, -1), (CUTS["farm"], 0.7, -1),
                     (CUTS["drop"], 0.9, 1), (CUTS["finale"], 1.1, 1)):
        place(sfx, whoosh(ln, d), t - ln * 0.6, 0.22)
    # reverse crash (swell) final oldidan
    rc = crash(2.0)[:, ::-1] * np.linspace(0, 1, int(2.0 * SR)) ** 2
    place(sfx, rc, 22.0, 0.35)

    # --- sidechain ducking (kick ga)
    t = np.arange(N) / SR
    duck = np.ones(N)
    for tk in kicks:
        i0 = int(tk * SR)
        n = min(int(0.3 * SR), N - i0)
        tt = np.arange(n) / SR
        duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], 1 - 0.55 * np.exp(-tt / 0.09))
    duck = np.convolve(duck, np.ones(48) / 48, mode="same")

    ir_long = reverb_ir(3.2, 1.6)
    ir_short = reverb_ir(1.2, 4.5, seed=5)

    pad_w = np.vstack([fft_filter(pad[0], lo=190), fft_filter(pad[1], lo=190)]) * duck * 0.75
    arp_w = ping_pong(arp * duck, BEAT * 0.75)
    lead_w = ping_pong(lead, BEAT * 0.75, fb=0.3, repeats=4)
    bass_w = np.vstack([fft_filter(bass[0], hi=900), fft_filter(bass[1], hi=900)]) * duck

    wet = convolve_stereo(pad_w * 0.5 + arp_w * 0.6 + lead_w * 0.7 + sfx * 0.25, ir_long)
    wet_d = convolve_stereo(np.vstack([fft_filter(drums[0], lo=300), fft_filter(drums[1], lo=300)]), ir_short)

    mix = pad_w + arp_w + lead_w + bass_w + drums + sfx + wet * 0.35 + wet_d * 0.12

    # fade-in boshida, oxirida tail
    fade_in = np.clip(t / 0.08, 0, 1)
    fade_out = np.where(t > TOTAL - 2.2, np.clip((TOTAL - t) / 2.2, 0, 1) ** 1.5, 1)
    mix *= fade_in * fade_out
    # yumshoq soft-clip faqat cho'qqilar uchun (asosiy limiter ffmpeg da)
    mix /= np.percentile(np.abs(mix), 99.9) + 1e-9
    mix = np.where(np.abs(mix) > 0.8, np.sign(mix) * (0.8 + 0.2 * np.tanh((np.abs(mix) - 0.8) / 0.2)), mix)
    return mix * 0.95


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1).T * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "music_raw.wav"
    write_wav(out, build())
    print("wrote", out)

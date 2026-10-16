"""UJC (Oʻzbekiston–Yaponiya markazi) roligi uchun original musiqa.

Yapon "yo" pentatonikasi (D E G A B) da koto (Karplus-Strong), taiko barabanlari,
pad, bass va yengil ritm. 120 BPM, Bm - G - D - A.
Video kesimlari bilan sinxron:
  0-4    intro (afisha)            : koto arpedjio, qo'ng'iroqchalar, riser, taiko roll
  4-20   asosiy qism               : ritm + koto melodiya, har taktda taiko
  20-28  kulminatsiya              : melodiya oktava yuqori, kuchliroq taiko
  28-34  intervyu (sokin)          : barabanlarsiz, pad + koto
  34     yakuniy zarb, logotip kadri, 41 s gacha so'nish
"""
import sys

import numpy as np

import music as m

TOTAL = 41.0
m.TOTAL = TOTAL
m.N = int(m.SR * TOTAL)
SR, BEAT, BAR, N = m.SR, m.BEAT, m.BAR, m.N
RNG = np.random.default_rng(11)

CHORDS = [  # (bass, akkord)
    (47, [59, 62, 66]),  # Bm
    (43, [55, 59, 62]),  # G
    (50, [57, 62, 66]),  # D
    (45, [57, 61, 64]),  # A
]
MELODY = [  # (beat, uzunlik, midi) - yo pentatonika
    [(0, 1, 71), (1, 0.5, 69), (1.5, 0.5, 71), (2, 1, 74), (3, 1, 71)],
    [(0, 1.5, 67), (1.5, 0.5, 69), (2, 1, 71), (3, 1, 69)],
    [(0, 1, 69), (1, 0.5, 71), (1.5, 0.5, 69), (2, 1, 67), (3, 1, 64)],
    [(0, 2, 64), (2.5, 0.5, 67), (3, 1, 69)],
]
CUTS = [4.0, 8.0, 10.5, 13.0, 15.0, 17.0, 20.0, 22.5, 24.5, 26.5, 28.0, 34.0]


def koto(freq, length=1.6, bright=0.5):
    """Karplus-Strong tor (davr bo'yicha bloklab vektorlashtirilgan)."""
    n = int(length * SR)
    p = max(int(round(SR / freq)), 2)
    exc = RNG.uniform(-1, 1, p)
    exc = m.fft_filter(np.tile(exc, 3), hi=2500 + 7000 * bright)[:p]
    y = np.zeros(n + p + 1)
    y[1:p + 1] = exc
    decay = 0.996 ** (440 / max(freq, 60)) if freq < 440 else 0.996
    for s in range(p + 1, n + p + 1, p):
        e = min(s + p, n + p + 1)
        y[s:e] = decay * 0.5 * (y[s - p:e - p] + y[s - p - 1:e - p - 1])
    y = y[1:n + 1]
    t = np.arange(n) / SR
    # yapon kotosining "metall" tembri uchun yengil oktava rezonansi
    y = y + 0.18 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 6)
    return y / (np.max(np.abs(y)) + 1e-9) * np.minimum(t / 0.002, 1)


def taiko(size=1.0):
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    f = (58 + 70 * np.exp(-t * 18)) / size
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    skin = m.fft_filter(RNG.standard_normal(n), lo=80, hi=900) * np.exp(-t * 22) * 0.55
    slap = m.fft_filter(RNG.standard_normal(n), lo=1500, hi=5000) * np.exp(-t * 90) * 0.25
    return np.tanh(1.5 * (body + skin + slap)) * 0.9


def chime(freq):
    n = int(2.5 * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * d)
            for r, a, d in ((1, 1, 1.6), (2.76, 0.45, 3.0), (5.4, 0.25, 5.0)))
    return s * np.minimum(t / 0.001, 1)


def shaker():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    return m.fft_filter(RNG.standard_normal(n), lo=5000, hi=11000) * np.exp(-((t - 0.02) / 0.02) ** 2) * 0.35


def bright_fn(t):
    t = np.asarray(t, dtype=float)
    intro = 400 + 2600 * np.clip(t / 4, 0, 1) ** 2
    calm = np.where((t >= 28) & (t < 34), 1400, np.where(t >= 20, 4200, 3000))
    return np.where(t < 4, intro, calm)


def build():
    pad, kot, lead, bass, drums, perc, sfx = (m.buf() for _ in range(7))
    n_bars = int(np.ceil(34 / BAR))  # 17 takt (0-34 s)
    mf = m.midi

    # --- pad
    for b in range(n_bars):
        t0 = b * BAR
        _, notes = CHORDS[b % 4]
        for x in notes:
            m.place(pad, m.supersaw(mf(x), BAR, bright_fn, t0), t0, 0.17)
        if 20 <= t0 < 28:
            m.place(pad, m.supersaw(mf(notes[1] + 12), BAR, bright_fn, t0), t0, 0.08)
    for x in (47, 59, 62, 66, 71, 74):  # yakuniy Bm -> D ga yechim (end card)
        m.place(pad, m.supersaw(mf(x + 3 if x in (47, 59, 71) else x), 3.0,
                                lambda t: np.full_like(t, 2600.0), 34.0, rel=3.0), 34.0, 0.15)

    # --- koto arpedjio (8-lik), intro va sokin qismda yumshoq
    arp = [0, 1, 2, 1, 2, 0, 1, 2]
    for b in range(n_bars):
        _, notes = CHORDS[b % 4]
        for s8 in range(8):
            t = b * BAR + s8 * BEAT / 2
            vel = 0.5 + 0.5 * (s8 % 2 == 0)
            if t < 4:
                vel *= 0.35 + 0.65 * t / 4
            if 28 <= t < 34:
                vel *= 0.95
            m.place(kot, koto(mf(notes[arp[s8]] + 12), 1.2, 0.4), t, 0.11 * vel, 0.4 * np.sin(s8))

    # --- koto melodiya (4-20, 28-34) va oktava yuqori (20-28)
    for b in range(2, n_bars):
        t_bar = b * BAR
        for off, ln, x in MELODY[b % 4]:
            t = t_bar + off * BEAT
            if t >= 34:
                continue
            if 20 <= t < 28:
                m.place(lead, m.bell(mf(x + 12), ln * BEAT + 1.0), t, 0.10)
                m.place(kot, koto(mf(x), 2.0, 0.8), t, 0.30, -0.1)
            else:
                m.place(kot, koto(mf(x), 2.0, 0.7), t, 0.30 if t < 28 else 0.30, -0.1)
                # koto "tremolo" uzun notalarda
                if ln >= 1.5 and t < 28:
                    for k in range(1, 4):
                        m.place(kot, koto(mf(x), 0.6, 0.5), t + k * BEAT / 4, 0.08, -0.1)
    # end card: sekin koto naqsh
    for i, x in enumerate((62, 66, 69, 74, 78, 81)):
        m.place(kot, koto(mf(x), 3.0, 0.6), 34.0 + 0.5 + i * 0.25, 0.20, -0.4 + 0.16 * i)

    # --- bass
    for b in range(2, n_bars):
        root, _ = CHORDS[b % 4]
        for e in range(8):
            t = b * BAR + e * BEAT / 2
            if t >= 34 or (27.5 <= t < 28) or (19.5 <= t < 20):
                continue
            g = 0.22 if not (28 <= t < 34) else 0.12
            if 28 <= t < 34 and e % 2:
                continue
            m.place(bass, m.bass_note(mf(root - 12 + (12 if e in (3, 7) else 0)), BEAT / 2 * 0.85), t, g)
    m.place(bass, m.bass_note(mf(38), 3.0), 34.0, 0.3)

    # --- ritm
    K, C, HC, HO, T, TS, SH = m.kick(), m.clap(), m.hat(), m.hat(True), taiko(), taiko(0.7), shaker()
    kicks = []
    for b in range(2, n_bars):
        for q in range(4):
            t = b * BAR + q * BEAT
            if t >= 34:
                continue
            calm = 28 <= t < 34
            if (19.5 <= t < 20) or (27.5 <= t < 28) or (33 <= t < 34):
                continue
            if calm:
                if q == 0:
                    m.place(drums, K, t, 0.35)
                    kicks.append(t)
                m.place(perc, SH, t + BEAT / 2, 0.5, 0.3)
                continue
            m.place(drums, K, t, 0.7)
            kicks.append(t)
            if q in (1, 3):
                m.place(drums, C, t, 0.36, 0.05)
            m.place(drums, HO if t >= 20 else HC, t + BEAT / 2, 0.13 if t >= 20 else 0.16, 0.25)
            for s16 in (1, 3):
                m.place(perc, SH, t + s16 * BEAT / 4, 0.4, -0.3)
        # taiko: har takt boshida, kulminatsiyada ko'proq
        t0 = b * BAR
        if t0 < 34 and not (28 <= t0 < 34):
            m.place(drums, T, t0, 0.55, -0.15)
            if t0 >= 20:
                m.place(drums, TS, t0 + 1.5 * BEAT, 0.4, 0.2)
                m.place(drums, TS, t0 + 1.75 * BEAT, 0.3, 0.2)
    # taiko roll'lar (intro oxiri, 19.5-20, 27.5-28 va 33-34)
    for start, end_ in ((2.5, 4.0), (19.5, 20.0), (27.5, 28.0), (33.0, 34.0)):
        t, k = start, 0
        while t < end_ - 1e-6:
            prog = (t - start) / (end_ - start)
            m.place(drums, TS if k % 2 else T, t, 0.2 + 0.45 * prog, (-1) ** k * 0.25)
            t += BEAT / 2 if prog < 0.5 else BEAT / 4
            k += 1

    # --- intro qo'ng'iroqchalari
    for i, x in enumerate((74, 76, 79, 81, 83, 86)):
        m.place(perc, chime(mf(x)), 0.3 + i * 0.32, 0.06, -0.6 + 0.24 * i)

    # --- SFX
    for t_end, ln in ((4.0, 3.5), (20.0, 2.0), (34.0, 3.0)):
        m.place(sfx, m.riser(ln), t_end - ln, 0.24)
    for t in (4.0, 20.0, 34.0):
        m.place(sfx, m.impact(), t, 0.38)
        m.place(drums, m.crash(3.0 if t == 34 else 2.5), t, 0.5)
        m.place(drums, T, t, 0.8)
    for t in CUTS:
        if t in (4.0, 20.0, 34.0):
            continue
        m.place(sfx, m.whoosh(0.6, 1 if int(t * 2) % 2 else -1), t - 0.36, 0.13)
    m.place(sfx, m.whoosh(0.9, 1), 4.0 - 0.54, 0.2)

    # --- sidechain
    t = np.arange(N) / SR
    duck = np.ones(N)
    for tk in kicks:
        i0 = int(tk * SR)
        nn = min(int(0.3 * SR), N - i0)
        tt = np.arange(nn) / SR
        duck[i0:i0 + nn] = np.minimum(duck[i0:i0 + nn], 1 - 0.45 * np.exp(-tt / 0.09))
    duck = np.convolve(duck, np.ones(48) / 48, mode="same")

    hp = lambda x, f: np.vstack([m.fft_filter(x[0], lo=f), m.fft_filter(x[1], lo=f)])  # noqa: E731
    pad_w = hp(pad, 180) * duck * 0.8
    kot_w = m.ping_pong(kot, BEAT * 0.75, fb=0.3, repeats=4)
    lead_w = m.ping_pong(lead, BEAT * 0.75, fb=0.3, repeats=4)
    bass_w = np.vstack([m.fft_filter(bass[0], hi=900), m.fft_filter(bass[1], hi=900)]) * duck

    wet = m.convolve_stereo(pad_w * 0.5 + kot_w * 0.7 + lead_w * 0.7 + perc * 0.5 + sfx * 0.25,
                            m.reverb_ir(3.5, 1.4))
    wet_d = m.convolve_stereo(hp(drums, 200), m.reverb_ir(1.6, 3.5, seed=5))
    mix = pad_w + kot_w + lead_w + bass_w + drums + perc + sfx + wet * 0.38 + wet_d * 0.14
    # past chastotalarni biroz yumshatish (taiko + kick + bass to'planib qolmasligi uchun)
    mix = mix - 0.4 * np.vstack([m.fft_filter(mix[0], hi=90), m.fft_filter(mix[1], hi=90)])

    fade_in = np.clip(t / 0.08, 0, 1)
    fade_out = np.where(t > TOTAL - 3.0, np.clip((TOTAL - t) / 3.0, 0, 1) ** 1.5, 1)
    mix *= fade_in * fade_out
    mix /= np.percentile(np.abs(mix), 99.9) + 1e-9
    mix = np.where(np.abs(mix) > 0.8, np.sign(mix) * (0.8 + 0.2 * np.tanh((np.abs(mix) - 0.8) / 0.2)), mix)
    return mix * 0.95


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "ujc_music_raw.wav"
    m.write_wav(out, build())
    print("wrote", out)

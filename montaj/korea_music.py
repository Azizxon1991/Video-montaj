"""Oʻzbekiston–Koreya uchrashuvi roligi uchun original musiqa.

E-major pentatonika (E F# G# B C#), C#m - A - E - B, 120 BPM.
Kayagum (gayageum) uslubidagi tor: Karplus-Strong + uzun notalarda "nonghyeon" vibratosi,
janggu barabani (past "kung" + baland "deok"), zamonaviy yengil ritm.
  0-4    intro titr        : pad, kayagum arpedjio, qo'ng'iroqchalar, riser, janggu roll
  4-19   tashrif, hovli    : ritm + kayagum melodiyasi
  19-34  ichkarida, davra  : kulminatsiya (oktava yuqori qo'ng'iroq, ochiq hat)
  34-44  ishtirokchilar    : barabanlarsiz, sokin yakun, 42 s da yakuniy akkord
"""
import sys

import numpy as np

import music as m
import ujc_music as u

TOTAL = 44.0
m.TOTAL = TOTAL
m.N = int(m.SR * TOTAL)
SR, BEAT, BAR, N = m.SR, m.BEAT, m.BAR, m.N
RNG = np.random.default_rng(23)

CHORDS = [
    (49, [61, 64, 68]),  # C#m
    (45, [57, 61, 64]),  # A
    (52, [56, 59, 64]),  # E
    (47, [54, 59, 63]),  # B
]
MELODY = [
    [(0, 1, 73), (1, 0.5, 71), (1.5, 0.5, 73), (2, 1.5, 76), (3.5, 0.5, 73)],
    [(0, 1, 73), (1, 1, 71), (2, 2, 68)],
    [(0, 0.5, 68), (0.5, 0.5, 71), (1, 1, 73), (2, 1, 71), (3, 1, 68)],
    [(0, 2, 66), (2, 1, 68), (3, 1, 71)],
]
CUTS = [4.0, 7.0, 9.0, 11.5, 14.0, 17.0, 19.0, 21.5, 24.0, 26.5, 29.5, 32.0, 34.0]
HITS = (4.0, 19.0)


def gayageum(freq, length, bright=0.6, vib=False):
    y = u.koto(freq, length, bright)
    if vib:  # nonghyeon: 0.25 s dan keyin kuchayib boruvchi vibrato (kasr kechikish orqali)
        t = np.arange(len(y)) / SR
        dev = 0.016 * np.clip((t - 0.25) / 0.4, 0, 1)  # chastota og'ishi ~ +-0.28 yarim ton
        tt = t + dev / (2 * np.pi * 5.5) * np.sin(2 * np.pi * 5.5 * t)
        y = np.interp(tt * SR, np.arange(len(y)), y)
    return y


def janggu_kung():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 85 + 60 * np.exp(-t * 25)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)
    skin = m.fft_filter(RNG.standard_normal(n), lo=100, hi=1200) * np.exp(-t * 30) * 0.4
    return np.tanh(1.3 * (body + skin)) * 0.8


def janggu_deok():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    crack = m.fft_filter(RNG.standard_normal(n), lo=1200, hi=7000) * np.exp(-t * 70)
    tone = np.sin(2 * np.pi * 520 * t) * np.exp(-t * 35) * 0.5
    return (crack * 0.7 + tone) * 0.8


def bright_fn(t):
    t = np.asarray(t, dtype=float)
    intro = 450 + 2400 * np.clip(t / 4, 0, 1) ** 2
    rest = np.where(t >= 34, 1800, np.where(t >= 19, 4000, 2900))
    return np.where(t < 4, intro, rest)


def build():
    pad, gay, lead, bass, drums, perc, sfx = (m.buf() for _ in range(7))
    mf = m.midi
    main_bars = int(34 / BAR)  # 17
    all_bars = int(42 / BAR)   # 21 (oxirgi akkord 42 s da)

    # --- pad
    for b in range(all_bars):
        t0 = b * BAR
        _, notes = CHORDS[b % 4]
        for x in notes:
            m.place(pad, m.supersaw(mf(x), BAR, bright_fn, t0), t0, 0.16)
        if 19 <= t0 < 34:
            m.place(pad, m.supersaw(mf(notes[2] + 12), BAR, bright_fn, t0), t0, 0.07)
    for x in (52, 56, 59, 64, 68, 71):  # yakuniy E-major
        m.place(pad, m.supersaw(mf(x), 0.5, lambda t: np.full_like(t, 2200.0), 42.0, rel=2.0), 42.0, 0.15)

    # --- kayagum arpedjio (8-lik)
    arp = [0, 1, 2, 1, 2, 1, 0, 2]
    for b in range(all_bars):
        _, notes = CHORDS[b % 4]
        for s8 in range(8):
            t = b * BAR + s8 * BEAT / 2
            vel = 0.55 + 0.45 * (s8 % 2 == 0)
            if t < 4:
                vel *= 0.35 + 0.65 * t / 4
            if t >= 34:
                if s8 % 2:
                    continue
                vel *= 0.8
            m.place(gay, gayageum(mf(notes[arp[s8]] + 12), 1.2, 0.45), t, 0.10 * vel, 0.4 * np.sin(s8 * 0.9))

    # --- melodiya: 4-34 kayagum, 19-34 qo'ng'iroq oktava yuqori, 34-42 sokin takror
    for b in range(2, all_bars):
        for off, ln, x in MELODY[b % 4]:
            t = b * BAR + off * BEAT
            if t >= 42:
                continue
            long_ = ln >= 1.5
            g = 0.30 if t < 34 else 0.24
            m.place(gay, gayageum(mf(x), 2.2 if long_ else 1.6, 0.75, vib=long_), t, g, -0.1)
            if 19 <= t < 34:
                m.place(lead, m.bell(mf(x + 12), ln * BEAT + 1.0), t, 0.09)

    # --- bass
    for b in range(2, all_bars):
        root, _ = CHORDS[b % 4]
        if b * BAR >= 34:  # sokin qism: uzun notalar
            m.place(bass, m.bass_note(mf(root - 12), BAR * 0.95), b * BAR, 0.16)
            continue
        for e in range(8):
            t = b * BAR + e * BEAT / 2
            if (18.5 <= t < 19) or (33 <= t < 34):
                continue
            m.place(bass, m.bass_note(mf(root - 12 + (12 if e in (3, 7) else 0)), BEAT / 2 * 0.85), t, 0.21)
    m.place(bass, m.bass_note(mf(40), 2.0), 42.0, 0.25)

    # --- ritm
    K, C, HC, HO, SH = m.kick(), m.clap(), m.hat(), m.hat(True), u.shaker()
    KU, DE = janggu_kung(), janggu_deok()
    kicks = []
    for b in range(2, main_bars):
        for q in range(4):
            t = b * BAR + q * BEAT
            if (18.5 <= t < 19) or (33 <= t < 34):
                continue
            m.place(drums, K, t, 0.68)
            kicks.append(t)
            if q in (1, 3):
                m.place(drums, C, t, 0.34, 0.05)
            m.place(drums, HO if t >= 19 else HC, t + BEAT / 2, 0.12 if t >= 19 else 0.15, 0.25)
            for s16 in (1, 3):
                m.place(perc, SH, t + s16 * BEAT / 4, 0.38, -0.3)
        # janggu: "kung . deok deok . kung deok ." uslubidagi naqsh
        t0 = b * BAR
        for off, ins, g in ((0, KU, 0.45), (0.75, DE, 0.30), (1.5, DE, 0.25), (2.5, KU, 0.35),
                            (3.0, DE, 0.30), (3.5, DE, 0.22)):
            t = t0 + off * BEAT
            if (18.5 <= t < 19) or (33 <= t < 34):
                continue
            m.place(drums, ins, t, g, -0.3 if ins is KU else 0.3)
    # janggu roll'lar
    for start, end_ in ((2.5, 4.0), (18.5, 19.0), (33.0, 34.0)):
        t, k = start, 0
        while t < end_ - 1e-6:
            prog = (t - start) / (end_ - start)
            m.place(drums, KU if k % 2 == 0 else DE, t, 0.15 + 0.4 * prog, (-1) ** k * 0.3)
            t += BEAT / 2 if prog < 0.5 else BEAT / 4
            k += 1

    # --- qo'ng'iroqchalar (intro va yakun)
    for i, x in enumerate((76, 78, 80, 83, 85, 88)):
        m.place(perc, u.chime(mf(x)), 0.3 + i * 0.32, 0.055, -0.6 + 0.24 * i)
        m.place(perc, u.chime(mf(x)), 42.1 + i * 0.22, 0.04, 0.6 - 0.24 * i)

    # --- SFX
    for t_end, ln in ((4.0, 3.5), (19.0, 2.0)):
        m.place(sfx, m.riser(ln), t_end - ln, 0.24)
    for t in HITS:
        m.place(sfx, m.impact(), t, 0.36)
        m.place(drums, m.crash(2.5), t, 0.5)
        m.place(drums, KU, t, 0.6)
    m.place(drums, m.crash(1.8), 34.0, 0.3)  # sokin qismga yumshoq o'tish
    for t in CUTS:
        if t in HITS:
            continue
        m.place(sfx, m.whoosh(0.6, 1 if int(t * 2) % 2 else -1), t - 0.36, 0.12)
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

    def hp(x, f):
        return np.vstack([m.fft_filter(x[0], lo=f), m.fft_filter(x[1], lo=f)])
    pad_w = hp(pad, 180) * duck * 0.8
    gay_w = m.ping_pong(gay, BEAT * 0.75, fb=0.28, repeats=4)
    lead_w = m.ping_pong(lead, BEAT * 0.75, fb=0.3, repeats=4)
    bass_w = np.vstack([m.fft_filter(bass[0], hi=900), m.fft_filter(bass[1], hi=900)]) * duck

    wet = m.convolve_stereo(pad_w * 0.5 + gay_w * 0.7 + lead_w * 0.7 + perc * 0.5 + sfx * 0.25,
                            m.reverb_ir(3.5, 1.4, seed=7))
    wet_d = m.convolve_stereo(hp(drums, 200), m.reverb_ir(1.4, 3.8, seed=9))
    mix = pad_w + gay_w + lead_w + bass_w + drums + perc + sfx + wet * 0.38 + wet_d * 0.13
    mix = mix - 0.4 * np.vstack([m.fft_filter(mix[0], hi=90), m.fft_filter(mix[1], hi=90)])

    fade_in = np.clip(t / 0.08, 0, 1)
    fade_out = np.where(t > TOTAL - 2.0, np.clip((TOTAL - t) / 2.0, 0, 1) ** 1.5, 1)
    mix *= fade_in * fade_out
    mix /= np.percentile(np.abs(mix), 99.9) + 1e-9
    mix = np.where(np.abs(mix) > 0.8, np.sign(mix) * (0.8 + 0.2 * np.tanh((np.abs(mix) - 0.8) / 0.2)), mix)
    return mix * 0.95


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "korea_music_raw.wav"
    m.write_wav(out, build())
    print("wrote", out)

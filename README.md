# Video montaj

Natija: **`output/montaj.mp4`** — 1080×1920 (vertikal, Reels/TikTok/Shorts), 30 fps, 33.8 s, H.264 + AAC.

## Montaj tarkibi

| Vaqt | Lavha | Ishlov |
|---|---|---|
| 0–4 s | Mehmonxona atriumi (qandil) | 0.7x slow-motion (harakat interpolyatsiyasi), Ken Burns zoom, light leak bilan ochilish |
| 4–12 s | Marrakesh Restaurant | iPhone HDR (HLG) → SDR tonemapping, 2x → 0.85x silliq speed-ramp, "hblur" whip o'tish + zoom-punch |
| 12–20 s | Loyiha muhokamasi (2 lavha) | vid.stab stabilizatsiya, shovqin tozalash, iliq rang |
| 20–24 s | Chorvachilik fermasi (CCTV) | vaqt/kamera yozuvlari kesib tashlangan, gorizontaldan vertikalga pan, denoise, oq "flash" o'tish |
| 24–33.8 s | Final: atrium shifti | 0.9x slow-motion, yuqoriga o'tish, yakuniy yozuv, fade-out |

Umumiy: rang korreksiyasi (har bir lavha alohida), vinyetka, yengil film grain, light leak,
animatsiyali yozuvlar (harfma-harf chiqish, oltin chiziq), zarb nuqtalarida kamera titrashi.

## Ovoz

Videolarning asl ovozlari butunlay o'chirilgan. Musiqa `montaj/music.py` da noldan sintez qilingan
(original, mualliflik huquqi muammosi yo'q): 120 BPM, Am–F–C–G, riser, impact, whoosh effektlari
har bir kesimga aniq moslangan. Loudness: -14 LUFS (ijtimoiy tarmoqlar standarti).

## Qayta yig'ish

```bash
python3 montaj/build.py <manba_videolar_papkasi> output/montaj.mp4 /tmp/montaj_work
```

Talablar: `ffmpeg` (libzimg, vid.stab, libx264), Python 3 + `numpy`, `Pillow`.
Yozuvlarni o'zgartirish: `montaj/overlays.py` dagi `CAPTIONS` ro'yxati.

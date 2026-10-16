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

---

# UJC Qoʻqon — Oʻzbekiston–Yaponiya markazi ochilishi

Natija: **`output/ujc_qoqon.mp4`** — 1080×1920, 30 fps, 41 s, -14 LUFS.

| Vaqt | Lavha |
|---|---|
| 0–4 s | Ochilish afishasi (karta ko'rinishida, xira fon, zoom-out) |
| 4–8 s | Mehmonlarni non-tuz bilan kutib olish (chapdan o'ngga pan) |
| 8–13 s | Tantanali marosim va nutq |
| 13–17 s | Markaz bilan tanishuv |
| 17–20 s | Hamkorlik uchrashuvi (bayroqlar) |
| 20–28 s | Taqdimot, ko'rishishlar, esdalik suratlari |
| 28–34 s | Jurnalistlar bilan suhbat (video, asl ovozi olib tashlangan, stabilizatsiya, HDR→SDR) |
| 34–41 s | UJC logotipi animatsiyasi, shior, yaponcha nom |

Musiqa (`montaj/ujc_music.py`): original, yapon "yo" pentatonikasi — koto (Karplus-Strong), taiko,
pad, bass; drop/taiko zarblari kesimlarga moslangan, intervyu qismida sokin.
Burchakda kichik UJC logotipi, animatsiyali yozuvlar, light leak, vinyetka, grain.

```bash
python3 montaj/ujc_build.py <manba_papka> output/ujc_qoqon.mp4 /tmp/ujc_work
```
Yozuvlar: `montaj/ujc_build.py` dagi `CAPTIONS`; rasm kadrlash/harakat: `SHOTS`.

# Tier 2 camera measurements on v15, September 9, 2026

**Two things could be measured on the installed v15 without a person at the
phone: an eight-minute Xiaomi video recording with thermal, clock and
frame-timing curves, and one photo per zoom step. The recording ran at a
steady 24 fps with no dropped frame, no thermal status change and a 2.6 °C
board rise; the photo series shows that the pitch-dark desk scene routes every
zoom step to the main sensor, so lens, focus and effect comparisons need a lit
scene and a person.** The video matrix itself could not start: the app's
resolution and frame-rate controls are inert on v15 for the reason in the
[camcorder profile record](camera-video-profiles-20260909.md). Nothing here
changed system state; the camera app's Dolby Vision toggle was turned off and
back on during the session, and the app was left in rear Photo mode.

## Sustained recording, 1080p, Dolby Vision on

Xiaomi Camera, Video mode, defaults (1080P, 30FPS, Dolby Vision on), 480 s
requested, phone flat on the desk in a dark room and on USB. Samples every 5 s.

| Measurement | Result |
| --- | --- |
| File | HEVC 1920×1080, Dolby Vision profile 8 (HLG, BT.2020), AAC 48 kHz mono, 479.6 s, 133.7 MB |
| Frame rate | 24.01 fps in every 30 s window, 11,515 frames, no inter-frame gap over 100 ms |
| Board temperature | 33.6 °C at start, 36.1 °C at the end, monotonic |
| Battery temperature | 32.7 °C to 35.7 °C; charge current 23 to 55 mA throughout |
| Thermal service status | 0 for the whole recording |
| CPU clocks | Prime/gold policy 1.1 to 1.9 GHz, little cluster 883 MHz, GPU 160 MHz; CPU pressure `some avg10` about 33 % |
| Audio | Peak −8.1 dBFS, RMS −41.9 dBFS: the microphone track is live and records the room |

The app announced 30 fps, and the file is 24 fps. The camera log shows the
HAL frame-rate range 24 to 30 for this session and the app's video settings
include "Auto frame rate: reduce frame rate for videos in low light or high
temperature", so this is the low-light path of that feature on a black scene,
not a dropped-frame condition. The same recording in daylight is the real
frame-rate check. With a black scene and 1080p, this is not a thermal stress
test either; the 4K and 60 fps runs wait for the profile fix.

## Per-zoom photos, Photo mode

One still at each zoom button (0.6×, 1×, 2×, 3.2×, 4.3×, 8.6×), Ultra HDR
JPEG, 3072×4096. EXIF focal lengths: 2.13 mm at 0.6× (ultrawide), 8.71 mm at
every other step (main sensor), with 35 mm equivalents 14, 23, 46, 75, 100 and
200. Exposure 1/3 s at ISO 3200 to 4000; mean luma under 0.1 of 255. On this
scene the app keeps the telephoto steps on the main sensor's crop, which
matches its "adaptive telephoto: switch based on distance and brightness"
setting. Focus distance is not written in EXIF; the maker note is present.
Nothing about focus, exposure choice or lens transitions can be judged from
black frames.

## What this does not prove

Frame rate, exposure, focus, stabilization and effect quality in real light;
4K, 8K, 60 fps and slow motion (unavailable on v15); thermal behaviour under a
real load; microphone response beyond "not silent". The
[structured record](../research/tier2-camera-v15-measurements-20260909.json)
holds the numbers; media files, logs and UI dumps stay under the ignored
evidence directory.

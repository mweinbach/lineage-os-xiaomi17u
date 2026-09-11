# Now Playing on the Qualcomm DSP, September 11, 2026

**Now Playing (Pixel ambient music recognition) is fully provisioned on this unit
and switched off by a single missing input: the two-file Qualcomm-DSP
music-detector model that Google ships on Snapdragon Pixels. This page records
the gate analysis from the installed ASI's own code, the model's provenance, and
the guarded fragment that installs it. The on-device result is recorded
separately once a set carrying it is installed.** You asked to get it working
and approved borrowing the Pixel model for this purpose.

## What the settings switch actually checks

The installed Android System Intelligence (`com.google.android.as`,
`B.13.playstore.pixel10`) renders the Now Playing screen normally but greys the
"Identify songs playing nearby" switch. Decompiling the app (jadx, as for the
Leica gate) gives the exact condition, in the settings fragment's resume path:
the switch is enabled only when `AmbientMusicServiceManager.l() && r()`.

- `l()` is "allowed for this user". It is **true** here, measured directly: the
  setup wizard's Turn-on button is gated by exactly `l()` and renders enabled.
- `r()` is a **file check**. For every non-Tensor device it requires
  `/product/etc/firmware/music_detector.sound_model` and
  `music_detector.descriptor` (falling back to `/vendor` then `/system`). The
  Tensor variant (`music_detector.sound_model_tflite`) is chosen only when that
  file exists, which it does not, so this phone takes the classic path. None of
  the files exist on the unit, so `r()` is false. That is the whole blocker.

Everything else is already in place and was verified read-only: ASI holds
`CAPTURE_AUDIO_HOTWORD`, `MANAGE_SOUND_TRIGGER`, `CAPTURE_AUDIO_OUTPUT` and
`RECORD_AUDIO`, and its uid is in the audio policy's hotword-capture list; the
Settings injection resolves; `MusicRecognitionManagerService` runs; the Pixel
feature declarations are present; 30 NowPlaying flags are delivered live and the
other 79 fall back to compiled defaults (`now_playing_allowed` defaults true);
and the device exposes the low-power `hotword_input` capture path. The engine is
DSP-only: when enabled it reads the model bytes, loads them through
`SoundTriggerManager.loadSoundModel` as a generic sound model (UUID
`9f6ad62a-1f0b-11e7-87c5-40a8f03d3f15`) onto sound-trigger module 0, and starts
intent-based recognition; the bundled `libsense_nnfp_v3` fingerprinter then
matches triggered audio against the downloaded music database on the AP.

## The DSP this model targets

Sound-trigger module 0 on this unit is the real Qualcomm HAL:

| Property | Value |
| --- | --- |
| Implementor / description | QUALCOMM Technologies, Inc / Sound Trigger HAL, version 259 |
| HAL UUID | `68ab2d40-e860-11e3-95ef-0002a5d5c51b` (the standard QTI STHAL UUID) |
| Recognition modes | 9 = VOICE_TRIGGER + **GENERIC_TRIGGER** |
| Max sound models | 8; capture transition and concurrent capture supported |
| Model architecture restriction | none |

Generic-trigger models are exactly what the music detector is, so the model is
the architecturally right object for this HAL. Whether the SVA 7.0 firmware on
this SoC accepts a model built for the 765G era is only provable by loading it;
that load result is the verdict and is recorded in the install page.

## The model and its provenance

| File | Bytes | SHA-256 |
| --- | --- | --- |
| `music_detector.sound_model` | 34432 | `5472e7358178e598251476cf67d4d0b120d1b702611a470ad242163b266c0e67` |
| `music_detector.descriptor` | 1057 | `dadf2cbd2978dce2f3832eafe6d6e1fbf4c777232c584666dc7e574c421f5989` |

Source: TheMuppets `proprietary_vendor_google_barbet` (LineageOS vendor blobs
extracted from the Pixel 5a factory image), branch `lineage-23.2`, commit
`c17e31ec9950bfd3c54690047be31b03b45495cf`, path
`proprietary/product/etc/firmware/`. The git blob hashes were recomputed locally
and matched, and the same two blobs are byte-identical in the Pixel 5 (`redfin`)
and Pixel 4a 5G (`bramble`) trees, so this is one shared model across three
Snapdragon generations. The descriptor is a protobuf of classifier tunables
whose names match ASI's `NowPlaying__music_model_*` flags. The blobs are Google's
proprietary Pixel firmware, borrowed with explicit approval; they live only in the
ignored `vendor/xiaomi/nezha-nowplaying` bundle and appear in Git as hashes.

## The guarded fragment

`device/xiaomi/nezha/now-playing-dsp-model.mk`, selector
`NEZHA_NOW_PLAYING_DSP_MODEL`, admits the bundle by size and SHA-256 through
`now-playing-dsp-model/verify.py` against
[`config/nezha-now-playing-dsp-model.json`](../config/nezha-now-playing-dsp-model.json)
and copies the two files to `/product/etc/firmware/`. It refuses a drifted or
missing blob, refuses a second owner of the destination, and changes nothing
else: no HAL, SELinux, vendor or identity change. `tests/test_now_playing_dsp_model.py`
exercises the selector, the admission and the copy with synthetic bundles, so
the offline suite never needs the proprietary files.

## What this page does not prove

That the Qualcomm firmware loads the model, that recognition triggers, or that a
song is identified. Those are device results for the install page of the set
that carries this fragment.

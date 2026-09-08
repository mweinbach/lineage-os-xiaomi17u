# Camera v12 installation and validation, 2026-09-08

**V12 (`nezha.0a0b5c6187d711a32aa3e46e`) is installed on slot A with normal
Android SELinux Enforcing. All ten rear/front CameraX effect captures now
fully decode as Ultra HDR.** Xiaomi ordinary photos, both 50 MP paths,
200 MP and Pro RAW also pass. UltraRAW still needs compressed Bayer support,
and audio policy initialization still blocks video. Complete camera acceptance
remains false.

The [package checkpoint](camera-v12-package-20260908.md) records the preceding
build, signing and bundle verification. The user subsequently approved that
exact eight-image bundle, reboot, camera/audio/video tests and root diagnostics.
All eight writes were acknowledged; there was no wipe or slot change. Normal
boot completed in 25.5 seconds. All seven selected installed framework, native
and application payloads match the verified component bytes.

## Captures and independent decodes

| Path | Saved output | Observed result |
| --- | --- | --- |
| Xiaomi rear/front Photo | 12.5 MP JPEG/R | Full JPEG and Ultra HDR decodes pass |
| Xiaomi main 50 MP | 6144 × 8192 JPEG/R | Full JPEG and Ultra HDR decodes pass |
| Xiaomi telephoto 50 MP | 6144 × 8160 JPEG/R | Full JPEG and Ultra HDR decodes pass |
| Xiaomi Pro telephoto 200 MP | 16320 × 12288 JPEG/R | Full JPEG and Ultra HDR decodes pass |
| Xiaomi Pro RAW | 4080 × 3072 DNG plus companion JPEG | Full LibRaw decode passes; orientation gives a 3072 × 4080 TIFF |
| Physical wide / ultrawide / telephoto RAW | 4096 × 3072 / 4096 × 3072 / 4080 × 3072 DNG | All three fully decode to RGB; capture crash buffers remain unchanged |
| Aperture rear/front Bokeh, HDR, Night, Face Retouch and Auto | Ten 3072 × 4096 JPEG/R files | All ten full JPEG and Ultra HDR decodes pass |

The Aperture process and its start time remain the same throughout both
five-effect sequences. The provider, cameraserver and system-server processes
also retain their identities, and all ten capture crash buffers are unchanged.
The front HDR neutral-gainmap failure measured on v11r1 is resolved in this
validation. The static, mostly dark scene does not establish useful effect
quality, focus, stabilization or sensor-native resolving power.

The 200 MP image is 19,420,039 bytes, SHA256
`5ae769a14f5e10f455312005aa1241da827620087a20ebdd369d21c07c682e76`.
The retained unmodified libultrahdr 1.4.0 source at commit
`d52a0d13814ca399fc8a07e23de1d2c63f0e8404`, built with a 16384 dimension
limit, fully decodes it to 1,604,321,280 bytes of RGBA F16 HDR data.
The decoded output hash is
`82e1ed2bfa557bb04e2c803dcc83a8edd9053a6d81a61a3a69b84a182cba101c`.

The Pro RAW DNG is 25,097,580 bytes, SHA256
`614241544ca336b9fd82ecd4ecbba8147a1590a9088cc88716f9b3089143fd38`.
Its TIFF orientation is 6. The first host dimension assertion omitted LibRaw's
rotation; inspecting the retained full decode and TIFF fields establishes the
correct portrait dimensions without another capture or decode.

## UltraRAW diagnosis

The new hidden `DngCreator` entry points exist and execute. The writer rejects
this capture because its metadata describes format **32**, while the v12
implementation accepts only linear RGB format **15**. The companion JPEG saves;
the DNG remains empty. There is no missing-method exception on this path now.

A one-capture camera-service tag watch produced no compression metadata. A
subsequent bounded writer trace collected the actual 604-byte metadata and only
the first 32 bytes of the compressed buffer. It used the verified installed
library, a separate tracing instance and the Camera app's threads; its two
probes and tracing instance were removed afterward. This uses the kernel's
[documented uprobe tracing facility](https://docs.kernel.org/trace/uprobetracer.html).
Normal Android remained Enforcing, and no library file was changed.

The measured metadata is:

| Field | Measured value |
| --- | --- |
| Format | 32, compressed Bayer RAW |
| Image | 4080 × 3072 |
| Tile grid | 8 × 8, 64 tiles |
| Total compressed bytes | 13,915,666; exactly equal to the sum of the 64 tile sizes |
| First lossless JPEG tile | 16-bit, 255 × 384, two components |
| Effective Bayer tile | 510 × 384 samples |

The remaining metadata words are zero. The two JPEG components pack Bayer
samples; this needs a CFA DNG path with matching dimensions and metadata.
Simply accepting the format number in the existing three-channel RGB writer
would be incorrect. Complete compressed-image decoding remains pending the
source repair and a separately approved successor installation.

The first UltraRAW capture overlaps a Wallpaper process crash reporting a
missing `ClockProviderPlugin` dependency. Its global crash buffer therefore
changes, while the camera app, provider, cameraserver and system-server
identities remain unchanged. This separate failure is retained in the record;
full phone health is not claimed.

## Audio and video

Startup audio diagnostics were collected before enabling root ADB. The two
earlier `AudioOutputFlags` and `AudioUsage` conversion errors do not recur.
Initialization instead rejects `AudioDeviceDescription{type: OUT_DEVICE,
connection: multiroute}`. The 75-second snapshot still has a null audio policy
manager. Video was not retried against that measured failure.

The live ODM/vendor audio configuration files match the factory files.
Factory converter inspection maps the multiroute descriptor to legacy device
value `0x20000004`. The configuration audit also identifies the MIHC encoding,
`audio/vnd.mi.mihc`, whose factory format value is `0x40000000`; this is absent
from the current conversion table. These are repair inputs, not proof that
audio initialization will succeed after adding them. Device/format validation
and the remaining configuration paths still require review.

## Retention, cleanup and evidence

Before the first camera launch, all 513 Camera CE members and five DE members
retain their bytes and metadata. The active Camera APK and signer are unchanged.
This comparison covers Camera app data and does not verify all userdata.

Cleanup restores Xiaomi rear Photo at 1× and 12.5 MP, with Pro format JPEG,
and Aperture rear with no effect, Ultra HDR on and RAW off. All three camera
test apps are stopped. USB stay-awake retains its original value of zero.
The temporary camera tag watch is stopped and both diagnostic probes are
removed. Final checks reconfirm the installed build, slot A and Enforcing policy.

The [structured runtime record](../research/camera-v12-install-validation-20260908.json)
binds installation, app data, captures, decoders, process checks, diagnostics and
cleanup. Raw logs, camera images, app data and proprietary analysis remain
ignored. The [v11r1 predecessor](camera-v11-install-validation-20260908.md), its
bundle and earlier recovery/stock-return inputs remain preserved. A future
bundle requires its own specific flash/reboot approval.

The completed runtime record passes all 67 evidence-pin checks.
`make test-current` passes 939 tests in 28.347 seconds; `make test` passes
4,892 tests in 186.830 seconds plus shell checks.

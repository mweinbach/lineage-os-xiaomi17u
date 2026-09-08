# Camera v13 installation and validation, 2026-09-08

**V13 is installed and booted on slot A with normal Android SELinux Enforcing.**
UltraRAW now saves a DNG whose complete Bayer image and embedded preview decode.
Audio policy initializes, and a short Xiaomi video saves fully decodable video
and audio tracks. The working photo, RAW and ten warm CameraX effect cases also
pass. Image quality and sustained behavior remain separate acceptance work.

## Installation and retained data

The user separately approved the exact [v13 package](camera-v13-package-20260908.md).
Shared Super and all seven A-chain image writes were acknowledged. Android
completed boot in 25.5 seconds as `nezha.2c510f47f6d99b93f0c3ee11`, userdebug,
with slot `_a` and SELinux `Enforcing`. No wipe or slot change was performed.
The separate reboot receipt follows the eight-write execution receipt.

All seven selected installed component payloads match the verified archive.
Xiaomi Camera's active APK and platform signer are unchanged. Before first
launch, all 513 CE and five DE app-data members match their pre-install bytes
and metadata. This comparison covers Camera's app data, not all userdata.
The predecessor bundles, working76 recovery and private inputs remain preserved.

## Measured captures

| Path | Observed result |
| --- | --- |
| Xiaomi rear and front Photo | Both 3072×4096 JPEGs fully decode as Ultra HDR |
| Main 50 MP | 6144×8192 JPEG and full Ultra HDR decode pass |
| Telephoto 50 MP | 6144×8160 JPEG and full Ultra HDR decode pass |
| Telephoto 200 MP | 16320×12288 JPEG and full Ultra HDR decode pass |
| Xiaomi Pro RAW | 4080×3072 Bayer DNG fully decodes with LibRaw |
| Xiaomi UltraRAW | 4080×3072 compressed Bayer DNG and embedded JPEG preview fully decode |
| Physical RAW sensors | Wide and ultrawide 4096×3072, telephoto 4080×3072; all fully decode with LibRaw |
| Aperture CameraX effects | Bokeh, HDR, night, face retouch and auto on rear and front; all ten JPEG and Ultra HDR decodes pass |
| Xiaomi video | 10.079-second 1920×1080 HEVC file; all 242 video frames and the 48 kHz mono AAC track fully decode |

UltraRAW produces a 17,656,589-byte DNG. All 64 lossless JPEG tiles have the
measured 16-bit, two-component 255×384 frame layout for 510×384 Bayer tiles.
The DNG retains its Bayer CFA metadata, with valid bounded, nonoverlapping tile
segments. The embedded 4080×3072 JPEG preview fully decodes independently.
LibRaw decodes the entire DNG to a 16-bit RGB TIFF, including its orientation.
This resolves the empty Bayer DNG observed on v12.

All ten Aperture effect captures use the same application process, including
rear/front switching and mode transitions. Each resulting JPEG and gainmap
passes the independent full decoder. Camera app, provider, cameraserver and
system-server process continuity is checked around the completed app captures, and their
crash buffers remain unchanged. The retained unmodified libultrahdr 1.4.0 build
with a 16384 dimension limit fully decodes the 200 MP gainmap; its source,
binary and output hashes are reverified.

## Audio and video

AudioPolicyManager is present at the 15-, 45- and 75-second boot checkpoints,
with primary output handle 13 and the factory multiroute/MIHC values present.
The earlier rejected-device, output-flag and usage conversion errors are absent
from the captured conversion-tag logs. The zero-second dump was empty while
services were still starting. These observations were collected before enabling root ADB.

The successful video uses the visible stop button. FFmpeg fully decodes both
tracks, with recorded audio peak −29.14 dBFS and RMS −44.44 dBFS. The file also
carries Dolby Vision profile 8 configuration metadata. Those checks establish a
complete recording with nonzero audio; microphone response, playback quality,
HDR presentation and a complete video-mode matrix are unverified.

## Test observations and limits

The first video test used Back to stop, but its screenshot still showed the
recording timer. Bounded cleanup force-stopped Camera, and no completed file was
collected. The test was corrected to tap the visible stop button; its next
bounded recording passed. This failed harness attempt is retained separately.

During the 200 MP test, 81 older test files were renamed into MediaStore trash.
The collector initially treated those renamed paths as new files. Their
generated duplicate host copies were removed, and the capture record counts
only the one new non-trash photo. No device delete or restore command was
issued. Later collectors exclude hidden/trash paths.

Wallpaper & style separately reports a missing `ClockProviderPlugin` dependency
before the capture matrix. Intermittent UIAutomator dumps also failed to produce
XML; action receipts distinguish failures before and after a tap, and completed
actions were not repeated. The Wallpaper issue remains unresolved.

The scene is mostly dark and static. Useful effect quality, autofocus,
stabilization, sensor-native detail, longer recordings and other video settings
still need real-world validation. A 200 MP output file does not establish
sensor-native resolution. No remaining failure was measured in the completed
capture matrix, but this is not full camera or full-phone acceptance.

## Repository verification

`make test-current` passes 939 tests in 28.142 seconds. `make test` passes
4,892 tests in 193.203 seconds, followed by the shell syntax check. These are
offline workspace checks, separate from the device captures and decoders.
The evidence audit recomputes 66 referenced file hashes and all 23 saved media
hashes across 21 capture cases. It also verifies the rear/front service IDs and
confirms that final cleanup leaves no active camera clients.

## Cleanup and evidence

Xiaomi Camera was returned to rear Photo, 1×, 12.5 MP, with Pro format JPEG.
Aperture was returned to rear NONE with Ultra HDR on and RAW off. All three
camera test applications were stopped, USB stay-awake was restored to its
original value, and build, slot, boot completion and Enforcing policy were
rechecked. No diagnostic uprobes remain.

The [runtime evidence record](../research/camera-v13-install-validation-20260908.json)
binds installation, source, installed payloads, app data, all captures and their
independent decoders, audio startup and cleanup. Raw logs, images, app-data
archives, proprietary inputs and keys remain ignored and are not redistributed.

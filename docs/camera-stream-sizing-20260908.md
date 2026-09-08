# Factory camera stream sizing, 2026-09-08

**The factory stream-sizing hooks are restored in source and pass a native
component build.** The successor is `nezha.130611bac9232625e0066968`; its full
package is in progress and it is **not device-admitted**. The phone remains on
[v10](camera-v10-install-validation-20260908.md). Telephoto high resolution,
Xiaomi Pro RAW and Ultra RAW remain unverified with this change.

The [structured record](../research/camera-stream-sizing-20260908.json) binds
the factory analysis, source transaction, host behavior tests and native build.
The [source contract](../config/nezha-camera-stream-sizing.json) pins the five
changed files and the supplemental
[0034 patch](../patches/evolution/0034-nezha-camera-stream-sizing.patch). Apply
it after the existing [native camera hook](camera-native-hook-20260907.md).
The original 0029 patch and its templates retain their historical bytes.

## Measured problem and source change

V10 saves valid ordinary Xiaomi photos and a main-camera 50 MP Ultra HDR image.
Its telephoto 50 MP and 200 MP outputs are truncated: the JPEG/R assembler needs
8,005,848 and 17,783,654 bytes respectively in a 4,388,802-byte buffer. Xiaomi
Pro RAW also fails before HAL configuration when public-table rounding rejects
the mock camera's 4080×3072 RAW16 stream.

The factory camera service makes three additional sizing calls. Its library
exports match both the base and Qcom vtable entries:

| Method | Export address | Vtable offset | Reproduced decision |
| --- | --- | --- | --- |
| `isMockCamera` | `0x6e41c` | `0x208` | Preserve requested mock-camera dimensions before public rounding |
| `getCustomBestSize` | `0x70324` | `0xf0` | Accept an exact custom size, or seed the normal nearest-size search |
| `raiseDimensionsforCustomImageQuality` | `0x706d4` | `0xf8` | Apply the factory quality adjustment after existing privileged-client rules |

The adapter resolves these methods before publishing its opaque library object,
using the existing loader and ABI checks. Camera identity comes from the factory
metadata-derived role map. The source does not hardcode a mock-camera ID or
change the privileged-client package property.

The existing `NEZHA_CAMERA_SESSION_INJECT` selector controls the new calls. If
it is disabled or the factory adapter is unavailable, ordinary public-size
rounding and the JPEG limit remain in effect. The JPEG change permits the
existing size interpolation to exceed the public maximum for factory-identified
mock cameras. Existing privileged-client behavior is retained. Public camera
metadata, the factory verifier, signing checks and normal Android SELinux
selection are unchanged.

The Ultra RAW provider crash is a separate observed failure in vendor DNG
encoding. Correct dimensions and buffer sizing are prerequisites for repeating
that path; this change does not establish that the crash is fixed. The video
AudioRecord failure still needs audio startup diagnostics from the next
separately approved boot.

## Source, tests and native artifact

The source transaction verifies 661 rows and changes five files. It adds two
previously unrecorded source preimages, replaces three already-recorded files,
and preserves the other 656 predecessor rows. The checkout stays at
`frameworks/av` commit `dfe1a704f074bbbc3f60b740a9e5ec6b786228f3`. A fresh
upstream `bka` observation returned `64d275464c01488267ad1d73abdd0ccbc57ecf4b`;
that newer branch head was recorded without updating the selected checkout.

The actual patched sizing functions passed a C++ host harness with metadata and
factory API doubles: 43 assertions with the selector disabled and 46 enabled.
Both runs use the undefined-behavior sanitizer. Coverage includes public
rounding, missing RAW dimensions, factory mock dimensions, custom exact and
nearest sizes, quality adjustment, unavailable-library fallback, dataspace and
maximum-resolution table selection, privileged behavior and high-resolution
JPEG allocation. These are source behavior checks with synthetic inputs.

The affected module's four evidence tests pass. `make test-current` passes
939 tests in 27.889 seconds, and `make test` passes 4,885 tests in 188.047
seconds plus shell checks.

The native `libcameraservice` and `cameraserver` build completes 152 actions.
All 661 source rows match before and after. The delivered native component is
`cameraserver`, which statically links the camera service. Its 4,026,968 bytes
hash to `5dd3bc8a8105877dbff507afaf9d2a420cce53a1f3a9397f2b869aadd603c938`.
It is an AArch64 ELF with the three new factory lookup names and a defined
`__cfi_check`; no CFI exception was introduced. Compilation and these artifact
checks do not establish runtime library behavior or successful captures.

The existing Linux source volume remains attached to its sole writer VM. Host,
architecture, case-sensitive filesystem, manifest and disk checks passed before
compilation. The exact redundant guest v10 Super image was removed only after
both retained host copies matched its hash and size; free guest space rose
from about 194.1 to 202.9 GiB. Source, current output/cache, protected policy
builds and rollback bundles were retained.

Next, complete the full archive, signing and eight-image bundle checks. A new
flash/reboot approval is required before installing v11, followed by ordinary
capture regressions, telephoto 50 MP/200 MP full decodes, Pro RAW and a bounded
Ultra RAW retest. Capture audio startup diagnostics during that approved boot.

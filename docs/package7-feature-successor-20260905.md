# Package7 feature successor — September 5, 2026

The user requested fixes for fingerprint enrollment, camera initialization, and
status-bar geometry, plus integration of the native Xiaomi Camera. Package7
remains the installed, booted baseline. The existing Linux source checkout now
contains the feature successor; do not mistake it for unchanged Package7 input.

## Selected source changes

- Stock-derived framework/SystemUI geometry from the exact Nezha product
  overlays; density stays 480 dpi. See the [overlay record](../device/xiaomi/nezha/overlay/README.md).
- [Aperture admission patch](aperture-camera-admission-20260905.md): excludes
  processing-only cameras before CameraX constructs camera objects/stream maps.
- [Fingerprint lifecycle patch](package7-fingerprint-lifecycle-20260905.md):
  Nezha sensor-5/v2-specific operation, overlay, and display notifications to the
  existing Xiaomi extension. Standard authentication and policy remain intact.
- [Original Xiaomi Camera product candidate](xiaomi-camera-product-candidate.md),
  enabled explicitly through `NEZHA_XIAOMI_CAMERA=true`. The private packet is
  required when selected; the factory APK remains presigned and byte-identical.

The original source lock still matches all 1,179 upstream project revisions.
The source audit preserves the nine pre-existing modified projects; the new
patches additionally modify Aperture and frameworks/base. No source sync,
selector conversion, or cleanup of previous outputs occurred.

## Source adoption and build checkpoint

The sole source-volume VM is `twrp-nezha-upstream74-20260829`, with source at
`/work/evolution`. Read-only preflight verified Linux aarch64, case-sensitive
ext4, idle build state, 357 GiB guest free and 683 GiB host free before staging.
Those are checkpoint measurements, not reserved capacity.

Three serialized transactions retained preimages and verified all selected
source hashes before and after installation:

- `/work/validation/feature-fixes-source-20260905-v1`: display and Xiaomi Camera
  packet, 17 selected replacements/additions.
- `/work/validation/feature-fixes-source-20260905-v2`: four Aperture files and
  two fingerprint-service files.

- `/work/validation/feature-fixes-source-20260905-v3`: original Xiaomi Camera
  packet moved to `system_ext`, with its same-partition permission XML, to use
  the existing bundled-app native library namespace. Thirteen packet files
  were reverified and staged; the original APK bytes are unchanged.

Current source/input identity is `nezha.a6d3109ae93158c498bb30b0`.
The complete source inventory and operational scripts are retained privately in
`reports/feature-fixes-20260905/`. The source transaction verifies preimages,
rejects unreviewed destinations and symlinks, preserves modes, and rolls back
its own writes if verification fails.

Ordinary Soong uses separate output
`/work/out/nezha-feature-fixes-20260905-v1` via the matching relative source
alias. The preceding display/Camera-packet-only `nothing` build passed. The
initial combined component build was intentionally interrupted to correct the
Camera partition placement. The corrected run was resumed with 16 jobs after
verifying 17 available CPUs and sufficient memory, preserving completed outputs.
The native component build for `framework-res`, SystemUI, services, Aperture and
NezhaXiaomiCamera **passed**, with exit 0 recorded under
`/work/validation/feature-fixes-builds-20260905/20260905T175047`.
Its before/after source snapshots match exactly. Both apps passed dexpreopt;
Xiaomi Camera passed strict uses-library verification. The installed Camera APK
matches the original hash, its same-partition permission XML is present, and no
stale product Camera copy exists. Exact component hashes are retained in
`reports/feature-fixes-20260905/component-artifacts.json`.

The full `target-files-package` build **passed** in the same separate output,
with exit 0 recorded under
`/work/validation/feature-fixes-builds-20260905/20260905T220105`.
The final source check passed; before/after snapshots match the selected source
record. Two preceding attempts stopped on host-tool runtime crashes (Go
`merge_zips`, then Java R8); their failure evidence remains preserved. The Go
command succeeded on an isolated retry, and the final ordinary build completed
with unchanged source and compiler settings. No failed attempt is used as a
successful package record.

Archive admission, host signing, Super assembly and final artifact qualification
remain pending. All existing Package7 outputs, bundle, private inputs and
working76 recovery remain preserved.

The selected build keeps the original pinned date interface, user variant,
4 KiB checks, GMS selection, source sandboxing, strict library checks, normal
SELinux enforcement and verified-boot configuration. The internal construction
capability remains source-owned. The development signing key stays on the Mac.

## Verification and remaining device work

All **4,630** offline workspace tests passed after the final system-ext integration (204.189 seconds). The fingerprint
classes also compiled against actual Package7 headers, with 111 Java lifecycle
assertions. The Aperture helper compiled against its pinned CameraX APIs, with
15 factory behavior checks. These checks are distinct from a full component or
ROM build.

The user explicitly authorized installation, execution and removal of the
metadata-only Camera probe. It exposed the malformed processing cameras without
opening a camera; removal and package absence were verified. No other phone
change was made. No successor installation is authorized by that diagnostic
approval.

Hardware checks still needed after a separately authorized successor install:
fingerprint enrollment/unlock/cancellation and screen-off behavior; Aperture
preview/capture and available lenses; Xiaomi Camera startup, photos/video and
OEM features; visual status-bar/corner alignment. The front physical camera is
present under logical camera 0, but this Aperture fix does not create a separate
selfie selector. No hardware success or full native Camera parity is claimed.

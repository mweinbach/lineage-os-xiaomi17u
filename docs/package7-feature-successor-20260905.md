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

Archive admission, host AVB signing and reconciliation, Super assembly, full
logical-partition readback, host transfer, and eight-image bundle assembly and
independent byte verification have passed. The candidate is retained privately
at `artifacts/flash/nezha/package7-feature-fixes-20260905-v1/`. Its manifest
SHA256 is `8550182663180841592a47cc0a33efa5bb7a76f5d70a197faa4d662f47040c1f`.
Boot-content and all-eight-image error-correction qualification have passed.
The candidate is ready for a separately authorized device installation and test. All existing Package7 outputs, bundle, private inputs and
working76 recovery remain preserved.

The selected build keeps the original pinned date interface, user variant,
4 KiB checks, GMS selection, source sandboxing, strict library checks, normal
SELinux enforcement and verified-boot configuration. The internal construction
capability remains source-owned. The development signing key stays on the Mac.

## Signed artifact qualification

The reconciled target-files ZIP is
`artifacts/avb/nezha/package7-feature-fixes-20260905-v1/reconciled-v1/target-files.zip`,
SHA256 `26ae30eddfd3716212b08f4c77b9d6674db26c64c8d798e0038208f24331bc9a`
(11,100,598,089 bytes). Signing verified the full selected chain and both
reproduction passes while retaining working76. The larger system-ext allocation
is bound to the measured Camera-bearing image and admitted build, within the
unchanged dynamic-partition group and physical Super capacities.

The private delivery remains eight payloads: shared `super.img` plus `boot_a`,
`dtbo_a`, `init_boot_a`, `recovery_a`, `vendor_boot_a`, `vbmeta_a`, and
`vbmeta_system_a`. The sparse Super is 9,446,512,740 bytes, expanding to the
original 15,300,820,992-byte partition. All eight populated logical images and
six LP metadata copies match the reviewed assembly; logical B is empty.
Firmware reference images remain references, not extra flash payloads.

Completed off-device checks are recorded under
`reports/feature-fixes-20260905/qualification-prep/host/results/`:

- `apk-v1/summary.json`: all 456 APKs pass API-36 signature and 4 KiB alignment
  checks; 39 APEX payloads, 26 CAPEX pairs, and three compressed-APK/stub pairs
  pass their checks. Existing legacy signature-range, duplicate-overlay, Shell
  and OTA-key findings remain explicit. The Camera candidate adds 22 unresolved
  or ambiguous requested permissions; no extra permission grants were inferred.
- `delivery-v1/result.json`: fresh filesystem exports match all 428 direct APKs,
  36 APEX containers and three compressed APKs. FamilySpace permissions pass.
- `classpath-v1/result.json`: selected classpath JARs, SDK selection, image DAC
  and APEX payload DAC pass, with 43 protobuf captures bound to fresh inputs.
- `boot-v3/report.json`: five boot-chain images, 16 archive-member joins, init,
  fstab, ramdisk modules, DTBs/DTBO, the retained 4 KiB kernel and working76 pass.
  First-stage init differs from Package7 only in its 16-byte GNU build ID;
  all other ELF bytes and runtime CPIO ownership/mode are identical. The
  earlier exact-hash rejection is retained alongside the measured derivation.
- `vintf-semantic-review-v1.json`: all three native VINTF commands pass with 39
  freshly materialized APEX packages. Relevant content and membership join 267
  files across five images; vendor/ODM use exactly matching retained images.
  Two definition-check skips and two warnings remain, so this is not a claim
  of complete static VINTF coverage or runtime APEX/SELinux behavior.

`camera-final-image-membership.json` additionally joins the original Xiaomi
Camera APK and its same-partition permission XML to final image bytes, root-owned
mode 0644. The final Aperture APK is present in product. Original Xiaomi Camera
SHA256 remains `7bce1fb140802511bb3d6527f6fcc25ef7558f278d24229755413d3a9b42199e`.

Final FEC comparison passed for all eight admitted logical images. The native
source571 check also passed with matching before/after source cohorts. The outer
wrapper subsequently rejected a directory timestamp changed by its own result
publication; that failed transport remains preserved in
`artifacts/build-validation/feature-successor-fec-prepare-v5/`. A separate
read-only collector rehashed the 16 staged controls and exact completed receipts,
then admitted all 42 finite readbacks through the unchanged FEC semantic checks.
No FEC comparison was relabeled or rerun. Final collector/source/idle/sole-owner
checks passed. The successful recovery is
`artifacts/build-validation/feature-successor-fec-recovery-v2/completion.json`,
SHA256 `f3a846c5b9b3718d24ad40e342f18df9741241dd6092a0eea4674758ce377b7e`.
Its semantic admission is `c244278ef90608609d3067010e2b06167d78d78ec56e6fbe7b0e50dad1f83c34`.

The bundle assembler and a separate portable verifier both rehashed all eight
payloads against manifest SHA256
`8550182663180841592a47cc0a33efa5bb7a76f5d70a197faa4d662f47040c1f`.
This is a private image bundle, not an OTA or TWRP installer. Its device-admission,
flash-authorization, boot and hardware fields remain false. The consolidated
private record is `reports/feature-fixes-20260905/qualification-summary.json`,
SHA256 `2cba7071bc494b7dd8e13f3a39864764d09770c625b1ffafeed9590f58f1daa1`.

## Verification and remaining device work

All **4,636** offline workspace tests passed after the final dynamic-budget and
contract updates (206.250 seconds). The fingerprint
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

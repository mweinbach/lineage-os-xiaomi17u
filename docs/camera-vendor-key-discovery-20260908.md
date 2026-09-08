# Xiaomi Camera vendor-key discovery (2026-09-08)

**The v9 Camera now passes its original verifier, but its first rear Photo
capture did not save a full image.** The app omitted the shot-name control that
the vendor processing path expects. A guarded source candidate restores the
factory app's registered-vendor-key discovery on this AOSP framework. The source is staged as `nezha.8fb05f49f5a7e31a6a3a498b` (658 rows);
its affected framework build passed with all 658 inventory rows unchanged.
It has not been installed.

## Measured v9 failure

The phone completed the authorized eight-image installation and booted
`nezha.393aae12fba9ebe8627cdc38` on slot A with SELinux Enforcing. The installed
Camera APK matches the final signed archive, retains app ID 10422, and its
credential/device-encrypted app-data archives were byte-identical to their
preflash copies before the first launch. CameraOpt reported
`boot_callback_completed=true`, `native_initialization_failure=null`, and then
`last_original_verifier_result=true` after the real Camera app called it.

The rear Photo UI selected 1×. Its single shutter request at 22:45:59 local
created a preview thumbnail, then reported `onPictureTakenFinished: succeed =
false` about twelve seconds later. No new file remained in DCIM/Camera. There
was no Camera, cameraserver or provider fatal crash in this capture window.
The app was stopped after collecting the failure.

The retained log establishes this sequence:

1. `MiCamera2MIVIStill` generated `IMG_20260907_224559.jpg` for a 4096×3072 shot.
2. The vendor `MiExifMgr` reported `MI_SNAPSHOT_IMAGE_NAME not found`, and
   `Session::processRequest` reported `initEntry failed: -1`.
3. The final-processing callback used a `RTPreview_Sat_Cam_5_OpMode_0x8001_…`
   name, which did not match the app's registered shot listener.
4. The app timed out. The preview thumbnail is not accepted as a saved photo.

CameraOpt also recorded one call to the explicitly unported
`reclaimMemoryForCamera`. That remains a separate compatibility gap; it is not
proven to cause the missing shot-name metadata. Wallpaper app `ClockProviderPlugin` dependency crashes are separately
recorded, including failures outside the camera capture window.

Private evidence is under
`reports/camera-completion-20260907/v9-validation/`, including
`xiaomi-cases/rear-photo/`, the before-launch package/data verification, and
`shot-metadata-diagnosis/advertised-request-keys.json`.

## Why the app skips the control

The exact factory APK is unchanged except for normal platform signing. Its
`m6.d` capability constructor uses two discovery paths:

- On HyperOS, `F5.A.u()` selects
  `CameraMetadataNative.getAllVendorKeys(CaptureRequest.Key.class)`.
- On this AOSP base, it selects
  `CameraCharacteristics.getAvailableCaptureRequestKeys()`.

The first branch detects existing HyperOS version properties. This source
candidate does not add or alter those OS identity properties. The app's
`m6.f.v2` checks the discovered names before `m6.d0.Q()` calls `m6.I.q0()` to
apply `xiaomi.snapshot.imageName`.

The actual vendor registry declares that key as `0x81990003`, type byte. The
advertised request-key lists omit it on all nine camera IDs. Logical rear ID 5
advertises 175 request keys. The standard AOSP key-list implementation filters
registered vendor keys against that advertised list, so the app's guard is
false. Its capture log contains no `applyParallelImageName` call.

This establishes a specific discovery mismatch and motivates the candidate.
Only a fresh installed capture can establish whether correcting it is enough
for Xiaomi's complete processing path.

## Guarded source candidate

[The selector contract](../config/nezha-camera-vendor-keys.json) binds
[patch 0032](../patches/evolution/0032-nezha-camera-vendor-key-discovery.patch),
[the helper](../templates/camera-vendor-keys/NezhaCameraVendorKeyCompat.java), and
[the product fragment](../device/xiaomi/nezha/camera-vendor-keys.mk).
`NEZHA_CAMERA_VENDOR_KEYS` defaults off and requires the exact Nezha product,
Camera framework inputs, Xiaomi Camera selection and platform signing. The
optional product overlay sets the new internal framework resource
`config_nezhaCameraVendorKeys`; the framework default is false.

The helper runs only for device `nezha` and the current application package
`com.android.camera`. It appends the real registered vendor-key catalog to
that client's existing advertised list, matching the factory app's original
HyperOS discovery branch. It preserves existing entries, key objects/types
and order, deduplicates by vendor ID and name, and returns an immutable list.
Other application packages keep the original AOSP list. The native metadata,
standard keys, camera permissions and original Camera APK remain unchanged.
Catalog membership does not prove a key works in every sensor/mode combination.

The patch is based on the preserved Evolution frameworks/base revision
`8140698cc12983deecdbd434220affb5f931bfc6`. A September 8 upstream branch check
observed `b557afa98c14f3f33f70be3bbeb8aaaeb95a8882`; that newer revision is not
adopted. Exact preimages remain bound to the installed v9 source cohort.

All 4,873 offline tests passed in 189.660 seconds, including seven new
product-selection and patch-integrity checks. `make test-current` passed 939
tests in 27.329 seconds. Applying the patch to an isolated host copy of all
four exact inputs reproduced every recorded postimage. The actual authored Java helper
also compiles with `-Xlint:all -Werror` against minimal host API fixtures and
passes 35 behavior assertions covering scope, disabled/null/empty catalogs,
preserved types/order, duplicate provider/name pairs, immutability and error
propagation. These are host checks, not an Android build or hardware result.

A future build must verify the compiled resource selection and actual helper
and call site in framework DEX, preserve the original APK payload/signature
checks, and repeat the real Xiaomi shutter test before advancing to front,
50/200 MP, RAW/Ultra RAW and video. The v9 Bokeh Ultra HDR and telephoto RAW
regression captures independently decoded successfully; they do not establish
Xiaomi Camera acceptance.

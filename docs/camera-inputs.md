# Selected Camera build inputs

The [explicit selection](../vendor/xiaomi/nezha/camera-selection.json) prepares
**nine system-ext files** for a separate Camera dependency build check: one
JNI library, four DEX JARs and four permission XMLs. Seven files are unchanged
captures; two XML registrations are explicitly derived. It is a bounded set of
captured dependencies, not a complete Camera port or a proven minimum for every
feature. The Camera APK and full MIUI framework are not included. The verified
bundle is now installed in the existing builder for the separate module check
recorded in [build progress](build-progress.md). No Camera APK was installed
and no phone was modified.

The package remains the user-provided modified Xiaomi.eu input with SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Its origin is unverified and its retained AVB metadata fails against the supplied
image set. Generating this profile neither repairs those failures nor approves
flashing. An official baseline needs its own verified hashes and selection;
this profile cannot silently be reused with a different package.

## Exact selection

Paths stay under `/system_ext/`. CameraX has a new, minimal permission filename;
the other installation paths retain their captured names. The selection JSON
records the complete SHA256 and size for every output and each derivation source.

| Path after `/system_ext/` | Bytes | Generated Soong type |
| --- | ---: | --- |
| `lib64/libcamera_algoup_jni.xiaomi.so` | 85,064 | `cc_prebuilt_library_shared`, ARM64 only |
| `framework/camerax-vendor-extensions.jar` | 72,829 | `dex_import` |
| `framework/com.xiaomi.hardware.camera.companion-V1.jar` | 43,102 | `dex_import` |
| `framework/miui-cameraopt.jar` | 326,413 | `dex_import` |
| `framework/vendor.xiaomi.hardware.postprocservice-V1-java.jar` | 13,298 | `dex_import` |
| `etc/permissions/camerax-vendor-extensions.xml` | 180 | `prebuilt_etc_xml`, derived |
| `etc/permissions/com.xiaomi.hardware.camera.companion.xml` | 335 | `prebuilt_etc_xml` |
| `etc/permissions/miui-cameraopt.xml` | 797 | `prebuilt_etc_xml` |
| `etc/permissions/vendor.xiaomi.hardware.postprocservice-V1-java-permission.xml` | 218 | `prebuilt_etc_xml`, derived |

The extra files total **542,236 bytes**. The five binary hashes match the earlier
[camera dependency record](../research/camera-dependencies.json). The copied
companion/cameraopt XML hashes and both XML derivation sources match their earlier
captures; the original three XMLs from camera-v1 also matched the live collection.
Each installed XML contains only one `<library>` element, with no permission
grants, unrelated registrations or app allowlists.

The vendor and ODM native dependencies, camera manifests, tuning and other files
remain inside their unchanged prebuilt images. This profile does not duplicate
individual vendor/ODM libraries into another partition. Matching bytes preserves
their provenance; it does not demonstrate compatible linker namespaces,
framework symbols, camera tuning, calibration or service behavior on Evolution X.

## JNI dependencies and module mapping

The copied JNI library is AArch64 ELF64. Its `DT_NEEDED` entries were independently
checked in the previous analysis with pinned extract-utils and NDK readelf;
the new capture has the same file hash. The selection explicitly maps all 20
entries to Soong module names:

| ELF `DT_NEEDED` | Selected `shared_libs` module |
| --- | --- |
| `android.hidl.token@1.0-utils.so` | [android.hidl.token@1.0-utils](https://android.googlesource.com/platform/system/libhidl/+/d063c3a2bf981d8dab2ca60ea471f940d71167a6/transport/token/1.0/utils/Android.bp) |
| `libandroid.so` | [libandroid](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/native/android/Android.bp#L44) |
| `libandroid_runtime.so` | [libandroid_runtime](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/core/jni/Android.bp#L512) |
| `libbase.so` | [libbase](https://android.googlesource.com/platform/system/libbase/+/bdf0f4db82fae78492c92a55d473aacc4e963e79/Android.bp) |
| `libbinder.so` | [libbinder](https://github.com/Evolution-X/frameworks_native/blob/d78897741ad798fe9c183795026cfd87cd03a76c/libs/binder/Android.bp#L663) |
| `libc++.so` | [libc++](https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+/9916fb51ccb914d62d35ad9a7b9b21d2ef046928/Android.bp) |
| `libc.so` | [libc](https://github.com/Evolution-X/bionic/blob/f30d4f5c85d44c44af76e317d1c9d5e02b7b7936/libc/Android.bp#L1523) |
| `libcamera_client.so` | [libcamera_client](https://github.com/Evolution-X/frameworks_av/blob/dfe1a704f074bbbc3f60b740a9e5ec6b786228f3/camera/Android.bp#L76) |
| `libcamera_metadata.so` | [libcamera_metadata](https://github.com/Evolution-X/system_media/blob/f49b447fd0f00152ecffbb9446403def0708a592/camera/Android.bp#L12) |
| `libcutils.so` | [libcutils](https://github.com/Evolution-X/system_core/blob/241488ea392c01079941d86ddc458b8a0c9ae6e1/libcutils/Android.bp#L143) |
| `libdl.so` | [libdl](https://github.com/Evolution-X/bionic/blob/f30d4f5c85d44c44af76e317d1c9d5e02b7b7936/libdl/Android.bp#L55) |
| `libgui.so` | [libgui](https://github.com/Evolution-X/frameworks_native/blob/d78897741ad798fe9c183795026cfd87cd03a76c/libs/gui/Android.bp#L573) |
| `liblog.so` | [liblog](https://github.com/LineageOS/android_system_logging/blob/e63321648d4f2cb7c437bd615366e8f8765ad2bc/liblog/Android.bp#L152) |
| `libm.so` | [libm](https://github.com/Evolution-X/bionic/blob/f30d4f5c85d44c44af76e317d1c9d5e02b7b7936/libm/Android.bp#L478) |
| `libmedia_jni_utils.so` | [libmedia_jni_utils](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/core/jni/Android.bp#L588) |
| `libnativehelper.so` | [libnativehelper](https://android.googlesource.com/platform/libnativehelper/+/2d584ec2da2c5271ed1576593c6590d652806f0d/Android.bp) |
| `libnativewindow.so` | [libnativewindow](https://github.com/Evolution-X/frameworks_native/blob/d78897741ad798fe9c183795026cfd87cd03a76c/libs/nativewindow/Android.bp#L72) |
| `libui.so` | [libui](https://github.com/Evolution-X/frameworks_native/blob/d78897741ad798fe9c183795026cfd87cd03a76c/libs/ui/Android.bp#L105) |
| `libutils.so` | [libutils](https://github.com/Evolution-X/system_core/blob/241488ea392c01079941d86ddc458b8a0c9ae6e1/libutils/Android.bp#L182) |
| `libvndksupport.so` | [libvndksupport](https://github.com/Evolution-X/system_core/blob/241488ea392c01079941d86ddc458b8a0c9ae6e1/libvndksupport/Android.bp#L5) |

All 20 names have matching declarations at the platform's pinned revisions;
the table links each definition. `libmedia_jni_utils` is declared in
`frameworks/base/core/jni/Android.bp`, not the older media-JNI location. This
establishes source definitions, not compatible variants, visibility, exported
symbols or a complete transitive dependency graph. The dependency list remains
unchanged for the real Soong check.

The JNI module preserves its original filename and partition, restricts its
source to `target.android_arm64`, keeps stripping off to preserve the captured
bytes, and requests `check_elf_files: true`. It does not override
`system_shared_libs` or set a broken-prebuilt allowance. A generated property is
not evidence that the build actually ran its ELF validator. The later
[completed Camera dependency build](build-progress.md) records that actual
action, including its 20 shared-library inputs and 16 KiB alignment check.
[Pinned Soong linker rules](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/cc/linker.go)

## Java registration and deliberately excluded inputs

All four JARs are DEX archives, not ordinary `.class` JARs. Their original stems
and system-ext installation paths are preserved. The private Soong module names
do not establish their runtime shared-library names or the Camera APK's
class-loader context: the pinned `dex_import` does not expose `provides_uses_lib`.
The selection does not change signature or uses-library settings. The original
v4 product inherited
`RELAX_USES_LIBRARY_CHECK=true` from `vendor/extras/bcr/bcr.mk`. The generated
dexpreopt configuration confirmed that value. The later v5 device correction
was installed and its regenerated configuration verifies
`RelaxUsesLibraryCheck=false` while dexpreopt remains enabled. The four JARs
now have verified ODEX and VDEX outputs. These JAR results are not proof of
strict APK validation and do not establish the Camera APK's context or
signature compatibility; it remains outside the bundle.
Signature and preprocessed-APK checks have not been exercised by these JAR
imports. [Pinned DEX importer](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/java/java.go)

The separate [DEX import patch](dex-import-uses-library.md) adds a strict
runtime provider with exact names and ordered required dependencies. It is
tested in isolated fixtures but is not yet installed in the Linux checkout;
the existing module names and bundle remain unchanged.

Companion and cameraopt XMLs remain byte-for-byte copies and point to the selected
JARs under `/system_ext/framework/`. **Two derived XML registrations** address
the previously identified path/registration gaps in the candidate build inputs.
They do not establish that Android loaded these libraries at runtime.

The pinned framework reads XMLs from `/system_ext/etc/permissions` and registers
a library by its declared name only if its referenced file exists. That supports
these separate minimal XMLs and the explicit path correction; it does not prove
installation or successful class loading on a device. [Pinned SystemConfig reader](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/services/core/java/com/android/server/SystemConfig.java#L1095)

The captured postproc XML still points to
`/system/framework/vendor.xiaomi.hardware.postprocservice-V1-java.jar`, while the
captured JAR is under `/system_ext/framework/`. No matching alias was observed.
The v2 recipe keeps the original library name and output XML filename, changes
only the registration's file attribute to the explicitly selected
`/system_ext/framework/vendor.xiaomi.hardware.postprocservice-V1-java.jar`, and
serializes a minimal XML document. Raw captures and the historical
[VINTF path evidence](vintf-contract.md#unresolved-postproc-java-path) are unchanged;
no alias or symlink is created.

The second recipe selects the exact CameraX entry from `platform-miui.xml`:
name `camerax-vendor-extensions.jar`, file
`/system_ext/framework/camerax-vendor-extensions.jar`. It emits only that entry
as `camerax-vendor-extensions.xml`. The other 21 library mappings and the
app-data-isolation exception are excluded, and the whole `platform-miui.xml`
is never installed by this profile. The `.jar` suffix in the registered library
name is intentional: it is the observed stock name, not an inferred Soong name.

| Derived XML | Source SHA256 | Output SHA256 |
| --- | --- | --- |
| CameraX, selected from 2,597-byte `platform-miui.xml` | `96da583654521934b27e6a4ce4eba994fa709a20864cd5117338bf1537a488d6` | `72b03ab4cb59c5de507171723f29a8fd6483b1f9104d32d02008eac82fe7eb53` |
| Postproc, corrected from its 188-byte permission XML | `3a22f4bfe89ad6388a67bf7d2f985ae285b602270f7b95cc116b9d46e8236bd7` | `52de3422c1c7bf138883f82951e3fac202277a6c5b562ec2921d289a2c2fbabd` |

The tracked selection records `library-registration-v1` recipes, not proprietary
XML bytes. The generator rehashes each regular capture and requires one direct
stock `<library>` entry with exactly the declared `name` and `file` attributes.
Extra attributes, child content, ambiguous or namespaced selected entries, DTDs
and entity declarations are rejected; unrelated source entries are not emitted.
The target must be an explicitly selected system-ext DEX JAR with the same filename.
Recipe output hashes are checked before staging and read back after writing.

Each derived receipt entry records the original runtime path, image hash, inode,
capture receipt hash and source-file hash separately from the output path/hash.
It also records both file attributes and the recipe SHA256, calculated over its
selection JSON object with sorted keys and compact `,`/`:` separators in UTF-8.
A derived output is not labeled as an original image inode. These local input
hash checks do not authenticate the firmware or prove Android class-loader,
uses-library, signature, symbol or service compatibility.

The stock Camera APK, product-wide privileged permission allowlist, stock window
extension JARs, init scripts and other MIUI framework files are also excluded.
The APK's install-time optional declarations do not prove which dependencies a
particular capture mode needs. Signature, class-loader, policy and feature
testing remain separate work described in the [Camera baseline](camera-baseline.md).
The later [APK integration review](camera-apk-integration.md) records actual
signature, alignment, preprocessing and manifest-name checks, including the
inherited relaxed setting and the exact class-loader provider gap. It does
not import or modify the APK.

## Generated private bundle and reproduction

The original guarded EROFS capture used the already inventoried `system_ext_a` image with
SHA256 `b2937ccb0dd38290af629c19064d1bacf4d9167d5074fb86e972f4d30b4c54ef`.
It copied only the eight camera-v1 regular inodes, with canonical path checks,
input identity checks, file hash readback, no mount and no firmware execution.
Its private receipt is:

```text
artifacts/firmware-analysis/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69/erofs/system_ext-camera-inputs-capture-v1/receipt.json
SHA256 9835144796deae068911d33d4073c175a8bbfd489cb02aa8b551bf7d01f7b36e
```

The original eight-file vendor tree remains under
`artifacts/vendor-inputs/nezha-xiaomieu-b29afecc-camera-v1/`. Its
`vendor-inputs.json` has SHA256
`d6ca3c1851b370032f7bf9dc7ba396c9e9e526183bdc5e6c6e3b9825c6b583c5`.
That receipt binds the source record, package, images, original selection and
captures to installed input paths and generated makefile/Blueprint hashes. Its
selection SHA256 is `7d250613a4ac98002939ece21a4d867af0bdfdc779566fcd3038665c71e33555`
(tracked at commit `a245c17570fa8d15b8585f2ca107dd7049c18463`). Neither this tree
nor the default `nezha-xiaomieu-b29afecc-base-v1` bundle is modified for v2.

The CameraX derivation additionally uses the existing
`erofs/system_ext-contract-capture/receipt.json`, SHA256
`93289dcbfbf6178e7d58477bd9afc68de1f868cf8ce9df532e69e90c3c2986b4`, under the
same package analysis directory. It binds the original `platform-miui.xml`
capture to the same `system_ext_a` image. No new firmware or phone capture is
needed to derive these registrations.

The verified new tree is
`artifacts/vendor-inputs/nezha-xiaomieu-b29afecc-camera-v2/`. Its
`vendor-inputs.json` SHA256 is
`0a6a70317eed9c1df1e30112eed10361ba49d5e8afa89fbd6b1feb507a8d09bc`;
the current selection SHA256 is
`be4f441d2f4424ce2b1add72df04565d0736cc64542aec81c91df9f589dbb5a7`.
The nine extras total 542,236 bytes, with 5,621,892,636 total image/extra bytes.
Staging verified both derivation inputs, their generated outputs and every
copied input. An independent readback then rehashed all 16 v2 outputs and all
22 outputs in base-v1/camera-v1; every hash matched its receipt and the older
receipt hashes were unchanged. Evidence is retained in
`reports/camera-inputs-stage-v2.json` and `reports/camera-inputs-integrity-v2.json`.

To reproduce from these existing verified captures, choose a **new** output:

```sh
camera_analysis=artifacts/firmware-analysis/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69
python3 scripts/vendor_inputs.py stage \
  --analysis "$camera_analysis" \
  --source-record research/firmware-layout.json \
  --expected-package-sha256 b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69 \
  --selection vendor/xiaomi/nezha/camera-selection.json \
  --capture-receipt "$camera_analysis/erofs/system_ext-camera-inputs-capture-v1/receipt.json" \
  --capture-receipt "$camera_analysis/erofs/system_ext-contract-capture/receipt.json" \
  --output artifacts/vendor-inputs/nezha-camera-review-NEW
```

Use `plan` with the same input arguments and without `--output` for metadata-only
inspection. A plan does not rehash the blobs or establish their buildability.
The capture workflow and its canonical image-path rules are documented in the
[EROFS guide](vintf-contract.md#guarded-read-only-reproduction).

The five binary-module targets submitted for the Soong check are:

```text
nezha_system_ext_lib64_libcamera_algoup_jni_xiaomi_so
nezha_system_ext_framework_camerax_vendor_extensions_jar
nezha_system_ext_framework_com_xiaomi_hardware_camera_companion_V1_jar
nezha_system_ext_framework_miui_cameraopt_jar
nezha_system_ext_framework_vendor_xiaomi_hardware_postprocservice_V1_java_jar
```

The generated `nezha-vendor.mk` lists all nine modules, including four XML
imports. The new CameraX XML module is
`nezha_system_ext_etc_permissions_camerax_vendor_extensions_xml`; the corrected
postproc keeps module
`nezha_system_ext_etc_permissions_vendor_xiaomi_hardware_postprocservice_V1_java_permission_xml`.
The five binary target names are unchanged. Generation and offline tests
establish input integrity and the intended build definitions. The later
installation and actual build result are tracked separately in
[build progress](build-progress.md). Enforcing policy, complete VINTF
compatibility, APK integration and separately authorized hardware tests are
still needed before claiming any stock Camera or Leica feature works on
Evolution X.

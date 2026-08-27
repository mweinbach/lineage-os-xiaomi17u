# Selected Camera build inputs

The [explicit selection](../vendor/xiaomi/nezha/camera-selection.json) prepares
**eight system-ext files** for a separate Camera dependency build check: one
JNI library, four DEX JARs and three permission XMLs. It is a bounded set of
captured dependencies, not a complete Camera port or a proven minimum for every
feature. The Camera APK and full MIUI framework are not included. No phone,
Downloads folder, container or device tree was accessed or changed by this slice.

The package remains the user-provided modified Xiaomi.eu input with SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Its origin is unverified and its retained AVB metadata fails against the supplied
image set. Generating this profile neither repairs those failures nor approves
flashing. An official baseline needs its own verified hashes and selection;
this profile cannot silently be reused with a different package.

## Exact selection

All paths below are original Android runtime paths under `/system_ext/`.
The selection JSON records the complete SHA256 and size for every file.

| Path after `/system_ext/` | Bytes | Generated Soong type |
| --- | ---: | --- |
| `lib64/libcamera_algoup_jni.xiaomi.so` | 85,064 | `cc_prebuilt_library_shared`, ARM64 only |
| `framework/camerax-vendor-extensions.jar` | 72,829 | `dex_import` |
| `framework/com.xiaomi.hardware.camera.companion-V1.jar` | 43,102 | `dex_import` |
| `framework/miui-cameraopt.jar` | 326,413 | `dex_import` |
| `framework/vendor.xiaomi.hardware.postprocservice-V1-java.jar` | 13,298 | `dex_import` |
| `etc/permissions/com.xiaomi.hardware.camera.companion.xml` | 335 | `prebuilt_etc_xml` |
| `etc/permissions/miui-cameraopt.xml` | 797 | `prebuilt_etc_xml` |
| `etc/permissions/vendor.xiaomi.hardware.postprocservice-V1-java-permission.xml` | 188 | `prebuilt_etc_xml` |

The extra files total **542,026 bytes**. The five binary hashes match the earlier
[camera dependency record](../research/camera-dependencies.json). The three XML
hashes also match the earlier live collection at the same paths. Each selected
XML contains only one `<library>` element, with no permission grants, unrelated
registrations or app allowlists.

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
not evidence that the build actually ran its ELF validator. [Pinned Soong linker rules](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/cc/linker.go)

## Java registration and deliberately excluded inputs

All four JARs are DEX archives, not ordinary `.class` JARs. Their original stems
and system-ext installation paths are preserved. The private Soong module names
do not establish their runtime shared-library names or the Camera APK's
class-loader context: the pinned `dex_import` does not expose `provides_uses_lib`.
No uses-library, signature or preprocessed-APK check was disabled. [Pinned DEX importer](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/java/java.go)

The three permission XMLs are copied byte-for-byte. Companion and cameraopt
point to the selected JARs under `/system_ext/framework/`. The postproc XML still
points to `/system/framework/vendor.xiaomi.hardware.postprocservice-V1-java.jar`,
while the captured JAR is under `/system_ext/framework/`. No matching alias was
observed. This discrepancy is preserved and must be resolved explicitly; the
generator does not rewrite the XML or fabricate a symlink. See the
[VINTF path evidence](vintf-contract.md#unresolved-postproc-java-path).

`platform-miui.xml` is excluded. Its camera-related entry registers
`camerax-vendor-extensions.jar` at `/system_ext/framework/camerax-vendor-extensions.jar`,
but the same file also contains 21 other library mappings and an app-data-isolation
exception. Copying it wholesale would introduce unrelated MIUI policy and
references to files not selected here. **CameraX shared-library registration
remains pending**; a future minimal derived XML must record its source and
transformation rather than masquerade as an unchanged stock file.

The stock Camera APK, product-wide privileged permission allowlist, stock window
extension JARs, init scripts and other MIUI framework files are also excluded.
The APK's install-time optional declarations do not prove which dependencies a
particular capture mode needs. Signature, class-loader, policy and feature
testing remain separate work described in the [Camera baseline](camera-baseline.md).

## Generated private bundle and reproduction

The guarded EROFS capture used the already inventoried `system_ext_a` image with
SHA256 `b2937ccb0dd38290af629c19064d1bacf4d9167d5074fb86e972f4d30b4c54ef`.
It copied only the eight selected regular inodes, with canonical path checks,
input identity checks, file hash readback, no mount and no firmware execution.
Its private receipt is:

```text
artifacts/firmware-analysis/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69/erofs/system_ext-camera-inputs-capture-v1/receipt.json
SHA256 9835144796deae068911d33d4073c175a8bbfd489cb02aa8b551bf7d01f7b36e
```

The new vendor tree is under
`artifacts/vendor-inputs/nezha-xiaomieu-b29afecc-camera-v1/`. Its
`vendor-inputs.json` has SHA256
`d6ca3c1851b370032f7bf9dc7ba396c9e9e526183bdc5e6c6e3b9825c6b583c5`.
That receipt binds the source record, package, images, selection and captures to
all installed input paths and generated makefile/Blueprint hashes. The selection
SHA256 is `7d250613a4ac98002939ece21a4d867af0bdfdc779566fcd3038665c71e33555`.
The default `nezha-xiaomieu-b29afecc-base-v1` bundle was not modified.

To reproduce from these existing verified captures, choose a **new** output:

```sh
camera_analysis=artifacts/firmware-analysis/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69
python3 scripts/vendor_inputs.py stage \
  --analysis "$camera_analysis" \
  --source-record research/firmware-layout.json \
  --expected-package-sha256 b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69 \
  --selection vendor/xiaomi/nezha/camera-selection.json \
  --capture-receipt "$camera_analysis/erofs/system_ext-camera-inputs-capture-v1/receipt.json" \
  --output artifacts/vendor-inputs/nezha-camera-review-NEW
```

Use `plan` with the same input arguments and without `--output` for metadata-only
inspection. A plan does not rehash the blobs or establish their buildability.
The capture workflow and its canonical image-path rules are documented in the
[EROFS guide](vintf-contract.md#guarded-read-only-reproduction).

The five binary-module targets for the next Soong check are:

```text
nezha_system_ext_lib64_libcamera_algoup_jni_xiaomi_so
nezha_system_ext_framework_camerax_vendor_extensions_jar
nezha_system_ext_framework_com_xiaomi_hardware_camera_companion_V1_jar
nezha_system_ext_framework_miui_cameraopt_jar
nezha_system_ext_framework_vendor_xiaomi_hardware_postprocservice_V1_java_jar
```

The generated `nezha-vendor.mk` lists all eight modules, including the three XML
imports. No transfer to the Linux checkout or activation in a device tree was
performed by this slice. Generation and offline tests establish input integrity
and the intended build definitions; a real Soong result, enforcing policy,
VINTF compatibility and separately authorized hardware tests are still needed
before claiming any stock Camera or Leica feature works on Evolution X.

# Captured Xiaomi Camera baseline

Analyzed offline on **2026-08-27** from the user's China-edition Nezha running
**xiaomi.eu**, reported build `OS3.0.309.0.WPACNXM`. This is the current modified
installation, **not an authenticated factory-stock APK or a working Evolution X
camera port**. The APK was neither installed nor executed. No phone commands
were used for this analysis. See [device-baseline.md](device-baseline.md) for
the device readback and [native-features.md](native-features.md) for device tests.

## Identified artifact

| Field | Observed value |
| --- | --- |
| Package | `com.android.camera` |
| Version name / code | `6.3.007010.0` / `630070100` |
| Original device path | `/product/priv-app/MiuiCamera/MiuiCamera.apk` |
| Bytes | `170279563` |
| SHA-256 | `cadf2c07cb6fd25c06f7fe6f37dc227df204bed3a873b3025aff93d53d72da79` |
| Minimum / target / compile SDK | `29` / `35` / `35` |
| APK native code | 40 `.so` files, all under `lib/arm64-v8a/`; ELF headers identify AArch64. |
| Application flags | `extractNativeLibs=false`, `allowBackup=false`, `largeHeap=true` |

The bytes and SHA-256 match the recorded collection manifest. `apkanalyzer apk
summary` and `apkanalyzer manifest print` both succeeded. Minimum SDK 29 is an
APK declaration, not evidence that the app works on arbitrary Android 10+
systems or that Xiaomi framework dependencies are unnecessary.

## Explicit APK dependency declarations

The manifest declares three Java shared libraries: `miui-cameraopt`,
`androidx.window.extensions`, and `androidx.window.sidecar`. It also declares
the following **13 unique native library names**, none bundled in the APK:

| Group for investigation | Manifest names |
| --- | --- |
| Compute/acceleration | `libSNPE.so`, `libOpenCL.so`, `libcdsprpc.so`, `libmialgo_ai_vision.so` |
| Camera JNI interfaces | `libcamera_ispinterface_jni.xiaomi.so`, `libcamera_algoup_jni.xiaomi.so`, `libcamera_imagecodec_jni.xiaomi.so` |
| Image/video algorithms | `libxmi_slow_motion_mein.so`, `libmialgo_utils.so`, `libmiocr.so` |
| Additional platform adapters | `libneuron_adapter_mgvi.so`, `libneuron_adapter.so`, `libneuronusdk_adapter.mtk.so` |

**Every Java and native shared-library declaration has `required=false`.**
Some native declarations are duplicated. These are proven declarations, not
proof that every named library is needed on SM8850 or used by every mode. The
MediaTek-named adapter entries must not be mistaken for this phone's SoC or
automatically added to its vendor tree. Optional at package-install time does
not establish optionality for a particular camera feature.

The captured `/system_ext/etc/permissions/miui-cameraopt.xml` maps the declared
`miui-cameraopt` name to `/system_ext/framework/miui-cameraopt.jar`. The APK
requests 70 unique permission names. Its current
`/product/etc/permissions/privapp-permissions-product.xml` contains a
`com.android.camera` block with 13 entries:

```text
android.permission.WRITE_MEDIA_STORAGE
android.permission.WRITE_SECURE_SETTINGS
android.permission.MANAGE_USB
android.permission.INTERACT_ACROSS_USERS
mediatek.permission.ACCESS_APU_SYS
android.permission.DUMP
android.permission.LOG_COMPAT_CHANGE
android.permission.READ_COMPAT_CHANGE_CONFIG
android.permission.START_ACTIVITIES_FROM_BACKGROUND
android.permission.SYSTEM_CAMERA
android.permission.TURN_SCREEN_ON
android.permission.SUBSCRIBE_TO_KEYGUARD_LOCKED_STATE
android.permission.READ_PHONE_STATE
```

These are static allowlist entries, not a dump of effective granted permissions
and not an approved Evolution X permission policy. The manifest also requests
Xiaomi Gallery, PowerKeeper, Security Center, continuity, cloud and scanner
permissions. Their names establish integration leads; they do not prove each
corresponding app is mandatory. Audit permissions and signatures individually
instead of copying the whole allowlist.

## Native dependencies proven by ELF linkage

All 40 bundled libraries' `DT_NEEDED` entries were parsed and independently
cross-checked with the installed Android NDK's `llvm-readelf`. The following
links identify concrete dependencies **outside this APK**:

| Bundled library | External linked libraries of particular interest |
| --- | --- |
| `libcamera_video_mein_algo_jni.so` | `libxmi_slow_motion_mein.so`, `libmialgo_utils.so` |
| `libmiocr_wrapper.so` | `libmiocr.so` |
| `libmialgo_saliency.so` | `libmialgo_ai_vision.so`, `libcdsprpc.so`, `libOpenCL.so` |
| `libDocumentProcess.so` | `libOpenCL.so` |

Other external names include Android graphics/media/runtime libraries,
`libnativewindow.so` and `libstdc++.so`. A `DT_NEEDED` entry is a linker dependency
when that bundled library is loaded; it does not prove when a camera mode loads
it or that the target ROM provides compatible symbols and namespace access.
This pass did not resolve the external files or their transitive dependencies.

The bundled inventory also includes camera utilities (`libCameraToolJNI.so`,
`libCameraUtils.so`), filters/rendering (`libMiFilterSDK.so`,
`librender_engine.so`, `libwatermark_effect.so`), image formats
(`libcameraheif.so`, `libheif_jni.so`, `libavif_android.so`), media processing
(`libMiShortVideoSDK.so`, `libijkffmpeg.so`, `libmiffmpeg.so`), and continuity
(`libmicontinuity_sdk.so`). These group names describe filenames, not validated
feature behavior. The full 40-file inventory and per-library hashes remain in
the private report.

## Camera services declared by the captured system

These entries come from the captured VINTF **device manifests**, not an
observation that each service is running or called by this APK. A dash means
the XML omits an explicit version; it does not mean an absent service.

| HAL name | Format / explicit version | Interface and instance |
| --- | --- | --- |
| `android.hardware.camera.provider` | AIDL / `3` | `ICameraProvider/vendor_qti/0` |
| `android.hardware.camera.provider` | AIDL / — | `ICameraProvider/external/0` |
| `vendor.qti.hardware.camera.offlinecamera` | AIDL / `2` | `IOfflineCameraService/default` |
| `vendor.xiaomi.hardware.postprocservice` | AIDL / — | `IPostProcService/default` |
| `vendor.xiaomi.hardware.quickcamera` | AIDL / `1` | `IQuickCameraService/default` |
| `vendor.xiaomi.hardware.camera.mivimessage` | AIDL / — | `IService/default` |
| `vendor.xiaomi.hardware.camera.synthetic` | AIDL / — | `IVirtualCameraRegistrar/default` |
| `vendor.xiaomi.hardware.aon` | AIDL / — | `IAlwaysOn/miaonservicehal` |
| `vendor.xiaomi.sensor.camera` | AIDL / — | `IMiCam/default` |
| `vendor.xiaomi.hardware.seccam` | AIDL / — | `IMiSecCam/default` |

The first eight entries are in `/vendor/etc/vintf/manifest/`; the last two are
in `/odm/etc/vintf/manifest/`. Notably, the file named
`vendor.xiaomi.hardware.dynamiccameraserver.xml` actually declares
`vendor.xiaomi.hardware.camera.synthetic`. Keep names from XML content, not
inferred from filenames. The system camera-service manifest separately declares
AIDL version 3 and HIDL `@2.2::ICameraService/default`.

The framework compatibility matrix additionally mentions legacy
`vendor.xiaomi.hardware.campostproc` HIDL 1.0 and other camera interfaces.
A matrix entry is not proof of an installed provider. Do not transplant the
older Peridot camera example's HIDL postprocessing dependencies without checking
this captured AIDL stack.

Additional captured permission XMLs expose these shared-library mappings:

| XML under `/system_ext/etc/permissions/` unless noted | Declared name → file |
| --- | --- |
| `com.xiaomi.hardware.camera.companion.xml` | `com.xiaomi.hardware.camera.companion-V1` → `/system_ext/framework/com.xiaomi.hardware.camera.companion-V1.jar` |
| `vendor.xiaomi.hardware.postprocservice-V1-java-permission.xml` | `vendor.xiaomi.hardware.postprocservice-V1-java` → `/system/framework/vendor.xiaomi.hardware.postprocservice-V1-java.jar` |
| `platform-miui.xml` | `camerax-vendor-extensions.jar` → `/system_ext/framework/camerax-vendor-extensions.jar` |
| `/vendor/etc/permissions/camera_extensions.xml` | `androidx.camera.extensions.impl` → `/vendor/framework/androidx.camera.extensions.impl.jar` |

These four mappings are system-side evidence. They are not direct
`uses-library` declarations in this APK, and the mapped JAR bytes were not
inspected in this pass. The unusual `/system/framework/` postprocessing path is
transcribed as captured rather than normalized to `/system_ext/`.

## Local evidence and limits

The original private collection is `evidence/xiaomi-eu-20260827T1530Z/`;
`manifest.json` records acquisition results and artifact hashes. Collection
status is partial because some unrelated reads were denied; both camera
package-path lookup and APK pull succeeded. This document does not reproduce
serials, logs, account data, APK contents, or proprietary binaries.

Ignored `reports/camera-static-20260827T153254Z/` contains `apk-summary.txt`,
decoded `manifest.xml`, `manifest-summary.json`, `zip-inventory.json`,
`camera-vintf.json`, `camera-permission-refs.json`,
`elf-dynamic-dependencies.json`, and independent `readelf/` outputs. Extracted
ELF inputs also remain ignored. No full decompilation was needed.

This establishes a reproducible initial dependency inventory. It does not yet
establish factory provenance, the complete library closure, linkage into every
camera feature, SELinux policy, signing compatibility, working Leica processing
or lens/accessory support. The immediate missing evidence is the matching
external libraries/JARs and their interfaces from the same China firmware,
followed by controlled device tests after a viable ROM exists.

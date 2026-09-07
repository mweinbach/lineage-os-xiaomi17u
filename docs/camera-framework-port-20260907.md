# Full HyperOS camera-framework port and its runtime result (2026-09-07)

You asked to bring the whole HyperOS camera framework over, not a subset. This
records that port: what was brought, how it was integrated, that it builds,
signs, flashes and boots cleanly, and the measured outcome. It is delivery set
v7 (`nezha.c6ad60080698a987390afc40`), flashed to slot A, enforcing.

**Later correction:** the [native hook investigation](camera-native-hook-20260907.md)
recovered the factory cameraserver call path. The missing integration is native
`frameworks/av` code. The earlier Java-framework and CameraExtensionsProxy
interpretations were not established runtime findings and are superseded by
that binary evidence. The measured v7 capture failure remains unchanged.

## What was ported

The complete transitive set of HyperOS camera components our build was missing,
computed as the shared-library dependency closure of every absent camera
library and resolved against what the device already ships:

- **24 system_ext native libraries**, including `libcameraimpl.so` (the client
  that calls `CameraImpl::updateSessionParams` and defines
  `com.xiaomi.sessionparams.MiStreamUsecase`, `clientName`, `activityName`,
  `cameraxConnection`), `libcameraopt.so` / `libcameraopt_jni.so` (the perf
  boost service the Xiaomi app's `CameraPerfInterface` needs), `libcameramind.so`
  (AI scene), `libcameradngimpl.so`, `libmicampostproc_client.so`, `libmivideo.so`,
  and the Xiaomi media/codec/telemetry and HAL-interface libraries they depend on
  (`libmqsas`, `libmicodec`, `libmediaimpl`, `libskuparser_cpp/ffi`,
  `vendor.xiaomi.hardware.campostproc@1.0`, `videoservice-V7-ndk`,
  `mediaeventgatherservice-V1-ndk`, `com.android.ozoaudio.notify-V1-cpp`).
- **The `CameraMind` app** (`system_ext/app`).
- **The camera configs** `cameraopt*.json`, `camerascene.json`,
  `cameracustomize.json`, `camera_perfetto.cfg`, and the forced-dark entries.
- **`init.miui.cameraopt.rc`**, which sets up the camera cgroups and memcg.
- **The factory camera system properties** `vendor.camera.support.mivi=true`,
  `vendor.camera.aux.packagelist`, `aux.packagelistext`,
  `persist.vendor.camera.privapp.list`, `hypercamera.disable_app_default_config`.

The framework jars this chain needs (`camerax-vendor-extensions.jar`,
`com.xiaomi.hardware.camera.companion-V1.jar`, `miui-cameraopt.jar`) were
already present in our build; only the native libraries were missing.

## How it was integrated

The proprietary blobs live in the ignored `vendor/xiaomi/nezha-camera-framework`
bundle as `cc_prebuilt_library_shared`, `prebuilt_etc` and `android_app_import`
Soong modules (35 modules). A tracked, guarded fragment
`device/xiaomi/nezha/camera-framework.mk` (selector `NEZHA_CAMERA_FRAMEWORK`,
off by default) inherits the bundle's package list and sets the camera
properties. A seventh guest source transaction added the fragment, its device.mk
include and the product selector (source identity
`nezha.c6ad60080698a987390afc40`, 605 rows). The build admitted the grown
system_ext (792,080,384 bytes), signed with the host AVB profile, bundled, and
flashed slot A with eight acknowledged writes, no wipe, no slot change.

## Result: the rear camera still does not capture

The build boots enforcing with all 24 libraries in `/system_ext/lib64`, the
properties set from build.prop, the cgroups created, nine cameras enumerated,
and no regression. But opening the rear camera fails exactly as before:

```
InitializeOverrideSession() get MiStreamUsecaseName tag failed
chifeature2graphmanager.cpp:342 Failed to create VirtualSuperGraphDesc: 4
chxmulticamerabase.cpp:2596 Failed to initialize Multicamera Usecase: 8
MiCamService configureStreams status=-19  ->  Camera 0: Function not implemented (-38)
```

The reason the port does not help: `libcameraimpl.so`, the component that would
inject `MiStreamUsecase`, is present on disk but **loaded by no process**. The
factory native cameraserver loader is absent from this AOSP-derived build.
The Xiaomi camera app still configures through standard
`android.hardware.camera2` and reaches the same HAL failure.

The original assessment attributed this to `framework.jar` / `services.jar`
without establishing a call site. Later disassembly instead found the native
loader and both required metadata hooks: `updateSessionParams` writes the
registered client name; `executeSceneIdentify` writes `MiStreamUsecase` and
activity name immediately before HAL configuration. Both use a camera-ID key.
See the native investigation for exact addresses and the guarded source port.

## What holds

- Enumeration fix (`va_aosp`) and the full camera-framework blob port are both
  flashed and booting, enforcing, with no regression.
- No CameraExtensionsProxy loader was demonstrated by the v7 test. The presence
  of vendor tag constants in the CameraX extension jar does not establish one.
- The next candidate is the bounded native cameraserver integration documented
  in the [native hook record](camera-native-hook-20260907.md). The binary evidence
  does not require wholesale replacement of the HyperOS Java framework.

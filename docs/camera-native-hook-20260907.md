# Native Xiaomi camera session hook (2026-09-07)

The missing camera integration is a native `frameworks/av` hook, and the factory
call path is now established from its binary. A guarded source implementation
has been installed in the existing Evolution checkout as
`nezha.0e2658970d62a3712f0398de` for the v8 successor. At this source checkpoint,
native compilation and every v8 phone result are **unverified**; the change is
**not device-admitted**. The installed v7 package and its host bundle remain the
predecessor and rollback evidence.

This record extends the [camera-framework port](camera-framework-port-20260907.md)
and [capture diagnosis](camera-capture-diagnosis-20260907.md). The
[structured record](../research/camera-native-hook-20260907.json) holds artifact
hashes, addresses, ABI measurements and the source receipt. Raw binaries,
disassembly and logs remain under ignored directories.

## What the factory actually does

The factory `cameraserver` is 4,065,288 bytes, SHA256
`ab2b9ef0c93c17e8252e64932b6ebb8746e2d10d37c782051f2ee84f7c9ad118`, build ID
`38f5c0b11c15f9e0109745e0c1eb9ffb`. Its compressed `.gnu_debugdata` supplied
internal function symbols; LLVM disassembly then established callers, argument
flow and the library's virtual dispatch. The retained v7 cameraserver is
4,013,544 bytes, a difference of 51,744 bytes. Size alone does not establish
which changes matter; the recovered call sites do.

`CameraSingleton::GetImplInstance()` starts at `0x2d077c`. It loads
`/system_ext/lib64/libcameraimpl.so` with `RTLD_LAZY` at `0x2d07b0`, resolves the
unmangled export `create` at `0x2d07c8`, calls that zero-argument factory function
at `0x2d07ec`, and retains its returned object. It logs loader failures and the
`CameraStub` wrappers become no-ops when no object is available. The factory
resolves only `create`; its wrappers call virtual methods on the returned object.
The library's `create` allocates and constructs its own `QcomCameraImpl`, so the
caller does not need to guess object size or construct opaque storage.

The `String8` argument to `updateSessionParams` is the **camera ID**. Both
configuration callers construct it from `Camera3Device::mId`; the factory
`getId()` returns the same member at offset `0xe8`. The library uses that key to
look up the package registered earlier through `setClientPackageName`.

Two methods supply the requested tags:

| Method | Established effect |
| --- | --- |
| `updateSessionParams(metadata, cameraId)` | Writes `com.xiaomi.sessionparams.clientName` from the registered package, plus customization/cloud-control tags |
| `executeSceneIdentify(metadata, configuration, cameraId)` | Derives the use case from the actual stream configuration and writes `com.xiaomi.sessionparams.MiStreamUsecase` and `activityName` |
| `detachSceneIdentify(metadata)` | Removes `MiStreamUsecase` after HAL configuration; the other tags remain |

The `MiStreamUsecase` metadata update is in `executeSceneIdentify` at library
address `0x72348`. Calling only `updateSessionParams` would omit the tag that the
vendor graph needs. Existing AOSP `injectSessionParams` and
`setInjectedSessionParams` names are not evidence of this Xiaomi path: the
observed configuration path mutates the metadata sent directly to the HAL.

## Configuration and client lifecycle

| Location | Factory call and position |
| --- | --- |
| `CameraService` construction | `hookModuleInit()` at `0xc8f64` |
| API2 connection | Split package/activity, then register activity with the camera ID at `0x11a62c` |
| API2 client constructor | Register package with API value `2` at `0x19e3bc`, then parse customization at `0x19e3ec` |
| API1 client constructor | Register package with API value `1` at `0x165208`, then parse customization at `0x165238` |
| `initializeCommonLocked` | `initializeDeviceInfo(mDeviceInfo, cameraId)` at `0x216c40` |
| `configureStreams` template fallback | Update the cached default template before speculative configuration at `0x1ff7dc` |
| `filterParamsAndConfigureLocked` | Update the filtered session metadata after rotation/autoframing handling at `0x209f28` |
| `configureStreamsLocked` | Execute scene identification after populating the stream configuration at `0x20b0e8` |
| HAL boundary | Lock the same metadata at `0x20b11c`, configure the HAL at `0x20b174`, unlock at `0x20b1a4`, then detach at `0x20b1ac` |

The factory also customizes default requests in `Camera3Device` on both cached
and fresh-template paths, and in `AidlDeviceInfo3` after setting the vendor ID.
It calls request-submit and cancel notifications with camera ID, client UID,
calling PID, request ID and package in the measured order. Submit notifications
receive the original per-entry request metadata. These notification methods
forward to an optional component; they do not populate the session maps.

This evidence supersedes the earlier inference that normal rear capture needs
wholesale replacement of `framework.jar` or `services.jar`. The examined core
session-update and scene-identification functions use native state and camera
configuration files. No additional MIUI service requirement was found in that
path. Whether the port executes successfully on this build remains a device
question.

## Authored integration

The [selector contract](../config/nezha-camera-session-inject.json) binds the
[product fragment](../device/xiaomi/nezha/camera-session-inject.mk),
[framework patch](../patches/evolution/0029-nezha-camera-session-inject.patch) and
[adapter source](../templates/camera-session-inject/NezhaCameraSessionHook.cpp).
`NEZHA_CAMERA_SESSION_INJECT` is off by default, requires
`NEZHA_CAMERA_FRAMEWORK=true`, and adds its source and define only to the Android
ARM64 target through the `nezha_camera_session.enabled` Soong selection. The
v8 generated product explicitly selects it.

The upstream source is Evolution-X `frameworks_av`, branch `bka`, revision
`dfe1a704f074bbbc3f60b740a9e5ec6b786228f3`. The transaction checked a clean
`frameworks/av` checkout and exact preimage hashes before installing the patch.
It preserves the other source projects and their selected inputs.

The adapter follows the recovered lifecycle with these deliberate differences:

- It lazily loads once with `RTLD_NOW | RTLD_LOCAL`, resolves every selected
  export before creating a usable object, calls `hookModuleInit`, and retains
  the object and handle for process lifetime. A loader or symbol failure logs
  once and leaves the adapter inactive for that process.
- It calls `create` and the measured exported `CameraImpl` methods through
  typed function pointers with an explicit opaque object pointer. The supplied
  Qcom implementation inherits these methods. This avoids recreating the
  factory's entire virtual interface or assuming the private object's layout.
- Activity and package registration run together in the validated API1/API2
  client constructor. The adapter keeps the framework's validated package
  identity and does not alter attribution or permission checks.
- `configureStreamsLocked` owns a mutable copy of the session metadata rather
  than casting away constness on caller metadata. The complete raw-buffer copy
  preserves vendor ID. Scene identification runs before `getAndLock`; detach
  runs after unlock and before handling the HAL result.
- Diagnostic output records tag presence, types, counts, the integer use case
  and the HAL configuration result for the later acceptance run.

Compile-time ABI pins require 8-byte pointers and `String8`, 24-byte libc++
`std::string` and `CameraMetadata`, and a 64-bit `long`. The framework
`camera_stream` fields read by the library are pinned at offsets width `4`,
height `8`, format `12`, use case `104`. Stream configuration offsets are count
`0`, stream array `8`, and operation mode `16`. These pins describe the measured
factory ABI; they do not prove all runtime compatibility.

A static dependency audit walked 92 libraries across the existing system,
system_ext and runtime APEX artifacts. It found zero missing libraries and zero
unresolved global imports. Runtime cameraserver namespace visibility, SELinux
access and successful loading remain unverified. The optional notification path
is gated by `persist.sys.miui.camera.cameramind.supported`, default false; when
selected it attempts to load `libcammsger.so`, and failure is a logged no-op.
The core tag-writing path has no such dependency in the examined code.

The live v7 linker configuration includes `system_ext/lib64` in its default
system namespace search and permitted paths. The optional CameraMind flag is
actually `true` on this phone while `libcammsger.so` is absent. The notification
methods handle a null optional instance in the examined code; that absence is
recorded separately from the core session-tag prerequisites. Successful v8
loading and capture still require the device run.

## Source checkpoint and retained artifacts

The guest transaction `/work/validation/camera-native-hook-source-20260907-v1`
installed ten changed files and emitted a 613-row inventory for
`nezha.0e2658970d62a3712f0398de`. The private receipt
`reports/camera-native-hook-20260907/source/source-installed.json` has SHA256
`87eb9268c0caaae04a94f4d9fcbbab06b14969d2a7715a3a921330c4a850ee85`.
Its predecessor is the 605-row v7 receipt. This proves source installation,
not compilation, delivery or capture.

Only the explicitly approved duplicate guest file
`/work/validation/variant-opt-in-super-20260906-v7/super.img` was reclaimed.
Before removal, it and both retained host copies were 9,476,081,776 bytes with
SHA256 `ac9cbf2d74fc58fd70b89cfd984da518db5afe757e9fbd56fa7049e3afa7b427`.
The guest path was confirmed absent afterward and free bytes increased from
209,767,469,056 to 219,243,556,864. The v7 transfer copy and flash bundle remain
under `artifacts/`; no other source checkout or build output was removed by
this reclaim.

At this checkpoint, native compile, v8 package admission, flash, boot, slot,
SELinux state and camera results are all unverified. Device admission requires
an enforcing slot A boot, Xiaomi session tags present at rear configuration,
no missing-use-case or virtual-super-graph error, successful camera 0
configuration, and a saved JPEG from both Aperture and Xiaomi Camera. Front
and single-sensor operation and a provider crash-free acceptance window are
also required. A further required runtime component, if observed, must be
recorded with its evidence before selecting another change.

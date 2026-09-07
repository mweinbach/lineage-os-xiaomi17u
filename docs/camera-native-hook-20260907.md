# Native Xiaomi camera session hook (2026-09-07)

**The native hook is built, flashed and running on v8; Aperture saves ordinary
JPEGs from rear camera 0 and front camera 1.** Both saved files independently
decode as 4096×3072 images. The phone boots
`nezha.f2e3feac321f56f92d2ad7ea` on slot A with SELinux Enforcing. The factory
library loads into cameraserver, writes the Xiaomi session tags and reaches
successful HAL configuration in those two capture windows.

The change remains **not device-admitted** against the complete acceptance
scope. Aperture's initial Ultra HDR/JPEG_R sessions fail graph construction;
Xiaomi Camera reaches a measured compatibility dialog and self-exit after a
temporary auxiliary-camera visibility test; no Xiaomi JPEG or isolated rear
camera 2/3/4 result is verified. The v7 host package remains the immediate
predecessor and rollback evidence. No further MIUI service requirement was
identified for the native core used by the successful Aperture captures.

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
path; v8 now executes it successfully in the measured Aperture JPEG captures.

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
unresolved global imports. The later v8 runtime confirms cameraserver can load
the library and execute the core calls while Enforcing. This does not establish
every optional method's runtime behavior. The optional notification path is
gated by `persist.sys.miui.camera.cameramind.supported`, default false; when
selected it attempts to load `libcammsger.so`, and a missing optional instance
is handled without blocking the core tag-writing path.

The v7 linker observation includes `system_ext/lib64` in its default system
namespace search and permitted paths. At that checkpoint the optional CameraMind
flag was `true` while `libcammsger.so` was absent. The notification methods
handle a null optional instance in the examined code; that absence remains
separate from the core session-tag prerequisites. The factory also calls
`notifyConfigStream`, an omitted callback that can forward optional intent-aware
notifications and reset CameraOpt timestamp state after successful configuration.
The structured record preserves its exact call sites. No evidence connects it
to the Xiaomi app compatibility gate or makes it a requirement for the measured
ordinary-JPEG captures.

## Source checkpoint and retained artifacts

The guest transaction `/work/validation/camera-native-hook-source-20260907-v1`
installed ten changed files and emitted a 613-row inventory for
`nezha.0e2658970d62a3712f0398de`. The private receipt
`reports/camera-native-hook-20260907/source/source-installed.json` has SHA256
`87eb9268c0caaae04a94f4d9fcbbab06b14969d2a7715a3a921330c4a850ee85`.
Its predecessor is the 605-row v7 receipt. This proves source installation,
not compilation, delivery or capture.

The first cameraserver compile stopped at a missing private metadata accessor
declaration in the diagnostic logger. Its ABI size/offset assertions passed.
Source revision 2 adds `camera_metadata_hidden.h`, keeps all 613 inventory rows,
and creates identity `nezha.f2e3feac321f56f92d2ad7ea` through a second transaction.
The first receipt and failed build result remain preserved in the structured
record. The actual build compiler is `clang-r563880c`; `clang-r547379` supplied
the analysis tools. Cross-DSO CFI stays enabled. The inspected Bionic loader
already handles the uninstrumented factory library, so the adapter adds no CFI
exemption.

Only the explicitly approved duplicate guest file
`/work/validation/variant-opt-in-super-20260906-v7/super.img` was reclaimed.
Before removal, it and both retained host copies were 9,476,081,776 bytes with
SHA256 `ac9cbf2d74fc58fd70b89cfd984da518db5afe757e9fbd56fa7049e3afa7b427`.
The guest path was confirmed absent afterward and free bytes increased from
209,767,469,056 to 219,243,556,864. The v7 transfer copy and flash bundle remain
under `artifacts/`; no other source checkout or build output was removed by
this reclaim.

The second focused cameraserver build returned exit 0 at native run
`20260907T205619-userdebug`, with identical 613-row source inventories before
and after. Its installed cameraserver is 4,026,840 bytes, SHA256
`a47fc0682722728b1433790a9dbe70d537d16b43979b99d84e0e263c86a5841f`.
The final installed binary readback matches that hash. The installed
`libcameraimpl.so` also matches its selected factory input at SHA256
`403782350ef40558edec32ff63dda6ff9c4b8ab18573e30c4f2dab80842fc5c5`.

The full target-files run `20260907T210017-userdebug` returned exit 0 with
identical source inventories. Host transfer and measured image admission
passed, and the packaged cameraserver matches the focused artifact exactly.
Signing, signed-archive reconciliation and independent eight-payload bundle
verification passed. The private bundle is
`artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v8/`.
The structured record holds the source, target-files, Super, signing and bundle
identities; these are distinct from the device results below.

`make test-current` passed 939 tests. The affected selector tests passed, and
`make test` passed all 4,809 tests before installation. The final post-install
run passed the same 4,809 tests in 177.510 seconds plus shell checks. These are
offline tooling and source-contract results.

## V8 installation and camera results

The authorized route acknowledged all eight writes: shared Super, then
`dtbo_a`, `init_boot_a`, `vendor_boot_a`, `recovery_a`, `boot_a`,
`vbmeta_system_a` and `vbmeta_a`. The phone rebooted without a wipe or slot
change and reached `sys.boot_completed=1` in 25.5 seconds as userdebug with
adb root. The first-boot and final snapshots independently identify f2e, slot A
and Enforcing. Recovery remains the pinned working76 derivative.

Nine acceptance snapshots span 17:38:54–17:56:43 local time. Each binds the same
613-row revision 2 source receipt, SHA256
`254b42243742a8b3945fb064156a84a2b0d1e19db1990403f6da4d094fa1f651`.
The provider and cameraserver PIDs stay unchanged across those snapshots, and
the captured crash buffers contain no native fatal signal or camera-process
crash. The library appears in cameraserver mappings after its first load;
the provider does not need to map it.

| Acceptance item | Measured result |
| --- | --- |
| Native loader and tags | Factory hook loads in cameraserver. Aperture rear/front configurations contain MiStreamUsecase int32[1]=2, clientName byte[23], activityName byte[5]; provider reads use case 2. |
| Aperture ordinary JPEG, rear camera 0 | Configure returns 0 at 17:47:59.514. Preview graph starts and a saved JPEG independently decodes as 4096×3072. |
| Aperture ordinary JPEG, front camera 1 | Configure returns 0 at 17:50:15.871. A separate saved JPEG independently decodes as 4096×3072. |
| Aperture Ultra HDR/JPEG_R | Initial rear and front sessions fail the MCXSuperFG sink-port check and return framework configure -38. No JPEG_R capture is admitted. |
| Xiaomi Camera with selected source configuration | The existing Java auxiliary-camera policy exposes only IDs 0/1 to this package; role initialization does not reach a successful capture. |
| Xiaomi temporary auxiliary exposure test | Exact `com.android.camera` allowlist exposes IDs 0–8. Camera 5 configures with status 0 and wide-sensor frames begin; the app then shows its compatibility dialog and exits after three seconds. No saved Xiaomi JPEG. |
| Isolated rear cameras 2/3/4 | Unverified; neither the logical rear capture nor camera 5's active wide sensor establishes individual-lens acceptance. |

The rear file is 1,308,821 bytes with SHA256
`f20185958455d1f482ec154581751583c239cd37bb5b84e38b7c2bea9c761dfb`.
The front file is 5,397,082 bytes with SHA256
`287021450c86e70f85249028af0340e1960b24dba9725da9b63c1d126bb9050b`.
Each host file matches its device-side stable metadata/hash receipt and passes
an independent image decode. These are two measured Aperture captures, not a
claim about every lens, mode or OEM feature.

## Remaining JPEG_R and Xiaomi app failures

The first JPEG_R failure is the vendor graph validator's missing MCXSuperFG
sink `(FeatureId:3 InstanceId:0, Session:0 Pipeline:0 PortId:0 Type:0)`. That
precedes `VirtualSuperGraphDesc:4`, vendor configure -19 and framework -38.
The hook already loaded and the provider received its tags before that failure.
The numerical feature ID has not been mapped to a named feature in this review.

The vendor's ordinary JPEG snapshot predicate accepts output BLOB streams with
dataspace `0x101` or `0x08c20000`, excluding JPEG_R `0x1005`. In the failed
session its feature-requirements dump marks the still stream as IsSnapshot=0;
the ordinary-JPEG run marks it as 1 and configures successfully. However,
disabling Ultra HDR also changes Android's standard stream use cases from
preview/still 0/0 to 1/2. Xiaomi's separate MiStreamUsecase remains 2, its normal
classifier fallback, in both runs. The comparison proves the ordinary-JPEG
configuration works without isolating dataspace alone as the cause. Yuv2Yuv
0:1 pruning appears in both failed and successful sessions and cannot by itself
explain the rejection. No JPEG_R-to-JPEG rewrite was found in the examined
factory configure path.

Xiaomi Camera's visibility issue comes from the existing framework helper's
exact package matching against `vendor.camera.aux.packagelist`. The imported
factory list omits `com.android.camera`; the package already has its required
camera grants. The temporary test replaced the list with that exact package
and confirmed nine app-visible IDs, successful camera 5 configuration and
wide-sensor activity. Camera 5 uses a logical three-camera configuration, so
that activity is not an isolated physical-camera test. The early screenshot
and app log then establish a real
compatibility rejection: the app says its Camera version is incompatible with
the device model, announces a three-second exit and finishes itself. This
measured v8 self-exit is separate from earlier experiments whose scripts
force-stopped the app. The bounded static trace follows handler message 11 to dialog kind 4,
resource `0x7f120018` (`plurals/f5p`), then the timer to `Activity.finish()`.
Static bytecode exposes device-configuration, native BSP/security and cloud
callback routes to that shared dialog. The retained logs do not identify which
route fired; `libHawk` loaded successfully. The underlying compatibility
predicate remains unresolved, so no required service, library or property
change is established. Work stops at that
additional app compatibility requirement without selecting a speculative fix.

The full original auxiliary property was restored after the observation
windows, and the temporary stay-awake setting was returned to 0. Aperture's
visibly selected Ultra HDR-off setting remains as the measured ordinary-JPEG
configuration. The final cleanup snapshot still reports f2e, A and Enforcing.

Detailed runtime comparisons, app actions, snapshot receipts and the final
acceptance audit remain in ignored reports and evidence; their paths and hashes
are indexed by the structured record. Complete camera admission remains open
for JPEG_R, a saved Xiaomi Camera JPEG, its compatibility/visibility issues and
isolated rear-lens validation. Any further required component must be supported
by its own evidence before selecting another change.

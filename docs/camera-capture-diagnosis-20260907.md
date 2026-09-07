# Camera capture after the enumeration fix: the multi-camera graph blocker (2026-09-07)

The [XML selection fix](camera-xml-selection-20260907.md) is flashed as delivery
set v6 and enumeration is correct: `dumpsys media.camera` reports nine devices,
two public, no damaged role, provider crash-free from first boot. This page
records why **capture still does not work in either camera app**, measured on
the flashed build (`nezha.e2b55ae5f0effd944736a6b0`, root shell, enforcing).
It is on-device diagnosis of a closed vendor stack; no fix is device-admitted.

**Later correction:** the [native hook investigation](camera-native-hook-20260907.md)
establishes the factory `cameraserver` loader and the metadata calls missing from
this v6 checkpoint. `updateSessionParams` writes the registered client name;
`executeSceneIdentify` writes `MiStreamUsecase` and activity name before HAL
configuration. Both use a camera-ID key. This refines the framework-side
diagnosis; the measured v6 failures below remain historical results. The earlier
Xiaomi app self-exit interpretation is also corrected below.

## What works and what fails

- **Single physical cameras open and stream.** The Xiaomi app opened device 5
  (one physical sensor) three separate times; each session connected, streamed
  for several seconds and closed cleanly, with zero `configureStreams`
  failures and zero super-graph errors in its window.
- **The default rear camera fails for every app.** Public camera 0 is a Xiaomi
  logical device fusing three physical sensors (`android.logicalMultiCamera.physicalIds`
  and `com.xiaomi.cameraconfiguration.physicalCameraIds int32[3]`). Opening it
  aborts stream configuration and returns an error to the app.

## The exact failure

Opening camera 0, the provider builds the Xiaomi Unified Multi-Camera graph and
fails:

```
chifeature2generic.cpp DoQueryCaps() ... multicamera 1 numPhysicalCameras:3, isUMcxEnabled:1
chifeature2graphmanager.cpp:342 Initialize() Failed to create VirtualSuperGraphDesc: 4
chxmulticamerabase.cpp:2880 CreateFeatureGraphManager() Failed to allocate graph manager
chxmulticamerabase.cpp:2596 Initialize() Failed to initialize Multicamera Usecase: 8
chxextensionmodule.cpp:7842 InitializeOverrideSession() send error to MQS: Normal CreateUsecaseObjectFail
MiCamService AidlCameraDeviceSession.cpp:198 configureStreams() status=-19  (convertStatus: 19 No such device)
Camera3-Device: Camera 0: configureStreamsLocked: Unable to configure streams with HAL: Function not implemented (-38)
```

`VirtualSuperGraphDesc: 4` is the QTI CDK result EInvalidArg. The CHI override
carries the paired check string `Invalid configuration, isUnifiedMCX is %d,
IsApolloArch is %d`, so the Unified Multi-Camera path is gated on the SoC
architecture, not on a settable option. The graph builder receives an invalid
argument while assembling the three-sensor virtual super graph and the whole
rear session is rejected with `ENODEV`.

## Why this is not our configuration

- `multiCameraLogicalXMLFile=nezha.xml` is set in the read-only
  `camxoverridesettings.txt`; the correct table is selected.
- `/vendor` and `/odm` are EROFS, read-only, dm-verity enforcing, and their
  camera trees are byte-identical to the factory extract. The failing inputs
  cannot be edited at runtime, and editing them is not the difference from
  stock, because stock uses the same bytes.
- The Xiaomi camera-service extension (`system_ext/lib64/libcsextimpl.so`,
  dlopened by `CameraServiceExtFactory`) is absent on our build **and** absent
  in the full factory `system_ext` extract (713 libraries, no `csext`). Its
  "extension not loaded" message is therefore not the cause.

The difference from stock is on the framework side. Throughout the failing
session the HAL logs that Xiaomi session parameters and per-stream use cases
are missing: `MI_SESSION_PARA_CLIENT_NAME/ACTIVITY_NAME not found`,
`COM_XIAOMI_SESSIONPARAMS_MI_STREAM_USECASE not found`, `get MiStreamUsecaseName
tag failed`, and CameraX's own `Expected stream use case ... null cannot be
set`. HyperOS's camera framework supplies those tags; the AOSP-based Evolution
framework does not, and the Unified Multi-Camera graph builder rejects the
configuration without them.

## App behaviour

- **Aperture** (CameraX) opens camera 0, receives the error, shows "Error while
  setting up the session, will try to recover", retries the rear, and finishes
  to the launcher within about two seconds. It never reaches a state where the
  front camera can be selected from the UI.
- **The Xiaomi app** (`com.android.camera`, the packaged `NezhaXiaomiCamera`)
  opens a single sensor and streams briefly in the recorded test windows.
  The earlier claim that it returned to the launcher on its own is withdrawn:
  the test scripts force-stopped it, as clarified in the subsequent native-hook
  task. This is not evidence of an app crash or spontaneous exit. It also logs
  a missing `com.miui.cameraopt` perf service (a SELinux
  `find` denial for the `cameraopt` service and an `UnsatisfiedLinkError` for
  `CameraPerfInterface`); that boost service is a HyperOS system component and
  is secondary to the graph failure.

## Assessment

At this v6 checkpoint, enumeration is fixed and flashed. Full capture through
the default rear camera is blocked inside Xiaomi's proprietary Unified
Multi-Camera feature-graph builder while the Xiaomi session tags are missing.
The later native investigation identifies the factory `frameworks/av` integration
that supplies them to normal camera clients. These findings do not establish
the Xiaomi app or wholesale Java-framework replacement as requirements for
basic rear capture. The vendor inputs remain read-only and identical to factory,
and no writable override was found to toggle the architecture-gated multi-camera
path. Single physical sensors stream, so the sensors and lower CamX pipeline
work for those measured sessions.

Not verified in this record: capture from a single physical sensor to a saved
file; whether porting the native stream-use-case
injection would let the super graph build; the exact predicate behind
`IsApolloArch`.

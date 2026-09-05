# Package7 Aperture initialization

The September 5 user report and captured crash identify an Aperture startup
failure while CameraX constructs stream maps: `minFrameDurations must not be
null`. This is distinct from importing Xiaomi Camera and does not establish a
capture-session or sensor failure.

## Device observation

The user authorized installation, execution and removal of a metadata-only
diagnostic. The exact previously flashed device was selected explicitly. The
probe was absent before installation and absent again after successful removal.
It requested only `CAMERA`, targeted SDK36, and never opened a camera or captured
media. It used its own package/UID and diagnostic signing key.

The probe showed public app-visible IDs **0, 1 and 2** while
`SYSTEM_CAMERA` permission was false. ID0 and physical IDs 252706817, 252706820
and 252706821 constructed standard stream maps successfully. ID1/2 advertised
system-camera/reprocessing capabilities without backward compatibility;
enumerating their characteristic keys also failed on missing metadata. The
service dump separately shows that ID1/2 omit standard minimum-frame and stall
duration tables. The probe's key enumeration failed before its independent
stream-map query for those two IDs, so that particular probe did not directly
repeat the minimum-frame-duration exception on ID1.

The front-facing sensor is physical ID252706817, exposed beneath logical ID0.
IDs1/2 are processing devices, not the normal front-facing camera. Filtering
them does not itself implement a front-camera selector or prove photography.

Private evidence is under `evidence/camera-metadata-probe-20260905-v1/`, including
the screenshot, sanitized per-camera log rows and removal receipt. The existing
seapp policy denied `run-as`; collection used the probe's log output rather than
changing SELinux. No policy workaround was applied.

## Proven source cause and candidate fix

Actual clean source revisions were inspected in the existing build guest:

| Project | Commit |
| --- | --- |
| packages/apps/Aperture | `88625a9b7c4178601169dbda2c38cd845b68cd38` |
| frameworks/base | `8140698cc12983deecdbd434220affb5f931bfc6` |
| frameworks/av | `dfe1a704f074bbbc3f60b740a9e5ec6b786228f3` |

The exact bundled CameraX 1.7.0-alpha03 AAR was inspected off-device. Its
`CameraCompatibilityFilter.getBackwardCompatibleCameraIds` always admits IDs
`0` and `1` before checking their capabilities. Nezha's ID1 therefore reaches
stream-map initialization despite being a processing-only device. Normal
Aperture aux-camera exclusions run after initialization. A custom CameraSelector
also creates CameraInfo objects before applying its filter; those constructors
read stream metadata, making that workaround too late as well.

[Patch 0026](../patches/evolution/0026-aperture-nezha-camera-admission.patch)
adds a Nezha-only factory wrapper through CameraX's factory-provider interface.
It examines raw IDs' capability arrays before CameraInternal or stream-map
construction. Cameras must advertise backward compatibility and must not
advertise system-camera capability. Unreadable capabilities fail closed.
The wrapper filters initial IDs, presence updates and interrogation results,
preserves the original manager/coordinator/backend, and leaves physical-camera
enumeration on each admitted logical camera intact. It never rewrites metadata,
changes permissions, disables checks or modifies vendor binaries. Other devices
retain their original CameraX configuration.

A failed/empty Nezha provider produces an empty camera list for Aperture's
existing no-cameras UI instead of an uncaught worker exception. No arbitrary
camera is selected as a fallback.

## Validation and adoption

The [source contract](../patches/evolution/aperture-nezha-camera-admission.json)
records exact preimage and result hashes for all four source files. The native
`app/Android.bp` explicitly selects the new Java helper alongside its existing
Kotlin glob; the original Kotlin-only glob would otherwise omit the wrapper.
`python3 -m scripts.aperture_camera_admission --source <Aperture source> --output
<new output>` validates and stages only those files. It does not modify the
checkout or install anything.

Seven offline Python tests exercise native Java source selection, direct CLI help,
exact patch replay, modified-preimage
rejection, refusal to overwrite existing source/output, and scope/presence
contracts. The Java wrapper compiled against the actual pinned CameraX API jars
and Android SDK36. A JVM harness using fake CameraManager/CameraFactory objects
passed 15 behavior checks, including valid logical/external cameras, malformed
and missing metadata, processing cameras, zero supported cameras, rejected
getCamera calls and update/shutdown forwarding. Harness sources are in
`tests/fixtures/aperture-camera-admission-jvm/`; the exact API jars, compiled
classes and execution output remain under ignored
`reports/camera-init-fix-20260905/`.

These checks establish a source candidate. A complete Aperture build, resulting
ROM adoption and device preview/capture validation remain separate gates. Native
Xiaomi Camera integration and physical front-camera exposure remain separate
work; this patch does not claim that either works.

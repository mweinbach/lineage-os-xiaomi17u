# Camera metadata probe

This diagnostic reads Camera2 characteristics in an ordinary app process. It
never opens a camera, starts a preview, captures media, connects to a network, or
changes system settings. The only requested permission is `CAMERA`. The target
SDK is 36, matching the installed Aperture baseline. Its package and UID differ
from Aperture, so package-specific vendor behavior is not ruled out by a pass.

The September 5 Package7 Aperture crash occurs while constructing the standard
stream map, with `minFrameDurations must not be null`. Camera service dumps show
standard duration tables for public logical camera 0 and its three physical
children; system-only reprocessing cameras 1 and 2 omit these tables. Aperture
does not request or hold `SYSTEM_CAMERA`. The failing app-visible ID therefore
needs observation before selecting a compatibility patch. The existing Aperture
aux-camera exclusions happen after CameraX initialization and cannot prevent
this failure. Framework metadata checks must remain intact.

Build off-device with installed SDK 36/build-tools 36.0.0 and a local JDK:

```sh
python3 scripts/build_camera_metadata_probe.py \
  --sdk /absolute/path/to/Android/sdk \
  --java-home /absolute/path/to/jdk \
  --output artifacts/new-private-camera-probe-build
```

The builder refuses an existing output directory, creates a separate diagnostic
signing key there, verifies the APK signature/alignment, and records input/APK
hashes. It does not use the ROM signing key or invoke ADB. Output and signing
material belong in ignored `artifacts/`; do not commit them.

Install and launch only after explicit phone-change authorization. Press
**Inspect camera metadata** and grant Camera permission. The app records visible
IDs, physical IDs, capabilities, available stream-key counts and independent
standard/maximum-resolution stream-map results. One failing camera does not
prevent inspection of other IDs. No characteristic values involving images or
accounts are collected. The report stays in the app's private
`files/camera-metadata.json`; the diagnostic is debuggable so authorized
collection can read it with `run-as org.nezha.camerametadataprobe`. Per-camera
results also use log tag `NezhaCameraProbe`.

Interpretation: a failure for ID 0 identifies an app-visible metadata conversion
problem even when the service dump has duration tables. Exposure of system-only
IDs without the system camera permission identifies a different admission
problem. Success here requires a follow-up in Aperture's actual client context;
it does not prove preview, capture, CameraX or Xiaomi Camera works.

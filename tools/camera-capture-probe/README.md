# Foreground Camera2 capture probe

This separate diagnostic app reads camera metadata or performs one explicitly
requested Camera2 capture with a visible preview. It requests only `CAMERA`,
has no network permission or background service, and stores reports and images
in its private files directory. It does not alter settings, camera properties,
package identity, capabilities, or vendor tags. Leaving the activity cancels an
active test and closes its resources. Pending actions are cleared on pause,
except while this activity is displaying its own permission request; stopping
the activity clears them even during that permission flow. The existing metadata-only probe remains
unchanged.

The app targets SDK 36, requires Android 14 or newer, and has a separate package
and UID from Aperture and Xiaomi Camera. A successful probe capture proves only
that exact configuration in this client context. Device installation and any
capture require the user's authorized phone-operation scope; the builder never
invokes ADB or accesses a phone.

Build with an installed SDK and JDK:

```sh
python3 scripts/build_camera_capture_probe.py \
  --sdk /absolute/path/to/Android/sdk \
  --java-home /absolute/path/to/jdk \
  --output artifacts/new-private-camera-capture-probe-build
```

The builder requires a new Git-ignored directory under `artifacts/`, creates a
dedicated diagnostic signing key, verifies signature/alignment, and records
source/tool/APK hashes. It refuses to overwrite an existing directory or key.
Each fresh build gets a new diagnostic key, so installing a later build over an
earlier one requires handling the different signature and preserving any wanted
private capture evidence first. No ROM signing material is used.

**Inspect** saves an `inventory-*.json` file without opening a camera. It records
actual app-visible IDs and physical children, standard and maximum-resolution
maps, every output format's normal/high-resolution sizes and durations, preview
sizes, capabilities, focal lengths, active arrays, and public request keys.
Platform extension enumeration may initialize the extension proxy; it records
each supported Camera2 extension's JPEG, JPEG_R, YUV and preview sizes with
individual errors. It does not configure an extension session. Camera2's named
extension constants are used; CameraX's numerical extension values differ.

**Capture one** validates the explicit form values against the current public
characteristics, creates a preview/still session, waits for eight preview
results, and submits one still request. Capture deadlines are 25 seconds from
start; cancellation and callbacks use a dedicated handler. SDK/binder operations
are subject to the platform's own IPC behavior, so the timer cannot preempt a
blocked framework call.

Once the matching image and total result arrive, the session and camera are
closed before file encoding, hashing, and JPEG validation. The acquired image
and reader remain valid until saving ends. Cancellation is checked after each
save stage and synchronized with the final outcome. A cancellation during a
native DNG write cannot preempt that native call, but it produces a cancelled
report, with any retained bytes listed as an unadmitted `partial_artifact`.

| Input | Values / behavior |
| --- | --- |
| `camera_id` | Exact ID from this package's visible list; no fallback to another camera |
| `physical_id` | Optional exact child of the selected logical ID; routes both outputs and uses the child's total result for DNG metadata |
| `format` | `jpeg`, `raw` (RAW_SENSOR written through DngCreator), or `jpeg_r` |
| `width`, `height` | Required positive integers, at most 210 MP; exact format/size must exist in the selected public map |
| `pixel_mode` | `default` or `maximum`; maximum requires advertised ultra-high-resolution capability and its public map |
| `stream_use_cases` | `default` or `preview-still`; the latter requires advertised PREVIEW/STILL_CAPTURE stream use cases |

The manifest's exported foreground activity also supports explicit diagnostic
invocations. Intent `org.nezha.cameracaptureprobe.INSPECT` requests metadata.
Intent `org.nezha.cameracaptureprobe.CAPTURE_TEST` plus boolean extra
`capture=true` requests exactly one capture with the inputs above as extras
(`width` and `height` are integer extras; the others are strings). The activity
must be resumed, focused, have Camera permission, and have a preview surface
before starting. A normal launcher start merely presents the form. Activity
recreation does not replay a previous capture request.

Each test creates `files/capture-<time>-<random>/report.json` and, if successful,
`capture.jpg` or `capture.dng`. The report records exact configuration, event
times, session-support query, preview count, returned dimensions, matching
image/result sensor timestamps, exposure, sensitivity, file bytes and SHA256.
It refuses to pair an image with mismatched metadata. JPEGs receive an encoded
dimension check and a bounded image decode; JPEG_R additionally requires a
decoded gain map. Independent host decode/inspection is still needed for device
admission. A failed save may leave an incomplete or rejected image beside its
failure report; only `outcome=captured` identifies a probe-completed test.

**Extensions** opens a separate foreground form without taking a picture. It
uses Android's `CameraExtensionSession` API for one explicitly selected camera,
extension, format, and exact advertised size. Camera2 extension mode names are
used (`automatic`/`auto`, `beauty`/`face_retouch`, `bokeh`, `hdr`, `night`);
CameraX's numerical values
are not interchangeable with them. Opening the form does not start a capture.

The separate `.ExtensionCaptureActivity` supports the explicit action
`org.nezha.cameracaptureprobe.CAPTURE_EXTENSION` plus boolean `capture=true` and
the `camera_id`, `extension_mode`, `format`, `width`, and `height` extras. Width
and height are integers; the other extras are strings. The extension must be
advertised for that exact camera, output format (`jpeg` or `jpeg_r`), and size.
RAW extension capture is not implemented. Reports distinguish
extension-session captures from ordinary Camera2 captures, and JPEG_R still
requires an actual decoded gain map. The same foreground, permission, one-shot,
cancellation, and evidence-admission requirements apply. Successful platform
extension capture verifies that API path in this package; CameraX integration
and Xiaomi Camera remain separate client paths.

Extension capture waits for eight visible `TextureView` frame updates and has
a 60-second total deadline. Ordinary capture uses eight capture results and a
25-second deadline. Explicit extension invocations must include `camera_id`
and `extension_mode`; omitted format and dimensions default to `jpeg` and
4096x3072, and still must match the extension's advertised configuration.

Audit a retained extension report beside its saved image with:

```sh
python3 scripts/audit_camera_extension_capture.py /private/capture-directory/report.json
```

The offline auditor requires a successful one-shot extension receipt with at
least eight visible preview frames, completed processing/sequence callbacks,
and matching image/result timestamps when result metadata is available. It
recomputes file size, SHA-256, and primary JPEG frame dimensions. The app's
decode/gain-map claims remain app-reported evidence; the auditor explicitly
does not independently decode pixels, validate a gain map, or prove callbacks
occurred. Cancelled, failed, and partial artifacts fail admission.

The probe does not implement Xiaomi's private operation modes, its processed
Ultra RAW pipeline, or vendor-only 50/200 MP tables. Those are separate
contracts. On the retained v8 metadata, physical camera 2 is
wide, 3 ultrawide, and 4 telephoto; the app must freshly observe whether those
IDs are public to its package. The standard API exposes binned RAW/JPEG sizes;
vendor full-resolution sizes must not be presented as standard
`SENSOR_PIXEL_MODE_MAXIMUM_RESOLUTION` support.

Primary API references: [DngCreator](https://developer.android.com/reference/android/hardware/camera2/DngCreator),
[OutputConfiguration](https://developer.android.com/reference/android/hardware/camera2/params/OutputConfiguration),
and [CameraExtensionCharacteristics](https://developer.android.com/reference/android/hardware/camera2/CameraExtensionCharacteristics).

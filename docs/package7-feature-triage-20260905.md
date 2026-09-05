# Package7 feature triage — September 5, 2026

The user confirmed Google sign-in works. Fingerprint enrollment displays its UI
but does not respond to a finger; camera fails; status-bar icons sit incorrectly
near the corners. Home-screen spacing was not the reported problem.

Read-only collection matched the attached device to the private Package7 install
receipt before querying it with an explicit ADB selector. Current incremental
identity is `nezha.128c96ed5e626cdd0d213542`, and `sys.boot_completed=1`.
Private dumps remain in `evidence/package7-feature-triage-20260905T155732Z/`.
No phone settings, packages, partitions, or boot state were changed.

## Status bar

The live display is 1200×2608 at 480 dpi, matching the stock density; there is no
size/density override. Android's active cutout resource is empty, corner radius
is 20dp, and status-bar height is 28dp. These generic values also exist in stock
framework-res, but stock overrides them in its device-specific overlay APKs.

The retained exact-device DevicesAndroidOverlay defines 170px corner radii,
144px default/portrait status-bar heights, and the cutout path
`M 0,0 H -34 V 144 H 34 V 0 H 0 Z`. DevicesOverlay targets SystemUI and supplies
100px rounded-corner content padding plus top/bottom status-bar padding of
38px/20px. The authored device overlays select the eight resources present in
the pinned Evolution framework/SystemUI, omitting Xiaomi's bottom-padding
resource because Evolution does not define it. Generated candidates must
include both XML files. Private APK
extraction receipts and resource dumps remain under
`artifacts/display-stock-20260905/`. This is a source correction awaiting a
successor build and device validation, not a fixed-on-phone claim.

## Fingerprint

The framework registers fingerprint sensor 5, the HAL and vendor extensions are
present, and the dump reports zero HAL deaths and no lockout. No fingerprints
are enrolled. The snapshot had no active enrollment operation, so it cannot
identify where the failing attempt stops.

SystemUI uses center (596,1984), radius 74, bounds (522,1910)–(670,2058).
These exactly match retained stock ODM properties specifying location 522,1910
and size 148,148. The different coordinates in the reference device checkout
are not adopted. Capture scheduler, SystemUI, and fingerprint logs while the
user leaves enrollment active to distinguish session startup from touch/HAL
coordination. No speculative sensor-position or SELinux change is justified.

The user then reproduced enrollment while read-only capture continued in
`enrollment-160624/`. Settings owns an active FingerprintEnrollClient; the HAL
accepts enrollment and reports successful setup. SystemUI enables its touch
overlay and recognizes/pilfers touch gestures, but the vendor service remains
waiting for the next finger-down event. This narrows the fault to vendor
finger detection/touch coordination after enrollment starts. It does not yet
identify the missing extension call or establish a safe source fix. No relevant
fingerprint policy denial or HAL crash was observed in that capture.

## Camera

Aperture crashes in CameraX initialization with
`NullPointerException: minFrameDurations must not be null`, before opening a
camera session. The camera-service dump contains standard frame-duration
metadata for logical ID 0 and its three physical devices, but IDs 1 and 2 lack
both standard minimum-frame and stall durations. Those two devices advertise
system-camera/external/reprocessing characteristics.

The installed Aperture package neither requests nor holds SYSTEM_CAMERA. Thus
the dump identifies malformed metadata but does not prove which app-visible
camera ID triggered the exception. Do not describe a privileged permission grant
as the cause. The recorded Aperture source initializes CameraX before applying
its camera exclusion overlays, so a normal post-initialization exclusion does
not address this failure. Identify the offending app-context metadata before
implementing a compatibility fix; preserve framework validation and do not
invent frame timings. Xiaomi/Leica app integration remains separate.

Tooling tests and stock resource extraction do not establish working camera,
fingerprint enrollment, or corrected on-device status-bar placement.

## Local validation

`python3 -m unittest discover -s tests -v` passed all 4,610 tests. The focused
generator suite passed 252 tests; the two overlay coverage tests passed again
after omitting the unsupported Xiaomi resource. Both resource directories
compile with AAPT2, and all eight selected names were checked against the
pinned Evolution sources. Generation coverage checks both build variants,
missing overlay rejection, and manifest/hash tamper detection. Full resource
linking, successor image construction, and on-device visual validation remain
pending.

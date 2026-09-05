# Package7 fingerprint lifecycle candidate — September 5, 2026

The fingerprint enrollment screen opened on Package7 but received no acquisition
samples during the authorized read-only observation. The standard AIDL sensor 5
service was alive, enrollment entered its wait-for-finger state, and SystemUI
received touch gestures. The stock-derived center `(596, 1984)` and radius `74`
already match the stock location and size properties. Geometry is unchanged.

This record describes a compiled source candidate, not a successful device test.
The candidate has not been installed by this workstream. Enrollment, unlock,
lockout, screen-off and AOD behavior still need device validation after an
explicitly authorized successor installation.

## Missing lifecycle integration

The exact stock daemon and framework inputs establish an additional Xiaomi FOD
engine lifecycle interface alongside the standard Android fingerprint HAL.
Stock config enables its `2.0` touch-control path. The stock daemon waits on
operation, overlay and display-power state before enabling its touch path.
Evolution's current overlay lifecycle does not send those vendor notifications.

The clean implementation in
[patch0027](../patches/evolution/0027-nezha-fingerprint-overlay-lifecycle.patch)
uses only the observed Binder wire contract and lifecycle constants. It does not
copy proprietary Java code or package stock MIUI framework JARs. The
[pinned patch metadata](../patches/evolution/nezha-fingerprint-overlay-lifecycle.json)
records the selected framework commit and before/after hashes.

| Notification | Command | Values |
| --- | --- | --- |
| Overlay requested/hidden | 1 | 1 / 0 |
| Display power | 3 | SurfaceFlinger off 0, doze 1, on 2, doze-suspend 3, on-suspend 4 |
| Enrollment start/stop | 4 | 1 / 2 |
| Authentication start/stop | 4 | 3 / 4 |
| Interaction detection start/stop | 4 | 7 / 8 |

The bridge is gated by device `nezha`, sensor ID 5 and
`ro.hardware.fp.fod.touch.ctl.version=2.0`. An exact-device read-only check
confirmed that property on installed Package7 incremental
`nezha.128c96ed5e626cdd0d213542`.

`SensorOverlays` starts the bridge after successfully requesting the SystemUI
UDFPS overlay and stops it when the existing client lifecycle hides the overlay.
This is an overlay-request boundary; it does not claim a new rendering
acknowledgment from SystemUI. Standard enrollment/authentication, lockout,
trust, HAL pointer handling and sensor geometry remain in their existing paths.

A dedicated worker serializes vendor Binder transactions and display callbacks.
The biometric and main threads do not wait for the vendor service or perform
these transactions. Missing service, binder death, transaction exceptions and
cleanup exceptions are contained. Cancellation before worker startup avoids
activating the engine. Stop clears overlay state and then operation state, with
independent cleanup attempts and inactive guards for stale callbacks.

## Policy and provenance

The installed Package7 vendor CIL contains the existing property-read, service
lookup, Binder call/transfer and file-descriptor-use permissions at lines 15565
and 15567–15570. Its SHA256 is
`b0f3f4f0ca4d9526f3c0a05e7d650a1032ff32b3f81a2677aa6e929d9446d0c2`.
Installed platform mapping line 1036 maps `system_server_202504` to `system_server`;
that mapping SHA256 is
`a98f4b8479aa64e7d2b5a4146e6edc89fc50d62c80d37200258ff719dfced03b`.
No SELinux rule or normal-Android enforcement change is needed for this bridge.

Private extraction receipts, original proprietary inputs, bounded disassembly,
read-only runtime captures and compiler evidence remain under the ignored
`artifacts/fingerprint-contract-20260905/` directory. Stock daemon SHA256 is
`f155c923e79b00c378e87bd5ca44deab3454c70edde8771c4e7eab288bd2bce7`.
Its extension dispatch at `0x1ab3c` forwards commands to the engine at `0x206ac`;
command branches identify the state fields used by touch-state selection at
`0x20c3c`. Stock framework constant names independently establish the operation
start/stop values. These observations explain the candidate; they do not prove a
complete stock-feature implementation.

## Validation

- Both changed Java classes compile with the selected source JDK21 against the
  completed Package7 framework and services headers. This uses real Android
  headers, with source and classpath hashes recorded in private
  `patchstage/native-javac.json`; it is separate from a full services build.
- `python3 scripts/test_nezha_fingerprint_lifecycle.py` passes 111 assertions in a
  deterministic Java fixture using API doubles. It exercises operation pairs,
  display modes, gates, asynchronous dispatch, cancellation, missing service,
  Binder death, transaction errors, listener cleanup errors, stale callbacks,
  idempotence and Parcel recycling. API doubles are not platform-build proof.
- Four offline standard-library unit tests authenticate patch extraction,
  reject tampering, verify fixture inputs and propagate compiler failure.
  Process execution is mocked in these tests.
- A full selected services build and successor image validation are coordinated
  by the main feature-fix workstream. Parent records carry their final results.

The phone was only read. This workstream did not reboot, flash, wipe, change a
setting, or submit an enrollment/authentication operation to it.

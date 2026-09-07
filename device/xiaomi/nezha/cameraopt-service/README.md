# CameraOpt service candidate

This selected source candidate publishes the factory `cameraopt` Binder protocol
through an authored system service. The unchanged `miui-cameraopt` JAR remains
the sole runtime owner of its interface, native loader, and complete `Verifier`.
The verifier still checks the camera package through the real
`PackageManagerInternal`, then consults the original native cache. Its original
boot-completion hook runs at phase 1000.

`NEZHA_CAMERAOPT_SERVICE=true` requires the Nezha target and explicit camera
framework, native compatibility, platform signing, and auxiliary-package
selectors. It selects the two runtime JARs, the ordinary device-specific service
resource, and dedicated enforcing service/property policy. The exact compiled v8
`framework-res.apk` array was measured as empty at resource ID `0x01070051`;
its APK hash and empty predecessor are recorded in the contract. Recheck that
predecessor when rebasing the overlay.
The read-only enable property defaults to false in the service and process-state
extension. No PackageManager signature rule or original verifier is changed.

The process helper authenticates the captured Binder UID and resolves the pinned
camera process under ActivityManager locks before queueing work. It retains the
record, actual PID and start sequence and rechecks them before mutation. Remote
one-way calls have no calling PID, as described in the
[Android Binder API](https://developer.android.com/reference/android/os/Binder#getCallingPid()).

## Implemented behavior and limits

`getVerifyResult` delegates to the complete original verifier. `getSystemStatusJson`
samples real platform and readable kernel measurements with the factory field
names and current named `Debug.MEMINFO_*` indices. Missing measurements are
omitted. Prelaunch history is not synthesized from camera client events; the
sampler has a real launch-event entry point whose producer is still unintegrated.

`adjBoost`, the observed camera event IDs 0/3/4/7/8, and postprocessing completion
use the authored temporary process-cap policy. That policy must be built into
`services.jar` through patch 0031. `reportMemPressure` matches the factory's
measured immediate-return implementation. The sole OOM contribution ends on
camera close; it does not model work that continues after close. Postprocessing
completion can remove an explicit cap requested after close. It does not release
native performance handles or implement the factory reclaim transitions.

The other 22 Binder methods remain explicitly unported. Four of them have
concrete app paths: `boostCameraByThreshold`, `reclaimMemoryForCamera`,
`notifyCameraPerformanceTime`, and `updateCloudData`. Their requested policies
must not be guessed from the existence of similarly named platform APIs. Each
unported operation throws `UnsupportedOperationException`, increments a bounded
diagnostic counter, and logs at a bounded rate. For one-way Binder commands the
exception is a server-side diagnostic; it is not a caller-visible negative
acknowledgment. Successful transport or capture therefore does not establish a
complete CameraOpt implementation.

The original app's direct native performance calls and separate CameraOpt
socket client are outside this Binder interface. Native symbol compatibility,
system-server library namespaces, original cache initialization and input
access still need real build/boot evidence. A present service and a completed
boot callback do not prove a true verifier result. A native boot-hook linkage or
runtime failure is retained as an unavailable state and makes verification
requests throw; it never becomes an acceptance result or a cached Boolean
replacement. Failed startup tears down its worker and process-policy observer.

## Class ownership

The compile-only declarations are `libs` dependencies, never `static_libs` or
installed modules. They exist because a DEX-only import cannot supply javac
headers. The complete factory JAR and authored service JAR are ordered after
`services.jar` in the normal system-server classpath. The process helper belongs
to `services.jar`, where its ActivityManager package access and locks are owned.

The retained factory JAR already overlaps the platform in five Android HIDL
base classes. The artifact contract pins that measured set; it permits no new
factory/platform duplicates. These old overlaps still need runtime linkage
validation and are not replaced by copied factory classes.

`verify_artifacts.py` checks actual DEX class definitions and ZIP-member bytes.
It rejects a changed factory payload, leaked compile-only declarations, an
unexpected adapter class, a missing process helper, duplicate classpath entries,
or incorrect JAR dependency order. ZIP compression and alignment may change
while member contents remain identical.

After building, pass the exact original input JAR, its packaged runtime JAR, the
authored service JAR, packaged `services.jar`, and a JSON list extracted from the
actual system-server classpath metadata:

```sh
python3 device/xiaomi/nezha/cameraopt-service/verify_artifacts.py \
  --contract config/nezha-cameraopt-service.json \
  --original-input ORIGINAL_MIUI_CAMERAOPT_JAR \
  --original-runtime PACKAGED_MIUI_CAMERAOPT_JAR \
  --adapter PACKAGED_NEZHA_CAMERAOPT_SERVICE_JAR \
  --services PACKAGED_SERVICES_JAR \
  --classpath-json EXTRACTED_SYSTEMSERVER_CLASSPATH_JSON
```

The offline tests exercise product selection and artifact rejection. Host
compilation, a platform module build, enforcing service startup, original
verification, actual caller behavior and saved camera outputs are separate
validation steps. Keep unsupported API counts and source-read failures with
camera acceptance evidence, including each RAW, high-resolution, Ultra HDR,
video and auxiliary-camera result.

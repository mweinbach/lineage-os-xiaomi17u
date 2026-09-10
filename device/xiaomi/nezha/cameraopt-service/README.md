# CameraOpt service candidate

This selected source candidate publishes the factory `cameraopt` Binder protocol
through an authored system service. The unchanged `miui-cameraopt` JAR remains
the sole runtime owner of its interface, native loader, complete `Verifier`
and configuration loader. The verifier still checks the camera package through
the real `PackageManagerInternal`, then consults the original native cache. Its
original boot-completion hook runs at phase 1000.

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
native performance handles.

### The four app-reachable methods (patch 0040)

The camera application reaches four more methods: `reclaimMemoryForCamera`
before every photo and video session, `boostCameraByThreshold` for 4K, 8K,
200 MP and master-live modes, `notifyCameraPerformanceTime` after timed
operations, and `updateCloudData` when its cloud configuration changes. Their
factory implementations were read from the retained bytecode and the device's
own encrypted reclaim tables, which the factory `JsonDisptcher` decodes through
its JNI. The service loads those tables with that loader at startup, registers
for the `CameraReclaim` section, and hands it to `NezhaCameraReclaimPolicy` in
`services.jar`.

| Method | Factory behavior | This port |
| --- | --- | --- |
| `reclaimMemoryForCamera` | Once per `duration_reclaim_capture`, the capture scene of the reclaim table: kill background processes until the memory gap closes, then a low-free reclaim | Same table, same spacing, same gap arithmetic; kills through `ProcessRecord.killLocked`, reclaim through the cgroup v2 root `memory.reclaim` and `CachedAppOptimizer` compaction |
| `boostCameraByThreshold` | Nonzero levels select the video-switch, 200 MP, live-motion or Dolby scene and record the mode level; zero drives the vendor performance wrapper | Same scene selection and table; zero stays unported and counted |
| `notifyCameraPerformanceTime` | Logs the event; the watcher behind `persist.miui.camera.perfwatcher.enable` is off by default | Retains the last 32 events for dumps; an enabled watcher is counted as unported |
| `updateCloudData` | Writes `persist.vendor.camera.cloud.*` properties, merges newer tables through `JsonDisptcher`, refreshes the memory reserve | Bounded property writes (vendor policy decides, denials are counted), the same dispatcher merge, memory-reserve keys counted and not applied |

`NezhaCameraReclaimPlanner` is the pure decision logic and is exercised on a
host JVM by `scripts/test_nezha_cameraopt_reclaim.py`. Deviations from the
factory are deliberate and visible in dumps: kills never go below the
service-B adjustment band even when the table's low-memory escalation asks
for adjustment 0, at most eight processes die per batch, processes with
foreground services, visible activities, the home process and isolated
processes are never candidates, and the factory's lmkd command set, MIUI
process list, PSI monitor scenes (`kill_once`) and memory-reserve writes are
not reproduced. The factory memcg v1 `memory.reclaim_once` node does not exist
on this cgroup v2 build; the root `memory.reclaim` file is the equivalent.

The other 18 Binder methods remain explicitly unported. Their requested
policies must not be guessed from the existence of similarly named platform
APIs. Each unported operation throws `UnsupportedOperationException`,
increments a bounded diagnostic counter, and logs at a bounded rate. For
one-way Binder commands the exception is a server-side diagnostic; it is not a
caller-visible negative acknowledgment.

The original app's direct native performance calls and separate CameraOpt
socket client are outside this Binder interface. A present service and a
completed boot callback do not prove a true verifier result. A native boot-hook
linkage or runtime failure is retained as an unavailable state and makes
verification requests throw; it never becomes an acceptance result or a cached
Boolean replacement. Failed startup tears down its worker and both policies.

## Class ownership

The compile-only declarations are `libs` dependencies, never `static_libs` or
installed modules. They exist because a DEX-only import cannot supply javac
headers. The complete factory JAR and authored service JAR are ordered after
`services.jar` in the normal system-server classpath. The process and reclaim
helpers belong to `services.jar`, where their ActivityManager package access
and locks are owned.

The retained factory JAR already overlaps the platform in five Android HIDL
base classes. The artifact contract pins that measured set; it permits no new
factory/platform duplicates. These old overlaps still need runtime linkage
validation and are not replaced by copied factory classes.

`verify_artifacts.py` checks actual DEX class definitions and ZIP-member bytes.
It rejects a changed factory payload, leaked compile-only declarations, an
unexpected adapter class, a missing process or reclaim helper, duplicate
classpath entries, or incorrect JAR dependency order. ZIP compression and
alignment may change while member contents remain identical.

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

The offline tests exercise product selection, artifact rejection, the patch
against its templates and the planner on the host JVM. Host compilation, a
platform module build, enforcing service startup, original verification,
actual caller behavior and saved camera outputs are separate validation steps.
Keep unsupported API counts and source-read failures with camera acceptance
evidence, including each RAW, high-resolution, Ultra HDR, video and
auxiliary-camera result.

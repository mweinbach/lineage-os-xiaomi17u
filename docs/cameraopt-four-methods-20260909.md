# CameraOpt: the four app-reachable methods, September 9, 2026

**The four CameraOpt Binder methods the Xiaomi camera reaches during ordinary
use, `reclaimMemoryForCamera`, `boostCameraByThreshold`,
`notifyCameraPerformanceTime` and `updateCloudData`, now have real
implementations in the authored service, built from the factory bytecode and
the device's own encrypted reclaim tables.** Source revision 14 builds
`services.jar` and the adapter JAR with them; the host planner harness passes
78 checks. Nothing on this page is a device result: the phone still runs v15,
where these four calls are counted as unsupported, and the prepared v16
bundle below waits for your installation approval. The
[completion record](camera-completion-20260907.md) describes the state before
this work; the CameraOpt service itself is described in
`device/xiaomi/nezha/cameraopt-service/README.md`.

## What the factory does

The retained `miui-cameraopt.jar` and the camera APK were read again for the
four call paths. Every claim below comes from that bytecode, not from the names
of similar platform APIs.

| Method | App call sites | Factory server path |
| --- | --- | --- |
| `reclaimMemoryForCamera(long, int, int)` | Photo capture (mode 163) and video session start (mode 162), the last two arguments always −1 | `ReclaimManager.notifyCameraStatusChanged(9, …)`: once per `duration_reclaim_capture` (60 s), the `miuicam_capture_event` scene of the reclaim table |
| `boostCameraByThreshold(long)` | 4K video (0x101), 8K video (0x102), 200 MP capture (0x201), master-live mode (0x202); the wrapper never sends zero | `ReclaimManager.boostCameraByModeLevel`: the level selects the video-switch, 200 MP, live-motion or Dolby scene and is remembered until the camera closes. The zero level, which drives Xiaomi's performance wrapper and a delayed system-server GC, is unreachable from the app |
| `notifyCameraPerformanceTime(String, String, long)` | The app's performance manager after timed operations | `CameraPerfWatcher.k`: a log line, then nothing unless `persist.miui.camera.perfwatcher.enable` is set |
| `updateCloudData(double, String)` | The app's cloud configuration module, `camera_booster` key | `CameraCloundSync.updateCloudData`: `persist.vendor.camera.cloud.<module>.<key>` properties, `JsonDisptcher.updateCloudData` for newer versions, and a memory-reserve refresh |

The reclaim tables live in `/system_ext/etc/cameraopt_reclaim.json` and the
`odm` overlay, encrypted; only the factory JNI decodes them. A read-only helper
run on the phone asked the factory JAR to decode all eleven CameraOpt tables so
the port could be checked against the real numbers. For the scenes above the
table configures two actions: `kill_target`, which frees a computed memory gap
by killing background processes ordered by recent-task history and footprint,
and `reclaim_once`, which asks the kernel to reclaim a target amount and then
compacts cached processes. The gap is the larger of a quarter of RAM minus
MemAvailable and the scene's free-memory target minus MemFree; the capture
scene's target is 400 MB free. The table's nominal kill threshold is the
service-B adjustment band (800), lowered to 0 for the Xiaomi camera whenever
MemFree drops under 600 MB.

## What was built

- `NezhaCameraReclaimPlanner` (services.jar, patch 0040): parses the
  `CameraReclaim` section the way the factory parsers do, including the
  `low:high` trigger ranges where −1 is unbounded, and produces kill and
  reclaim plans from synthetic-friendly inputs. No Android service reference.
- `NezhaCameraReclaimPolicy` (services.jar, patch 0040): samples memory,
  pressure and board temperature, reads the LRU process list under the AMS
  locks, revalidates every victim before `ProcessRecord.killLocked`, requests
  compaction through `CachedAppOptimizer.compactApp`, and writes the cgroup v2
  root `memory.reclaim` file. The factory memcg v1 `memory.reclaim_once` node
  does not exist on this build.
- The service loads the tables through the factory `JsonDisptcher` at startup
  and registers for the `CameraReclaim` section, so no decoded table is shipped
  and cloud merges follow the factory version rule. The `properties` module of a
  cloud update is written with bounded names and values; vendor policy owns the
  property type, so a denial is counted rather than hidden. The memory-reserve
  keys are counted and not applied.
- `notifyCameraPerformanceTime` keeps the last 32 events in the dump. The
  enabled watcher is unported and is counted when the property asks for it.

Deviations from the factory, all visible in `dumpsys cameraopt`:

| Factory | This build | Why |
| --- | --- | --- |
| Kill threshold escalates to adjustment 0 under 600 MB MemFree | Floor at the service-B band; escalations counted | MemFree is routinely low here without the factory memory daemons, so the escalation would reach visible processes on almost every capture |
| No bound on kills per scene | 8 per batch, 16 compactions per pass | Authored safety bound |
| MIUI process list, lmkd command set, PSI monitor scenes (`kill_once`), memory-reserve writes, intercept-restart hook | Not reproduced | Absent services; the remaining behaviour is documented as unported |
| Foreground services, visible activities, home, persistent and isolated processes classified by MIUI lists | Never candidates | The AOSP equivalents are read lock-free from the process record |

## Evidence

| Check | Result |
| --- | --- |
| Host planner harness (`scripts/test_nezha_cameraopt_reclaim.py`) | 78 checks: range parsing, capture spacing, gap arithmetic, floor, exclusions, ordering, white-list thresholds, reclaim and compaction gates |
| Offline suite before the source revision | 980 focused, 4,957 full, green |
| Source revision 14 | `nezha.b0cd50c12a3abae1bb26c3ff`, 707 rows, nine changed files |
| Guest component build | `services`, `nezha-cameraopt-service` and the compile stubs built; services.jar defines both reclaim classes, the adapter JAR defines only its own classes and leaks no factory declaration |

The phone-side decode of the tables is private evidence under
`evidence/cameraopt-config-20260909/`; the tables are Xiaomi's and are not
reproduced here beyond the values needed to explain the port.

## Delivery set v16 (prepared, not installed)

The host stages ran as for v15 and every gate passed. Nothing was flashed;
the bundle needs your separate approval bound to its manifest hash, and it
carries both this port and the [camcorder profile selection](camera-video-profiles-20260909.md).

| Item | Value |
| --- | --- |
| Build identity | `nezha.434625bd9b5cd7a8a7eabd84` (userdebug, source revision 15, 708 rows) |
| Unsigned archive | SHA256 `f443a103f228d43e13c9fc64e8fcdbbd74558b4000258820170105bea8514909`, 11,324,330,533 bytes |
| Measured system_ext | 793,632,768 bytes, 20,480 more than v15; admitted through the cascade |
| Reconciled signed archive | SHA256 `734c22b58e13ea3c0bc1c8c6f0b28139dc4f96ddf5b2b37a53aa5e40ce7e323c`, 11,146,542,546 bytes |
| Super | SHA256 `f79ed975acbbbfbfaa9144394358877d1db01e4749a783504a1fb55dc0a95612`, 9,477,851,248 bytes |
| Bundle | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v16/`, manifest SHA256 `5c57a12ff14d98349742ce59e6214d2ab2377c0c5e18edc2265b9b27b7188c3d`, eight payloads, byte identities verified |
| Guest gates | `framework-res` still compiles `config_screenBrightnessDimFloat` = 0.05; TeleService still compiles `config_ims_mmtel_package` = `org.codeaurora.ims` |
| Host gates | 16 checks on the unsigned archive and the same 16 on the signed archive: the stock `media.settings.xml` line once in the system build.prop and no profile-variant override, CameraOpt artifact ownership over the packaged system-server classpath (factory JAR bytes, clean adapter, both reclaim classes in services.jar, five known HIDL duplicates only), dexpreopt outputs, the CameraOpt selector property, the IMS APK bytes, domain, mapping and selector, no permissive domain, unchanged calibration XML, display packet delivery |
| Tests during admission | 994 focused, 4,971 full, both green |
| Release checker | every stage recognized for this identity |

The v15 set stays on the host until v16 is installed and recorded; the
retention rule then removes v15.

## What this does not prove

No kill, compaction or reclaim has run on the phone. The service has not
started with the new code, the factory loader has not been exercised inside
system_server, and the app's four calls have not been observed against it.
Whether the capture scene helps or hurts the camera on this build is a device
question for the next delivery set.

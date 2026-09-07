# Camera experiment with root on the userdebug opt-in build (2026-09-07)

Record: `research/camera-root-experiment-20260907.json`. Build
`nezha.cc551b14bc2cc72c2b138bb0` (userdebug opt-in, delivery set v5), SELinux
enforcing, `ro.debuggable=1`. The phone was accessed with explicit user
authorization for flashing and adb use.

**Interpretation correction:** the later
[offline library analysis](camera-library-analysis-20260907.md) supersedes
the raw CamX probe-status attribution below. CHI checks logical-camera XML
IDs, and the retry message reports the initial budget, not exhausted retries.
The experimental outcomes and historical phone state below are unchanged.

## What was verified

- **Root works on the diagnostic build.** `adb root` yields uid 0 in
  `u:r:su:s0` once the Lineage "Rooted debugging" gate is enabled, and the
  userdebug `su` binary gives the shell uid 0. Three blockers were removed in
  order: the debuggable flag (any non-empty value counts as set), the missing
  `adb_root` gate service (`WITH_SU=true`), and this repository's removal of
  `permissive su`, which made adbd abort on its context switch and `su` fail
  its setgid silently. See the [build-variant opt-in record](build-variant-opt-in-20260906.md).
- **Clearing persisted camera state does not fix the camera.** Every
  `persist.vendor.camera.*` entry was removed from the persistent property
  store and the vendor camera cache was moved aside before a reboot. The HAL
  came back with the same three devices and one usable logical camera, the
  same four "sensor probe fail" verdicts for roles 1, 0, 21 and 20, one
  provider abort and two stream-configuration failures, and it regenerated
  `sensorffrlist=1,0,21,20` and `mi.module.info=…=none` on the clean start.
- **The kernel and CamX probe the sensors successfully.** The camera driver
  logs "Probe success" for all four sensors, CamX logs "Probe EEPROM success"
  for all four modules, and Xiaomi's immune system records probe successes.
  The CHI's "sensor probe fail" verdict comes from CamX's per-sensor probe
  status after static-caps initialisation, not from the I2C probe.
  *(Superseded on 2026-09-07: the verdict is a logical-camera XML-id lookup in
  the CHI, see the [XML selection record](camera-xml-selection-20260907.md).)*
- **The boot chain matches stock where it was compared.** The flashed boot
  image carries the same Google GKI kernel as both stock packages, the DTB is
  byte-identical, and the vendor ramdisk differs only in the first-stage
  fstab, where the mi_ext bind mount and its product/system overlays are
  deliberately absent. Vendor and ODM are the same HyperOS build.

## Open leads, not device-admitted

- The camera driver reports three `cam_vfe_hw_init: inval param` errors and
  "no valid SFE HW devices" at module load, and the ICP firmware fails its
  IPC channel setup. Whether stock HyperOS shows the same lines is unknown;
  no stock boot log exists.
- Xiaomi's diagnostic layer expects tele role 23 while the CHI table uses 20
  and reports a role-map parse error.
- CamX's per-sensor probe counts are info-level and stayed hidden: log-mask
  keys in the `/data/vendor/camera` override file parse to zero on this
  vendor build, so a different logging route is needed.

## Stock package exploration (2026-09-07)

The factory China package (`d2cf57fd…`) was compared against the flashed
build offline and, with root, against the phone. Identical to factory: the
kernel bytes, the DTB, the DTBO table (only our AVB footer differs), the vendor
ramdisk apart from the intentionally dropped mi_ext fstab entries, both DLKM
module sets, the mi_ext image, and every file of the vendor and ODM trees
except the regenerated SELinux policy files. Different from factory: the
vendor_boot cmdline lacks `swinfo.fingerprint` (consumed only by the swinfo,
bootmonitor and mtdoops modules); mi_ext is not mounted so its build.prop never
loads; 26 keys of the identical vendor/ODM build.prop files never load because
`vendor_init` is denied `set` under our platform policy; `ro.build.tags` is
`test-keys`; and Xiaomi's system-side camera components (CameraMind, the
cammsger and cameraopt init scripts, their configs) are absent.

Every runtime experiment based on those differences was negative: setting the
mi_ext and vendor_init-denied properties, opening the camera messenger nodes,
a provider start with SELinux permissive, blanking the probe history, and every
attempt to raise CamX log masks (data override, property, bind-mounted vendor
override, the unrelease switch). The HAL regenerates the fail list on every
provider start. Binary analysis shows the CHI's damage routine marks an XML
entry damaged when no CamX camera record matches it, and CamX's static-caps
loop only reports its retry summary because `libcamlog` mutes info logs on
`test-keys` builds and MP hardware.

Still unproven: whether the ISP init errors and the probe error occur on stock
HyperOS. Slot B holds a boot chain but the super image carries one logical
copy, so a stock boot for comparison needs a stock super flash. Extractions,
inventories, pulled vendor libraries and comparison outputs stay under the
ignored `artifacts/camera-analysis/`.

## Reverse engineering the camera HAL (2026-09-07)

With root, the provider was traced at the syscall level (strace), sampled
(simpleperf), and instrumented with kernel uprobes that capture arguments and
user stacks, and its vendor libraries were disassembled in the guest. Findings:

- **The fail list is an output, not an input.** A property-set uprobe with
  stack capture shows `sensorffrlist=1,0,21,20` and `mi.module.info=…=none` are
  written by the HAL during enumeration (through `camera.qcom.so`,
  `libmicamera_adapter`, `libmicamera_hal_core` and the CHI extension module).
  They are recomputed and rewritten on every provider start, which is why
  clearing them never helped.
- **CamX enumerates all four sensors.** A uprobe in the CHI's hardware pass
  shows `ChiContextInterface::GetCameraInfo` (the per-sensor CamX query, distinct
  from the logical `ExtensionModule::GetCameraInfo` the damage routine reads)
  succeeds for physical camera indices 0 to 3, and the
  generated-camera pass evaluates eight distinct definitions (ten lookup
  events; MultiCamera contributes three) against available slots {0,1,2,3};
  the three front definitions request slot 4. The probe fires before the
  search executes, so it records arguments, not matches. The kernel logs probe success for all four sensors
  on every restart.
- **The collapse is in Xiaomi's role map.** `buildCameraRoleIds` produces
  `mLogical2RoleCameraMap [4,0,0,64,2,3PartSat]`, one logical camera at role 64,
  and `addDamagePyhCameraRoleIds` marks the four per-lens roles unavailable
  because no built logical-camera record matches each XML entry's expected id.
  Xiaomi's diagnostic layer expects tele at role 23 while the table uses 20, and
  logs a role-map parse error.
- **The known gates are inert.** The device-protection kernel skip switches
  (`/sys/module/camera/parameters/xm_cam_dev_probe_skip_*`) are both zero. The
  table-selection inputs `ro.boot.camera.config` and `persist.vendor.camera.mapid`
  are empty, and setting them at runtime changed nothing.

Because the XML table library and the sensor-module binaries are byte-identical
to stock, the divergence was first attributed to CamX's per-sensor
static-caps and the kernel/firmware init errors. **That attribution is
superseded**: the missing system property `ro.vendor.qti.va_aosp.support`
switches the CHI to the GSI logical-camera table, which explains the XML-id
mismatch without any hardware fault; see the
[XML selection record](camera-xml-selection-20260907.md). The kernel messages
remain unexplained observations.

An aarch64 `lldb-server` from the tree prebuilts is staged on the phone at
`/data/local/tmp/lldb-server` for future live debugging; it attached but its
gdb handshake did not complete this session, so kernel uprobes were used.

## Magisk detour

At the user's request a Magisk v30.7 route was tried between the root fixes.
A patched init_boot flashed with a verification-disabled vbmeta did not boot;
`fastboot boot` of a boot image carrying the Magisk ramdisk booted normally
without Magisk because this header-v4 device takes its ramdisk from
init_boot. The signed images were restored and verified booting. The Magisk
manager app remains installed and inactive.

## Phone state at the end

Slot A runs the signed v5 userdebug package with root enabled, the diagnostic
override file removed, and userdata untouched apart from the cleared vendor
camera properties (the HAL rewrote them) and the moved cache directory
`/data/vendor/camera.pre-clear-20260906`.

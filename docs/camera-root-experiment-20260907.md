# Camera experiment with root on the userdebug opt-in build (2026-09-07)

Record: `research/camera-root-experiment-20260907.json`. Build
`nezha.cc551b14bc2cc72c2b138bb0` (userdebug opt-in, delivery set v5), SELinux
enforcing, `ro.debuggable=1`. The phone was accessed with explicit user
authorization for flashing and adb use.

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

# Camera logical-XML selection and the QTI framework flag (2026-09-07)

**Measured on this build: the property that selects the Nezha camera table is
absent.** Stock HyperOS sets `ro.vendor.qti.va_aosp.support=1` in its system
build.prop; the flashed build (`nezha.cc551b14bc2cc72c2b138bb0`) has no such
property, while `ro.build.product` is `nezha` and the SoC id is 660. In the
pinned CHI override those three inputs select the `kaanapali_gsi.xml`
logical-camera table instead of `nezha.xml`. The offline analysis below was
then confirmed by an authorized runtime test the same day (see
[Runtime result](#runtime-result-measured-2026-09-07)): setting the flag makes
the CHI select `nezha.xml` and enumerate nine camera devices with no damage
verdicts, and the fix built into the v6 system image reproduces that from
first boot. Capture is not yet confirmed and no camera fix is device-admitted.
The sanitized [record](../research/camera-xml-selection-20260907.json) pins
every input hash, address and measured count.

## Measured facts

- **Property state.** The device property capture taken on this build
  (2,467 lines, SHA256 `782c74fa…`) contains `ro.vendor.qti.va_odm.support=1`
  (loaded from the byte-identical ODM image) but no
  `ro.vendor.qti.va_aosp.support`. The factory system build.prop (SHA256
  `2c2811af…`) sets it to 1 at line 197 under the comment
  "System Enable QCOM enhanced feature".
- **Detector semantics, from source.** The tree carries
  `hardware/qcom-caf/common/fwk-detect/vndfwk-detect.c`:
  `isRunningWithVendorEnhancedFramework()` returns 1 exactly when
  `property_get_bool("ro.vendor.qti.va_aosp.support", false)` is true. The CHI
  override lists `libqti_vndfwk_detect.so` as a direct dependency.
- **Branch, verified in the pinned binary.** SoC 660 (0x294) indexes the jump
  table at `0x11279b` to byte 0, landing at `0x4e5750`. The calls at `0x4e5754`
  and `0x4e575c` test the two predicates; when both return 0, `0x4e5764` loads
  the string at `0xd09fe`, which is `kaanapali_gsi.xml`, and `0x4e56e0` assigns
  it into the auxiliary settings object. The picker call at `0x4f70cc` receives
  that string in `x1`. The library's executable segment has file offset equal
  to its virtual address, so these values double as uprobe offsets.
- **Loader.** AOSP init loads system build.prop keys as the `init` context
  and our built platform policy allows init to set every property type; the
  key resolves to `vendor_default_prop`, a context the provider already opens
  successfully in the retained syscall trace.
- **Retained slot trace, reread.** The retained capture holds ten lookup
  events across eight distinct definitions (MultiCamera contributes three),
  with available slots {0,1,2,3}; the three front definitions request slot 4.
  That probe sits before `wmemchr` runs, so it records search arguments, not
  matches, and the retained built-camera probe recorded zero hits.

## Hypothesis

The GSI table's eight definitions carry implementation ids of the form
`0x0f1000xx` and place the front sensor at slot 4. On this four-sensor device
none of them satisfies Xiaomi's expected XML ids 1 to 4, so the role map keeps
only the three-sensor logical camera and reports the four per-lens roles as
damaged. Restoring the factory flag from the system image should make the
CHI keep `nezha.xml` (thirteen definitions) and build the per-lens cameras.
Written before the runtime test; the enumeration half is now measured below.

## Candidate fix (prepared; built as the v6 delivery set, see below)

`device/xiaomi/nezha/qti-value-add-framework.mk`, selected by
`NEZHA_QTI_VALUE_ADD_FRAMEWORK := true`, adds
`ro.vendor.qti.va_aosp.support=1` to `PRODUCT_SYSTEM_PROPERTIES`, the same
partition and value as the factory build. It is off by default and bound by
`config/nezha-qti-value-add-framework.json` with a make-driven test. The flag
is global: 153 vendor and 17 ODM files link the detection library, including
the Bluetooth HAL, connectivity engine, IMS and GNSS helpers. Stock runs all of
them with the flag set, but their behaviour on this framework is unverified,
so the acceptance checks include them. The damage verdict itself is not
patched and no camera ids are rewritten.

## Runtime test plan (needs authorization for each device step)

Device: `adb -s 32c100d6` only. Read-only precheck first:

```sh
adb -s 32c100d6 shell 'getprop ro.build.version.incremental; getprop ro.vendor.qti.va_aosp.support; getprop ro.build.product; getprop ro.vendor.qti.soc_id; getenforce; id'
```

Control run (arms tracing and restarts the provider):

```sh
adb -s 32c100d6 shell 'T=/sys/kernel/tracing; L=/vendor/lib64/hw/com.qti.chi.override.so
echo 0 > $T/tracing_on; echo 0 > $T/events/enable; echo > $T/uprobe_events
echo "p:cam/vef $L:0x4e5758 vef=%x0:u32" >> $T/uprobe_events
echo "p:cam/gsi $L:0x4e5760 gsi=%x0:u32" >> $T/uprobe_events
echo "p:cam/xml $L:0x4f70cc name=+0(%x1):string" >> $T/uprobe_events
echo "p:cam/slot $L:0x4e7db8 name=+0(+0(%x19)):string slot=%x1:u32 n=%x2:u32 a0=+0(%x0):u32 a1=+4(%x0):u32 a2=+8(%x0):u32 a3=+12(%x0):u32 a4=+16(%x0):u32" >> $T/uprobe_events
echo 1 > $T/events/cam/enable; echo > $T/trace; echo 1 > $T/tracing_on
stop vendor.camera-provider; sleep 2; start vendor.camera-provider; sleep 15
echo 0 > $T/tracing_on; cat $T/uprobe_profile; grep -a -v "^#" $T/trace
dumpsys media.camera | grep "Number of"; logcat -d | grep -a "addDamagePyhCameraRoleIds\|mLogical2RoleCameraMap"'
```

Expected: `vef=0`, `gsi=0`, `name="kaanapali_gsi.xml"`, eight definitions,
front slot 4, the four damage lines.

Change run (writes one read-only property for this boot, then restarts):

```sh
adb -s 32c100d6 shell 'setprop ro.vendor.qti.va_aosp.support 1; getprop ro.vendor.qti.va_aosp.support'
# then the control-run block again
```

Expected: `vef=1`, `name="nezha.xml"`, thirteen definitions, no damage lines,
a higher device count. Cleanup: clear `uprobe_events`, disable the `cam` events
and `tracing_on`. The property cannot be unset until the next reboot; that is
a recorded state, and no reboot is part of this plan.

## Runtime result (measured 2026-09-07)

The user authorized the plan above on the installed userdebug build
(`nezha.cc551b14bc2cc72c2b138bb0`, root shell, SELinux enforcing throughout).
Both runs used the same uprobes and the same provider restart; the property
write is volatile and clears at the next reboot. Raw traces stay under the
ignored evidence directory of the v5 install.

| Probe or count | Control run (flag absent) | Change run (`setprop ro.vendor.qti.va_aosp.support 1`) |
| --- | --- | --- |
| `isRunningWithVendorEnhancedFramework()` (`0x4e5758`) | 0 | 1 |
| `IsGSIVersion()` (`0x4e5760`) | 0 | not reached (short-circuited) |
| Selected XML at the picker (`0x4f70cc`) | `kaanapali_gsi.xml` | `nezha.xml` |
| Slot lookups (`0x4e7db8`) | 10 over 8 definitions, front slot 4 | 29, including Wide, Tele, Ultrawide and FrontLogicalCamera |
| `dumpsys media.camera` devices | 3 | 9 (2 normal, 7 auxiliary) |
| `addDamagePyhCameraRoleIds` lines | 4 | 0 |
| `persist.vendor.camera.sensorffrlist` after start | four failures | empty |
| `persist.vendor.camera.module.info` after start | empty | populated (`back_main`, `back_tele`, ...) |

This measures the selection and enumeration half of the hypothesis: the flag
alone switches the table and removes every damage verdict. Reboot-persistence
needs the flag in the system image, which is what the v6 build carries.

**Capture is not confirmed.** With nine devices enumerated, opening the Xiaomi
camera app aborted the provider once: `get InternalStreamConfigInfo failed,
fwkOpMode:0x9005, roleId:64` raised in `libmicamera_hal_policy.so`
(`DeviceSessionPolicy::buildVendorConfiguration`) from
`mihal::Session::configureStreams`. The provider respawned, cameraserver
re-added all nine devices, and no further crash occurred. That is a
stream-configuration failure in the Xiaomi session policy for the app's
vendor operating mode, distinct from the enumeration failure fixed here, and
it is unexplained. Aperture verified lens facing through CameraX but opened no
device within a 25 second window, logged no error, and saved nothing; its
behaviour on the flashed build is the next check. The MIUI app also reports
an unrelated missing `com.miui.cameraopt` native library.

## Build and delivery (v6, flashed 2026-09-07)

The sixth guest transaction installed the fragment, the device.mk include and
the product selector on top of the permissive-su userdebug source (identity
`nezha.e2b55ae5f0effd944736a6b0`, 604 verified inputs, receipt SHA256
`e02f13349063f394…`). The incremental userdebug target-files build placed
`ro.vendor.qti.va_aosp.support=1` at line 123 of the packaged system
build.prop. The package was admitted (system_ext unchanged in size, new
identity), signed with the host AVB profile, bundled as
`artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v6/` (manifest
SHA256 `324553474d6c6d06…`, reconciled archive `884a62bcdf519b72…`)
and written to slot A over the same shared-super route as v5: eight writes
acknowledged, no wipe, no slot change, reboot, boot completed in
25.4 seconds as `userdebug` with `ro.debuggable=1`, adb root working.
The v5 bundle is retained as rollback evidence.

Acceptance on the flashed build, 62 seconds after boot and without any
runtime property write:

| Check | Result |
| --- | --- |
| `ro.vendor.qti.va_aosp.support` | 1, from `/system/build.prop` line 123 |
| SELinux | Enforcing |
| `dumpsys media.camera` | 9 camera devices, 2 normal, 2 public to API1 |
| `addDamagePyhCameraRoleIds` lines since boot | 0 |
| Provider crashes since boot, through both app sessions | 0 (same provider pid throughout) |
| `persist.vendor.camera.sensorffrlist` / `module.info` | both empty at that point |
| Aperture | verified lens facing, opened no device in 12 s, no photo, no error |
| Xiaomi camera app | connected device 5 and disconnected within the same second; no provider abort this time; the `com.miui.cameraopt` UnsatisfiedLinkError persists; no photo |

Enumeration is therefore fixed from the image and survives reboot. Capture is
still not confirmed by either app, so no camera fix is device-admitted. The
next checks are the reasons Aperture does not open a device and why the
Xiaomi app releases device 5 immediately (its missing `cameraopt` native
library on this framework is the first candidate); the earlier roleId 64
abort did not recur in this single attempt and remains unexplained.

## Acceptance checks for a fix

Enumeration alone is not a camera fix. Before and after: the effective selected
XML; physical sensor count and slot mapping; built logical XML ids and Xiaomi
roles; public versus auxiliary camera counts; front, wide, ultrawide and tele
capture in both camera apps; stream configuration, lens switching and provider
crash-free operation; SELinux enforcing; and Bluetooth, IMS and connectivity
unchanged, since they read the same flag.

## Corrections to earlier records

The [root experiment](camera-root-experiment-20260907.md) record's inference
that the divergence sits in CamX static-caps or at the kernel and firmware
layer is superseded: the "sensor probe fail" verdict is a logical-camera XML-id
lookup failure computed by the CHI, the retry line is a budget printed before
processing, and CamX's per-sensor `ChiContextInterface::GetCameraInfo` is a
different function from the logical `ExtensionModule::GetCameraInfo` the
damage routine reads. The VFE/SFE/ICP kernel messages remain unexplained
observations, not a proven cause.

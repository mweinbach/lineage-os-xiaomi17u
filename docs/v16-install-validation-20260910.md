# V16 installation and validation, September 10, 2026

**V16 (`nezha.434625bd9b5cd7a8a7eabd84`, source revision 15) is installed on
slot A, boots in 25.4 seconds with SELinux Enforcing and root ADB, carries the
four ported CameraOpt methods and the factory camcorder-profile selection, and
retained userdata.** You approved the install and test in one message ("ok why
don't you install and test this, and make sure that we can also use the cloud
leica processing for xiaomi M3/M9 and the leica modes are enabled on the
device"). The approval was bound to the bundle manifest before any phone write.
No SIM is inserted, so no IMS registration was attempted. The camera side is in
the [tier 2 v16 page](tier2-camera-v16-20260910.md).

## Installation

The read-only Android preflight found the expected v15 on slot A, unlocked and
encrypted, with no errors; the bootloader review found slot A, slot count 2, no
pending snapshot. The bundle was reverified against manifest
`5c57a12ff14d98349742ce59e6214d2ab2377c0c5e18edc2265b9b27b7188c3d`. The eight
writes over the shared Super were acknowledged in the fixed order (super in
242 s, then dtbo, init_boot, vendor_boot, recovery, boot, vbmeta_system,
vbmeta) with every payload rehashed identical afterwards. Slot A was observed
before every write and before the reboot. No wipe, slot change or data clear.
Android completed boot 25.4 seconds after the reboot as the v16 identity,
userdebug, debuggable; root ADB was re-established.

## Retained userdata

The eight-image write set contained no userdata or metadata partition and no
wipe was requested, so `/data` was preserved structurally. The account count is
unchanged from v15. The pre-install file counts were discarded as unreliable
(permission-denied noise inflated them); retention rests on the write set and
the stable account count.

## Camcorder profiles and CameraOpt

`media.settings.xml` reads `/vendor/etc/media_profiles_vendor.xml` and the
codecs variant resolves to `_canoe_v2`, so the platform loads
`media_profiles_canoe_v2.xml` (SHA256
`c1cf4365e3361ff1de384f338ff0681e98bb6ae3004c6da07c8de992e8b0b6c5`). `dumpsys
cameraopt` shows the configuration loaded (28 actions, 8 lists) and the reclaim
policy configured with the service property `ro.nezha.cameraopt.service` set.
Both ran on real camera use during the session.

## Device state

One property was changed during testing and restored: `ro.theme_customize` was
set to `LCC` to probe the Leica edition gate, which made the stock camera app
self-close. It is a read-only property that cannot be cleared from userspace,
so the phone was rebooted to reset it to the build's empty value. After the
reboot the property is empty, the camera app launches normally, and
`stay_on_while_plugged_in` was returned to its pre-session value of 0. The
phone was left asleep.

## Retention

The superseded v15 delivery set was removed after this install was recorded
(three directories, about 60 GB), keeping the v15 admission record. Host free
space rose to about 1.27 TiB. The
[structured record](../research/v16-install-validation-20260910.json) holds the
writes, boot, authorization and retention detail.

## What this does not establish

No IMS registration, call or SMS (no SIM). Camera capability and quality are
measured separately in the [tier 2 v16 page](tier2-camera-v16-20260910.md).
Other hardware-ledger rows are unchanged.

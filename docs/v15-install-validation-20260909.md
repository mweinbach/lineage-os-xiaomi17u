# V15 installation and validation, September 9, 2026

**V15 (`nezha.81c1b93277a1fa371a3efbb3`, source revision 13) is installed on
slot A, boots in 25 seconds with SELinux Enforcing and root ADB, the IMS
provider runs in its restored domain and is bound by the telephony process,
and the keyguard dim now lands at a visible level instead of the panel
minimum.** No SIM is inserted, so no IMS registration was attempted or
expected. The QMI daemon was left alone at your request. This page records the
device side of the [tier 1 source work](tier1-ims-dim-20260909.md).

## Installation

You approved the flash in reply to the v15 recap ("you can flash, there is no
SIM"), and the approval was bound to the bundle manifest
`64e5741d37eabcee872d6a64553e4ba7e99442465396fe2190431172bc22f4ed` before any
phone write. The read-only Android preflight found the expected v14 on slot A,
unlocked and encrypted, with no errors; the bootloader review found slot A,
slot count 2, no pending snapshot. The bundle was reverified. The eight writes
over the shared Super were acknowledged in the fixed order (super in 242 s,
then dtbo, init_boot, vendor_boot, recovery, boot, vbmeta_system, vbmeta) with
every payload rehashed identical afterwards. Slot A was observed before every
write and before the reboot. No wipe, slot change or data clear. Android
completed boot 25.4 seconds after the reboot command as the v15 identity,
userdebug, debuggable; root ADB was re-established for diagnostics.

## Observed after boot

| Check | Observed |
| --- | --- |
| Identity | `nezha.81c1b93277a1fa371a3efbb3`, slot `_a`, `sys.boot_completed=1`, `userdebug`, Enforcing, adb uid 0 |
| IMS package | `/system_ext/priv-app/ims/ims.apk`, bytes identical to the reviewed original; privileged system_ext app; `usesLibraries` resolve to the three registered libraries |
| IMS process | `org.codeaurora.ims` running as a persistent process in `u:r:vendor_qtelephony:s0`, uid 10377 with groups 1005 (audio) and 2901 (diag) from the group projection |
| IMS binding | `com.android.phone` holds a bound `ImsService` connection to `org.codeaurora.ims/.ImsService` |
| SELinux | 64 denial lines since boot, none for `vendor_qtelephony`; the rest are pre-existing `tee` and `gmscore_app` lines |
| Crashes | none in the crash buffer |
| Dim level | `config_screenBrightnessDimFloat` resolves to 0.05; framework `mBrightnessDim=0.05`; on the keyguard the display reached policy DIM after about eight seconds and the panel read 314 of 16383 (v14 read the minimum, 7) |
| Retained userdata | 1 account, 22 third-party packages, 153 media files, unchanged from the tier 0 counts |
| Camera | 9 HAL devices, camera provider and cameraserver running; `libimscamera_jni.so` is the same bytes the camera framework already shipped |
| Wi-Fi | enabled; radio still reports no SIM in either slot |
| QMI daemon | still restarting every five seconds, as expected and as agreed |

Payload readback on the phone: `ims.apk` SHA256 `56f10321…`, `lib-imsvt.so`
`44dbdad6…`, `libimscamera_jni.so` `9ed2022d…`, all equal to the reviewed
inputs.

## What changed on the phone during validation

The screen was woken once for the dim measurement and put back to sleep; no
setting was changed. A pre-install snapshot script mis-quoted two commands and
printed nonsense counts (789 packages, 4.1 million files); the post-boot
collector used correct quoting and matches the tier 0 numbers. The mistake is
recorded in the private receipts and does not affect any result.

## Retention

With v15 installed and recorded, the v14 signing set, bundle and transfer copy
were removed from the host (57.2 GiB). The v14 admission record stays; host
free space is 1.2 TiB.

## What this does not prove

No IMS registration, VoLTE call or IMS SMS: there is no SIM. The dim level was
measured on the panel readback, not by eye. The daemon loop, the brightness
transitions by eye, fingerprint, audio, sensors, power and the other ledger
rows remain the hands-on list from the [tier 0 record](hardware-ledger-v14-20260909.md).

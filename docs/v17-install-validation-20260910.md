# V17 install validation — always-on Leica Essential, September 10, 2026

**V17 (`nezha.11b0a26475073bca18f34c39`, source revision 16) is installed on
slot A. It is revision 15 (v16) plus one change: the guarded
`device/xiaomi/nezha/leica-essential.mk` fragment is now enabled
(`NEZHA_LEICA_ESSENTIAL := true`), which bakes `ro.theme_customize=LCC` and
`camera.debug.safe.check.disable=true` into the system `build.prop`. The Leica
M3/M9 "Leica Essential" mode is therefore on at boot, with no runtime resetprop
and no Magisk. The device keeps its real model, market name and attestation
identity.** The flash was explicitly authorized ("do it") after a recap that
named the plan and the route; the approval was bound to bundle manifest
`6230582068c8133487c10af7097be7ff10dc52cd29c1cf0f6177961df4819ec0` before any
phone write. The eight-image shared-Super slot-A write acknowledged every
payload rehashed identical, with no wipe and no slot change; userdata was
retained. The structured record is the
[install validation JSON](../research/v17-install-validation-20260910.json); the
gate analysis is in the [Leica Essential record](leica-essential-20260910.md).

## The write

| Image | Target | Result |
| --- | --- | --- |
| super (9.5 GB) | super (slot A) | acknowledged, rehashed identical, 243 s |
| dtbo, init_boot, vendor_boot, recovery, boot | `_a` | acknowledged, rehashed identical |
| vbmeta_system, vbmeta | `_a` | acknowledged, rehashed identical |

No `userdata` or `metadata` partition was in the write set; no wipe and no slot
change were requested or performed. The bootloader stayed on slot A.

## Boot and health

The phone booted `nezha.11b0a26475073bca18f34c39` in 25.5 seconds with
`sys.boot_completed=1`, SELinux **Enforcing**, and root ADB (`uid=0`, `u:r:su`).
No fatal crashes; the 54 boot-time AVC lines are the usual `qseecomd`/`tee`
`permissive=0` denials, none permissive. The display dim float is 0.05 and the
camcorder profile selection is unchanged (`media.settings.xml` still points at
the vendor table). One account and 22 third-party packages are present,
unchanged from v16 — userdata was retained.

## Leica Essential is baked on

After a clean flash and reboot — which clears any runtime resetprop values — the
system reads:

- `ro.theme_customize=LCC`
- `camera.debug.safe.check.disable=true`

Both come from the image `build.prop`, proven by their presence after the
reboot. Launching the camera app, it stayed open past the three-second
self-close window with **no "APK version error"**, reported `phone is lcc_gl`,
and its mode selector listed `Leica Essential` at `mValue=256`:

```
MCAM_ModeSelectView: init: curMode = 163 mItems = [ ... 'Leica Essential' mValue='256' ]
```

This is the same behavior first proven on v16 with runtime properties, now made
permanent at the build level. Root (native userdebug `adb root`) is unaffected;
Magisk was never the root provider and is not involved.

## What this does not prove

Rendered Leica look quality, focus, stabilization and the M9-vs-M3 selection
still need a lit scene with a person. The camera video matrix (up to 4K60;
8K/120fps/long-4K60 fail on this build's media writer) is unchanged from v16 and
recorded separately in [tier2-camera-v16](tier2-camera-v16-20260910.md). No IMS
registration, call or SMS (no SIM). Media and logs stay under the ignored
evidence directory.

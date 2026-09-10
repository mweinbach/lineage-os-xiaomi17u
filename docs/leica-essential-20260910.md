# Enabling Leica Essential (M3/M9) on the standard unit, September 10, 2026

**The Xiaomi Leica Essential mode, with the Leica M3 Monopan and Leica M9 film
looks, is enabled and working on this standard-edition Xiaomi 17 Ultra by
setting two properties: `ro.theme_customize=LCC` and
`camera.debug.safe.check.disable=true`. The device keeps its real model and
attestation identity. The mode captures and runs its on-device style-transfer
pipeline.** This was investigated at the user's request after the first pass
reported the mode as edition-locked; that report was correct that the stock
gate blocks it, but the gate turned out to be two properties, not a hardware
attestation. A guarded source fragment
([`leica-essential.mk`](../device/xiaomi/nezha/leica-essential.mk),
contract [`nezha-leica-essential.json`](../config/nezha-leica-essential.json))
bakes the two properties into the build; it is enabled in source revision 16 and
built and installed as v17 (see "Built and installed as v17" below). The runtime
recipe below is the equivalent toggle on an unmodified build.

## Why the first attempt failed

Forcing only `ro.theme_customize=LCC` made the camera app run as the Leica
edition, but the app closed itself after three seconds with an "APK version
error". Reading the MiuiCamera bytecode showed the exact cause. On resume the
app runs a native anti-tamper check in `libHawk`
(`com.camera.LSsdQFvLalapDwvA.RitIeKoenwCSqcPf`). When that check returns false,
which it does on an unlocked bring-up bootloader, the app posts the exit dialog
and finishes. The check is not a live cloud call; it fails the same way with
the device offline.

## The two gates

| Gate | What it checks | Property that satisfies it |
| --- | --- | --- |
| Mode visibility | `LegendaryEnter.support()` needs the app to run as the Leica edition | `ro.theme_customize=LCC` makes `G7.b.O()` true |
| Anti-tamper close | `RitIeKoenwCSqcPf()` in libHawk fails on an unlocked bootloader | `camera.debug.safe.check.disable=true` skips the check (via `F6.d.X`) |

The mode itself and its models already ship on this unit: the style transfer
runs on the DSP from `/odm/etc/camera/styletrans/styletrans_{low,high,colorfix}.minn`
through `com.xiaomi.plugin.legendST` and `libmialgo_styletrans`, with the M9
and M3 Monopan snapshot pipelines in `legendsnapshot.json` and
`legendmonopansnapshot.json`. Nothing was missing; only the two gates blocked it.

## What was measured on v16

With both properties set and the device model left at the stock `2512BPNDAC`:

- The camera app stays open. The "APK version error" no longer fires.
- The mode list contains `Leica Essential` (module id 256).
- Entering it makes the camera HAL run module `0x100` and the "OEM Legend"
  processing path.
- A capture through the Legendary module (mid 256) saved a valid JPEG whose
  EXIF carries `customize=P1_Leica`.

The full identity spoof used during investigation (model, market name, cert)
was not needed; the two properties alone are sufficient, so the device keeps
its real identity and attestation.

## Runtime recipe on the installed v16

`ro.theme_customize` is empty at boot on this unit, so a plain `setprop` sets
it once; `camera.debug.safe.check.disable` is an ordinary property. Both revert
on reboot.

```sh
adb root
adb shell setprop ro.theme_customize LCC
adb shell setprop camera.debug.safe.check.disable true
adb shell am force-stop com.android.camera   # relaunch to pick up the properties
```

To turn it off before a reboot, `camera.debug.safe.check.disable` can be
cleared with Magisk `resetprop --delete`; `ro.theme_customize` is read-only once
set, so a reboot is the clean way to fully revert. The helper
`reports/tier2-camera-20260909/leica_toggle.py` wraps both directions.

## What this does not change and does not prove

The two properties do not alter the device model, market name or attestation
identity, and do not touch platform verified boot or SELinux;
`camera.debug.safe.check.disable` disables only the camera application's own
integrity self-check. The M9-versus-M3 look selection, the rendered image
quality of each film look, and behaviour in a lit scene are not evaluated here;
the dark-desk test only proves the mode opens, captures and runs its pipeline.
The [contract](../config/nezha-leica-essential.json) holds the bytecode evidence
and the device-file list; media and decompiled sources stay under the ignored
evidence directory.

## Built and installed as v17

The two properties are no longer set at runtime. Source revision 16 enables the
fragment (`NEZHA_LEICA_ESSENTIAL := true`), which writes both into the system
`build.prop`, and that source is built and installed as v17
(`nezha.11b0a26475073bca18f34c39`). After a clean flash and reboot — which clears
any runtime resetprop values — the phone reads `ro.theme_customize=LCC` and
`camera.debug.safe.check.disable=true` from the image, the camera app stays open
past the three-second self-close window with no "APK version error", reports
`phone is lcc_gl`, and its mode selector lists `Leica Essential` at `mValue=256`.
So the mode is on at boot with no resetprop and no Magisk; root is the native
userdebug `adb root`, unaffected. See the
[v17 install record](v17-install-validation-20260910.md). The runtime recipe
above remains only as a way to toggle the mode on an unmodified build.

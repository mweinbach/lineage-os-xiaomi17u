# Wallpaper & style clock plugin crash, 2026-09-08

**Root cause measured: the shipped `SystemUIClocks-Flex` prebuilt targets the
pre-QPR2 plugin interface package, so every plugin host on this platform
rejects it, and the Google wallpaper picker crashes on that rejection.** The
fix drops that one product selection. The Flex clock itself stays available
because QPR2 SystemUI's default clock provider already registers it. The other
seven Pixel clock plugins, the wallpaper picker and SystemUI are unchanged.
This page records the diagnosis, the source change and the host checks; the
successor package has not been installed and the crash is not yet closed on
the phone.

## Observed failure

`com.google.android.apps.wallpaper` dies on its main thread with
`VersionInfo$InvalidVersionException: Missing required dependency
ClockProviderPlugin` from `PluginInstance.onCreate` during
`PluginActionManager.handleQueryPlugins`. The retained v13 crash buffer holds
four such crashes on 2026-09-08 between 14:27 and 14:33 device time. The same
signature appears in the v9 and v12 records, so it predates the camera work.

## Diagnosis

The wallpaper app is the Google prebuilt `WallpaperPickerGoogleRelease` from
`vendor/gms` (stallion `CP1A.260505.005`), which overrides the source
`ThemePicker`. It embeds its own copy of the SystemUI plugin library, so the
crash is inside the wallpaper process, not SystemUI. The clock plugins are the
nine `SystemUIClocks-*` Pixel prebuilts in `vendor/extras` at `c401d732`.

A stdlib DEX/manifest audit of the built v13 APKs and of the transferred v13
target-files archive gives the following identities:

| Artifact | Clock plugin interface referenced | Own copy of plugin interfaces |
| --- | --- | --- |
| SystemUI (source, `bka`) | `com.android.systemui.plugins.keyguard.ui.clocks.ClockProviderPlugin` | host |
| WallpaperPickerGoogleRelease | `…plugins.keyguard.ui.clocks.ClockProviderPlugin` | host |
| BigNum, Calligraphy, Growth, Inflate, Metro, NumOverlap, Weather | `…plugins.keyguard.ui.clocks.ClockProviderPlugin` | no |
| **Flex** | `com.android.systemui.plugins.clocks.ClockProviderPlugin` | **yes** |

AOSP moved the interface package on 2025-08-06 (`frameworks/base`
`c5d2b0fd639d`, "Move package of LockscreenElement and related classes").
Evolution X refreshed seven clocks from mustang `BP4A.260205.001` on
2026-01-08 (`vendor/extras` `156bf76`) but left Flex at its 2025-11-18
`BD3A.251105.010.E1` build. Upstream `bka` is still at `c401d732` with no newer
Flex.

The plugin class loader delegates `com.android.systemui.plugin*` names to the
host and otherwise falls through to the plugin's own DEX. Flex's `@Requires`
target therefore resolves to its bundled old-package class, which is a
different `Class` object from the host's required interface. `VersionInfo.checkVersion`
leaves the host entry unmatched and throws "Missing required dependency".
Source SystemUI returns `false` from its version checker and disables the
plugin; the device log shows eleven "Disabling plugin:
com.android.systemui.clocks.flex/…FlexClockProvider" lines and "Clock Id
conflict on attach: DIGITAL_CLOCK_FLEX is double registered by
DefaultClockProvider", confirming that QPR2 already ships the Flex clock
natively. The newer wallpaper prebuilt performs the same check inside
`loadPlugin` and lets the exception escape.

The hypotheses of a missing APK, a wrong wallpaper package selection or a
SystemUI version-number mismatch are ruled out: all nine clock APKs and both
hosts are packaged, the version numbers agree, and only Flex's interface
identity differs.

## Source change

[Patch 0039](../patches/evolution/0039-remove-stale-systemui-clocks-flex.patch)
removes `SystemUIClocks-Flex` from `PRODUCT_PACKAGES` in
`vendor/extras/evolution.mk` and leaves a comment naming the reason. The
[contract](../config/systemui-clocks-flex-removal.json) pins the patch, both
complete source identities, the retained Flex APK, the seven kept plugins and
both hosts. The Flex APK, its `Android.bp` import and the plugin allowlist
entries are untouched. No version check is weakened, no clock provider is
removed from SystemUI and no user data is cleared.

[`scripts/systemui_clock_plugin_audit.py`](../scripts/systemui_clock_plugin_audit.py)
performs the audit above on APK files or a target-files archive and replays the
contract. Its `check` command fails on the v13 archive with exactly the two Flex
findings (foreign interface, bundled interface copy) and passes when Flex is
absent and the seven kept clocks and both hosts are present.
[Thirteen offline tests](../tests/test_systemui_clock_plugin_audit.py) exercise
the classifier and archive scan on synthetic APKs, reconstruct both source
files from the full-file patch, and reject a tampered patch.

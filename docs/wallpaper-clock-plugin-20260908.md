# Wallpaper & style clock plugin crash, 2026-09-08

**Root cause measured: the shipped `SystemUIClocks-Flex` prebuilt targets the
pre-QPR2 plugin interface package, so every plugin host on this platform
rejects it, and the Google wallpaper picker crashes on that rejection.** The
fix drops that one product selection. The Flex clock itself stays available
because QPR2 SystemUI's default clock provider already registers it. The other
seven Pixel clock plugins, the wallpaper picker and SystemUI are unchanged.
This page records the diagnosis, the source change and the host checks as of
the package checkpoint. The package was later installed with the user's
separate approval; the device results are in the
[v14 installation and validation record](wallpaper-v14-install-validation-20260908.md).

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

## Source revision 11 and build

Source revision 11 is `nezha.98d08f70d20e5a87a2777f81`, with 672 recorded rows:
all 671 revision-10 rows preserved byte for byte plus the new
`vendor/extras/evolution.mk` row. Before adoption `make test-current` passed
939 tests and `make test` passed 4,905 tests. The guest transaction checked
every baseline row and the `vendor/extras` HEAD (`c401d732`) before writing
the one file, and its receipt is
`reports/wallpaper-clock-plugin-20260908/source-revision-11/source-installed.json`.

Preflight verified aarch64, case-sensitive ext4, the pinned manifest and the
sole `evolution-nezha-work` writer. The guest's copy of the verified v13 super
image was removed only after it and both host copies rehashed identically;
that restored the 200 GiB build threshold. The userdebug `target-files-package`
build ran in the existing `/work/out/nezha-feature-fixes-20260905-v1` output
and closed with exit 0 in about fourteen minutes; source bytes were verified
unchanged before and after. The build tree lists exactly the seven kept clock
modules, stages no Flex directory, and carries the new incremental identity.

## Package checks

The unsigned archive is 11,321,504,578 bytes, SHA256
`bc786fe393208bf66f61d37aaed78bcb61fc6c7c1cd498f43cdecb4b89297a11`; the
sparse super image is 9,475,836,016 bytes, SHA256
`7a3b95ac3f0a88f17b428f1742abd0898513b927d298e7a3e0c0790697d8c41a`.

A member-by-member comparison against the transferred v13 archive shows 9,049
identical members, exactly two removed entries (the Flex directory and its
APK), nothing added, and 19 changed members that are all build-identity
files: partition build props, the boot and init_boot ramdisk props, the
system, system_ext, product, system_dlkm, vendor_dlkm, init_boot and vbmeta
images, the system_ext map, care map, filesystem config and vbmeta digest.

The seven v13 camera and audio components (cameraserver, framework.jar,
framework resources, Aperture, the runtime library and both audio conversion
libraries) and all nine plugin-related APKs (seven clocks, the wallpaper
picker and SystemUI) are byte-identical to v13. The clock plugin audit passes on
the archive with four hosts and seven plugins, Flex absent and every expected
module present. The v13 camera artifact, native CameraOpt, configuration and
policy gates pass unchanged: 98 policy inputs identical, the compiled normal
policy leaves only `su` permissive, and the strict neverallow differential
reports no new violation.

## Signing, admission and bundle

After the unsigned gates, the package was admitted, the host-measured
system_ext image (791,797,760 bytes, SHA256
`e14912d3645357c8ee8a525eea439c63cd9b55164d30a5f8c466a86f05756598`) was added
to the AVB image-set budget, and `make test-current` (939 tests) and
`make test` (4,905 tests) passed again. The reconciled signed target-files
archive is 11,143,860,576 bytes, SHA256
`fee3f8e03fef7ca7c29faf63d492d28d99c72be47dc93ddc05eafd90e9bd390d`. The signed
archive passes the same component, archive-diff, clock-audit, camera, native
and configuration gates as the unsigned one.

The private eight-image bundle is
`artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v14/`, manifest SHA256
`b36a0482e3b28be2c16d609f6cc6252b6c8b68ee25d0f87d624472df5b678ce0`, status
byte-identities-verified, not device-admitted, not flash-ready. It is not an
OTA or TWRP installer. The v13 bundle, working76 recovery and all predecessor
bundles are preserved. No phone was accessed at any stage of this work.

The [research record](../research/wallpaper-clock-plugin-20260908.json) binds
the crash trace, both v13 audits, the contract and patch, the source receipt,
build, package, admission, signing and bundle receipts, and the gate outputs.
Raw logs, APKs, images and keys stay under ignored directories.

## Device validation plan and remaining gates

Installing v14 needs a fresh explicit approval against the manifest hash above.
The intended route is the same as v13: the eight A-chain writes over the
shared Super, no wipe, no slot change, no data clear, then a reboot. After
boot, confirm the build identity, slot A, userdebug and Enforcing.

Then, with the phone unlocked: open Wallpaper & style from the launcher long
press and from Settings; enter the wallpaper picker; open lock-screen
customization and the clock chooser; select one Pixel clock (for example
BigNum), return to the lock screen and confirm it renders, then restore the
previously selected clock; also confirm the default Flex-style clock remains
offered. Read the fresh crash buffer and the SystemUI log for
`InvalidVersionException`, `Disabling plugin` and `Clock Id conflict` lines;
all three should be absent. Restore any wallpaper or clock change made during
the test to the state observed before it. Repeat the v13 camera subset (rear and
front photo, UltraRAW, one Aperture effect, one short video) to show the
preserved baseline still captures.

Until those observations exist, the crash is unresolved on the phone. The Flex
APK, its `Android.bp` import and the allowlist entries remain in the tree; a
QPR2-compatible Flex plugin from a future `vendor/extras` refresh could be
re-enabled after passing the same audit.

# Camera v13 package, 2026-09-08

**Host package checkpoint for V13.** Its subsequent separately approved
installation and phone results are recorded in the
[v13 runtime record](camera-v13-install-validation-20260908.md). This document
preserves the pre-installation build and package checks. The package adds
compressed Bayer UltraRAW support and factory multiroute/MIHC audio values.

## Source, components and behavior

Source revision 10 is `nezha.2c510f47f6d99b93f0c3ee11`, with 671 recorded rows.
Its receipt is `reports/camera-completion-20260907/source-revision-10/source-installed.json`, SHA256 `1316c5392b530fff257d05088b8b841ba8279d647ffb1086c4f47c2a99715021`.
Both the six-goal component build and full `target-files-package` build pass,
with exact source bytes and modes checked before and after each build.

The [source and host behavior record](camera-bayer-audio-compat-20260908.md)
describes the two changes. The DNG writer accepts compressed Bayer format 32,
retains its CFA metadata, and relates full TIFF tile width to the two-component
lossless JPEG width. Linear RGB format 15 remains supported. The audio changes
map the factory multiroute device and MIHC encoding in both directions and
extend the shared legacy validators with their exact measured values.

The source-level native parser passes 1,228 sanitizer-backed checks; the
unchanged gainmap helper passes 685 checks. Twelve synthetic DNGs produced by
the actual AOSP writer fully decode with LibRaw, covering RGB and Bayer,
strips and tiles, previews and raw-only files, including the measured
4080-by-3072 Bayer layout. The full audio converter fixture checks every unique
device, format, flag mask and directional channel layout advertised by the
captured primary module: 309 disabled checks and 314 enabled checks pass.
These results do not establish audio-policy initialization or an actual
successor UltraRAW capture on the phone.

The component receipt records actual DEX/native definitions, required camera
CFI, retained Aperture behavior and the checks on the delivered audio binaries.
Seven selected component files match both unsigned and signed archives:
`cameraserver`, `framework.jar`, framework resources, Aperture,
`libandroid_runtime.so` and both audio conversion libraries. The unselected
shared `libcameraservice.so` is absent from the archives and actual system image.

## Signed package and policy

The reconciled signed target-files archive is 11,145,246,800 bytes,
SHA256 `5ec834aed93a0fe9acc288e24a3c3252a8ba4ec039b297d50b1eeaac37eb4b4d`. The private bundle is
`artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v13/`, with manifest
SHA256 `129912c8f2f5d956b8c482a40e60ac11e10c9d03bc01b042649fd75ed676b7a4`.

All eight payload hashes and sizes pass verification: shared Super, DTBO,
init_boot, vendor_boot, recovery, boot, vbmeta_system and vbmeta. Signing,
reconciliation and AVB inventory checks pass. This bundle is not an OTA or
TWRP installer. Predecessor bundles and working76 recovery remain preserved.

Camera payload, signer, ABI, native dependency and configuration gates pass
on both archives. All 98 policy input files remain byte-identical to the v9
reference. Normal policy compilation passes. Strict neverallow checking
retains the same 16 existing conflicts with no new violations.
Signed and unsigned configuration matches across
272 inspected image files. These are package results; the
installed v12 phone's measured normal Android state remains Enforcing.

## Verification and retained evidence

After image admission, `make test-current` passes 939 tests in
28.949 seconds. `make test` passes 4,892 tests in
195.845 seconds plus shell checks. The
[delivery evidence record](../research/camera-v13-package-20260908.json) binds
the source, behavior fixtures, component, full-build, archive, signing and
bundle receipts.

Preflight verifies disk space, OS, architecture, filesystem case sensitivity,
manifest identity and the sole source-volume writer. Before starting the
component build, two retained host copies and the guest copy of the v12
Super image were rehashed. Only that generated guest validation duplicate was
removed to restore the 200 GiB build threshold. Source, output, cache and
rollback bundles were preserved. Private inputs, source checkouts, device
captures and keys remain ignored.

## Original device acceptance plan

The separately approved installation and bounded capture matrix below have
since passed; see the runtime record for results and remaining quality limits.

V12 already passes fully decoded ordinary Xiaomi photos, main and telephoto
50 MP, telephoto 200 MP Ultra HDR, Pro RAW, all three physical RAW sensors and
all ten warm Aperture Ultra HDR effect cases. Its UltraRAW writer rejects the
measured Bayer format; early audio startup rejects the factory multiroute
descriptor and leaves audio policy null. Those are the failures addressed here.

Following separate approval, install this exact eight-image set to the current
A chain with shared Super, without a wipe or slot change, then reboot. Capture
early audio diagnostics before root ADB interrupts transport. Require an
actual UltraRAW DNG and embedded preview to fully decode, verify audio-policy
startup and video/audio tracks, and repeat the working photo and RAW cases.
Useful effect quality, sensor-native resolution and sustained behavior remain
separate acceptance work.

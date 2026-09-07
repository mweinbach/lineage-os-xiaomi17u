# Build-variant opt-in (September 6, 2026)

The native construction guard used to admit only the `user` variant. Camera
diagnosis on the installed f9e build needs `adb root`, and the working76
recovery no longer boots under the ROM's own boot chain, so a `userdebug` build
is the practical route to root. This record adds that as an explicit opt-in;
the default build stays `user`.

## What changed

- `scripts/rom_construction_source.py` gains an explicit successor that derives
  the opt-in guard from the maintained user-only guard. Only the variant clause
  changes: `user` is always admitted, `userdebug` is admitted only when the
  invocation also sets `NEZHA_BUILD_VARIANT_OPT_IN=userdebug`, and `eng` is
  never admitted. `variant_environment()` returns the environment a runner must
  add for each admitted variant.
- `config/nezha-rom-construction-variant-opt-in-v1.json` binds the predecessor
  guard (`fe1e32cf…`, 2,553 bytes) to the derived guard (`a6ae5a08…`,
  2,737 bytes). Earlier construction contracts and their recorded identities are
  unchanged.
- Tests cover the exact single-clause derivation, the contract binding, the
  environment mapping, and host GNU Make behavior for every admitted and
  rejected combination.

## Using it

The private runner `reports/variant-opt-in-20260906/build_successor.py`
accepts `--variant user` (default) or `--variant userdebug`. Both variants reuse the
existing physical output tree, following the incremental-build policy; a fresh
tree under Rosetta would rebuild everything from scratch and exceed the guest
reserve. Before either variant can
build, the derived guard must be installed into the build guest by the reviewed
source transaction in `prepare_variant_opt_in.py --execute`; that transaction
records preimages and rolls back on any mismatch. That transaction ran on
September 6 (`/work/validation/variant-opt-in-source-20260906-v1`); the guest
source identity is now `nezha.3dc84b361cb517a1d98941db` with one changed file.

```sh
python3 reports/variant-opt-in-20260906/build_successor.py --variant userdebug nothing
```

## Space reclaimed on September 6

To make room for the userdebug signing outputs, six redundant payload copies
(59.1 GiB) were deleted from `artifacts/build-validation/` at the user's
request: the raw a6d and f9e target-files zips (their reconciled signed archives
remain under `artifacts/avb/nezha/`), the raw Package 6 and Package 7 zips
(their signed image sets remain), and the a6d and f9e super transfer copies
(byte-identical to the retained flash bundles, verified by SHA-256 before
removal). Each directory keeps its transfer receipt; the recorded hashes in the
documentation still describe the deleted bytes.

## Metadata delivery exception for userdebug

The first userdebug package attempt failed at the prebuilt target-files
metadata install: its policy gate pins the exact platform SELinux policy
(`plat_sepolicy.cil` and sidecars) that the delivered vendor and ODM policy
images were verified against, and a userdebug platform policy differs by
construction. The opt-in therefore also derives
`device/xiaomi/nezha/generated/target-files-metadata.mk` so that the explicit
userdebug/userdebug pair leaves the delivery unselected; the default user build
keeps the full delivery and gate. The derivation is pinned in the same contract
(`bbf310cc…` 351 bytes before, `615b7ed9…` 791 bytes after) and was installed by
a second guest transaction, source identity `nezha.1088ec3b159be6c32e1403f2`.

Consequences for the userdebug package: no injected VENDOR/ODM metadata trees in
target-files, and the packaged vendor/ODM policy images are not verified against
the userdebug platform policy. Their precompiled policy hashes will not match, so
init compiles SELinux policy at boot from the CIL files. This is acceptable for a
diagnostic build and must be confirmed on the device (enforcing, no policy load
failure); it is not a release configuration.

## Restoring adb root on the userdebug build

The first userdebug package flashed and booted (identity `nezha.1088ec3b…`,
build type userdebug, SELinux enforcing) but reported `ro.debuggable=0`, so adbd
refused root. Lineage's common product config sets
`PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG` for userdebug builds, and the build
property generator then emits `ro.debuggable=0`.

A third guest transaction first overrode the variable to `false` from the device
product makefile. The rebuilt package (identity `nezha.d4f428f2…`) still carried
`ro.debuggable=0`: the build exports the variable with `add_json_bool`, which
maps any non-empty value, including `false`, to true. That override is therefore
recorded as ineffective and removed again (`f9955fd7…` 1,561 bytes installed,
`b53dc7f3…` 1,193 bytes restored). The effective derivation wraps the assignment
inside Lineage's common config so that only the explicit userdebug/userdebug
pair leaves the variable unset (`2747b367…` 10,468 bytes before, `38ac0f28…`
10,789 bytes after; the predecessor is snapshotted under
`research/source-snapshots/`). Both changes form the fourth guest transaction;
a host GNU Make test pins the three cases and the helper's non-empty rule. A
rebuilt package carries a fresh source identity and therefore a new measured
system_ext image to admit.

A userdebug image is a diagnostic build. It weakens `ro.debuggable` and adb
policy and is not a release candidate. Signing, partition fit, device admission
and the camera result remain separate gates; nothing here touches the phone.

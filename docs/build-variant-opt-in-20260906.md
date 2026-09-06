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

A userdebug image is a diagnostic build. It weakens `ro.debuggable` and adb
policy and is not a release candidate. Signing, partition fit, device admission
and the camera result remain separate gates; nothing here touches the phone.

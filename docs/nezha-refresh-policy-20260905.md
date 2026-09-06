# Guarded refresh defaults and adaptive-refresh investigation

`NEZHA_REFRESH_POLICY := true` selects an authored framework overlay with
default and default-peak rates of 120 Hz. It corrects the generic 240 Hz peak
default and preserves the observed 120 Hz normal default. This is a source
candidate, not a measured battery improvement: no advertised physical mode
above 120 Hz was available for the old 240 Hz setting to select anyway.
Unset/false keeps the previous path. Malformed/multi-token selectors and a
missing selected overlay fail. Saved user minimum/peak settings are untouched.

## Evidence and important correction

The retained Package7 `display.txt` snapshot in the September 5 feature-triage
capture advertises 24/30/60/90/120 Hz, contains a minimum-render vote of 60 Hz,
default 120 Hz, peak default 240 Hz, and a null display idle configuration.
It contains off-screen and differently timed state; it is not a transition trace.
The snapshot does **not** prove the user saved a minimum of 60 Hz: pinned
Evolution's `DisplayModeDirector` explicitly uses **60f as the missing-setting
fallback**. An overlay for an invented minimum-rate resource would not change it.

Reviewed source revisions remain the Package7 source lock:

- `frameworks/base`: `8140698cc12983deecdbd434220affb5f931bfc6`.
- `frameworks/native`: `d78897741ad798fe9c183795026cfd87cd03a76c`.
- `vendor/lineage` (Evolution): `11d2966a3294a0a692fc958127c770cfe9c00a3c`.

Live `bka` ref checks on September 5 found base had advanced to
`929be7281ce09a311d262c83415db04e9f127adb`; native still matched its pin.
No source selector was updated. Resource and consumer hashes are recorded in
`config/nezha-refresh-policy.json`.

Source references: [pinned refresh settings consumer](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/services/core/java/com/android/server/display/mode/DisplayModeDirector.java),
[pinned resource defaults](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/core/res/res/values/config.xml),
and [pinned SurfaceFlinger rate selector](https://github.com/Evolution-X/frameworks_native/blob/d78897741ad798fe9c183795026cfd87cd03a76c/services/surfaceflinger/Scheduler/RefreshRateSelector.cpp).

## Why no new idle timer or 24 Hz minimum

The retained factory `VENDOR/build.prop` already supplies content detection
`true` and touch timer `200` ms. These properties remain in the preserved vendor
input, so adding duplicates is unnecessary. Null `idleScreenRefreshRateConfig`
alone does not prove every legacy/kernel idle path is disabled.

The exact ODM properties include Xiaomi-specific dynamic-rate/brightness lists
(`120,90,60,30:100,60,5`, `120,60:5`, and `346,16383:90,120`). Their Xiaomi
consumers and brightness domain are not the AOSP blocking-zone curve contract.
They cannot safely be translated into AOSP arrays or arbitrary idle timeouts.
This candidate does not replace brightness calibration, alter gamma/HBM/thermal
votes, claim LTPO 1 Hz, or force 24/30 Hz. Those physical-mode advertisements are
qualification leads only. Existing calibrated-display work stays independent.

## Offline checks and useful diagnostics

```sh
python3 scripts/refresh_policy.py verify-source
python3 scripts/refresh_policy.py analyze-display --display-dump /absolute/private/display.txt
python3 -m unittest tests.test_refresh_policy -v
```

The analyzer reads a bounded regular saved file, reports advertised rates,
snapshot render rates, defaults, effective minimum-render votes, desired physical
and render ranges, and other vote lines (including low-power/thermal votes when
present). It preserves ambiguity about setting origin and does not access a
phone. A single dump cannot establish physical transitions or battery savings.

## Native and device gates

1. Native successor build: verify the overlay is compiled and actually wins
   resource/RRO precedence. Verify preserved vendor properties in target-files
   and effective runtime properties; static source inclusion is not that proof.
2. On an explicitly authorized installed successor, retain build identity,
   effective resource/default values, saved min/peak values, DisplayManager votes
   and SurfaceFlinger content/touch/legacy/kernel-idle state. Do not silently
   rewrite existing settings to make a result pass.
3. Measure idle static content, 24/30/60 fps playback and touch/scroll recovery
   using physical mode transitions and frame timing, not render-rate text alone.
   Record battery saver, thermals, charging state and brightness alongside it.
4. Before any separately selected lower-rate policy, qualify repeated dark and
   low-brightness gray transitions, auto/manual brightness, bright/HBM behavior,
   flicker and gamma shifts, AOD/wake, and UDFPS. Honor all thermal restrictions.
5. Compare matched-duration and matched-brightness power/charge-counter deltas
   plus jank before calling anything a battery/performance improvement.

No native build, installation, phone setting, active VM or main checkout was
changed by this work. Lower-rate policy and all behavioral gates remain open.

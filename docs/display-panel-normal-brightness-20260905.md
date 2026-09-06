# Exact-panel normal and automatic brightness candidate

This opt-in source change supplies the missing calibration for Nezha physical
display `4630946639341352083`. It deliberately limits the panel to the factory
normal-brightness transition, approximately **600.017 nits**, and withholds HBM.
The full factory XML cannot be selected safely without further framework work.
This is a prepared private packet and source integration, not an installed fix.

## Selected inputs and derivation

`scripts/display_panel_inputs.py` admits only the hash-bound factory product
capture already retained in `artifacts/display-stock-20260905`. It verifies the
captured APKs, decoded resource dumps, capture paths/readback/size/hash records,
product image hash and pinned Evolution resource definitions. It does not mount
an image, run firmware, fetch sources, start a build, or access a phone.

Factory product SHA256:
`67e6c683c1091abc0a548c27e4681bbe26471529129d15453b95c8d69417795f`.
Factory `/product/etc/displayconfig/display_id_4630946639341352083.xml` SHA256:
`71949a144918a4e31036806d213aba4d3454c06348d578a9bdf810b9463d9605`.
APK and resource-dump identities are explicit constants in the generator.

The packet preserves the nine factory backlight/nits calibration points and the
factory density/ambient-light horizons. It removes the entire HBM element and
uses its exact `0.374862654` backlight transition as the normal-mode ceiling.
The 133-point factory nits curve and 132-point lux curve are selected from
`AospFrameworkResOverlay.apk`; nits targets above the normal ceiling are capped
(55 points). Automatic brightness availability comes from
`FrameworksResCommon_Sys.apk`. The two factory 1,000 ms debounce resources are
retained. No sensor identity is guessed; Android's default light sensor remains
subject to device qualification.

The legacy 14-bit LCD-backlight array is excluded because the pinned framework's
integer-array contract is 0–255. Physical nits mapping is selected instead.
The Xiaomi `_hyper` integers, 14-bit legacy ramp rates, unrelated overlay
resources, and questionable 1% gamma adjustment are not imported.

## Pinned framework semantics

All source review used Evolution `frameworks/base` commit
`8140698cc12983deecdbd434220affb5f931bfc6`. The retained framework resource XML
has SHA256 `b7c169c6ce96e3e76617eb2e253e74deac4c3a1e9822025d5ba7443db235e0ba`.
Only individual files from this exact commit were inspected; the ongoing source
checkout and build VM were not changed.

- [DisplayDeviceConfig.java](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/services/core/java/com/android/server/display/DisplayDeviceConfig.java):
  product display-config lookup precedes vendor; framework float min/max constrain
  HAL backlight; `rawBacklightToNits` linearly interpolates a constrained endpoint;
  `createBacklightConversionSplines` maps that range to system brightness 0–1.
- [LocalDisplayAdapter.java](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/services/core/java/com/android/server/display/LocalDisplayAdapter.java)
  publishes the DDC normalized minimum/maximum in DisplayInfo, and
  [PowerManagerService.java](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/services/core/java/com/android/server/power/PowerManagerService.java)
  uses valid DisplayInfo constraints preferentially, with resource values only
  as fallback. The selected DDC path therefore does not double-cap the slider.
- [BrightnessMappingStrategy.java](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/services/core/java/com/android/server/display/BrightnessMappingStrategy.java)
  selects physical mapping from valid DDC nits/brightness plus overlay lux/nits;
  flat nits plateaus are valid.
- [HighBrightnessModeData.java](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/services/core/java/com/android/server/display/config/HighBrightnessModeData.java)
  does not consume the factory legacy `thermalStatusLimit`. Disabling only the
  HBM boolean is insufficient: its loader still validates the transition, which
  would equal the newly constrained maximum and throw.
- [HighBrightnessModeController.java](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/services/core/java/com/android/server/display/HighBrightnessModeController.java)
  considers zero remaining time sufficient when minimum time is zero, then
  schedules another callback one millisecond later while above the transition.
  The factory 0/0/0 timing requires a separate compatibility fix and thermal
  policy review before HBM can be admitted. No replacement durations or thermal
  thresholds are invented here.

The normal ceiling is the framework endpoint interpolation between factory
`(0.03699182, 59.8 nits)` and `(0.499938957, 800 nits)`, evaluated at
`0.374862654`: `600.017168093` nits. This is a source-derived calibration value,
not a new photometer measurement. The system default is explicitly renormalized:

`(0.055854 - 0.000366256) / (0.374862654 - 0.000366256) = 0.148166296`.

The dim level is normalized zero, corresponding to the factory minimum backlight
and 1-nit calibration point. Both framework resources and DDC supply the
normalized default. Existing saved slider values change physical meaning when
this narrower range is selected; there is no settings migration in this packet.

## Prepare and select after the existing build

Create an output parent beneath this worktree's ignored `artifacts/`, then run:

```sh
python3 scripts/display_panel_inputs.py prepare \
  --stock /absolute/path/to/retained/display-stock-20260905 \
  --output artifacts/display-panel/normal-v1
```

The output directory must be new. Inputs and ancestors cannot be symlinks;
publication never overwrites an existing packet. The generator checks all three
derived output hashes against its reviewed contract before publication. Only
the authored generator, tests, integration and documentation belong in Git;
the private packet and original proprietary captures remain ignored.

When the current build is finished, stage this packet as
`vendor/xiaomi/nezha-display` in the selected source tree through the reviewed
source-staging workflow, carry `display-panel.mk` with the device templates,
and explicitly select `NEZHA_CALIBRATED_DISPLAY=true`. Unset/false preserves the
existing candidate. Invalid/multiword flags fail. True requires the private
packet, whose Make fragment checks the exact XML and overlay hashes and copies
the XML to its exact product display-config path. The packet overlay precedes
the existing device overlay and defines only brightness resources.

Do not enable this in the currently running main-branch build. Merge and source
staging, native compilation, image delivery and device adoption are separate.

## Validation and remaining gates

The focused offline tests exercise normalization and endpoint interpolation,
curve monotonicity and plateau handling, typed float resources, missing/type-
mismatched resources, input hash/path rejection, symlink rejection, Make flag
and missing-packet failures, and exact/duplicate/mismatched ZIP delivery.

The generated `brightness.xml` also passed a local `aapt2 compile --dir` with
the pinned SDK 37 compiler SHA256
`13a206c0b022ba3b92f21b6f142f3a4b2d0f3bb1ac0bddfa820ee2c6b00c4c99`.
The private compiled resource ZIP is SHA256
`e18baef4d0502b7f3e16fe9cbec5e64702f3866553d8ff865913d9ae26e1d50a`.
This verifies resource syntax/compilation only; it does not link framework-res
or demonstrate that the product selects the overlay.

After a successor native build, inspect the compiled framework resources and
run the limited panel delivery check:

```sh
python3 scripts/display_panel_inputs.py verify-delivery \
  --packet artifacts/display-panel/normal-v1 \
  --target-files /absolute/path/to/successor-target-files.zip
```

This checks only the final product XML bytes; it explicitly does not certify
compiled framework resource delivery. Then separately verify the active DDC
path, normalized brightness constraints, physical mapping, ambient sensor events,
manual and automatic sweeps, minimum brightness, saved-slider transition,
suspend/AOD and temperature behavior on an authorized device session. HBM/HDR
boost, outdoor luminance, refresh pacing and thermal qualification remain open.

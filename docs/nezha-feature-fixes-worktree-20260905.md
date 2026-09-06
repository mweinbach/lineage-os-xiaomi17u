# Nezha feature-fix worktree — September 5, 2026

This work follows the [remaining-feature audit](package7-remaining-feature-audit-20260905.md)
on branch `codex/nezha-feature-fixes`, prepared separately from main's ongoing
successor packaging work. It supplies display and IMS API source changes,
reproducible IMS build inputs, corrected power evidence and tools for the next measured
hardware session. It has not been installed in the Android source VM or phone.

## Mergeable changes and their limits

| Slice | Source result | Remaining proof |
| --- | --- | --- |
| Display | Opt-in exact-panel normal/automatic brightness packet, private derived XML/resources, strict product input hashes and generated-device include | Native resource build, final-image contents, effective display selection and a phone brightness sweep |
| IMS | Exact property-query framework API patch, definitions for 24 modules, and 20 private inputs behind an immutable-hash build producer | Integrate the API patch and complete qtelephony policy; then Soong, image and carrier results. IMS remains disabled. |
| Power | Reproducible exact-input verification and correction of the WLC/charging inference | A real Nezha component power model and measured charging behavior. No power profile or charging control is enabled. |
| Hardware | Opt-in capture profile and 30-check offline evidence ledger | Actual operator measurements on a separately authorized installed build |

The display selector is `NEZHA_CALIBRATED_DISPLAY=true`. It requires the generated
private packet at `vendor/xiaomi/nezha-display`; missing or changed panel/resource
inputs fail product parsing. The new `display-panel.mk` is part of the authored
device-template inventory so regeneration retains the selection interface.
Default builds do not select the new packet implicitly.

The normal-brightness implementation caps physical backlight at the exact stock
HBM transition, approximately **600 nits**, normalizes the default to the
framework's `0..1` brightness scale and caps the 133-point automatic nits curve.
This changes saved-slider interpretation. It deliberately withholds HBM: the
selected framework does not consume the retained legacy thermal-limit field,
and stock zero-duration timing is incompatible with its HBM scheduling path.
Do not infer outdoor boost or full luminance parity from this source change.

Independent review traced the cap through DisplayDeviceConfig,
LocalDisplayAdapter, PowerManagerService and DisplayPowerController at pinned
framework revision `8140698cc12983deecdbd434220affb5f931bfc6`. The active display
publishes normalized limits, avoiding a second application of the physical
backlight cap. Native and hardware validation remain necessary.

The [IMS workflow](ims-private-inputs.md) keeps both build definitions named
`Android.bp.in` and all public modules disabled. Its new producer and exact
payload reproduction are useful build preparation, not a working provider.
Do not rename the templates or flip flags as a substitute for implementing the
remaining domain, seapp and mapping contracts and integrating the API patch.

The new hidden `TelephonyBaseUtilsStub.isMiuiRom()Z` method implements the
observed normal-provider predicate: whether either real MIUI version property
is nonempty. It preserves per-call reads without faking properties or returning
a constant. All four inspected IMS callsites use this method. The original app
already declares `usesNonSdkApi=true`; existing system-app eligibility supplies
that access without a new whitelist or enforcement change. Local JVM tests
cover 52 assertions, including the method ABI, short-circuiting and no caching.
This is a narrow compatibility implementation, not the complete MIUI plugin
framework or a proven ART/carrier result.

The [power review](nezha-power-inputs-20260905.md) found that both retained
framework power profiles contain generic placeholder values. It also confirms
that `vendor_wlc_app` is a workload classifier. Those findings rule out the
proposed direct profile copy and charging inference; they do not establish a
hardware failure. The captured `mi_ext` init script only adds product resource
mounts, and the earlier audit established no unconditional startup failure.
Effective mounts, properties and overlays belong in the measured qualification
track before further source imports.

## Use after main's build completes

1. Record main's completed source/artifact identities. Merge or cherry-pick these
   commits through the normal review process; do not replace main's newer AVB,
   logical-budget or packaging work with this branch's older baseline files.
2. Generate and verify the display packet from retained exact-stock evidence
   using `scripts/display_panel_inputs.py prepare`. Keep its contents in ignored
   private storage; only its generated build-source files belong in the Android
   private namespace. The [display document](display-panel-normal-brightness-20260905.md)
   records the exact command and candidate limitations.
3. When the sole source-volume writer is idle, stage the reviewed device include
   and private packet using the existing source transaction workflow. Recheck
   host/disk/source prerequisites and select the display flag explicitly. Reuse
   the existing source checkout with separate successor outputs.
4. Build and inspect framework resources and target-files. Run the display
   delivery verifier, then inspect effective compiled resource values; XML
   membership alone does not establish overlay delivery. Preserve the original
   signing, VINTF, SELinux, 4 KiB, recovery and compatibility checks.
5. After separately authorized installation, use the
   [hardware workflow](hardware-qualification.md) for the actual installed
   identity. Each pass/fail needs a measured observation and saved evidence.

Offline previews require no device:

```sh
make feature-diagnostics-plan
make hardware-qualification-plan
```

The capture profile is separately opt-in through `--feature-diagnostics` in
`collect_stock.py`. It adds radio/location/network, power, display and `mi_ext`
observations while retaining explicit-device checks, private output and partial
failure records. It runs no functional tests. The ledger never turns a service
registration into a pass, and incomplete/failing sessions return nonzero.

## Validation

Focused offline tests exercise packet generation, original byte preservation,
input failure paths, source-template regeneration, diagnostics and evidence
handling. The IMS producer was also executed on all 20 real retained inputs
(3,899,108 bytes), with every output hash matching. The power verifier reproduced
the findings from the exact retained APK and nine captured system-ext files.

The final full offline suite passed **4,696 tests in 196.406 seconds**. Its
private log is `reports/feature-fixes-worktree-20260905/all-tests-final.log`.
The initial run is retained separately: its five failures were documentation
links to ignored historical reports absent from this worktree. Those references
now explicitly identify private evidence paths; the link test was not weakened.
The generated brightness resources also compiled with the pinned host `aapt2`;
that result remains separate from framework resource linking and product delivery.

The implementation is split into independent commits:

| Commit | Scope |
| --- | --- |
| `3d59f9e` | Calibrated normal/automatic display source candidate and tests |
| `5f8a1f6` | Build-bound hardware ledger and opt-in diagnostics |
| `2c878ab` | Exact power evidence and workload-classifier correction |
| `17c518d` | IMS identity API, guarded provider inputs and expanded property capture |

The final integration commit adds the Make shortcuts, focused test selection,
documentation index, corrected audit and this handoff. No full Android build,
shared source-volume mutation, main merge, signing, phone query or phone mutation
was performed by this worktree task.

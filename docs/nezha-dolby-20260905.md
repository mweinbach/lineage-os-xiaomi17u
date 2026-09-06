# Nezha Dolby controls candidate

This worktree adds a small **opt-in source controller**, not a port of the
proprietary MiSound app or a claim that Atmos playback is qualified. It uses the
control interface observed in this phone's factory MiSound APK against the
original vendor Dolby backend. No other phone's libraries, calibration or
partition layout is introduced.

## Existing foundation and exact inputs

The saved Package7 September 5 service list contains
`vendor.dolby.dms.IDms/default` and `vendor.dolby.dvs.IDvs/default`. Registration
does not establish successful audio processing. The preserved factory vendor
image includes the Dolby service, configuration and AIDL effect implementation.

The [input contract](../config/nezha-dolby.json) records exact image/file hashes
for the original MiSound APK and six vendor files. Locally retained inputs were
read from the existing images without mounting or executing firmware and without
contacting a phone. Private copies and decompilation stay under ignored
`artifacts/dolby-stock-20260905/`; no proprietary implementation is committed.

The factory AIDL `audio_effects_config.xml` associates `dap_hw` with
`libhwdapaidl.so` and implementation UUID
`9d4921da-8225-4f29-aefa-39537a04bcaa`. Its music postprocessor is
`dlb_music_listener`. The legacy `audio_effects.xml` is different: proving which
configuration the installed audio service consumes remains a device gate.

The factory APK provides the control interface facts: global output session 0,
priority 0, little-endian 32-bit parameter payloads, enable and profile operations.
These are recorded in the contract independently of the new implementation.
`dax-default.xml` supplies profile IDs/names, including Dynamic, Movie, Music,
Custom and Voice; the mobility profiles are not presumed appropriate for every
route. The factory MiSound manifest and code also reference Xiaomi framework
facilities, so copying that APK alone is not an admitted integration.

Recheck private inputs locally:

```sh
python3 scripts/dolby_inputs.py --capture-root artifacts/dolby-stock-20260905
```

This verifies seven exact captured files and the effect/profile mapping. It does
not install them, create a blob bundle, invoke a device, or admit a working build.

## Controller scope and next gates

Set `NEZHA_DOLBY_CONTROLLER := true` at product scope before inheriting the Nezha
device product to select `NezhaDolbyController`. Unset/false leaves it out; invalid
or multiword values fail. The complete source directory is included in the
device-tree generator's template list. The app uses the build's normal platform
certificate and platform APIs in system-ext, with only the two audio-control
permissions. It neither consumes nor repackages the private MiSound APK.

The source controller is for explicit user-driven inspection, enable/disable and
profile selection. No boot receiver, periodic action, automatic profile switch,
MIUI property spoof, policy relaxation, or proprietary APK import is part of it.
Effect availability, control ownership, returned status and readback must be
checked; a checked switch alone is not proof of working sound.

Before enabling in a successor, complete the platform component build and
confirm the installed package and normal permission grants. After a separately
authorized installation, qualify effect creation and control ownership, audible
A/B playback on speakers and supported headphones, output-route transitions,
audio-server stability, and behavior after leaving the controller/rebooting.
State persistence and DMS ownership after releasing the controller are not yet
verified. Leave head tracking, spatializer selection, EQ tuning and route-specific
automatic behavior out until these basics have measured results.

Factory backend presence does not prove all Android-side Dolby native bridge
libraries are needed or supplied; this controller uses the platform AudioEffect
interface directly. Failed effect creation must be diagnosed from actual loader,
linker and policy evidence, not by transplanting unrelated libraries.

## Local validation

The seven exact private inputs passed the verifier. Eight input tests and thirteen
controller tests passed; the latter include nine Java protocol/controller cases
against an explicitly fake AudioEffect plus build/manifest/lifecycle contracts.
The full generated-device-tree suite passed 252 tests with the new template list.
An independent source review confirmed the factory wire protocol and opt-in scope;
its cached-handle retry suggestion was implemented before the final tests.

Pinned Android build-tools 37.0.0 `aapt2` compiled and linked the controller
resources/manifest against the local SDK. All three Java classes, including the
activity, compiled with generated `R.java`, the SDK and a compile-only stand-in
for the hidden AudioEffect methods. These checks are **not** a native Soong build:
the stand-in is neither packaged nor run, and the resource-only APK is not an
executable or signed application. No phone was contacted or modified.

See also [haptics controls](nezha-haptics-20260905.md) and the
[feature-fixes handoff](nezha-feature-fixes-worktree-20260905.md).

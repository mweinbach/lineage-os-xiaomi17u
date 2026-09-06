# Nezha haptics controls and preserved factory calibration

The opt-in `NEZHA_HAPTICS_CONTROLS=true` candidate exposes Android's existing
three-level vibration intensity controls and an independent keyboard vibration
toggle. It preserves the factory vendor/ODM implementation and calibration.
This is a source candidate; no subjective tuning, latency improvement or
installed haptics result is claimed.

## What changes

`device/xiaomi/nezha/haptics.mk` selects a device overlay only when explicitly
enabled. It rejects malformed selector values and is retained by the authored
device-template inventory.

| Resource | Candidate | Behavior |
| --- | --- | --- |
| Settings `config_vibration_supported_intensity_levels` | 3 | Shows existing intensity sliders for supported ring, notification, alarm, media and touch categories instead of single-level toggles |
| Framework `config_keyboardVibrationSettingsSupported` | true | Shows the existing keyboard on/off switch and enables the framework's separate IME usage handling |

The keyboard control is **not an intensity slider**. Existing medium defaults
(2), default amplitude (255), non-fixed keyboard amplitude (-1), fallback
patterns and waveform ramp values remain at the selected framework baseline.
These are also the values in the retained factory framework, except for its
different virtual-key/long-press fallback patterns described below. The overlay
does not enable the ringtone-pattern feature or provide a new effect library.

Source behavior was checked against the locked Evolution revisions:

- `frameworks/base`: `8140698cc12983deecdbd434220affb5f931bfc6`.
- `packages/apps/Settings`: `37cb949f5636f19c71de08f7a014c2ee5e9d141c`.
  `KeyboardVibrationTogglePreferenceController.java` and its Kotlin counterpart
  gate the keyboard switch on the framework boolean. Settings `res/values/config.xml`
  documents level count 3 as the direct low/medium/high HAL strength mapping.
  The live `bka` branch was independently checked at
  `018d1289c488ac23f70c5c33812d0cf7d93ab224`; it does not replace the locked basis.

## What stock already supplies

The retained factory vendor image includes `HapticsPolicy.xml`,
`Hapticsconfig.xml`, the haptics PCM/tuning files and vibrator libraries. ODM
includes `vendor.xiaomi.hardware.vibratorfeature.service`, its init/VINTF
declarations, `libaachaptics.so`, `vendor.hardware.vibratorCL.impl.so` and
waveform firmware. The preserved image path already carries this lower stack;
copying replacement files to vendor staging would not modify that image.

Fresh offline EROFS capture verified the two policy/config files against the
factory vendor image SHA256
`c9c2a03b61cd7c96466f09ffebf723382f430fd1389b1b73186270f3e15dfb20`:

| Factory file | Bytes | SHA256 |
| --- | ---: | --- |
| `/vendor/etc/HapticsPolicy.xml` | 3,975 | `45be7db06467a3eae8823eb189571fa1e9a4fa20d06eec47db7a8e265d1c5e33` |
| `/vendor/etc/Hapticsconfig.xml` | 21,375 | `27be444399dddad40cea831245026cc8018fe696d92f0742b8d905de205fca2a` |

The policy routes predefined effects 0–5 and composition to its open-loop
path, with other routes handled separately. The config contains six predefined
effect rows with low/mid/high values. Five rows have mid=100 and high=90; the
verifier reports this exactly. These fields alone do not establish which
implementation is selected or prove three perceptually distinct, monotonic
strengths. The candidate exposes existing standard strength choices; it does
not rewrite this table or infer a motor-drive calibration from it.

The factory framework has long-press fallback `[0,1,75,76]` and virtual-key
fallback `[0,30,45,53]`, versus the selected AOSP `[0,30]` and `[0,20]`.
They are not imported: preserving their timing semantics would require a
separate consumer/runtime check, and native predefined effects can bypass
fallbacks. No primitive/effect support is fabricated, and the recovery-only
zero-vibration setting is unrelated to normal Android haptics.

The raw factory captures are private under the worktree's ignored
`artifacts/haptics-stock-20260905/`. The exact Nezha product feature XML was
also captured and contains no haptics/vibrator feature keys; it does not supply
an additional framework tuning profile.

## Verification and next build

The offline verifier checks exact bytes, receipt path/size/hash identity,
factory image identity and the capture's non-executing/non-mounted provenance:

```sh
python3 scripts/haptics_controls.py verify-stock \
  --capture artifacts/haptics-stock-20260905/vendor
python3 -m unittest discover -s tests -p test_haptics_controls.py -v
```

Both resource overlays passed local `aapt2 compile` using Android build-tools
37.0.0. This establishes resource syntax only. After the reviewed source merge,
select `NEZHA_HAPTICS_CONTROLS=true` for the successor, build the affected
framework and Settings resources, and inspect the compiled effective values.
Target-files calibration membership can be checked separately:

```sh
python3 scripts/haptics_controls.py verify-delivery \
  --target-files /private/path/to/successor-target-files.zip
```

That check covers the two calibration files, not the complete HAL, image
equivalence, compiled controls or runtime effect quality. Archives carrying
only the prebuilt image require the existing EROFS capture workflow to inspect
the actual vendor image; missing expanded members fail this check.

On a separately authorized installed build, verify the effective overlay and
vibrator capabilities, then compare low/medium/high for touch, notifications,
ringing and alarms; check keyboard off/on and that the global vibration-off
setting still wins. Assess rapid typing, cancellation, suspend/resume and
audible rattle. Change waveform or drive calibration only in response to those
measurements. Retained factory resources and service registration do not prove
the user-visible feel.

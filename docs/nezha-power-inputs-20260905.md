# Exact-stock power-input findings — September 5, 2026

The exact retained factory inputs do **not** currently supply an admissible
Nezha framework power profile. Both `res/xml/power_profile.xml` and
`res/xml/power_profile_kleerin.xml` in the retained `framework-res.apk` contain
the generic 1000 mAh, one-core 400 MHz, 0.1 mA screen-on placeholder. Installing
either would not supply Nezha-specific framework calibration. The inspected six product
and three device-overlay resource dumps have no `xml/power_profile` resource;
this bounded search does not establish that no calibration exists elsewhere.

The September 5 remaining-feature audit also conflated `vendor_wlc_app` with
wireless charging. Exact factory `system_ext_seapp_contexts` maps that domain
to `com.qualcomm.qti.workloadclassifier`; its APK manifest independently
confirms the package. The private `vendor_wlc_prop` type labels
`vendor.perf.workloadclassifier.enable` and `persist.vendor.build.date.utc`.
This is the Qualcomm workload classifier. Its missing integration cannot
establish missing Qi or reverse-charging support.

The original PowerKeeper package separately declares `android.uid.system`.
That creates a required platform shared-UID signing relationship that a
privileged allowlist cannot substitute for. Its manifest requests Xiaomi/MIUI
permissions and controls power/thermal services. It is not selected by this
change. The six factory `power-save-conf.xml` package exemptions are inventoried
without importing them or treating exemption-list differences as charging
failures. Existing charging and thermal behavior remains unmeasured.

## Reproduce the evidence

[`config/nezha-power-evidence.json`](../config/nezha-power-evidence.json) pins the
framework APK, both binary XML members, nine captured system-ext inputs and
the SDK 37 `aapt2` decoder. APKs, model data and raw policy stay in ignored
private artifacts. The system-ext inputs were captured with the maintained
EROFS reader into `artifacts/power-stock-20260905/{system-ext,wlc}` from image
SHA256 `53dd447bf8453f07b9df24e91a9429c2a15b5589b31406747cc62f0fc79cab5e`.
The existing framework APK is SHA256
`9e92be6fde2f503bdee5149fe4528abe6d1c046c701916321a30a037b4fe1f22`.
Extraction mounts no image and executes no firmware.

Run `python3 scripts/power_inputs.py --framework-apk <retained-framework-apk>
--capture-root <private-power-stock-directory> --aapt2 <sdk-37-aapt2>` on one
line. The JSON result distinguishes successful evidence verification from
product admission: `evidence_verified` is true, while
`product_changes_admitted`, `hardware_qualified` and both calibrated-profile
admissions are false. Byte mismatches, changed selection, duplicate paths,
unsafe receipt paths and unrecognized decoding output fail the command.
The verifier reads local captures only and does not emit an overlay or alter
properties, package permissions, policy, firmware or the phone.

The verifier passed against all retained inputs. Its offline tests cover
placeholder rejection, refusal to infer calibration from different numbers,
malformed and duplicate coefficients, XML attribute ownership, WLC identity
and private-context drift, and receipt path/hash mismatches.

## Required follow-up

Locate and validate an actual Nezha calibrated component model before adding
`power_profile.xml`; a valid XML document or a different phone's capacity is
insufficient. A later model needs exact-device provenance and effective
PowerProfile/BatteryStats verification in a built and installed successor.
Track workload-classifier restoration independently, with its app, model/JNI,
platform signing and SELinux/property requirements. Restore charging controls
only from a demonstrated client/HAL contract and measured failure. Wired, Qi,
reverse power, limits, temperature response and idle drain each still require
their own authorized hardware qualification.

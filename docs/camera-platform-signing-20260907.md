# Xiaomi Camera platform-signing source candidate, 2026-09-07

The separate Camera source candidate requests ordinary Android platform signing
for the exact reviewed factory APK. Its source packet has been staged and
verified on the host. **No APK has been signed or installed by this work, and
the candidate is not device-admitted.** The existing presigned Camera generator
and original APK remain available as the baseline.

The unchanged factory CameraOpt `Verifier.getVerifyResult()` first calls
`PackageManagerInternal.isPlatformSigned("com.android.camera")`. It calls the
native `FileUtils.getCacheVerifyResult()` only when that platform-signature
prerequisite succeeds, and returns the native result unchanged. The v8 Camera
and platform APKs have different verified public signers. A legitimate platform
signature can address that first prerequisite; it does not establish that the
native verification result, service initialization or Camera capture succeeds.

## Source selection and input preservation

The [generator](../scripts/camera_platform_product_inputs.py) first invokes the
existing Camera APK packet verifier. That verifier binds the reviewed factory
capture, original APK identity, original public signer evidence, strict library
review and runtime dependency provenance. The new packet uses a separate
namespace and module:

| Setting | Candidate |
| --- | --- |
| Selector | `NEZHA_CAMERA_PLATFORM_SIGNED=true` |
| Required selectors | `NEZHA_XIAOMI_CAMERA=true`, `NEZHA_CAMERA_FRAMEWORK=true` |
| Public selector fragment | `device/xiaomi/nezha/camera-platform-signed.mk` |
| Private source namespace | `vendor/xiaomi/nezha-camera-platform` |
| Product include | `vendor/xiaomi/nezha-camera-platform/camera-platform-product.mk` |
| App module | `NezhaXiaomiCameraPlatform` |
| Package and installed APK filename | `com.android.camera`, `MiuiCamera.apk` |
| Partition | `system_ext` |
| Soong signing property | `certificate: "platform"` |

The selector is off by default and rejects malformed values or missing
dependencies. Product integration must choose exactly one of this candidate and
the original `vendor/xiaomi/nezha-camera/camera-product.mk` include. Selecting two
modules for the same package is not a supported integration.

The candidate removes the original import's `presigned` and `preprocessed`
properties because Soong requires one signing mode. The retained Soong source
has `preprocessed` imply `presigned` at `app_import.go:393`, requires exactly one
certificate mode at line 401 and invokes `SignAppPackage` for a certificate-based
import at line 516. The source SHA256 is
`872d75d0a9002e51d1c48b755738426ca3f65021b74e554d8937f8d0bade87c2`.
This source path may normalize ZIP compression and alignment as part of its
ordinary import/signing process. Final uncompressed payload entries must be
compared after a real build; source staging cannot prove final APK contents.

The staged APK remains 204,365,218 bytes with SHA256
`7bce1fb140802511bb3d6527f6fcc25ef7558f278d24229755413d3a9b42199e`.
No DEX, resources, native libraries, manifest or verification code was edited.
The generated host producer hashes every declared input before publishing that
same original APK for Soong. Its input list includes the new signing-policy
record, Blueprint, product include, permission XML and original provenance.

`enforce_uses_libs: true` and the original ordered optional providers
`miui-cameraopt`, `androidx.window.extensions`, `androidx.window.sidecar` remain.
The new candidate adds no missing-library exception, preprocessed-check skip,
dexpreopt disablement, public PackageManager exception or verifier replacement.
The [source contract](../config/nezha-camera-platform-signed.json) records the
candidate's boundaries and outstanding build/device evidence.

## Signer transition and privileges

The factory Camera public certificate SHA256 is
`c9009d01ebf9f5d0302bc71b2fe9aa9a47a432bba17308a3111b75d7b2149025`.
The measured v8 `framework-res.apk` and `SystemUI.apk` certificate SHA256 is
`c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`.
The retained public APK verification found no signing lineage for those
artifacts. A future delivery must verify its actual final platform signer;
the source keyword `platform` alone is not final artifact evidence.

Changing the signer is an application identity transition. Existing installed
Camera package records, updates and private app data cannot be assumed to
migrate to the new signer. No compatible lineage or data-preserving transition
has been established. This candidate performs no uninstall, data deletion,
package-manager reset, migration or device replacement. The actual transition
must be reviewed before a device operation is selected.

The reviewed manifest requests three pure platform-signature permissions:
`CONTROL_DEVICE_STATE`, `CONTROL_DISPLAY_BRIGHTNESS` and `INJECT_EVENTS`.
Platform signing makes the app eligible for those permissions under the normal
platform signature rules, subject to the final platform's permission policy.
They are not added to the generated privileged-permission XML: the existing
eleven reviewed privileged entries remain unchanged. Actual installed grants
must be measured. The new signer also changes the trust relationship for
Camera's own signature permissions and any OEM signature-protected interfaces;
continued interoperability with separately OEM-signed packages is unverified.

SELinux identity must be assessed independently from PackageManager signature
identity. The retained composed policy maps both the original Camera
certificate in `vendor_mac_permissions.xml` and the v8 platform certificate in
`plat_mac_permissions.xml` to `seinfo=platform`. Its generic app-UID platform
rule selects `platform_app` and `app_data_file`. Thus that retained policy does
not predict a domain change solely from this re-signing. It also does not prove
the selected successor's generated policy or installed labels. The candidate
adds no MAC rule and retains normal Android enforcement; final `seinfo`, process
domain, data labels and required access still need measurement.

## Evidence and next admission gates

The ignored source packet is
`artifacts/camera-apk-inputs/platform-system-ext-candidate-20260907/`.
Host stage and independent readback verification receipts are retained under
`reports/camera-completion-20260907/xiaomi-app/camera-platform-source-*.json`.
The generated host producer separately verified all 13 declared inputs in the
14-file source packet and published the exact original APK bytes. This is a
host input-integrity check; it invokes no Android build or signing operation.
The original verifier bytecode, public certificate comparisons and original
factory native dependencies are recorded in the adjacent `hawk/` reports.
The bounded public-certificate MAC mapping review is recorded in
`camera-platform-mac-review.json` with the ten retained policy input hashes.

The offline run of `test_camera*_product_inputs.py` passed 16 test methods:
11 new candidate tests and five existing baseline tests. The new tests execute
26 actual GNU Make cases and 18 host producer cases, including same-length hash
changes to each of the 13 declared inputs and rejection of missing, duplicate,
unknown or extra input arguments. They also recompute the public config pins
and compare the candidate's app-import properties with the original generator.

A real selected build must prove a single Camera package, strict library
resolution, successful normal signing, the final platform public signer and
unchanged uncompressed non-signature APK entries, including all DEX, resources,
manifest and native libraries. Device acceptance additionally requires the
reviewed signer/data transition, installed permission and MAC evidence, genuine
CameraOpt service/JNI initialization, the unchanged complete verifier's actual
result and Xiaomi Camera capture. Staging this source candidate establishes none
of those later results.

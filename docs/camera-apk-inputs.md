# Camera APK admission after the DEX provider work

The captured Xiaomi Camera APK remains unselected for the first Evolution X
boot. Preserve its original bytes and signature, and continue the separate
[nine runtime dependency integration](camera-runtime-inputs.md). Selecting the
APK now would require changing its signing or privileged packaging contract;
neither is justified by the available evidence. This does not change ROM
readiness or establish Camera/Leica support.

The August 29 [admission record](../research/camera-apk-admission.json) adds
fresh host checks and a bounded private-API call-site review. It supplements
the [original APK review](camera-apk-integration.md), whose statement that the
DEX provider extension was unimplemented is historical: the extension is now
installed and its five native Soong fixtures passed, including eleven
subtests, with zero failures or skips. Those synthetic graph tests did not
build this APK or execute proprietary code. See the separate
[native fixture evidence](dex-import-uses-library.md).

## Reproduced packaging blocker

The unchanged 170,279,563-byte APK is version `6.3.007010.0`, SHA256
`cadf2c07cb6fd25c06f7fe6f37dc227df204bed3a873b3025aff93d53d72da79`.
Its v3 signature verifies again, and all 9,477 ZIP entries pass CRC checks.
It remains a supplied modified Xiaomi.eu/live-capture match, with unverified
factory origin. Eight DEX entries are compressed; forty bundled JNI libraries
are uncompressed. The earlier 4 KiB ELF findings are unchanged, not a new
native-linking or device test.

The pinned Soong validator again rejects both applicable attempts:

| Unchanged APK configuration | Actual standalone result |
| --- | --- |
| Presigned without `preprocessed` | Exit 1: target SDK 35 requires preprocessed handling |
| Preprocessed and privileged, with privileged DEX uncompression required | Exit 1: compressed DEX entries |

The latter check is separate from Soong's decision not to rewrite a
preprocessed APK. Disabling module dexpreopt would not remove it. No supported
per-APK compression exemption was found in the pinned importer. Repacking DEX
would invalidate the existing v3 signature. The global compression policy,
preprocessed checks and strict uses-library checks remain unchanged.

The strict standalone manifest check passes with exactly three optional
libraries, in order: `miui-cameraopt`, `androidx.window.extensions`,
`androidx.window.sidecar`. There are no required declarations. The other three
selected Camera JARs must not be added as direct APK declarations. A future
APK build must still verify its actual strict command and class-loader context.

## Signing and inspected feature paths

The retained certificate SHA256 is
`f87bd41b5bf1d78023a823b29a40e08ad3d90e7570c96f01d6a804b47245e869`.
It differs from the inspected default platform certificate; the future release
signer is not established. A privapp allowlist alone cannot grant the three
requested pure `signature` permissions to a differently signed app. The APK
does not declare a shared UID.

Twelve method disassemblies narrow the feature questions without proving
complete startup compatibility:

| Requested signature permission | Inspected related path |
| --- | --- |
| `CONTROL_DISPLAY_BRIGHTNESS` | Temporary auto-brightness adjustment/reset and crash cleanup; the adapter catches failures |
| `INJECT_EVENTS` | Remote-control motion/key handlers check a registered client and call an adapter that catches failures |
| `CONTROL_DEVICE_STATE` | Reflected state request in flat-selfie display switching returns false on reflection/invocation failure; cancellation is conditional and guarded |

Activity startup's inspected device-state references register callbacks; they
are not state-changing requests. These findings do not prove launch without
grants or that every affected feature is optional. System-service enforcement,
remote-service authorization, remaining OEM dependencies, native/reflected
paths and hardware behavior were not comprehensively audited. No broad
permission grant follows from this inspection.

## Next admission boundary

An original-signature privileged import needs a compatible, properly signed
input satisfying the selected DEX packaging policy. A different signing route
requires a separate review of update identity, OEM trust relationships,
permissions and feature scope before transforming anything. A nonprivileged
import is also a feature decision, not an approved way around the check.
After resolving those inputs, build the real APK with exact library providers,
inspect installed permissions and class-loader outputs, and conduct authorized
device tests. First platform boot can proceed without selecting this APK.

The private receipts retain tool/source hashes, unchanged-input checks and
unfiltered output. The first call-site capture rejected an unexpected empty
stderr; its failed harness record remains alongside the successful rerun with
an explicit Java environment. Existing Camera APK, runtime-input and DEX-patch
offline checks passed **42 tests, zero skips**. A mistyped discovery pattern
ran zero tests and is retained as a failed invocation, not counted as a pass.
These results are separate from Android artifact builds and phone tests.

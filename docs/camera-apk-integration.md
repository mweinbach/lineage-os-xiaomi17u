# Camera APK import prerequisites

The captured Camera APK has a valid existing v3 signature and passes the ZIP
and ELF layout checks for Nezha's observed **4 KiB kernel**. No APK was imported,
rewritten, signed, installed or executed. The next integration work is concrete:
provide the Java class-loader metadata that Soong requires, resolve the APK's
privilege/signing/DEX-packaging contract, and verify the authored strict-check
override in a new build configuration.

The [sanitized record](../research/camera-apk-integration.json) preserves the
observations, tool hashes, source pins and remaining gates. This is separate
from the [nine selected Camera dependency modules](camera-inputs.md), which do
not include the APK, and from [actual build progress](build-progress.md).

## APK identity and signing

The input remains the 170,279,563-byte `com.android.camera` APK, version
`6.3.007010.0` / `630070100`, from
`/product/priv-app/MiuiCamera/MiuiCamera.apk`. Its SHA256 is
`cadf2c07cb6fd25c06f7fe6f37dc227df204bed3a873b3025aff93d53d72da79`.
It matches both the earlier live collection and the supplied modified Xiaomi.eu
package. The package's origin remains unverified and its retained AVB failures
are unchanged; a successful APK signature check does not authenticate Xiaomi
factory provenance.

Both the earlier decoded manifest and a fresh SDK 36.0.0 `aapt2` read show no
`sharedUserId` or `sharedUserMaxSdkVersion`. The manifest does not require a
shared system UID. It declares minimum SDK 29, target SDK 35 and
`extractNativeLibs=false`; these do not establish runtime compatibility.

SDK 36.0.0 `apksigner verify --verbose --print-certs` succeeds with one RSA-2048
signer and v3 verification. Its certificate SHA256 is
`f87bd41b5bf1d78023a823b29a40e08ad3d90e7570c96f01d6a804b47245e869`.
The other reported signing schemes do not verify. This certificate differs from
both pinned default public certificates inspected in `build/make`: platform
`c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8` and testkey
`a40da80a59d170caa950cf15c18c454d47a39b26989d8b640ecd745ba71bf5dc`.
No private key was read. The installed platform signer and future release
signing identity were not established by this comparison.

The APK requests three permissions whose pinned platform definitions have
exactly `protectionLevel="signature"`: `CONTROL_DEVICE_STATE`,
`CONTROL_DISPLAY_BRIGHTNESS` and `INJECT_EVENTS`, all under `android.permission`.
A privileged-permission XML alone does not grant those permissions to a
differently signed app. Other permission definitions have additional flags and
must be reviewed separately; effective grants and feature impact are untested.
[Pinned platform permission definitions](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/core/res/AndroidManifest.xml)

## Packaging and page alignment

All 9,477 ZIP entries passed streaming CRC checks, and the APK hash remained
unchanged after the tools ran. All 40 bundled AArch64 libraries are stored
uncompressed. SDK `zipalign -c -P 4 -v 4` and `-P 16` both pass; an independent
ZIP-header parse also finds every JNI data offset aligned to 16 KiB.

ELF program headers give a different, narrower result: all 40 libraries satisfy
4 KiB `PT_LOAD` alignment and offset/address congruence, while 37 satisfy the
same 16 KiB checks. `libHawk.so`, `libavif_android.so` and `libpendant.so` have
4 KiB load alignment and fail the 16 KiB congruence check. Pinned NDK 28.2
`llvm-readelf` independently confirms these three exceptions and a 16 KiB
control library. This does not block the observed 4 KiB layout; passing ZIP
alignment does not prove 16 KiB ELF suitability or successful native linking.

All eight `classes*.dex` entries are compressed. The observed candidate has
`UncompressPrivAppDex=true`. Running the pinned preprocessing validator against
the unchanged APK produces these results:

| Standalone check | Result |
| --- | --- |
| Presigned, without `preprocessed` | Fails: target SDK 35 requires `preprocessed: true` |
| Preprocessed, nonprivileged policy | Passes packaging checks |
| Preprocessed, privileged policy with DEX uncompression required | Fails: compressed DEX files |

`preprocessed: true` preserves the existing signature through a validated copy
and implies presigned handling. The nonprivileged pass is not a recommendation
to remove privileges to avoid the failure. No compression policy was changed
and no preprocessing check was skipped. These are standalone host checks, not
an `android_app_import` build. [Pinned APK checker](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/scripts/check_prebuilt_presigned_apk.py),
[pinned import handling](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/java/app_import.go)

## Java names and class-loader metadata

The APK declares no required Java shared libraries. Its optional declarations,
in order, are `miui-cameraopt`, `androidx.window.extensions` and
`androidx.window.sidecar`. The other three captured system-ext JARs are not
direct manifest `uses-library` declarations and must not be added to that list
merely because they are selected build inputs.

The pinned manifest checker passes with those exact three names and fails when
`miui-cameraopt` is replaced by the current module name
`nezha_system_ext_framework_miui_cameraopt_jar`. A fully qualified
`//vendor/xiaomi/nezha:miui-cameraopt` name also passes this name-only check;
namespace trimming does not prove that a matching module or provider exists.
[Pinned manifest checker](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/scripts/manifest_check.py)

Renaming alone is insufficient. The pinned `dex_import` has neither the
`UsesLibraryDependency` install-path/class-loader methods nor a
`provides_uses_lib` property. Its Java provider therefore lacks the metadata
used by an APK's `optional_uses_libs` dependency. This conclusion comes from
source inspection, independently hash-matched to the guest checkout; no APK
dependency graph was built to reproduce the expected error. A future provider
extension must expose the actual DEX/install paths, declared class-loader
context and observed runtime name, with focused graph tests. No such extension
is active. [DEX importer and provider construction](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/java/java.go),
[APK class-loader handling](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/java/app.go)

The pinned platform already defines `androidx.window.extensions` and
`androidx.window.sidecar` as installable system-ext `java_library` modules with
their permission XMLs. Their source definitions support using platform modules;
stock window JARs need not be copied merely to provide these names. Runtime
behavior with Xiaomi Camera remains unverified. [Pinned WindowManager definitions](https://github.com/Evolution-X/frameworks_base/blob/8140698cc12983deecdbd434220affb5f931bfc6/libs/WindowManager/Jetpack/Android.bp)

## Observed policy versus the authored strict fix

The review observed `RelaxUsesLibraryCheck=true` in the Camera-v2/device-v4
build configuration, while dexpreopt itself remained enabled. Its source is
the unconditional `RELAX_USES_LIBRARY_CHECK=true` in
`vendor/extras/bcr/bcr.mk:6`, inherited through the telephony product, whose
`TARGET_INCLUDE_BCR` defaults to true. The generated JSON observation must not
be described as strict APK validation. [Pinned BCR assignment](https://github.com/Evolution-X/vendor_extras/blob/c401d732c0475b7010c205a2e9bfb0fd6888d0be/bcr/bcr.mk),
[telephony inheritance](https://github.com/Evolution-X/vendor_evolution/blob/11d2966a3294a0a692fc958127c770cfe9c00a3c/config/telephony.mk)

Commit `91832e011a2703e73fd093afc7b0ee0f0ad5704d` authors
`RELAX_USES_LIBRARY_CHECK := false` at the end of Nezha's
[BoardConfig](../device/xiaomi/nezha/BoardConfig.mk), with a guard rejecting a
conflicting effective value. The local v5 admission contains that fix. **At
this snapshot, v5 was not installed and no new generated configuration had
verified the override.** The earlier running build used v4.

The location follows the pinned include order: `envsetup.mk` loads product
configuration at line 351, then board configuration at line 368. Later,
`config.mk:1324` loads `soong_config.mk`, which includes the dexpreopt
configuration. That file respects an already-set relaxation value and then
makes it read-only. Setting only `PRODUCT_BROKEN_VERIFY_USES_LIBRARIES=false`
cannot override BCR's existing global assignment.
[Pinned include order](https://github.com/Evolution-X/build/blob/a438ca40c6ed779042f806142b1165ba1360a7b2/core/envsetup.mk),
[dexpreopt variable handling](https://github.com/Evolution-X/build/blob/a438ca40c6ed779042f806142b1165ba1360a7b2/core/dex_preopt_config.mk)

The next admitted configuration must show `RelaxUsesLibraryCheck=false`,
`DisablePreopt=false` and `OnlyPreoptArtBootImage=false` in
`dexpreopt-lineage_nezha.config`, plus `WithDexpreopt=true` in
`soong.lineage_nezha.variables`. Actual APK manifest-check commands must omit
`--enforce-uses-libraries-relax`. Authored settings and offline tests do not
replace that generated-config and command verification.

## Unresolved decisions and evidence

Preserving the captured signing identity requires packaging that passes the
chosen privilege contract. For the observed privileged policy, that means a
properly signed input with uncompressed DEX. Any separately authorized
transformation/signing route needs an approved identity, original/output hashes
and review of signature-sensitive integrations and update behavior. A normal-app
scope requires an explicit feature/permission review; the passing host check
does not authorize it as a workaround. No permission, signature, compression,
uses-library or ELF bypass is proposed.

The private review receipt is
`reports/camera-apk-import-review-20260827/receipt.json`, SHA256
`2b0732ea80574aecd436a9e2e2177fc4fdef750599dc802519368c90bbf767a2`.
It hashes 66 evidence files, including verifier outputs, source snapshots,
read-only guest configuration observations and the 649-test workspace run.
The v5 admission is
`artifacts/device-candidates/nezha-xiaomi-eu-framework-v5/admission.json`, SHA256
`b08915e0328cb87da5829bc55df2a2b851bbdfad6981ef08c3bab9a50adc7ca7`.

Only hashes, safe attributes and source references are published here. APK,
decoded manifest, certificate output and detailed logs remain ignored. The
offline consistency tests need no private files, network, phone or container.
The full dependency graph, enforcing policy, actual permission grants and
native Camera/Leica behavior still require their own corresponding tests.

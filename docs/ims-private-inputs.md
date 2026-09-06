# Reproducible Nezha IMS inputs

The exact-stock Android IMS candidate now has maintained module templates and a
build-time input producer. A separate reviewed framework patch now supplies the
one missing API used by the inspected IMS callsites. **IMS is still not enabled.**
That patch still needs component integration, and SELinux domain/mapping work
remains open; the packet cannot waive those checks.
Package7 and the source successor retain their existing IMS limitation.

This change promotes the previously ignored September 4 candidate into the
tracked [input contract](../config/nezha-ims.json),
[module template](../templates/ims/Android.bp.in) and
[generator](../scripts/ims_inputs.py). The new work beyond that earlier candidate
is an actual `python_binary_host`/`genrule` producer: every private filegroup now
consumes a named **verified output**, rather than an unchecked proprietary path.
The producer embeds the reviewed hash/size identities, validates the entire
input set before writing any output, preserves the original bytes and rejects
duplicates, mixed source roots, symlinks, changed bytes and existing outputs.
Its identity list does not come from an editable success receipt.

## Delivered source definitions

The 20 private inputs total 3,899,108 bytes: the original Xiaomi-signed
`org.codeaurora.ims` APK, three DEX JARs, three library-registration XMLs and
thirteen native libraries. Twelve native inputs belong to the provider closure;
`libdiagatbparser_system.so` is modeled as a separate optional diagnostic module
and is not required by the APK. Reproduction includes it to preserve the full
reviewed candidate.

The 24 public modules retain the measured install paths and dependency graph:

- The three `dex_import` modules retain system-ext/product placement and exact
  XML registration. The APK requires all three libraries in manifest order.
  Preserve the existing [DEX import support](dex-import-uses-library.md).
- The thirteen native modules retain AArch64, explicit shared dependencies,
  `check_elf_files: true`, `allow_undefined_symbols: false` and unstripped bytes.
  Existing Evolution libraries are reused for the platform side of the graph.
- The two `install_symlink` modules retain the original app-local JNI targets.
  The historical source inspection was pinned to Soong
  `cbcbea9e65503ca15b363a0b06dda88fdbcb0154`, with `install_symlink.go` SHA-256
  `f7a5540b20f9c0ae05b9a69dfb90b407dae847b61e13bc88f7f90353ea6a9b3e`.
  This is retained source evidence, not a current guest graph test.
- The presigned, preprocessed privileged APK retains strict uses-library checks.
  Its six-permission privileged allowlist and two permission/GID declarations
  are separate authored templates. They do not grant pure-signature permissions.
- The only TeleService selector is `config_ims_mmtel_package=org.codeaurora.ims`.
  No RCS, GBA, carrier override or blanket device capability toggle is added.

All 24 modules remain `enabled: false`. Both generated build definitions are
named `Android.bp.in`, so simply placing this packet in an Android directory
cannot add it to Soong's module discovery. There is no product include snippet
to apply now. The generated `admission.mk` deliberately raises a Make error if
someone includes it before implementing the missing contracts.

## Offline use

Run from this worktree. Supply a private root containing the contract's
`proprietary/` hierarchy, such as the retained original IMS bundle. The source
root is read-only. The output must be a new directory beneath this worktree's
ignored `artifacts/`, with an existing parent directory.

```sh
python3 scripts/ims_inputs.py prepare \
  --private-root /absolute/private/ims-bundle/vendor/xiaomi/nezha-ims \
  --output artifacts/ims-candidate-review
python3 scripts/ims_inputs.py verify --packet artifacts/ims-candidate-review
python3 scripts/ims_inputs.py assert-ready --packet artifacts/ims-candidate-review
```

`prepare` and `verify` return zero only for exact content. `assert-ready` verifies
the same packet and then returns **2** with the open engineering gates. Setting
a receipt's `activation_allowed` field to true does not change this behavior.
There is no force-enable option. Existing output directories are preserved;
choose a new name for a revised packet.

The generated private `tools/verify_inputs.py` is the Soong producer. Its
`--output-dir` is `$(genDir)` and its arguments are the declared `$(in)` set.
Every public private-filegroup reference resolves through the producer's
`verified/proprietary/...` outputs. No proprietary JAR, XML, shared library or
APK is committed by this workflow.

## Open integration gates

1. The APK calls `android.telephony.TelephonyBaseUtilsStub.isMiuiRom()Z`, absent
   from the inspected Evolution provider set. The
   [new API patch](../patches/evolution/nezha-ims-telephony-api.patch) now implements
   the exact normal factory predicate, as detailed below. Integrate and build it
   with the final framework and verify the resulting DEX descriptor and package
   eligibility before activating the provider. The packet's original pinned
   activation gate remains closed until that integration is proven.
2. The intended `vendor_qtelephony` source domain, IMS seapp selection and public
   mapping must be restored as one compatible slice against the retained vendor
   policy. The retained MAC audit already found the original signer assigned
   platform seinfo; re-signing solely for seinfo is unnecessary. No permissive
   domain, neverallow relaxation or access-control bypass is introduced.
3. Necessary signature/privileged/runtime permissions and the `audio` and
   `oem_2901` groups still need final-source and functional validation. Preserve
   the OEM signer. Pure-signature requests cannot be granted by a privileged
   allowlist, and a requested permission alone does not prove a required path.
4. Execute actual strict app/dexpreopt, ELF symbol/version/namespace, JNI,
   SELinux, and signed-image delivery checks on the final source successor.
   Retained symbol-name matching is not complete runtime linker closure.
5. After separately authorized installation, validate carrier provisioning,
   MMTEL registration and ordinary incoming/outgoing calls. Emergency behavior
   requires an approved procedure; this change makes no emergency-call claim.

The next source-enabling change must integrate the API patch, resolve policy,
adapt the templates and install the guarded producer into the selected source
graph, then prove component and image results. Merely renaming `.bp.in` files or
flipping `enabled` does not close these gates.

## Narrow framework API implemented September 5

[The source contract](../patches/evolution/nezha-ims-telephony-api.json) binds a
32-line new hidden framework class with the exact public static `()Z` method.
It reads the real `ro.miui.ui.version.name` property, then the real
`ro.miui.ui.version.code` property if needed, each with an empty-string default.
Either nonempty value means true, including `0`, `false` and whitespace. No
property is written, synthesized, parsed as a boolean or cached.

The inspected original IMS code uses this one method at four sites:

| IMS caller | Predicate controls |
| --- | --- |
| `ImsSubController.handleRadioAvailable` | Primary-radio multi-SIM voice-capability query |
| `ImsSubController.registerForRadioEvents` | Available-radio multi-SIM voice-capability query |
| `ImsServiceSub.onStackConfigChanged` | Non-MIUI automatic-reject configuration path |
| `ImsServiceStateReceiver.updateHDIcon` | Non-MIUI HD-icon presentation path |

Retained factory DEX analysis traces the original method through a cached
provider object to this predicate. The result itself is recomputed for each
call. The compatibility patch implements the observed normal-provider behavior
needed by those four sites. It does not reproduce the unrelated plugin-loading
architecture, reflection failure behavior, automotive provider or additional
methods from the larger OEM interface. Both properties absent returns false;
that does not claim arbitrary plugin failures are modeled.
The saved Package7 feature capture does not establish both properties' effective
values. Do not assume the result is false on Evolution: preserved nonempty OEM
properties can select MIUI-specific call paths. During authorized device
qualification, capture both actual property values and the resulting behavior
at the IMS callsites before judging the adapter's runtime compatibility.

The selected framework revision is
`8140698cc12983deecdbd434220affb5f931bfc6`. Its
[telephony filegroup](https://raw.githubusercontent.com/Evolution-X/frameworks_base/8140698cc12983deecdbd434220affb5f931bfc6/telephony/java/Android.bp)
includes Java sources recursively, and its root build definition includes that
filegroup in the framework. A new file at
`telephony/java/android/telephony/TelephonyBaseUtilsStub.java` is therefore selected
without changing the module graph. The class is `@hide`, keeping it out of the
public SDK; no API allowlist or permission grant is added.

The exact original APK already declares `usesNonSdkApi=true`. The selected
[ApplicationInfo implementation](https://raw.githubusercontent.com/Evolution-X/frameworks_base/8140698cc12983deecdbd434220affb5f931bfc6/core/java/android/content/pm/ApplicationInfo.java)
permits that existing manifest contract for system/updated-system applications.
With the candidate's system-ext placement, this provides a standard hidden-API
eligibility path without changing the signer, seinfo, global enforcement or
package allowlists. Final package flags and DEX linkage still need readback.

The upstream `bka` head was checked and recorded as
`929be7281ce09a311d262c83415db04e9f127adb`; this patch deliberately targets the
source lock above. The two build-definition files and `ApplicationInfo.java`
were fetched by that locked revision into an isolated ignored public-source
snapshot. Their hashes and `git apply --check` passed. The API did not exist at
its target path in that locked upstream source. No original source checkout was
changed, and no claim is made about an uninspected future branch revision.

Run the optional host validation with a local JDK:

```sh
python3 scripts/test_nezha_ims_api.py
```

Add `--source /absolute/frameworks/base` to perform a read-only check of the
three source-basis hashes and absence of a conflicting API before the JVM test.
Changed source control files or an existing target implementation require review.
This checker does not apply a patch or assert an installed source revision.

## Validation recorded September 5

- 21 standard-library offline tests pass, including execution of the generated
  input producer, mutation rejection, duplicate/mixed-root rejection, preservation
  of existing outputs and inability to forge activation through a receipt.
- Exact retained private inputs were reproduced into
  `artifacts/ims-candidate-20260905-v2/` in this isolated worktree and independently
  verified: 20 inputs, 3,899,108 bytes. The original retained bundle was read only.
- The generated producer was executed on those real inputs into separate ignored
  `artifacts/ims-build-guard-check-20260905-v2/`; all 20 output SHA-256 values
  match the tracked contract. This validates the Python producer, **not Soong**.
- `assert-ready` returned 2 as designed. No component build, source sync, signing,
  VM operation, phone access or installation was performed by this slice.
- Eight additional standard-library tests pass for API patch integrity, exact
  source reconstruction, read-only applicability checks and compiler-failure
  handling; they mock the JVM commands and require no JDK. The separate actual
  JVM run passed **52 assertions** for ABI, truth-table edge cases, short-circuit
  ordering, empty defaults and repeated property reads. JVM API doubles do not
  establish Android framework, hidden-API or carrier runtime success.

The underlying evidence remains in the private
`reports/flash-ready-20260904/deadline-radio/ims-candidate/` records, including
`input-manifest.json`, Java closure and factory-method analysis, native closure,
app permission review and source-pinned `install_symlink` inspection. The
[remaining-feature audit](package7-remaining-feature-audit-20260905.md) explains
the user-visible IMS gap.

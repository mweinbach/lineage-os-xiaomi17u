# Native ROM integration after v11b

The **policy-only-v13h-1** source build passes at **2026-08-30 05:40:07 UTC**:
31 goals and 273 Ninja actions after configuration, with unchanged source inputs
and verified sandboxing. The installed v13ha policy subsequently passes
**analysis-v13h-policy-only-v1** at **13:12:51 UTC**, with all 6,366 original
assertions plus four provider assertions, nine fresh checks and three
zero-permissive binaries. Independent capture review has no findings, and the
matching native digest derivation passes six checks with zero skips. Provider
runtime, image adoption and hardware remain unverified. The later separate
4 KiB ELF/symbol result is recorded below.

The matching **policy-images-v13h-v1** raw EROFS reconstruction now passes nine
checks and 38 commands with zero skips. Independent review confirms both
identical TAR/image/export sets and the exact five policy replacements, with
all other contents and semantic metadata retained. Original images remain
unchanged; this is not image adoption, AVB, partition-fit or boot evidence.
The subsequent keyless footer run passes six native checks and sixteen commands,
preserving both raw prefixes and verifying FEC and exact package budgets.
The signed parent chain and physical partition fit remain separate gates. The
**v13i** allocator component build and independent output review now pass.
Its partial VINTF run has an explicit skipped matrix-definition subcheck;
the fresh producer descriptions are admitted, but full compatibility remains open.
The first 26-goal provider ELF build and four-goal follow-up produce a distinct
inventory of four passed checks and twenty-two alignment failures at 16 KiB.
The follow-up's complete readback and independent evidence review pass. The
user now authorizes a checked 4 KiB first-boot baseline; the corrected **v13ja
source is installed**, and the 37-goal **pagesize-v13j-1** component build passes
at **2026-08-31 00:43:11 UTC (August 30 in New York)**. Generated settings now
verify 4096 with prebuilt checks enabled. The separate **26-provider ELF/symbol
checks pass freshly at 01:15:10 UTC**; that result does not itself establish
VINTF or runtime validation. The first full VINTF run reaches the combined command and fails on
155 device HAL instances absent from the framework matrix. All earlier 16 KiB
evidence is preserved. The inactive Camera stage and
maintained delivery candidates do not bypass the remaining native gates.
Commit **c3686ed** provides the reviewed [framework-matrix projection](framework-matrix.md)
for the exact 155 missing tuples. The **matrix-v1 source transaction is now
installed**. Its 38-goal native command completes with exit 0 and 128 Ninja
actions after 163 frontend steps, producing new matrix outputs, but the wrapper fails an XML postcheck
that requires explicit default AIDL version 1. The separate corrected read-only
postcheck and independent review now pass. The later ordinary 27-goal provider
installation and full raw review pass with 29 fresh copies and two preserved XML
outputs. Fresh producer/input captures now lead to a separate successful
four-command VINTF run on matrix-v1. Its fifteen postflight checks and final
independent raw/coverage/materialization reviews pass. Complete input compatibility remains
false: the combined check has no reported skips/warnings, but the separate
framework-consistency path retains one definition skip and two warnings. The
earlier full-run failure is preserved, not relabelled by this later success.

The source subsequently advances to **packaging-matrix-v1** at
**2026-08-31 08:13:39 UTC**. Eight committed operations and their complete readback
select reviewed packaging inputs while preserving the prior native outputs.
Independent transaction review is clear. No build has run from that source
selection; the matrix-v1 component, VINTF and crypto results retain their exact
earlier scope, and the three normal policy-sidecar modules remain required.
The later **first-target-files-v1** source selects the construction guard and
pinned-date patch 0012 at **08:45:28 UTC**. Its 478-file vector is recorded below;
native dispatch, generated build metadata and the first build remain unverified.
The original guard reads `TARGET_RELEASE` after the pinned release configuration
forbids direct access. The current **first-target-files-release-flags-v1** source
corrects that one file at **09:17:15 UTC**, retaining the source count and prior
outputs. Independent correction review passes for the recorded installation;
effective partition properties, metadata-file freshness and target-files builds
remain unverified. The subsequent selected-input closure is sealed, and two
corrected native queries pass 28 selected value checks. The three preflight
failures and fourth attempt's native obsolete-variable failure remain preserved.
The original `nothing1` command exits zero but fails two exact generated-state
checks. The later **nothing2** run passes current source/configuration and six
metadata-value checks, with independent review complete; fresh file rewrites
and image reproducibility remain unverified. The current leading blocker is
full Evolution policy selected by `LINEAGE_BUILD`, which was absent from the
earlier configuration. Retained policy/VINTF results do not establish full
current-policy or image compatibility. Commit **5d557a0** now provides the
explicit [Evolution-base source/reference integration](evolution-policy-base.md),
with repeated host bundle verification. These new inputs are not installed in
the VM; native policy/context and image-compatibility checks remain pending.

The independent **analysis-v12f-export4-v1** native verification passed at
**2026-08-30 02:13:44 UTC**, retaining all 6,366 original assertions, exact
reviewed property effects and zero permissive domains in three binaries.
Source/M4, API mapping, compiler, OEM guard and nine fresh check bindings pass.
This is the preserved baseline for the later v13h comparison. The earlier
v13f bootstrap failure is preserved. Current provider-policy verification and
the older five-file image derivation are distinct evidence; image adoption remains
separate. The Camera/mi_ext/recovery
phase and bounded producer review pass, with all eleven installed base payloads
inspected. Runtime API closure, Camera APK integration and a complete signed
boot chain remain unverified.

The later isolated native **policy-images-export4-v1** reconstruction passes
nine checks and 38 commands with zero skips. Two independent complete
TAR/image/export sets reproduce the exact five policy changes for the sealed
v12/export4 baseline. These raw EROFS outputs remain unadopted and do not validate
current source inputs, AVB, partition fit or boot.

The expanded **policy-v12f-export-1** build passed at **2026-08-30 00:16:57 UTC**
(August 29 in New York), installing the missing runtime CIL/mapping outputs and
freshly executing the compiler, OEM guard and nine factory checks. Its 35 main
Ninja actions follow 162 configuration steps. The first independent verification
passed runtime/compiler equality but stopped before semantics while hashing a
build tool larger than its reader bound. Host rehearsal then verified the exact
aggregate-property representation and reviewed effect budgets. Export3 later
ran natively, producing a verified semantic comparison and nine fresh check
records before its M4 source guard rejected newline interleaving. The successful
export4 correction below is a separate result; export2 remains held.
[v11b](oem-policy-integration.md) remains the preserved comparison baseline.

The first **v12e** build remains a recorded Kati failure at **22:19:27 UTC**:
`build/make/core/Makefile:4776` read undefined `BOARD_MI_EXT_IMAGE_NO_FLASHALL`
before any requested native policy action ran. The correction passed 99 native
Kati fixture cases and was installed as **run-v12fa at 23:22:28 UTC**. The later
successful build is separate evidence; no failed or unexecuted check is counted
as a pass.

The [machine-readable record](../research/native-rom-integration.json) binds
each claim below to private receipts and hashes. No complete ROM, framework
image set, target-files, super image, OTA or first Evolution boot is established.
No phone was accessed during this integration.

## Installed inputs

The original v12e transaction uses a frozen public control snapshot from workspace commit
`8aaa347be95e8a83c86c5b21b07b6f93c6ce31cf`. Later host commits are not silently
included. The platform remains Evolution `bka` / `bp4a`, manifest
`cc4ebb8db9750afba6049825127304b09327f7c1`, with the existing 1,179-project source
lock and Repo revision. The source and outputs remain on the existing ext4
volume; no new VM, attachment or sync was created.

| Installed slice | Scope |
| --- | --- |
| Four OEM properties | Source/M4 inputs for `vendor_mm_parser_prop`, `vendor_sys_video_prop`, `vendor_persist_dpm_prop` and `vendor_wlc_public_prop`; four source files and two reviewed `get_prop` uses, not edited generated CIL |
| Camera runtime inputs | Four exact DEX library names, their four original XML registrations and one JNI library; the strict Soong DEX uses-library patch is installed, but the Camera APK is not selected |
| Factory mi_ext | Original 111,198,208-byte image and verified receipt; patch 0007 provides the direct-root AVB custom-image path |
| Dedicated A/B recovery | Unchanged working76 image and public key; patch 0006 corrects the inapplicable non-A/B two-step requirement only for the A/B-only mode |
| Existing integration | v11b OEM classifications, helper capability, Binder derivation, kernel, original vendor/ODM images and the earlier reviewed patches are retained |

The property contract budgets **105 added ordinary allow edges** and records
**7,190 existing dontaudit edges that become applicable** through the new
property memberships. The later export4 native analysis independently verifies
this budget, the logging effect, source/M4 mappings, all assertions and enforcing
binaries; the input contract alone did not establish those results.
The provider-policy extension is a later, distinct input set.

Staging completed at **22:06:35 UTC**; installation completed at **22:10:41 UTC**.
The durable journal records `commit_verified` after all ten operations. The
transaction retained the old objects and independent previous copies, checked
the previously built outputs unchanged, and verified the installed inputs.
Its manifest SHA256 is
`084e740e4888bdded20c2ca3b44ce3400652c5ac8ab242a8c17dc99d56a04820`.

The installed audit matches all **1,179 project HEADs and origins**, with
**1,174 clean projects**. The five reviewed modified projects are:

| Project | Pinned base revision | Local input scope |
| --- | --- | --- |
| `build/make` | `a438ca40c6ed779042f806142b1165ba1360a7b2` | Existing recovery consumer plus patches 0006 and 0007 |
| `build/soong` | `cbcbea9e65503ca15b363a0b06dda88fdbcb0154` | DEX uses-library provider implementation and fixtures |
| `system/core` | `241488ea392c01079941d86ddc458b8a0c9ae6e1` | Existing init property patch |
| `system/sepolicy` | `e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27` | Existing enforcing-user and scoped helper patches |
| `vendor/lineage` | `11d2966a3294a0a692fc958127c770cfe9c00a3c` | Existing security-property selection |

The fifth modified project is intentional. Do not reset it, or any earlier
reviewed patch, to make a source audit report a pristine checkout.

## Native checks and the first build failure

Installed-source verification passed all **12 isolated native Kati recovery
guard fixtures**. Negative cases require their specific expected diagnostic;
an unrelated Kati error does not count as a pass. The fixtures cover the exact
guard with pinned product read-only ordering. They do not run the complete
Android configuration or build a recovery image. Separate Python branch tests
exercise the actual pinned packaging functions with synthetic inputs; they do
not produce target-files or an OTA. Public-key verification of working76 and
native verification of the existing mi_ext hashtree also passed, without
establishing OEM authentication or a complete signed ROM chain.

The actual `lineage_nezha-bp4a-user` phase `policy-v12e-1` ran from
**22:11:46 to 22:19:27 UTC** and returned **exit 1**. Soong bootstrap and graph
generation progressed, then Kati failed while finishing packaging rules:

```text
build/make/core/Makefile:4776: error: unknown variable: BOARD_MI_EXT_IMAGE_NO_FLASHALL
```

The receipt verifies the installed source inputs unchanged, no timeout, no
remaining build processes and no sandbox fallback. It records
`actual_ninja_sandbox_observed: false` and `native_sandbox_verified: false`,
because the build never reached those actions. The `-k0` request did not turn
unexecuted checks into passes. No fresh v12 policy, assertion count, permissive
analysis, Camera runtime build, mi_ext target or recovery target is claimed
from that first attempt.

Earlier `run-v12` through `run-v12d` stage failures remain in their original
ignored directories. They exposed snapshot ordering, case-probe, unified-patch
parsing and Kati-fixture mistakes before active installation. The separately
preserved recovery Kati v3 probe passed all 12 cases before the v12e transaction.
None of those narrower results erases the full-build failure above.

## v12f correction, native fixtures and v12fa installation

Commit `44ec02f3a1eba37b23f13bcd4222f34bed3768dc` adds
[patch 0010](../patches/evolution/0010-initialize-direct-avb-readonly.patch) and
an [explicit source composition](../patches/evolution/direct-avb-readonly.json).
The patch replaces direct `.KATI_READONLY` assignment with the pinned
`readonly-variables` macro. It initializes seven undefined optional settings to
empty, preserves two derived values and freezes the selected settings. Existing
incoming-override guards run first and remain unchanged. In particular,
`NO_FLASHALL` must be empty, not the nonempty string `false`, so the image remains
eligible for the update ZIP.

The v12f candidate and repeat are byte-identical, with admission SHA256
`9bf0f6f8e5b9e76160e5b5f7291d795b87381b28fbd73d0fbed15a73295b18be`.
Only two generated device guards change: `generated/mi-ext-prebuilt.mk` and
`recovery-prebuilt.mk`. No device file is added or removed. Updated recovery and
mi_ext receipts select the new exact source composition without changing either
image or the working76 public key. The property policy bundle remains
`b5504b326da9c4be57009a5451a6eca45b3f3105f4ebb2e733e33c0b261decbf`, including
the unchanged `e9183b60…` OEM policy tool. Providers and metadata projection are
not added to this base correction; the metadata composition needs its own
explicit patch-0010 extension.

The native Kati probe completed at **22:54:08 UTC**. Its **99 expected outcomes**
comprise one reproduced historical failure, five corrected positive cases and
93 specific negative cases. It parses the full hash-bound custom-image region,
checks the defaults and derived values, and preserves the original inputs. It
does not run Ninja, image recipes or avbtool. These results qualify the patch
for installation; they do not establish a successful full Android build.

The [native DEX provider fixture record](../research/dex-import-native-fixtures.json)
also now passes: **five top-level tests and 11 subtests**, with no failures or
skips, completed at **22:57:13 UTC**. The first run actually compiled the test
binary in nine normal Ninja actions but then failed its freshness harness,
which expected the idle diagnostic on stdout instead of stderr. That attempt
ran no fixtures and remains recorded as failed. The corrected v2 harness
verified the same binary through its normal dependency target and ran the
selected fixtures without short mode. It did not write the full Java-suite
stamp or execute generated Android rules, Camera JAR/JNI/XML builds, APKs or
dex2oat. The guest still had the installed v12e input set at that fixture
checkpoint; the later v12fa transaction is recorded below.

The earlier `run-v12f` transaction candidate passed staging without changing
active inputs; it was not installed. The fresh **run-v12fa** transaction began
at **23:21:33 UTC** and committed at **23:22:28 UTC**, with seven exchanges and
17 durable journal events. Its manifest SHA256 is
`8907f7705cd1a767a037531c63ee9b4c4454def1ec8bfbd623862f4df879ce14`.
It installs patch 0010, the two device guards, the corrected EROFS C source,
the new mi_ext receipt and the recovery receipt/include. All 1,179 project
HEADs and origins still match, with the same 1,174 clean projects and five
reviewed modified projects.

The property policy receipt and tool remain unchanged. Original vendor/ODM,
mi_ext and working76 image bytes are retained, as is the old EROFS binary.
The fixup verification does not check the complete previous Android-output
inventory; only that old binary has an explicit output-preservation check.
Installation itself neither compiles the corrected C nor verifies new policy.

## Successful native v12f build

Phase **policy-v12f-1** ran from **23:26:28 to 23:40:31 UTC**, exit 0, with
unchanged source inputs, no timeout, no remaining build processes and the
read-only source/writable output sandbox verified. The log contains **73 Ninja
actions** after configuration. Its progress display ends at 235/235 because
the counter includes the preceding 162 configuration steps; 235 is not the
number of Ninja actions.

Fresh native work includes source/M4 and API mapping generation, neverallow
compilation, framework and factory-combined policy compilation, the OEM guard,
five factory context checks, two seapp checks and two structural checks. The
corrected EROFS C source was compiled, linked and installed at progress entries
184–188. The two identical service-specification warnings for
`android.hardware.media.c2.IComponentStore/default2` and
`vendor.qti.hardware.display.config.IDisplayConfig/default` remain visible and
match the previous v11 log; they did not fail the checks.

The build result SHA256 is
`9db004d20cf498728bf321913c038c3c82fb472daf831a53dbdc2801694691ff`.
The captured source inventory binds 107 unique paths, including the unchanged
property policy bundle and original images. This
build requested **no images** and does not establish Camera component, corrected
EROFS runtime, policy-image adoption, VINTF, packaging or hardware success by
itself. Subsequent exporter runtime checks are recorded below.

The first independent verification, **analysis-v12f-v1**, failed before
semantic comparison when it found that the actual compiler's system_ext CIL
differed from the runtime output. A read-only Ninja graph audit confirmed two
stale runtime files:

| Runtime file | Old output SHA256 prefix | Actual compiler-input SHA256 prefix |
| --- | --- | --- |
| `system_ext/etc/selinux/system_ext_sepolicy.cil` | `5b83e2ffb9f0` | `80524bd17259` |
| `system_ext/etc/selinux/mapping/202504.cil` | `50ef50a5b561` | `3d5599f31ba1` |

Full identities and the graph-audit receipt are in the research record. The
requested policy-compiler targets did not guarantee that these runtime install
targets ran. The later expanded 25-target build preserved 11 previous outputs
and forced fresh execution through the normal graph; no hand-edited or manually
copied generated CIL was substituted. That failed attempt establishes no
semantic or permissive result; the later successful export4 analysis is separate.
The failed analysis and its captured commands remain preserved.

## Expanded runtime exports and the next verification failure

The expanded phase ran from **00:03:38 to 00:16:57 UTC on August 30**, exit 0.
It adds seven ordinary runtime-policy goals to the earlier 18 goals. The log
has **35 main Ninja actions**, numbered 163/197–197/197 after 162 Kati steps.
The system_ext mapping and CIL install at entries 169 and 170; product exports
also install. All 11 preserved outputs have one fresh producer action: the
combined compiler, OEM guard, five context checks, two seapp checks and two
structural checks. Source identities and sandbox verification pass; no image
was requested and no build process remained. The 29-file capture retains
3,189,204 bytes, including both preserved and moved copies of the old outputs.

Preservation verifies those old copies; it does not itself rehash the newly
produced active outputs. That binding belongs to independent analysis. The
subsequent **analysis-v12f-export-v1** verified runtime/compiler equality, then
failed because the 19,226,918-byte `build_sepolicy` executable exceeded the
16,777,216-byte policy-reader limit. The failure is retained. It is a provenance
reader failure, not a new SELinux assertion failure or a completed semantic pass.

The frozen **export2** analysis driver uses the existing bounded resource
streamer for only the two exactly pinned mapping executables, with final
rehashing and alias checks. The policy-reader limit and semantic requirements
are unchanged. Its 224 offline checks and package preparation pass; native
execution is held pending the additional aggregate adapter below. A separate
22-file, 9,655,573-byte policy snapshot was captured for host rehearsal while
`components-v12f-1` was running. That
read-only snapshot is not native analysis or proof of freshly executed checks.

Host rehearsal found exactly three aggregate source assignments that differ
from the earlier model. Each contains the unchanged platform members followed
by the four restored property types:

| Aggregate | Unchanged platform members | Actual members |
| --- | ---: | ---: |
| `property_type` | 369 | 373 |
| `system_property_type` | 364 | 368 |
| `system_public_property_type` | 145 | 149 |

The [recorded host proof](../research/native-rom-integration.json) preserves all
6,366 original assertion statements and exactly the reviewed **105 added allow
edges, 7,190 newly applicable dontaudit edges and 28,604 additional neverallow
coverage edges**, with no extra effects. Other assignments, global closures,
roles and namespaces match; the two intended source allow clauses remain exact.
The unchanged verifier still rejects the aggregate assignment form. Neither
policy nor driver was edited by this diagnostic rehearsal, and no native
verification is claimed. Export2 remains held with its known-failing model.

The corrected **export3** adapter's complete host rehearsal passed at
**00:50:22 UTC**: property delta, public exports and recomputed OEM semantic
record. All 22 captured files and 47 host input bindings were rehashed, including
the seven runtime/compiler pairs. This runs the corrected analysis against
captured inputs, but does not verify fresh native checks, native sandboxing or
permissive binaries. The subsequent native attempt is recorded separately below.

The final export3 package is frozen at manifest
`23676a9a5658e1a4393c887cd62a6c44179e5fd519a2e7b29f1a762a6e106322`:
36 files, 9,654,116 bytes, with 240 offline tests passing and zero skips. The
independent review found no remaining issue. The record binds the exact next
command; package preparation did not contact the guest or run native analysis.

The native **analysis-v12f-export3-v1** attempt produced a verified semantic
comparison and nine independently fresh context/structural action records.
It then failed with `native property-context M4 did not consume exactly the
authored source`: the guard did not model the command's newline interleaving.
The 31-file failure capture preserves those partial results. An earlier empty
capture from the wrong result path is also retained and proves nothing. This
failure does not establish a policy violation or a complete analysis pass.
The source-exact export4 correction and its later successful execution are
recorded below; export3 remains failed.

## Verified current native policy baseline

**analysis-v12f-export4-v1** completed at **02:13:44 UTC**, status `verified`,
against the actual `policy-v12f-export-1` build. The correction binds the pinned
`buildGeneralContexts` behavior: a newline file follows every M4 input,
including `flagging_macros`. It requires the exact sequence without dropping,
ignoring or changing inputs. Its 243 offline tests passed before native use;
no source policy or generated CIL was edited.

The native receipt verifies all 6,366 original assertion statements and exactly
105 added allow effects, 7,190 newly applicable inherited dontaudit effects and
28,604 added neverallow coverage effects, with zero removals. These are concrete
effects under the retained assertions, not new assertion statements. Three
unfiltered `sepolicy-analyze` runs report zero permissive domains: the factory
combined binary and both source-policy binaries. Strict compiler flags, source/M4
and API mapping producers, the fresh OEM action, nine context/structural actions,
and final input rehashes all pass. Runtime MLS evaluation and embedded Python
bytecode equivalence are not claimed by this analysis.

The receipt is **342,300 bytes**, SHA256
`dd338730212aadf7dde9847cd63f60e5023c3c1d5c2fae91ff3d199593219c95`.
The 67-file capture totals 38,863,497 bytes. The stdout serialization has a
different whitespace/hash representation; it is not substituted for this file.
All guarded inputs remain unchanged, provider policy is unselected, and no
Android source/output, image or phone mutation occurred. Full Treble APK labeling,
provider integration, policy-bearing vendor/ODM images, packaging and boot
remain unverified.

## Completed Camera, mi_ext and recovery component build

**components-v12f-1** ran from **00:21:12 to 02:03:33 UTC**, exit 0, taking
102 minutes 20 seconds. Its eleven goals are the nine exact Camera runtime
modules, `mi_extimage` and `recoveryimage`. Source inputs remained unchanged,
the native sandbox was verified, and no timeout, fallback or remaining build
process was recorded. The five-file build capture totals 3,207,797 bytes.

All eleven installed outputs were captured and inspected. The four JARs,
four XML registrations and JNI library match the admitted payload bytes;
JAR member content, DEX checksums/alignment, XML registrations and the ARM64
ELF header pass the separate host inspection. Recovery is exact working76
(`a130ba75…018e`) and mi_ext is the unchanged factory image (`60f79117…e196`).
That initial payload inspection is separate from the later producer review.

The bounded producer review rehashes 58 captured files and all eleven installed
outputs, then binds four fresh DEX invocations to their raw serialized Soong
inputs and matching installed ODEX/VDEX. The actual commands use `quicken`,
`--abort-on-hard-verifier-error` and recorded `PCL[]` contexts. None of the four
`dexpreopt.config` targets was materialized; their existing raw producer inputs
are verified instead, without counting an absent target as a pass. The observed
library-import `EnforceUsesLibraries=false` does not validate the Camera APK's
manifest or uses-library contract, or establish runtime API closure.

The JNI action freshly ran with SONAME, DT_NEEDED, symbol-resolution and 16 KiB
alignment checks enabled; the captured ARM64 load segments independently satisfy
16 KiB. The separate phony `recoveryimage` recipe freshly performed its guarded
working76 copy, and mi_ext freshly passed native NONE-footer and SHA-256 hashtree
verification. Neither is a new TWRP runtime compilation or complete signed-chain
result. Freshness is bound to phase actions, output/ledger times and preserved
source/graph evidence; opaque Ninja ledger command hashes are not independently
recomputed.

The review receipt is **22,098 bytes**, SHA256
`f197a5b1ff666d08bf447291e1511dd6cdb662a542a35e2da4af4f38eea5baa2`.
The coordinator reran the unchanged host review and produced an identical
receipt. Native DEX/ELF commands were not independently replayed; the complete
bootclasspath, dynamic dex2oat flag-file contents, all ELF dependencies and host
tool bytes were not recaptured by this review. No Camera APK was selected or
built, and no runtime linker access, complete framework images, packaging,
first Evolution boot or Camera/Leica operation is established.

## Other inputs and installation boundaries

| Slice | Verified result | Still required |
| --- | --- | --- |
| [Sigma/QCC source admission](framework-provider-source-admission.md) | Installed v13ha policy passes native semantic/provenance analysis; the later v13ja 4 KiB source passes all 26 fresh ELF/symbol checks | Complete ABI/runtime linker behavior, VINTF and APK labeling, service validation and matching image selection |
| [Target-files metadata](target-files-metadata.md) | Original-image bundle contains all 205 required property, VINTF and complete APEX files; host source admission and isolated Kati cases pass, with later reviewed packaging-matrix source selection recorded below | Ordinary sidecar production and final target-files policy/installation checks; source selection does not prove packaging |
| [Host AVB signing](avb-signing.md) | Inert planning, offline workflow tests and real unsigned countrycode/pvmfw descriptor-carrier checks; original inputs preserved | All 15 final input images with correct hashtrees/FEC, explicit Mac signing and independent verification of the resulting 17 image roles |
| [Original ODM shipping API](vintf-shipping-api.md) | Patch 0011 and 59 source-bound host cases forward the original ODM API 36; the combined packaging source is now selected | Ordinary target-files path execution and final-input compatibility checks; no property bytes are fabricated |
| [Earlier Camera APK admission](camera-apk-inputs.md) | Fresh unchanged-signature, ZIP CRC and strict library-name checks; two real validator failures remain reproduced for the Xiaomi.eu/live input | This input stays unselected; its code findings do not transfer to the distinct factory DEX payloads |
| [Original factory Camera APK](factory-camera-apk.md) | Commit `d3316b4` records unchanged original input passing strict privileged/preprocessed packaging and exact uses-library checks | Ten always-privileged requests, eleven across feature branches, still require grant review, effective SELinux labeling and actual APK build; neither APK is selected or hardware-tested |
| [Factory Camera build-only packet](camera-apk-build-admission.md) | Commit `117261c` adds a separate exact namespace packet; 13 repeated files match and the host content-verifying producer passes | Explicit guest source admission and a verified graph limited to intermediate outputs; no product selection, permission/MAC admission or real APK build |
| [Combined packaging sources](target-files-source-composition.md) | Commit `1a4bd58` joins patches 0005–0011 with ten complete source identities; later packaging-matrix installation binds current metadata/recovery/mi_ext and policy-image inputs, preserving the older contracts | Complete native configuration and ordinary packaging; final flashable-artifact admission remains separate |
| [ROM construction prerequisites](rom-construction.md) | The initial unbound consumer reports missing roles; the later explicit constructor source transaction selects its guard with retained evidence | Native dispatch/configuration admission, required coverage and actual construction; source selection is not a build result |
| [Policy-image input preparation](policy-image-inputs.md) | Commit `78376c7` adds explicit v13h evidence admission; raw reconstruction and keyless footer checks pass, and later packaging-matrix source selection retains the exact reviewed leaves | Signed parent chain, physical partition fit and final-input compatibility; source selection is not flashable-artifact admission |
| [Factory Camera grant behavior](../research/factory-camera-permission-grants.json) | Commit `e433a5d` traces three pure-signature requests through captured grant-evaluator and service source; 30 focused tooling tests pass | Effective signing/flags/grants, generated enforcement bodies and actual Camera behavior; no grant or APK installation is performed |
| [Pinned build metadata](pinned-build-metadata.md) | Commit `ec21a87` adds an explicit UTC epoch capability; 33 isolated native Kati outcomes pass, and later patch 0012/helper source selection commits | Actual product configuration, generated metadata and helper execution; source selection is not proof of a build number or reproducible images |

The metadata projection is content-only packaging input. It is not a full
filesystem inventory, an APK inventory or proof that a rebuilt partition
preserves ownership, labels, capabilities and timestamps. It intentionally
rejects future policy-bearing image hashes until their complete derivation is
reviewed. The signing workflow has not read a private key or signed a ROM.
It preserves the existing recovery image and never authorizes relocking.

The combined packaging candidate and repeat match all 41 manifest-listed
payload files plus their admission receipt. Against the preserved host v13f
candidate, one metadata include is added and three device includes change;
policy/provider/OEM/DSP/helper bindings and readiness flags remain unchanged.
Metadata, mi_ext and recovery receipts share the same exact ten-file source
composition. This candidate remains uninstalled in the guest.

The separate **v13f provider packet** completed staging at **02:18:20 UTC**,
manifest `e370994fe7fd7d29353ddf0924ef6546c98f13f54aecabe281776a0289f996a0`.
The staging receipt verifies active sources and previous outputs unchanged.
The later installation committed at **02:34:51 UTC**, with four exchanges and
the transaction journal read back as `commit_verified`. It installs the device,
policy and framework-provider trees plus the scoped `external/mdnsresponder`
visibility change. Previous objects and independent copies remain preserved;
the original images, Camera runtime, mi_ext, recovery and exporter trees are
unchanged. Active inputs became v13f at that checkpoint, but export4's policy baseline
still applies only to the earlier v12f input set.

The **policy-only-v13f-1** request contains 31 exact goals, including
policy/runtime exports and MAC/seapp outputs. It retains the 16 KiB maximum and
enabled prebuilt checks, requests no provider runtime or image build, and has
failed during Soong bootstrap at **02:36:44 UTC**, exit 1. The emitted
`android_arm64_armv8-a_static` variant of `nezha_framework_libmiracastsystem`
depends on `android.media.audio.common.types-V2-cpp` directly and V4 through
`libaudiofoundation`. The complete dependency-path diagnostics remain captured.
No new policy compiled, no context check ran, and no provider ELF action passed.
Source inputs remained unchanged; the phase recorded no timeout or remaining
process, and never reached the native Ninja sandbox. The six-file failure
capture totals 159,676 bytes. Resolve the exact ABI/source graph rather than
blindly rewriting the V2 dependency to V4. V13f remained installed after that
failure; the later v13ha correction and successful source build are recorded below.

Three isolated native Soong fixtures pass their expected outcomes: a consistent
shared-prebuilt graph succeeds, while both shared-scoped and top-level mixed
Audio AIDL graphs are rejected. Selecting only the shared variant therefore
does not resolve the V2/V4 conflict. The fixture receipt is
`7f2f85c40d1fcc4356636910d8516872249c45434a3b7e5593716c49edeb5e92`
(54,722 bytes); it is neither a product build nor a full AIDL suite. The first
compile-only audio-layout probe failed at **03:24:05 UTC** with an unrecognized
AST record header. No ABI was admitted, and no target code was linked or run.
The corrected **audio-native-layout-run-v2** completes at **03:31:25 UTC**:
two cases, four compilations and all 15 measured factory constraints match.
Its receipt is `a76cc907…4dadd9` (6,222,532 bytes), with 17 captured files totaling
13,874,960 bytes; sandbox observations are captured separately. This is a
compile-only layout result, not complete ABI admission, linking or target-code
execution. Static review of the two selected descriptor-vtable CFI checks also
finds matching type metadata and acceptance predicates without CFI suppression;
runtime linker/CFI routing and the remaining caller ABI stay unverified. The
host-verified v7 Miracast correction is now committed as **364ab89**, including
the producer and consumer bindings. The [correction record](../research/framework-provider-audio-compatibility.json)
preserves the original input and binds the exact one-byte DT_NEEDED derivation.
Those host results do not establish the whole caller ABI or runtime behavior.

The first **run-v13h** snapshot failed before staging because the absent provider
producer had a missing intermediate parent directory. Its empty stdout, nonzero
exit and diagnostic are preserved. The **run-v13ha** retry changes only the
snapshot handling and run label, retaining the same profile. Its read-only
snapshot completes at **04:48:32 UTC** with all 1,179 revisions/origins matching,
1,173 clean projects and the six reviewed modified projects. No source reset,
replacement sync or native build is performed by that snapshot.

The v13ha installation commits at **04:52:42 UTC**: three tree exchanges and
nine journal events, replacing only the device, policy and framework-provider
trees. The manifest is `07ff79c7…f27b0` (89,987 bytes); the installation receipt
is `1b035f5a…39ad7` (69,309 bytes), bound by the 537-byte commit acknowledgment.
Old objects and independent copies remain preserved. The subsequent source
proof binds 182 files; all 55 prior output identities were preserved at
installation, including the eleven runtime outputs. The snapshot retains the
16 KiB maximum and enabled prebuilt checks, without claiming an ELF action ran.

The actual **policy-only-v13h-1** build runs from **04:55:14 to 05:40:07 UTC**,
exit 0, for 31 goals and 273 Ninja actions after configuration. All source
inputs remain unchanged; the native sandbox is verified with no fallback,
timeout or remaining build process. Eleven preserved policy outputs and all
eleven protected runtime outputs pass their separate post-build checks. The
35-file capture totals 3,466,855 bytes; its 213,849-byte result is
`1596843eca8377fdb17359e3a70009b84c95aad5a0219531f521e52e21659e5b`.
Provider runtime/ELF actions and images are not requested or built. The separate
native analysis below supplies the subsequent semantic and provenance evidence.

The canonical **analysis-v13h-policy-only-v1** receipt is **10,058,468 bytes**,
SHA256 `bb6e8f0218d1f4c61a3cd8221478007548e2a1950d048a9dd60d5d7842334b66`.
It completes at **13:12:51 UTC** and binds the exact successful build, ten
compiler inputs, source/M4 and API-202504 producer graphs, public exports,
the fresh OEM guard and nine fresh context/structural checks. The complete
208-file capture totals 58,407,051 bytes. No compiler or OEM guard is replayed
by this analysis; their fresh build actions and exact provenance are rebound.

Against the actual v12f/export4 baseline, all **6,366 original assertions** remain
and **four provider assertions** are added. The ordinary concrete effect delta
is **+12,005 allow, +1,883 dontaudit and +3,291,674 neverallow coverage**, with
zero removals. The complete review separately records extended permissions and
inherited changes. Two added CIL dontaudit statements are present, so denial
logging is not claimed unchanged. Helper property-set permissions remain zero.
Three unfiltered native analyses find no permissive domains. The strict combined
binary is **1,517,136 bytes**, SHA256
`44113598331ae410279432d39adb884db56fc1217ab5a35158c36fb3bee9f707`.

The provider-input genrule freshly executed in the build at action 207/273.
Its 42 original inputs produce 31 verified payloads: 30 remain unchanged and
one has only the admitted one-byte DT_NEEDED derivation. The analysis binds
the real command, dependencies, producer outputs and receipt; file modification
times alone are not used to infer execution. This does not build or install the
provider runtime modules, execute firmware or prove ELF/linker compatibility.
The 31 native payload files were not separately copied in this analysis capture;
their byte checks are bound through the native receipts and graph queries.

Independent review rehashes all 208 captured files, 36 frozen controls, 55
prepared inputs and the 42 original provider inputs, and reconstructs the
one-byte derivative. The complete effect inventory matches its unchanged
reviewed identity after only four validated generated assertion-name roles are
normalized for comparison. No source or CIL is changed. The review has no
findings; its receipt is
`6de9be94f6765cd18f27feb6a5789194cd0b511b55f25fb9d098e407ec0ff82b`
(8,926 bytes). The separate author's capture summary records completed checks
without rerunning them. Neither review reruns compilation, native analyses or
the offline suite.

All guarded inputs remain unchanged, and the analysis writes no Android source,
output or images. Normal Android enforcement and strict neverallows remain
selected. Six MAC/seapp exports match their producer bytes, without a freshness
or Camera permission claim. Full Treble APK labeling, provider runtime/ELF,
complete VINTF, matching current-policy images, AVB and hardware remain open.

The matching **policy-sidecar-v13h-native-v1** run passes **six checks and
fourteen native commands, zero skips**. It derives platform, system_ext and
product digest files from the six sealed CIL/mapping inputs using the pinned
source recipe. The 65-byte system_ext digest file changes to SHA256
`04b3cfdefbc293724f48a4a6c0e6098d46aa944274c74928b9b9cd20b6709335`;
platform and product files match the earlier derivation. All 61 captured files,
16,606,505 bytes, rehash. The native receipt is
`d679acf232419b70c89c1fd05a48dd6647ca0a9d818f2dc9386db71669626630`.
Known-answer and three negative controls pass. Source and Android output remain
read-only for this operation; installed digest outputs are not captured and
Android genrules are not executed. This derives validation files without
adopting policy or accessing images.

The read-only post-v13h VINTF graph capture completed at **13:29:30 UTC**. It
binds 21 selected XML inputs, including both provider fragments, and 36 APEX
inputs. The graph still defines no full compatibility action: `check-vintf-all`
depends only on the system and frozen-manifest checks. The three-goal
**vintf-v13h-1** build requested that alias and the stock-kernel version and
configuration outputs. It ran from **13:32:27 to 16:32:28 UTC**, then timed out
at its configured **10,800-second** limit, returning exit 1. The last logged
progress was **58,702/61,802**, not a completed action count. No forced kill,
post-build validation error or remaining build process is reported. Source
history, strict settings, Ninja arguments, sandboxing and the 13 policy/11
runtime guards pass their separate checks; the build remains failed.

The timeout capture contains eleven files and 9,590,702 bytes; result SHA256 is
`a61d5ba729f6763ba19615d637dc6aae2f00a3ecd2fd2ccfd28c32b07abca011`.
A separate preservation captures the Ninja action log and nine available XML
outputs, with 41,138,767 payload bytes plus its receipt. This is not a complete
intermediate inventory or proof that the requested final targets passed.

The fresh read-only capture at **16:42:27 UTC**, SHA256
`b6d13e0a1f5eb3a4acee1d66063e0f7273194c47429cb1ae49722dd0bfd6b0be`,
matches the original goals and selected graph shape, the post-timeout graph
identity, and unchanged source history/settings. The **vintf-v13h-2** incremental
retry retained the same three goals, strict checks and 10,800-second limit,
reusing existing outputs without cleaning or replacing the checkout. It ran
from **16:46:32 to 16:58:47 UTC** and returned **exit 1 without a timeout**.
At logged progress 3,108/3,109, the `vintffm.log` action failed because
`android.hidl.allocator` is mandatory but undeclared. The diagnostic identifies
the frozen level-5 device matrix. This is a real strict-check failure, not a
completed VINTF build.

The post-build graph inventory records all **21 XML and 36 APEX artifacts
present**, with none missing; the separate requested-target success inventory
is empty. Source, 13 policy/11 runtime guards, strict settings, sandboxing and
Ninja arguments pass, with no post-build validation error or remaining process.
The eleven-file capture totals **672,905 bytes**; result SHA256 is
`88e4200261601edc7b941249b275bc2a2f47ff7cd0c2c3dc872b5d0d7c159f4f`.
The configuration retains `16384` and the enabled prebuilt page-size check.
The [allocator capability](framework-allocator.md), committed as **1647192**,
binds **24 exact captured sources / 329,015 bytes** and selects the existing
upstream `android.hidl.allocator@1.0-service`. It retains upstream init, SELinux
and `max-level="8"` behavior, with no extra policy or matrix changes. Candidate
and repeat each contain 43 payload files / 605,013 bytes: 40 are unchanged,
one product file adds a package selection plus comment, and two controls are
added. Both admission records have SHA256
`429c25640ca1c0951832a56fe91ca7efc05b8ad1200d6430fba32d7171024baf`.
Independent host review has no open findings. That host source admission is
separate from the later installation and still does not prove service behavior.

The **run-v13i** transaction installs the allocator device selection at
**18:48:34 UTC** through one tree exchange and a journal ending in
`commit_verified`. Manifest SHA256 is
`f399be79c9745fea9389bd1bf5094eb8facae7973fbb43cea740e8f3e2fe1c2d`;
the 19,531-byte installed receipt is
`571c46dbe7392e58cffd008deaad7f0e34bf4b559e1e54b068fef1e33855b8fc`.
All 24 guarded inputs and 112 prior outputs are preserved, including the existing
policy and runtime outputs. The snapshot matches all 1,179 project revisions
and origins, with 1,173 clean projects and the same six reviewed modified
projects. It retains strict 16 KiB checks and changes no policy/provider inputs
or project source.

The 37-goal **allocator-v13i-1** component build runs from **19:06:17 to
19:20:26 UTC** and returns exit 0, with no timeout or remaining build process.
There are **178 Ninja progress rows after 163 frontend steps**, not 341 native
checks. The log records fresh allocator compile, link, strip and install actions.
All 204 selected source files, 24 allocator source guards, 13 protected policy
and eleven runtime output hashes are preserved; strict 16 KiB settings and
source-read-only/output-writable sandbox checks pass. This does not establish
an unprivileged or zero-capability process.

The 13-file core capture totals **389,430 bytes**. Result SHA256 is
`11ab9b9348474adc42b5fe5e4172c4a54b52b75529df999b589d8819304311d7`.
The separate three-output capture contains the 51,800-byte AArch64 allocator
binary, 187-byte init file and 350-byte VINTF fragment. Independent review
`df29af4c64dc93fe313b4dfa67fcbce4ad3c330736c859ecd07b3e5a034fd410`
has no blocking findings. It confirms all four ELF load segments have 16 KiB
alignment and congruent offsets, byte-identical upstream init, and semantic
agreement of the generated allocator fragment, including max-level 8. The XML
is canonicalized and is not byte-identical to source.

The actual partial VINTF log explicitly skips `checkMatrixHalsHasDefinition`
for `compatibility_matrix.device.xml` with no level. The two limited VINTF edges
include the allocator fragment, but do not perform full vendor/kernel/APEX
compatibility. No zero-skipped native claim is made. Exact allocator
source-to-output producer commands, provider ELF checks, APEX cryptographic
validation and runtime registration remain unverified. The strict v13h policy
analysis is reused through unchanged policy inputs and exact byte equality of
the analyzed policy; no fresh compiler/assertion/permissive analysis is claimed.

The first **allocator-producers-v13i-1** read-only capture passes nine commands
across three query layers and describes all three allocator outputs, with zero
skips. Its inner receipt is
`8432513247ccb0cb675005d3a0927c148e4c6d267b974cb5fb76a2578b1de9a0`
and outer receipt is
`9ec7fabe993d9610ff49b3f6ada8819cbe41a9104bc842a732ff513280c5452f`.
The accepted capture-time envelope preserves source, outputs, graphs and logs;
it does not rebuild the allocator or establish source-to-binary equivalence.
The later product-list metadata copy appends 126 bytes to OUT `.ninja_log`,
making this snapshot stale for the current full-VINTF guard. The exact
staleness record is
`d44a863f77770d9d05feecedb1544ab9e1e993ceea834ee252d7fa8fdb46f7a9`.
The historical capture remains valid evidence; the fresh phase-2 capture below
supplies the required current receipt without relaxing the complete log guard.

The older v13h full-check packet remains historical staging: all 221 files are verified,
including the manifest
`35927a29e117c8c2d879cc36d46aed6c7f3001700ef60543b5a0c2f032ca4143`
(which lists 220 files). It requires 36 generated framework APEX
packages and three original vendor APEX packages, plus all five partition maps
and both kernel outputs. The staging receipt verifies the transferred files
without source or Android-output writes. It does not execute materialization,
admit future build outputs or run full compatibility. The coordinator's 44
offline packet tests pass in 0.333 seconds with zero skips; these are not native
VINTF results.
The fresh **allocator-producers-v13i-2** capture runs from **22:41:16 to
22:46:09 UTC** and passes nine commands across three query layers, zero skips,
with source and Android outputs unchanged. The inner receipt is
`77dc707aa544240ad30c45644afff7e58376a05066fc5ae9b0d92f5b902d7543`,
and the outer receipt is
`8cb6f9f8e01ffe870c3d698f1aad74bb461b0dc24cf4a23491873b8e296c5867`.
Independent transport review reopens all 69 published members, including 66
payloads totaling 1,428,590 bytes, and verifies the terminal recheck. The 35
absent optional allowlist slots are explicit, not passes. The receipt is
admitted for packet preparation; this does not claim a fresh compiler action,
source-to-binary equivalence or service registration.

The full v13i packet now has **230 payloads plus its manifest**, SHA256
`63af6f0e8483d89561192b3e8f3732af9bc4a06386bce1155fd7a205de3c15e1`.
It binds 22 framework XML files and all 39 APEX inputs to the existing 16 KiB
source state. This first packet remains preserved and unstaged. After correcting
the historical-baseline versus live-state guard, the successor stages all 231
files, but its first capture rejects a shadowed writable `/work` mount beneath
the read-only overlay. The preserved diagnostic is
`edf891f2987637c0835044e0178e6896b8ae92fecf6dc5994ac870ce715c26f9`.
The mount-stack correction stages another 231-file packet. Its capture advances
past that check, then fails its assumed `.py` archive membership: the actual
built `apexd_host` and `deapexer` package `.pyc` files. The diagnostic is
`418f80e0c60500b3fec16d2e3c43df75628a029a35c21b4be545560cc58d29af`.
A deterministic source-to-bytecode proof using the pinned Soong recipe is in
progress. No full native compatibility command has executed; both capture
failures remain preserved. The unfinished 16 KiB packet is historical after the
source turnover. The 4 KiB component build now passes; a fresh capture and full
compatibility checks must use its actual outputs.

The current **allocator-producers-v13j-4k-1** capture runs from **01:26:19 to
01:31:45 UTC** and passes nine commands across three query layers, zero skips,
describing all three allocator outputs. Its outer receipt is
`3fd6d3dda7681d1351dfc9daeb84858fd98b8029a69d8ff015b0b54583aaf40c`;
the inner producer receipt is
`5e8a44f27ab9ea25fd93ff9d666f418e00d16373c481b5d1ed243f43ada02744`.
The 66 captured payloads total 1,879,899 bytes, with collection receipt
`7e0927910e48434f9866d57282c15a737e1f5f03e8dcac6d95cf5c8256a3890e`.
Host envelope admission
`c54fb57f78e23f510a593a004930e463e47cbb5c6d4b498b85b2527758c1ba8e`
binds the recorded success, preserved source/graph/log inputs and matching
producer identities. It explicitly does not perform full native allocator
admission: external native references must still be reopened. No fresh compiler
action, source-to-binary equivalence, runtime registration or full compatibility
is inferred from this read-only capture.

The auxiliary source-to-bytecode capture v2 preserves a 179-file failed
capture: thirteen commands pass, but the producer query exceeds its 8 GiB RSS
limit. The query-only v3 successor allows 32 GiB sampled RSS and 300 seconds,
requiring 40 GiB available-memory headroom; it does not apply an address-space
rlimit. It gets past the memory limit but fails on `unknown pool name
'highmem_pool'` in the standalone Soong graph. Its 183-file capture totals
1,238,748 bytes, with receipt
`3667f50271f24db454b50ed51ef728aa754187b507dfa7efd51941dce6dfea78`.
Thirteen other commands and all postflight guards pass; preservation covers
selected bound inputs, not a complete OUT census. Neither attempt completes a
source-to-bytecode comparison or full VINTF. The corrected combined-graph
retry below is a separate passing result, without inventing a pool or changing
the global VINTF memory limit.

The **v4 compiler capture and whole-bytecode proof both pass**, with capture
receipt `0f30a4c4c3f5618f0dda4b5bcc1d9816af7074a46e93a7b0a34345960c3bd2f1`
and proof receipt
`442daf21b91e5109d83e0bec654b88a4375273a48240c05063c7a84b174e66eb`.
The two phases execute 28 native commands, all with zero exit and zero skips.
Four comparisons reproduce complete packaged `.pyc` bytes, including headers
and marshaled bodies, using the exact pinned Soong compilation recipe:
`apexd_host.pyc`, `deapexer.pyc`, and `apex_manifest.pyc` in each tool. The
10,987-byte inner proof is
`6638a0075fd9fdd7fb4475ac848c619ee3b920e5f4c45e966150e0ccc1c23787`.
The host capture returns 183 capture-phase files and 185 proof-phase files;
independent review rehashes 408 evidence/input files and verifies all four
comparisons, with receipt
`e2e7ba117137fdf8384dc47f4c78141a3e754035fe5d04667c8318c3ca36aeda`.
It does not rerun native execution or reopen live guest inputs. Preservation
covers the selected bound inputs and source-project state, not a whole OUT
census. Generated-proto source provenance, APEX signatures, runtime activation,
full VINTF and boot remain unverified.

The separate **AVB-tool whole-bytecode capture/proof passes**, preserving the
earlier four-member proof unchanged. Capture receipt
`6748d82a9b658d5d8074b1a56bd68d1c187b8d7c040395eb38f7900ffd24459d`
and proof receipt
`cd244b3b378b6a13efd7147c0928ceb78aad64353b34168c77efc1c60a2c2280`
bind 28 native zero-exit commands, zero skips and one complete `avbtool.pyc`
comparison. The 7,884-byte inner proof is
`cc5f84a8c2fac84eca171a1e7f8ddd819a2fd4a13388d9e679d992e4e4a15ce7`.
Selected inputs remain unchanged. Reproducing the packaged tool's bytecode is
not APEX-signature, signed-chain or runtime validation; those gates remain open.

The subsequent **APEX integrity run and independent raw review pass for all 39
packages**, with 130 completed zero-exit commands, no postflight errors and
source/OUT preservation. Its 4,509,310-byte receipt is
`40a79b5c6ba160132aa0b7a9e868816e86661b4984709118dc22b1e7f99e7215`.
The 1,589-file capture contains 15,966,766 evidence bytes; no package, payload
image or manifest bodies were copied by that collector. Independent review
`5393443eaff971e7fe454bbfdcc49ed29ba7fa88267eeb6dbb9047eeca00859b`
rehashes all 1,589 files and replays all 130 native completions, read-only
observations and diagnostics. It verifies 65 APK v3 signature checks, 26 CAPEX
digests and 39 signed AVB payloads, with zero failed or skipped native commands.
The admitted scope is static cryptography for the historical pre-matrix v13ja
204-source/4-KiB output basis. It does not admit later source/package changes,
every embedded signature scheme, a source stamp, runtime activation, partition
AVB or OTA validation. The one presigned and three retained vendor baselines
prove exact selected bytes and internal signatures, not independent OEM signer
authenticity. No private key was read.

The earlier **pre-matrix 4 KiB full-VINTF input capture** completes with zero
exit and empty stderr. Its 493,527-byte receipt is
`83a59e55a5732cbbf44693f7cb2552817e26f621e10c99c9e07b111691ea49dd`.
It freshly reopens and verifies the external allocator prerequisites, binding
nine commands, three query depths and six described nodes. It also revalidates
the existing four whole-PYC comparisons and their current compiler/runtime
inputs; no new bytecode compilation occurs in this capture. The closure binds
22 framework XML files and all 39 APEX packages, comprising 36 framework and
three vendor packages, against the actual 4 KiB component result and strict
4096 settings. Source and Android outputs remain unchanged. APEX materialization
and full compatibility comparisons remain unexecuted in this capture; its
compatibility, runtime-activation and ROM-readiness fields stay false.

The subsequent **pre-matrix full 4 KiB VINTF run fails normally**. APEX materialization
for all 39 packages, framework consistency and vendor/ODM consistency each
return zero. The combined framework/vendor/kernel/APEX command returns **65**:
`checkUnusedHals` reports **155 unique instances** in the device manifest but
absent from the framework compatibility matrix. There are no unreached commands;
all fifteen postflight checks pass, and source and Android outputs remain
unchanged. The framework command retains one explicit matrix-definition skip
and two warnings. The log identifies kernel 6.12.23 as non-mainline, but complete
kernel acceptance and required VINTF coverage are not established by this
failure. The native 1,129,945-byte receipt is
`59fd65765e521e6ca98f91b27067d285d46ec17bbbbdd6fd4484c448dce6e969`.
The 54-file / 5,279,920-byte host capture includes the complete selected
diagnostics, not the materialized APEX payloads or manifests. No APEX-signature,
runtime-activation, signed-chain or boot result follows. That failure required
the subsequent exact framework-matrix correction without suppressing the check.
Independent host review
`61960cea5eeeb0ca068780339e8a369e5b91f5f1ab0dae32f9cde906ac502f55`
binds the full failure, all 54 captured files and nine immutable command-ledger
revisions. The separate materialization review covers the recorded 39-package
closure. Its 1,110 payload inventory rows describe paths and metadata, not
hashes of every regular-file body; extracted manifest and payload bytes were
not returned by this capture or reopened by the host reviewer.

The later matrix-v1 producer capture records **nine read-only commands, three
query depths and six described nodes**. Its inner receipt is
`a18ef5b6092a2fbef9015d13503c476694a33be7273beea6c8229b4ddb3227f2`
(198,499 bytes); the paired outer receipt is
`41ed78612e38fbbf41e4e0c02218734e2f799334f11cfbde19de320480bbb87c`
(265,988 bytes). Collection retains all **68 files / 3,242,620 bytes**, and host
envelope admission passes. The subsequent full-input guest check reopens the
external native evidence and verifies the paired observations. It preserves the
original `f83b2e87` failed wrapper and separate `7ab3bf7d` postcheck; neither a
fresh allocator compiler action nor source-to-binary equivalence is claimed.

The fresh full-input capture is
`3b972242280279ae67356e75bf24ddbd278cd5e3f660ca10583b2a59f816a7f6`
(1,191,048 bytes). It binds the matrix-v1 source inventory of 220 files, 53
source guards, strict 4096 settings, 22 framework XML files and 36 framework plus
three vendor APEX packages. Its capture-only review is
`b6ee53023c13c38684eed3ea11b180f27c185c7d768cae9753b80a4d0ffb17f0`
(4,746 bytes). Current allocator prerequisites and the four-plus-one existing
whole-PYC proof inputs are revalidated without a new compile. Independent
APEX input-equality review
`972ef5b47107b9bec89c4c0b24db7fc1b1f66780cf6d33709a243eb8b0634788`
(6,060 bytes) permits reuse of the previous 39-package, 130-command static crypto
result. It verifies the selected package, public-trust, tool/runtime and source
expectations; **zero cryptographic commands are rerun**. That review does not
itself establish fresh materialization or full-run postflight success.

The subsequent **full matrix-v1 VINTF run passes all four native commands**:
39-package materialization, both consistency commands and the combined
framework/vendor/kernel/APEX check. The native receipt is
`209a4cc05a378dc8ff7144ffbbdc92fe62346afaa7ad2578862e171e02863e8e`
(1,815,685 bytes); the **54-file / 5,593,782-byte** capture manifest is
`4fca4d8ced5ca76fb66e00b9e263c7bbf609f50a880610dc073ffcd7757fd9ee`
(31,073 bytes). All fifteen postflight checks pass, no command is unreached,
and source/Android outputs remain unchanged. The combined command reports no
skips or warnings and accepts the supplied non-mainline kernel requirements.
The separate framework-consistency command still reports one no-level
matrix-definition skip and two warnings. The combined path does not execute
that omitted matrix-definition check; zero exit does not prove every required
subcheck ran. Host runtime substitution also does not verify the running kernel,
kernel SELinux policy-version support, runtime AVB versions or a signed chain.
Final independent raw, coverage and materialization reviews now pass. The
7,534-byte scoped final review is
`bc799001f86dfb16e5ac096ea4014f57476f68e4685bc8aceb7010e1cabb9372`.
It binds all 54 captured files, nine immutable command-ledger revisions and
the 39-package materialization record with 1,110 inventory entries and two APEX
VINTF fragments. Five absent allowlisted temporary journals are expected
absences, not skipped checks. Inventory entries describe retained paths and
metadata, not hashes of every payload body. Complete input compatibility,
runtime APEX activation, partition AVB, OTA and boot remain unverified. This
capture leaves materialized APEX payloads/manifests in the guest and does not
reopen their bodies on the host. Any construction admission consuming this
result must retain its coverage limits and the other independent gates.
The subsequent 6,222-byte final crypto-reuse review is
`0eb9c0987fde2d2b7604f6db5c767e6771da1e2fc1b0d5665e3a941eca5bd15c`.
It binds the earlier input-equality review to this actual full result,
materialization and all fifteen postflight checks. The historical 130 crypto
commands remain reused evidence, with zero new cryptographic execution and
unchanged runtime, partition-AVB, OTA and boot limits.

Three separate capture attempts remain failures: the footer-tool reader rejected
a valid empty Soong shard, the provider ELF parser rejected duplicate dependency
edges, and the Camera capture stopped at its first Ninja query without retaining
the raw query diagnostic. The second footer capture accepts the complete graph
inventory, including the valid empty shard, but its first read-only jailed
query fails with `ninja: error: opening build log: Read-only file system`.
Its 48,329-byte receipt is
`63a6955831db77a6dc09ef7e9116906959d6d7a3a6d85e76bf92104932b296e8`.
No query or footer-tool runtime result passed in that second capture.

Earlier direct provider queries and the native memfd fixture lacked read-only
mount protection. Their static no-source/OUT-write flags are unproven. The
**17:12:42 UTC** observation records a 15-byte source-root `.ninja_log` and
16-byte `.ninja_deps`; those files remain preserved in place. Without prior
before/after identities, neither their exact writer nor absence of earlier log
mutation is established. No original project source payload change is known.
All affected query captures were held until the pinned `-n`/`-t` behavior and
actual read-only confinement were qualified; writable original-OUT fallback and
log deletion are not allowed. These limitations do not change the VINTF builds'
passing source guards, and no ordinary compatibility check is waived.

The actual **ninja-readonly-query-v1** qualification subsequently ran and failed
overall: **four checks pass, two fail, zero skips**. Its dry-query and
dry-commands `-n` cases match their known answers under read-only confinement.
The help-output-stream expectation and corrupt-dependency negative fixture
fail; the latter does not establish the expected read-only denial separately
from ordinary access permissions. Receipt SHA256 is
`7caa0ae905357d1fe0742c67fe709dbb2b6569dd9515cf255a635a3ada25bd7f`.
This remains an executed failed qualification, not permission to resume captures.

The corrected **ninja-readonly-query-v2** passes **six checks across eleven
commands, with zero skips** and all 55 raw diagnostic files captured. Its positive `-n`
known answers and expected read-only build-log/dependency-log failure controls
pass, with fixtures unchanged. Receipt SHA256 is
`31f0c3327a53f9905a38e7c0c656afcfceda56723b5595e2305b312493c954e3`.
The independent 29,584-byte review
`14e9b7da9d2709ba46b289760ea557d2e3498e22ed8fd290b286ab817a0d802c`
releases only the exact reviewed footer-capture recipe under its source, graph,
tool, log and read-only-mount guards. Other graph-capture recipes are not
automatically admitted. Ninja is not intrinsically read-only, and the earlier
unconfined queries' no-write claims remain unproven.

The actual **policy-footer-tools-native-v3** capture passes with **28 commands,
two query depths and zero skips**. Its 144,303-byte receipt is
`21f37f03237c40475f68a75ef3e80ec7e252c874eb6914aac0b8162197f5cf5d`.
Independent review
`1e031ac05aa5ba9f366214c41c8f53349ee5601b5c5c405716c55e55af1b45cd`
verifies 81 captured files, including 80 raw diagnostics, and eight observed
Ninja/loader jails. Fifteen graph identities, four full-stat log records,
27 selected sources and four project states remain unchanged. The evidence
binds copied `avbtool`/`fec` identities, producer descriptions and loader
discovery/confirmation; it does not execute those tool entrypoints, establish
complete linker/Python provenance or prove fresh producer execution.

The subsequent **root-qualify-admission-v1** host attempt, using the v4 packet,
fails with `runtime closure omits a dependency`: its closure comparison does
not account for the separately recorded interpreter. The empty stdout and
complete stderr remain hash-bound in the research record. The narrow v5
correction now passes host admission. The separate **policy-footer-qualify-v1**
run passes four native checks across seven commands with zero skips at
**18:27:14 UTC**. Payload and tree corruption are rejected; independent parity
regeneration detects FEC corruption that native AVB verification alone does not
detect. Its 81,252-byte receipt is
`30643b81e3465af2d1050b00b644fccb77b0135a231ce23972091dae64e5a8c6`;
the independent review is
`09c5b5b6bd1b3911b0a9ecfcc7ca7ae98f7f72577c475d32d8837a724d6db005`.
All 44 captured files rehash. This synthetic qualification precedes the real
production result recorded below; it does not itself touch the original images.

The **Camera capture v3** still fails before any Ninja query: the graph reader
rejects `builddir = ${g.bootstrap.outDir}` in the shared bootstrap shard. The
bounded diagnostic receipt
`295f71a37a16bf7e37ef4f353f838cdd2c8437264e60982886481e47d902047f`
identifies that exact expression, without admitting the graph, selecting the
APK or running a build. It does not establish full source/OUT nonmutation.
The shared v4 helper now admits only this exact variable under definition,
alias, ordering and uniqueness guards; 50 author and 22 independent offline
checks pass with zero skips. Its freeze does not authorize execution or prove
current native graph acceptance. Camera/provider recipe admission remains
required against v13i inputs.
The subsequent **Camera capture v4** also fails before any query, now with
`foreign, ambiguous, or continued protected bootstrap definition`. Its
1,292,107-byte failed receipt has SHA256
`47ad2ca0896131396bef550db42a0a473588cedd25774a10268092c27884467b`.
Post-capture verification did not complete. The subsequent successful bounded
**graph-diagnostic-v2** observation binds the same literal `g.bootstrap.outDir`
definition at bootstrap line 28 and main Soong line 500 in distinct roots.
Its 19,197-byte receipt is
`9ee94c44c294032b1a448723c0ac4cb05c9f8d4d01ab3dde1c697f5381338639`.
Shared v4 consumers were held pending a corrected per-root reader. The
diagnostic runs no queries and admits no graph; no APK selection, build,
producer proof or source/OUT nonmutation is inferred.

The subsequent **product-list-build-v1** prerequisite runs one actual upstream
Ninja copy edge from **21:09:37 to 21:09:40 UTC**. It produces a 26,921-byte
`product_packages.txt`, SHA256
`b2bd4d22699704f19b4179f727b207e342f9c8b2552f30e5f043defb80b068eb`,
matching all 1,230 selected packages and the raw producer input. All five
postchecks pass. The 204 source inputs, thirteen policy/eleven runtime outputs
and sixteen graph files are preserved. Only OUT `.ninja_log` grows by 126
bytes; source-root logs and dependency logs are unchanged. This is a metadata
component build, not a Camera APK build.

The **Camera read-only capture v5b** then passes four queries from **21:12:19
to 21:15:28 UTC**, with complete postchecks and unchanged guarded source,
output, graph and log inputs. Receipt SHA256 is
`95e6b79165a4c1641457274eefa756212daea28a1f5a239237c60ee8d9b7ba64`.
All 28 captured byte records and eight raw query streams rehash. Independent
review `d141fe4d1210fb9ea8e93649a9922702555ff155c17894f44c836c03c557885f`
is clear. Strict normal preoptimization and the three selected providers remain
intact. The Camera namespace is still unexported and unselected, with no APK
admission, build or grants. The complete protected-target inventory, source
transaction and actual build checks remain required.
The later inactive Camera stage preserves the exact eleven-file namespace and
original APK, with all fifteen file/directory modes checked. Its 69,116-byte
host capture is
`fd6c1efae5fe58037142d33fdb88ac8a06480024966897aaa32fd5c99e0128eb`;
independent review
`177217e380639605d1b2b3fe633653b7b40f427731a18e63dc8e0a95dc483646`
passes for staging only. All 204 source files, thirteen policy/eleven runtime
outputs and sixteen graphs are preserved. The active namespace is unchanged;
activation remains held for refreshed Camera source/output evidence and remaining
admission checks. The later VINTF command success does not select or build this APK.

The fresh **4 KiB Camera prerequisite capture** runs from **01:46:10 to
01:50:13 UTC**, with four passing read-only queries and unchanged source,
captured-output and query-log guards. Its 3,120,685-byte receipt is
`f930b76d8d4939587948f7540bc492bedf12b1e4a3e3a7181635eee01177ebde`.
Independent review
`8514c0502c3a8cc882639ccdd441b45d4b4b56a6ef246b7c7e60d189eae25cde`
rehashes 28 copied files, eight query streams and 83 host bindings. It verifies
the strict 4096/prebuilt/Bionic/preoptimization settings and unchanged sixteen
graph/four log identity records; it does not reread complete guest graph bytes.
Two namespace mapping warnings remain recorded, with all native Ninja stderr
streams empty. That capture does not include the complete target inventory,
activate the namespace or build an APK. The subsequent **complete target/alias
inventory capture** passes at **02:29:12 UTC**, with 1,570,791-byte receipt
`20aa80f53b90d9a74e3def15875d967b422488e23c1b2c756181b97b4b6b9092`.
It verifies source/output preservation. Independent inventory review now
passes: review
`8c500f3889cb0738707f2309ac729c35438f0e4935dd6c3b7eb59ec16270360a`
accepts the recorded v13ja inventory of 4,071 entries: 3,321 regular files
(2,263,742,391 bytes), 711 directories and 39 symlinks, without external
hardlinks. Twenty-four links stay within the target; fifteen reference eleven
absent guest `/system` or `/apex` destinations. No writable OUT alias escapes
the target, but ten protected policy intermediates are outside that tree and
must be protected separately in any future target-read-only build. This was
an inventory collection, not a Ninja query or target build. Target-file bodies
were not returned or independently rehashed by the host reviewer. Fresh
source/build/graph/configuration and inventory evidence is required after the
matrix exchange. Source activation, graph execution, APK build and runtime
grants remain unadmitted.

Provider capture v6 fails on ambiguous source/private-provider resolution.
The corrected **v7 read-only capture** passes five queries, retaining strict
16 KiB configuration and its source, graph, log and selected-input guards.
Its receipt is
`5fbf5e1bea88a90de270a654c3516efaf547b0c600af3a92bc96678e51c07ea7`.
All 26 selected ELF-check stamps are absent in that capture, which executes no
native ELF or symbol check. The subsequent **provider-elf-v13i-1** build runs
from **21:51:33 to 21:51:56 UTC** and returns exit 1 without timeout or overflow.
Its seven-file capture totals **91,591,689 bytes**; result SHA256 is
`b97659d56e4ff3e3b99a664cb1d604dffcc481f09f71e0723b45714b72b09313`.

| First provider ELF attempt | Targets |
| --- | ---: |
| Passed checks | 3 |
| Failed 4 KiB alignment against the retained 16 KiB requirement | 19 |
| Unreached or unproven | 4 |

Six separate dependency-strip failures report read-only temporary storage.
Source inputs, protected policy/runtime outputs and strict settings remain
unchanged, and postchecks complete. Independent review
`bc56abc6667dbbba2cfe2106790efc3459d5aa4260f13e8146547111ba8b9127`
reconstructs all 26 outcomes from the complete selection, native output and
both Ninja logs, with no findings about that evidence. The native build remains
failed; unreached targets are not passes and no full ABI or runtime claim follows.

The four-goal **provider-elf-v13i-2** follow-up runs from **22:38:06 to
22:38:14 UTC**, using the existing writable Soong temporary directory while
retaining the 16 KiB requirement. `libwfdconfigutils` passes; `libmiracastsystem`,
`libwfdcommonutils` and `libwfddisplayconfig` fail alignment. None of these four
targets remains unreached. Its result
`64107767b9c962853dfd6339049b327a29fe304a293b29fdb0ca6d9a76f72df7`
records all six global postchecks passing, no postcheck errors and no remaining
build processes. The native exit remains 1. The prior three passes and nineteen
failures are preserved, giving **four distinct passes and twenty-two alignment
failures** across both attempts. Normal dependency actions extend beyond the
four selected goals; this is not a claim of 26 fresh checker results. Independent
review `3df11175b7a9df364d4697e3b1c9861f6c6ec44d6b064e7448598469540649b2`
reconstructs the complete outcome inventory from all seven new capture files
(90,950,619 bytes), seven prior files and full raw envelopes, with no findings.
It accounts for thirteen repeated prior alignment failures separately. All 71
dependency outputs are present and no temporary-directory failure recurs;
twenty-two modules still fail before symbol checking. Other source, graph,
tool and dependency identities remain bound to the guarded native receipts,
without additional guest reads by the reviewer. No full ABI, provider runtime
or image-adoption result follows.

The first image-delivery dispatch fails before staging because its two
case-observation paths are absent; no image copy is attempted. The corrected
dispatch prepares independent private guest copies of the exact vendor/ODM
footer images. Its 61,136-byte receipt is
`dd11cdbee4b5d9193dfeb875ff2bfbfd5410cc4e2de14213577b386545b4c4ab`.
The guest verifies both destination hashes and preserves 204 source, thirteen
policy, eleven runtime and original-image inputs. Source/OUT are on a writable
mount; this is guarded preservation, not a read-only namespace claim. The
copier records distinct inodes, but raw inode numbers are not retained for
independent host reconstruction. Large image bodies stay in the guest.
Independent review
`77af2a71e0463379ec65aff3a787b18ec4d8627d31ce7c4e0e150ec606842045`
accepts only the private copies and guarded preservation, with no blocking
findings. Metadata/source/image adoption, signatures, physical fit and boot
remain unverified.

Commit **e304faa** brings the reviewed [delivery adapters](policy-image-delivery.md)
and [generator capability](target-files-delivery-integration.md) into ten
maintained workspace files. The original metadata tools and factory selectors
remain unchanged. Repeated delivery candidates match at admission SHA256
`0f8bea1ac8a16754633af3430089e565c42c8d9c7be4a74cd07cec9bdb740b11`;
the maintained consumer freeze is
`e30d0904189ddf16d62f4bd0a4702e8d5cdae74b7e974d9e2fa8a29c9a7ab674`.
Both maintained metadata bundles preserve all 205 original metadata files /
6,460,780 bytes while binding the reviewed leaves and current-policy/copy
evidence. This is host source admission, not a selected guest input. Normal
product Kati, the explicit source/image transaction and ordinary metadata-hook checks
remain pending; no date, care-map or page-size profile is selected by that
delivery candidate. Its first isolated native Kati fixture records **58 passed
and two failed cases, zero skips**. Both undefined original-image selector
cases stop at `probe.mk:10: missing separator` before reaching the expected
production diagnostic. The preserved embedded result is
`fdf8d649e0d74b1d045e48f54d6aac6f098b99b3c77f1083b9661bf74d0f1f39`.
Source/postflight guards pass, with no timeout or forced cleanup; the owned
jail process group is quiescent. The corrected fixture now passes **all 60
cases with zero failures or skips**. Its dispatch is
`8ac0a9d80c4e649994faa3e8f263fee1049b69136c6e9c82d40809e899fd7c51`,
and embedded probe result is
`f1ed984cfe2aec07c40bedd8baedd3b0a0a3843bc317b64ad22da6f2a83a4c3f`.
Source and postflight guards, namespace/limits and owned-group cleanup pass.
The production include is unchanged; only the fixture was corrected. This
does not execute the ordinary product route, Ninja or the metadata hook, verify
real images or adopt source/image inputs. Independent review
`e1c179ede17ac0790b2f5dd50314f06c877afc0c4b65eca781151bf337bf7497`
accepts the isolated fixture after reviewing all 73 captured payloads and the
complete native result. The first 58/2 attempt stays failed.

Commit **137f438** adds the explicitly paired 4 KiB delivery successor in seven
maintained files. Both host metadata bundles contain the same **247 files**,
including all 205 preserved original metadata members; their shared receipt is
`dbefc908c596a25b70aa75956cb02e52505b00ce314c069e6064fa311ed27680`.
The metadata freeze is
`373d17e585ea778f0b7d331e8b896a77efe7b82578688f49858da0b81e53e666`.
Two **47-file** device candidates match admission
`159ad7e2807fe143a7484b44c286d210500ac0a3c43134e8a035a05824cb35c2`;
their freeze is
`f09d8b981b78d452478d0654987786c24aeadb6aadf6b3692998f5677229f1fb`.
The new mode binds the actual 37-goal build and exact current 4 KiB profile.
Independent host review checks the metadata consumer, repeated candidates and
source composition within its stated scope. It does not rerun native
installation or read the large image bodies. The historical private-copy
receipt remains provenance, not a fresh 4 KiB image-copy operation. That host
checkpoint did not install the candidate sources or metadata/image selections;
the later matrix source transaction is separate. Normal product execution and
the metadata hook remain pending. Older descriptors and delivery modes are unchanged.

The subsequent **inactive 4 KiB policy-image stage passes** with dispatch
`b2607057026c8ba6be71fb9d810fa22d91a2719672fb7416eeef39522e86de4a`
and native receipt
`0bbfe2a95d4a2a205602119120376b5b224b9d9dcb3df15bb5abbd056a77c651`.
It prepares a separate candidate subtree containing the exact vendor/ODM
keyless leaf bytes and their bound controls, rehashing current source, policy
and runtime inputs. The source/OUT namespace is writable, so preservation is
verified rather than attributed to read-only mounting. Active source and
Android outputs remain unchanged. Complete stage review
`ddffc5ec310a0dc624e365abbc9919e5aa7948e240b69abb7dec70a048badcde`
binds the separate transport and native-receipt reviews, with no findings.
All eleven captured transport files verify; large image bodies were not
reopened by the host reviewer. The admitted scope is this inactive four-file
copy only. A later transaction requires deliberate rebase and fresh source
admission after the matrix correction; metadata installation, active image
selection and signed-parent/physical-fit validation remain separate.

The **matrix packaging qualification v2** runs from **07:59:50 to 08:00:47 UTC
on August 31** and passes. Its receipt is
`05733356e962a634a3ed2911c9e537b9060b03e38f8d6548f5a4507f84298c7a`
(206,546 bytes). The complete eight-file / 311,701-byte readback is bound by
`04c3a984a9a1bba0018da98cf133841455058b9ced587fbcfabffe2b82e092dc`
(417,987 bytes). Qualification verifies seven current policy inputs and
recomputes the three digest recipes in their pinned input order; it performs
**zero installed-sidecar artifact checks** and does not run normal Android
genrules or the actual target-files hook.

The first inactive-stage attempt failed because the private mi_ext bundle did
not have the required directory mode. The private-view successor then failed
when it assumed an installed platform digest already existed. Both failed
attempts, diagnostics and `INCOMPLETE` markers remain unchanged. The platform
sidecar is confirmed absent by that failure; the system_ext/product installed
files and normal generator intermediates remain unobserved. Absence from an
earlier capture is not evidence that every possible output is missing.
The source-backed producer audit is
`35f52e554cf82edbcf31fea556c079b5a66ac76c463c13d1b6a3d1da7e0944dc`
(10,298 bytes). The normal modules remain required:

- `plat_sepolicy_and_mapping.sha256`
- `system_ext_sepolicy_and_mapping.sha256`
- `product_sepolicy_and_mapping.sha256`

Their real installed 65-byte contents must match the recomputed digests. The
unchanged final metadata `_policy_gate` must still inspect all seven actual
target-files policy inputs and all three installed framework-sidecar paths;
`_installation_report` must reject missing sidecars. No digest file is fabricated,
copied from isolated validation outputs or admitted by counting a missing check
as a pass. Qualification preserves all 269 archive copies (7,651,215,453 bytes),
37 source preimages, 542 staged payload files and six staged guest-copy inputs.
Its read-only scope includes rechecking the selected derivative images and the
205 original metadata members, not adopting a final flashable image.

The subsequent eight-operation source installer returns a verified commit at
**08:13:39 UTC**. Its 539-byte completion is
`f708e58837b2bfa720154d22ad9176a040203a0fefca0f3794f8dc7595793bb9`;
the journal ends at sequence 18, for nineteen events. The complete nine-file /
549,554-byte readback is bound by
`07b27b0a134610fcd1a14c6b6113366f2a4125df7a83197aaf7b9af79485bd7e`
(735,413 bytes). The installation receipt is
`44cab4e34179269cd984f5fde4539ab5750a606d4eec7b8d3ae5e6b5346c5ec5`
(382,046 bytes), and the journal is
`ca835aaf8b93cee76f9aa79c9700b1fcfd264571ae5dea00b33b75638bd3851c`
(57,929 bytes). The installed-input semantic check is
`6ffcfd421198d1b844fb0c34832f2d863315fba48c4dcebf5303158544a91ea2`
(27,174 bytes), with zero installed-sidecar checks as before.

Three source-file exchanges update the combined build/make recipe; five tree
operations (three exchanges and two additions) install the device tree,
recovery records, mi_ext records, metadata
bundle and reviewed policy-image bundle. The actual source inventory grows
from 222 to **475 files**; 478 belongs to a prospective construction profile.
The selected vendor/ODM `NONE` leaf images are the existing `ce11f1c6…` and
`854c0047…` derivatives. Original images and independent prior copies remain
preserved. Recovery stays exactly working76 (`a130ba75…`), and mi_ext image bytes
remain unchanged. The installer verifies all 269 prior outputs, thirteen policy
files and eleven runtime files unchanged, with normal Android enforcement
required. The 6,900-byte independent transaction review is
`f6b8f2441189092ec8840953f95246976822d61471860351b9590b412011c5d1`.
It binds all nine captured files, nineteen events, eight operations and twelve
source-project records without reopening the live guest, large image bodies or
archives, and without executing a new installation helper in the guest.
This is actual source-input selection, not a new image build or final
flashable-artifact admission. Construction and pinned-date source remain unselected
at that packaging checkpoint. No native
build, normal sidecar generation or target-files hook runs in the transaction.
Scoped VINTF/crypto evidence does not become complete input, runtime, AVB-chain,
OTA or boot verification through source selection.

The subsequent **first-target-files-v1** transaction commits at **08:45:28 UTC**,
with **three operations and nine journal events**. One device-tree exchange adds
the construction guard; two vendor/lineage file exchanges select patch 0012 and
its pinned-date helper. The installation is
`f70dab48bb862a06fef4d67e0b2ae76369c77eeb06ebc82f4bbd4cea8d7591b7`
(1,150,851 bytes). Complete per-file readback retains four files / 2,430,463 bytes,
including the unchanged staged record. It verifies **478 source files and modes
across twelve projects**, preserving prior outputs and strict 4 KiB settings.
Independent transaction review
`98b1152497a10bb196121eeb83d3b606f8a4215117efbccb2c48fe63f1c5de90`
(9,839 bytes) passes for the recorded source installation without reopening
live source, archives or image bodies. Native dispatch and the full
configuration delta remain unadmitted. No `BUILD_NUMBER`, product metadata,
date-helper execution, sidecar output or native build success is inferred;
readiness and flash permission remain false.
Captured `envsetup.mk` includes release configuration at line 51 and board
configuration at line 368; the former forbids direct `TARGET_RELEASE` access
before the original guard reads it. This source-order finding is not a failed
native build. Its separate correction commits at **09:17:15 UTC** through one
exchange and five journal events, replacing only that guard with
`fe1e32cffe0d7b7ba20a9fd1d90f1cf8712f9fa6b7aa0e3ec1a90a6b7058c469`
(2,553 bytes). Eight complete stable reads return 1,664,080 bytes, including the
active corrected guard and both original preimages. Exactly one of 478 source
identities changes; all twelve project records, strict 4 KiB settings and prior
outputs remain unchanged. The guard checks four resolved `RELEASE_*` flags;
the raw `bp4a` selector still requires separate invocation binding. The 23 host
preparation tests pass with zero skips. Independent actual correction review
`3a4a4408a3ebbeb6cb901f36cdc2adad8bf5fc2a9c5baa1968f738dbba151abf`
(9,389 bytes) binds the captured guard and recorded source vector without
reopening live source or archives. Normal Kati parsing, generated metadata and
the first build are not verified by this source transaction.

The ordinary-product metadata closure now binds **1,475 unique inputs**: 1,474
named-file inputs and one process-backed Rosetta runtime identity. Its frozen
five-descriptor composition derives `nezha.76dfc5727ce7a5291cb53565` without
claiming that Android has generated that build number. Independent host review
binds the selected composition and deterministic calculation; it does not admit
native dispatch, all future packaging/signing inputs or cross-date image equality.

The first three product-configuration attempts each return exit 1 before native
invocation or output preparation. Attempt 1 stops on the source-history reader's
`file` alias; attempt 2 rejects conflicting inherited `OUT_DIR`; attempt 3 retains
that conflict after the container environment override. An isolated observation
confirms that the override did not change the inherited output directory. These
are preflight failures, not Kati/compiler failures. The fourth attempt runs from
**10:16:56 to 10:17:52 UTC** and returns native exit 1: dumpvars rejects obsolete
`BUILD_DATETIME` and directs the caller to `BUILD_DATETIME_FROM_FILE`. Its stdout
is empty and stderr is 513 bytes, including two occurrences of the retained
kernel-origin/AVB warning. Preflight completes, all six source/input admission
sets match before and after, and no postcheck errors are reported; the product
profile itself does not complete or validate. Seven metadata/log preservation
copies verify. No image invalidation occurs, but whole-output-tree immutability
is not claimed. The later source-bound query correction changes the query
adapters, not Android source; the failed receipt remains unchanged.

The corrected **config5** and **context5** native queries finish at **10:40:19**
and **10:45:23 UTC**, both with exit 0 and successful value postchecks: 21 primary
configuration fields and seven context fields. A fresh read-only confirmation
rehashes both guest result files. Each query preserves the six source/input
guard sets, 1,475 selected inputs, 478 source files, 1,179 pins and the complete
generated configuration. Independent reviews of both queries are clear within
that scope.
The three `FROM_FILE` assignments are checked as literal references. These
queries do not verify metadata-file bodies or freshness; the later ordinary
phase supplies the separate value evidence below. The complete property-declaration string matches the expected source
projection, but effective postprocessed properties remain unverified. Both
known kernel-origin/AVB warning occurrences remain in each query. Neither
query verifies Ninja actions, a new producer graph, sidecar outputs, images,
target-files or boot.

The **nothing1** native invocation runs from **10:56:20 to 11:09:02 UTC** and
returns exit 0. Its wrapper returns exit 1: `verify_source_history` and
`verify_strict_settings` each report that the full generated Soong configuration
differs from the exact reviewed phase state. Four after-admission entries match,
but the archive entry returns cached source-history data after the configuration
guard throws. Only selected-input, source-lock and protected-input groups are
fresh. Neither the retained source-history observation nor that archive entry
is a fresh full after-source/archive verification. The profile does not complete, and
its metadata postcheck remains null, so no six-file content/freshness result is
claimed. Seven preservation copies verify and no image invalidation is requested;
whole-output-tree immutability is not claimed. The 18,464-byte native stdout ends
at the `nothing` phony target and native stderr is empty. These raw logs and the
failed wrapper are preserved without diagnosing the configuration change or
claiming component-image, target-files or boot success.

The exact seven-leaf explanation (`79ab14bf06bd56b733d35e0ff97dae83c010a1dff17ee1b24bef28d88b51101d`)
reconstructs the complete 254-key configuration from captured source rules.
`LINEAGE_BUILD` adds the Evolution policy directories, removes the conditional
AllAudio/APNs block and Camera2/debug-su selections, and re-exports the existing
4 KiB maximum. The observed vendor-policy branch is inferred from its exact
directory list; its selector was not directly dumped. The source-admission
review permits only the exact `nothing` retry, not current policy or images.

The **nothing2** native invocation runs from **11:43:13 to 11:44:57 UTC**, with
native and wrapper exit 0. All six source/input guards use fresh current-phase
proof and match, including the complete reviewed configuration. The frozen
validator checks all six metadata bodies (240 bytes); fresh read-only
confirmation rehashes the result and files. Independent actual review
`b704098dede258e57548694ad630d466e51b14d1e5e6bc01e7d0ced64ee55cc3`
(15,162 bytes) is clear within this scope. The build-number file contains
`nezha.76dfc5727ce7a5291cb53565`. This does not prove that this invocation freshly
rewrote every file: output-freshness and Ninja-action proof remain false.
Kernel-origin/AVB and UID/GID warnings remain. No image, target-files or boot
success follows, and the original nothing1 failure/cache limits stay preserved.

The expanded Evolution policy now requires new source/M4 integration, strict
compilation and context checks against the factory inputs. The older thirteen
policy identities are preserved, not promoted to full current compatibility.
Commit `3c9cd2adfa5aff8de8c6ee0c670ba415f6664049` prepares
[patch 0015](evolution-backuptool-enforcing.md), wrapping only the existing
backuptool permissive declaration in `recovery_only`. Types, permissions and
assertions are unchanged. Host qualification is separate from Android M4,
policy compilation and installation, none of which is claimed for this patch.

Commit `5d557a06182bd8c8ea16db726cd80ef16587626d` adds the explicit
[Evolution-base contract and reference checker](evolution-policy-base.md),
source filegroups and optional bundle/generator integration. Omitting the option
preserves the previous path. The source freeze
`59f2a3dfea0842e8bd488aa532fd00daa2a5ed1f4d2d3aedc8a354765e321a64`
and independent review
`1b053251eeb62da72a6e62c0c62156bb5c4bb6d6d2fc9531ece6bfb59d353c9d`
bind the source-only result. Normal Android M4, CIL and mapping producers supply
the independent base; the checker compares the full corpus with that base plus
the reviewed owned contribution without writing generated CIL. Native producer
provenance, strict compilation, contexts and unfiltered binary analysis remain
required.

Two actual host stagings reproduce **57 files / 6,204,545 bytes**, including
receipt `27741ceaef6b46f50842d8c466baf46dd7eb93b255f10805d138a6b775957186`.
The bundle freeze is
`065bc5d4c5c5aee362a3ed8de3d5a4bffa9dddd039debfb03296a274873773e3`.
Compared with the preserved v13h bundle, 49 payload members are unchanged,
three change, four are added and none are removed. The ten classification CIL
inputs, thirteen factory contexts and ten prior owned source copies remain
exact. Verification from the relocated 36-file trusted control tree matches
the workspace verifier. The separate component packet adds only the device
policy filegroup Blueprint; no existing device Makefile, root Blueprint, page
size, construction or image selector changes.

This is host preparation, with no VM source installation or new native policy
result. The proposed 32-goal phase includes twelve distinct normal policy
binaries requiring unfiltered permissive-domain analysis. Existing diagnostic
compatibility producers must not be called strict neverallow passes. Actual
review must also resolve the seven Evolution-base property-prefix label and
permission effects; the four owned-property checks do not cover them. Selected
vendor-source contributions are not delivered into opaque factory images by
this reference mechanism. Current image compatibility, normal enforcement,
all assertions, target-files and device validation remain separate gates.

The host packaging rebase now produces identical validated candidates from the
then-current v13ha inputs while preserving the provider correction, strict settings
and original images. Its freeze is
`cf0622bfc69ff2e431442b4348edc6594403d2b9812fc696a1d33c4aa6e6b5f6`;
the candidate admission is
`4aaf5a905a00745e628750b6de8e18c327636456516e2739293a103fb862f66c`.
The separate host metadata bridge verifies all 205 original metadata members
against both raw reconstruction passes. Delivery still requires source-bound
admission of the new footer outputs. These are host preparation results, without
guest source installation, image adoption, native target-files packaging or
compatibility admission; no unfinished native packet is counted as a pass.

The retained Soong configuration snapshot selects `DeviceMaxPageSizeSupported`
as `16384` and `DeviceCheckPrebuiltMaxPageSize=true`, while static inspection
finds 22 of the 26 provider ELFs use 4 KiB load alignment; the other four use
16 KiB. The snapshot was collected during the component build. The optional
[4 KiB experiment](nezha-page-size.md), commit `84d63c2`, and its host v13g
candidate remain unadopted historical inputs. The user now explicitly accepts
a **4 KiB first-boot baseline**, without requiring 16 KiB compatibility for the
initial bring-up. Commit **17cde61** adds the separate
[current-provider successor](nezha-page-size-v2-integration.md), with the check
enabled at 4096 and no ignore flags. Both actual host candidates match admission
`392485b8ef5005f6d8079487c7a8ee7931597bacaab593478277f8201c4d03a2`:
44 payloads plus admission, changing only the generated product fragment and
adding the v2 descriptor. The stock Image/configuration and current provider
bindings are independently reverified. The freeze is
`600e286a1be0ee29d06c26a831cd7ef92db042915bef695a4ce234873c429551`.
Default rendering and the old descriptor remain unchanged. Combining this
profile through the earlier delivery mode remains explicitly blocked. The
separate `137f438` successor above supplies reviewed host pairing to the actual
native result, without selecting those delivery inputs in the guest.
The corrected v13ja source transaction below now selects 4096. This does not turn
the failed 16 KiB checks into passes or establish VTS compatibility, native
image adoption or hardware support; normal Android SELinux remains enforcing.
The **23:30:55 UTC** pre-install snapshot binds 216 present files among 266
requested paths, totaling 7,646,909,660 bytes. All 1,179 base revisions and
origins match; the six reviewed patched projects remain intact. It freshly
checks 204 source inputs, thirteen policy and eleven runtime outputs, with
the active maximum still 16384 and checks enabled. Receipt
`b3bda63a1e5d62996f80766d2280cb073aaaf083ee80941560523d5b005d7ff2`
verifies snapshot preparation, not a source transaction or native 4 KiB build.
The subsequent inactive **run-v13j** stage returns exit 1 before installation:
the archive verifier's `ensure_absent` call requires a missing ancestor.
Diagnostic `1431f52ca97ebedabff070a8d9568d72cfa254e1db7472a3166830c0a206e657`
is preserved with the backup; the active source/OUT was not replaced by that
failed attempt.

The corrected **run-v13ja** stage passes with receipt
`7b3eba00c88f3ec2dbad5d58259f62662ac60e7f32ae8ac497cad9a25f2bbe8c`.
Its installation commits at **2026-08-31 00:07:36 UTC (August 30 in New York)**:
one device-tree exchange, with five journal events ending in `commit_verified`.
The captured installation is
`0c477a6a405fec0f3a282fcdf3f1fb726ba0fd2bee69b9c5cb8dd03ae72f109a`;
the journal is
`26dbbec24fb165541072a2645a4c929bf05a05d00336d7f6ae10865267d08db9`.
Only the generated product fragment differs within the exchanged device tree.
The prior tree and independent backup copies remain retained. The independent
review passes eight host checks with zero skips, binding captured hashes and
journal relationships. It does not independently rerun installation verification
or reread guest source/output/archive bytes; the receipt's preservation check
does not freshly check live outputs.

The **37-goal pagesize-v13j-1** component build runs from **00:13:06 to
00:43:11 UTC on August 31**, with request
`9cba3287760503b47a4cc9402d019f4e29ec38a916c15f516733f9252a8a399b`.
It returns exit 0, with no post-build error or remaining build process. Result
`949bd0882087d403637e542a0bc82c37b4ecabc8196ba0c160fe8a3ddd46e145`
verifies the generated maximum's transition from 16384 to 4096, retaining the
enabled ELF/prebuilt checks. Source verification covers 204 files; all thirteen
protected policy and eleven runtime identities match the preceding result.
The existing strict policy analysis is reused by byte identity, not relabeled
as a new semantic analysis. The partial VINTF alias explicitly skips
`checkMatrixHalsHasDefinition` for the device matrix without a level; this is
not a zero-skipped native compatibility result.

The completed-build readback contains **54 selected file bodies / 3,655,836
bytes**, all rehashed, and metadata for **36 APEX packages**. No image or APEX
bodies are returned. Its capture is
`af16ba1962d75abd1912d334aeee90f73604d40d1be0dac6c34ed3602b65fc45`.
The request includes policy, allocator and partial VINTF artifact targets;
it is not the separate 26-provider ELF check or full unfiltered compatibility run.

The scoped review
`dc7d9ea95e8c5775dedc30f3bce14416f4749bf20122737eca87041ba84e0a55`
and independent log review verify **4,890 normal Ninja action descriptions
after 163 frontend steps**. The displayed 5,053 total is not a test count.
Only the maximum changes among all 254 raw Soong settings. Fresh CIL,
neverallow and context action descriptions are present, but no separately
named fresh Treble/freeze action or new assertion/permissive analysis is claimed.
The captured 27,224-byte allocator has four load segments aligned to 4096, with
matching offset/address alignment. Its logged link/strip/install actions do
not establish fresh C++ compilation, qualified producer capture or runtime
registration. Vendor-manifest and device/kernel FCM warnings remain recorded;
the skipped matrix-definition subcheck is not a pass.

The separate **provider-elf-v13j-4k-1** normal build runs from
**2026-08-31 01:14:54 to 01:15:10 UTC** and passes **all 26 fresh ELF and symbol
checks** at 4096. Its 924,077-byte result is
`c0ace122a40697f42a1d014e6575d872594cf88e038bacb979cab3a5b6c53c54`.
The preceding five-query read-only capture binds the current graph/settings
with receipt `677231ed3dd097fed1876020ae67448d02dae38e1eb426de87adc9855654dbea`.
The native build executes 48 actions: 26 checks and 22 dependency actions.
Independent review replays all seven native evidence files / 93,444,455 bytes
and the complete transport envelopes. Each pass has its exact verbose command,
a new complete Ninja-log row and an empty current stamp; the four existing
stamps are not counted as cached passes. All 71 dependency outputs are present,
fourteen historical evidence files remain preserved, and the strict settings,
source, graph, policy and runtime guards pass, including 86 protected read-only
paths. The 200,837-byte independent review is
`b3bf3e304dc1316685d88823625cda4a6f37403758e41c59ad2b2be94621d3f6`.
The selected ELF/symbol gate passes; this does not establish complete ABI
compatibility, runtime service registration, full VINTF, VTS or boot behavior.
The earlier 16 KiB inventory remains four passes and twenty-two alignment
failures, unchanged.

The [native date fixture record](../research/pinned-build-metadata-native.json)
verifies nine positive/legacy cases and 24 specific negative outcomes, with
zero skips, at **01:33:47 UTC**. Source and Android output mounts remained
read-only. The live date patch/helper were not installed, and the first failed
diagnostic harness is preserved. This is not an ordinary product configuration,
an actual clock-rollover test or a reproducible-image result.

The metadata Kati probe completed at **22:39:19 UTC** with 14 positive and 29
specific negative cases, source and Android outputs unchanged. It parses the
exact hash-bound patch-0009 guard and checks the positive dependency closure;
it does not execute Ninja, the metadata verifier or the target-files recipe.
The metadata source-admission changes are committed as `9c528cf`; they are
not included in the frozen v12e installation.

The latest full `python3 -m unittest discover -s tests -v` run passed
**4,043 tests in 169.140 seconds with zero failures, errors or skips**, executed
by the coordinator with all ten frozen Evolution-base files unchanged and then
committed as `5d557a0`. Its log is
`ac46eb711280f518615d4c0d26a2b0798e1c944aa6c6bd360045320c7d519733`;
completion receipt
`bd01a8bc0f7de9ede079da9c5be17565c5678cabfaa1543ef13dbd2920b50261`
binds the exact source cohort. This later central-document update is separate.
The preceding **3,984-test run in 168.104 seconds** was executed by the
coordinator in an isolated `ee2d19db` snapshot plus the four frozen
backuptool files, equivalent to commit `3c9cd2a`. The log is
`d42c8ce8cbd478ba444841b46b33ff77504d73cdc8c53678e3a671f7ac68fba5`.
Other then-in-progress root policy edits and its later documentation update
were excluded from that isolated run. The preceding
working-tree run passed **3,972 in 169.113 seconds**, with all three checkpoint
documents unchanged. Its later factual evidence refresh is separate; its log is
`43cb0ecd5d2b68942fe35389fabc963eb30639d4f64d0cef03c8a133974e1a8e`.
The earlier v1 launcher failed preflight before running tests; it is not counted
as a skipped or completed suite. The preceding 3,972-test run took 168.418
seconds, preserving its three product-input checkpoint documents; its log remains
`e14c7ba21776f0dde729c1511131e8c741187334674e8f44c493a8df520a28d0`.
The preceding 3,972-test run took 166.208 seconds, preserving all eight
construction-source checkpoint files; its log remains
`ab23f5a27305eddfd458a911f6f1ab64994efab9781289ece8185db533ffe494`.
The preceding 3,961-test run took 171.407 seconds, preserving all three packaging
checkpoint files; its log remains
`8840c2da10b9178247884e491f6c6653520c3fd5bc9dcbc79ae284df0cfa6497`.
The earlier 3,961-test run took 166.023 seconds, preserving all three scoped
VINTF checkpoint files; its log remains
`983894a1ee29fb2fdf79222d5e6f3b1ba9ea74bf56b10d0c071080c4224b3c91`.
The earlier 3,961-test run took 165.776 seconds, preserving all three provider
checkpoint files; its log remains
`f0ffbbd2f6357698175f640a5173dd86f9fe706c349fc78b40dcf642c227221a`.
The earlier 3,961-test run took 167.201 seconds, preserving all five checkpoint
files; its log remains
`7bfd1ea06a54e1674670689904bf285b519ff157077f03d46ed203aefa241cd1`.
The earlier 3,961-test run took 173.222 seconds, preserving all seven bound
files; its log remains
`20f5203fcd2658f11677c00a003a61cf0cbb8134d9cbc448c6fe9b5ed7b12d72`.
The new [read-only target-files AVB inventory](target-files-avb-inventory.md)
adds 42 synthetic tests. It hashes bounded ZIP roles and explicit retained
firmware inputs, without extraction, image validation, signing or actual
target-files admission. The preceding full run passed
**3,919 tests in 164.329 seconds**, executed
by the coordinator, with all four checkpoint documents unchanged throughout.
They were subsequently committed as `4116868`; the full log is
`b5770d1840b800f9ea6fbcd6169ef77e2fc95498ed9c7e46b30ee9a447779605`.
The preceding matrix-owner run passed **3,919 in 164.103 seconds**.
The five frozen public files match `c3686ed`; executable
controls and tests stayed unchanged while the dedicated guide gained host
verification details during the run. The full log is
`6c9e801fa3ced648913da6f1d67d5991f19e4d0e6789cb313b7b6e9df3194d4d`.
Native matrix and APEX cryptographic results remain separate. The preceding
run passed **3,892 tests in 164.280 seconds**, executed
by the care-map owner, covering `4070b1a` and the four files committed unchanged
as `203ab67`. The coordinator rehashed the complete log
`7b07299ac970db1d268613633b0da58ac535ef5799bbef5dd457174c13007125`.
The handoff is
`4d0dcc25a490b96739f6cc550dd674d4026af0313250c0b3c4ee2723fc5e012a`.
This is host coverage for the inactive original-ODM-import care-map successor;
native codec/tool qualification, the final Evolution SYSTEM input and active
composition remain pending. Later matrix source changes are not covered.
The preceding run passed **3,854 tests in 172.911 seconds**, executed
by the construction owner for the five files committed as `4070b1a`.
The coordinator independently rehashed the complete log
`7740705a60d9546d807c2068125743832720a6bd967378c522814ed390176711`.
This run excludes the concurrently authored 0014 care-map tests; a combined
coordinator rerun is pending. The preceding coordinator run passed
**3,835 tests in 166.748 seconds** on `8fc2162` with the seven delivery successor files later
committed unchanged as `137f438`. The complete log is
`a65f67c99fe5ce4dc66c709db130cd38d9f1fff36e1c2cee83dacb6946d22ed6`.
The preceding coordinator run passed **3,795 tests in 163.444 seconds** on
committed `17cde61`, with these checkpoint documents then uncommitted.
The page-size integration owner's preceding run passed 3,795 in
143.328 seconds; the coordinator rehashed that complete log. The six frozen
public files match the commit. The previous coordinator
run passed 3,778 in 157.969 seconds with the ten maintained delivery files
uncommitted, before their commit as `e304faa`. The preceding Camera metadata/capture and private-copy
checkpoint passed 3,711 in 154.009 seconds; the earlier allocator component
checkpoint passed 3,711 in 152.316 seconds. The preceding 3,711-test
run passed in 158.487 seconds for the optional [mi_ext care-map source](mi-ext-care-map.md)
committed as `8144704`. It remains inactive: authentic ODM imports and the final
Evolution SYSTEM property input still require qualification. The previous
coordinator run passed 3,665 in 156.924 seconds for allocator capability
`1647192`. The previous 3,651-test run in 156.391 seconds was executed by the target-files metadata
agent with bytecode writing disabled; the
coordinator independently verified the complete log. The preceding coordinator
run passed 3,651 in 160.426 seconds after the v13h raw-image milestone.
Those earlier runs used unchanged public code from the
3,651-test run in 158.950 seconds for the profile committed as `78376c7`. The
preceding v13ha integration run passed 3,634 in 152.111 seconds. The previous coordinator
run passed 3,634 in 156.509
seconds for the v7 producer/consumer integration committed as `364ab89`. The preceding
policy-image profile checkpoint passed 3,591 tests in 152.682 seconds at
`35324b4`. The prior coordinator component
checkpoint passed **3,558 tests in 163.269 seconds**. The separate page-size agent
run passed the same 3,558 tests in 153.985 seconds at `84d63c2`; the later
`d3c29a5` native-date documentation records separate focused rechecks.
The previous coordinator full run passed **3,517 tests in 176.383 seconds**.
The date-patch agent's separate full run passed the same 3,517 tests in
156.752 seconds, and the
coordinator also reran its 12 focused tests successfully. The earlier
coordinator full run passed **3,505 tests in 161.056 seconds**, following the
3,303-, 3,336- and 3,363-test checkpoints. These are workspace-tooling results,
not an Android build result or a phone test. Later source changes require their
own rerun. Earlier failing runs remain preserved rather than counted as passes.

The later combined-source change passed a coordinator run of **441 focused
tests in 19.955 seconds** and a separate agent-run full suite of **3,452 tests**,
both with zero skips. That later full run is not relabeled as the coordinator's
earlier 3,363-test checkpoint. The 3,505-test coordinator run covers the
committed policy-image preparation changes as well.

## EROFS qualification and image adoption

The authored [metadata exporter](../tools/erofs-metadata/README.md) built through
the actual Android graph at **21:15:53 UTC** in phase `erofs-tool-v1`, with six
main Ninja actions after 163 configuration steps (169 cumulative progress
entries) and verified read-only source mounts. Its binary SHA256 is
`fdb9fd26272e3552a70e08d32ea831b3b7a9afa5ef21ca5b4a53ad194d65361b`.
The pinned `external/erofs-utils` revision remains
`2c190a73fceb29f00da0558e44bb88ce19ec5bf4`.

| Native qualification | Passed | Failed | Skipped | Result |
| --- | ---: | ---: | ---: | --- |
| Synthetic v3 | 25 | 2 | 0 | Exporter checks pass; the pinned tar writer drops fractional nanoseconds and upstream fsck reports an error for an empty-xattr fixture despite exit zero |
| Read-only stock v1 | 4 | 2 | 0 | Both original filesystems pass upstream fsck; both exporter runs fail on their root shared-xattr header |
| Shared-xattr v4 | 8 | 0 | 0 | Corrected native exporter accepts valid block-zero shared entries and passes the regression checks |
| Synthetic v4 | 25 | 2 | 0 | Corrected exporter checks pass; the same fractional-nanosecond writer and empty-xattr fsck failures remain |
| Read-only stock v2 | 6 | 0 | 0 | Both original images export completely and pass upstream fsck; 3,910 vendor and 3,059 ODM entries are recorded |
| Synthetic writer round trip | 11 | 6 | 0 | Both fixture partitions reproduce the exact five-file change across two independent derivations; all six upstream empty-xattr checks fail |
| Production file-size primitives v2 | 4 | 0 | 0 | Finite 2 GiB/6 GiB syscall limits, sparse readback/cleanup, bounded stdout overflow and input preservation pass; no production mkfs execution |
| Full unchanged-vendor v2 | 8 | 0 | 0 | Two independent TAR/image/export passes preserve the complete stock vendor contents and nonphysical metadata; exact 2 GiB recipe qualified, no policy adoption |
| Full unchanged-ODM v1 | 8 | 0 | 0 | Two independent TAR/image/export passes preserve all 3,059 stock paths and 2,925 regular contents; exact 6 GiB recipe qualified, no policy adoption |

The stock failure exposed an invalid exporter assumption that a shared xattr
table cannot begin at block zero. The narrow C correction, committed as
`f3d740e3d6ce5c7509bc8601e68a9e681111efde`, compiled in the successful v12f build.
It was not part of the v1 binary or earlier runtime probes above. The corrected
binary is 3,611,664 bytes with SHA256
`9fa98c5d9a698868b730201852c0029747c3a7458f1a9dc40426d878f8e3d270`.
Its fresh shared-xattr tests passed at **23:42:26 UTC** and the read-only stock
qualification completed at **23:47:05 UTC**, with source, Android outputs and
original images unchanged. The tool capture alone is not build provenance;
the separate successful C build and unchanged source manifest supply that
binding. All exported stock inode timestamps have zero fractional nanoseconds,
and the stock receipts report no hardlink groups. At that checkpoint neither
factory filesystem had a complete writer round trip; the later vendor result
is recorded below. The existing bounds
checks remain. The first
native fixture attempts and their resource-limit failures are retained.

The actual synthetic writer run completed at **23:49:25 UTC**. It created two
independent derivations of each vendor/ODM fixture and reproduced their tar,
image and exported-manifest bytes with exactly five literal replacements.
Exports, unchanged-input checks and tool stability pass. The overall result is
**failed: 11 passes, six failures, zero skips**. Each seed and each derived
image contains an empty-xattr fixture that makes upstream fsck log an error
despite exiting zero; those six failures remain enforced. The original factory
inputs have no empty xattrs or fractional nanoseconds, but that observation
does not qualify a factory writer or prove an actual factory derivation.

The first host launcher correctly refused to start while a read-only Ninja
query was active. The retry changed only host evidence filenames. Earlier
partial host captures are also retained: Mac case folding and non-UTF8 names
prevented faithful direct-path copies. The complete capture uses 158 flat
files totaling 3,566,793 bytes; `path_hex` preserves each original byte path and
`captured_path` selects its hashed flat filename. Capture-manifest SHA256 is
`d70018fcdc6beefa952cf9216df0ae525999d745bcf7271fe9a729285e13da9b`.
These capture corrections do not change the native qualification result.
No original factory image, source or Android output was changed, and no AVB,
retained-image writer admission or policy-image adoption passed.

The later production-size probe compiled and ran an x86-64 C executable through
the existing Rosetta path, with 64-bit file offsets. Both finite-limit cases
reject oversized growth and verify a bounded sparse write at the last valid
byte; the overflow case terminates the whole process group and drains both
pipes. All four checks pass, with zero skips, and all 59 captured files rehash.
The v1 compiler-planning failure remains recorded. This qualifies only the
file-size/log primitives: its `mkfs_production_execution_qualified` remains
false. The separate later vendor run supplies the bounded writer evidence below.

The later **full-original-vendor v1** attempt remains failed. Fresh full export
and original structure/data/xattr checks passed, and fsck extraction completed.
The harness then required the wrong completion diagnostic for extraction and
stopped before TAR construction or mkfs image creation. No derived or signed
image resulted. V2 narrows completion checks by fsck role and passes 28 offline
tests without relabeling that failed attempt.

The actual **full-original-vendor v2** run then passed all **eight native checks,
zero skips**. Two independently assembled 1,643,234,816-byte TARs have SHA256
`e3e4f2c88b4252adc303bbe0b240f2a7a1ca8d982f51cdc897c604ce872f51ff`.
Both 941,744,128-byte raw images have SHA256
`63008bee074d0030630b502c0bf4a396c26419b825480c68b6c8a2eb7dd20d59`.
Every one of the 3,910 entries and 3,389 regular-file contents matches stock,
as do nonphysical metadata and UUID/features. Only inode IDs and the recorded
physical superblock placement fields are excluded from that comparison.

The exact unchanged-vendor recipe ran within its 2 GiB file limit, with actual
private spools observed and resource bounds retained. Disk-buffer fallback is
inferred from those spools, pinned source and limits; its 2 TiB failure errno
was not directly traced. The host capture verifies 63 direct diagnostic and
metadata files totaling 5,815,807 bytes. The four large TAR/image artifacts were
rehashed and remain only in the private guest directory. Original inputs were
preserved. This vendor-only result does not qualify the separate ODM recipe,
the five policy replacements, AVB, partition fit, kernel mounting or boot.

The later **full-original-ODM v1** run passes all **eight native checks with
zero skips** under its 6 GiB file limit. Both independently constructed raw
images are 4,678,053,888 bytes with SHA256
`6bb446e5ba6811cdd0a8c7bde994d3a42f81ce130bd0d81d31b504a9d1a60492`.
The two 6,004,780,032-byte TARs share SHA256
`c26e9a304ec6a375d511ecadca8b9f2e24f0bcc9ef6d3186531341f6655d09b3`.
All 3,059 paths and 2,925 regular-file contents, nonphysical metadata and
UUID/features match stock under the same explicit physical-layout exclusions.
Private spools were observed; internal fallback remains inferred rather than
directly tracing its 2 TiB failure errno.

The ODM host capture contains 63 direct files totaling 4,759,090 bytes. Four
large TAR/image artifacts were rehashed and retained only in the private guest
directory. These qualify the exact unchanged vendor and ODM recipes; they do
not qualify modified policy inputs, AVB, partition fit, kernel mounting or boot.
No image is adopted, and all earlier synthetic and harness failures remain
recorded as failures.

The policy-image contract requires exactly five changes: the derived vendor CIL,
the strict combined ODM policy, and its three framework matching digests.
Every other file and semantic metadata field must be preserved. The sealed
v12/export4 reconstruction below verifies that derivation. The later v13h
hashtree/FEC result and current-source qualification govern source selection;
final artifacts separately require the signed AVB chain and physical fit.
The old source-only ODM policy output must not substitute for the validated
factory-combined binary. Original proprietary images remain untouched.

The separate **policy-sidecar-native-v2** run passes all six checks and fourteen
native commands with zero skips. It derives the three platform/system_ext/product
digest files from the sealed v12f/export4 CIL and mapping inputs using the pinned
source recipe. Exact-output checks also reject reversed input order, changed
input bytes and a missing final newline. The receipt is
`54e95463bcbc02f47bcca7c27b0d2089ad3da54f67a4ac4c37557b1ca5976865`
(41,444 bytes); all 61 captured files, totaling 6,868,442 bytes, are rehashed.
Source, Android output and inputs were read-only. These are derived validation
files, not captured installed sidecars or executed Android genrules. No image
was accessed or adopted. The v1 loader-output parser failure remains recorded
as a failure. This v12 derivation does not validate the later provider policy;
the separate v13h result above supplies its own matching digest evidence.

Commit **35324b4** adds explicit `v12-export4` evidence admission with canonical
contract SHA256 `5c7e020cbf2101bc6ed5af412f1e667d41e75e3259547c0700090d2d1f10ffb4`.
The coordinator's complete unmocked replay passes policy, sidecar and original
filesystem qualification checks. It performs no TAR preparation, native
execution or image access. The historical profile remains the blocked default;
neither profile selection nor this replay establishes compatibility with the
then-active v13f inputs or admits changed-policy images.

The subsequent **policy-images-export4-v1** run executes the actual public TAR
preparation and native EROFS writer under the qualified finite limits. All nine
checks and 38 commands pass with zero skips. For each partition, both complete
TARs, raw images and metadata exports are byte-identical. The complete comparisons
verify 3,910 vendor entries and 3,059 ODM entries: only the vendor CIL, combined
ODM policy and three ODM framework digests change. Every other file content and
semantic metadata field is preserved under the recorded physical-layout exclusions.

| Derived raw partition | Bytes per image | SHA256 |
| --- | ---: | --- |
| vendor | 941,744,128 | `b74b8b92…3aa065` |
| odm | 4,678,025,216 | `9e7fc8ef…60078` |

The inner native receipt is **152,538 bytes**, SHA256
`77b40170a55f15418f75d2bbe89ff7bb99c5024600f0d5aacee23c064f3f765e`.
The complete host capture rehashes 97 files totaling 10,639,644 bytes with none
missing, including all four derived metadata exports. Large TAR/image bytes
remain in the guest; the collector neither copies nor reopens them. Their
identities come from the native run, separately from the host-captured evidence.

Independent review reparses all six complete manifests without using the subject
comparator and verifies all 97 captured files and 77 staged packet files. It confirms
the exact changes in both passes, native final artifact rechecks, 18 fsck and
four mkfs invocations, and the sandbox/source bindings, with no findings.
Its 11,234-byte receipt is
`fca05a27579a9a666e27a69db4b9a5b3f47cc7042bb4d6048539f030a86afcd4`.

This qualifies the raw five-file derivation for sealed v12/export4 inputs only.
Original images and staging, Android source/output and the phone are untouched.
No hashtree/FEC/footer is generated, no AVB signing or verification is performed,
and no partition-fit, source/image adoption, retained-kernel mount or boot result
is established. The current v13ha provider policy's matching derivation is
recorded separately below; this earlier export4 result does not substitute for it.

The later **policy-images-v13h-v1** run passes **nine checks and 38 native
commands**, including **18 fsck checks and four mkfs invocations**, with zero
skips. The actual public preparation and two independent native passes produce
identical complete TAR/image/export sets for the sealed v13h snapshot. Exactly
one vendor CIL file and four ODM policy/digest files change. Both full filesystem
exports retain every other content digest and semantic metadata field, excluding
only inode NID and five named physical superblock fields. The raw vendor image
is unchanged from export4; the ODM image changes with the v13h policy.

| Partition | Raw image bytes | SHA256 |
| --- | ---: | --- |
| vendor | 941,744,128 | `b74b8b92d121a83ffbe4ee14d9e973bb4f52ff40c0dbdea9000e112b463aa065` |
| odm | 4,678,025,216 | `6daec2017b88f4e51304db418e5e329baa55f322faca3624adffe3c4943bc84a` |

The 97-file capture totals **10,640,135 bytes** and rehashes without missing
files. Its native receipt is
`42ba98ef90aa318c0863e5f28ec53f868e1b5d97313ea563c47223b4d44163fe`
(152,438 bytes). Independent review reparses all six complete exports without
the subject comparator, verifies the staged payload and native final artifact
rechecks, and reports no findings. Its receipt is
`7d6244dc1a392a32743224527a00867a0f713eccce5b546f9731e71518cb5f69`
(10,825 bytes). This capture leaves the large native TAR/image outputs and
staging in the guest; the host review does not reopen those files or the native
original images. Source, Android output, original images and staging are
read-only for this operation. No AVB/FEC/footer, partition fit, compatibility
with the active source, provider runtime, image adoption, mount with the retained
kernel, boot or hardware result is established.

The separate **policy-footer-produce-v1** operation runs from **18:41:19 to
18:49:27 UTC** and passes **six native checks and sixteen commands, zero skips**.
Two complete vendor/ODM leaf derivations are byte-identical. Each preserves its
raw EROFS prefix, verifies the hashtree, compares the complete FEC payload with
independent native regeneration, and fits its exact original package budget.
Original vendor/ODM inputs, bound tools and controls remain unchanged. The leaf
algorithm is `NONE`; the intended signed parent chain is not yet verified.

| Partition | Footer image bytes | SHA256 |
| --- | ---: | --- |
| vendor | 959,709,184 | `ce11f1c6dfc87c29ade267e53d968426cb1e4fa7ce7decca9b1ee85dcb5c7a43` |
| odm | 4,767,621,120 | `854c0047709496136557fbdaf2f3ee0a124fa6a18c1bfaddd063d2a3d006d257` |

The 256,866-byte native receipt is
`025b8524e0c6b843cf63790c2ba2bee14d8deb4641f8dbd8840bfd07f0c70e5e`.
All **110 captured files / 939,530 bytes** rehash; the large image and FEC
outputs remain in the guest and are not reopened by this host evidence review.
Independent review has no findings; its 28,422-byte receipt is
`a17f0ba3c6992650ce44f617da476682a79904a96663308f4c2e17960d8be664`.
This proves keyless leaf derivation and exact package-budget fit, not physical
partition fit, rollback compatibility,
a signed parent chain, current-source compatibility, image adoption or boot.
No private key or phone is accessed; working76 remains unchanged.

## Next build sequence

The **matrix-v1** installation commits at **2026-08-31 03:14:25 UTC** through
one atomic device-tree exchange. Its five-event journal ends in
`commit_verified`; installation receipt
`37871f4a0879aa0a0fc69eb9f3ab60b3f6aca74c0c25ecb22fb27c62579037ee`
and journal
`62480298bcacf9d6e031af1a848ad484bb2f854d9425cce4fec9b927625d5b43`
bind the transaction. The source guard count grows from 219 to 220: the
original 204 inputs, fifteen read-only producer preconditions and the new
matrix XML. Thirteen policy/eleven runtime outputs and the 4 KiB product remain
unchanged; 238 rollback copies and 26 stamps are preserved. This installs
source only. The subsequent native **matrix-v1-1** command finishes at
**03:51:10 UTC**, with 128 Ninja actions after 163 frontend steps and exit 0;
291 progress rows are not 291 native actions. The wrapper exits 1 with
`matrix HAL contains non-exact declaration syntax`; original result
`f83b2e8706d947e86b30d2a4a31a0d823d96fb6d2d7e84efb891c4349759f962`
remains a failed wrapper record. Its parser incorrectly requires an explicit
version child even when pinned libvintf uses the canonical AIDL default of 1.
The installed/generated matrix preserves all 155 tuples across 130 HAL nodes;
103 HAL nodes omit the default version, covering 122 version-1 tuples.
The reviewed correction only accepts that omission and retains rejection of
empty, zero, range or duplicate explicit versions. It does not edit generated
XML, remove checks or rewrite the failed receipt. The distinct read-only
**matrix-postcheck-v2** runs from **04:29:59 to 04:32:59 UTC (August 31 in New
York)** and exits zero with empty stderr. Receipt
`7ab3bf7d5b7de50f89a030284f43ad54175515335aa0890c4019f969a519a071`
verifies the exact source selector and normal Ninja input, all 155 tuples,
220 source inputs, thirteen policy/eleven runtime outputs, three allocator
outputs, four tools and five targets. It executes no build commands and makes
no source/output changes. Independent paired review
`ee86f6ce55f4d22f7f15c17ed885b07953dfc04f04db6e5c23d5409923891a0f`
verifies both receipts and the action counts, without rerunning the build. It
preserves one explicit no-level matrix-definition skip as a skip and reuses
the existing strict policy analysis through exact thirteen-file equality.
The original failed wrapper receipt is unchanged. Provider installation,
producer qualification and the complete VINTF retry remain separate.

Three provider-install preflights stop in the evidence reader, while their
native read-only queries all return zero. The preserved capture identities are:

| Attempt | Capture SHA256 | Bytes | Native queries | Reader failure |
| --- | --- | ---: | ---: | --- |
| v1 | `0f1070455754f9959b545ec98b535feb4c206d8798efab12c8722c47fdf34a60` | 943,319 | 2 | Exact duplicate aggregate dependency |
| v2 | `e201ed83b9b4d5f19b53099d543071e710aa40ec50b08a8aed6d45707b3232ff` | 1,074,981 | 3 | Companion install not reached by alias-only traversal |
| v3 | `1ed962fb8148d283f877f4dbcb2b7f794131b84f8e62cf2cd1fa84d9911fd8e8` | 1,469,623 | 4 | Two manifest producers do not have a single explicit input |

Pinned `base_rules.mk` adds the primary installed destination twice for each
of exactly 27 phony aggregates, directly and through `LOCAL_SOONG_INSTALL_PAIRS`.
The corrected reader preserves that raw multiplicity and rejects other duplicate
edges. Bounded traversal then follows each owner's selected installed nodes,
including order-only links to companion init/manifest files, without expanding
unrelated dependency branches. The two selected manifest producers use the
verified XML and pinned `assemble_vintf` tool; their source and assembled-output
identities are separate roles. The other 29 installs require ordinary copies.

Two subsequent diagnostics pass one read-only query each: the two-XML capture
is `1530f0f4bdd33ffca07ccb6b59379eca7bd51edc1104aee4bb5e69458bd0eb75`
(903,504 bytes), and the complete 31-leaf recipe capture is
`be2f0104ee514d11b30018b3c3eb57fb10c57ce2b2422b9832a0987017abd660`
(934,078 bytes). The latter records exactly 29 copy and two assembly recipes,
with two XML outputs already present and the other 29 install outputs absent.
Exact command matching does not admit generic shell unwrapping. Source, graph,
log and selected-output guards remain unchanged; no installation or fresh ELF
check occurs in these diagnostics. The full corrected v4 preflight, with freeze
`97d8ec7ea34fc65af413ec4f7cd503581661bb9b6e0646ce90202ede2d6a8659`
(39,740 bytes), now passes all nine read-only queries. Its 13,911,611-byte
capture is `5c6e97461da3fe0e4a473df3ec9b8dbcafd155b09bae2e57575e10998736947d`.
It binds all 27 ordinary goals through 80 phony nodes to 31 selected installs,
their 26 enabled ELF checks and 71 shared dependencies. Native query stderr is
empty, streams are complete, and source/output, graph/log and strict settings
guards pass. This is complete graph capture, without a build, fresh checker
execution or newly installed outputs. Independent host admission now passes,
reconstructing all nine queries and rehashing 126 bound host inputs. Its review
is `3f03537e78bc2fbb7d318e7f1a600cc9ffec57b4431a65a2e96d1884b2ad02e2`
(39,277 bytes). A separate host-only three-field mapping correction preserves
the rejected legacy-field attempt and the original matrix build/postcheck pair;
it does not require new native queries. The ordinary 27-goal build uses freeze
`6bd87cbc83259fedda0782d4531565b1ae5540f60d29cd8a1a38369af2efd64b`
(87,626 bytes). All earlier failure records remain unchanged.

The normal **provider-install-matrix-v1-1** command runs from **06:09:56 to
06:10:10 UTC on August 31**, returning zero. Its 1,428,675-byte result is
`02e81e88a850dc4b5e65598df29a537eca3bbdae59caadc0e35fff8fbc7c12c8`.
It reports 29 fresh copy installs and two preserved assembled manifest files,
verifying all 31 selected destinations. The existing 26 strict ELF passes are
reused by exact effective-input, dependency, tool and flag equality: there are
**zero fresh strict checker actions and zero failed checks**. No old stamp is
deleted or invalidated. All six postcheck groups complete without errors or
remaining build processes. Source, policy/runtime, protected XML/APEX, producer
graphs and tools remain unchanged; ordinary output writes and the added Ninja
log rows are expected build effects. Independent replay now verifies all **164
contiguous Ninja actions**, with no failed lines, and all 31 install/26 reused
checker outcomes. The complete seven-file capture contains **95,812,419 bytes**;
its 3,484-byte manifest is
`466d9e5ac9b570a3bd50e838fda89435f7b034279232f0d82faa0eb6873085d7`.
The 312,192-byte independent review is
`c6f295345c8a72486ef711411b2627349282b40905ec39d515860988bcf98923`.
It rehashes the seven raw files, 186 host inputs, fourteen historical files and
seven prior 4 KiB files. Other source/graph/tool/dependency identities remain
bound to the actual guarded native receipt, not a separate host reopening of
every native input. The 220 source inputs, thirteen policy/eleven runtime files,
22 XML files, 39 APEX packages and 152 read-only guards retain their documented
preservation scope. This is an installed-provider component result, without full
ABI, service registration, image file-mode verification, full VINTF or boot evidence.

Commit **78376c7** adds the explicit `v13h-policy-only` preparation profile with
canonical SHA256
`39192f9272a222e4ca62caa501688e135ef227f1a2afe9e9a9a7c87dffdc53f0`.
It binds the verified native policy and sidecar records and is eligible for
evidence validation; both older profiles and the blocked default remain
unchanged. Matching raw reconstruction and keyless footer/FEC checks now pass;
reversible source-input integration may select the exact verified `NONE` leaf
images after current-source qualification, with AVB still enabled. Final
flashable-artifact admission separately requires the complete signed parent
chain, rollback settings and physical partition fit. This stage distinction
neither adopts the current host candidates nor changes readiness flags.
The earlier raw v12/export4 reconstruction remains a separate baseline.
Use the completed 4 KiB component result and its verified generated settings
for the next provider and compatibility checks. Preserve the earlier allocator
producer capture and unfinished 16 KiB full packet as
historical evidence. The four selected whole-bytecode comparisons now pass;
the fresh 4 KiB input capture verifies the producer prerequisites and complete
selected XML/APEX closure. Preserve the pre-matrix exit-65 failure separately
from the successful matrix-v1 retry. Use the verified matrix outputs, reviewed
provider installation and current producer/input captures with their scoped
independent reviews; address the documented coverage limits before making a complete
compatibility claim.
The partial all-target alias and its skipped matrix-definition subcheck cannot
establish full compatibility.
The separate 26-provider ELF/symbol checks now pass for the installed 4 KiB
baseline with checks enabled and no ignore flags. Preserve the original 16 KiB
failures and the remaining VTS compatibility gap. The bounded Camera
component producer/output review passes; runtime API and linker access, Camera
APK admission and full checker-input
coverage remain separate. Complete strict provider runtime checks and the normal
system, system_ext and product image dependencies. Full VINTF must include the
actual framework and vendor APEX manifests, explicit kernel requirements and
the original shipping-API evidence; full Treble labeling requires real APK
inventories.

The reviewed packaging-matrix source selection is now committed. Build and verify
the three ordinary policy-sidecar modules and retain the unchanged final policy
and installation hook; neither isolated digest recipes nor an absent sidecar is
a substitute. Then complete ordinary target-files,
super, A/B/snapshot/OTA packaging and the signed AVB chain. Construction and
flash readiness remain false throughout this checkpoint. Source-lock, runtime
integration, private-input derivation and future platform features stay
separate so the working Evolution baseline can become a maintainable OS fork.
An eventual first boot remains a separate, explicitly authorized phone action.

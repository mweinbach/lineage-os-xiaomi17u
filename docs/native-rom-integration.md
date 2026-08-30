# Native ROM integration after v11b

The independent **analysis-v12f-export4-v1** native verification passed at
**2026-08-30 02:13:44 UTC**, retaining all 6,366 original assertions, exact
reviewed property effects and zero permissive domains in three binaries.
Source/M4, API mapping, compiler, OEM guard and nine fresh check bindings pass.
This is the latest verified v12f policy baseline. The later v13f provider inputs
are installed, but their first 31-goal policy build failed before policy
compilation; policy-image adoption remains separate. The Camera/mi_ext/recovery
phase and bounded producer review pass, with all eleven installed base payloads
inspected. Runtime API closure, Camera APK integration and a complete signed
boot chain remain unverified.

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
| [Sigma/QCC source admission](framework-provider-source-admission.md) | v13 candidate and repeat are byte-identical; the later v13f transaction installs the exact device, policy and provider inputs with the scoped mdnssd visibility patch | Complete current policy build and independent analysis, strict native runtime ELF/linker checks, full labeling and service validation |
| [Target-files metadata](target-files-metadata.md) | Original-image bundle contains all 205 required property, VINTF and complete APEX files; host verification binds nine composed source files through patches 0005–0009; source admission and 43 isolated native Kati cases pass | Guest installation and ordinary target-files checks; a new complete preservation contract for policy-bearing vendor/ODM derivatives |
| [Host AVB signing](avb-signing.md) | Inert planning, offline workflow tests and real unsigned countrycode/pvmfw descriptor-carrier checks; original inputs preserved | All 15 final input images with correct hashtrees/FEC, explicit Mac signing and independent verification of the resulting 17 image roles |
| [Original ODM shipping API](vintf-shipping-api.md) | Patch 0011 and 59 source-bound host cases forward the original ODM API 36 with strict conflict and malformed-input rejection | Explicit composition extension, guest installation and complete native VINTF checks; no property bytes are fabricated |
| [Earlier Camera APK admission](camera-apk-inputs.md) | Fresh unchanged-signature, ZIP CRC and strict library-name checks; two real validator failures remain reproduced for the Xiaomi.eu/live input | This input stays unselected; its code findings do not transfer to the distinct factory DEX payloads |
| [Original factory Camera APK](factory-camera-apk.md) | Commit `d3316b4` records unchanged original input passing strict privileged/preprocessed packaging and exact uses-library checks | Ten always-privileged requests, eleven across feature branches, still require grant review, effective SELinux labeling and actual APK build; neither APK is selected or hardware-tested |
| [Factory Camera build-only packet](camera-apk-build-admission.md) | Commit `117261c` adds a separate exact namespace packet; 13 repeated files match and the host content-verifying producer passes | Explicit guest source admission and a verified graph limited to intermediate outputs; no product selection, permission/MAC admission or real APK build |
| [Combined packaging sources](target-files-source-composition.md) | Commit `1a4bd58` joins patches 0005–0011 with ten complete source identities and fresh metadata/recovery/mi_ext admission, preserving the older contracts | Guest installation, complete native configuration and ordinary packaging; no policy-bearing factory image is admitted by this host composition |
| [Policy-image input preparation](policy-image-inputs.md) | Commit `35324b4` adds explicit v12/export4 record admission, verified by the coordinator's complete unmocked replay; historical default remains blocked | Actual changed-policy TAR preparation, writer execution, AVB and image adoption; the v12 profile does not admit current v13f inputs |
| [Pinned build metadata](pinned-build-metadata.md) | Commit `ec21a87` adds an explicit UTC epoch capability; `d3c29a5` records 33 expected native Kati outcomes on isolated source copies | Guest admission, actual product configuration and output inspection; not enabled in this build or proof of reproducible images |

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
unchanged. Active inputs are now v13f, but export4's verified policy baseline
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
blindly rewriting the V2 dependency to V4. V13f remains installed, but
v12f/export4 is still the latest verified policy baseline.

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
proposed Miracast dependency correction is not yet admitted or installed.

The current Soong configuration snapshot selects `DeviceMaxPageSizeSupported`
as `16384` and `DeviceCheckPrebuiltMaxPageSize=true`, while static inspection
finds 22 of the 26 provider ELFs use 4 KiB load alignment; the other four use
16 KiB. The snapshot was collected during the component build. The optional
[4 KiB experiment](nezha-page-size.md), commit `84d63c2`, and its host v13g
candidate are on hold and unadopted. Lowering the checker threshold does not
resolve the pinned 16 KiB/VSR requirement. The failed v13f policy build retained `16384`
with checking enabled; this experiment is not approved as the next integration.

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

The latest coordinator `python3 -m unittest discover -s tests -v` run passed
**3,591 tests in 152.682 seconds with zero failures, errors or skips**, covering
the policy-image profile committed as `35324b4`. The prior coordinator component
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

Image adoption still needs an exact five-file change: the derived vendor CIL,
the strict combined ODM policy, and its three framework matching digests.
Every other file and metadata field must be proved unchanged. Native metadata
export, deterministic writer qualification, whole-filesystem comparison,
hashtree/FEC regeneration, AVB and partition-fit checks precede adoption.
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
as a failure, and current provider-policy validation is still required before
adopting a policy-bearing image.

Commit **35324b4** adds explicit `v12-export4` evidence admission with canonical
contract SHA256 `5c7e020cbf2101bc6ed5af412f1e667d41e75e3259547c0700090d2d1f10ffb4`.
The coordinator's complete unmocked replay passes policy, sidecar and original
filesystem qualification checks. It performs no TAR preparation, native
execution or image access. The historical profile remains the blocked default;
neither profile selection nor this replay establishes compatibility with the
active v13f inputs or admits changed-policy images.

## Next build sequence

Resolve the Audio AIDL source/ABI conflict, then rerun the v13f policy build and
verify the provider delta against v12f/export4 before policy-image derivation.
Keep the 4 KiB experiment held and resolve the 16 KiB compatibility requirement
without lowering checks. The bounded Camera component producer/output review
passes; runtime API and linker access, Camera APK admission and full checker-input
coverage remain separate. Complete strict provider runtime checks and the normal
system, system_ext and product image dependencies. Full VINTF must include the
actual framework and vendor APEX manifests, explicit kernel requirements and
the original shipping-API evidence; full Treble labeling requires real APK
inventories.

After metadata-preserving policy-image adoption, complete ordinary target-files,
super, A/B/snapshot/OTA packaging and the signed AVB chain. Construction and
flash readiness remain false throughout this checkpoint. Source-lock, runtime
integration, private-input derivation and future platform features stay
separate so the working Evolution baseline can become a maintainable OS fork.
An eventual first boot remains a separate, explicitly authorized phone action.

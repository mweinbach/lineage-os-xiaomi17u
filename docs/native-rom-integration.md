# Native ROM integration after v11b

The **actual v12f policy and corrected EROFS exporter build passed** on
August 29, 2026, at **23:40:31 UTC**. Source/combined policy compilation, the OEM
guard and all nine factory context and structural checks ran successfully.
Independent v12f verification failed before semantic analysis because two
installed system_ext CIL/mapping outputs were stale;
[v11b](oem-policy-integration.md) remains the latest completed independent
comparison, retaining all 6,366 assertions and zero permissive domains in
three binaries.

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
property memberships. These are intended semantic changes, not a native v12
analysis result. A successful rebuild must independently verify this budget,
the logging effect, source/M4 mappings, all assertions and enforcing binaries.
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
targets ran. An expanded normal 25-target build is being prepared, with 11
previous check outputs preserved before forcing fresh execution. No hand-edited
or manually copied generated CIL substitutes for the graph. Until that build
and a new independent analysis pass, no v12 assertion count, concrete permission
delta, dontaudit effect or three-binary permissive result is claimed. The failed
analysis and its captured commands remain preserved.

## Preparation that is not installed in v12fa

| Slice | Verified host result | Still required |
| --- | --- | --- |
| [Sigma/QCC source admission](framework-provider-source-admission.md) | v13 candidate and repeat are byte-identical; 31 proprietary payloads, 27 installable modules, private enforcing policy and verified producer outputs are bound to the composed policy bundle | Reviewed guest transaction, strict native ELF/linker and policy checks, full labeling and runtime service validation |
| [Target-files metadata](target-files-metadata.md) | Original-image bundle contains all 205 required property, VINTF and complete APEX files; host verification binds nine composed source files through patches 0005–0009; source admission and 43 isolated native Kati cases pass | Guest installation and ordinary target-files checks; a new complete preservation contract for policy-bearing vendor/ODM derivatives |
| [Host AVB signing](avb-signing.md) | Inert planning, offline workflow tests and real unsigned countrycode/pvmfw descriptor-carrier checks; original inputs preserved | All 15 final input images with correct hashtrees/FEC, explicit Mac signing and independent verification of the resulting 17 image roles |
| [Original ODM shipping API](vintf-shipping-api.md) | Patch 0011 and 59 source-bound host cases forward the original ODM API 36 with strict conflict and malformed-input rejection | Explicit composition extension, guest installation and complete native VINTF checks; no property bytes are fabricated |
| [Camera APK admission](camera-apk-inputs.md) | Fresh unchanged-signature, ZIP CRC and strict library-name checks; two real validator failures remain reproduced | Resolve original-signature/preprocessed privileged DEX packaging and separate privilege questions before selecting the APK; no APK or hardware validation is claimed |
| [Combined packaging sources](target-files-source-composition.md) | Commit `1a4bd58` joins patches 0005–0011 with ten complete source identities and fresh metadata/recovery/mi_ext admission, preserving the older contracts | Guest installation, complete native configuration and ordinary packaging; no policy-bearing factory image is admitted by this host composition |

The metadata projection is content-only packaging input. It is not a full
filesystem inventory, an APK inventory or proof that a rebuilt partition
preserves ownership, labels, capabilities and timestamps. It intentionally
rejects future policy-bearing image hashes until their complete derivation is
reviewed. The signing workflow has not read a private key or signed a ROM.
It preserves the existing recovery image and never authorizes relocking.

The metadata Kati probe completed at **22:39:19 UTC** with 14 positive and 29
specific negative cases, source and Android outputs unchanged. It parses the
exact hash-bound patch-0009 guard and checks the positive dependency closure;
it does not execute Ninja, the metadata verifier or the target-files recipe.
The metadata source-admission changes are committed as `9c528cf`; they are
not included in the frozen v12e installation.

The coordinator reran `python3 -m unittest discover -s tests -v`: **3,363 tests
passed in 177.286 seconds with no skips**, following the earlier 3,303- and 3,336-test
checkpoint. This is a workspace-tooling checkpoint,
not an Android build result or a phone test. Later source changes require their
own rerun. Earlier failing runs remain preserved rather than counted as passes.

The later combined-source change passed a coordinator run of **441 focused
tests in 19.955 seconds** and a separate agent-run full suite of **3,452 tests**,
both with zero skips. That later full run is not relabeled as the coordinator's
earlier 3,363-test checkpoint.

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
and the stock receipts report no hardlink groups. A complete writer round trip
of the factory images is still unverified. The existing bounds
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

Image adoption still needs an exact five-file change: the derived vendor CIL,
the strict combined ODM policy, and its three framework matching digests.
Every other file and metadata field must be proved unchanged. Native metadata
export, deterministic writer qualification, whole-filesystem comparison,
hashtree/FEC regeneration, AVB and partition-fit checks precede adoption.
The old source-only ODM policy output must not substitute for the validated
factory-combined binary. Original proprietary images remain untouched.

## Next build sequence

Build the complete ordinary policy-output target set, then repeat independent
v12f semantic analysis with consistent runtime exports and real compiler inputs.
Build and inspect the current Camera runtime modules, mi_ext and exact working76
recovery targets. Admit the provider inputs separately and complete the normal
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

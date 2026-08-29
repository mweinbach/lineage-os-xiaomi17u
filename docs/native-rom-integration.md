# Native ROM integration after v11b

The **v12e source and private-input installation passed** on August 29, 2026.
Its **first actual Android policy build failed during Kati configuration** at
22:19:27 UTC, before any requested policy compiler or context-check action ran.
The immediate blocker is the read of undefined `BOARD_MI_EXT_IMAGE_NO_FLASHALL`
at `build/make/core/Makefile:4776`. The last successful policy checkpoint remains
[v11b](oem-policy-integration.md), with all 6,366 assertions retained and zero
permissive domains in three independently analyzed policy binaries.

The [machine-readable record](../research/native-rom-integration.json) binds
each claim below to private receipts and hashes. No complete ROM, framework
image set, target-files, super image, OTA or first Evolution boot is established.
No phone was accessed during this integration.

## Installed inputs

The transaction uses a frozen public control snapshot from workspace commit
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
analysis, Camera runtime build, mi_ext target or recovery target is claimed.

Earlier `run-v12` through `run-v12d` stage failures remain in their original
ignored directories. They exposed snapshot ordering, case-probe, unified-patch
parsing and Kati-fixture mistakes before active installation. The separately
preserved recovery Kati v3 probe passed all 12 cases before the v12e transaction.
None of those narrower results erases the full-build failure above.

## Preparation that is not installed in v12e

| Slice | Verified host result | Still required |
| --- | --- | --- |
| [Sigma/QCC source admission](framework-provider-source-admission.md) | v13 candidate and repeat are byte-identical; 31 proprietary payloads, 27 installable modules, private enforcing policy and verified producer outputs are bound to the composed policy bundle | Reviewed guest transaction, strict native ELF/linker and policy checks, full labeling and runtime service validation |
| [Target-files metadata](target-files-metadata.md) | Original-image bundle contains all 205 required property, VINTF and complete APEX files; host verification binds nine composed source files through patches 0005–0009; source admission and 43 isolated native Kati cases pass | Guest installation and ordinary target-files checks; a new complete preservation contract for policy-bearing vendor/ODM derivatives |
| [Host AVB signing](avb-signing.md) | Inert planning, offline workflow tests and real unsigned countrycode/pvmfw descriptor-carrier checks; original inputs preserved | All 15 final input images with correct hashtrees/FEC, explicit Mac signing and independent verification of the resulting 17 image roles |

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

The coordinator reran `python3 -m unittest discover -s tests -v`: **3,303 tests
passed in 169.596 seconds with no skips**. This is a workspace-tooling checkpoint,
not an Android build result or a phone test. Later source changes require their
own rerun. Earlier failing runs remain preserved rather than counted as passes.

## EROFS qualification and image adoption

The authored [metadata exporter](../tools/erofs-metadata/README.md) built through
the actual Android graph at **21:15:53 UTC** in phase `erofs-tool-v1`, with 169
Ninja actions and verified read-only source mounts. Its binary SHA256 is
`fdb9fd26272e3552a70e08d32ea831b3b7a9afa5ef21ca5b4a53ad194d65361b`.
The pinned `external/erofs-utils` revision remains
`2c190a73fceb29f00da0558e44bb88ce19ec5bf4`.

| Native qualification | Passed | Failed | Skipped | Result |
| --- | ---: | ---: | ---: | --- |
| Synthetic v3 | 25 | 2 | 0 | Exporter checks pass; the pinned tar writer drops fractional nanoseconds and upstream fsck reports an error for an empty-xattr fixture despite exit zero |
| Read-only stock v1 | 4 | 2 | 0 | Both original filesystems pass upstream fsck; both exporter runs fail on their root shared-xattr header |

The stock failure exposed an invalid exporter assumption that a shared xattr
table cannot begin at block zero. The narrow C correction is committed as
`f3d740e3d6ce5c7509bc8601e68a9e681111efde`; it was
not part of the native binary above and needs fresh regression, stock and
round-trip qualification. The existing bounds checks must remain. The first
native fixture attempts and their resource-limit failures are retained.

Image adoption still needs an exact five-file change: the derived vendor CIL,
the strict combined ODM policy, and its three framework matching digests.
Every other file and metadata field must be proved unchanged. Native metadata
export, deterministic writer qualification, whole-filesystem comparison,
hashtree/FEC regeneration, AVB and partition-fit checks precede adoption.
The old source-only ODM policy output must not substitute for the validated
factory-combined binary. Original proprietary images remain untouched.

## Next build sequence

Correct the undefined custom-image variable through reviewed source admission,
then rerun the normal policy targets and their independent semantic analysis.
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

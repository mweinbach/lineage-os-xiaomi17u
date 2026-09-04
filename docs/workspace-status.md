# Current Nezha workspace status

The selected target is **Evolution X Android 16 QPR2 `bka` for Xiaomi 17 Ultra
(`nezha`, SM8850 / `canoe`)**, with **TWRP `working76` as the default recovery**.
The ROM remains a `framework-checks` product, not a complete or flashable ROM.
The recovery has a separate successful device test using the installed stock
companion boot, kernel and vendor stack; it does not establish that it works
with newly built Evolution components or that Evolution X boots. This page
consolidates recorded evidence through **September 4, 2026 UTC (September 1–4 in
New York)**. UTC milestones before 04:00 occur on the preceding New York date.
This page does not assert that a historical builder VM is still running.

**Flash-readiness work has identified two APK integration defects in Package6:**
FamilySpace lacks two required product privileged-permission declarations, and
TurboAdapter fails four-byte ZIP alignment because SignApk inherits timestamp
metadata. Do not flash Package6 while their source/image fixes are pending.
Both source corrections are now installed and independently verified as a
549-file source state, build identity `nezha.128c96ed5e626cdd0d213542`. The
original Java/XML files and Package6 artifacts are preserved. Configuration
queries and the ordinary SignApk/TurboAdapter build have completed. The new APK
passes strict signatures, unchanged-payload checks and 4 KiB alignment. A
source-inventory postcheck correction now passes separately, preserving the
original failed receipt. The ordinary recovery/vendor/ODM/mi_ext and policy-
hash rebuild passes, including all seven fresh producer checks. The GMS app
stage also passes native checks and independent replay, distinguishing two
fresh APK actions from verified reuse. Selected-app checks now also pass;
platform images and the successor package are still pending.
The first selected-app attempt stopped before Android invocation because its
staging map omitted six capture-proof aliases. Those original files are now
staged and hash-verified; the failed attempt and all build outputs are preserved.
The separate Selected6 retry now passes the complete native profile and
postchecks: 35 ordinary Ninja actions, 26 fresh required outputs including eight
strict statuses, ten live verification passes, and all 52 retained copies and
originals. All six source callback maps match. Its 193 retained evidence files
are exported and hash-verified. Independent semantic replay of the complete
300-file proof also passes, including all 36 artifact commands and the separate
historical Flex check.
Final platform images and the successor package still need building.

**First-stage init reproduction now passes:** 13 direct compilations plus link,
strip and install reproduce all 16 outputs exactly, with retained originals.
All 455 APKs pass signature verification for API 36 and all 39 APEX payloads
pass their AVB/key checks; the distinct alignment and permission failures remain
blocking. No phone operation has occurred. See [experimental first-boot
readiness](flash-readiness.md) for the precise completed checks, A-only Super
risk, data/device gates and current feature limits.

Fresh vendor/ODM extraction also verifies all **19 additional APKs** for
signatures, manifests and 4 KiB alignment, with the Adreno host-provider
exception recorded separately. Known OEM permission feature gaps remain; no
OEM signer or grant was changed. A bounded read-only device preflight tool is
prepared but has not contacted a phone. The current complete offline suite
passes **4,602 tests, zero skips**.
The original China OS3.0.309.0.WPACNXM Android return set and separate working76
rescue are also freshly hash-verified. Stock return requires the original
recovery/AVB pairing; current-device fit and userdata recovery remain unproven.

## Earlier Package6 static checks

This checkpoint precedes the first-stage reproduction and comprehensive APK audit above.

**The three original VINTF checker commands now pass**, with native and
supervisor exits 0/0; full framework/vendor/kernel/APEX stdout ends `COMPATIBLE`.
All six source callbacks, 548 selected source files, 1,179 locked HEADs/origins,
and the 39-APEX input set remain unchanged. Independent host review passes.
The framework-only mode retains **two definition-check skips and two warnings**;
these are not passed subchecks or proof of runtime service compatibility.
See [the exact original-checker scope](package6-static-validation.md#original-vintf-checker-results).

**Fresh signed Package6 boot-content checks pass**: five images, 16 published
archive members, the exact 4 KiB kernel, eight Canoe DTBs, working76 recovery,
430 ramdisk modules, and the selected factory fstab/bootconfig values agree.
Seven alternative GSI key paths remain absent; the pinned source has a
conditional ordinary-AVB fallback and the matching parent descriptors are
present. This does not prove bootloader acceptance or key closure. The complete
workspace suite passes **4,512 tests with zero skips**. No source, image or phone
was changed. See [current static validation](package6-static-validation.md).

The pinned checker does not impose a universal provider-presence requirement
on the combined matrix. Preserve the separate proprietary metadata and
runtime checks. First-stage reproduction, APK/APEX/OTA signing and
update behavior, device trust/fit and actual boot remain open; complete-ROM and
flash readiness stay false.

## Earlier Package6 diagnostic outcome

**The experimental diagnostic executes with captured zero results**, and its
trace-structure review passes after authenticated readback. **All 155 retained
AIDL tuples match effective-manifest declarations**; this is not proof of live
services or all combined-matrix requirements. The generated-metadata 127-name
gap persists, not a finding of 127 missing providers. **All 38 compile/archive/link
observer-body replays pass**, and the separate runtime observer/raw-trace readback
also closes.
Super static fit and prior boot-candidate comparisons remain recorded; functional
Super, original-checker/ODR/runtime equivalence, full VINTF, flash safety,
policy/trust/ABI, OTA and boot are unqualified. No phone operation or additional
cleanup occurs. See the [diagnostic-outcome checkpoint](build-progress.md#package6-diagnostic-outcome-and-observer-readback--2026-09-04).

## Earlier Package6 sparse Super and published boot candidates

The following checkpoint predates diagnostic execution and compile/link observer-body readback.

**A sparse Super image is assembled and statically validated**: full LP
metadata, all eight embedded-image hashes and logical/group/physical fit pass.
**Published boot-candidate comparison
passes**, without qualifying the historical build branch, complete constructor,
source or runtime. The Super run closes September 3 UTC; the boot capture closes
September 4 UTC, both on September 3 in New York. **The diagnostic tool is compiled
and linked**, but remains an unqualified link-only experiment: execution, ODR and
runtime remain open. Functional Super, flash safety, policy/trust/ABI, full VINTF, OTA and
boot remain open; no phone operation or additional cleanup occurs. See the [Super and boot-candidate checkpoint](build-progress.md#package6-sparse-super-and-published-boot-candidates--2026-09-04).

## Earlier Package6 source endpoint and diagnostic dependency failure

The following checkpoint predates Super assembly and published boot-candidate comparison.

**P4 observes the exact `mkbootimg.py` source endpoint**, without qualifying
the complete installed-to-source route or constructor. **The diagnostic build
attempt fails its job08 dependency gate**: the required trace header is absent
from the depfile, so successful compiler exits do not establish the intended
instrumented build. Separate source recovery preserves the original failed
flags; no archive or diagnostic run is admitted. Super assembly remains
pending, with no accepted result. Full source/runtime, policy/trust/ABI, VINTF,
super/fit, OTA and boot remain open; no phone operation or additional cleanup
occurs. See the [source-endpoint and diagnostic-failure checkpoint](build-progress.md#package6-source-endpoint-and-diagnostic-dependency-failure--2026-09-03).

## Earlier Package6 generated headers and Super help smoke

The following checkpoint predates P4 and the diagnostic dependency failure/readback.

**P3 captures both generated headers and the next packaging-query pair**;
the fixed observations are admitted, not complete header or source provenance.
**The generated Super tool's `--help` smoke test passes**, with its current
identity checked. A separate host-only correction recovers namespace-token
ordering without rerunning native execution or rewriting the original host
failure. This proves the entrypoint/help path, not broad library/runtime or
functional Super behavior. No `super.img` is assembled. Full source/runtime,
compiled policy, trust/ABI, VINTF, super/fit, OTA and boot remain open; no phone
operation or additional artifact cleanup occurs. See the [generated-header and help-smoke checkpoint](build-progress.md#package6-generated-headers-and-super-help-smoke--2026-09-03).

## Earlier Package6 producer recovery and function-anchored BTF

The following checkpoint predates P3 and the generated-tool help-smoke admission.

**P2's four producer observations and seven paired input files are admitted**,
without establishing header closure or producer/runtime qualification.
**Super producer evidence is recovered without a rebuild**: a separate review
admits four retained commands and selected source/PYC joins; the original
wrapper failure and its flags remain intact. Current artifact identity, full
composition and generated-program runtime remain unverified.
**Function-anchored BTF selects `module` type 257 and `sig_ok` at byte 377**,
supporting a conditional static gate interpretation. The global two-type
census remains ambiguous; live pointer identity, `sig_ok` value, signature
trust and whole-policy behavior are not established. Full source/runtime,
ABI, VINTF, super/fit, OTA and boot remain open. No phone operation or
additional artifact cleanup occurs. See the [producer recovery and function-anchored BTF checkpoint](build-progress.md#package6-producer-recovery-and-function-anchored-btf--2026-09-03).

## Earlier Package6 producer tools and kernel BTF

The following checkpoint predates P2 admission, producer recovery and the function-anchored declaration review.

**LN producer-listing review passes** for 33 ordered object recipes and their
response file, without proving built-archive membership or producer provenance.
**Machinery metadata is mixed-architecture**: AArch64 env/Python and x86-64
nsjail; identity matches do not qualify execution. Limited kernel static
review supports ordering sign and an on-disk guard match, but **two BTF
`module` candidates prevent a unique type/field mapping**. FIFTEEN's member
identities and metadata join without full boot-consumer qualification.
**The Super tool wrapper fails after four reported zero-exit commands**;
its outputs await recovery admission. Compiled policy, ABI/trust, tool and
boot runtime, full VINTF, super/fit, OTA and boot remain open. No phone
operation or additional artifact cleanup occurs. See the [producer-tool and BTF checkpoint](build-progress.md#package6-producer-tools-and-kernel-btf--2026-09-03).

## Earlier Package6 boot-property reviews and follow-up captures

The following checkpoint predates LN producer interpretation, machinery capture and the BTF type result.

**Scoped boot and property observation reviews pass**, without qualifying
the three boot-source proofs, packaged init provider or effective property
selection. **Two kernel search windows are captured at 21:54:18 UTC** and
limited static review passes. Actual string comparison, guard outcomes and
BTF type interpretation remain unverified.
Captured boot texts match candidate arguments; full constructor qualification remains open.
**The 68-call producer follow-up completes at 22:14:12 UTC**, with a fixed
response-file read and paired tool metadata. ROOT's validator replay passes;
deeper consumer review remains pending.
Fresh init remains unexecuted, and diagnostic instrumentation is unbuilt
and unrun. Compiled policy, ABI/trust, full boot-source/runtime, VINTF,
super/fit, OTA and boot remain open. No phone
operation or additional artifact cleanup occurs. See the [boot-property and capture checkpoint](build-progress.md#package6-boot-property-reviews-and-follow-up-captures--2026-09-03).

## Earlier Package6 protected-export gate and libvintf producer query

The following checkpoint predates the scoped boot/property reviews and search-window capture.

**A bounded kernel gate window is captured at 21:23:03 UTC**, and static
review identifies count/table arguments and a conditional local rejection
path. Callback/search behavior, object-field meaning, runtime counts, trust
and ABI remain unverified. **Six read-only libvintf producer queries complete
at 21:25:35 UTC**, without reading producer bodies or executing their recipes.
A host-only AIDL checker correction preserves the **127-name negative**;
it does not establish missing runtime services. Further query/code work is
unexecuted, and VINTF diagnostics remain unbuilt and unrun. Full boot-source/
runtime, VINTF, super/fit, OTA and boot remain open. No phone operation or
additional artifact cleanup occurs. See the [gate and producer-query checkpoint](build-progress.md#package6-protected-export-gate-and-libvintf-producer-query--2026-09-03).

## Earlier Package6 producer retry and pointed-name reference review

The following checkpoint predates the gate-window and libvintf producer-query results.

**The corrected producer retry completes at 21:02:17 UTC**, with exit 0 and
complete output; the original failed batch remains unadmitted. Original-driver,
source and PYC admission passes; deeper boot, property, super and AIDL
consumer reviews remain separate from this scoped closure.
**Pointed-name capture and reference assessment now close**, including exact
replay across all 637 current payloads. Observed marker bytes are not
cryptographic trust, and provider selection, stage order, compiled policy and
ABI remain unverified. Further query/code-window preparations are unexecuted;
VINTF diagnostics remain host-only, unbuilt and unrun. Full boot-source/runtime,
VINTF, super/fit, OTA and boot remain open. No phone operation or additional
artifact cleanup occurs. See the [retry and reference-review checkpoint](build-progress.md#package6-producer-retry-and-pointed-name-reference-review--2026-09-03).

## Earlier Package6 static kernel mapping and pointed-string capture

The following checkpoint predates the successful retry and closed pointed-name reference review.

**Conditional static kernel mapping passes independent review**, covering
9,696 RELR-backed table slots and 9,364 candidate targets. The subsequent
**pointed-string capture closes cleanly at 20:45:22 UTC**, preserving those
slots and decoded strings; its deeper semantic review remains pending.
Three libvintf source files are captured and host-published, but the diagnostic
implementation is unbuilt and unrun. The preceding native batch failed on a
repeated implicit `libc.a` edge; its corrected retry is in progress, with no
successful capture yet. Compiled policy, ABI/trust, boot-source/runtime, full
VINTF, super/fit, OTA and boot remain open. No phone operation or additional
artifact cleanup occurs. See the [static-mapping and capture checkpoint](build-progress.md#package6-static-kernel-mapping-and-pointed-string-capture--2026-09-03).

## Earlier Package6 conditional stages and kernel relocation capture

The following checkpoint predates conditional static mapping and pointed-string capture.

**Reference vermagic comparison now covers all 637 payloads / 914 instances**,
without selecting the current compiled loader branch. The conditional normal
and recovery ramdisk closures have no nonmatching expectations or findings;
nine Wi-Fi gaps in the restricted provider pool lie outside those closures.
This assumes simultaneous module availability, not verified load order or ABI.
**Kernel relocation capture returns cleanly at 20:06:38 UTC**, and independent
capture admission passes 35 tests. Pointer mapping remains pending. Trust, full boot-source and
runtime qualification, VINTF, super/fit, OTA and boot remain open. No phone
operation or additional artifact cleanup occurs. See the [stage and relocation checkpoint](build-progress.md#package6-conditional-stages-and-kernel-relocation-capture--2026-09-03).

## Earlier Package6 current module union and source-copy origin

The following checkpoint predates extended vermagic, conditional stage review and relocation capture.

**The current ramdisk/DLKM union supplies matching CRC providers for all 718
previously missing expectations**, with ROOT replay passing at **19:43:35 UTC**.
Twenty ambiguous/mixed rows remain, including two mixed-CRC rows; ABI, trust
and load order are not verified. **Source/copy-origin review also closes** for
21 boot-input copies after corrected read-only admission of the successful
child; its original outer failure is retained. Full boot-source semantics and
runtime remain open. Raw kernel protection-table words are captured but not
mapped, and AIDL coverage remains negative with its successor unqualified.
The next native batch, full VINTF, super/fit, OTA and boot remain pending. No
phone operation or additional artifact cleanup occurs. See the [module-union and source-origin checkpoint](build-progress.md#package6-current-module-union-and-source-copy-origin--2026-09-03).

## Earlier Package6 corrected captures and negative AIDL audit

The following checkpoint predates the current module union and source/copy-origin admission.

**The corrected NGB and vendor-ramdisk captures return cleanly**, while their
earlier failed attempts remain preserved. Kernel-static evidence and Mac
dependency admission also advance, without establishing ABI or runtime closure.
**The compiled-metadata AIDL audit remains negative**: 127 missing names affect
142 tuples, with 13 names matched; this does not prove absent services or runtime
failures, and interpretation/provenance remain unfinished. Current ramdisk/DLKM
ABI aggregation is still pending, with no claimed reduction of the 718 earlier
unbound CRC expectations. Source-origin work, full VINTF, super/fit, OTA and boot
remain open. No phone operation, additional artifact cleanup or push occurs.
See the [corrected-capture and AIDL checkpoint](build-progress.md#package6-corrected-captures-and-negative-aidl-audit--2026-09-03).

## Earlier Package6 independent VINTF inputs and retained ABI gaps

The following checkpoint predates the corrected captures and negative AIDL audit.

**Package6's independent VINTF input review passes on the host**, accounting
for all 298 selected members and staging the third of six proof roles as a
read-only host file. Native qualification and full VINTF compatibility remain
open. **The retained 484-module ABI analysis completes, but does not verify
ABI compatibility**: 718 CRC expectations lack current providers, and historical
ramdisk candidates are not current evidence. The original next-grounded-batch
capture stops at a capture limit with partial results; no retry result is
admitted here. Current ramdisk/vermagic/protection/trust, runtime properties,
host runtime, AIDL, super/fit, OTA and boot remain open. No cleanup or phone
operation occurs. See the [independent-input and ABI checkpoint](build-progress.md#package6-independent-vintf-inputs-and-retained-abi-gaps--2026-09-03).

## Earlier Package6 DLKM reference-model semantics and loader-text binding

The following checkpoint predates independent input review and retained ABI analysis.

**Package6's DLKM reference-model analysis and current loader-text binding pass.**
The 11 retained metadata bodies are admitted at **18:10:30 UTC**, and current
image init texts, declared import selectors and DLKM links join at **18:26:49
UTC**; ROOT's exact replays pass. Selected reference-model closures have no
missing mandatory requests or hard/pre cycles, with 15 optional pre-requests
still unresolved. A separate top-level early-init `msm_11ad_proxy` request has no
current DLKM match, without proving a boot-fatal failure or built-in absence.
These static results do not establish loader execution or source/binary
equivalence. ABI/trust, effective properties, full VINTF, super/fit, OTA and boot
remain open. No cleanup or phone operation occurs. See the [DLKM semantics and loader-text checkpoint](build-progress.md#package6-dlkm-reference-model-semantics-and-loader-text-binding--2026-09-03).

## Earlier Package6 DLKM membership and two-node semantic admission

The following checkpoint predates DLKM metadata semantics and current loader-text binding.

**Package6's two DLKM images pass exact module-membership verification**, after
successful scans at **17:54:55 UTC** and ROOT semantic replay at **18:02:37 UTC**.
All 484 modules and 11 metadata/selector files match the historical corpus by
path, hash and size; eight ordinary `/etc` files remain recorded outside that
comparison. This does not verify module ABI, signature trust, loader behavior
or boot. The separate two-node source/PYC semantic replay also passes, without
producer/runtime qualification. Five-image content projection remains verified;
runtime property behavior, full VINTF, super/fit, OTA and boot remain open.
No additional cleanup or phone operation occurs. See the [DLKM membership checkpoint](build-progress.md#package6-dlkm-membership-and-two-node-semantic-admission--2026-09-03).

## Earlier Package6 five-image VINTF content projection

The following checkpoint predates DLKM membership and two-node semantic admission.

**Package6's five-image VINTF content projection passes**, after the corrected
reader successfully captures system, system_ext and product at **17:16:09 UTC**.
The join with retained vendor/ODM evidence covers 267 relevant files and 21
property-import candidates; ROOT's exact API replay passes at **17:36:01 UTC**.
The 46 system-root entries outside the partition view and five `build.prop`
permission differences remain recorded. This does not establish runtime property
behavior, inner APEX validation or full VINTF compatibility. Two-node and super
precursor queries close, but their remaining qualifications and super/fit/OTA/boot
gates stay open. No cleanup or phone operation occurs. See the [five-image projection checkpoint](build-progress.md#package6-five-image-vintf-content-projection--2026-09-03).

## Earlier isolated EROFS reader build and query admission

The following checkpoint predates successful image capture and content projection.

**The corrected native EROFS reader builds successfully at 17:07:42 UTC**,
with 18 commands, 175 paired inputs and seven runtime files; ROOT's exact
result replay passes. Its three-image projection remains pending. Four
super-tool queries and the eight-seed semantic replay also pass, establishing
observed installation copies and producer/response-file origins, not full
producer/runtime qualification. Eight-role FEC and published-kernel evidence
remain verified; image validation, final VINTF, super/fit, OTA and boot stay open.
No cleanup or phone operation occurs. See the [reader-build checkpoint](build-progress.md#isolated-erofs-reader-build-and-query-admission--2026-09-03).

## Earlier Package6 eight-role FEC and producer queries

The following checkpoint predates the isolated reader build and later query admissions.

**FEC evidence now joins all eight final Package6 dynamic-image roles.** The
clean host-wrapper return closes at **16:43:53 UTC**, followed by independent
exact replay at **16:46:12 UTC** and ROOT admission. Six fresh semantic results
are joined with two historical vendor/ODM proofs by exact final-image identity;
those two checks are not rerun. All 14 held inputs and the published archive's
observed identity remain unchanged. This is a separate FEC aggregate, not a
rewrite of the earlier public verification report or a boot claim.

**EROFS producer-query capture passes at 16:45:35 UTC**, and its one observed
linker response file is captured at **16:51:00 UTC**. Isolated compilation and
qualification of the corrected native reader remain pending. The eight-seed
producer/PYC capture also closes successfully at
**16:40:12 UTC**, with ROOT's envelope checks passing and semantic review still
pending. Super discovery remains blocked in the query helper, with no super
build. Final VINTF, physical fit, OTA and boot remain open gates; no additional
cleanup or phone operation occurs. See the [eight-role FEC and query checkpoint](build-progress.md#package6-eight-role-fec-and-producer-queries--2026-09-03).

## Earlier Package6 six-image FEC and published kernel admission

The following checkpoint predates the complete eight-role FEC join and query captures.

**Six Package6 images pass strict FEC semantic admission**: mi_ext, product,
system, system_dlkm, system_ext and vendor_dlkm. ROOT independently reproduces
all 32 diagnostic readback admissions and the original strict semantic result,
with all 148 held input states rechecked. Native liveness is verified separately
at the **16:23:29 UTC** readback completion. Joining the separate vendor/ODM FEC
evidence remains pending.

**Published boot-chain/kernel/META binding also passes**, with the actual join
closing at **16:19:43 UTC** and ROOT's exact replay admitted. All five boot-chain
identities and the complete kernel META match the signed evidence, including
6,405 config symbols, literal 4 KiB selection and preserved `working76`.
Its unchanged `final_boot_kernel` proof is host-staged and read back; native
staging and complete six-proof qualification remain pending. Module ABI,
native EROFS-reader qualification, super/physical fit, OTA and boot remain
unverified. No additional cleanup or phone operation occurs. See the
[six-image FEC and kernel checkpoint](build-progress.md#package6-six-image-fec-and-published-kernel-admission--2026-09-03).

## Earlier Package6 discovery admission and failed-archive retirement

The following checkpoint predates six-image FEC and published-kernel admission.

**Shared discovery-v3 passes at 15:34:25 UTC**, with ROOT admission at
**15:37:18 UTC** and independent review at **15:43:26 UTC**. All six Package6
source-callback vectors match, paired graph observations are preserved, and
the exact nine-target read-only query succeeds. Dependency-edge, PYC-identity
and raw property-source joins are admitted, not producer/runtime or AIDL
qualification, compiled property selection, or VINTF compatibility.

**One obsolete failed reconciliation ZIP is retired at 15:36:46 UTC**:
**10,834,328,619 logical bytes**, with 127 held keeper files and 17 directory
identities preserved. The successful `reconciled-v2` output and small failure
diagnostics remain; the old failed archive's exact body replay is lost. The
observed **10,834,333,696-byte** host-space increase is not exclusively
attributed to this file. The cleanup is host-only. Native EROFS-reader
qualification, FEC, VINTF, super/physical fit, OTA and boot remain pending;
neither operation touches the phone. See the [discovery and retirement checkpoint](build-progress.md#package6-discovery-admission-and-failed-archive-retirement--2026-09-03).

## Earlier Package6 archive publication and reader corrections

The following checkpoint predates discovery-v3 admission and failed-ZIP retirement.

**The ZIP64 writer correction and opt-in EROFS reader are committed**, with
**4,512 offline tests passing** on the frozen changes. The ZIP64 change fixes
offset-only header-version promotion while preserving strict readback. The
EROFS successor handles an unused compact EOF marker without replacing the
canonical reader or its default selection; native qualification remains pending.

**Package6 reconciliation-v2 passes at 14:44:59 UTC.** All **9 host-tool records**
succeed, all **9,154 ZIP members** are independently read back, and the DTBO
prebuilt alias is normalized. The **17-role signed image set**, **14 unchanged
leaves** and `working76` join successfully; ROOT's exact result replay passes
at **15:25:57 UTC**. The resulting archive is `fbb6cba4…` /
**10,834,328,619 bytes**. **Published-path inventory passes at 15:32:08 UTC**;
ROOT admits all 17 role identities, matching aliases and the complete directory
without `IMAGES/system_other.img` at **15:32:55 UTC**. The archive's observed
state remains unchanged throughout inventory, metadata capture and review.

The first archive attempt and original three-image EROFS failure remain
preserved; the latter admitted no manifests. Shared VINTF discovery-v1 stopped
on an adapter graph/closure mismatch, and v2 was interrupted with no result.
The reviewed v3 successor launches at **15:24:16 UTC**, after fresh idle and
sole-owner checks, but no completed discovery result is admitted here. FEC,
VINTF compatibility, super/physical fit, OTA and boot remain open gates. No new
cleanup or phone operation is claimed. See the [archive and reader checkpoint](build-progress.md#package6-archive-and-reader-corrections--2026-09-03).

## Earlier Package6 public preparation and signing

The following checkpoint predates the archive retry and reader corrections.

**Package6 public AVB preparation and host private signing pass.** Preparation
closes at **2026-09-03 13:49:06 UTC**. All
**18 host-tool invocations and 15 input checks** succeed, including the five
rebuilt images' SHA-256 hashtree descriptors. The normalized signer manifest is
recorded, source inputs stay unchanged and `working76` is preserved. ROOT's
separate result review passes at **13:50:49 UTC**.

Signing closes at **14:03:59 UTC** with **33 successful host-tool records** and
a verified **17-role AVB image set**: 14 leaves remain unchanged, while `boot`,
`vbmeta` and `vbmeta_system` reproduce identically in two signing passes.
`working76` is preserved and the selected-key Android AVB chain passes; ROOT's
postcheck replay agrees. **Archive reconciliation is in progress, not admitted.**
Full FEC payload verification, VINTF semantic admission/compatibility, physical
fit, OTA and device boot remain unverified. No new cleanup or phone operation
is claimed. See the [preparation and signing checkpoint](build-progress.md#package6-public-avb-preparation-and-signing--2026-09-03).

## Earlier Package6 input materialization and host retirement

The following checkpoint predates successful public AVB preparation and signing.

**Package6's 15 host signing inputs are materialized and the old P5 host ZIP is
retired.** Materialization closes at **2026-09-03 03:55:41 UTC** with full output
readback and local publication checks; ROOT's separate review passes. The
13 Package6 images and two retained stock inputs are not yet publicly prepared
or signed, and DTBO archive-alias normalization remains pending.

After the host reboot, the existing builder is restored at **13:40:34 UTC**
with unchanged configuration, sole-writer ownership and strict idle checks.
VINTF's **19,117,617-byte** capture is read back at **13:41:55 UTC**, matching
the acknowledgment, native final hash and complete transfer. **Semantic
admission and compatibility execution remain pending.**
The **20 obsolete native leaves** inspected at **04:04:45 UTC** are only
metadata-probed: **none is deleted**. P5's exact historical ZIP replay is lost;
Package6 is retained, not a byte-identical replacement. No full-capacity,
FEC/AVB-chain, VINTF, super, OTA or boot readiness is claimed. Later host-space
changes are not attributed to this cleanup. No phone operation
occurs. See the [materialization and retirement checkpoint](build-progress.md#package6-input-materialization-and-p5-host-retirement--2026-09-03).

## Earlier Package6 transfer and original inventory

The following checkpoint predates host input materialization and P5 host retirement.

**Package6 is copied to the host and its original input inventory is complete.**
Transfer finishes at **2026-09-03 03:29:05 UTC**, with native final hashing and
host readback verified. Inventory closes at **03:32:45 UTC** without errors,
covering **13 data-image roles, two generated vbmeta roles and two retained
stock inputs**. The archive identity remains `e3b9aa2b…` / **11,006,603,036 bytes**.

ROOT verifies the five independent **ZIP ↔ expanded-packaging** image joins,
not equality with earlier native installed images. DTBO's **1,495,111-byte**
payload matches across its aliases, with permitted unsigned metadata differences;
**normalization is still pending**. Host image materialization, signing, FEC, VINTF, super
and boot remain unverified. No old P5 host archive had been deleted at this checkpoint, and no publication
or phone operation occurs. See the [transfer and inventory checkpoint](build-progress.md#package6-host-transfer-and-original-inventory--2026-09-03).

## Earlier Package6 build and host admission

The following checkpoint predates the host archive transfer and inventory.

**Native Package6 build, profile validation and exact host admission pass.**
The native command runs **2026-09-03 02:49:41–02:54:14 UTC**, exit **0**; the
outer executor closes at **03:01:01 UTC**, also exit **0**. Both directory and
ZIP producers are fresh, with **205 metadata records and 221 selected ZIP
members** verified. This is not verification of every archive member or a
complete, signed or bootable ROM.

A narrow host-only system-copy budget correction admits the unchanged completed
result without a native rerun. Post-build free-block trim observes a separate
**15,021,551,616-byte** host-space gain, restores the original builder and passes
the recorded preservation checks; no new files are deleted by that trim.
**Archive copy/inventory, signing, FEC, VINTF, super and device boot remain
pending.** No phone operation occurs. See the [Package6 success checkpoint](build-progress.md#package6-build-and-host-admission--2026-09-03).

## Earlier Package6 launch and P5 mirror retirement

The following checkpoint records launch only, before the completed result was admitted.

**Native Package6 launches at 2026-09-03 02:43:52 UTC.** The launch observes
**142,274,932,736 bytes available**, exceeding its **133,769,298,255-byte**
requirement while retaining the unchanged **100 GiB reserve**. This is a
**launch-only checkpoint**: no completed build, profile or archive result is
inspected or admitted, and no ROM/signing/boot success is claimed.

Before launch, exactly one obsolete **native P5 mirror ZIP** is retired. Its
host keeper, expanded target-files tree, list and other protected inputs remain.
The subsequent trim observes **11,047,260,160 bytes** more host free space,
separately from backing allocation, and restores the original builder with
unchanged configuration and passing post-restart checks. This does not establish
full continuation capacity or whole-filesystem integrity. No phone operation
occurs. See the [launch and mirror-retirement checkpoint](build-progress.md#package6-launch-after-p5-mirror-retirement--2026-09-03).

## Earlier corrected projection and bound request

The following checkpoint records preparation before cleanup and native launch.

**The Package6 wrapper and shared source-context projection are corrected.**
After **98 focused tests**, guarded host deployment and request preparation
complete at **2026-09-03 02:28:30 UTC**. The genuine request is **5,298,505 bytes**;
its fully bound bridge is **519,654 bytes**, below the unchanged **524,288-byte**
limit. Six prior preparation files and the previous host preparation remain intact.

The final request-consumer binding now passes default, publish and check-only
reproduction with identical preparation data. **Package6 has not been launched**:
no actual Package6 runtime result or archive is admitted. Storage remains a
launch gate under the unchanged **100 GiB host reserve**; full capacity is not
cleared. No subsequent ZIP retirement or trim is claimed here, and no phone
operation occurs. See the [prepared-request checkpoint](build-progress.md#package6-corrected-projection-and-bound-request--2026-09-03).

## Earlier proof staging and extraction cleanup

The caller correction was still pending in the following checkpoint.

**The two-producer capture closes successfully at 2026-09-03 01:20:12 UTC.**
The GMS two-proof stage and exact 21-record proof/control stage are now actually
completed, not merely prepared. These operations do not build Package6.

**Extraction cleanup removes 10,876 descendants and retains all three roots.**
It frees **9,294,848,000 bytes inside ext4**; subsequent trim observes a separate
**9,382,678,528-byte (8.74 GiB)** host-space gain. The original builder and
post-restart checks pass. Current target-files output/ZIP and retained inputs
remain protected; these bounded checks do not establish whole-workspace integrity.

**Package6 has not been dispatched.** Host inspection finds the caller passing
an outer postcheck wrapper instead of its verified `target_files` record to the
unchanged checker. A narrow correction and regression check are in progress.
Full storage capacity, Package6, signing and ROM/boot readiness remain unverified;
no phone operation occurs. See the [staging and cleanup checkpoint](build-progress.md#package6-proof-staging-and-extraction-cleanup--2026-09-03).

## Earlier prerequisite qualification and fresh captures

The following checkpoint records the then-pending capture, stages and cleanup.

**The exact-seven-field consumer correction is qualified.** Root tests and
genuine `_originals`, `_postcheck_recovery`, `read_plan` and full verbose replay
pass; the original failed result and full nine-field validators remain intact.
This clears the recorded stat-schema blocker, not full Package6 admission.

**Fresh GMS capture completes at 2026-09-03 01:05:36 UTC**, with independent
transport/source/graph review and a fresh host equivalence proof. Its two-proof
native staging is **prepared only**. The Selected4 request is actually staged
at **01:08:19 UTC**, without rebuilding. The separate two-producer capture
starts at **01:09:48 UTC**; its result is pending at this checkpoint.

Three obsolete extraction trees are **probed, not deleted**. Their allocation
is not reclaimed space, and retirement still needs refreshed guards and keeper
hashes. No cleanup after the two raw supers, complete capacity clearance,
Package6 build, signing or ROM/boot success is established; no phone operation
occurs. See the [qualification and captures checkpoint](build-progress.md#package6-prerequisite-qualification-and-fresh-captures--2026-09-03).

## Earlier recovery acceptance and two-super retirement

The stat-schema correction was still pending in this earlier checkpoint.

**Five's V2 native postcheck recovery passes**, exit **0**, at
**2026-09-03 00:08:48 UTC**. Its native receipt and exported copy match exactly;
the original failed result remains unchanged. This is postcheck-only recovery,
not another build or forced output invalidation. Receipt-only host validation
passes, but Package6's plan reader still needs a narrow stat-schema correction;
all shared stat values match. **Package6, final AVB/signing and ROM/boot remain
unverified**. Fresh four-log readback passes without granting graph admission.

**The two reconstructed stock-super copies are now retired**, after the exact
two-target action supersedes their earlier KEEP status. The operation observes
**23,525,974,016 bytes (21.91 GiB)** more host free space, separately from its
allocation count. Original archives, sixteen sparse inputs, LP images and small
records remain; direct raw-super inspection requires reconstruction and a fresh
historical-hash check. No phone operation occurs. See the
[recovery and super-retirement checkpoint](build-progress.md#five-recovery-execution-and-two-super-retirement--2026-09-03).

## Earlier recovery diagnostics and twelve-image cleanup

This September 2 checkpoint records V2 still running and both raw supers still
retained; the actual later outcomes are recorded above.

**Five postcheck recovery is not yet verified.** Recovery v1 fails at callable
authentication on **2026-09-02 23:37:18 UTC**, before the recovered full postbuild
guards and recovery artifact writes. All 23 held inputs and the original failed
result remain unchanged.
A compile-only Python 3.12 diagnostic finds identical hook ASTs but different
`co_code` for isolated versus full-module compilation. V2 restores full-module
compilation without weakening the shape guard or four postcheck substitutions.
Its reviewed packet and focused tests pass; **native V2 starts at 23:56:10 UTC
and is in progress**, with no result established by this checkpoint.

**Twelve old Images2–4 retained image copies are retired.** The subsequent
approved trim and post-restart review finish at **23:55:20 UTC**, restoring the
original builder and recovering an observed **18,004,549,632 host bytes (16.77
GiB)**. Bounded preservation checks pass; this is not a whole-source/output
integrity claim. Two reconstructed stock supers pass full direct reconstruction
comparison but remain **KEEP**, pending a separate exact-target retirement.
No Five admission, Package6, signing, ROM/boot success or phone operation is
established. See the [recovery and cleanup checkpoint](build-progress.md#five-recovery-diagnostics-and-further-cleanup--2026-09-02).

## Earlier Five native failure

**Five's native invocation exits 0, but its profile fails.** The ordinary Ninja
build runs **2026-09-02 22:33:40–22:36:05 UTC**; the outer command closes at
**22:40:08 UTC**, exit **1**, with `selected image build changed protected sidecars`.
All **56 held inputs**, six complete before/after callback maps and **254
configuration fields** remain unchanged. Each of the three 65-byte sidecars
retains its bytes, path, eight other stat fields and ancestor identities; only
`ctime` changes within the build window. Captured temporary-hardlink code is
consistent with that observation, not a trace of the actual syscalls.

At this earlier checkpoint, the failed result remains immutable and **recovery
is preparation only**.
No rebuild or forced invalidation has recovered the profile, and no Five image
admission, Package6, final AVB, signing or ROM success is established. No phone
operation occurs. See the [Five failure checkpoint](build-progress.md#five-native-exit-and-protected-sidecar-failure--2026-09-02).

## Earlier preparation, cleanup and Images6 checkpoints

**Eight obsolete vendor/ODM image files are retired.** The host-only operation
completes at **2026-09-02 22:14:08 UTC**, recovering an observed **22,577,491,968
bytes (21.03 GiB)** and leaving **181,437,829,120 bytes (168.98 GiB)** available.
Only eight leaves from four historical bundles were removed; their manifests
and directories remain, but the four manifests are incomplete until restoration.
Six keeper images, stock/current runtime inputs, source/output, working76 and
super images remain outside the deletion set.

The **five-image read-only queries and proof staging pass**, including both
query streams, 13 retained originals and 115 unchanged staging inputs. Narrow
host-reader and exact empty-graph corrections pass 25 focused tests; at that
earlier checkpoint final independent preparation review is pending. **Five native rebuild not yet
verified**; Package6, signing and boot gates remain open. No phone operation
occurs. See the [retirement and preparation checkpoint](build-progress.md#vendorodm-retirement-and-five-image-preparation--2026-09-02).

**Images6 native build and complete source/action/retention review pass.**
Native execution runs
**2026-09-02 21:06:06–21:08:58 UTC**, exit **0**; the root dispatch closes at
**21:13:01 UTC**, also exit **0**. Seven fresh installed producers cover
**vendor, ODM, mi_ext and working76 recovery**, plus three policy SHA sidecars.
The current image identities match their selected inputs; recovery remains
`a130ba75…`. All six complete source/input callback maps match before/after
and the successful Nothing11 result, covering **548 files/fifteen projects**.

The read-only supplement passes at **21:23:51 UTC**: complete before/after Ninja
logs reproduce all seven action objects, all four retained original images are
hashed after the build, and nine sidecars pass their recorded checks. Host replay
verifies all four compact retention records without exporting large image or
Ninja-log bodies. The six metadata bodies also replay exactly; the image metadata hook,
runtime and signed parent chain remain unverified. At this earlier Images6
checkpoint, the five-image read-only capture starts at **21:31:09 UTC** with its
result then pending; its later verified query/staging is recorded above. Five-image SHA-256,
Package6, signing, super and boot gates remain open. No phone operation occurs.
See the [Images6 checkpoint](build-progress.md#images6-verified-build-result--2026-09-02).

## Earlier cleanup and Selected4 checkpoints

**Further host scratch and Package5 duplicates are retired.** At
**2026-09-02 20:31:31 UTC**, six scratch files and 15 duplicate P5 image bodies
have been removed. Their operation-local host-free increases total **10.08
GiB**, leaving **165,457,305,600 bytes (154.09 GiB)** available at that checkpoint.
The old P5 ZIP, two original stock inputs, small records and directories remain.
**The old P5 input manifest is now historical and incomplete**: reuse requires
restoring all image bodies and fresh validation, not an automatic fallback or
substitution with Package6. The subsequent Images6 read-only capture closes
successfully at **20:31:59 UTC**; recovery-specific proof and the actual image
rebuild remain separate, with no phone operation. See the
[host-retirement checkpoint](build-progress.md#host-scratch-and-package5-duplicate-retirement--2026-09-02).

**Second old-output cleanup completes with the original builder restored.** At
**2026-09-02 20:14:46 UTC**, post-restart checks pass after removing **169,727
descendant entries** from two reviewed historical intermediate directories;
both empty roots remain. Deletion recovers **16,106,471,424 bytes inside ext4**.
The separately approved trim increases host availability by **16,114,458,624
bytes (15.01 GiB)**; final host free space is **154,373,144,576 bytes (143.77
GiB)** at that checkpoint. Guest and host recovery are not added together or
counted again as part of the earlier 229.28 GiB cleanup.

The current output and source checkouts remain outside the deletion set. The
original builder configuration, output alias, four logs and three selected
sentinels pass bounded preservation checks, not a complete filesystem audit.
**Images6 capture is in progress; no new image result is established.** The
five-image SHA-256 stage, Package6 and final signing/ROM/boot gates remain open.
No phone operation occurs. See the
[second cleanup checkpoint](build-progress.md#second-old-output-cleanup-and-trim--2026-09-02)
for exact scope, accounting and receipts.

**Selected4 component build and profile postcheck pass.** The native invocation
runs **2026-09-02 19:24:16–19:25:59 UTC**, exit **0**; the root wrapper closes
at **19:37:41 UTC**, also exit **0**. The result verifies **26 fresh producer
actions and eight fresh strict library statuses**, plus configured signature
and manifest checks for nine APKs. Flex's current-equivalent prior strict check
is separate, not a ninth fresh status.

All **six complete before/after callback maps match**, with **548 selected
source files** and **1,179 project HEAD/origin matches**. Backup-first output
preparation preserves **26 originals and 26 independent copies**. Source
identity **`nezha.86e40fe309189fdcd20dff9b`**, normal Android enforcing, 4 KiB
and working76 remain unchanged. The root reviewed the actual result and its
36 signature/manifest command records; separate export/replay of those raw
command streams is not established by this checkpoint. These checks do not
verify every embedded signature scheme, full manifest XML or runtime behavior.

**Images6, the five-image SHA-256 stage and Package6 remain pending**, followed
by signing and complete AVB/FEC/VINTF/super/partition, OTA and device-boot gates.
No source mutation or phone operation occurs, and the ROM is **not flashable**.
See the [Selected4 checkpoint](build-progress.md#selected4-component-build--2026-09-02)
for exact receipts and scope.

## Earlier Nothing11 and cleanup checkpoint

This entry preserves its frontend-only result and then-pending Selected4 work.

**Nothing11 passes after cleanup.** The resumed native `m nothing` invocation
runs **2026-09-02 17:51:18–17:53:01 UTC**, exit **0**; the genuine root wrapper
closes at **17:56:39 UTC**, exit **0**. Profile validation, the metadata
postcheck and all six complete before/after callback-map comparisons pass.
The **254-field configuration** is unchanged with all six expected SHA-256
settings, under **`nezha.86e40fe309189fdcd20dff9b`**. This is a frontend/metadata
validation result, not fresh component or image production. The
[Nothing11 checkpoint](build-progress.md#nothing11-passes-after-storage-cleanup--2026-09-02)
records actual receipts and the unchanged limits on Ninja/image/ROM claims.
Selected4/Images6, the five-image SHA-256 stage, Package6, signing and final
AVB/VINTF/super/OTA/boot gates remain pending. No phone operation occurs.

**Verified cleanup leaves 273.56 GiB available on the host.** At
**2026-09-02 17:45:04 UTC**, completed deletion of **51 obsolete files** and the
separately approved free-block trim leave **293,727,363,072 bytes** available.
The three operation-local host-free increases total **229.28 GiB**. The guest's
**99.18 GiB** scratch deletion is not added again to that host total. The same
builder is restored with its original configuration, the temporary maintenance
container is removed, and the active 1 TiB volume remains present.

Source checkouts, working76, stock originals, current build inputs and small
evidence remain outside the deletion set. Preservation checks cover selected
files and ownership, not every filesystem object. The earlier 114.21 GiB
host-only milestone and failed unprivileged trim remain in the
[dated cleanup record](storage-cleanup.md), with exact checks and receipts.

The unchanged **100 GiB host reserve** is exceeded at this checkpoint; the
**full follow-on storage budget and later build admission remain separate**.
The subsequent Nothing11 result above is separate from cleanup itself.
Cleanup does not establish fresh component/image proof or a flashable ROM. No reserve
guard is lowered or bypassed, and no phone operation occurs.

## Earlier Nothing10 profile failure and storage hold

At the September 2 **16:26:15 UTC** checkpoint, native continuation was held:
the host reserve check found **63,488,000,000 bytes** free against the unchanged
**100 GiB** minimum. An additional **45 GiB** was requested to restore that
minimum. The roughly 267 GiB then free in the guest did not satisfy the
host-volume gate. This historical hold precedes the host cleanup above.

**Nothing10's native invocation exits 0, but its profile fails and the root
command exits 1.** The generated configuration changes six SHA-256 leaves,
not the single top-level field predicted by the request. Source-history and
strict-settings checks reject that mismatch; the dependent archive-check
error does not establish archive corruption. The original false profile
flags and null postcheck remain intact. Source identity stays **86e40**, build
**`nezha.86e40fe309189fdcd20dff9b`**.

At that earlier checkpoint, Nothing11 check/bind/preparation commands and
**36 focused host tests pass**, but **Nothing11 has not executed**. No native-wrapper readiness, fresh
component/image proof, Package6 result or flashable ROM is claimed. The
backup-first Selected4/Images6 workflow, no-invalidation five-image stage and
all signing/AVB/VINTF/super/OTA/boot gates remain pending. Normal Android
**enforcing**, **4 KiB** and **`working76`** remain unchanged; no phone operation
occurs. See the [Nothing10 and storage checkpoint](build-progress.md#nothing10-profile-failure-and-host-storage-hold--2026-09-02)
and [exact receipts](../research/workspace-integration.json).

## Earlier SHA256 source-adoption and query checkpoint

This entry preserves the completed source/query milestone and its then-pending
Nothing10 transition.

The **SHA-256 hashtree source correction is installed**, and **Config13 and
Context13 pass** under **`nezha.86e40fe309189fdcd20dff9b`**, epoch **1788144555**.
One device-tree exchange changes only `BoardConfig.mk` among **548 source
files/fifteen projects**. Full record validation checks five journal events;
both queries retain all **1,179 HEAD/origin matches**, **1,170 clean projects**
and **nine expected patched projects**, with all six callback maps stable.

The **254 configuration fields remain unchanged** across the queries. Neither
query observes Ninja or passes a sandbox check; query success is not image
production. Full readback of the pinned Soong writer and installed BoardConfig
supports the expected `BoardAvbSystemAddHashtreeFooterArgs` change from `[]` to
`["--hash_algorithm", "sha256"]`, but that generated transition is **not yet
observed** and remains a Nothing10 gate.

**Nothing10, backup-first Selected4/Images6, the five-image SHA-256 rebuild and
Package6 remain pending.** The five-image stage retains its no-invalidation
rule. Earlier Package5 images, AVB preparation and VINTF failures are not
retroactively promoted. Normal Android enforcing, 4 KiB and `working76` remain
unchanged; no phone operation, source sync or private-key transfer to the VM
occurs. Signing, super-image/partition, full VINTF, OTA and boot/hardware gates
remain open, and the ROM is **not flashable**. See the dated
[source-adoption and query checkpoint](build-progress.md#sha256-source-adoption-and-config13context13--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier Package5 host-input checkpoint

This entry preserves the closed host results and then-pending source correction.

The **complete Package5 archive is independently admitted on the host**, and
**15 image inputs are materialized**. The ZIP is **10,997,962,405 bytes**, with
the same `622073f3…` SHA-256 as the native supplement. This does not promote the
copier to success: its first attempt failed with zero bytes and `EAGAIN`; the
second copied the complete file but failed the final input-ancestor check.
Both failures and the absence of `transfer.json` remain preserved.

**AVB public preparation exits 2** on invalid hash/hashtree parameters. Five
images—**product, system, system_ext, system_dlkm and vendor_dlkm**—carry SHA-1
descriptors where the reviewed profile requires SHA-256. The other ten strict
metadata parses pass, not complete image or signature verification. No private
signing or completed public image set is established.

**VINTF staging verifies 31 files, but capture exits 1** when the original
property parser rejects `ODM/etc/build.prop`. There is no ACK or successful
capture completion; this is not a VINTF compatibility result. A SHA-256 source
producer correction and faithful property-parser successor remain **in
progress, not validated or adopted**.

Normal Android enforcing, 4 KiB and `working76` remain required. Signing,
ZIP reconciliation, full AVB/VINTF, FEC, super-image/partition checks, OTA and
boot/hardware remain open. No phone operation occurs and the ROM is **not
flashable**. See the dated [host-input and AVB/VINTF checkpoint](build-progress.md#package5-host-inputs-and-avbvintf-failures--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier Package5 supplement checkpoint

This entry preserves the supplement replay and its then-pending host transfer.

The **corrected Package5 post-build supplement and complete finite-evidence
replay pass**. The separate verifier runs in the **VM Python supervisory
harness**, finishing at **2026-09-02 12:17:30 UTC**, without rerunning the build.
It validates the **two original fresh directory/ZIP producer actions**, fresh
metadata-hook execution, **205 metadata members** and **221 selected ZIP
members**. The original native-exit-0/host-exit-1 result retains its false
profile flags and null postcheck; the supplement does not rewrite that failure.

Root replay verifies **242 complete files / 168,788,306 bytes**, including 219
expanded-member bodies, six metadata values, seven policy bodies and three
recomputed sidecars, with five complete export seals and 286 held host inputs.
The separate paired-input replay admits the supplement alongside the original
failure. **ZIP and image bodies are not exported to or read on the host**.
The native archive is **10,997,962,405 bytes / 9,154 entries**; not every member
or complete archive semantics is verified.

Source **548/fifteen projects**, **`nezha.b429840950d789320b04847a`**, epoch
**1788144555**, enforcing normal Android, 4 KiB and `working76` remain unchanged.
ZIP transfer and final AVB/VINTF/partition, signing/rollback, OTA and
boot/hardware gates remain pending. No phone operation occurs and the ROM is
**not flashable**. See the dated [Package5 supplement](build-progress.md#package5-corrected-supplement-and-complete-evidence-replay--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier Package5 profile-postcheck failure

This entry preserves the original failure and its then-pending supplement.

**Package5's native Soong invocation exits 0, but its profile postcheck
fails**. Native execution finishes at **2026-09-02 11:41:29 UTC**; the direct
host session exits 1, observed at **11:47:38 UTC**. The recorded error is
`AttributeError`: the checker module has no `_installation_report` attribute.
The profile postcheck runs in the VM's Python supervisory harness.
The original result remains unchanged: preflight, invocation and native
success are true, while **profile completion and validation are false** and
**`postcheck=null`**.

Both complete native streams are retained and verified: **801,876-byte stdout
and empty stderr**, with matching two-pass seals and nine-field stats. Native
Ninja observation, argv, limits and sandbox checks pass with observation
required; all six complete callback maps match before/after. This does **not**
establish archive admission, ZIP validation or the two fresh package-action
proofs. A corrected checker and separate supplement remain pending.

Source **548/fifteen projects**, **`nezha.b429840950d789320b04847a`**, epoch
**1788144555**, enforcing normal Android, 4 KiB and `working76` remain unchanged.
Final AVB/VINTF/partition, signing/rollback, OTA and boot/hardware gates remain
open. No phone operation occurs and the ROM is **not flashable**. See the dated
[Package5 postcheck failure](build-progress.md#package5-native-exit-and-profile-postcheck-failure--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier Images5 checkpoint

This entry preserves its image-only scope and then-pending package work.

The **Images5 native build, postcheck and complete evidence replay pass**.
Native execution exits 0 at **2026-09-02 10:56:15 UTC**, with **seven fresh
actions, three recomputed policy sidecars and four image checks**. Ninja
observation, argv, limits and sandbox checks pass, with observation required.
All six complete callback maps match before/after.

The root's successful original replay covers **56 files / 144,374,566 bytes**,
including twelve current/preserved metadata files, seven compiler/policy pairs
and retained sidecar evidence. Four original image inodes and three sidecar
copies plus three originals remain retained. Large image and graph bodies are
**not read on the host**; image hashes remain completed native postcheck proof.

Ordinary **`postcheck.metadata.verified=true`** is separate from
**`images.metadata_hook_verified=false`**. Image reproducibility, runtime and
the signed parent chain remain unverified. Source **548/fifteen projects**,
**1,179 revisions/origins**, **254 configuration fields**,
**`nezha.b429840950d789320b04847a`**, epoch **1788144555**, enforcing normal
Android, 4 KiB and the `working76` prebuilt derivative remain unchanged.
**Package5 is next**; final AVB/VINTF/partition, signing/rollback, OTA and
boot/hardware gates remain open. No phone operation occurs and the ROM is
**not flashable**. See the dated [Images5 checkpoint](build-progress.md#images5-and-complete-evidence-replay--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier Selected3 checkpoint

This entry preserves its component-only scope and then-pending image work.

The **Selected3 native build and complete original-evidence replay pass**.
Native execution exits 0 at **2026-09-02 09:57:46 UTC**, with **26 fresh
producer actions, eight fresh strict statuses and zero reuse**. Ninja
observation, argv, limits and sandbox checks pass, with observation required.
The prior Flex check remains separate. All six callback maps match before/after.

Full replay covers **203 files / 165,615,424 bytes**, including 36 recorded
verification attempts, 72 attempt streams and both build streams. The root's
independent repeat reproduces all three outputs byte-for-byte with consumer
filesystem/process/network access blocked. Retention metadata authenticates
**26 native copies plus 26 originals**; those 52 binary bodies are not exported
to the host. The Package5 source-context projection uses recorded observations
and is **not physical Package5 admission or execution**.

Source **548/fifteen projects**, **`nezha.b429840950d789320b04847a`**, epoch
**1788144555**, enforcing normal Android, 4 KiB and `working76` remain unchanged.
**Images5 and Package5 are next**, with signing/rollback, OTA and boot/hardware
still unverified. No phone operation occurs and the ROM is **not flashable**.
See the dated [Selected3 checkpoint](build-progress.md#selected3-and-complete-evidence-replay--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier query/Nothing9 checkpoint

This entry preserves its query/build scope and then-pending component work.

**Config12, Context12 and Nothing9 pass** under
**`nezha.b429840950d789320b04847a`**, epoch **1788144555**. Nothing9 exits 0
at **2026-09-02 09:04:46 UTC**; its genuine wrapper exits at **09:08:22 UTC**.
The original host review and independent root recheck verify complete
**18,460-byte stdout and empty stderr**, six metadata values/newlines and all
six callback maps across both queries and Nothing9. Source **548/fifteen
projects**, **1,179 revisions/origins** and **254 configuration fields** pass.

Config12 retains direct-launch, byte-only completion limits; no outer timing,
full outer-stream or prelaunch-stat proof is invented. The queries record no
observed Ninja or sandbox pass. Nothing9 observes Ninja and passes limit/sandbox
checks, but **Ninja argv is unverified** and observation is not required. This
does not prove fresh metadata rewrites or component actions.

The next gates are a **fresh 26-action selected-component rebuild → Images5 →
Package5**. Normal Android enforcing, 4 KiB and `working76` remain unchanged.
Signing/rollback, OTA and boot/hardware remain unverified; no phone operation
occurs and the ROM is **not flashable**. See the dated [query/Nothing9 checkpoint](build-progress.md#config12context12-and-nothing9--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier metadata-mode source-install checkpoint

This entry preserves its source-only scope and then-pending native work.

The **metadata-mode flags correction is installed in the source tree**. The
root install command runs **2026-09-02 08:09:40–08:19:10 UTC**, exit 0; full
readback completes at **08:19:21 UTC**. Original-record validation verifies
**three atomic exchanges, nine journal events and seven content replacements**
within **548 files/fifteen projects**, with all **1,179 HEADs/origins** matching.
Image, kernel, recovery and Makefile contents remain unchanged.

This is source adoption, not a new configuration or build result. The retained
**254-field configuration** is unchanged and its prior native build identity
is **`nezha.a7db36604f45fcc657373f89`**; no successor identity calculation is
included here. Config12/context12, Nothing9, Images5 and Package5 remain
separate verification gates. Normal Android enforcing, 4 KiB and `working76`
remain required. No phone operation occurs; signing/rollback, OTA and
boot/hardware remain unverified, and the ROM is **not flashable**. See the
[source-install checkpoint](build-progress.md#metadata-mode-flags-source-installation--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier Package4 failure checkpoint

This entry preserves the failure and its then-uninstalled host-fix scope.

The **Package4 native retry fails** at a build-metadata guard, exiting 1 at
**2026-09-02 07:15:57 UTC**. Full retained stdout confirms checksum `OK`, then
**`native target-files mode differs`** at the failed `.zip.list` target. This
concerns packaging configuration, not file permissions: `building_vendor_image`
and `building_odm_image` are absent where the installer expects empty strings.
A/B and VINTF enforcement remain `true`; `allow_non_ab` is absent.

Complete native stream readback and all **three failure metadata bodies /
227,334 bytes** are verified, with two matching reads and nine-field stat
checks. Preflight and invocation occurred, but native success, profile
completion and validation are false; no package postcheck or successful ZIP
is verified. All six callbacks match before/after this run.

The current checksum-adapter correction is committed as **`3e4f904`**, with
**4,463 offline tests passing**, but is **not installed in the VM**. Successor
metadata and mi_ext controls remain host candidates. The installed source is
still **548 files/fifteen projects**, **`nezha.a7db36604f45fcc657373f89`**, epoch
**1788144555**. Images4 remains a separate successful milestone. Normal Android
enforcement, 4 KiB and `working76` remain unchanged; final VINTF/AVB/partition,
signing/rollback, OTA and boot/hardware gates remain open. No phone operation
occurs and the ROM is **not flashable**. See the dated [Package4 failure checkpoint](build-progress.md#package4-build-metadata-mode-failure--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier Images4 checkpoint

This entry preserves its original image/replay scope and then-pending work.

The **Images4 native phase and complete original-evidence replay pass**.
Native execution exits 0 at **2026-09-02 06:26:44 UTC**, verifying **seven fresh
actions, three recomputed framework sidecars and four image outputs**. Four
original image inodes and three sidecar copies plus three originals are
retained. Recovery remains the pinned `working76` prebuilt derivative.

The root's complete host replay exits 0 at **06:46:12 UTC**, checking **56
evidence files / 144,194,084 bytes**, original names, nine-field stat records
and final second-pass seals. It replays the fresh actions, twelve current and
preserved metadata files, seven compiler/installed policy pairs and retention
journals. **Large image and full graph bodies are not exported**; image hashes
remain native postcheck evidence. All six callbacks match before/after and
Nothing8, unlike selected-nine2's expanded protected-input callback.

The source remains **548 files/fifteen projects**, build
**`nezha.a7db36604f45fcc657373f89`**, epoch **1788144555**, enforcing normal
Android and 4 KiB. Package4 remains the next unverified build phase; read-only
preparation is not package success. The metadata packaging hook, image
reproducibility, signed parent chain, final VINTF/AVB/partition, rollback, OTA
and boot/hardware gates remain open. No phone operation occurs and the ROM is
**not flashable**. See the dated [Images4 checkpoint](build-progress.md#images4-and-complete-evidence-replay--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier selected-nine2 checkpoint

This entry preserves its original component/replay scope and then-pending work.

The **selected-nine2 native build and complete retained-evidence replay pass**.
Native execution exits 0 at **2026-09-02 05:30:17 UTC**, followed by genuine
outer-wrapper exit 0 at **05:41:09 UTC**. The deliberately forced-fresh build
verifies **26 fresh actions, eight fresh strict statuses and zero reuse**.
Its 26 retained copies and 26 originals are preserved; host metadata replay
checks all **109 journal events**, without exporting those 52 file bodies.

Full host replay verifies **203 evidence files / 165,002,879 bytes**, including
36 recorded native verification attempts and 72 streams. All three replay
products reproduce byte-for-byte with consumer filesystem/process/network
access blocked. Six native callbacks match before/after; compared with Nothing8,
**five** are identical and the protected callback retains the same **25 ordinary
inputs plus 180 selected-app inputs**. No new guard is introduced.

The package-context projection uses recorded component observations: it is not
Package4 execution or a fresh observation of the **173 GMS files**. Images4,
Package4, final VINTF/AVB/partition, signing/rollback, OTA and boot/hardware gates
remain open. Enforcing normal Android, 4 KiB, `working76`, kernel warnings and
`test-keys` are unchanged; no phone operation occurs and the ROM is **not
flashable**. See the dated [selected-nine2 checkpoint](build-progress.md#selected-nine2-and-retained-evidence-replay--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier query/Nothing8 checkpoint

This entry preserves its original query/build scope and then-pending work.

The **548-file/fifteen-project source passes config11/context11 and ordinary
Nothing8**. Nothing8 finishes with native exit 0 at **2026-09-02 04:25:20 UTC**;
its genuine root wrapper exits 0 at **04:28:56 UTC**. Full host review retains
the complete **18,460-byte stdout, empty stderr and six physical metadata
bodies** matching **`nezha.a7db36604f45fcc657373f89`**, epoch **1788144555**,
hostname and fingerprint/thumbprint. This verifies values, not fresh rewrites.

All six source/input guard maps match both queries and Nothing8 before/after;
**1,179 pinned HEADs/origins** and **254 configuration fields** remain unchanged.
Config11 retains its byte-only completion limits. Nothing8 observes Ninja and
passes sandbox/limit checks, but does **not** verify Ninja argv or fresh
component actions. The measured output `.ninja_deps` grows **62,488 bytes** to
**171,758,884**; its narrow capture exception and shared-graph qualification
remain pending, followed by selected-nine2, Images4 and Package4.

Normal Android enforcement, 4 KiB, `working76`, kernel warnings and `test-keys`
remain unchanged. No phone operation occurs; final VINTF/AVB/partition, signing,
rollback, OTA and boot/hardware gates remain open, and the ROM is **not
flashable**. See the dated [query/Nothing8 checkpoint](build-progress.md#config11context11-and-nothing8--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Earlier source-install checkpoint

This entry preserves its original source-only scope and then-pending work.

**The checksum 0023 source correction is installed**, with verified native exit
0. The root install command ran **2026-09-02 03:23:44–03:33:54 UTC** and exited
0; complete readback finished at **03:34:05 UTC**.
Receipt review verifies six exchanges, **548 files/fifteen projects** and all
**1,179 pinned HEADs/origins**. Ten existing source files change and three
checksum controls are added; modes and observed images are preserved, with no
image or public-key exchange. The original 205-file metadata source projection
passes; that is not a packaged-metadata or ZIP result.

The completed host identity projection over verified installed records yields
**`nezha.a7db36604f45fcc657373f89`**; independent replay reproduces all eight
outputs. This is not a fresh VM query. The **254-field configuration observed
during installation remains the preceding `nezha.b51a6b5609d2001e9ae1f7ae`
snapshot**, not native `a7db` evidence. config11/context11, Nothing8, physical metadata,
selected-nine2, Images4 and Package4 remain pending. Package3 retains its
historical failure below. Normal Android enforcement, 4 KiB, `working76`, kernel
warnings and `test-keys` are unchanged; no phone operation occurs and the ROM
remains **incomplete and not flashable**. See the dated
[source-install checkpoint](build-progress.md#checksum-0023-source-installation--2026-09-02)
and its [exact receipts](../research/workspace-integration.json).

## Historical checkpoints

The following entries preserve their original results and then-pending work.

**Package3 fails at the target-files metadata checksum hook**, with native exit
1 at **2026-09-02 02:09:50 UTC** and actual host exit 1 at **02:14:06 UTC**.
The failing target-files-directory action is **13,468/13,582** and reports
`sha256sum: Unknown option 'strict'`. Later parallel progress reaches 13,475;
the failure is not an APK or Metalava error. No successful Package3 ZIP or
artifact postcheck is established.

Complete readback of the result and both native streams verifies **12,917,575
bytes** and two matching hash/stat passes. All six ordinary guard maps and the
GMS/selected-app prerequisite summaries match before and after. Runtime
observations legitimately differ after the build; they are not asserted equal.
The active source remains **545 files/fifteen projects**, build
**`nezha.b51a6b5609d2001e9ae1f7ae`**, with 254 configuration fields unchanged.

A pinned native Toybox compatibility probe verifies all **14 expected outcomes**:
canonical lowercase 64-hex digest validation followed by `sha256sum -c` accepts
correct bytes and rejects wrong, malformed or missing inputs and command
failure. The first probe's provenance-path typo remains recorded. Additive
[patch 0023](../patches/evolution/0023-portable-target-files-metadata-checksum.patch)
also passes a **15-case rendered-guard smoke test**, reaching a test sentinel
only for the matching digest. No Make/Kati or metadata installer runs in that
test. The patch is prepared only; no replacement source is installed in the VM.
The metadata runtime and source composition must also be refreshed because the
existing bundle pins the complete Makefile. Fresh source/configuration/metadata
receipts precede a packaging retry.

Images3 and selected-nine retain their verified scopes. Normal Android
enforcement, 4 KiB, working76, kernel warnings and `test-keys` are unchanged;
no phone operation occurs and complete-ROM readiness remains false. See
[build progress](build-progress.md) and the
[Package3 failure checkpoint](../research/workspace-integration.json). Earlier
checkpoints below preserve their original results and then-pending work.

The **Images3 native build, postcheck and retained-evidence replay pass**. Native
execution runs at **2026-09-02 01:12:09–01:13:56 UTC**, with exit 0 and actual host exit 0
at **01:17:50 UTC**. All seven installed producers are verified fresh: recovery,
mi_ext, vendor and ODM images plus three framework policy SHA sidecars. The four
images match their pinned inputs; working76 remains **`a130ba75…`**. This is
delivery of the selected prebuilt images, not new recovery/vendor runtime
compilation or a verified Evolution boot.

The result intentionally records **`output_invalidated_or_deleted=true`**:
four prior installed images and three sidecars are moved to retained locations
before rebuilding, with original inodes and three sidecar copies preserved.
All six ordinary guard maps match Nothing7, and **545 source files/fifteen
projects**, **1,179 pinned HEADs/origins** and **254 configuration fields** stay
unchanged. Six metadata bodies match **`nezha.b51a6b5609d2001e9ae1f7ae`** and
epoch **1788144555**.

Full host replay verifies **56 retained files / 138,925,847 bytes**, including
the seven fresh actions, policy pairs, three sidecar hashes and current/preserved
metadata. Large image and graph bodies are not read back to the host; their
native hash checks remain bound to the completed postcheck. Package3 and its
VINTF/AVB/partition checks, the signed boot chain and hardware tests remain
separate. The selected-kernel warnings, `test-keys`, enforcing normal Android,
4 KiB and working76 are unchanged. No phone operation occurs and complete-ROM
readiness is false. See [build progress](build-progress.md) and the
[Images3 checkpoint](../research/workspace-integration.json). Earlier checkpoints
below keep their dated results and then-pending work.

The **selected-nine native build and retained-evidence replay pass**. BCR and all
eight Clock apps build from **2026-09-02 00:16:36 to 00:18:20 UTC**, with native
exit 0 and actual host completion at **00:27:52 UTC**, also exit 0. The complete
result/action review and raw-proof replay verify **26 fresh outputs, zero reused**:
nine built APKs, nine installed APKs and eight strict status files. BCR's status uses
its normal route; seven corrected Clocks use qualified detached goals. Flex's
prior strict check is equivalent, but no Flex status is produced or reused.

All **180 selected input pins** match admission and before/after guards. The six
normalized ordinary guards equal Nothing7, with **545 source files/fifteen
projects**, **1,179 matching HEADs/origins** and all **254 configuration fields**
preserved. The **36 successful native verifiers** cover source and installed APKs,
not intermediate APK signatures: BCR retains its signer, installed Clocks match
the platform certificate, and all nine manifest comparisons pass. Six metadata
bodies match **`nezha.b51a6b5609d2001e9ae1f7ae`** and epoch **1788144555**.

The **201-file retained-evidence export completes with exit 0**, and independent
full host replay passes at **00:45:22 UTC**, rehashing **186,601,892 bytes** and
reproducing the original consumer result. This verifies captured component-end
observations, not fresh package-time VM observations or Package3 execution.
Images3, Package3 and final VINTF/AVB/partition and device tests remain separate
gates. The selected-kernel warnings, `test-keys`, enforcing normal Android,
4 KiB and working76 remain;
complete-ROM readiness is false and no phone operation occurs. See
[build progress](build-progress.md) and the
[selected-nine checkpoint](../research/workspace-integration.json). Earlier
checkpoints below retain their original scope and then-pending work.

The **shared graph capture and eight raw Clock configuration readbacks pass**.
The capture's actual host process exits 0 at **2026-09-01 23:58:47 UTC**; complete
host replay review passes at **2026-09-02 00:00:32 UTC**. All **83 read-only
queries** return exit 0 with complete, untruncated streams: 14 GMS, five provider,
six SignApk and 58 selected-prebuilt queries. All six complete root callback
identities match Nothing7 on **545 files/fifteen projects**, and the before/after
graph, log, native-result and Ninja snapshots match. The nonempty capture stderr
and its sandbox warnings remain retained and bound to the outer source guard.

The separate readback finishes at **00:01:42 UTC**, verifying eight nonempty raw
JSON bodies totaling **108,277 bytes** against their source-owned
`g.android.rawFileCopy` declarations. These are source payloads, not proof that
the copied configuration destinations exist or were built. The qualified graph
plans **26 outputs**: 18 APK outputs and eight fresh status outputs, with BCR on
its normal route, seven corrected Clocks on explicit detached goals, and Flex
requiring prior-read-only-check equivalence. No producer or checker executes in
this capture, and mode selection alone does not establish that Flex equivalence.

The measured `.ninja_deps` ceiling is **170,213,408 bytes**; the authenticated
combined JSON envelope uses **65 MiB** for the measured 67,512,218-byte input.
Both narrow limit repairs preserve original controls and query scope; the
envelope repair leaves individual-file limits unchanged. A first host replay's
`KeyError: pins` is corrected only in the wrapper shape, without a VM call or
changed serialized evidence.

Actual selected-app admission, build, fresh strict statuses and native
signature/manifest checks remain next; Images3, Package3 and final boot-chain
and hardware gates remain separate. The capture and raw readback change no
source or Android output and do not access the phone. Normal Android
enforcement, 4 KiB, working76, `test-keys`, the selected-kernel warnings and false
complete-ROM readiness are unchanged. See [build progress](build-progress.md)
and the [shared-capture checkpoint](../research/workspace-integration.json).
Earlier checkpoints below retain their original scope and then-pending work.

The **545-file/fifteen-project source now passes config10/context10 and ordinary
`nothing7`**. The exact `--make-mode -j8 nothing` invocation exits native 0 at
**2026-09-01 23:24:12 UTC**; its actual host command also completes with exit 0.
Full retained-stream review passes at **23:30:31 UTC**, binding the 2,049-byte
native stdout and empty stderr. Six physical metadata-file bodies confirm
**`nezha.b51a6b5609d2001e9ae1f7ae`**, epoch **1788144555**, the hostname and
the expected fingerprint/thumbprint. These value checks do not prove fresh
metadata rewrites or binary producer actions.

All six complete source/input guard maps and 254 configuration entries match
admission and both predecessor queries; all 1,179 pinned project HEADs and
origins match, preserving nine reviewed locally patched projects. Four separate
read-only collectors at **23:29:54 UTC** retain logs and selected dependency
configuration evidence. Neither those captures nor the ordinary `nothing` goal
qualify the corrected Clock checker rules or establish an APK component pass.

The next gate is qualification of the regenerated Clock rules and corrected
strict status/module checks, with fresh ordinary producer/signature evidence.
Images3, Package3, final VINTF/AVB/partition checks and device testing remain
separate. The selected-kernel AVB/origin warnings and `test-keys` remain visible;
normal Android enforcement, 4 KiB, working76 and false complete-ROM readiness
are unchanged. See the [build progress](build-progress.md) and
[Nothing7 checkpoint](../research/workspace-integration.json). Earlier query,
source-adoption and failure checkpoints below retain their original scope.

The **545-file/fifteen-project Clock-corrected source now passes native
config10 and context10**. Soong exits 0 at **2026-09-01 23:00:17 UTC** and
**23:08:51 UTC**; the wrappers also exit 0, with context10 closing at
**23:11:57 UTC**. Complete retained-stream review passes. All six source/input
guard maps remain equal within and across both queries, all 254 configuration
entries match admission, and all 1,179 pinned project HEADs and origins match.
The nine reviewed locally patched projects are preserved. The native build
environment is bound to **`nezha.b51a6b5609d2001e9ae1f7ae`** and epoch
**1788144555**; this does not verify physical metadata files for that identity.

Context10 reports Android 16 build **`BP4A.251205.006`**, Xiaomi branding and
**`test-keys`**. Both queries retain the exact warning that the selected kernel
inputs report failed AVB verification and unverified origin, kernel/module
compatibility and device boot. The initial context dispatcher failed on a
host metadata lookup before any native query; its corrected wrapper changes
no native request or build setting. That prelaunch failure remains recorded.

The next gate is ordinary **`nothing7`**, physical metadata verification and
regenerated Clock rules, followed by corrected strict checks and fresh ordinary
producer/signature evidence. Images3, Package3, the signed boot chain and
hardware validation remain separate. Normal Android enforcement, the 4 KiB
baseline, working76 and false complete-ROM readiness are unchanged. The
[Clock guide](systemui-clocks-optional-window-libraries.md) and
[query checkpoint](../research/workspace-integration.json) retain the evidence.
The earlier source-adoption and audit checkpoints below keep their dated scope.

The **Clock 0022 source correction is installed**, with native/root exit 0 at
**2026-09-01 22:47:17 UTC**. Complete readback and review of the actual receipts
pass. The active inventory now contains **545 files across fifteen projects**,
preserving all 544 ancestral rows and modes and thirteen protected APKs. One
source exchange adds the seven reviewed optional-library declarations; Flex
and the existing BCR integration remain unchanged.

The separate host projection completes at **22:50:30 UTC**, calculating build
number **`nezha.b51a6b5609d2001e9ae1f7ae`** with the same pinned epoch. This is
not yet verified in native configuration or metadata. config10/context10,
ordinary `nothing7`, corrected strict Clock checks and fresh producer/signature
evidence remain pending, as do Images3 and Package3. The earlier two-pass,
seven-mismatch audit retains its failed result. Normal Android enforcement,
the 4 KiB baseline and working76 are unchanged, and complete-ROM readiness
remains false. [Clock source integration](systemui-clocks-optional-window-libraries.md)
records the adoption and its limits. Earlier checkpoints below retain their
dated source counts, identities and then-pending work.

The next verified blocker is the **nine-APK strict library audit: two passes
and seven Clock manifest mismatches**, ending with exit 1 at
**2026-09-01 21:49:21 UTC**. BCR and SystemUIClocks-Flex pass the standalone
check. BigNum, Calligraphy, Growth, Inflate, Metro, NumOverlap and Weather each
need the ordered optional Window library pair. All nine badging commands pass;
all selected APKs were checked, with none waived, omitted or unresolved. This
read-only audit changes no source, APK or Android output and establishes no
ordinary status-file production or BCR component-build success.

Reviewed [patch 0022](systemui-clocks-optional-window-libraries.md) adds the
missing declarations to those seven imports and preserves Flex. Host tests and
synthetic checker fixtures pass, but source adoption, regenerated rules and
actual successful producer evidence remain pending. The active source remains
**544 files/fifteen projects**, build number
**`nezha.f9f678051a7b3de57c741ca2`**. The 4 KiB baseline, normal Android
enforcement and working76 remain unchanged. Images3, Package3, the signed boot
chain and hardware validation remain separate gates; complete-ROM readiness
is false. The earlier checkpoints below retain their dated scope.

The **544-file/fifteen-project source now passes config9, context9 and ordinary
`nothing6`**. Nothing6 finishes with native exit 0 at **2026-09-01 20:23:46 UTC**
and wrapper exit 0 at **20:26:41 UTC**. All six complete source/input guard maps
remain equal; all 254 configuration entries match admission and both queries.
All 1,179 pinned project HEADs and origins match. Six physical metadata-file
values verify build number **`nezha.f9f678051a7b3de57c741ca2`** and the selected
build epoch. Full native stdout readback and review pass; four subsequent
read-only captures retain log and dependency-configuration evidence.

This establishes graph generation and metadata values, without proving fresh
metadata rewrites or complete binary provenance. BCR's strict status action,
module/class-loader and APK-signature checks, the combined non-GMS audit,
Images3 and Package3 remain separate gates, as do the signed AVB chain, boot and
hardware validation. The 4 KiB baseline, normal Android enforcement and
working76 are unchanged; complete-ROM readiness remains false. See
[BCR source integration](bcr-optional-window-libraries.md) and
[build progress](build-progress.md). The earlier checkpoints below retain their
dated results and then-pending work.

The **BCR 0021 source correction is now installed**, completing through the
guarded Linux source transaction at **2026-09-01 19:32:56 UTC**, with native/root
exit 0. One 85-byte optional-library assignment is added; the APK, signing
selection, privileges and product placement are unchanged. Complete readback
and independent installation review pass. The active inventory is **544 files
across fifteen projects**, preserving all 543 ancestral rows and modes. The
pinned `vendor/extras` project has exactly the one reviewed modified declaration.

The host identity projection passes at **19:36:03 UTC**, calculating
**`nezha.f9f678051a7b3de57c741ca2`**. This is not yet a native configuration or
metadata result. At this adoption checkpoint, config9, graph regeneration,
strict BCR component checks, Images3 and Package3 remain unverified; the broader
non-GMS audit is also required before packaging. The Package2 failure and prior
GMS2/Images2 successes retain their original scopes. Normal Android enforcement,
the 4 KiB baseline, working76 and false complete-ROM readiness are unchanged.
See [BCR source integration](bcr-optional-window-libraries.md). The paragraphs
below preserve the preceding checkpoints, including their source counts and
then-pending adoption state.

The current build blocker is **Package2's strict BCR uses-library mismatch**.
The ordinary `target-files-package` attempt exits native 1 at
**2026-09-01 18:08:23 UTC** and wrapper 1 at **18:12:04 UTC**. BCR's manifest
declares optional `androidx.window.extensions` then `androidx.window.sidecar`;
its build declaration supplies neither. Both required-library lists are empty.
Strict checking remains enabled. The active source remains **543 files/fourteen
projects, identity `3c24`**, with the 4 KiB baseline and normal Android enforcement.
No BCR source correction or successor inventory has been adopted.

Complete readback retains the failed result and both native streams. All six
source/input guard maps and 254 configuration entries match before and after;
Ninja, sandbox, resource-limit and process checks pass without a resource fault.
The artifact postcheck did not run. This failure capture provides no new
package, image or boot verification. BCR input qualification, a reviewed
declaration correction and a strict retry are the next slice. The earlier GMS2
and Images2 successes retain their separate scopes. See
[build progress](build-progress.md) and the
[Package2 failure record](../research/workspace-integration.json).

The **ordinary Images2 build and postcheck pass**, with native exit 0 at
**2026-09-01 17:10:06 UTC** and wrapper exit 0 at **17:13:46 UTC**. All seven
installed-output producers are verified fresh: the four selected prebuilt
images (`recovery`, `mi_ext`, `vendor`, `odm`) and three framework-policy SHA
sidecars. The images match their pinned source inputs, including working76;
the sidecars match the selected ODM policy basis. Seven compiler-output and
installed-policy pairs are verified. All six complete source/input guard maps
and all 254 configuration entries remain equal on the **543-file/fourteen-project
`3c24` source**, with the 4 KiB baseline and normal Android enforcement unchanged.

The reviewed preparation deliberately moved four prior installed images and
three sidecars into retained locations before the build, preserving their
originals. The result therefore records **`output_invalidated_or_deleted=true`**;
this was a scoped output rebuild, without source changes or another whole-output
archive. Readback of all 56 planned evidence files and independent replay of
action and policy evidence pass. The readback excludes large image and graph
bodies; the native postcheck supplies the source/output image hash checks.
Package2, final package VINTF/AIDL and boot checks, the signed AVB chain,
partition fit and physical-device testing remain separate
gates. No complete or flashable ROM is verified. See
[build progress](build-progress.md) and the
[Images2 checkpoint](../research/workspace-integration.json).

The following paragraphs preserve earlier dated checkpoints. Their pending
work and failed attempts retain that historical scope.

The **GMS2 component attempt passes its native build and postcheck** on the
543-file/fourteen-project source with identity `3c24`. Native Soong exits 0 at
**2026-09-01 16:06:05 UTC**; the completed wrapper also exits 0. Three SignApk
actions and CrossDevice's build/install pair are fresh. Ten ordinary module
actions are verified as reused, including all four strict uses-library checks;
none of those four is claimed fresh. Complete retained-evidence readback and
independent replay pass, including all sixteen native signature/manifest checks.
Strict signature verification remains enabled. The earlier failed capture and GMS1 attempt
remain failed; Images2, package2 and ROM readiness remain unverified. See
[GMS source integration](gms-source-integration.md) for the separate capture,
staging, action and postcheck evidence.

The **543-file/fourteen-project source passes config8, context8 and ordinary
`nothing5`**, with native/root exit 0 through **2026-09-01 14:33:17 UTC**.
Six actual metadata-file values verify build number
**`nezha.3c24f46cf801e6abd6d5361c`**; matching values do not establish fresh
producer actions. Fresh read-only log/config observations complete at
**14:37:58 UTC**, without admitting a new graph or component build. The corrected
SignApk has not yet been rebuilt, and the prior GMS SourceStamp failure remains
failed. Graph qualification, strict GMS retry, Images2 and package2 remain
pending. See [GMS source integration](gms-source-integration.md); the earlier
source-adoption and failed-attempt checkpoints below retain their original scope.

The prepared boot-content check's public macOS runtime separately passes its
live recheck at **2026-09-01 14:56:33 UTC**, with outer exit 0.
[Boot-image validation](boot-image-validation.md) records its exact inputs and
the raw-v6 omission corrected by raw-v7. This does not admit package2 or any
final boot image; the GMS/build gates above remain pending.

The corrected **SignApk source installation succeeds at 2026-09-01 13:36:04
UTC**, with two exchanges, seven journal events and no rollback. Full readback
and independent review pass. The active inventory is **543 files/fourteen
projects**; the calculated successor build number is
**`nezha.3c24f46cf801e6abd6d5361c`**. That identity is a host projection, not yet
verified in native configuration or build output. config8/context8, a rebuilt
signer, strict GMS retry, Images2 and package2 remain pending. Normal Android
enforcement, the 4 KiB baseline and working76 are unchanged. See
[GMS source integration](gms-source-integration.md) for the source transaction
and its limits; the paragraphs below preserve earlier checkpoints.

The first **SignApk source-install attempt fails and rolls back both edits** at
**2026-09-01 12:56:39 UTC**. Staging passed, but a retained history check rejected
the intended `build/make` status change. The rollback and fresh input comparison
pass; active source remains **541 files/fourteen projects with the `a2d9`
identity**, not the staged 543-file candidate. The guard correction is still
preparation, with no corrected signer build or successful component retry.
Sixteen separate read-only APK commands complete with fifteen exits 0 and the
same installed CrossDevice SourceStamp failure. The later parser correction
passes saved-output replay only. [GMS source integration](gms-source-integration.md)
records the failed installation, retained evidence and verification limits.

The earlier targeted four-module **GMS attempt fails its postcheck**. Native Soong exits
0 at **2026-09-01 11:45:18 UTC**, recording four strict uses-library checks and
four APK build/install pairs, but the wrapper exits 1 at **11:50:26 UTC**.
CrossDevice's installed APK triggers `-Werr` with `No SourceStamp signature`:
the old stamp-certificate digest survives platform signing without its matching
stamp signature. Original APKs and the 541-file/fourteen-project `a2d9` source
remain unchanged. The [prepared SignApk correction](signapk-source-stamp.md)
preserves strict verification; source adoption and a successful retry are still
required. Images2, package2 and ROM readiness remain blocked. See
[GMS source integration](gms-source-integration.md) for the retained failure.

The earlier **corrected GMS read-only graph capture passes at
2026-09-01 11:11:47 UTC**, with all nineteen query streams verified and source, graph and log guards
unchanged. Six proof records are staged at **11:21:37 UTC**; these are neither
app builds nor image outputs. Their evidence does not establish successful
module builds or packaging. [GMS source integration](gms-source-integration.md)
records the source-defined HTTP runtime provider, existing precompilation
settings and the preserved earlier capture failure. ROM readiness remains false.

The preceding **config7/context7 queries and ordinary `nothing4` run pass with
native and root exit 0** on the 541-file/fourteen-project source and build number
**`nezha.a2d9ab6affbe09593d338212`**. config7 passes 21 values at **09:17:23 UTC**,
context7 passes seven at **09:25:02 UTC**, and `nothing4` finishes at
**2026-09-01 09:46:14 UTC**. All six complete guard maps and all 254 configuration
entries match; six actual metadata-file values match the new identity. Those
value checks do not establish fresh file rewrites. The retained stdout shows
165 frontend steps plus one `nothing` action, not GMS module or image builds.
Those query results do not qualify GMS status actions, APK outputs or final
package selection; the later failed component attempt has its own evidence.

The source audit matches all **1,179 pinned HEADs and origins**, with **eight
intentional locally patched projects** whose statuses match the installed source
guards. The earlier read-only post-run measurement retains the complete
`nothing4` stdout and log measurements; the later graph capture has its own
separate evidence and scope.

The **four-file GMS source adoption completes at 2026-09-01 09:08:48 UTC with
native and root exit 0**. Staging, full installation readback and all eleven
journal events are retained; the journal's `commit_verified` event is earlier,
at **09:06:54 UTC**. The active source inventory is now **541 files across
fourteen projects**, preserving the prior 537-file/thirteen-project checkpoint.
The [source integration record](gms-source-integration.md) binds all four original
Makefiles, the installed 0018/0019 changes and eight unchanged image observations
(six present files and two exact archive absences). Independent stage and
installation reviews pass; the separate host identity review is also clear.

The earlier host identity calculation remains distinct from the later native
query and metadata results above. The ordinary frontend uses the reviewed exact
`-j8 nothing` command; observed Ninja limits and sandbox checks pass, but this
profile does not qualify descendant Ninja argv or component actions. No
installed source changes in this run. The 4 KiB baseline, working76,
normal Android enforcement and original APKs remain unchanged. HTTP remains
selected; CrossDevice removes only its stale direct declaration and retains
automatic SDK-28 compatibility.

The earlier **95-APK audit remains 91 passes/four mismatches**, and the
**08:45:34 UTC four-module proposal probe** remains separate read-only evidence,
without generated rules or ordinary status stamps. The seven omitted declarations
in the raw product request inventory are three compressed ETC payloads, two JARs
and two APKs with pre-existing strict-check waivers. None is counted as a manifest
pass. The Bugle/Velvet read-only manifest capture completes at **09:29:53 UTC**
with native/root exit 0 and all five input guards unchanged. Neither APK declares
a required Java uses-library; Bugle omits four optional declarations and Velvet
omits six. No strict checker, APK signature or provider-presence result follows,
and the existing waivers remain unchanged.

The **first ordinary `target-files-package` build remains failed**, with native
and wrapper exit 1 at **08:03:01 UTC** on the customization bundle's missing
optional `wear-sdk` declaration. Its complete result, stdout and three action
logs remain retained; no artifact postcheck or verified ZIP is established.
Package production does not itself run the full VINTF comparison: final package
inputs and explicit SKU/vendor-API selection still need admission. The older
220-source VINTF evidence remains historical.

The policy and image sequence below preserves its earlier source checkpoints.

The corrected Evolution/factory policy source build and its **scoped policy3
verification now pass**. Source/M4/context review retains all 6,399 assertions,
all twelve normal binaries pass unfiltered zero-permissive checks, and the
public-name freeze check is verified. The **policy3 raw-image reconstruction
also passes**, with both TAR/image/export sets identical and independent review
confirming exactly five policy-file replacements. The subsequent **NONE leaf
footer/FEC production also passes** with identical repeated outputs. Private
image copies and the later **source-v2 adoption now pass**: three tree exchanges
commit at **2026-09-01 02:37:56 UTC**, with nine journal events, complete receipt
readback and independent review. The active source inventory is **537 files
across thirteen projects**; the reviewed policy3 vendor/ODM leaves are selected
as source inputs. The earlier capacity and Camera JNI mode-guard failures remain
preserved. [Volume maintenance](apple-container.md) cleared the recorded budget,
and the narrow archive-mode correction preserves the original JNI mode.
The build identity is now rebound to the recorded private metadata-copy modes,
and **config6/context6 pass all 21 configuration and seven context value checks**
on the adopted source. The subsequent **ordinary `nothing3` run passes at
2026-09-01 03:22:47 UTC**, including graph regeneration and the six actual
metadata-file value checks for the new identity. This does not establish fresh
rewrites or component/image actions. The subsequent seven-goal **images1 native
process exits 0 at 04:26:42 UTC, but its wrapper exits 1**: validation rejects
the combined Ninja graph's pool-depth change from 15 to 8. Independent review
explains that exact change from the pinned source and observed `-j8`; it does
not promote the failed wrapper result. A **separate read-only postcheck passes
at 05:03:29 UTC**, verifying four output images, three policy sidecars and all
seven producers' fresh action evidence. Saved-receipt readback and independent
artifact review now pass within that scope. The later **AIDL component build
exits native 0/wrapper 0 at 05:34:01 UTC**, compiling the host auditor and seven
NDK backends; the auditor has not been executed. **Packaged-policy checks and
target-files remain unverified**. Commit **4335f1b** adds
the explicit [policy3 image-input profile](policy-image-inputs.md), including
qualified installed sidecars. Source-input selection does not admit a final
flashable artifact: the full signed chain and physical partition fit remain
unverified. Full recursive graph provenance and final installed-APK Treble
coverage remain unverified; no ROM or boot readiness is implied.
`LINEAGE_BUILD=nezha` selects upstream policy directories absent from the earlier
build configuration. The thirteen retained policy identities and earlier strict
analysis remain historical evidence; they do not establish current policy or
factory-image compatibility. Commit **5d557a0** adds the explicit
[Evolution policy base](evolution-policy-base.md) and its source/reference
checker. Two host stagings reproduce the same 57-file private policy bundle.
Those inputs and patch 0015 are now installed as **evolution-policy-components-v1**
at **2026-08-31 13:24:59 UTC**, with three committed operations, complete receipt
readback and independent review. That transaction inventories 529 source files
across thirteen projects. The first 32-goal attempt **fails in Soong graph
generation at 14:02:13 UTC**, before policy compilation: a device filegroup
requests visibility to a specific vendor package, which Soong forbids.
The minimal correction from commit **30a9f74** is now installed as
**evolution-policy-visibility-v1** at **14:43:26 UTC**, with complete receipt
readback. It changes three files and preserves the 529-file inventory, patch
0015 and strict 4 KiB settings. The second attempt passes Soong and enters main
Ninja, but **fails strict combined-policy compilation at 15:28:07 UTC**:
Evolution allows `vendor_init` to set `vendor_persist_camera_prop`, conflicting
with the factory neverallow for non-core domains. Commit **85c5b40** prepares the
[one-grant source correction](camera-property-vendor-init-write.md), without
removing assertions. Commit **7c22c82** adds the separate
[seven-prefix factory-label capability](factory-property-contexts-capability.md),
and **641af6a** integrates both capabilities into explicit source/bundle admission.
Two host stagings reproduce all 63 policy-bundle files, with original factory
inputs unchanged. The paired corrections and separate AIDL-audit source are
now installed at **2026-08-31 18:10:01 UTC**, with four committed operations,
eleven journal events, complete receipt readback and independent review.
That policy3 build inventories **539 source files across thirteen projects**;
strict 4 KiB checks and historical output archives are preserved. **Policy3
passes all 32 requested goals at 2026-08-31 18:40:00 UTC**, with native and
wrapper exit 0 and all six fresh source/input guard groups matching. The log
records 390 main Ninja actions after 166 frontend steps, not 556 tests.
All six metadata-file values match the selected `d1485e` identity; fresh rewrites
are not inferred. Independent wrapper/source/metadata and retention-accounting
reviews are clear within that scope. The later semantic review preserves all
seven factory property-prefix regions and finds zero helper property-write
grants. Separate native analysis verifies zero permissive domains in all twelve
normal binaries. The scoped public freeze compares 1,419 types and 353
attributes without differences. Current image compatibility and final packaging
remain unverified. Normal Android enforcement remains required.

The user now authorizes a **4 KiB first-boot baseline**; 16 KiB compatibility is
not a prerequisite for that initial bring-up. The preceding guest source was
**first-target-files-release-flags-v1**. Its one-file correction commits at
**2026-08-31 09:17:15 UTC**, preserving the 478-file source vector and prior
outputs; independent correction review passes for the recorded installation.
It replaces forbidden direct
`TARGET_RELEASE` access with four resolved release flags, while `bp4a` remains
a separate invocation binding. That selected input closure was sealed, and
the corrected native queries pass **21 configuration and seven context value
checks**. The later **nothing2** run passes the exact source/configuration checks
and six metadata-file value checks, with independent review complete. This does
not prove fresh rewrites or image reproducibility, and its metadata evidence
retains its pre-component input scope. The earlier component build number was
host-derived and selected in its failed attempt, without a new six-file
metadata qualification; policy3's later value checks are separate. The three preflight failures,
obsolete-query native failure and failed `nothing1` validation remain preserved. The maintained
[construction source selector](rom-construction.md) reproduces the thirty
then-installed device files through the full original input checks. Two fresh
candidates match, while omitting the selector preserves the original candidate.
This does not admit flashable artifacts or change the default generator path.
The reviewed **first-target-files-v1** construction/date installation
at **08:45:28 UTC**, its original guard and all nine journal events remain
preserved. Those source transactions alone did not verify generated metadata.
The preceding **packaging-matrix-v1** transaction
committed eight operations at **08:13:39 UTC**, with reviewed packaging selections. The earlier
**matrix-v1** source was committed at **03:14:25 UTC**. Its 38-goal build
finishes at **03:51:10 UTC** with native exit 0 and **128 Ninja actions after
163 frontend steps** (291 total progress rows), but the
wrapper exits 1 on an XML postcheck that wrongly requires explicit AIDL
version 1. The original failed receipt is preserved. A separate read-only
postcheck now passes at **04:32:59 UTC (August 31 in New York)**, verifying the
new matrix outputs and guarded inputs. Independent host review now passes;
this does not rewrite the failed wrapper or prove full VINTF. The previous
**v13ja 4 KiB** component record remains historical. The previous v13ja source
configuration introduced `4096` with prebuilt checks enabled. Commit **17cde61** adds
the [current-provider 4 KiB successor](nezha-page-size-v2-integration.md), with
matching host candidates and checks enabled, without ignore flags or SELinux
changes. Only the generated product fragment and new descriptor change. The
compiled stock kernel's 4 KiB configuration is independently verified; running
phone behavior is not. The **37-goal `pagesize-v13j-1` component build passes at
2026-08-31 00:43:11 UTC (August 30 in New York)**. Its actual generated Soong
maximum changes from `16384` to `4096`, with prebuilt checks still enabled.
All thirteen protected policy and eleven runtime identities match the prior
result, preserving the existing strict policy analysis. This is not a fresh
full-policy analysis or the separate 26-provider ELF check. The partial VINTF
alias skips the matrix-definition subcheck for a matrix with no level; full
compatibility and VTS remain unverified. Earlier 16 KiB failures and the old
host experiment remain preserved.
Scoped review verifies **4,890 logged Ninja actions after 163 frontend steps**,
not 5,053 tests. Only the maximum changes among 254 generated settings. The
captured allocator has four 4 KiB-aligned load segments. Its later producer
capture and subsequent native prerequisite verification succeed within the
scope below; runtime registration remains open. The separate provider result follows.
The fresh pre-install snapshot passes at **23:30:55 UTC**, retaining all 1,179
source pins/origins and the active 16 KiB settings; it does not install the
candidate or run a build. The subsequent inactive v13j stage fails while
checking an absent archive path with a missing ancestor, before installation.
That failed stage and its backup remain preserved. The corrected v13ja
transaction commits at **2026-08-31 00:07:36 UTC (August 30 in New York)**,
with one device-tree exchange and a five-event journal ending in
`commit_verified`. The independent host review binds the captured receipts;
it does not reread the live guest. The later component result is separate
evidence, with 54 selected file bodies captured and 36 APEX identities recorded
as metadata only; no image or APEX bodies were returned. The scoped build and
log reviews are clear within those limits.

The separate **provider-elf-v13j-4k-1** build now passes **all 26 fresh ELF and
symbol checks**, completing at **2026-08-31 01:15:10 UTC**. Independent review
reconstructs each exact command, new Ninja-log row and empty result stamp;
the four stamps already present before launch are not counted as cached passes.
The 48 native actions comprise 26 checks and 22 dependency actions. All seven
captured files rehash, the fourteen historical evidence files remain preserved,
and strict settings, source, policy and runtime guards pass. This closes the
selected provider ELF/symbol gate at 4 KiB, not full ABI, service registration,
runtime behavior, VTS or boot validation.
The **latest full VINTF run on matrix-v1 now passes all four native commands**:
39-APEX materialization, framework consistency, vendor/ODM consistency and the
combined framework/vendor/kernel/APEX check. All fifteen postflight checks pass
with source and Android outputs unchanged; no command is unreached. The combined
command has no reported skips or warnings and accepts the supplied non-mainline
kernel inputs. The separate framework-consistency command retains one no-level
matrix-definition skip and two warnings; its skipped subcheck is not a pass.
Complete input compatibility, runtime behavior and ROM readiness remain false.
Final independent raw, coverage and materialization reviews pass within that
scope. The earlier pre-matrix run's
exit-65 failure on 155 missing HAL instances remains preserved.
Commit **c3686ed** adds the [exact framework-matrix source projection](framework-matrix.md).
Host verification binds all 155 missing AIDL tuples to original declarations
and factory matrix coverage, producing 130 packages without wildcard instances,
broadened versions or changes to numbered platform matrices. Repeated 47-file
candidates match. The subsequent matrix-v1 transaction now selects that source
through one atomic exchange and a five-event journal ending in `commit_verified`.
The guarded source set grows from 219 to 220 with the authored XML: the original
204 source inputs plus fifteen producer preconditions and the new file. All
thirteen policy/eleven runtime identities and the 4 KiB product remain unchanged;
238 rollback copies and 26 stamps are retained. The native matrix command now
exits zero; its failed wrapper is followed by the separate passing postcheck.
The installed and
generated XML have the same 30,492-byte identity and all 155 expected tuples;
103 HAL nodes omit the canonical default version 1. The correction uses the
pinned libvintf default and keeps invalid explicit declarations rejected. Its
separate read-only postcheck verifies all 220 source inputs, thirteen policy
and eleven runtime outputs, three allocator outputs, four tools and five
targets, without another build or source/output writes. Independent review
binds both receipts and confirms one retained no-level matrix-definition skip,
which is not counted as a pass. Existing strict policy analysis is reused by
exact equality of thirteen protected policy files. Neither the failed receipt
nor generated XML is rewritten.
The provider installation and its raw review now pass as described below. Fresh
producer descriptions and the full-input capture bind the successful VINTF retry
without rewriting the earlier failed matrix wrapper or the exit-65 result.

Three read-only provider-install preflights stop in their evidence reader after
two, three and four zero-exit native queries. The bounded corrections recognize
the exact 27 repeated aggregate dependencies, companion installs reached through
order-only links, and two manifest-assembly producers among 29 ordinary copies.
Two later diagnostics verify the actual leaf recipes, with source/output guards
unchanged; they do not install providers or verify the full dependency graph.
All failures remain preserved. The complete corrected preflight now passes nine
read-only queries, binding 27 normal module goals to 31 installed destinations
and the 26 enabled ELF checks. Independent host admission passes without fresh
checks or installs. The subsequent **27-goal ordinary provider build passes at
06:10:10 UTC**, reporting 29 fresh copies and two preserved XML files: all 31
selected installed files verify. It reuses the 26 earlier strict ELF passes
with the same effective inputs, dependencies, tools and flags; **zero fresh ELF
checks run**. All six postcheck groups complete, with source, policy/runtime,
XML/APEX and producer graphs unchanged. Independent replay verifies all **164
Ninja actions** and the complete seven-file capture, with no findings. It keeps
fresh installs, preserved XML and reused checks distinct. No new source selection,
image integration, full ABI, runtime or hardware success is implied.

The previously analyzed policy baseline is **policy-only-v13h-1**, completed
at **2026-08-30 05:40:07 UTC**, with 31 goals and 273 Ninja actions after
configuration. Source inputs remained unchanged, the native sandbox was verified,
and all eleven preserved policy outputs and eleven protected runtime outputs
were verified. Provider runtime/ELF actions and images were not requested.
The subsequent native analysis now verifies the provider policy's exact
assertions, effects and source provenance.

The latest native analysis, **analysis-v13h-policy-only-v1**, passed at
**13:12:51 UTC**. It retains all **6,366 original assertions plus four provider
assertions**, verifies nine fresh context/structural checks, and finds **zero
permissive domains in three binaries**. Against v12f/export4, the reviewed
ordinary delta is exactly **12,005 allow**, **1,883 dontaudit** and **3,291,674
neverallow coverage effects added**, with none removed. The complete review also
binds extended-permission changes. Two new dontaudit statements are recorded;
denial logging is not claimed unchanged. Helper property-set permissions remain
zero, normal Android stays enforcing, and all guarded inputs remain unchanged.
The independent capture review has no findings: all 208 captured files and the
complete reviewed effect inventory match, with only four validated generated
assertion-name roles normalized for comparison. This does not modify policy.

This establishes the historical v13ha policy-selection baseline, not the full
current Evolution policy. The earlier v12f/export4
analysis and [v11b analysis](oem-policy-integration.md) remain separate dated
evidence. The earlier v13f provider inputs were
installed, but their first 31-goal policy build failed during Soong bootstrap
at **02:36:44 UTC**. `nezha_framework_libmiracastsystem`'s emitted static variant
depends on Audio AIDL V2 directly and V4 through `libaudiofoundation`. No new
policy compiled or context check passed in that failed attempt. The later
v13ha transaction installed the reviewed correction at **04:52:42 UTC** through
three exchanges and a verified nine-event journal; its native policy build now
passes. The first missing-ancestor snapshot failure remains preserved.
Three native Soong fixtures reproduce the expected graph outcomes and show
that selecting only the shared variant does not resolve the mixed V2/V4
dependency. The first compile-only audio-layout probe failed in its AST parser;
the corrected v2 probe passes two cases and four compilations, matching all
15 measured factory layout constraints. Static review also verifies the two
selected descriptor-vtable CFI checks without requiring CFI suppression. Neither
result admits the complete caller ABI or proves runtime routing. Commit
`364ab89` includes the v7 Miracast correction and verified host producer/consumer
bindings now installed as v13ha. The analysis binds the actual provider-input
genrule: 42 original inputs and 31 payloads, with 30 unchanged and one exact
one-byte dependency derivation. This is input-production evidence; provider
ELF compatibility, runtime installation and service behavior remain unverified.
Retained vendor/ODM images still contain
their original policy. Provider compatibility, complete Treble APK labeling,
current-provider policy-image integration and the remaining ROM build gates are
still open.
Earlier tool-bound, aggregate-model
and M4-guard failures remain preserved in the
[native integration record](native-rom-integration.md); they are not relabeled
as passes.

The matching **policy-sidecar-v13h-native-v1** derivation passes six native
checks and fourteen commands with zero skips. It derives three digest files
from the sealed current-policy inputs; the system_ext digest changes while
platform and product remain unchanged. These are validation outputs; installed
digest files, Android genrule execution and image adoption remain separate.
The read-only VINTF graph capture
now binds 21 XML inputs, including both provider fragments, and 36 APEX inputs.
Its `check-vintf-all` alias still omits full compatibility. The three-goal
**vintf-v13h-1** build timed out at **16:32:28 UTC** after its configured
10,800 seconds, with logged progress at 58,702/61,802. It returned exit 1;
no forced kill or remaining build process was reported. The failed result,
logs and nine available XML outputs are preserved. A fresh capture at
**16:42:27 UTC** verifies the same source history, graph and strict settings.
The incremental **vintf-v13h-2** retry finished at **16:58:47 UTC**, without a
timeout, but failed the frozen level-5 `vintffm` check because
`android.hidl.allocator` is mandatory and not declared in the manifest. All
57 selected XML/APEX artifacts are present; presence is not compatibility.
Full VINTF remains a compatibility blocker after the selected 4 KiB provider
ELF checks pass. The earlier v13i allocator producer capture remains admitted for
its historical packet; the new 4 KiB capture and its separate limits follow.
Commit `1647192` adds the
[host-verified allocator capability](framework-allocator.md), selecting the
existing upstream service while retaining its init, SELinux and `max-level="8"`
manifest behavior. The **v13i** transaction installed that device selection at
**18:48:34 UTC**, preserving 24 guarded inputs and 112 prior outputs. All 1,179
base revisions and origins still match. The 37-goal **allocator-v13i-1**
component build passed at **19:20:26 UTC**, with 178 Ninja progress rows after
163 frontend steps. Independent review confirms fresh allocator compile/link/
strip/install actions, all three captured outputs and strict 16 KiB alignment.
The init file matches upstream bytes; the generated manifest preserves the
expected allocator declaration and max-level 8 semantics. The partial VINTF
run explicitly skipped `checkMatrixHalsHasDefinition` for a matrix with no
level. This is not a zero-skipped native or full compatibility result. Exact
allocator producer descriptions do not prove source-to-binary equivalence or
runtime service registration. The strict v13h
policy analysis is reused through unchanged policy inputs and exact byte
equality of the analyzed policy; no fresh analysis is claimed.
The first allocator producer capture passes nine commands across three query
layers and describes all three outputs, with zero skips and preserved inputs.
Its capture-time evidence remains valid, but the later product-list metadata
action appended 126 bytes to OUT `.ninja_log`. The full VINTF guard therefore
requires a fresh capture; that guard is not weakened to accept stale logs.
The fresh **allocator-producers-v13i-2** capture passes at **22:46:09 UTC**,
with nine commands, three query layers, zero skips and unchanged source/OUT.
Its complete host collection is independently reviewed and admitted for packet
preparation. The older 221-file v13h staging remains historical. A subsequent
231-file v13i packet stages successfully, but its first capture rejects a
shadowed writable `/work` mount beneath the read-only overlay. The corrected
capture advances past that check, then fails because its archive reader expects
`.py` sources while the built tools package `.pyc` files. A deterministic
source-to-bytecode proof using the pinned Soong recipe is in progress. This
unfinished 16 KiB packet remains historical. The 4 KiB component build now
passes; the next checks use its fresh outputs and the passed provider ELF
results. No full native VINTF compatibility pass is established.
The auxiliary bytecode capture v2 fails one producer query at its 8 GiB RSS
limit while thirteen other commands pass. Its narrowly enlarged query-only
successor v3 gets past that limit but fails because the standalone Soong graph
does not define `highmem_pool`. All v3 postflight guards pass; its selected
inputs remain unchanged. Both failed captures are preserved, without a
fabricated pool or global VINTF memory-limit change.

The corrected **v4 bytecode capture and proof both pass**. Across the two
phases, 28 native commands exit zero with no skips. Four complete `.pyc`
comparisons reproduce the packaged headers and bodies from the pinned Soong
recipe: `apexd_host.pyc`, `deapexer.pyc` and the `apex_manifest.pyc` member of
each tool. Independent review verifies the captured proof and selected-input
preservation. This does not prove generated-proto source provenance, APEX
signatures, runtime activation or full VINTF.
The separate **AVB-tool bytecode capture/proof also passes**: 28 zero-exit
native commands reproduce the one complete packaged `avbtool.pyc` member from
the pinned recipe, with zero skips. This does not verify an APEX signature or
signed image chain. The subsequent **native APEX integrity run passes
for all 39 packages**, with 130 completed zero-exit commands, no postflight
errors and preserved source/OUT. Independent raw review verifies all 1,589
captured files and replays the 130 completions and diagnostics: 65 APK signature
checks verify v3, 26 CAPEX digests match and 39 signed AVB payloads verify.
This is static verification of the historical pre-matrix v13ja inputs. It does
not establish every embedded signature scheme, independent OEM signer
authenticity for retained vendor baselines, runtime activation, partition AVB
or OTA validation.

The current **allocator-producers-v13j-4k-1** capture completes at
**01:31:45 UTC**, with nine zero-exit commands across three query layers and
zero skips. All three producer outputs are described, with source and selected
graph/log guards preserved. The complete 66-file host collection and envelope
checks pass. That host-only admission leaves external native references for a
subsequent guest check; no new compile action, source-to-binary equivalence or
runtime registration is established by this read-only capture.

The earlier **pre-matrix 4 KiB full-VINTF input capture passes**, freshly
reopening the allocator prerequisites and the four bytecode proof comparisons.
It verifies the nine-command/three-layer/six-node allocator descriptions and
binds **22 framework XML files and 39 APEX packages**: 36 framework plus three
vendor packages. Strict 4096 settings and the actual component result remain
bound. This closes those input prerequisites; the subsequent full run below is
a separate failed compatibility result.

That pre-matrix full run materializes all 39 APEX packages and passes the framework
and vendor/ODM consistency commands. The combined framework/vendor/kernel/APEX
command then returns **65**, reporting **155 unique device HAL instances not
specified in the framework matrix** through `checkUnusedHals`. All four
commands complete normally, none is unreached, and all fifteen postflight
checks pass with source and Android outputs unchanged. The framework command
still reports one explicit matrix-definition skip and two warnings; those are
not counted as checks passed. The log identifies kernel 6.12.23 as non-mainline,
but the failed run does not prove complete kernel acceptance. The 54-file
capture preserves the result and diagnostics; signatures, runtime APEX
activation, complete VINTF coverage and ROM readiness remain unverified.
Independent host review is clear for the captured failure and materialization
evidence. It does not reopen extracted payload bodies or turn the failed
combined command into a compatibility pass.

The later **matrix-v1 producer capture** records nine read-only commands across
three query depths and six described nodes. All 68 evidence files are collected;
the subsequent guest input check reopens the native references and verifies the
paired original-build/separate-postcheck observations. It does not claim a fresh
compile, source-to-binary equivalence or runtime registration. The fresh full
capture binds 220 source identities, 53 source guards, 22 framework XML files and
all 39 APEX packages. The subsequent four-command run is the current successful
native VINTF result above, not a replacement for the preserved failure.

The same capture also verifies equality of all 39 packages and their selected
trust, tool and runtime inputs against the prior static APEX proof. Independent
review permits reuse of that **130-command cryptographic result**, with **zero
new cryptographic commands**. A later final review binds that reuse to the
actual successful materialization and all fifteen postflight checks, without
rerunning cryptography. No partition AVB chain, OTA behavior, APEX activation
or hardware result is inferred.

Ninja query captures were held pending qualification of the pinned query
modes under read-only mounts. The second footer capture accepted the valid empty
Soong shard, then failed its first jailed query while trying to open a build log
on a read-only filesystem. Earlier unconfined provider queries and the memfd
fixture therefore do not prove absence of source-root or OUT log writes. Small
source-root `.ninja_log` and `.ninja_deps` files are recorded and preserved in
place; their writer is not established. No original project payload change is
known. This caveat does not invalidate the VINTF builds' separately verified
source guards or relax their compatibility checks.
The actual query qualification v1 remains failed: four checks pass and two fail,
with zero skips. Its positive `-n` known answers pass, but the help-stream and
corrupt-dependency negative-fixture expectations fail. The corrected **query
qualification v2 passes all six checks**, with eleven commands and zero skips,
including the expected read-only failure controls. Independent review releases
only the exact reviewed footer-capture recipe; other graph-capture recipes are
not automatically admitted, and earlier no-write claims remain unproven.

The actual **footer-tools-native-v3** capture passes with 28 commands, two query
depths and zero skips. Independent review verifies all 81 captured files, eight
observed Ninja/loader jails, unchanged graph identities and all four tracked log
files. This captures tool identities, producer descriptions and loader mappings;
it does not execute the `avbtool`/`fec` entrypoints or prove a fresh producer build.
The following v4 host admission failed because its runtime-closure comparison
omitted the separately recorded interpreter. The narrow v5 correction passes
host admission. **policy-footer-qualify-v1** then passes four native checks
across seven commands, including payload/tree corruption rejection and a
separate regenerated-FEC comparison; zero skips. Independent review is clear.

The current **policy-images-v13h-v1** native reconstruction passes **nine checks
and 38 commands with zero skips**, including 18 fsck checks. Both independent
TAR/image/export sets are byte-identical, with exactly one vendor file and four
ODM files changed; every other content digest and semantic metadata field is
preserved under the explicit physical-layout exclusions. Independent review
of the 97-file capture has no findings. The raw vendor image matches export4;
the ODM image carries the sealed v13h policy and matching digests. These outputs
remain unadopted, with original images and staging preserved.

The subsequent **policy-footer-produce-v1** run completes at **18:49:27 UTC**
with six native checks, sixteen commands and zero skips. Two independent
vendor/ODM pairs are byte-identical, preserve the raw EROFS prefixes, and pass
hashtree, independently regenerated FEC and exact factory-package size checks.
These are keyless `NONE` leaf footers; physical partition fit, a signed parent
chain, current-source compatibility, adoption and boot remain unverified.
Independent review of all 110 captured files is clear. The host review does not
reopen the large native image or FEC outputs.

The **Camera product-list prerequisite** now passes one actual upstream Ninja
copy action, producing the exact 26,921-byte list of 1,230 packages. All 204
source inputs, thirteen policy and eleven runtime outputs, and sixteen graph
files remain unchanged; only OUT `.ninja_log` grows by the expected 126 bytes.
The subsequent **Camera capture v5b** completes four read-only queries and all
postchecks at **21:15:28 UTC**, preserving its source, graph and log inputs.
Independent review is clear. The namespace remains unexported and unselected;
APK source admission, protected-output inventory, actual build checks, grants
and runtime behavior remain unverified. Earlier failed captures are preserved.
The exact eleven-file Camera namespace and original APK are now staged in an
inactive candidate, with all fifteen file/directory modes verified. Independent
review confirms preserved source, output and graph guards. Activation remains
held for refreshed Camera source/output evidence and remaining admission checks; staging
does not change the active namespace or select/build the APK.
The fresh **4 KiB Camera prerequisite capture** completes at **01:50:13 UTC**,
passing four read-only queries with source, captured-output and query-log
guards unchanged. Independent review passes, rehashing 28 copied files and all
eight query streams while retaining the exact strict settings. The complete protected-target
inventory was still missing from that capture; it does not select the APK or
establish permission grants. The subsequent **complete target/alias inventory
capture passes at 02:29:12 UTC**, with source/output preservation verified.
Independent review now passes for that recorded v13ja state: 4,071 entries
include 3,321 regular files, 711 directories and 39 symlinks. No writable OUT
alias is found outside the target tree, but ten protected policy outputs lie
outside that tree and need separate read-only protection in a future build.
Fresh source/graph/inventory evidence is required after the matrix exchange.
Namespace activation, graph execution and the actual APK build remain held.

Provider capture v6 remains a parser-ambiguity failure. The corrected **v7
read-only capture** passes five queries with strict 16 KiB configuration and
unchanged guarded inputs, with all 26 ELF-check stamps absent at capture time.
The subsequent **provider-elf-v13i-1** build fails at **21:51:56 UTC**: three
checks pass, nineteen reject 4 KiB alignment where 16 KiB is required, and four
are unreached or unproven. Six separate dependency-strip actions fail on
read-only `/tmp`. Independent review confirms these outcomes. The targeted
four-goal follow-up finishes at **22:38:14 UTC** using the corrected temporary
directory: `libwfdconfigutils` passes, while `libmiracastsystem`,
`libwfdcommonutils` and `libwfddisplayconfig` fail alignment. All six global
postchecks pass. Across the two attempts, the distinct inventory is **four
passed and twenty-two failed at 16 KiB**; this is not 26 newly executed checks
or a replay of the earlier successful checks. Independent review rehashes all
seven new capture files and all seven prior files, separately accounting for
thirteen repeated failures. All 71 dependency outputs are now present and the
temporary-storage failure is resolved. The later authorized 4 KiB successor
passes its own 26 fresh checks; these failed 16 KiB results are not relabeled.

The first image-delivery dispatch failed before staging on its
case-observation check. The corrected dispatch now prepares independent private
guest copies of the exact vendor/ODM footer images, with preserved source,
policy, runtime and original-image inputs. This is private preparation, not
metadata or image adoption. Delivery used a writable source/OUT namespace;
preservation is checked, not inferred from read-only mounts. Independent review
accepts only these private copies and their guarded preservation.
Commit **e304faa** adds the maintained [policy-image delivery adapters](policy-image-delivery.md)
and [explicit device integration](target-files-delivery-integration.md). Repeated
host candidates match and preserve all 205 original metadata files. Original
factory modes remain unchanged. The first isolated delivery Kati fixture runs
60 cases: **58 pass and two fail, with zero skips**. Both undefined-selector
cases stop at a fixture parse error before their intended production guard.
The corrected fixture now passes **all 60 cases with zero skips**, retaining
the exact production include and all source/postflight guards. The failed
first attempt remains preserved. Independent review of the 73-file capture is
clear for this isolated fixture.
That fixture does not establish ordinary product execution, source/image
adoption or the metadata hook; complete targets stay blocked.

Commit **137f438** adds a separate, explicitly paired 4 KiB delivery successor.
Two host metadata bundles match across all **247 files**, retaining the 205
original metadata members, and two **47-file** device candidates are identical.
The capability binds the actual 37-goal result and current 4 KiB profile;
independent host reviews are clear within their stated scope. The older
delivery mode and descriptor remain unchanged. That host checkpoint did not
install the metadata bundle or source/image candidates. Historical private-copy
evidence is retained as provenance, not a fresh 4 KiB copy or source check.
At that checkpoint, current input qualification and source activation remained
required. The later transaction below selects the exact verified `NONE` leaf
images with AVB enabled. Ordinary product/metadata-hook execution remains
pending. Final flashable-artifact admission still requires the complete signed
parent chain, rollback settings and physical
partition fit.
The subsequent **inactive 4 KiB policy-image stage now passes**, copying the
exact reviewed vendor/ODM leaves into a separate candidate source bundle and
rehashing current source/policy/runtime inputs. It changes neither active
source nor Android outputs and does not install metadata or adopt images.
The complete transport and native-receipt reviews pass within their stated
scope, including all eleven captured transport files. Large image bodies remain
in the guest. Activation required the deliberate source rebase and fresh
admission recorded below; no signed-parent, physical-fit or boot
result follows.

The later **matrix packaging qualification passes at 08:00:47 UTC**. It verifies
seven current policy inputs and three ordered digest comparisons, with **zero
installed framework-sidecar checks**. It does not run the normal Android
sidecar generators or the final target-files hook. The original private mi_ext
directory-mode failure and the later missing-platform-sidecar failure remain
preserved, including their incomplete markers. Only the platform sidecar was
observed absent; the other two installed sidecars and normal generator outputs
were not observed. All three ordinary sidecar modules and the unchanged final
policy/installation checks remain mandatory before packaging admission.

The eight-operation packaging source installer subsequently returns
`commit_verified` at **08:13:39 UTC**. Its complete nine-file readback verifies all
nineteen journal events and the actual **475-file source inventory**, up from
the installer's 222-file baseline. The three build/make edits, device tree,
recovery/mi_ext input records, metadata bundle and reviewed vendor/ODM leaf bundle
are now selected in source. Working76 and mi_ext image bytes, the 269 preserved
outputs, thirteen policy files and eleven runtime files remain unchanged.
Independent transaction review is clear. No component build, sidecar production
or target-files result is claimed by that transaction. Construction and pinned-date
source were not yet selected at that checkpoint; the later transaction follows.
Scoped VINTF/crypto limits, 4 KiB settings and false ROM-readiness flags remain in force.

The **construction/0012 source transaction commits at 08:45:28 UTC**: one device
tree exchange and two vendor/lineage file exchanges, with **nine events and 478
source files/modes across twelve projects**. Its four-file readback preserves
the staged record and prior outputs. Independent review confirms the recorded
transaction without reopening live source or archives. Construction
and date source are selected, but native dispatch and the configuration delta
remain unadmitted; no generated `BUILD_NUMBER`, sidecar, target-files or build
success follows. The original guard's direct `TARGET_RELEASE` access is a
source-order finding, not a failed native attempt. A **one-file correction
commits at 09:17:15 UTC**, with five journal events and an eight-file readback
retaining both original preimages. Exactly one of 478 source identities changes;
the twelve project records, strict settings and prior outputs remain unchanged.
Independent correction review binds the captured guard and recorded source
vector without reopening live source or archives. Twenty-three host preparation tests
pass, but normal Kati/build execution remains unverified. The three ordinary
sidecar modules and final policy hook remain required.

The reviewed ordinary-product input closure binds **1,475 unique inputs** and
derives a deterministic build identifier; this is selected-input metadata, not
generated product metadata or reproducible-image proof. The first three
configuration attempts stop before native invocation: a source-history field
alias error, then two inherited `OUT_DIR` conflicts, the latter persisting after
the container environment override. Their failed receipts remain preserved.
The fourth attempt reaches native dumpvars and fails at **10:17:52 UTC** because
`BUILD_DATETIME` is obsolete; the error directs callers to
`BUILD_DATETIME_FROM_FILE`. All six source/input guard sets match before and
after, the seven metadata/log preservation copies verify, and no images are
invalidated. Both occurrences of the existing kernel-origin/AVB warning remain.
The later corrected queries retain this failed receipt.

The corrected native **config5** and **context5** queries finish successfully at
**10:40:19 and 10:45:23 UTC**, checking 21 and seven selected values. Both six-part
source/input guard sets and the full generated configuration remain unchanged.
The three `FROM_FILE` results are literal references, not file-content proof;
six metadata files and their freshness required separate ordinary-phase evidence.
Independent reviews
of both queries are clear within their selected-value scope.
The two existing kernel-origin/AVB warnings remain in each query. No Ninja
actions, effective partition properties, images, sidecars or target-files are
verified by these queries.

The **nothing1** native command finishes at **11:09:02 UTC** with exit 0, but the
overall attempt returns exit 1. `verify_source_history` and
`verify_strict_settings` both reject a generated Soong configuration that differs
from the exact reviewed phase state. Four after-admission entries match, but the
archive entry is cached alongside the stale source-history observation. Only
selected-input, source-lock and protected-input checks are fresh; this is not a
fresh full source/archive proof. The metadata postcheck does not run, and no six-file
success is claimed. The result and raw logs are preserved while the configuration
change was investigated; that failed result is not relabelled by the later pass.

A source-bound explanation now accounts for all seven changed leaves in the
complete 254-key configuration. `LINEAGE_BUILD` selects additional Evolution
policy, changes conditional package/copy lists and exports the already selected
4 KiB maximum. This is exact source-derived admission, not a general mismatch
exception. The **nothing2** retry finishes at **11:44:57 UTC** with native and
wrapper exit 0. All six current source/input guards run freshly and match, and
all six captured metadata values verify, including the selected build number.
Fresh confirmation rehashes the result and six files; independent actual review
is clear. File rewrites/freshness, effective partition properties, image and
target-files results remain unverified.

Commit **3c9cd2a** adds the [recovery-only backuptool guard](evolution-backuptool-enforcing.md).
Patch 0015 wraps the existing permissive declaration in `recovery_only`, without
changing types, permissions or assertions. The component transaction now installs
its reviewed postimage; complete strict policy verification remains pending.
Working76 is unchanged.

Commit **5d557a0** adds an explicit Evolution-base option without changing the
default generator path or the 4 KiB selection. Its independent source review
is clear. The host preparation reproduces all **57 files / 6,204,545 bytes**,
including the receipt; relocated trusted controls give the same verification
result. All ten classification inputs and thirteen factory contexts remain
unchanged. The reference uses normal Android M4/compiler/mapping producers and
separately checks the owned policy contribution; it does not edit generated CIL.
The first 32-goal invocation stops before policy compilation; the second reaches
the strict compiler but fails. Complete unfiltered analysis of the twelve normal
binaries remains unverified. Seven base property-prefix specializations still require actual label
and permission-effect review, and selected vendor-source contributions have
not been delivered into the retained factory images.

The component installation retains 54 independent source preimages and 21
policy-output archives, including eleven existing copies and ten new copies.
The nine-event journal ends in `commit_verified`; source/mode vectors, strict
4096 settings and the complete prior configuration pass the recorded checks.
The first read-only preflight rejected a dated OEM report. Exact comparison
traces its 66 stat-field changes to the earlier matrix producer, with semantic
fields unchanged; both report versions and the failed attempt remain preserved.
The corrected preflight and installation admit source changes and retention
only, without a new policy, metadata, image or boot result.

The **first-target-files-policy-1** invocation runs from **14:01:11 to 14:02:13
UTC** and exits 1, as does its wrapper. All six source/input guard groups pass
before and after, including 1,525 named inputs and the runtime input. Eleven
prior outputs are preserved and renamed for regeneration; this is not an
unchanged-output claim. Bootstrap Ninja runs, but the required main-Ninja
observation is not obtained. The policy postcheck never runs and there are no
postcheck errors. The failure, raw logs and original source installation remain
preserved; no new policy or metadata success is inferred.

The subsequent visibility transaction changes only the device filegroup
Blueprint, its private provenance copy and the policy receipt. It uses Soong's
required `//vendor:__subpackages__` form without changing SELinux sources or
permissions. Three operations and nine journal events commit the correction;
three original preimages, the eleven policy1 output archives and ten other live
outputs remain verified. The host code review and the separate actual receipt
replay are clear. This is not a new Soong/policy pass or a successor
build-identity/metadata result.
The separate host metadata successor now derives
`nezha.9c8ecb23e876fcf464a02e1d`; coordinator replay verifies all fifteen bound
files and nine identical outputs. Native input rechecks and six-file metadata
qualification were pending at that host checkpoint. The second native attempt
selects this identity and passes the input guards, but does not qualify the six
post-make metadata files.

The **first-target-files-policy-2** invocation runs from **15:13:37 to 15:28:07
UTC**, with native and wrapper exit 1. Main-Ninja argv, sandbox and resource-limit
verification pass, along with all six fresh source/input guard groups. The sole
reported failed target is `nezha_factory_precompiled_sepolicy`: the diagnostic
binds factory `plat_pub_versioned.cil:6117` to Evolution `public/property.te:2`.
No policy postcheck runs; its error list is empty, and there is no timeout or
forced kill. All eleven retained policy1 originals and their independent copies
remain verified. A later read-only snapshot now finds **eleven present and ten
absent outputs** in the tracked 21-file set; five present files differ from the
dated bytes/modes and six match. This is observed state, not producer freshness
or policy success. The original Soong failure remains preserved;
no new combined-policy, six-file metadata, image or boot success is claimed.

Patch **0016** gates only the `vendor_init` camera-property set grant, preserving
the type, reads, socket permissions and assertions. It remains a committed,
host-qualified source input. A separate diagnostic on the failed policy2 CIL
and contexts finds lost camera-service/HAL reads and HAL writes, USB access
losses, and wider Dolby reader access under seven changed labels. Application
domain camera reads remain present in that diagnostic. These are static policy
effects, not observed hardware failures. Committed patch **0017** suppresses
only the seven Evolution prefix rows when explicitly selected, preserving
factory labels and the default source path. Its host M4 fixtures pass 48 valid
and 22 expected-invalid cases; these are not Android M4 or native context checks.
The paired integration verifies exact definition/override guards and repeats
the **63-file / 6,265,781-byte** private bundle. All original CIL and factory
context bytes remain unchanged. The later source transaction now installs both
corrections, preserving 90 independent source preimages, copies of all eleven
present partial outputs and the ten then-recorded absences. The subsequent
policy3 source build passes, including the previously failing combined-policy
target. Scoped actual source/M4 and five-context review now verifies the seven
complete prefix regions: all 55 baseline camera readers and both writers remain,
with only three expected Evolution app readers added; audio/USB ordinary edges
do not change. The two duplicate service-context diagnostics remain warnings.
All twelve unfiltered binary checks pass separately, without implying strict
neverallow compilation for every upstream compatibility binary. The public-name
freeze is verified, while full recursive graph provenance and final installed-APK
Treble labeling remain separate. All three ordinary policy-sidecar generators
and installs ran in policy3. Their later read-only qualification now verifies
the three installed 65-byte outputs against six ordered CIL/mapping inputs,
three exact recipes and recorded producer/copy actions, without new native
generator execution. The original failed capture remains preserved.

The new `policy3-evolution` profile permits exact evidence validation and TAR
preparation for this snapshot; the three earlier profiles and blocked historical
default remain unchanged. Its native reconstruction now passes **nine checks and
38 commands with zero skips**. Independent review compares all 6,969 entries in
both passes: exactly one vendor and four ODM policy payloads change, while other
contents and semantic metadata are preserved. The 97-file capture is complete;
large TAR/image outputs remain in the guest and were not reopened by the host
review. The separate footer run completes at **23:33:34 UTC** with **six checks,
sixteen top-level commands and zero skips**, plus twelve nested FEC calls.
Independent review verifies raw-prefix preservation, regenerated parity and
identical repeated NONE leaves within the exact package budgets. This does not
establish physical partition fit or a signed parent chain. At that footer-only
checkpoint, delivery/adoption and boot remained unverified, with original images
and the 539-file source unchanged; the later source selection is recorded below.

Commit **4505222** adds explicit policy3 delivery/construction-source support.
The independent private image copies and inactive four-file image-source
candidate pass their recorded native checks and independent reviews. The later
three-tree adoption stage fails at **2026-09-01 00:43:45 UTC**, before creating
its candidate. A separate read-only post-failure proof retains all 539 source
files across thirteen projects and the current configuration. It records
**165,301,895,168 bytes available**, below the unchanged requirement of
**226,459,516,499 bytes**: a 200 GiB reserve plus 11,711,151,699 bytes of copies.
At that failed checkpoint, the prospective 537-file source was not installed.
No image-goal or target-files build had run from it. The earlier successful
inactive stage remains separate.
This failed capacity check is preserved; subsequent maintenance clears that
specific storage gate without adopting the candidate.

At **2026-09-01 02:14:58 UTC**, the existing source volume is qualified at
**1,024 GiB**, with **402,047,229,952 bytes available** against the unchanged
226,459,516,499-byte staging requirement. At that checkpoint, the original
800 GiB image and volume metadata were retained through APFS clone/swap, **not an independent physical
backup**. The initial preen exit 1 remains a failed attempt; separate confirmation,
growth and postcheck each return native exit 0. Complete raw-image hashes and
post-restart checks bind the retained original, current 539-source/thirteen-project
proof, strict 4 KiB configuration and inactive staged inputs. The same builder
is the sole observed volume user. This maintenance is not an Android build,
source adoption or ROM/boot proof; see the [environment details](apple-container.md)
and [bounded maintenance evidence](../research/workspace-integration.json).
The old raw snapshot was subsequently removed with explicit approval at the
[September 2 host-cleanup checkpoint](storage-cleanup.md); its small maintenance
evidence and the current 1,024 GiB volume remain preserved.

The later **source-v2 transaction commits at 02:37:56 UTC** and returns native
exit 0 at **02:38:56 UTC**. It exchanges the device, target-files metadata and
policy-image source trees, verifying **537 source files/thirteen projects** and
preserving fourteen policy plus eleven runtime outputs. Independent actual
review binds all three operations and nine journal events. The exact Camera JNI
0711 archive exception leaves the original bytes, mode and inode unchanged;
the failed prior stage is not selected. All **205 metadata payloads retain their
bytes and roles**, but their new private source copies use declared mode
**0600**, while retained originals use **0644**. Subsequent identity reprojection
verifies that declared distinction, with no source chmod. Current
strict 4 KiB settings and normal Android enforcement remain required. Selected
source inputs are now active, but no new output images, packaged-policy checks
or target-files have been built from them. The
[installation and audit record](../research/workspace-integration.json) also
binds the preceding **02:24:28 UTC** source audit: all **1,179** revisions and
origins match, with seven reviewed modified projects preserved.

The new identity **`nezha.8643b579050aab0dd3218ae3`** is independently reconstructed
from the authenticated source/metadata records and selected by both actual
product queries. **Config6 passes at 02:51:15 UTC** and **context6 at 03:01:01
UTC**, returning 21 and seven checked values respectively. Both native processes
exit 0 with complete streams, verified postchecks and clear independent reviews.
All six before/after source/input guard maps match, including the 537-source,
thirteen-project scope and unchanged 254-field generated configuration. The three `FROM_FILE` values
remain literal references; the build number is bound through the actual invocation
environment, not directly printed by the queries. Neither Ninja nor a new image
build is required or observed. Each query retains the two kernel warnings for
`AVB=failed` and `origin_verified=false`. Those queries alone do not establish
six-file metadata, packaging, signed-chain or boot success.

The subsequent **ordinary `nothing3` run passes at 03:22:47 UTC**, with native
exit 0, completed postchecks, six matching source/input guard maps and clear
independent review. The six actual metadata-file contents match `nezha.8643b579050aab0dd3218ae3`; this is a
value check, without inferring that all files were freshly rewritten. Across
the 254 generated configuration fields, only `NamespacesToExport` changes,
from eight to ten entries for the two approved QTI paths. The log contains
166 frontend steps and one `nothing` phony target, not 167 tests. Ninja and its
sandbox are observed, but this profile does not require or verify exact Ninja
arguments; its automatic `-j19` is not component-build qualification. Four
kernel AVB/origin warnings, the prebuilt-kernel banner and two namespace UID/GID
warnings remain preserved. The 537-source/thirteen-project input and protected
records remain verified, while graph/configuration/metadata writes are allowed.
Subsequent read-only capture covers four image goals and three policy sidecars,
with independent review of the outer 537-file/thirteen-project source guards and two
Ninja queries. Separate review binds exactly two identical recovery goal/leaf
command declarations. Nine proof records are staged without image bodies or
private keys. These preparation records do not establish producer execution.
The later **images1 native invocation exits 0 at 04:26:42 UTC**, but its
**wrapper remains failed** because the combined Ninja graph changes. Independent
review finds only `highmem_pool` depth 15 to 8, consistent with the pinned
generator and observed `-j8`; the old graph body is reconstructed to its sealed
hash, not independently captured. All six admission maps, 254 configuration
fields and the other fifteen graph contents match. The original failed receipt
is preserved. A **separate read-only postcheck passes at 05:03:29 UTC**: the four
output images match their selected source copies, the three framework sidecars
are recomputed and match the ODM basis, and all seven fresh producer actions
are tied to the recorded commands and log rows. This qualifies output production
separately from the earlier source-image reconstruction. It performs no new
build or source/output writes. The saved receipt matches the actual result,
and independent artifact review now passes. Its sidecar-to-ODM join uses the
selected delivery entries and prior raw-image/footer evidence, without new host
image extraction. This root-context verifier does not establish a new read-only
mount namespace. Target-files and the packaged metadata hook are not verified.

The first optional AIDL capture's 8 MiB query-bound failure is preserved. Its
v2 successor completes reviewed, scoped read-only capture of 1,163 nodes,
753 declarations and 62 API-check descriptions through 74 query and eight
command-list calls. Those captures do not execute component checks. Protection
covers exactly three policy sidecars, sixteen graphs/four logs and six outer
source/input callbacks; it does not establish seven protected image outputs.
The review retains 1,996 frontier groups outside the fixed scope; this is not
full dependency closure.

The subsequent **AIDL component v4 build passes at 05:34:01 UTC**, with native
and wrapper exit 0. Its 341 main Ninja actions follow one bootstrap step; they
are not workspace tests. The postcheck accounts for 70 selected outputs:
**38 fresh actions and 32 reused display-config checks**. The host metadata
auditor and seven NDK backends compile, but the auditor has not run. Source
inputs and current recovery/mi_ext are preserved; this component callback does
not establish preservation of current vendor/ODM output images. Independent
review of the complete captured action logs and all 70 outcomes passes. Auditor execution, full definition coverage,
target-files, signing, super/OTA and hardware checks remain separate gates.
See the [actual build and review records](../research/workspace-integration.json).

After a host restart, the
coordinator resumed only the existing stopped builder. The **22:50:26 UTC**
read-only verification records it as the sole source-volume writer, with the
same 539-source/configuration proofs, case-sensitive ext4, about 211 GiB free
and working Rosetta Ninja. No replacement VM or source sync was started.
This is a dated environment check, not a new Android build or phone test.

Commit **76fe975** adds the [unlevelled-matrix AIDL name audit](../tools/vintf-definition-audit/README.md).
Its host tool is now compiled and linked; execution remains pending. The
historical read-only discovery of policy2 artifacts and host replay
find **149 of 155 matrix tuples / 134 of 140 names absent from all 336 captured
metadata modules**. The generated C++ is reproduced byte for byte from the
captured JSON on the host; that does not prove native producer execution or
linkage. Export filtering means metadata absence is not proof of source absence.
This exposes a definition-coverage gap without changing production `checkvintf`,
removing its retained skip or inventing interface definitions. Complete VINTF
compatibility remains unverified.

Commit **9f0c8bd** separately adds an optional, explicit
[Qualcomm AIDL namespace contract](../config/nezha-qti-aidl-namespaces.json) and
generator support. The source-v2 device configuration now selects the two
recorded namespaces; it does not select new runtime services. The native input
guard verifies 666 regular files, one explicitly declared namespace alias and
thirteen required project HEADs. This does not
compile metadata/APIs/backends or close the definition-coverage gap; runtime
support remains unverified.

The earlier **policy-images-export4-v1** native reconstruction passes
**nine checks and 38 commands with zero skips**. Both independent TAR/image/export
sets match, with exactly one vendor policy file and four ODM files changed;
all other contents and semantic metadata are preserved. Independent review
reparses all six complete manifests and verifies the 97-file host capture and
77 staged packet files, with no findings. This qualifies the raw five-file
derivation for sealed v12/export4
inputs; it does not adopt those images, validate current source, regenerate AVB/FEC,
establish partition fit or prove a kernel mount or boot.

The earlier **v12e** integration was installed into the existing guest source at
**22:10:41 UTC**. It adds the four OEM property sources, exact Camera runtime
inputs and their Soong patch, factory `mi_ext`, and the A/B recovery/custom-image
packaging patches. Its first native policy attempt failed at **22:19:27 UTC**
in Kati: `build/make/core/Makefile:4776` reads the undefined
`BOARD_MI_EXT_IMAGE_NO_FLASHALL`. No policy compiler or context-check action ran
in that attempt. The [native ROM integration record](native-rom-integration.md)
binds the successful installation and failed build separately. The correction
passed all **99 native Kati fixture cases**, including the reproduced original
failure, then was installed as **run-v12fa** at **23:22:28 UTC**. Its seven
changes include the corrected C source, while retaining the property policy
bundle and original images. The actual v12f retry now passes; the v12e failure
and earlier stage-only run-v12f remain preserved. **components-v12f-1 passed at
02:03:33 UTC**, after 102 minutes 20 seconds, with unchanged source inputs and
verified sandboxing. All eleven installed outputs were captured and inspected:
the nine Camera runtime payloads match their inputs, and recovery/mi_ext retain
their exact expected bytes. The bounded producer review verifies four fresh
DEX invocations and matching installed ODEX/VDEX outputs, the fresh JNI checks
including 16 KiB alignment, a fresh guarded working76 copy, and fresh mi_ext
NONE-footer/hashtree verification. The coordinator reproduced the review receipt
byte for byte. Native checkers were not independently replayed, and complete
checker-input recapture and runtime API validation remain separate. No Camera
APK was built, and this is not a complete ROM, signed-chain or boot result.

Commit **4070b1a** adds the [construction-prerequisite consumer](rom-construction.md).
That initial unbound consumer reports five missing selected-input roles and
refuses explicit generation before private-input reads or candidate publication.
The later explicit source transaction selects the construction guard; it does
not itself admit native dispatch or a completed build. Final compatibility coverage remains distinct from a runner's
outer success field and from artifact/device admission.

Commit **203ab67** adds the inactive [ODM-import care-map successor](mi-ext-care-map.md).
It binds all 22 original ODM property files and resolves the exact captured
imports without skipping arbitrary imports or changing original properties.
Native codec/tool qualification, the final Evolution SYSTEM identity and
ordinary packaging remain unverified; this care-map source capability remains inactive.

Commit **a253c97** adds the [read-only target-files AVB inventory](target-files-avb-inventory.md).
Its 42 new synthetic tests cover bounded archive/role inspection and failure
handling. It separates final image entries, generated vbmeta outputs and the
two retained firmware inputs; it does not extract, validate or sign images.
No actual target-files archive has been admitted with this helper.

Commit **1ef9bf3** promotes the maintained
[signed target-files reconciler](signed-target-files-reconciliation.md) and
streaming archive copier with 72 synthetic tests. They preserve an original
archive while integrating an already verified signed image set; the helper
itself does not sign. No actual target-files archive, signing operation or
reconciliation run is established by this tooling milestone.

Commit **0f09135** adds the maintained
[target-files input materializer](target-files-materialization.md), with 44
synthetic tests. It copies thirteen selected ZIP images and two retained inputs
into the existing signing-manifest format; no actual materialization has run.
Its persisted receipt verifies only the checkpoint before publication. A
successful API return or CLI exit 0 is required to establish publication, and
later reconciliation must use the signer's normalized-manifest digest rather
than the earlier materializer-manifest digest. This is preparation for actual
archive handling, not image, signing or boot validation.

The last full workspace suite recorded before this milestone passed **4,305
tests in 202.826 seconds with zero failures, errors or skips**, against `aa93e72`
plus the three unchanged materializer files, then committed as `0f09135`.
This later package-progress/materializer checkpoint is outside that offline run.
The preceding suite passed **4,261 tests in 179.563 seconds with zero failures,
errors or skips**, against `d072d06` plus the four unchanged AIDL/image-review
documents, then committed as `aa93e72`.
The preceding suite passed **4,261
tests in 193.210 seconds with zero failures, errors or skips**, executed by the
coordinator against `4dad41f` plus four unchanged image/AIDL-capture documents,
then committed as `d072d06`. This later artifact-review/component-build update
is outside that offline run; native evidence remains separate.
The preceding suite passed **4,261 tests in 204.808
seconds with zero failures, errors or skips**, executed by the coordinator
against `1ef9bf3` plus the four unchanged preparation documents, then committed
as `4dad41f`. This later image-attempt/AIDL-capture documentation is outside that
offline run; native execution and artifact validation remain separate evidence.
The preceding suite passed **4,261 tests in 192.570
seconds with zero failures, errors or skips**, executed by the coordinator
against `d5e9305` plus the five signed-target-files tooling files, then committed
as `1ef9bf3`. All five identities remained unchanged. This later preparation
documentation is outside that offline run; synthetic cryptography tests are not
native signing evidence.
The preceding suite passed **4,189 tests in 172.558 seconds with zero failures,
errors or skips**, against `e6a0a63` plus the three unchanged `nothing3` documents,
then committed as `d5e9305`.
The preceding suite passed **4,189 tests in 178.577
seconds with zero failures, errors or skips**, executed by the coordinator
against `f99a944` plus the three query documents, then committed as `e6a0a63`.
All three bound document identities remained unchanged. This later `nothing3`
documentation and its native results are outside that offline suite.
The preceding suite passed **4,189 tests in 172.826
seconds with zero failures, errors or skips**, executed by the coordinator
against `f875980` plus the three source-adoption documents, then committed as
`f99a944`. All three bound document identities remained unchanged. This later
query documentation and the native query results are outside that offline run.
The preceding suite passed **4,189 tests in 178.752
seconds with zero failures, errors or skips**, executed by the coordinator
against `ab083ee` plus the four maintenance documents, then committed as
`f875980`. All four bound document identities remained unchanged. This later
source-adoption documentation update and the native installation are outside
that offline run; neither is counted as a workspace test.
The preceding suite passed **4,189 tests in 168.608
seconds with zero failures, errors or skips**, executed by the coordinator
against `e6bb4e7` plus eight integration files, then committed as `4505222`.
All thirteen bound identities remained unchanged. The interrupted v1 run is
preserved as a non-pass; its whole-workspace-copy fixture was corrected to copy
only declared controls. This later documentation update and native adoption
attempt are outside the offline suite.
The preceding suite passed **4,162 tests in 167.578
seconds with zero failures, errors or skips**, executed by the coordinator
against `9f0c8bd` plus the four raw-image checkpoint documents, then committed
as `7c8c27e`. All eleven bound document/code/config/test identities remained
unchanged. This later footer/test-record update is outside that run; native
footer evidence is recorded separately from the offline suite.
The preceding suite passed **4,162 tests in 165.342
seconds with zero failures, errors or skips**, executed by the coordinator
against `4335f1b` plus the four then-current checkpoint documents and three
namespace files; the three namespace files were subsequently committed as
`9f0c8bd`. All eleven bound file
identities remained unchanged, including the four committed image-profile files.
This later raw-image/test-record documentation update is outside that run;
offline tests do not establish native image or hardware success.
The preceding suite passed **4,146 tests in 161.125
seconds with zero failures, errors or skips**, executed by the coordinator
against `6f504fa` plus the exact four image-profile files, then committed as
`4335f1b`. All four files remained unchanged. This later central-document update
and any subsequent source work are outside that recorded run; it does not
qualify native image reconstruction or hardware.
The preceding suite passed **4,115 tests in 175.932
seconds with zero failures, errors or skips**, executed by the coordinator
against `5204366` plus the exact eleven frozen 0017/integration files, then
committed as `7c22c82` and `641af6a`. All eleven files remained unchanged. This
tests the completed paired source implementation; it is not a guest installation
or Android policy build. This later central-document update is separate.
The preceding suite passed **4,055 tests in 171.878
seconds with zero failures, errors or skips**, executed by the coordinator in
an **isolated snapshot** of `fdc9b1e` plus the exact seven committed 0016/audit
files, equivalent to `76fe975`. The seven then-ongoing integration-file changes
were excluded; that run was not a full test of the working tree or a native
build of the audit tool. Its later documentation update was separate.
The preceding suite passed **4,043 in 169.370 seconds**, with
two source-correction files and four checkpoint documents unchanged. The source
bytes are committed as `30a9f74`; this later factual test-record refresh is
separate. The preceding suite passed **4,043 in 169.140 seconds**, with
all ten frozen Evolution-base source files unchanged, then committed as
`5d557a0`. This later central-document update is separate. The preceding suite
passed **3,984 in 168.104 seconds**, executed in an
**isolated snapshot** of `ee2d19db` plus the four frozen backuptool files,
equivalent to commit `3c9cd2a`. Other then-in-progress root policy edits and its
later documentation update were excluded from that isolated run. The preceding working-tree suite passed
**3,972 in 169.113 seconds**, with all three checkpoint documents unchanged;
its subsequent factual test-evidence refresh is separate. Its earlier v1 launcher
failed preflight before running tests and contributes no skipped-test count.
The preceding 3,972-test run took 168.418 seconds and retained its three
product-input checkpoint documents. The earlier
3,972-test run took 166.208 seconds and retained its eight construction-source
checkpoint files. The preceding 3,961-test run took 171.407 seconds and retained
its three packaging-source checkpoint files.
The earlier 3,961-test run took 166.023 seconds and retained its three-file
scoped VINTF checkpoint. The earlier 3,961-test run took 165.776 seconds and retained its three-file
provider checkpoint. The earlier 3,961-test run took 167.201 seconds and retained its five-file
checkpoint. The earlier 3,961-test run took 173.222 seconds and retained its
seven-file checkpoint.
The earlier coordinator run passed
**3,919 tests in 164.329 seconds**.
All four checkpoint files stayed unchanged throughout that run and were then
committed as `4116868`. The preceding matrix-owner run passed **3,919 in
164.103 seconds**.
The five frozen public files match `c3686ed`. Executable controls and tests
stayed unchanged during the run; the dedicated matrix guide gained host evidence
details during it. This is host source/projection coverage, not native matrix
or APEX cryptographic verification. The preceding suite passed **3,892 tests in
164.280 seconds**, executed by the care-map owner
and independently log-verified by the coordinator. It covers `4070b1a` and the
four care-map files committed unchanged as `203ab67`; later matrix source work
is not included. The preceding suite passed **3,854 tests in 172.911 seconds**,
executed by the construction
owner and independently log-verified by the coordinator. It covers the five
construction files committed as `4070b1a`, but excludes the concurrently
authored 0014 care-map tests; a combined coordinator rerun remains pending.
The preceding coordinator suite passed **3,835 tests in 166.748 seconds**,
covering all seven delivery
successor files subsequently committed unchanged as `137f438`, on parent
`8fc2162`. The preceding coordinator run passed **3,795 tests in 163.444
seconds**, on committed `17cde61`, with these checkpoint documents then
uncommitted. The preceding
page-size integration owner run passed 3,795 in 143.328 seconds; the coordinator
independently rehashed its full log. All six frozen public files match the
commit. The preceding coordinator suite passed **3,778
tests in 157.969 seconds**, covering the ten maintained delivery files before
their commit as `e304faa`. The preceding Camera
metadata/capture and private-copy checkpoint passed 3,711 in 154.009 seconds.
The preceding allocator component checkpoint
passed 3,711 tests in 152.316 seconds. An earlier 3,711-test run passed in 158.487 seconds, covering the optional
[mi_ext care-map source path](mi-ext-care-map.md), committed as `8144704`.
That capability is inactive: authentic ODM imports and the final Evolution
SYSTEM property input still require qualification. The preceding allocator
suite passed 3,665 in 156.924 seconds. The previous suite passed 3,651 in
156.391 seconds, executed by the
target-files metadata agent;
the coordinator independently verified its complete log. The separate previous
coordinator run passed 3,651 in 160.426 seconds after the raw-image milestone.
Those earlier runs used unchanged public code from the profile run, which passed 3,651
tests in 158.950 seconds at `78376c7`. The preceding v13ha integration
run passed 3,634 in 152.111 seconds. The previous v7 run passed 3,634 in
156.509 seconds, and the previous profile
checkpoint passed 3,591 tests in
152.682 seconds. The earlier coordinator component
checkpoint passed 3,558 tests in 163.269 seconds; the separate page-size agent run
passed 3,558 in 153.985 seconds. These are offline tooling results, separate from
Android builds, host policy proofs and physical-device tests. This checkpoint records
code through `a253c97`, with the previous component checkpoint committed
as `8fc2162`, followed by `da9648b`, `3001e85` and `4116868`. The active
guest source is now first-target-files-release-flags-v1 with the 4 KiB product unchanged. Its
first target-files build remains pending; the latest verified component outputs are from
matrix-v1, with the failed wrapper and distinct passing postcheck/review preserved;
`analysis-v13h-policy-only-v1` remains the latest verified policy baseline for the
earlier source selection.

The immediate destination remains a reproducible, working Evolution baseline;
that baseline will support a maintainable platform fork without mixing future
framework features into device bring-up.

The observed phone reports `nezha` and CN hardware-country information. Its
physical sales region is not independently established. During the authorized
August 29 tests, the bootloader positively reported `unlocked: yes`,
`secure: yes`, slot `a`, and 100 MiB recovery slots, despite Android properties
reporting a locked state. Use the [bootloader observations](../research/twrp-boot-attempts.json)
for that checkpoint; older unresolved-bootloader statements are historical.
Recheck the selected device before a future authorized operation.

## Build baseline and provenance

| Input | Selected baseline and evidence |
| --- | --- |
| Platform | Evolution `bka`, manifest `cc4ebb8db9750afba6049825127304b09327f7c1`, release configuration `bp4a`; [source selection](../config/sources.json) |
| Project revisions | [Resolved 1,179-project snapshot](../research/source-snapshots/evolution-bka-20260827.xml), SHA256 `a7b9b5aec7f07a4d351771dbb834f4c4561c26564c7292930409f3f5968edeac`; [source verification](../research/source-sync.json) |
| Product | Authored `device/xiaomi/nezha`, `lineage_nezha-bp4a-user` and `userdebug`; ARM64, 4 KiB kernel pages, shipping API 36, board API `202504`; [generation contract](../device/xiaomi/nezha/README.md) |
| Kernel and modules | Exact stock-prebuilt Nezha bundle, with its original Xiaomi.eu provenance retained; [kernel wrapper](../kernel/xiaomi/nezha/README.md), [factory comparison](../research/factory-input-reuse.json) |
| Vendor/ODM | Reviewed factory-named `OS3.0.309.0.WPACNXM` archive, SHA256 `d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`; [factory intake and validation](factory-firmware-validation.md) |
| Recovery | `working76`, SHA256 `a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e`; [working-image contract](../research/twrp-working-defaults.json), [build and handling instructions](../recovery/twrp-working/README.md) |

The manifest commit alone does not lock every project: its upstream entries
include branches. The [reviewed source-lock workflow](source-lock.md) now uses
the exact resolved snapshot for fresh initialization and sync. It never
converts an existing selector or resets local changes. `make source-check`
audits existing HEADs, remotes and worktree state against that lock. The earlier
August 28 audit matched all 1,179 HEADs/remotes, with 1,176 clean projects and
three expected patched projects; see [build progress](../research/build-progress.json).
The [August 29 integration audit](../research/workspace-integration.json) again
matched all 1,179 HEADs/remotes, with 1,175 clean projects. The fourth patched
project is now `build/make`, for the verified prebuilt-recovery consumer. The
audit deliberately returns status `2` for those local changes; it does not
reset them or describe the checkout as pristine. A source lock does not
include the remaining build inputs below.

The [v11 preflight](../research/oem-policy-integration.json) rechecked all
1,179 revisions and origins at 19:37:51 UTC, with 1,175 clean projects and the
same four patched projects. The [v12e installed-source audit](../research/native-rom-integration.json)
again matches all 1,179 revisions and origins, now with **1,174 clean projects
and five reviewed patched projects**: `build/make`, `build/soong`, `system/core`,
`system/sepolicy` and `vendor/lineage`. The fifth project carries the strict
DEX uses-library provider patch. The v12fa installation reconfirmed those same
counts; its successful v12f build verified the corrected inputs unchanged.
The v13ha snapshot still matches all 1,179 revisions and origins, with **1,173
clean projects and six reviewed modified projects**. The additional project is
`external/mdnsresponder`, carrying the scoped provider visibility change.
The successful v13h build verifies its 182 selected source files unchanged.
The v13i preinstallation audit reconfirms all 1,179 revisions/origins and the
same six modified projects; its device selection changes no project source.
Neither source verification nor a successful input
transaction is a component-build result.

Those local changes are part of the build inputs: the
[Evolution property patch](../patches/evolution/security-properties.json),
[SELinux enforcement patch](../patches/evolution/selinux-enforcement.json), and
[init property patch](../patches/evolution/init-boot-properties.json), together
with the [prebuilt-recovery consumer](../patches/evolution/prebuilt-recovery.json),
the [A/B recovery correction](recovery-packaging.md),
[direct-root custom-image integration](mi-ext-inputs.md),
[DEX provider correction](dex-import-uses-library.md),
the [scoped helper capability](policy-source-integration.md), authored
device/kernel sources and hash-bound private vendor bundles. The helper patch
is applied in the existing `system/sepolicy` project; the additional v12e
project is `build/soong`. The snapshot alone does not include these changes.
Factory archive origin and OEM
trust remain unauthenticated; passing internal AVB checks does not authenticate
the archive. Matching factory bytes do not relabel the older kernel bundle.

The verified local host route is Apple Container ARM64 plus Rosetta, with
`/work/evolution` on the persistent ext4 volume `evolution-nezha-work`.
Native Linux x86-64 is also supported by the workspace preflight. Recheck host,
disk, architecture, case sensitivity, source pins and volume ownership before
work; never attach the same volume to concurrent writer VMs. Preserve source,
output and cache. The [build-host guide](build-host.md) and
[container workflow](apple-container.md) distinguish component-build evidence
from a full build and require destination hash verification after transfers.

## What has actually passed

| Validation level | Result | Primary record |
| --- | --- | --- |
| Native source configuration and modules | User/userdebug product checks; ARM64 `libbase.so`; nine selected Camera dependencies, including four JARs with ODEX/VDEX; host VINTF and policy tools | [Build progress](../research/build-progress.json) |
| Native component builds and inspection | Boot, DTBO and both DLKM images in the recorded userdebug snapshot; factory-based user v8 init_boot, vendor_boot and DTBO preserve admitted DT/module/fstab inputs | [Boot/DLKM](../research/boot-dlkm-build.json), [factory boot](../research/factory-boot-build.json) |
| Native user v9 source policy | DSP membership integrated through Soong; both source-policy binaries have zero permissive domains | [DSP source build](../research/dsp-policy-build.json) |
| Strict policy prototype | Derived Binder correction plus two helper-permission removals compile as combined CIL with zero permissive domains; all 6,366 assertions retained | [Helper projection](../research/helper-policy-projection.json) |
| Native user v10 source and factory policy | The reviewed helper patch now runs through Android M4; a native genrule reproduces the Binder correction and the strict combined policy target builds successfully, including its user permissive-domain guard | [Source integration](../research/policy-source-integration.json) |
| Independent v10 analysis | Native combined binary matches the earlier prototype exactly; all 6,366 assertion statements remain, with only the intended 69 allow removals; three binaries have zero permissive domains | [Source integration](../research/policy-source-integration.json) |
| Native user v11b OEM policy | Authored system_ext declarations, object roles and generated API mappings; strict combined compilation, OEM ownership guard and all nine factory context/structural checks pass | [OEM policy integration](../research/oem-policy-integration.json) |
| Independent v11b analysis | All 6,366 assertions retained with reviewed concrete coverage; exactly five added lookup permissions and 47 removed vendor_init file permissions; zero permissive domains in three binaries | [OEM policy integration](../research/oem-policy-integration.json) |
| v12e source and private-input installation | Durable ten-operation transaction; pinned sources and exact installed inputs verified; original vendor/ODM, kernel and working76 bytes preserved | [Native ROM integration](../research/native-rom-integration.json) |
| v12fa correction installation | Seven committed exchanges, exact corrected source and receipt identities, same pinned project bases and preserved original image inputs | [Native ROM integration](../research/native-rom-integration.json) |
| v13f provider input installation | Four committed exchanges verified; original vendor/ODM, Camera runtime, mi_ext and working76 preserved; provider policy build and independent verification remain separate | [Native ROM integration](../research/native-rom-integration.json) |
| v13ha correction and native policy verification | Three exchanges commit; 31 native goals pass; analysis retains 6,370 assertions, exact reviewed effects and three zero-permissive binaries; runtime and image adoption remain open, with later 4 KiB ELF evidence separate | [Native ROM integration](../research/native-rom-integration.json) |
| v13i allocator installation and component build | One device-tree exchange commits; 37 goals complete with fresh allocator actions and three inspected outputs; partial VINTF has an explicit skipped subcheck, and exact producer/full compatibility checks remain open | [Native ROM integration](../research/native-rom-integration.json) |
| Matrix 4 KiB component attempt | Matrix-v1 runs 38 goals with native exit 0 and 128 Ninja actions after 163 frontend steps; the failed wrapper receipt is preserved, while the distinct read-only postcheck and independent review pass | [Native ROM integration](../research/native-rom-integration.json) |
| Current 4 KiB provider ELF/symbol checks | All 26 checks execute freshly and pass within 48 native actions; complete raw review verifies commands, new log rows and stamps; full ABI, runtime and hardware remain separate | [Native ROM integration](../research/native-rom-integration.json) |
| Ordinary provider installation | The normal 27-goal build and independent raw replay pass: 164 actions, 29 fresh installs and two preserved XML files; all 31 verify and 26 prior strict ELF passes are reused, with zero fresh checks | [Native ROM integration](../research/native-rom-integration.json) |
| Current allocator producer capture | Matrix-v1 records nine read-only commands across three query layers and six nodes; all 68 evidence files are collected and the full-input check reopens native references; no fresh compile/runtime claim | [Native ROM integration](../research/native-rom-integration.json) |
| Native packaged-bytecode proof | Four complete PYC members reproduce from the pinned Soong recipe; 28 native commands across capture/proof pass with zero skips; generated-proto provenance, signatures and full VINTF remain separate | [Native ROM integration](../research/native-rom-integration.json) |
| Current full-VINTF result | All four native commands, fifteen postflight checks and scoped independent review pass on matrix-v1; the combined check has no reported skips/warnings, while framework consistency retains one definition skip and two warnings; complete input compatibility stays false | [Native ROM integration](../research/native-rom-integration.json) |
| Native v12f policy and exporter build | 73 Ninja actions after configuration; source/combined policy compilation, OEM guard, five context checks, two seapp checks and two structural checks pass; corrected C exporter compiled and linked | [Native ROM integration](../research/native-rom-integration.json) |
| Expanded native policy-output build | 25 ordinary goals, 35 Ninja actions; runtime CIL/mapping installation and all 11 preserved compiler/guard/check outputs freshly executed; independent analysis subsequently stopped on its tool-reader bound | [Native ROM integration](../research/native-rom-integration.json) |
| Preserved independent v12f policy analysis | Export4 verifies source/M4/mapping and fresh-check provenance, all 6,366 assertions and exact reviewed effects; three unfiltered zero-permissive binaries; provider policy unselected | [Native ROM integration](../research/native-rom-integration.json) |
| Native v13h policy sidecars | Six checks and fourteen commands pass, zero skips; three current-policy digest files derive from sealed inputs, without Android genrule execution or image adoption | [Native ROM integration](../research/native-rom-integration.json) |
| Current Camera/mi_ext/recovery build | Eleven goals complete; captured producers verify four fresh DEX invocations, matching ODEX/VDEX, strict JNI checks, working76 copy and mi_ext integrity; APK/runtime and signed-chain gates remain open | [Native ROM integration](../research/native-rom-integration.json) |
| Native recovery-mode fixtures | Twelve isolated Kati guard cases pass, including required diagnostic failures; the first full v12e configuration separately failed on mi_ext before the later v12f correction passed | [Native ROM integration](../research/native-rom-integration.json) |
| Native custom-image correction fixtures | 99 expected outcomes: one reproduced historical failure, five corrected positive cases and 93 specific negative cases; full custom-image region parsed, with no image recipes or Ninja execution | [Native ROM integration](../research/native-rom-integration.json) |
| Native DEX provider fixtures | Five top-level tests and 11 subtests pass in the pinned Linux Soong test binary; no full Java-suite stamp, actual Camera artifact build or dex2oat execution | [Native DEX fixtures](../research/dex-import-native-fixtures.json) |
| Native EROFS inventory-tool build | Actual compile/link/install passes with source read-only; subsequent metadata qualification has unresolved failures and is not an image-adoption pass | [Native ROM integration](../research/native-rom-integration.json) |
| Native production file-size primitives | Four checks pass with zero skips, including finite 2 GiB/6 GiB limits and bounded log-overflow termination; this probe did not execute mkfs | [Native ROM integration](../research/native-rom-integration.json) |
| Native unchanged-vendor round trip | Eight checks pass, zero skips; two identical raw images preserve all 3,910 entries and 3,389 regular-file contents under the exact 2 GiB vendor recipe; not policy/image adoption | [Native ROM integration](../research/native-rom-integration.json) |
| Native unchanged-ODM round trip | Eight checks pass, zero skips; two identical raw images preserve all 3,059 entries and 2,925 regular-file contents under the exact 6 GiB ODM recipe; no policy replacements, AVB or boot result | [Native ROM integration](../research/native-rom-integration.json) |
| Native v12/export4 policy-image reconstruction | Nine checks and 38 commands pass, zero skips; two identical complete TAR/image/export sets preserve all but the exact five policy payloads; raw derivation only, no adoption or AVB | [Native ROM integration](../research/native-rom-integration.json) |
| Native v13h policy-image reconstruction | Nine checks and 38 commands pass, zero skips; independent review confirms both exact five-file derivations and all other semantic metadata; unsigned raw outputs remain unadopted | [Native ROM integration](../research/native-rom-integration.json) |
| Native v13h keyless leaf footers | Six checks and sixteen commands pass, zero skips; identical repeated vendor/ODM leaves preserve raw prefixes and pass hashtree, FEC and exact package budgets; no physical fit, signed parent chain or adoption | [Native ROM integration](../research/native-rom-integration.json) |
| Native pinned-date fixtures | All 33 expected outcomes verified: nine positive/legacy cases and 24 diagnostic-specific negatives, zero skips; live product unchanged | [Native date checks](../research/pinned-build-metadata-native.json) |
| Original factory Camera packaging | Unchanged APK passes strict privileged/preprocessed and uses-library checks; no APK selection, permission-grant, effective-label or hardware result | [Factory Camera APK](../research/factory-camera-apk.json) |
| Static vendor VINTF | Vendor/ODM manifest load and merge, including captured active vendor APEX fragments | [VINTF validation](../research/vintf-validation.json) |
| Native VINTF build inputs | Selected framework XML, host tools and stock-kernel requirements built; the graph audit identifies the still-missing framework fragments and APEX artifacts rather than treating the partial inventory as complete compatibility | [VINTF build closure](../research/vintf-compatibility.json) |
| Recovery device test | `working76` installed to recovery_a; matching readback; visible UI and fast touch confirmed by the user; root ADB, logs and automatic defaults verified | [Working recovery](../research/twrp-working-defaults.json) |
| Recovery reproduction and ROM build target | Two fresh Mac rebuilds match working76 byte for byte; Linux public-key staging/verification and two actual `recoveryimage` target runs pass with unchanged output bytes | [Workspace integration](../research/workspace-integration.json) |

TWRP preserves the working `fix22ZJ-touchfix18` executables, libraries, drivers,
firmware and policy. Exactly two text files change: early recovery startup sets
SELinux permissive, and theme vibration defaults are zero. Its AVB footer is
signed with the local development key, flags zero, recovery rollback index 1
and location 1. This is a verified repack of a prebuilt runtime, not a proven
source compilation or OEM signature. The exception is recovery-only; normal
Android enforcement and denial checks remain required. Saved TWRP settings can
override theme defaults. No Magisk integration is included.

## Gates before a complete ROM

- **Policy and policy-image integration:** v11b restored the two evidenced Xiaomi system_ext service
  declarations, object roles and generated API mappings, plus the framework
  offlinelog classification. Strict combined compilation, the ownership guard
  and all nine factory checks pass. Independent v11 comparison verifies the
  reviewed effective permission and assertion coverage changes; unfiltered
  analysis finds zero permissive domains in all three policy binaries.
  The [four-property source contract](../config/nezha-oem-properties.json) now
  passes the actual v12f policy build after the Kati correction. Its independent
  comparison against v11b now passes in export4, including exact permission,
  dontaudit and neverallow coverage, all 6,366 assertions, M4/API producer
  provenance, nine fresh checks and three zero-permissive binaries. Earlier
  stale-export and analysis-adapter failures remain preserved; export4's exact
  newline-interleaved source check does not change policy or waive checks.
  The [framework-provider policy](../config/nezha-framework-provider-policy.json)
  now passes the actual v13h source build and native analysis against export4:
  6,370 assertions, nine fresh checks, three zero-permissive binaries and the
  complete reviewed effect delta. Neither later addition was part of v11b.
  Commit `78376c7` adds the explicit matching `v13h-policy-only` image-input
  profile, eligible for evidence validation. Earlier profiles and the blocked
  default are unchanged. The separate `policy-images-v13h-v1` raw reconstruction
  and independent review now pass; image adoption remains unverified.
  Full labeling needs the actual complete Evolution APK inventory; a missing
  artifact skip or API-202504 touch-only target is not a pass. The corrected
  policy is a non-installable validation output: retained vendor/ODM images
  still contain their original policy. The qualified raw derivation replaces
  the vendor CIL and the ODM combined policy plus its three matching framework
  digests while preserving every other file and semantic metadata field under
  explicit physical-layout exclusions. Its adoption is a separate gate. The authored
  [EROFS inventory tool](../tools/erofs-metadata/README.md) has built natively.
  The corrected exporter now passes all six read-only stock checks, exporting
  3,910 vendor and 3,059 ODM entries, and all eight shared-xattr regression
  cases. Its latest synthetic qualification still records 25 passes and two
  writer/upstream-fsck failures. The earlier exporter failures remain preserved.
  The synthetic writer round-trip run records **11 passes and six failures**:
  repeated exact five-file derivations pass, but all six upstream empty-xattr
  checks fail. That synthetic run derived no factory image. The later vendor/ODM
  results below are separate; policy-image adoption remains open.
  The [five-file policy-image preparation](policy-image-inputs.md) now binds
  complete stock manifests, exact replacements, repeated TAR construction and
  finite production limits. Commit `35324b4` adds an explicit `v12-export4`
  profile with the reviewed native records; the historical default retains its
  original seven-pin blocker. The coordinator's complete unmocked admission
  replay passes, without running TAR preparation, opening images or executing
  native tools. This profile does not admit the active v13ha provider policy.
  The separate native sidecar v2 run now passes six checks and fourteen commands
  with zero skips, deriving all three framework digest files from the sealed
  v12f/export4 inputs and pinned recipe. These are validation derivatives, not
  captured installed outputs or executed Android genrules. No image, policy or
  source adoption follows; the first loader-parser failure remains preserved.
  The native production-size primitive probe now passes four checks with zero
  skips, using finite 2 GiB/6 GiB file limits and bounded log-overflow handling.
  Its 59-file capture is verified; the first failed attempt remains preserved.
  It did not execute mkfs or qualify its production fallback, full spool I/O,
  disk headroom, partition fit or AVB.
  The subsequent full-vendor no-change attempt remains failed: two checks and
  original fsck extraction completed, then the harness rejected that operation's
  completion diagnostic before TAR construction or mkfs image creation. The
  corrected v2 then passed all eight native checks with zero skips. Its two
  941,744,128-byte raw images are identical to each other and preserve all
  original content and nonphysical metadata, including UUID/features. This
  qualifies the unchanged-vendor 2 GiB recipe. The subsequent original-ODM run
  also passes eight native checks with zero skips under its 6 GiB limit. Its two
  4,678,053,888-byte raw images match each other and preserve all 3,059 paths,
  2,925 regular-file contents and nonphysical metadata. Both runs make zero
  policy replacements and do not themselves qualify changed policy inputs.
  The later **policy-images-export4-v1** run now qualifies the exact five-file
  raw derivation, with nine checks, 38 commands and zero skips. Its repeated
  vendor and ODM images are respectively 941,744,128 and 4,678,025,216 bytes;
  only the reviewed policy payloads change. Complete exports and diagnostics
  are captured; the large TARs/images remain guest-only and were not reopened
  by the host collector. The later v13h footer run separately verifies hashtree,
  FEC and exact package budgets; signing, physical partition fit, source
  adoption, retained-kernel mounting and boot remain unverified.
- **Complete partition and OTA packaging:** retain `mi_ext`, both DLKM sets,
  the dedicated A/B recovery layout, factory encryption/AVB fstab declarations
  and measured Nezha budgets. The [mi_ext input and build path](mi-ext-inputs.md)
  and [A/B-only recovery packaging correction](recovery-packaging.md) are
  installed in v12e. Twelve isolated recovery-mode Kati cases pass; the full
  build failed on the uninitialized mi_ext variable above. The installed v12f
  correction uses the pinned read-only initialization macro, preserving the
  override checks and empty optional values. The actual policy build now gets
  through configuration successfully; it requested no images.
  The current Camera/mi_ext/recovery component build now passes, with inspected
  unchanged recovery/mi_ext payloads. Its bounded producer review confirms the
  fresh guarded recovery copy and mi_ext NONE-footer/hashtree check; complete
  packaging and signed-chain evidence remain necessary. The A/B correction
  removes the inapplicable non-A/B two-step requirement only for A/B-only
  products; never fabricate a `recovery-two-step.img` from the kernel-free
  working76 image. Target-files, OTA, super-image and flash admission remain
  false. Selecting TWRP does not prove an OTA contains, preserves or restores
  it correctly on either slot. The new [target-files metadata projection](target-files-metadata.md)
  binds 205 original property, VINTF and APEX files to the retained images;
  host source admission and 43 isolated native Kati cases pass, but it is not
  installed in v12fa or a target-files pass.
  The new [combined source composition](target-files-source-composition.md)
  joins patches 0005–0011 through explicit ten-file identities, with fresh
  host-verified metadata/recovery/mi_ext admission. The later packaging-matrix
  transaction now selects the reviewed source composition and policy-image
  metadata; no build or final target-files hook has run from that selection.
  Its complete derivation and metadata bindings remain required; changing
  expected image hashes alone is insufficient.
  The [optional mi_ext care-map path](mi-ext-care-map.md) is committed but
  inactive. Qualify the authentic ODM import closure and final Evolution
  SYSTEM marker before composing it into the ordinary packaging path.
- **Signing and boot chain:** the inspected v8 generated boot components have
  AVB algorithm `NONE`, despite AVB being enabled in configuration. A complete
  signed chain, key availability, rollback compatibility and partition fit
  still need validation. The recovery bundle supplies its matching public key
  instead of using the generic engineering test key for that chain descriptor;
  this configuration is not proof of a completed, trusted vbmeta chain.
  The [new public-key image-set verifier](avb-image-set.md) has checked four
  prior components with real avbtool/OpenSSL; complete verification remains
  blocked by 13 absent roles. A leaf footer using `NONE` can be covered by its
  signed parent, but no complete signed parent chain has yet been established.
  The [host signing workflow](avb-signing.md) now supplies a tested recipe using
  the existing development key and 15 final input images. Its planning and
  unsigned descriptor-carrier checks have run; private-key signing and the
  complete 17-role output-chain verification have not. Keys remain on the Mac.
  The maintained [signed target-files reconciler](signed-target-files-reconciliation.md)
  can preserve an existing archive around an already verified signed set; its
  synthetic tests do not supply an actual archive or signing result.
  The [pinned build-metadata capability](pinned-build-metadata.md) now verifies
  33 expected isolated native Kati outcomes. Patch 0012 and its helper are now
  selected in source. Nothing2 verifies six metadata-file values; independent
  rewrites, output freshness and helper-execution proof remain unverified.
  The first diagnostic-harness failure remains preserved. It cannot relabel earlier build
  dates or establish reproducible images without native and artifact checks.
  Working recovery's development signature does not sign the ROM or authorize
  relocking. Its kernel-free image depends on the intact device boot chain and
  is not protection against bootloader damage.
- **Framework/vendor compatibility:** the [native closure audit](vintf-compatibility.md)
  built selected XML and kernel inputs but still found ten required framework
  fragments and all 36 selected framework APEX artifacts absent at its
  checkpoint. Complete those inputs, materialize the actual APEX manifests,
  and run the full comparison with explicit kernel requirements. The pinned
  compatibility CLI does not enforce every framework-provider expectation in
  the factory matrix. The authored [Sigma and QCC provider bundle](framework-providers.md)
  therefore also needs strict native ELF, policy, linker and service checks;
  [v13 source admission](framework-provider-source-admission.md) reproduces a
  host candidate with its 31 payloads, 27 installable modules and private policy.
  The v13f provider packet was staged at **02:18:20 UTC**, then installed in four
  verified exchanges at **02:34:51 UTC**. Earlier inputs and outputs were
  preserved. The 31-goal `policy-only-v13f-1` phase failed in Soong bootstrap on
  the direct Audio AIDL V2 versus transitive V4 conflict above, before any new
  policy compilation. The strict 16 KiB settings remain enabled, but no provider
  ELF actions ran. The later v13ha correction is installed and its 31-goal
  native policy build and independent analysis now pass. This closes the policy
  verification slice, not provider ELF, runtime or complete VINTF compatibility.
  The new read-only VINTF graph capture binds 21 XML and 36 APEX inputs, but
  confirms the all-target alias lacks the full compatibility action. Its
  first three-goal build timed out and remains failed. The incremental
  `vintf-v13h-2` retry completed without timeout but failed the mandatory
  `android.hidl.allocator` declaration at frozen level 5. All 57 selected XML/APEX
  artifacts are present; service integration and a successful unchanged check
  remain required. The older v13h full-check packet is historical staging, with 221
  files verified and 39 APEX packages required; native materialization and
  compatibility checks remain unexecuted. Its 44 coordinator offline tests
  pass with zero skips, separately from the native build.
  A captured current Soong configuration selects maximum ELF page size 16,384
  with the prebuilt check enabled; static inspection finds 22 of 26 provider
  ELFs have 4 KiB load alignment. The [older 4 KiB experiment](nezha-page-size.md)
  in `84d63c2` and its host v13g candidate remain unadopted historical inputs.
  The user now authorizes a 4 KiB first-boot baseline, with enabled checks and
  a separate current-provider candidate, now host-verified in `17cde61`.
  The corrected v13ja source transaction selects `4096`, and its completed
  37-goal native build verifies that generated maximum with checks enabled;
  neither that selection nor future 4 KiB results resolve the recorded
  16 KiB/VTS compatibility gap.
  The [original-ODM shipping-API patch](vintf-shipping-api.md) passes source-bound
  host probes without fabricating vendor properties; it is authored but not
  installed by the v13f provider transaction and is not a complete native compatibility result.
- **Runtime and stock features:** no Evolution boot or native feature is
  verified. Module stage loading/signature behavior, storage, telephony, audio,
  thermals, sensors, camera/Leica and accessories require separate tests. The
  Camera APK itself is not packaged; strict signing and uses-library integration
  remain open despite its nine dependencies building. The new
  [exact Camera runtime-library bundle](camera-runtime-inputs.md) and reviewed
  Soong provider patch are installed in v12e. The current names and strict
  class-loader integration now has a successful component build and byte-matched
  runtime outputs. The producer review binds four fresh DEX invocations to their
  raw Soong inputs and matching installed ODEX/VDEX, and verifies the fresh JNI
  action with SONAME, dependency, symbol and 16 KiB checks enabled. The absent
  `dexpreopt.config` targets are not counted as passes; the observed library-import
  configuration does not verify the Camera APK's uses-library contract. Runtime
  APIs and linker access remain unverified. The five native provider fixtures and 11 subtests remain
  separate evidence, and none establishes the Camera APK or hardware behavior.
  The [earlier APK admission review](camera-apk-inputs.md) verifies the unchanged
  signature, ZIP contents and exact library names, while reproducing both
  packaging failures: target SDK 35 needs preprocessed handling, and privileged
  preprocessed handling rejects the compressed DEX entries. The APK remains
  unselected; no signing or privilege exception was introduced.
  The distinct [original factory Camera APK](factory-camera-apk.md) passes the
  strict privileged/preprocessed check unchanged, resolving that input's DEX
  compression blocker. Its ten always-privileged requests, rising to eleven
  across feature branches, still need actual grant and effective
  SELinux-label validation. Neither APK is selected or hardware-tested.
  The [factory permission-grant review](../research/factory-camera-permission-grants.json)
  traces three pure-signature requests through captured evaluator and service
  source. Allowlisting or a debuggable build cannot replace signing eligibility;
  a denied grant is distinguished from an installation error. Effective signing,
  flags, permission grants and Camera call behavior remain unverified. The
  coordinator's 30 focused tooling tests pass; no grant or permission definition
  was changed and no APK was installed.
  The [build-only Camera packet](camera-apk-build-admission.md), committed as
  `117261c`, reproduces on the host and its content-verifying producer passes.
  Its separate namespace is not installed in the guest or exported to Make;
  product selection, permissions, MAC labeling and real APK outputs remain open.
- **Recovery completeness:** encrypted `/data`, backup/restore coverage,
  additional reboot/Android round trips, A/B and OTA behavior, ADB host
  authentication and restoring recovery SELinux enforcement remain unverified.

Keep `SELINUX_IGNORE_NEVERALLOWS`, relaxed uses-library validation, VINTF
bypasses, AVB bypass flags and writable-source exceptions out of the ROM
workflow. A permissive recovery or successful component build does not waive
these gates. [Integration sequencing](nezha-integration.md) records the next
source work; [recovery handling](recovery-plan.md) records recovery boundaries.

## Current entry points and historical evidence

| Use now | Keep for diagnosis; do not treat as the current default |
| --- | --- |
| This status page and [Nezha integration](nezha-integration.md) | Detailed dated checkpoints in `docs/build-progress.md` and the individual component-build records |
| [Working TWRP instructions](../recovery/twrp-working/README.md) and [current recovery guide](twrp-bringup.md) | [Recovery history](twrp-bringup-history.md): earlier minimal builds, RAM-boot attempts and `provided75` before persistent defaults |
| [OEM policy integration](oem-policy-integration.md) and its [current record](../research/oem-policy-integration.json) | [v10 source-policy integration](policy-source-integration.md), v7/v8/v9 builds and copied-CIL prototypes remain dated evidence; their original results are preserved |
| [Native ROM integration](native-rom-integration.md) and its [current record](../research/native-rom-integration.json) | Preserved v12 staging history and first Kati failure; the successful policy build and host provider, metadata and signing inputs are not completed native ROM builds |
| Current factory vendor/ODM input receipts | Modified Xiaomi.eu package, earlier candidates, outputs and failed AVB results with their original provenance |

Run `make test` before completing workspace changes. Generate into new ignored
candidate directories, validate configuration admission, preserve separate
user/userdebug output directories, and bind each build to its source snapshot,
patches, input receipts, tool hashes and artifact hashes. Offline tests neither
compile Android nor test a phone. Cleanup and local builds do not authorize
device changes; any future flash, reboot or restore needs its own explicit
user instruction and selected-device preflight.

The v10 native result, independent analysis and three failed context checks
remain in their original record. The first v11 build resolved those checks but
failed its new ownership guard because Android retains inherited platform
members in generated attribute sets. The corrected guard requires that exact
platform membership plus only the reviewed additions; it does not allow
arbitrary widening. The v11b retry archived the ten previous validation outputs
and reran the combined compiler and all nine checks, completing 30 main Ninja
actions after one bootstrap step (31 cumulative progress entries), with source
read-only and user output writable. No check was waived. The
independent analysis then bound the ten real compiler inputs, M4 sources,
public exports, mappings, inherited semantics and executed native checks to
the successful phase. Its three permissive analyses ran with inputs read-only.
The original factory images, working76, four existing upstream patch projects and
complete-ROM gates were preserved. No new source sync, image adoption or device
operation occurred in this policy milestone.

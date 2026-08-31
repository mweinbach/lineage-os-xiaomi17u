# Current Nezha workspace status

The selected target is **Evolution X Android 16 QPR2 `bka` for Xiaomi 17 Ultra
(`nezha`, SM8850 / `canoe`)**, with **TWRP `working76` as the default recovery**.
The ROM remains a `framework-checks` product, not a complete or flashable ROM.
The recovery has a separate successful device test using the installed stock
companion boot, kernel and vendor stack; it does not establish that it works
with newly built Evolution components or that Evolution X boots. This page
consolidates recorded evidence through **August 31, 2026 UTC (August 30 in
New York)**. UTC milestones before 04:00 occur on the preceding New York date.
This page does not assert that a historical builder VM is still running.

The user now authorizes a **4 KiB first-boot baseline**; 16 KiB compatibility is
not a prerequisite for that initial bring-up. The **v13ja source configuration
is now installed**, selecting `4096` with prebuilt checks enabled. Commit **17cde61** adds
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
The **current full VINTF run fails the combined check**: 155 device HAL
instances are absent from the framework compatibility matrix. All 39 APEX
packages materialize and the two separate consistency commands exit zero, but
the combined command exits 65. Native integration and verification of the
matrix correction is the next compatibility blocker; no check is suppressed
or counted as a pass.
Commit **c3686ed** adds the [exact framework-matrix source projection](framework-matrix.md).
Host verification binds all 155 missing AIDL tuples to original declarations
and factory matrix coverage, producing 130 packages without wildcard instances,
broadened versions or changes to numbered platform matrices. Repeated 47-file
candidates match. Native matrix build and the compatibility retry remain
unverified; the preserved exit-65 result is still the current full-check result.

The independently analyzed policy baseline is **policy-only-v13h-1**, completed
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

This establishes the current v13ha policy baseline. The earlier v12f/export4
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
signed image chain; cryptographic APEX verification remains pending.

The current **allocator-producers-v13j-4k-1** capture completes at
**01:31:45 UTC**, with nine zero-exit commands across three query layers and
zero skips. All three producer outputs are described, with source and selected
graph/log guards preserved. The complete 66-file host collection and envelope
checks pass. That host-only admission leaves external native references for a
subsequent guest check; no new compile action, source-to-binary equivalence or
runtime registration is established by this read-only capture.

The subsequent **current 4 KiB full-VINTF input capture passes**, freshly
reopening the allocator prerequisites and the four bytecode proof comparisons.
It verifies the nine-command/three-layer/six-node allocator descriptions and
binds **22 framework XML files and 39 APEX packages**: 36 framework plus three
vendor packages. Strict 4096 settings and the actual component result remain
bound. This closes those input prerequisites; the subsequent full run below is
a separate failed compatibility result.

The actual full run materializes all 39 APEX packages and passes the framework
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
held for full VINTF and the remaining Camera admission checks; staging
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
Ordinary product execution, source/image adoption and the metadata hook remain
pending; complete targets stay blocked.

Commit **137f438** adds a separate, explicitly paired 4 KiB delivery successor.
Two host metadata bundles match across all **247 files**, retaining the 205
original metadata members, and two **47-file** device candidates are identical.
The capability binds the actual 37-goal result and current 4 KiB profile;
independent host reviews are clear within their stated scope. The older
delivery mode and descriptor remain unchanged. Neither the metadata bundle nor
these new source/image candidates are installed. Historical private-copy
evidence is retained as provenance, not a fresh 4 KiB copy or source check.
Current input qualification and ordinary product/metadata-hook execution remain
required. Reversible source-input integration may select the exact verified
`NONE` leaf images with AVB enabled; final flashable-artifact admission still
requires the complete signed parent chain, rollback settings and physical
partition fit.
The subsequent **inactive 4 KiB policy-image stage now passes**, copying the
exact reviewed vendor/ODM leaves into a separate candidate source bundle and
rehashing current source/policy/runtime inputs. It changes neither active
source nor Android outputs and does not install metadata or adopt images.
The complete transport and native-receipt reviews pass within their stated
scope, including all eleven captured transport files. Large image bodies remain
in the guest. Any activation needs a deliberate source rebase and fresh
admission after the matrix correction; no signed-parent, physical-fit or boot
result follows.

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
It inspects five missing selected-input roles but deliberately remains unbound:
the check exits 2 and explicit generator selection refuses before private-input
reads or candidate publication. It enables no native product, BoardConfig or
blocked target. Final compatibility coverage remains distinct from a runner's
outer success field and from artifact/device admission.

Commit **203ab67** adds the inactive [ODM-import care-map successor](mi-ext-care-map.md).
It binds all 22 original ODM property files and resolves the exact captured
imports without skipping arbitrary imports or changing original properties.
Native codec/tool qualification, the final Evolution SYSTEM identity and
ordinary packaging remain unverified; the active source composition is unchanged.

The latest completed full workspace suite passed **3,919 tests in 164.103
seconds with zero failures, errors or skips**, executed by the matrix owner.
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
code through `c3686ed`, with the previous component checkpoint committed
as `8fc2162`, followed by `da9648b` and the full-failure checkpoint `3001e85`. The active
guest source remains v13ja with 4 KiB selected;
`analysis-v13h-policy-only-v1` remains the latest verified policy baseline.

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
| Current v13ja 4 KiB source and component build | Corrected installation and 37 goals pass; only one of 254 generated settings changes, with all thirteen policy and eleven runtime identities preserved; partial VINTF still skips one subcheck | [Native ROM integration](../research/native-rom-integration.json) |
| Current 4 KiB provider ELF/symbol checks | All 26 checks execute freshly and pass within 48 native actions; complete raw review verifies commands, new log rows and stamps; full ABI, runtime and hardware remain separate | [Native ROM integration](../research/native-rom-integration.json) |
| Current allocator producer capture | Nine commands across three query layers report success; all 66 payloads are collected and subsequent guest prerequisite verification reopens the external references; no fresh compile/runtime claim | [Native ROM integration](../research/native-rom-integration.json) |
| Native packaged-bytecode proof | Four complete PYC members reproduce from the pinned Soong recipe; 28 native commands across capture/proof pass with zero skips; generated-proto provenance, signatures and full VINTF remain separate | [Native ROM integration](../research/native-rom-integration.json) |
| Current full-VINTF result | Input capture verifies allocator/bytecode prerequisites and the 22-XML/39-APEX closure; all 39 APEX packages subsequently materialize, but the combined check fails at exit 65 on 155 missing matrix tuples | [Native ROM integration](../research/native-rom-integration.json) |
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
  host-verified metadata/recovery/mi_ext admission. It is not installed in
  the guest; earlier isolated Kati results do not validate its full build.
  Later policy-bearing images require a new complete derivation proof and
  metadata bundle; changing expected image hashes alone is insufficient.
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
  The [pinned build-metadata capability](pinned-build-metadata.md) now verifies
  33 expected isolated native Kati outcomes, but is not installed or enabled.
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

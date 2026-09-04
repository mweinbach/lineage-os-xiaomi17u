# Nezha product and build progress

## Package6 diagnostic outcome and observer readback — 2026-09-04

**Experimental diagnostic execution closes at 00:54:34 UTC**, after
**632.775854 seconds**, with 39 fresh static host APEX materializations.
The captured supervisor exit and trace terminal uint32 return are both **0**;
the returned native structural review reports **265 events, 60 calls and four
cache generations**, effective device level **202504** and retained original
level **UNSPECIFIED**. Original driver/guest, link-authority and source-pair
replay pass. This initial admission does not independently replay the native raw
trace or establish a separate native child-wait observation.
It remains `NONQUALIFIED_DIAGNOSTIC_OUTCOME_ONLY`, not the original checker.

**Compile/archive/link observer readback closes at 00:55:06 UTC**, exit **0**.
All **38 pairs / 76 files / 391,851 decoded bytes** pass the unchanged original
observer verifier. This closes those stages' observer-body gate only: it does
not parse mountinfo into a full mount table or cover this runtime's observer.

**Runtime trace/observer readback closes at 00:59:28 UTC**: four files retain
**18,160,895 decoded bytes**, including the **18,091,151-byte raw trace**.
ROOT replays the original observer and trace summary, matching the runtime's
complete structure exactly. Diagnostic stdout ends `COMPATIBLE`; this does not
establish original-checker equivalence or full forward coverage.

**All 155 retained AIDL package/version/interface/instance tuples match exact
effective-device-manifest declarations**; 122 matched provider tuples use the
existing parser's default version 1. This bounded declaration check does not
erase the generated-metadata 127-name gap or prove live services/full requirements.

Full combined-matrix requirements, header/ODR, original-CLI/runtime equivalence, VINTF,
functional Super, flash safety, policy/trust/ABI, OTA and boot remain unqualified.
No phone operation or additional artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-vintf/coverage-policy-successor-v1/diagnostic-caller-implementation-v1/diagnostic-execution-preparation-v1/root-dispatch-preparation-v1/bound-packet-v2/actual-v1/semantic-admission.json` | `3f20ccf064510105828a583794e9c0047c472a769e32955fff4de95691d35575` | 14,002 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-caller-implementation-v1/producer-grounded-build-proposal-v4/compile-link-observer-readback-v1/actual-v1/readback-admission.json` | `214b5df27647f9bb615592e7ef49fd084008e21658f45589859e890ce1ff2f2d` | 26,821 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-caller-implementation-v1/diagnostic-execution-preparation-v1/trace-readback-preparation-v1/actual-v1/root-trace-admission.json` | `42407ee89293146a06dcc6985fd12d880d7f1c4da341935939802e72503d89eb` | 5,712 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-caller-implementation-v1/diagnostic-execution-preparation-v1/trace-readback-preparation-v1/actual-v1/forward-declaration-check-v1/report.json` | `081721ee5eeafa89d889587c5b7189a7614d105a50bc44028672b68675bc3f87` | 63,032 |

## Package6 sparse Super and published boot candidates — 2026-09-04

This earlier checkpoint predates diagnostic execution and compile/link observer-body readback.

**Super assembly closes September 3 at 23:57:08 UTC**, in **568.338574 seconds**.
One **9,291,741,260-byte sparse image** expands to **15,300,820,992 bytes**;
strict framing checks accept **171 chunks: 151 RAW, 11 FILL and nine DONT_CARE**.
Output SHA-256: `ad8a0fb87b2ab7a60e5f71c8a633610444942a814b167ed0f32d651f4942fbac`.
All eight fresh same-descriptor input pairs are preserved, including actual
vendor/ODM paths. Semantic admission closes **September 4 at 00:02:31 UTC**,
replaying original stage, observer and source-pair APIs with 17 named controls
unchanged. **LP readback closes September 4 at 00:15:25 UTC**; its later admission
verifies both geometry copies, six LP metadata copies and all eight embedded hashes.
Static logical/group/physical fit passes with **5,969,076,224 bytes** of group-A
headroom. Populated images contain no DONT_CARE or LP_ZERO bytes; all eight B
partitions are empty. Runtime-library, functional Super and flash safety remain open.

**The published boot-candidate capture closes September 4 at 00:04:21 UTC**,
exit **0**, in **11.988 seconds**, with complete streams and empty stderr.
It joins 29 retained member identities and compares the original DTBO payload,
with two full published-ZIP hash checks and six unchanged metadata pairs. This is
candidate-only evidence, not historical-branch selection, full constructor,
source/runtime or ROM qualification. Helper replay accepts the actual result
and rejects eight mutations. Both actual captures occur on September 3
in New York; the UTC dates above distinguish the midnight crossing.

**Diagnostic compile-v2 closes September 4 at 00:09:36 UTC**: 36 compiles and
one archive command pass, preserving the original 33 archive operands/order.
Mandatory native trace-header dependency checks and explicit host summary checks
pass; raw depfiles and observer bodies are not independently replayed here.

**The diagnostic link closes September 4 at 00:27:13 UTC**, exit **0**, in
**539.949 seconds**. One exact command joins ten current archives and four
closed-compile inputs, with source-pair replay passing. The **6,245,080-byte**
binary has SHA-256 `22ed88de48f2e874d2e8518813b327ccdbdc1debd39b82920b717fbc8d76ac97`.
It remains `NONQUALIFIED_EXPERIMENTAL_LINK_ONLY`; no diagnostic run is admitted.

Diagnostic execution, full header/ODR, source/runtime, policy/trust/ABI,
VINTF, flash safety, OTA and boot remain open. No phone operation or cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-avb/package6-super-continuation-v1/super-assembly-semantic-admission-v1/admission.json` | `2681c06a934866efba7a339206603b3fd8db6d3bb368eb7a1da357cf8fd69cbe` | 15,416 |
| `final-boot-content/package6-preparation-v1/published-projection-preparation-v1/root-dispatch-v1/actual-v1/completion.json` | `5e5aa49d02cd9543735cfdfdae40ff55a6662fc8da7a3339d355a382e7c8efbf` | 2,391 |
| `final-boot-content/package6-preparation-v1/published-projection-preparation-v1/result-admission-v1/receipt.json` | `2e1ebd7e1b0839712576017c489bec17c3d29277b3b773fae0607fb4ff9a1a78` | 7,227 |
| `final-avb/package6-super-continuation-v1/super-lp-readback-v1/actual-semantic-admission-v1/admission.json` | `e25153d3f4669966c3937fc7e6c52f2427e6a8ea50c8985b902eeb3a696f4725` | 23,766 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-caller-implementation-v1/producer-grounded-build-proposal-v4/compile-archive-stage-v2/root-dispatch-preparation-v1/bound-packet-v1/actual-v1/semantic-admission.json` | `d59d1ca234c0a41794e53737d388ba946049383ea54c721752fbba2a13328b84` | 16,599 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-caller-implementation-v1/producer-grounded-build-proposal-v4/link-only-stage-v1/compile-v2-successor-v1/root-dispatch-preparation-v1/bound-packet-v1/actual-v1/semantic-admission.json` | `df0236b6f02b4a5f3991fa48d0c4006ac65522586bbdfcbecdf0d7bd69ed8604` | 25,713 |

## Package6 source endpoint and diagnostic dependency failure — 2026-09-03

This earlier checkpoint predates Super assembly and published boot-candidate comparison.

**P4 closes at 23:46:38 UTC**, exit **0**, in **29.077 seconds**. Its two
query/command rows name `system/tools/mkbootimg/mkbootimg.py` and the matching
`-f` operand, without source/ZIP-body reads. Original APIs and eight mutation
cases pass, with 69 controls and 13 actual records unchanged. The observed
endpoint is not complete route, constructor, PYC, source or runtime qualification.

**The diagnostic attempt fails at 23:37:38 UTC** after **575.439 seconds**:
nine compiler commands exit 0, but only eight objects are recorded and no archive
is admitted. Job08 fails the required diagnostic-header dependency check.
**Three-file readback closes at 23:47:29 UTC**, exit **0**, retaining **94,770
decoded bytes**. Its **84,199-byte depfile** has 941 dependency tokens and no
`NezhaVintfTrace` header basename under any spelling. Original observer replay
passes; the unchanged dependency validator still rejects this depfile.
The intended source replacement is not proven.
A PWD/VFS lookup mismatch remains a hypothesis, not an established mechanism.
Separate source-guard recovery passes without changing the original failed
compile/source flags or incomplete-stream record; no link or diagnostic run follows.

Super assembly remains pending without an accepted result. Full source/runtime,
header/ODR, policy/trust/ABI, VINTF, super/fit, OTA and boot remain open.
No phone operation or additional artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/next-archive-inputs-v1/next-two-root-inputs-v1/next-packaging-header-inputs-v1/next-mkbootimg-source-zip-v1/root-dispatch-v1/actual-v1/actual-admission-v1/review.json` | `867dcc2cd6f9b25d35ab7279c3dc60c7d2d09e0adddf105a3d3080190a17a8cf` | 12,624 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-caller-implementation-v1/producer-grounded-build-proposal-v4/compile-archive-stage-v1/root-dispatch-preparation-v1/bound-packet-v1/actual-v1/failure.json` | `339b2b38fe3e83cb00b4f61e0c98718ae5c7b244cb12a11f706765dd42acdcdb` | 14,865 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-caller-implementation-v1/producer-grounded-build-proposal-v4/compile-archive-stage-v1/root-dispatch-preparation-v1/bound-packet-v1/actual-v1/source-recovery.json` | `9408fd3b2a0a47a0532ad2e1c4daa8aa73a520097ac099304278d8e3b6c6bf05` | 2,711 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-caller-implementation-v1/producer-grounded-build-proposal-v4/compile-archive-stage-v1/failed-job08-readback-v1/actual-v1/semantic-admission.json` | `944e3cf661feed02112f769ea6c5eac66574eba8f6620b14727c561b71e44b2e` | 8,539 |

## Package6 generated headers and Super help smoke — 2026-09-03

This earlier checkpoint predates P4 and the diagnostic dependency failure/readback.

**P3 capture closes at 23:23:18 UTC**, exit **0**, with complete streams,
empty stderr and **28.334-second** transport. The **23:26:15 UTC** admission
replays the original validators and four omission cases, preserving 68 controls
and 14 actual records. Both generated APEX headers are present and paired,
totaling **3,678 bytes**, alongside **two query/command rows**. The observed
`mkbootimg` precompile recipe reaches an unqueried `mkbootimg.py.srcszip` input,
not a qualified source endpoint. Full header closure, producer provenance,
PYC, runtime and the complete 548-source guard remain unqualified.

**The generated Super tool's actual `--help` run closes at 23:22:11 UTC**,
native exit **0**, producing the expected **1,564-byte help text** in
**0.458 seconds**, with empty stderr and paired current-tool identity.
The original host wrapper exits **1** on namespace JSON token ordering. A
separate host-only derivative corrects only that ordering, retaining the
complete argument comparison and all other predicates; **23 ROOT tests**
and actual replay pass. The original failed receipt remains unchanged and
no native command is rerun. This admits the generated program's entrypoint/help
execution only: full library/runtime, source preservation/full-source guard,
functional Super and `super.img` assembly remain unverified.

Diagnostic-build qualification, compiled policy, signature trust/ABI, full VINTF,
super/physical fit, OTA and boot remain open. No phone operation or additional
artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/next-archive-inputs-v1/next-two-root-inputs-v1/next-packaging-header-inputs-v1/root-dispatch-v1/actual-v1/actual-admission-v1/review.json` | `c67c64b8aad2407df8ab18238455f67122ce14ec8bcd1029799e116f020d7afc` | 18,167 |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/next-archive-inputs-v1/next-two-root-inputs-v1/next-packaging-header-inputs-v1/root-dispatch-v1/actual-v1/root-replay.json` | `fbcda3f1de6f4fdd3ffd9e83697b24fc7b49bd24d4d9bee354115c933c0dfdcf` | 346 |
| `final-avb/package6-super-continuation-v1/tool-assembly-preparation-v1/native-producer-v1/environment-scope-fix-v1/runtime-smoke-v1/outer/root-dispatch-v1/actual-v1/failure.json` | `1334312e5e55c0af1d42aaf588eebb156b83af7cbeef4304d151a6a352be3b62` | 3,517 |
| `final-avb/package6-super-continuation-v1/tool-assembly-preparation-v1/native-producer-v1/environment-scope-fix-v1/runtime-smoke-v1/argv-order-admission-v1/admission.json` | `8c52584f4928eed28f06238556cd25868369fc0aec86f6a522e8d2a4ad29b3ae` | 18,005 |
| `final-avb/package6-super-continuation-v1/tool-assembly-preparation-v1/native-producer-v1/environment-scope-fix-v1/runtime-smoke-v1/argv-order-admission-v1/root-replay.json` | `7baadf04347dd2c73a43a9db8733d43bbe835c29c5fcc5696de0b8a60db31ea2` | 674 |

## Package6 producer recovery and function-anchored BTF — 2026-09-03

This earlier checkpoint predates P3 and the generated-tool help-smoke admission.

**P2 capture closes at 22:50:46 UTC**, exit **0**, with complete streams in
**37.082 seconds**. Its **22:59:05 UTC** admission replays the original
validators and 11 omission cases, preserving all 53 controls. Four query/command
rows and **seven paired input files (352,136 bytes)** are admitted: one recovery
source, two generated APEX sources and four depfiles. Observed generated-header
inputs and the unqueried `mkbootimg` precompiled-ZIP producer do not establish
header closure, complete source provenance, production or runtime behavior.

**N9 readback closes at 22:57:27 UTC**, exit **0**, in **0.123 seconds**:
nine text files are read in 18 passes, not nine worker commands. A separate
ROOT-replayed recovery admits **four retained producer/verifier commands and
19 paired inputs**, with selected source scope and whole **9,422-byte PYC
equality**. No command is rerun or output rebuilt, and the original failed
wrapper/guest flags remain unchanged. The readback does not itself admit source
or worker semantics. Current generated-artifact identity, full container framing,
composition, program entrypoint/runtime and `super.img` remain unqualified.

**Function-anchored BTF semantic review closes at 23:03:12 UTC.** Eight saved-proof
tests consume all 37 slices (1,552 bytes) and resolve the possible predecessor
extents. `complete_formation`'s declared first parameter selects `module` type
**257**; only member 20, **`sig_ok`**, spans bits **[3016, 3024)**, byte **377**.
The global census still has two `module` types; its completeness and function
uniqueness are closed-parser observations, not replayed by these sparse slices.
The **23:05:34 UTC** conditional join matches that declaration to the same-name
code's byte-377/bit-0 bypass. Under the stated helper/loop, declaration and normal
memory/call conditions, the reviewed search supports protected-name membership
and a nonnull returned **X0 pointer** leading to local **-13** rejection. The
comparator's signed W0 is internal to the search, not the caller's pointer test.
Independent review closes at **23:11:19 UTC**, passing **11 denied-I/O tests**
and joining the exact member-extent and conditional-gate reports without findings.
This does not establish live X0's type, a current `sig_ok` value, signature trust,
whole compiled policy, or any module's admission/ABI outcome.

Full source/runtime, VINTF, super/physical fit, OTA and boot remain open.
No phone operation or additional artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/next-archive-inputs-v1/next-two-root-inputs-v1/root-dispatch-v1/actual-v1/actual-admission-v1/review.json` | `e62ae6b2e763c7b82b064231c0ac6bda8ae66ab87ed2c1a1eb964bf061e8203f` | 16,131 |
| `final-avb/package6-super-continuation-v1/tool-assembly-preparation-v1/native-producer-v1/environment-scope-fix-v1/observer-readback-v1/worker-stdout-successor-v1/root-dispatch-v1/actual-v1/completion.json` | `f7ff3c9a0398b731ff899c98bb01ec37a2b367cecdfae8b98b0ea4dc1489b2dc` | 3,725 |
| `final-avb/package6-super-continuation-v1/tool-assembly-preparation-v1/native-producer-v1/environment-scope-fix-v1/parse-recovery-admission-v1/observer-schema-fix-v1/actual-admission-v1/recovery.json` | `7c78e2a8bbb99598d492380ef549ecd14ea1cfcfc8e8f78f20d72584cdc1e7e1` | 6,387 |
| `final-avb/package6-super-continuation-v1/tool-assembly-preparation-v1/native-producer-v1/environment-scope-fix-v1/parse-recovery-admission-v1/observer-schema-fix-v1/actual-admission-v1/root-replay.json` | `2472877a8b806d950d6ef102a409930c092d13b8b10b57bd24c6fd99ea77ab97` | 669 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/func-anchored-btf-capture-preparation-v1/postcapture-review-v1/review.json` | `eafe53b1abd81105f10dceb2be8a76456cc891ff62b1c3596430aa1ab5665050` | 15,159 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/func-anchored-btf-capture-preparation-v1/postcapture-review-v1/conditional-gate.json` | `13a5fce3b1fe754c2ff6c0b6b4834aa6483f5eeb618d49fbdd6c7b1cc8702d32` | 7,979 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/func-anchored-btf-capture-preparation-v1/postcapture-review-v1/independent-review-v1/review.json` | `ce3134d74820d4c562dd89881fbe4596dbadb3c7d605f7b342b10869d918db61` | 15,913 |

## Package6 producer tools and kernel BTF — 2026-09-03

This earlier checkpoint predates P2 admission, producer recovery and the function-anchored declaration review.

**LN's finite producer review closes at 22:18:22 UTC.** All **33 object
recipes** match the prior ordered archive inputs, and the **4,939-byte RSP**
equals those 33 ordered targets. Original validation and negative checks pass.
This is not inspection of the built archive's member table. Paired tool
metadata and an install-only `mkbootimg` recipe do not qualify production,
complete source/header provenance, embedded Python or runtime behavior.

**Machinery capture closes at 22:23:04 UTC**, exit **0**, with full streams,
empty stderr and the local process reaped in **0.157 seconds**. All **23
controls**, strict idle and sole ownership pass; ROOT replays both validators.
The observed env/Python executables are **AArch64**, while nsjail is **x86-64**.
Python and nsjail match retained identities; env's identity is newly observed.
These metadata observations do not prove cross-architecture execution or
loader/dependency closure, and no producer is built by this capture.

**The subsequent Super tool-assembly wrapper fails at 22:44:51 UTC** after
**604.709 seconds**. All four build/verifier commands report exit 0 before
the missing `primitives.parse` raises `AttributeError`; the failed transport
and guest/source admission flags remain unchanged. Recovery capacity,
controls, idle and ownership checks pass. ROOT's separate original source-guard
replay also passes, without rewriting the failed guest record. Generated
outputs remain candidates awaiting readback/admission; no rebuild, runtime
entrypoint or `super.img` success is claimed.

**Kernel search/BTF capture closes at 22:34:17 UTC**, exit **0**, with full
streams and **1.936-second** transport. It preserves 42 child inputs and 55
outer controls, a **4,096-byte `strcmp` window** and **four guard bytes**.
The bounded BTF parser finds **two complete `module` structure candidates**;
the result is **ambiguous**, with no unique first-parameter or member mapping.
**The static-review handoff closes at 22:47:43 UTC**: independent review passes
**24 tests and 77 word-mutation checks**, supporting conditional unsigned-byte
ordering sign and the on-disk guard match, not exact difference magnitude or
runtime guard success. The type census remains a reported producer result,
not a reconstruction from the retained header-only BTF proof. Compiled field
meaning, pointer validity, policy and runtime behavior remain unverified.

**FIFTEEN v2 stream-checks 15 selected ZIP members**: 11 expected hashes match
and four META texts retain **27,089 bytes**, with 27 held inputs unchanged.
It decodes **50,095,806 bytes**, reading **38,581,286 selected physical bytes**
plus **1,687,346 structural bytes**; components are hashed without extraction,
and no partition-image member is opened. The **22:47:30 UTC** host join closes
a **29-member identity union and 10 metadata texts**, rechecking 35 records.
Full constructor, source/runtime, CPIO permissions and boot-consumer qualification
remain false; no original boot projection or replacement payload is executed.

Compiled policy, ABI/trust, tool and boot runtime, full VINTF, super/physical
fit, OTA and boot remain open. No phone operation or additional artifact
cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/next-archive-inputs-v1/root-dispatch-v1/actual-v1/actual-admission-v1/outer-review.json` | `62a5867514fe9f107ffd8370bb9f280776545f8092ec1d6b26b487631064bf39` | 46,952 |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/next-archive-inputs-v1/root-dispatch-v1/actual-v1/actual-admission-v1/producer-frontier.json` | `7714d2f8eae20c423afc8b1678cfc1b62552dc908239a639aab723035e594ea7` | 56,456 |
| `final-avb/package6-super-continuation-v1/tool-assembly-preparation-v1/native-producer-v1/machinery-capture-v1/root-dispatch-v1/actual-v1/completion.json` | `4a9109d5d23d7dd65bf204c91ca77393454dc698d3721db7fc0cb846aee19238` | 3,571 |
| `final-avb/package6-super-continuation-v1/tool-assembly-preparation-v1/native-producer-v1/machinery-capture-v1/root-dispatch-v1/actual-v1/root-replay.json` | `35f3bf7f2f97327117cd0e89cc225765003f964f06a7cc7e4cca7a96aea1d416` | 501 |
| `root-package6-protected-search-btf-capture-dispatch-v1/completion.json` | `67e9bb380119c6423209b02acd33665aef318842b83ef5ef94ab1f31d2070d42` | 18,206 |
| `final-avb/package6-super-continuation-v1/tool-assembly-preparation-v1/native-producer-v1/environment-scope-fix-v1/root-dispatch-v1/actual-v1/failure.json` | `07d822432b30ddaa5eeb5d53ba75bf54cb267ccfc4d1b4fbb7b09ef18c905ff9` | 15,361 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/protected-search-btf-capture-preparation-v1/postcapture-review-v1/handoff.json` | `c77729a73271c20ec979469733df4e4f7a85e50ea67b77cda3dd0ee9edaabd91` | 5,767 |
| `final-boot-content/package6-preparation-v1/consumer-v4/next-producer-result-admission-v2/fifteen-member-zip-preparation-v2/actual-v1/completion.json` | `a73102846ace5f1e797f5c95207f138ae1a6c9087c47b784a0c52aa65ce98475` | 79,356 |
| `final-boot-content/package6-preparation-v1/consumer-v4/next-producer-result-admission-v2/fifteen-member-zip-preparation-v2/result-join-v1/report.json` | `a85bdba518240a8a2540563c420ab29af34ee6f2022550dd26498c9dba1ed960` | 50,011 |

## Package6 boot-property reviews and follow-up captures — 2026-09-03

This earlier checkpoint predates LN producer interpretation, machinery capture and the BTF type result.

**Boot's host admission closes at 21:31:03 UTC**, replaying the original
driver/emitter, graph/query, native-file and source-control predicates against
the actual NR capture. It reruns **11 adapter and eight prior-contract tests**
(**19 total**). The handoff binds the exact **7,341-byte response-file
publication and readback**. All three boot-source
semantic proofs remain unqualified, `source_capture.review` stays null, and
historical first-stage action and the complete boot constructor remain open.

**Property observation validation passes at 21:36:32 UTC**, with **19 tests
and 17 held inputs**. Original policy/observer replay joins 64 ordered archive
members, three compile/source listings and paired response/vendor-init text.
These are source and command observations, not effective preprocessing,
packaged-provider selection or runtime-property proof. Final source membership
remains restricted to the original 72 rows; sidecar observations are not added.

**Kernel search capture closes at 21:54:18 UTC**, exit **0**, with full streams,
empty stderr and the local process reaped in **1.386 seconds**. It preserves
32 child inputs and 48 outer controls and captures two **4,096-byte** windows
for `cmp_string` and `bsearch`. **Limited static review passes at 22:02:24 UTC**,
with **16 tests and 48 word/listing checks**: the callback load/call coordinate
and 64-bit search-count, midpoint and conditional-return paths are observed.
`strcmp` remains an `unknown_non_text_selector`, not proven non-executable;
its comparison semantics, guard outcomes, pointer/count validity and compiled
policy remain unverified. BTF boundaries remain metadata only, without body
or type interpretation.

**Six selected boot texts are captured at 22:02:57 UTC**, totaling **379 bytes**,
with exit **0**, complete streams and **0.173-second** transport. The bounded
ZIP reader consumes **1,685,506 bytes** with the original archive guard unchanged;
no image is opened or extracted, and no whole-archive hash is repeated.
The metadata matches source-derived candidates; full constructor qualification
remains open.

**The 68-call producer follow-up closes at 22:14:12 UTC**, exit **0**, with
full streams, empty stderr and the local process reaped in **217.458 seconds**.
All **60 controls**, strict idle and sole ownership pass. One fixed response
file retains **4,939 bytes**, and `mkbootimg`/`soong_zip` metadata observations
match across both passes. ROOT replays both original validators with all held
controls unchanged. No queried executable or image body is exported, and
neither the tools nor producer recipes execute. Deeper consumer review remains pending;
this capture adds no source/PYC, producer/runtime or full VINTF qualification.

Fresh init reproduction remains unexecuted; diagnostic instrumentation is
unbuilt and unrun. ABI/trust, full
boot-source/runtime, VINTF, super/physical fit, OTA and boot remain open.
No phone operation or additional artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-boot-content/package6-preparation-v1/consumer-v4/next-producer-result-admission-v2/handoff.json` | `64a133616995e2b97a326d027bb25b18ab5f73fa5dd103a1d9be0a2a63af79fd` | 15,308 |
| `final-vintf/property-qualification-current-v1/ngb-property-successor-preparation-v1/actual-retry-v1/findings.json` | `2c4819876f37939ae718cdd639f51b889818730a0be2870d24191c0b83e94a99` | 25,887 |
| `final-vintf/property-qualification-current-v1/ngb-property-successor-preparation-v1/actual-retry-v1/validation.json` | `2e8780a17f7b3c70b44ef02b5d9000862db5b1826d3a0654fc13260d06592dac` | 13,382 |
| `root-package6-protected-search-capture-dispatch-v1/completion.json` | `1d0707227c33cd892febe3aaf6c46cfa527c432f75f62f136bd2e6790f53e093` | 13,894 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/protected-search-capture-preparation-v1/postcapture-review-v1/independent-review-v1/review.json` | `c49785acdfd8549055f552e6d22998e6253eff52ef5e852b2b02380b3aeff7cb` | 13,306 |
| `root-package6-six-text-dispatch-v1/completion.json` | `7c971c952c810970815bd2d84499e2bdaea30e79b902de2ddc281af59bbcb535` | 2,214 |
| `final-boot-content/package6-preparation-v1/consumer-v4/next-producer-result-admission-v2/six-text-zip-preparation-v1/constructor-join-v1/report.json` | `46d4b7a47dcc30acf817ef8fb13696e65151ad83c7b7040cb74eaae060de3560` | 12,311 |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/next-archive-inputs-v1/root-dispatch-v1/actual-v1/completion.json` | `4a46f272eb5ef7035f090a02ad4696c9835831ea0726775e3df583012b035188` | 8,048 |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/next-archive-inputs-v1/root-dispatch-v1/actual-v1/root-replay.json` | `a9c4cfb2cef345889a41ad95ce8b8e61a8f28e9195da36019a91ab307d6bbb82` | 726 |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/next-archive-inputs-v1/root-dispatch-v1/actual-v1/root-replay-field-clarification.json` | `0cb28dd648c40ef75f101ce0cf0a7f8e203df0cc032acc3c07bf0e2d940ea685` | 426 |

## Package6 protected-export gate and libvintf producer query — 2026-09-03

This earlier checkpoint predates the scoped boot/property reviews and search-window capture.

**Kernel gate capture closes at 21:23:03 UTC**, exit **0**, with the local
process reaped, full streams and empty stderr in **1.427 seconds**. Thirty
child inputs and 44 outer controls remain unchanged. One **4,096-byte**
`complete_formation` window is captured; two other exact function names are
absent from the decoded name table, **not proven absent from compiled code**.

**Static local-gate review closes at 21:31:11 UTC.** Two call sites load a
**64-bit count** and pass table arguments; bit 0 at incoming-object byte 377
can bypass those calls. A nonzero result reaches a conditional local **-13**
return path, assuming normal external returns and no stack-check diversion.
ROOT independently decodes the raw words. Callback/search implementation,
object-field meaning, runtime count, complete policy behavior, trust and ABI
remain unknown; this is not a module-admission or runtime execution result.

**Six read-only libvintf query/command calls close at 21:25:35 UTC**, exit
**0**, with full streams, empty stderr and the local process reaped in
**46.015 seconds**. All **45 controls**, strict idle and sole ownership pass.
Original validation and nested policy parsing replay independently; **zero
producer-artifact or response-file body bytes** are read. No producer build,
new source/PYC admission or runtime/provenance qualification is established.

The narrow AIDL command checker now treats `-c` as a unary option and locates
the terminal source correctly; **25 host tests pass**. Earlier incorrect
projection evidence is retained, and the **127 missing-name metadata negative
is unchanged**, without proving absent runtime services. Further query/code
preparations have not executed; diagnostic instrumentation remains unbuilt
and unrun. Full boot-source/runtime, VINTF, super/physical fit, OTA and boot
remain open. No phone operation or additional artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-package6-protected-export-capture-dispatch-v1/completion.json` | `ec6d486b3ff1e2a877bced39f619baffd6a96a67fd98afd28548880f547499a4` | 13,892 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/protected-export-capture-preparation-v1/postcapture-review-v1/static-gate-review.json` | `f859fcca5c52df27850a695f4eb47debfe8a476b9c1981bf2339e10990bce5bf` | 11,003 |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/root-dispatch-v1/actual-v1/completion.json` | `05bd231b57b91192fc5b15a5dae09d70c3e8b0e4fec5da9d40eec07145b1a04e` | 4,584 |
| `final-vintf/coverage-policy-successor-v1/libvintf-producer-query-preparation-v1/root-dispatch-v1/actual-v1/actual-admission-v1/outer-review.json` | `dc6c6cf5661bc848564588be140f657976a6634d1fda462c0cc9b8f8a4b0a178` | 39,053 |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/shared-discovery-success-v3/producer-followup-preparation-v1/next-producer-input-batch-v1/implicit-libc-retry-v1/root-dispatch-v1/actual-v1/actual-semantic-review-v1/aidl/checker-correction-v1/independent-review/review.json` | `3f85406243bfe3a2022d4ad614a7519c99dc72d604e42079ca5fd3396ce72921` | 15,279 |

## Package6 producer retry and pointed-name reference review — 2026-09-03

This earlier checkpoint predates the gate-window and libvintf producer-query results.

**The corrected producer retry completes at 21:02:17 UTC**, exit **0**, with
the process reaped, full output streams and empty stderr in **813.91 seconds**.
The **22,969,748-byte** result is retained; **104 controls**, source/input
preservation, sole ownership and strict idle checks pass. **Original-driver,
source and PYC admission passes at 21:16:56 UTC**, with six complete source
callbacks and 16 graph metadata rows preserved; ROOT's source replay also
passes. Ten fixed query/command calls and 11 nested boot query rows retain
four core bodies (**60,207 bytes per pass**) and five boot file observations.
Historical compilation is not rerun, and nested boot observations are not
qualified source proofs or a completed boot constructor. The original failed
batch remains preserved and unadmitted. Deeper boot, property, super and AIDL
consumer reviews remain separate from this scoped closure.

**Pointed-name capture and conditional reference assessment close at
21:11:16 UTC.** Both name tables satisfy the reference byte-order precondition,
and all six capture sidecars and the ordered join reproduce exactly. ROOT's
**20-test** review replays **all 637 original payload comparisons**, all five
detail shards and 90 input states. Marker cohorts describe observed
bytes, **not cryptographic trust**. Actual provider selection, stage/load order,
compiled count types and policy use, source equivalence and ABI remain open;
no module-admission decision is established.

The six-query continuation and five-selector/three-window kernel preparation
have **not executed** at this checkpoint. VINTF diagnostic instrumentation is
host-only and remains **unbuilt and unrun**. Full boot-source/runtime
qualification, VINTF, super/physical fit, OTA and boot remain open. No phone
operation or additional artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/shared-discovery-success-v3/producer-followup-preparation-v1/next-producer-input-batch-v1/implicit-libc-retry-v1/root-dispatch-v1/actual-v1/completion.json` | `9761a68b6854fd2544314aa01ed9736c9a6be93063502a3c1a26c281cedf0669` | 19,301 |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/shared-discovery-success-v3/producer-followup-preparation-v1/next-producer-input-batch-v1/implicit-libc-retry-v1/root-dispatch-v1/actual-v1/actual-semantic-review-v1/admission.json` | `b49bf50bb3a4b1050c8909c1f65401cd6184a5c4ea3de0bde0f0132522f7671e` | 12,992 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/pointed-string-capture-preparation-v1/postcapture-review-v1/handoff.json` | `6bf5b96f095fda9efa2742b1d52bd8b9bded4c042e89596d8fb59868dbeba140` | 16,582 |
| `root-package6-pointed-name-reference-review-v1/review.json` | `3ddad0f0dbb82758ecf07e7bafc8adf47f328dec3a72cbcd8225fc82eecb347d` | 5,143 |

## Package6 static kernel mapping and pointed-string capture — 2026-09-03

This earlier checkpoint predates the successful retry and closed pointed-name reference review.

**Saved-byte conditional static mapping passes independent review at
20:27:50 UTC**, with **40 tests**. All **9,696 table slots** are uniquely
covered by RELR and map to **9,364 candidate target offsets** under the
reviewed static-link interpretation. This does not establish runtime/KASLR
mapping, compiled count types or policy use, source equivalence, ABI or trust.

**The pointed-string capture closes at 20:45:22 UTC**, exit **0**, with full
streams and empty stderr in **0.633 seconds**. It retains **9,364 strings**
for the **9,696 original slots**, preserving **332 cross-table target aliases**
and **222,399 name-plus-NUL bytes**; the longest name is **58 bytes**. ROOT
rechecks 54 child inputs and 71 outer controls. Actual capture and derived
output checks pass; deeper pointed-string semantics remain pending.

**Three libvintf source files are captured at 20:26:08 UTC and host-published**:
`CompatibilityMatrix.cpp`, `VintfObjectUtils.h` and `Android.bp`, totaling
**28,331 bytes**. Both project observations are clean at
`69c456ea4aa2f503a2904cfbc11f279a3b2efb09`. This is source-only evidence;
the diagnostic implementation remains **unbuilt and unrun**.

The prior next-producer batch fails at **20:24:10 UTC** on the repeated
implicit `libc.a` edge. Its original failure is preserved, with no accepted
completion; capacity, control, idle and ownership recovery checks pass. The
corrected retry is now **in progress, with no successful capture yet**.
Compiled protection policy, ABI/trust, full boot-source/runtime qualification,
VINTF, super/physical fit, OTA and boot remain open. No phone operation or
additional artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/relocation-capture-preparation-v1/postcapture-review-v1/semantics-v1/review.json` | `aebf93862bebefd1957aeedbe229d912c2540ca88813e10cc2a8584253616975` | 275,842 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/relocation-capture-preparation-v1/postcapture-review-v1/semantics-v1/independent-review-v1/review.json` | `b0e5e13fbdc49cea182d839cd39ae9a96cc41bd4c7f0b7e0eee35ca76431922d` | 278,827 |
| `root-package6-kernel-pointed-strings-dispatch-v1/completion.json` | `2753e6c7836834d28eba9bc02038ff1fe1d5aa5b6577a93d4b95fbe69f13cc7a` | 35,034 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/pointed-string-capture-preparation-v1/actual-v1/capture.json` | `a651728f3e29b17426c45b7ac3846772a1ce5709c3d1244e3f9d5761b23fdd2a` | 273,285 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-source-capture-v1/actual-v1/completion.json` | `cd21bcb49b52b179505d10b40baac8676656d5aaea3f33a273f7752697dee8e5` | 2,398 |
| `final-vintf/coverage-policy-successor-v1/diagnostic-source-capture-v1/host-bodies-v1/publication.json` | `047e40885e9f008c7bf86648f72cd0f7f7648dabc4f1304ded95ade2ed1f9aa5` | 13,925 |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/shared-discovery-success-v3/producer-followup-preparation-v1/next-producer-input-batch-v1/root-dispatch-v1/actual-v1/failure.json` | `f01eca7d4d0a7eeb8876f47ffc59a1ba42e1844c632b59834b6939556e1a5823` | 17,209 |

## Package6 conditional stages and kernel relocation capture — 2026-09-03

This earlier checkpoint predates conditional static mapping and pointed-string capture.

**The vermagic comparison now covers all 637 distinct payloads / 914 current
module instances.** Every payload matches under reference `has_crcs=true`
suffix-comparison semantics; **103 payloads match literally**, while **534
have differing prefixes**. This does not select the current compiled loader
branch or verify ABI compatibility, signature trust or loader order.

**Conditional early-ramdisk stage review passes at 20:02:35 UTC.** Restricting
providers to the kernel plus ramdisk leaves **nine missing Wi-Fi expectations**,
whose consumers are outside both the **154-module normal** and **426-module
recovery** closures. Both closures have **zero nonmatching expectations and
zero findings**, assuming simultaneous availability of modules reached through
the recorded load roots and `modules.dep`. Mount timing, soft dependencies,
blocklists, actual provider selection and module insertion remain unverified.

**The kernel relocation capture closes at 20:06:38 UTC**, exit **0**, with full
streams in **1.440 seconds**. It retains **47,072 relocation-body bytes** and
**16,416 code/literal-window bytes**, with 42 child input states and 56 outer
controls rechecked. A unique supported literal selector is observed, not a
verified pointer mapping. Independent capture admission passes **35 tests**,
including retained-byte consistency and genuine transport closure. Relocation
interpretation, algorithm equivalence and compiled policy use remain unverified.

ABI, trust, full boot-source/runtime qualification, VINTF, super/physical fit,
OTA and boot remain open. No phone operation or additional artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-package6-all-current-vermagic-review-v1/review.json` | `a0c322c7d985ec9996b7f39075b12a2f67eba7befb0738de2d990e16c8d49e0c` | 12,089 |
| `final-boot-content/package6-preparation-v1/current-ramdisk-abi-join-v1/early-ramdisk-stage-v1/independent-review.json` | `53935d3bcac21716edb48af60309fa6bb7c9755c62378b5cef6bdbea1cfecde4` | 81,407 |
| `root-package6-kernel-relocation-dispatch-v1/completion.json` | `489be9e018a71c2c576d13aa4e616a28f46abb89e7c4dc4edf7ce66c0ed5e454` | 18,209 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/relocation-capture-preparation-v1/actual-v1/capture.json` | `327f593d2c0cd46ca6c99d91f812d669f08aa67cdd77a99b07d4120bc7c76690` | 220,432 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/relocation-capture-preparation-v1/postcapture-review-v1/capture-closure.json` | `72f225ab24fd471b160e82af5b27fc55eec0b1c2ad6b76837d873722d00a7ae3` | 8,233 |

## Package6 current module union and source-copy origin — 2026-09-03

This earlier checkpoint predates extended vermagic, conditional stage review and relocation capture.

**The current ramdisk/DLKM union closes the 718 previously missing CRC
expectations**, using **49 now-current ramdisk providers**. ROOT's exact
denied-I/O replay passes at **19:43:35 UTC** across **914 module instances,
637 distinct payloads and 36,963 CRC expectations**. Remaining missing-provider
counts are zero, but **20 ambiguous/mixed rows remain**, including **two with
both matching and conflicting provider CRCs**. This is not unambiguous provider
selection or a pass for ABI compatibility, signature trust or loader order.

**Source and copy origin are verified for 21 boot-input copies, 3,783,771 bytes.**
The genuine successful child is admitted read-only at **19:47:40 UTC**, after
correcting an outer checker that wrongly required every source-check boolean
to be true. The original failure stays preserved; neither the child nor copy
publication is rerun. The subsequent original-driver/source-origin API review
passes with 120 held inputs and 127 consumer guards. Full boot-source semantics,
first-stage producer, complete graph/log coverage and runtime remain open;
`source_capture.review` remains null.

The **19:45:50 UTC raw kernel-table handoff** preserves **590 protected-export
and 9,106 permitted-import eight-byte words**. These are raw numeric candidates,
not mapped symbol names or verified compiled protection-policy behavior.
The AIDL coverage successor preserves all 127 metadata negatives; its actual
production-API witness, binding and native qualification remain pending.
The next boot/property/super/AIDL native batch has not executed at this
checkpoint. Full VINTF, super/physical fit, OTA and boot remain open. No phone
operation or additional artifact cleanup occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-package6-current-module-union-review-v1/review.json` | `ffbf7fb3c835689f71a3317083cc96479660998004a168a25e3eb9acb687aafb` | 12,014 |
| `root-package6-boot-source-origin-dispatch-v2/read-only-admission-v1/completion.json` | `d1b5b730f6b0bee913b189a4893c17b9e8ca4d3d8a91119d33d6cfbd40809f8d` | 4,975 |
| `root-package6-boot-source-origin-v1/successor-v2/actual-semantic-review-v1/completion.json` | `c21a7e4eb578929c9b9bbfddd21b77e90d8e2a410a23d212c22da3d66681b4fe` | 4,929 |
| `final-boot-content/package6-preparation-v1/kernel-abi-gap-assessment-v1/table-capture-preparation-v1/postcapture-review-v1/handoff.json` | `c5bc03837c33600e62c895501434a63cd02c262e588360344a5e297848abcb50` | 136,125 |

## Package6 corrected captures and negative AIDL audit — 2026-09-03

This earlier checkpoint predates the current module union and source/copy-origin admission.

**The corrected NGB retry closes at 19:13:14 UTC**, exit **0**, with complete
streams in **641.115 seconds**. It records nine query pairs/18 calls, four core
bodies (**566,527 bytes**) and 21 boot-input bodies (**3,783,771 bytes**), with
64 controls and source/input preservation verified. The original capture-limit
failure remains separate; this return is not full source-origin, ROM or VINTF
semantic qualification.

**The compiled-metadata AIDL coverage audit returns a negative result**, exit
**65**: **127 missing names, 142 affected tuples and 13 matched names**. ROOT's
exact replay passes at **19:25:27 UTC**, not the audit itself. This does not
establish absent services, runtime failures or a build defect. Metadata/binary
provenance, runtime closure and interpretation remain open; the result is not waived.

The kernel-static capture is admitted at **19:09:11 UTC** after correcting a
postflight reader that rejected empty stderr; the original child had exited 0
and is not rerun. Its failed postflight remains preserved. ROOT's **19:21:19 UTC**
vermagic replay finds **103/484 full literal matches** and **484/484 matches
under reference `has_crcs=true` semantics**. The current compiled loader branch,
module ABI and signature trust remain unproven.

**Vendor-ramdisk capture-v2 returns cleanly at 19:22:53 UTC**, with stream
readback admitted at **19:23:41 UTC**: **430 module payloads / 47,961,360 bytes**, with
its exact temporary scratch removed. The earlier wrong-sink attempt was killed
with child exit **-9** and a partial stream; it cannot be admitted or relabeled
as the fresh corrected run. Deep review and the current ramdisk/DLKM ABI union
remain pending; no reduction of the earlier 718 unbound expectations is claimed.

Mac dependency admission-v4 also passes at **19:22:34 UTC**, covering **195
file-backed dependencies and 244 guarded inputs**; complete dynamic runtime
closure and boot are not established. Source-origin follow-up and the next
combined batch remain unqualified. Effective properties, full
VINTF, super/physical fit, OTA and boot remain open. No phone operation,
additional artifact cleanup or push occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/shared-discovery-success-v3/producer-followup-preparation-v1/next-grounded-batch-v1/merge-producer-retry-v1/root-dispatch-v1/actual-v1/completion.json` | `ae30a51500c5afe6a3c25e7dd5b3bd724fe4028661183c6a277a169b6f81da2c` | 15,401 |
| `root-package6-aidl-negative-review-v1/review.json` | `4287de9035e42fb045739247d504bf97089dce2c29f504a7e8424550e47dfa61` | 4,221 |
| `root-package6-kernel-static-capture-v1/admission-v1/completion.json` | `3928149212be2189b5b05e1548bfdf190a9750a9a6291b3d2bdfef7597eeb724` | 18,891 |
| `root-package6-kernel-vermagic-review-v1/review.json` | `b977bbf3e4de369c104d861a984595595baff9e7010e554511d0c0b631df4136` | 56,413 |
| `root-package6-vendor-ramdisk-capture-v2/stream-readback-admission.json` | `30c2c3e102918c37f58d6e0f45ea441cf91b571971fa18bf36654c2a01e4b636` | 2,531 |
| `root-package6-boot-runtime-v4-review-v1/review.json` | `4d83ff76d88f4d3f22680c20de610f08895cedb7b6fbf0731061030f3555cf29` | 2,119 |

## Package6 independent VINTF inputs and retained ABI gaps — 2026-09-03

This earlier checkpoint predates the corrected captures and negative AIDL audit.

**Independent host review admits the 298 selected VINTF input members.** The
recorded publication copy/readback chain accounts for **297 unchanged members**
and the expected `META/vbmeta_digest.txt` replacement; this is not fresh archive
body inspection. Two ramdisk and two DLKM property files remain outside the
five-image projection. **76 focused tests pass**, and ROOT's exact replay
rechecks **109 held controls**. The unchanged `independent_input_review` proof
is the **third of six roles staged on the host**, mode **0400**; native staging,
aggregate qualification and full VINTF compatibility are not established.

**Retained ABI analysis completes for all 484 current DLKM modules, without
verifying ABI compatibility.** Of **29,503 CRC expectations**, **718 remain
unbound to current providers**. The 49 historically matching ramdisk payloads
are candidates only, not admitted current providers. ROOT independently
reproduces the complete authority and analysis with held inputs and outputs
unchanged. Current ramdisk binding, compiled vermagic, module protection and
signature trust remain unresolved; this is not a successful module-load test.

The original **next-grounded-batch (NGB) capture fails at 18:37:47 UTC**, after
**655.888 seconds**, on a capture limit: rows 0–15 are complete, row 16 is
truncated and row 17 is not reached. It returns 21 boot-input bodies but none
of the four requested core bodies. Source preservation and recovery checks
remain recorded; partial output is not a completed discovery result. A retry
is separately prepared, with no retry result admitted here. Host runtime,
effective properties, AIDL, full VINTF, super/physical fit, OTA and boot remain
open. No cleanup or phone operation occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-vintf/independent-input-current-v1/root-replay.json` | `58ababd99aa314ff286f057b42d03b3bead45d83284f594b3108c63b4c86dbb7` | 323,595 |
| `root-package6-independent-input-review-v1/review.json` | `522f67ed81fcf51e40443d234b9f532aa95b909b088ebc360f9ef9eded3852d1` | 1,133 |
| `root-package6-independent-input-review-v1/host-staging.json` | `235a567ae66cb618849528de940fa9e9666d9e4f12a4282adafc99289bbef82a` | 908 |
| `root-package6-dlkm-abi-review-v1/review.json` | `673166cb4e41360b5b0382194b0d60683f34df86ec91120d07756b1a8aa0cbbc` | 4,424 |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/shared-discovery-success-v3/producer-followup-preparation-v1/next-grounded-batch-v1/root-dispatch-v1/actual-v1/failure.json` | `0a3b9938d3fb95c7045315a3ff4948ce6e2b8cf0b71b4fccdd5e4d9db734c492` | 14,709 |

## Package6 DLKM reference-model semantics and loader-text binding — 2026-09-03

This earlier checkpoint predates independent input review and retained ABI analysis.

**The 11 exact retained DLKM metadata bodies, 284,308 bytes, pass current
semantic reuse at 18:10:30 UTC**; ROOT reproduces the original result at
**18:11:53 UTC**. The reference `system/core` model selects **101 system
modules**, excluding the GKI `zram`/`zsmalloc` pair, and **380 vendor roots**
from 381 vendor modules, excluding `ipclite_test`. The vendor selection reaches
**382 modules**, including two system modules. The selected closures have no
missing mandatory requests or hard/pre cycles; **15 unresolved optional
pre-requests across nine names** remain explicit. This is conditional on the
reference loader model, not a claim that every graph owner has no missing
request, or that these modules actually load.

**Current loader-text binding passes at 18:26:49 UTC**, followed by ROOT's
exact replay at **18:29:00 UTC**. It joins **72 framework init RC files plus
the root environment file**, six vendor text bodies, declared `androidboot.hardware=qcom`
and `ro.zygote=zygote64`, candidate image import paths and DLKM directory links.
ROOT reproduces 29 analysis fields with 29 held inputs; eight focused loader
tests pass. Retained text origins and ZIP-only ramdisk text remain distinguished
from fresh execution or decoding of boot-image components.

The separate top-level early-init request for **`msm_11ad_proxy` has no matching
current DLKM module**. Built-in or prior-stage availability is unverified; this is not
proof of a boot-fatal failure. Effective property selection, competing init
declarations, current executable/source equivalence, host-runtime qualification
and loader execution remain open, as do module ABI/signature trust, full VINTF,
super/physical fit, OTA and boot. No cleanup or phone operation occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-boot-content/package6-preparation-v1/dlkm-membership-preparation-v1/metadata-semantic-reuse-v1/review.json` | `a0164ada1be2e576199e3dbff5db56213497f5ebc8d3eb9b0b005633270abbbf` | 29,521 |
| `root-package6-two-dlkm-result-review-v1/metadata-semantics-review.json` | `e6869cd5493499de834a74c8ff30134cd1f7785f5b4b59a0461f8fdbede19242` | 1,809 |
| `final-boot-content/package6-preparation-v1/loader-binding-v1/review.json` | `d1ea8a005f57efd6f749eab367f287db5630f75b32013543c4e85e3832c2e037` | 127,958 |
| `root-package6-loader-text-review-v1/review.json` | `5fc571327d2bea3164e62363d61bbf44fc8c2a1c2eff9b39114013d6177c2e7e` | 1,236 |

## Package6 DLKM membership and two-node semantic admission — 2026-09-03

This earlier checkpoint predates DLKM metadata semantics and current loader-text binding.

**Both current DLKM image scans pass at 17:54:55.361365 UTC**, in **2.465
seconds**, with unchanged inputs and strict-idle/sole-owner checks. ROOT's
separate membership replay passes at **18:02:37 UTC**: all **103 system_dlkm
and 381 vendor_dlkm modules**, plus **11 metadata/selector files**, match the
historical corpus by path, hash and size. No modules are missing, extra or
changed. The **eight ordinary `/etc` files** remain recorded outside the
historical module-namespace comparison; equality is not claimed for them.

ROOT reproduces the original preparation's six outputs and replays the typed
proofs, complete manifests and membership comparison. **21 focused tests pass.**
Historical evidence is not relabeled as fresh execution. Metadata/selector
contents still need current semantic validation; loader-source binding,
module ABI, signature trust and actual loading remain unverified.

Separately, ROOT admits the earlier **two-node source/PYC semantic replay at
17:44:17 UTC**, including all three fixed response files (**8,274 bytes**) and
exact original source/PYC admissions. This is not producer/runtime qualification.
The five-image VINTF content projection remains verified, while runtime property
behavior, full VINTF, super/physical fit, OTA and boot remain open. No additional
cleanup or phone operation occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-boot-content/package6-preparation-v1/dlkm-membership-preparation-v1/root-dispatch-v1/actual-v1/completion.json` | `f9510161485611f545d25b9ddac1110743225f6a5c870ccc3b22e037d05b4031` | 9,755 |
| `root-package6-two-dlkm-result-review-v1/review.json` | `eb8560fc6fb59f1416e44d83a8e5933a1eb4669ca2f0a065eda7921776560ef6` | 2,514 |
| `root-package6-two-dlkm-result-review-v1/membership-review.json` | `49a2c3ba05af1127ab45b54ab8a1b332fadea829ac86e270d697207bd28554f4` | 118,634 |
| `root-package6-two-node-semantic-result-review-v1/review.json` | `f793642e67841dc6580ddf84b7f8c8a5a2351ab46e5ef388abc4719f4e5c1139` | 1,034 |

## Package6 five-image VINTF content projection — 2026-09-03

This earlier checkpoint predates DLKM membership and two-node semantic admission.

**The corrected reader captures system, system_ext and product successfully at
17:16:09.410724 UTC**, in **43.851 seconds**, with **7,838 entries**. ROOT replays
the original typed proofs and manifest parser; image hashes remain unchanged.
The earlier compact-EOF failure is preserved as a separate historical result.

**The combined five-image namespace and relevant-content projection passes.**
It joins those three captures with the retained vendor/ODM evidence, covering
**267 files: 201 VINTF, 27 property and 39 outer APEX packages**, plus **21
property-import candidates**. There are **14,807 physical entries** and
**14,761 partition-mapped entries**; 46 system-root entries outside the partition
view remain recorded. All five canonical `build.prop` files retain the observed
**0600 image versus 0644 expanded-tree** difference; permission equivalence is
not claimed. Historical vendor/ODM exporter provenance is retained, not relabeled
as execution by the corrected reader. Outer APEX equality is not payload validation.

ROOT's **17:36:01 UTC** replay reproduces the original three- and five-role APIs'
output bytes, deeply replays the retained 205-file vendor/ODM review, and checks
51 held controls. **55 focused tests pass.** This admits content projection,
not source provenance, runtime property behavior or complete VINTF compatibility.

The two-node query closes at **17:31:45.226195 UTC**, in **657.847 seconds**:
four calls, two nodes and three present response files; ROOT's envelope replay
passes with 43 held controls, while deep semantic admission remains pending.
The super precursor query closes at **17:34:25.858498 UTC**, in **28.576 seconds**,
with two calls and an observed embedded-Python PAR recipe, not a tool build or
runtime qualification; ROOT's result replay rechecks 35 controls before and after.
Independent-checker, AIDL and final VINTF qualification, super,
physical fit, OTA and boot remain open. No cleanup or phone operation occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-package6-three-image-result-review-v1/review.json` | `7362ee497a86223a753154e609979212e6715daf7f8f2d00b0f2e2557d077977` | 3,273 |
| `root-package6-five-image-projection-review-v1/review.json` | `44aefe761fd040b22894e12902e41c442211585d72822d34f008c0bdd9889ccf` | 1,243 |
| `three-image-erofs-lookback-diagnosis-v1/native-build-preparation-v1/successor-v4/completion-schema-v1/consumer-duplicates-fix-v1/isolated-build-v1/three-image-rebind-v1/downstream-projection-v1/five-role-review-v2.json` | `6ccea80cf2cd72da1595894873e35530b98726ea91f139fa26ab7fec5ac327ff` | 1,025,459 |
| `root-package6-two-node-result-review-v1/review.json` | `690a154bca7ea6e09c9ae3d6c157aed7ac7c16f9993036629ebf64b7001511e4` | 1,232 |
| `root-package6-super-precursor-query-result-review-v1/review.json` | `a09f910d9120f0001932da4ea830b22ec746fd528408ba204b068da17086ce64` | 1,251 |

## Isolated EROFS reader build and query admission — 2026-09-03

This earlier checkpoint predates successful image capture and content projection.

**The corrected native EROFS reader builds successfully at 17:07:42.997617 UTC**,
exit **0**, with **5.442 seconds** recorded by the transport. The isolated build
records **18 commands, 175 paired inputs and seven runtime files**, using the
unchanged opt-in `c814fc64…` source. Its **3,613,016-byte** binary is SHA-256
`058e53eca562da32c22eee0dcb5b2790151020dbb03c6b9f7b5da61cc9058ddd`.
ROOT's **17:08:32 UTC** exact validator replay rechecks 28 held controls and
the recorded strict-idle/sole-owner result. Pinned static-library `.a` archives
are read and linked, but no ROM image or ZIP body is read.
**Three-image projection is still pending**: this
build does not yet demonstrate the compact-EOF fix against the final images.

**Four super-tool queries pass at 17:02:42.323529 UTC**, exit **0**, in
**38.227 seconds**. ROOT's replay passes with 33 held controls checked. The
observed commands are installation copies; qualification of their preceding
producers remains pending, and no super image is built.

ROOT also admits the **eight-seed semantic replay at 17:04:41.484935 UTC**:
22 held inputs are rechecked, the complete six callback vectors and four
observation groups join to the prior capture, and the exact origins of two
producer nodes and three response-file paths are reproduced. This does not
qualify runtime closure or complete VINTF compatibility.

The eight-role FEC and published-kernel results remain verified. Image-level
EROFS validation, complete VINTF qualification, super/physical fit, OTA and
device boot remain open. No additional cleanup or phone operation occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-package6-erofs-build-result-review-v1/review.json` | `e421f60c67a42c73ea4028f79ed753572558c6b35c93798314fb07176b3e4a30` | 2,723 |
| `root-package6-super-producer-result-review-v1/review.json` | `d91b76573ac8ba69212ea5104482e6094f584dd9ed89eb7763eadfffb7de3cb0` | 1,811 |
| `root-package6-eight-seed-semantic-result-review-v1/review.json` | `fd29e4ea480646c8ef3ab27d2953ecb2ca620e469a5afb76498a7c7da6177552` | 15,794 |

## Package6 eight-role FEC and producer queries — 2026-09-03

This earlier checkpoint predates the isolated reader build and later query admissions.

**The final eight-role FEC join passes**, with a clean host-wrapper return at
**16:43:53.836856 UTC** and independent exact replay at **16:46:12.094947 UTC**.
It combines the **six fresh semantic results** with **two historical vendor/ODM
proofs**, reused through exact final-image identity joins, not rerun. ROOT
reproduces the original **11-record** join, rechecks all **14 held inputs**, and
confirms unchanged published-archive stats and ancestor identities. The separate
aggregate verifies FEC content for all eight selected dynamic images; the older
public verification report and its original FEC flag remain unchanged.
The join's **66 focused tests** pass. No image/archive bodies, native execution,
or fresh liveness probe are added by this host-only aggregation.

**EROFS producer-query capture closes at 16:45:35.422078 UTC**, exit **0**, in
**45.556 seconds**. It records three nodes and six query commands in an
**84,266-byte** result. ROOT replays the exact bound validator, checks 32 held
controls, and admits scoped preservation plus strict-idle/sole-owner checks.
The one observed linker response file is subsequently captured at **16:51:00 UTC**:
**1,503 bytes**, SHA-256 `81361ed7…`, with 48 held controls rechecked and separate
strict-idle/sole-owner checks passing. Isolated compilation and qualification of
the corrected native reader remain pending.

The **eight-seed producer/PYC capture** closes at **16:40:12.326868 UTC**, exit
**0**, in **690.467 seconds**, returning **8,830,411 bytes**. ROOT admits its
execution envelope and 40 held controls, with strict-idle and sole-owner checks
passing. Detailed semantic consumer review remains pending; capture success is
not producer/runtime qualification. Super discovery still stops on the helper's
handling of legitimate repeated input occurrences, and no super image is built.

The preceding six-role results and earlier query failures remain historical
checkpoints. Complete VINTF qualification and compatibility, native EROFS-reader
qualification, super/physical fit, OTA and device boot remain unverified. No
additional cleanup or phone operation occurs.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-avb/package6-fec-continuation-v2/final-eight-role-join-v1/actual-v1/result.json` | `18d7dd1abb8f94635a08787c265b4e4acb9161cb8660d9c7a5923b83f079acc3` | 22,981 |
| `root-package6-eight-fec-result-review-v1/review.json` | `7485cd41c36fe4f34d0e6b63f061e95e6ffede0dbf3455b25032aa590b7734cd` | 7,654 |
| `final-avb/package6-fec-continuation-v2/final-eight-role-join-v1/independent-review-v1/actual-replay.json` | `b1b362eecca7baf081f3167b2561194d9d5c7aeb1412347a013a3aae72f36296` | 20,267 |
| `root-package6-erofs-producer-result-review-v1/review.json` | `da28ea7f2aeded753378aacd72c640b7d4cf6f3f546069fe22f940e1506c2741` | 1,729 |
| `root-package6-erofs-link-response-v1/completion.json` | `1ec43b7de76db02766d5b457ab76be982ad80976e21b1fe8bee8cfc6d42ccf1b` | 3,050 |
| `root-package6-eight-seed-result-review-v1/review.json` | `4df5c34bbeb3282f28c320ef26865000a3fb58ebda3cbf7f091d16949ed484a7` | 1,696 |

## Package6 six-image FEC and published kernel admission — 2026-09-03

This earlier checkpoint predates the complete eight-role FEC join and query captures.

**The six-image FEC result passes strict semantic admission.** The corrected
native run closes at **16:10:14.312955 UTC**; all **32 diagnostic files**,
**206,103 bytes**, are subsequently read back. ROOT independently replays all
32 readback admissions and the original strict success validator, reproducing
the semantic result exactly and rechecking all **148 held input states**.
Verified roles are **mi_ext, product, system, system_dlkm, system_ext and
vendor_dlkm**, using the actual Package6 packaging images. Their protected
prefix and FEC parity results pass; native input/runtime preservation is bound
to the authenticated caller. This does not yet join the separate vendor/ODM
FEC evidence into one complete result.

The host semantic API does not establish guest termination. ROOT retains the
separate readback completion at **16:23:29.442892 UTC**, with strict-idle and
sole-volume-owner checks passing. No image bodies are reread on the host by
semantic admission. Earlier failed native and adapter attempts remain separate
from this admitted corrected result.

**The published boot-chain/kernel/META join passes at 16:19:43.528998 UTC**,
and ROOT admits its semantics by an exact record replay. All five boot-chain
roles join to the published archive and signed evidence; `working76` remains
unchanged. The complete **220,404-byte** kernel META matches the measured
**39,963,136-byte** kernel, SHA-256 `4441e484…`, including all **6,405 config
symbols** and literal **4 KiB** page selection. The bounded archive read totals
**1,782,217 bytes**; archive stats remain unchanged, no image member is opened,
and no whole-archive hash is repeated. ROOT rechecks 26 actual-read
records and seven handoff records without rereading image/archive bodies.
The unchanged **92,265-byte** role proof is then host-staged and read back as
`final_boot_kernel.json`, mode **0400**, with a proposed native reference.
Native staging/readback, complete six-proof VINTF qualification and kernel/module
ABI qualification remain separate; host staging makes no other role claims.

The EROFS exporter query still stops on the helper's handling of a duplicated
output-consumer line in the **401-byte** raw query, with paired observations of
the three protected exporter inputs, tools and graph preserved. No corrected
native reader is qualified yet.
Super discovery finds the installed `build_super_image` missing; the bounded
two-path probe finds `lpmake` present, and a follow-up query remains pending.
The eight-seed producer/PYC query is running as of **16:28:41 UTC**, without an
admitted result. Final VINTF compatibility, super/physical fit, OTA and device
boot remain unverified. No additional cleanup or phone operation occurs at this
checkpoint; unrelated host-space increases are not credited to earlier cleanup.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-package6-fec-dispatch-v2/run-v1/completion.json` | `c93bd80dc74e758b10a0c293d5c6df424d066501630e7453e81f4796226ffa1f` | 2,390 |
| `final-avb/package6-fec-continuation-v2/result-readback-preparation-v1/semantic-admission-v2/actual-v2-admission-v1/actual-v1/semantic-result.json` | `70c1fe26ddf14643c2dad4faccf4af3c9394273f2fbe5cccca2fcf4fc3c0437a` | 13,394 |
| `final-avb/package6-fec-continuation-v2/result-readback-preparation-v1/semantic-admission-v2/actual-v2-admission-v1/actual-v1/completion.json` | `3b0b0d6f7cbd93715fd8f12e8298c59123cf1fee0a7619db6abdefdb5e03953a` | 490,098 |
| `root-package6-fec-semantic-result-review-v1/review.json` | `bb2ec4c6fb6f2895251feb6f62c2cfe3643694d42084611b4a406eddb9b596a2` | 9,214 |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/boot/published-join-v1/review.json` | `c097100c2dac4113f8264f86727d68ff6b86b1ed6eec8812dac378c874b89840` | 92,265 |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/boot/published-join-v1/handoff.json` | `d77151daa8798e99d4a009523b47057b39d8f4169540d581ac966c253cbd83fe` | 9,706 |
| `root-package6-published-kernel-result-review-v1/review.json` | `5fe266e6a3c86862aea4823a0119b879472e2a5898b2e42c6dfbb6804f7da29a` | 978 |
| `final-vintf/package6-qualification-staging-v1/kernel-staging-completion.json` | `32e48b7bde0f521a0e950f4df1293ae2d24c6b41d3ff3c02b940e9f5ac129826` | 25,614 |

## Package6 discovery admission and failed-archive retirement — 2026-09-03

This earlier checkpoint predates six-image FEC and published-kernel admission.

**Shared discovery-v3 closes at 15:34:25.018945 UTC**, exit **0**, with
**607.744 seconds** recorded by the transport. The complete **8,888,513-byte**
capture is admitted by ROOT at **15:37:18.994916 UTC**; independent review
passes at **15:43:26.206997 UTC**. All six original source-callback vectors
match Package6. Paired observations cover **15 reachable Ninja graphs plus
one standalone bootstrap identity**, **6,862,614,527 bytes per pass**; the
bootstrap's include closure is not traversed. All 15 held controls remain
unchanged, with strict idle and sole-volume-owner checks passing at completion.

The exact **nine-target read-only query** succeeds. The frozen semantic handoff
admits observed dependency edges, nine current PYC identities with launcher and
two-project joins, and raw property source/audit joins. These observations do
not qualify compile/link commands, fresh tool binaries, runtime or generated
AIDL provenance, compiled property selection, or the original native PYC
verifier. The eight observed next selectors are preparation inputs, not an
executed producer qualification. The earlier graph-mismatch failure and
interrupted discovery-v2 remain separate, unadmitted attempts.

**One superseded failed reconciliation ZIP is deleted at 15:36:46.040304 UTC**.
The removed `target-files.zip` is inside the exact
`.reconciled-v1.incomplete-d7c0f0bf2b0a42ff91dd6b48c8b8ec0e` directory, not the
verified `reconciled-v2` output. It occupied **10,834,328,619 logical bytes** and
**10,839,019,520 allocated bytes**. All **127 held keeper files and 17 directory
identities** remain unchanged; the parent and small diagnostics are retained.
The old failed ZIP's exact body replay is lost. Host availability observations
rise by **10,834,333,696 bytes**, but this is not exclusive per-file reclamation
or a current-capacity guarantee. This deletion accesses neither the VM nor the
source volume or phone.

The preceding publication checkpoint is committed as
`08a3daacaea7e8f4e817c46aef87a6788ffe5209`, after **4,512 offline tests** pass
at **15:38:19.851318 UTC**, with all **586 tracked files** unchanged during the
run. That test result precedes this documentation edit. Native qualification
of the opt-in EROFS reader, complete FEC payload checks, VINTF compatibility,
super/physical fit, OTA and device boot remain pending. No new build or phone
operation is established by this checkpoint.

Evidence paths are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-package6-shared-discovery-v3/actual-v1/completion.json` | `95f9e37c3664980a15b6493d204f9dc57ff8def2decab319816fc1f5e61e9f75` | 14,798 |
| `root-package6-shared-discovery-v3/outer-result-review.json` | `a4b54ee54503467b3eb3031470be93bfb468e6458435569489c704ed3c4103ce` | 1,783 |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/shared-discovery-success-v3/handoff.json` | `72aa3807cc59fcf8bc79d6bbbf3775e4285d9fbc6bb1beb907b7696c35d4b0a8` | 11,614 |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/shared-discovery-success-v3/independent/review.json` | `0ebd4d96c481be854422a911ca27ce7a14fdebf595119c6a1e2654d59c7e1ab1` | 6,045 |
| `root-package6-failed-zip-retirement-v1/completion.json` | `c9fe8c168f18e6c053b19351533954e8a28ad0a7796b0646784ab36055e61b31` | 1,128 |
| `root-package6-publication-checkpoint-validation-v1/actual-v1/summary.json` | `45187d3584f25cad6b55270834feae5bd1071eb5d21c762906c459c2d43b7ea7` | 2,877 |

## Package6 archive and reader corrections — 2026-09-03

This earlier checkpoint predates discovery-v3 admission and failed-ZIP retirement.

**Reconciliation-v2 closes at 14:44:59.368409 UTC**, exit **0**, in **677.609
seconds**. All **9 recorded host AVB-tool calls** succeed. The maintained copier
independently reads back all **9,154 ZIP members**: 9,149 are preserved and five
change, including the signed image replacements and normalized DTBO prebuilt
alias. The **17-role signed image set** joins to the archive/retained inputs,
with all **14 unchanged signer leaves** and `working76` preserved. The selected
public-key Android AVB chain is reverified; original build metadata and source
inputs stay unchanged. This operation does not access the private key or VM.

ROOT's separate **15:25:57.640832 UTC** review reproduces the exact postcheck,
matches preflight and final provenance, and verifies 39 held small files and
20 additional body stat records. It does not repeat the large-body hashes.
The completed process is reaped, its streams and nested-tool cleanup are
verified, and no liveness review remains required. Minimum periodically sampled
host availability is **149,654,671,360 bytes**, above the unchanged **100 GiB
reserve**, not a guarantee of full continuation capacity.

The published archive is
`artifacts/avb/nezha/package6-20260903-v1/reconciled-v2/target-files.zip`,
**10,834,328,619 bytes**, SHA-256
`fbb6cba4ee1a0872634494c9398857bd7a176abba9b3adceee7c6bcbcbc0adb4`.
**Published-path inventory closes at 15:32:08.871326 UTC**, exit **0**, in
**48.239 seconds**. ROOT admits the result at **15:32:55.545808 UTC**: all 17
roles match the signed manifest, all image aliases match their canonical images,
and the complete **9,154-name** directory has no `IMAGES/system_other.img`.
Archive stat records remain unchanged across the original CLI, bounded metadata
capture and ROOT review. The metadata capture reads **1,687,413 bytes**; neither
its wrapper nor ROOT repeats the whole-archive hashes performed by the original
CLI. The earlier staging-path inventory remains preserved separately.

Commit `1777ce653c8ed08e18a9680b8d3b169604901e22` promotes local and central
ZIP header versions before writing members beyond the ZIP64 offset threshold.
Strict readback and the separate AOSP streaming exception stay unchanged.
Commit `26ed564670e4c76427df4cf50eb7cb9fb5015600` adds the **opt-in compact-EOF
EROFS reader**. The historical canonical `89d6…` source is restored, its default
selection stays unchanged, and the reviewed corrected C bytes live under the
explicit variant filename. Historical source-pin contracts remain valid.
This host change is not native reader qualification.

The frozen changes pass **4,512 offline tests** at **14:31:13.527753 UTC**:
**182.680 seconds** reported by unittest, **184.081 seconds** wall time, with
all **586 tracked files** unchanged through the run. This precedes the current
documentation edit; it is not a new test result for this checkpoint.

**The first reconciliation attempt remains failed and preserved**: it closes
at **14:14:35 UTC**, exit **2**. The original three-image
EROFS scan stops on `system` at **14:12:01 UTC**, admitting **no manifests**.
Source review identifies an unselected compact EOF marker rejected before
payload mapping, not demonstrated excessive lookback or decoder failure.
Shared VINTF discovery closes at **14:27:43 UTC**, exit **1**, before any Ninja
query: the literal graph closure was incorrectly equated with the broader
fixed-selector inventory. Both full source-guard returns match, but missing
paired graph observations prevent whole-discovery preservation admission.
Discovery-v2 is subsequently interrupted with an empty capture and no completion
record. Discovery-v3 launches at **15:24:16 UTC**, using the identical reviewed
successor wrapper after fresh strict-idle and sole-volume-owner checks. No
completed discovery result is admitted at this checkpoint.

Full FEC payload checks, VINTF compatibility, super/physical fit, OTA and device
boot remain unresolved. Archive reconciliation is not signing-metadata, APK,
APEX or OTA-payload signing and does not establish OEM trust or device rollback
compatibility. No new cleanup or phone operation is performed by this checkpoint.

Saved evidence below is relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`; raw failure streams
remain retained separately.

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-avb/package6-reconcile-retry-v1/reconcile-v2/completion.json` | `0d077d0c14b2daa8c46f8f3b749f3a74171dde1f1c818b0aba9270716cd8d7cd` | 1,130,274 |
| `root-package6-reconcile-result-review-v2/review.json` | `18079405fbf3d234a24d76f863e88725dd114c642b7c8fd06592edacea26b178` | 20,208 |
| `final-avb/package6-super-continuation-v1/root-published-inventory-preparation-v1/actual-v1/completion.json` | `4cfe935ace3237b265423171df79ecc0a2a648a181cb4c8cf7e0346b1070b3ca` | 87,329 |
| `final-avb/package6-super-continuation-v1/root-published-inventory-preparation-v1/actual-v1/inventory-metadata-admission.json` | `9b238ec4bd10ee16fa171bf7b05f96b5684716c514e81a17a4db886e6f5e1075` | 2,456 |
| `root-package6-published-inventory-result-review-v1/review.json` | `9d0aa9b39190d3ba9ed3fde7320b79a81f8fe6bf6b444faac177c802cbaef575` | 7,846 |
| `root-zip64-erofs-fixes-validation-v2/actual-v1/summary.json` | `8727c49d62b4bc16af81bfbf47027f568aecbf6abc866993dd6f2b30961d3d81` | 3,166 |
| `final-avb/package6-signing-continuation-v1/reconcile-v1/completion.json` | `112fd66182367c7d78180615e339ff93682dda21d783b9d9864ba889bf387140` | 1,017,216 |
| `root-package6-three-image-capture-v1/actual-v1/failure.json` | `426d207ad25ffcbd9026bb8cd7650ac50249889999561962881d80795a461ea9` | 3,421 |
| `three-image-erofs-lookback-diagnosis-v1/independent-source-review-v1/source-review.json` | `abe80ff51fd5a675087ab66c5e0297c23359028162b318e45f8ee74c078ec172` | 10,094 |
| `three-image-erofs-lookback-diagnosis-v1/independent-source-review-v1/source-variant-review.json` | `54658ea56aa729d8de5baf06dce0f76d8aa799baa74620c4dbd28f5f538fec60` | 5,726 |
| `root-package6-shared-discovery-v1/actual-v1/failure.json` | `4272ed6067ec75fda5ce6da5944aa44d3c8db45c5f2098991bcc2eee4c2ab6ea` | 14,166 |
| `final-vintf/actual-package6-preparation-v1/actual-capture-review-v1/tools/next-capture-preparation-v1/failure-analysis-v1/review.json` | `4da5aa82369674f65e93c89f96418ac24f58474a98219017fd9ebd800be6bd79` | 10,483 |
| `root-package6-shared-discovery-v3/recovery-review.json` | `a91ae7149c50e0a0124ff3f209282b00778dc98afbd1b80cd68d1b3dba606cbf` | 1,200 |

Published reconciliation and inventory evidence is relative to
`artifacts/avb/nezha/package6-20260903-v1/`:

| Record | SHA-256 | Bytes |
| --- | --- | ---: |
| `reconciled-v2/receipt.json` | `c9fb8b55c8dadafb48ca71f91ee1961ce2bd603034a9f96e7e91657cd7b1d2ae` | 35,781 |
| `reconciled-v2/public-verification.json` | `9dba981b7a902971851d58611c83ce2c4cb9d55bdd011d17577f399e939e20bf` | 59,951 |
| `published-inventory-v2.json` | `d56d1ab6bc17a83c9e0859a6c3b4b08989882eb03b83b52f82f396124f18ef7e` | 13,608 |

## Package6 public AVB preparation and signing — 2026-09-03

This earlier checkpoint predates the archive retry and reader corrections.

**Public preparation closes at 13:49:06.092582 UTC**, exit **0**, in **24.130
seconds**. All **18 host AVB-tool invocations** succeed: one public-key
extraction, two unsigned retained-input descriptor carriers and **15 input
verification calls**. The five rebuilt **product, system, system_dlkm,
system_ext and vendor_dlkm** images have SHA-256 hashtree descriptors. The
normalized signer manifest is `44bc1fc5…` / **5,660 bytes**; normalization here
is of the signer input manifest, not DTBO archive-alias replacement.

ROOT's **13:50:49 UTC** review replays the exact postcheck and verifies
`working76`'s unchanged identity, **39 small inputs and 16 stat-only inputs**.
The original preparation reports unchanged source inputs, no guest/device
operations and no private-key access. Minimum periodically sampled host
availability is **172,092,657,664 bytes**, above the unchanged **100 GiB
reserve**; this is not a guarantee of full continuation capacity.

**Host private signing closes at 14:03:59.601082 UTC**, exit **0**, in **68.000
seconds**. The **17-role image set** retains **14 unchanged leaves**, including
`working76`; `boot`, `vbmeta` and `vbmeta_system` each reproduce byte-identically
across two signing passes. All **33 recorded host-tool calls** succeed: 18
public rechecks, seven signing/key operations and eight chain-verification
calls. The selected-public-key Android AVB chain passes, with no missing
partitions; package-budget checks pass but physical partition fit is unverified.

ROOT replays the exact postcheck and confirms preserved input records and
output stats; it does not independently rehash output bodies. The existing
private key is used only by pinned host tools, not copied, and no key is
generated or guest accessed. Signing's minimum periodic free-space sample is
**166,560,354,304 bytes**; full continuation capacity is not thereby cleared.

**Archive reconciliation is running; no successful result is admitted here.**
Full FEC payload verification, VINTF semantic admission and compatibility,
super/physical fit, OTA signing and device boot remain pending. Android AVB
closure does not establish OEM trust or device rollback compatibility. No new
cleanup, phone operation or new full-suite result is claimed. Exact preparation,
signing, verification-manifest and ROOT-review pins are in the
[integration record](../research/workspace-integration.json).

## Package6 input materialization and P5 host retirement — 2026-09-03

This earlier checkpoint predates successful public AVB preparation and signing.

**Exactly one old P5 host ZIP is retired**, after fresh full hashes of it and
the retained Package6 ZIP: **22,004,565,441 bytes read**. Parents, immediate
siblings and keepers remain. The removed file was **10,997,962,405 logical bytes**
and **10,997,964,800 allocated bytes**. Host availability observations at
**03:45:25–03:45:43 UTC** rise by only **119,111,680 bytes**; this is not exclusive
per-file reclamation or a current-capacity guarantee. P5's exact old ZIP replay
is lost; Package6 is not its byte-identical replacement. Historical receipts
remain, including the earlier native-mirror retirement as a separate action.

**Materialization closes at 03:55:41.725919 UTC**, exit **0**, after **125.986
seconds**. The unchanged materializer creates **13 canonical Package6 images
and two retained stock inputs**, independently reads back their bytes and
returns successful local publication checks. ROOT review at **03:58:14 UTC**
joins all 15 manifest identities to inventory/stock and confirms distinct,
private, regular single-link files and retained controls. That review does not
rehash the large bodies. The original prepublication receipt remains distinct
from the successful returned publication result. Periodic observations stay
above the **100 GiB reserve**; full continuation capacity is not cleared.

The VINTF capture transport exits **0** and acknowledges result `d0c7c012…` /
**19,117,617 bytes**, without running compatibility checks. After the recorded
host reboot, the stopped builder is restored at **13:40:34 UTC** with the same
configuration, renewed host-device binding, sole-writer ownership and strict
idle checks; this does not verify whole-volume contents. Capture readback
completes at **13:41:55.775938 UTC**, exit **0**: acknowledgment, native final
hash, complete stream and host readback agree, with **16 controls unchanged**.
**Semantic admission and VINTF compatibility execution remain pending.** The
later **183,686,529,024-byte** availability observation is not attributed to a
particular cleanup or treated as full continuation capacity.

Separately, the **04:04:45 UTC** metadata probe identifies **20 regular native
leaves**, **18,308,329,472 allocated bytes**, with four directories and 88
protected entries retained. **No fresh body hashes, deletion admission,
deletion or trim** result follows from that probe.

Public AVB preparation, private signing, DTBO archive-alias normalization,
FEC/complete AVB-chain verification, VINTF compatibility, super/partition fit,
OTA and device boot remain pending. Materialization does not repack the archive
or verify image formats. No phone operation or new full-suite result is claimed.
Exact saved receipt pins are in the [integration record](../research/workspace-integration.json).

## Package6 host transfer and original inventory — 2026-09-03

This earlier checkpoint predates input materialization and P5 host retirement.

The completed Package6 archive is transferred to the host at **03:29:05.747875
UTC**. Transport exits **0** after **38.279 seconds**, streaming exactly
**11,006,603,036 bytes**, SHA-256 `e3b9aa2b…`. Native final hashing and host
readback pass. Independent review replays the saved transfer evidence and
checks retained records; it does not rehash the large archive again.

The original inventory closes at **03:32:45.819849 UTC**, exit **0**, with no
errors or missing required inputs: **13 data images, two generated vbmeta
images and two retained stock inputs**. This is an input/role inventory, not
complete archive semantics, signing or ROM verification.

At **03:36:29 UTC**, ROOT joins the inventory to the completed native result.
For **product, system, system_dlkm, system_ext and vendor_dlkm**, ZIP members
match the expanded packaging images from independent producers; **all five
explicitly differ from the earlier native component images**. Vendor/ODM joins
also pass. Against the old inventory, **mi_ext, odm, recovery and vendor** are
unchanged; the other nine data roles change. Neither comparison proves runtime
compatibility or replaces the remaining image/chain checks.

The fresh DTBO alias inspection proves identical **1,495,111-byte payloads**
and tables, with unsigned `NONE`, zero flags/rollback and verified salted
digests. Whole images differ through permitted salt/fingerprint metadata and
associated sizing. **Inputs are unchanged and normalization is not applied**;
payload equality is not whole-image byte equality.

Host image materialization, signing, full FEC/AVB checks, VINTF, super/partition fit, OTA and
device boot remain pending. No old P5 host archive had been deleted at this checkpoint, and no publication,
phone operation or new full-suite result is claimed. Exact transfer, inventory,
DTBO and ROOT-join pins are retained in the
[integration record](../research/workspace-integration.json).

## Package6 build and host admission — 2026-09-03

This earlier checkpoint predates the host transfer and original inventory.

**Native Package6 construction and profile validation pass.** The native command
runs **02:49:41.581029–02:54:14.659305 UTC**, exit **0**; the root executor runs
**02:43:52.799280–03:01:01.638918 UTC**, exit **0**, for **1,028.836 seconds**.
`profile_completed` and `profile_validation_verified` are true, with no postcheck
errors. Both target-files directory and ZIP producers are fresh. Validation
covers **205 expanded metadata records and 221 selected ZIP members**, not all
archive-member content or complete ROM semantics.

The native archive is **11,006,603,036 bytes**, SHA-256 `e3b9aa2b…`; the completed
result is `506a7b7c…`, **12,102,050 bytes**. The first pure-host admission fails
because a **596,561,920-byte** system-copy identity exceeds the default evidence
cap of **536,870,912 bytes**. Exactly two call sites are corrected to use the existing
**912,273,408-byte system budget**, without changing the native result or global
cap. **Eight tests plus seven subtest cases pass**. Corrected admission passes,
followed by root independent replay at **03:11:08 UTC**; the original failure remains
preserved. No native build/callback rerun or archive-body read/copy occurs in
this host admission.

Post-build free-block trim completes at **03:05:34.062025 UTC**, with **no new
file deletions**. Host availability rises **115,391,803,392 → 130,413,355,008 bytes**,
an operation-local **15,021,551,616-byte** increase; backing allocation decreases
**15,155,810,304 bytes**. These are separate observations, not additive savings
or current-capacity guarantees. The original builder/configuration is restored,
the temporary container removed, and fresh pre/post alias, logs, selected files,
stat-only module-info and project objects compare equal. Selected sentinels are
preserved; complete live-filesystem integrity is not claimed.

**The archive has not been copied to the host or signed at this checkpoint.**
Host inventory, whole-payload FEC, VINTF extraction/compatibility, final AVB,
super/partition fit, OTA and device boot remain pending. Planned extraction
roots are not an extraction result. No phone operation or new full-suite result
is claimed. Exact result, admission and trim pins are in the
[integration record](../research/workspace-integration.json).

## Package6 launch after P5 mirror retirement — 2026-09-03

This earlier checkpoint records launch only, before native completion and host admission.

**The original native Package6 executor starts at 02:43:52.799280 UTC**, using
the genuine `0b3cfb98…` request and `cf3c18eb…` guest. Launch availability is
**142,274,932,736 bytes**, above the **133,769,298,255-byte** requirement including
the unchanged **107,374,182,400-byte (100 GiB) host reserve**. This records launch
only: no running output or incomplete result is inspected/admitted by this
documentation task, and no completion, profile, archive or build success is claimed.

The first read-only `dist` query fails its jail gate; the separate closed V2
query establishes an **input-free phony** branch, with real read-only namespace
and capability checks and unchanged full graph/tool/makefile/alias guards.
It is a reader-closure check, not a package build or deletion.

At **02:40:46 UTC**, exactly the old native P5 mirror ZIP is removed: **10,997,962,405
logical bytes**, **10,997,968,896 allocated bytes**. Its fresh native full hash
matches the retained host-keeper proof; that keeper's stat record remains unchanged,
not freshly full-hashed by this deletion. Independent review verifies the single
unlink, all 80 protected selectors and retained expanded tree/list/parents/siblings.
This is an exact exception for the redundant ZIP, not removal of the output tree.
The historical archive remains on the host; reuse at a native path needs a verified copy.

Trim completes at **02:42:40.539751 UTC**. Host availability rises **131,279,601,664 →
142,326,861,824 bytes**, an observed **11,047,260,160-byte** operation-local increase;
backing allocation falls **10,997,972,992 bytes**. These are separate, non-additive
observations. The original builder/configuration is restored and the temporary
container removed. Fresh preflight collectors pass; the post-restart comparison
shows the entire alias/logs/files/stat-only module-info/project records equal,
with selected sentinels preserved. This is not full live-filesystem validation.

Exact closure, retirement, trim and launch pins are in the
[integration record](../research/workspace-integration.json). Full continuation
capacity and final AVB/signing/FEC/VINTF/super/partition, OTA and device-boot gates
remain separate. No phone operation or new full-suite result is claimed.

## Package6 corrected projection and bound request — 2026-09-03

This earlier checkpoint records the then-unlaunched request and unresolved storage gate.

The ordinary wrapper now supplies the verified inner `target_files` record to
the unchanged checker. An exact shared Package6 source-context projection also
passes qualification, with **98 focused tests**. Guarded host deployment and
preparation complete at **02:28:30.222875 UTC**, preserving six previous native-
preparation files and the original host preparation, with historical evidence
unchanged.

The genuine prepared request is `0b3cfb98…`, **5,298,505 bytes**. Its fully bound
bridge is `9011098f…`, **519,654 bytes**, within the unchanged **524,288-byte**
limit. The original request binder then completes default preparation,
`--publish` and `--check-only` reproduction, all exit **0**, with identical
preparation data and unchanged held inputs. The bound consumer is `9a19ac66…`,
**73,419 bytes**. This verifies host request binding, not a native Package6 run
or admission of an actual runtime result/archive.

**Native Package6 remains unlaunched.** Storage review and the unchanged
**100 GiB host reserve** still gate execution; full continuation capacity has
not been cleared. This checkpoint records no subsequent ZIP retirement or trim.
Package6, final AVB/signing/FEC/VINTF/super/partition checks, OTA and device boot
remain unverified. No phone operation or new full-suite result is claimed.

Exact deployment, qualification and binding pins are retained in the
[integration record](../research/workspace-integration.json).

## Package6 proof staging and extraction cleanup — 2026-09-03

The caller correction was still pending in this earlier checkpoint.

The two-producer read-only capture closes at **01:20:12.311790 UTC**, exit **0**,
with all **119 held inputs** unchanged. The actual GMS two-proof stage completes
at **01:30:02 UTC**, preserving 27 held files; the exact **21-record** proof/control
stage completes at **01:41:58 UTC**, verifying **1,551,248 bytes** and preserving
31 held files. These are capture/staging results, not a Package6 build.

At **01:48:30 UTC**, the refreshed extraction retirement removes **10,876 descendants**, leaving
all **three roots** intact, and fully hashes **eleven keepers / 5,750,240,056
bytes**. Historical extraction replay now requires re-extraction.
It recovers **9,294,848,000 bytes inside ext4**. At **01:50:12 UTC**, the separate
approved trim reduces backing allocation by **9,294,950,400 bytes** and observes a
**9,382,678,528-byte (8.74 GiB)** host-free increase, reaching **135,527,866,368
bytes** at that operation's completion. These measurements are not added together
or treated as current capacity. Post-restart comparison verifies the fresh
alias, four logs, selected files, stat-only module-info observation and project record;
the original configuration remains unchanged and the temporary container is
removed. This is bounded preservation, not a complete filesystem integrity audit.

**No Package6 native dispatch occurs.** Final host inspection finds the frozen
`b16be31e…` caller passes the outer ordinary wrapper into the unchanged
`c2017322…` checker, which requires the verified inner `target_files` record.
A narrow caller correction and regression check remain in progress; historical
receipts are not rewritten or promoted to build success.

The current target-files tree and ZIP remain protected. Their read-only inventory
already reports **26,106,458,112 allocated bytes (24.3135 GiB)** at the same paths.
The older **24.332 GiB** package estimate is gross, not proven incremental growth.
The full continuation budget still requires reconciliation; cleanup does not
establish capacity for every remaining package/export/signing operation.

Exact receipts are pinned in the [integration record](../research/workspace-integration.json).
Package6 build, final AVB/signing/FEC/VINTF/super/partition checks, OTA and device
boot remain pending. No phone operation or new full-suite result is claimed.

## Package6 prerequisite qualification and fresh captures — 2026-09-03

This earlier checkpoint records the then-pending capture, native stages and cleanup.

At **00:47:15 UTC**, the exact-seven-stat consumer (`8294fd99…`, 69,393 bytes)
passes root qualification: **18 tests** and genuine `_originals`,
`_postcheck_recovery`, `read_plan` and full `_verbose` replay with three actual
log bodies. Only `_retention`, `_verbose` and the dedicated `_verbose_stat`
helper change; full nine-field validators and raw records remain unchanged.
The plan retains **30 evidence rows, 47 inputs, six outputs and 19 controls**.
The original failed result stays failed; canonical Package6 control/request
bindings and complete prerequisite admission remain separate.

The read-only GMS capture runs **00:45:00–01:05:36.507147 UTC**, exit **0**,
with all **44 held inputs** unchanged. Independent review verifies the complete
transport, exact packet/program/payload, original source/sidecar joins and
graph/log comparison. The fresh host equivalence driver authenticates **22
inputs and all sixteen current graphs**, producing a new proof and helper.
**Two-proof native staging is prepared, not executed**; a successful host
preparation command is not a guest staging receipt or Package6 admission.

The Selected4 request is actually staged at **01:08:19.886349 UTC**, exit **0**:
**10,413,456 bytes**, exact hash `89c4fd9b…`, with all **27 held files** unchanged.
This stages one request, not image bodies or a rebuild. The separate two-producer
capture starts at **01:09:48.387160 UTC**, with **119 inputs held at launch**;
its result remains pending at this checkpoint.

A read-only probe of three old vendor/ODM extraction trees verifies **80
protected selectors**, unique inodes across the roots and no non-directory
hardlinks. The **9,294,860,288 allocated bytes are not reclaimed space**.
No tree is deleted: Selected4 staging changed a validation-parent stat record,
so exact retirement requires a refreshed probe and full keeper hashes. No new
cleanup follows the two-super retirement in this checkpoint. Host-space changes
are not attributed solely to the source-volume backing file, and the full
continuation capacity budget remains uncleared.

Exact local evidence is relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`; additional proof/helper,
launch and completion pins are in the [integration record](../research/workspace-integration.json).

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-five-recovery-consumer-review-v2/review.json` | `23cfce32f1bf4fd62782d96c6ce663eeec089d3a3d81fcdc57e217fbc4b57ab6` | 1,907 |
| `package6/post-recovery-gms-capture-review-v1/review.json` | `928f333e3173c2773b6d581896bfb329eca6993a02126ee3b1151639b396813d` | 15,504 |
| `package6/post-recovery-gms-equivalence-preparation-v1/actual-handoff.json` | `77a8b74ad3bbd5b3234814a9ce4d7b395ecd5b29dd18ebbae2f301adfa0c44cb` | 10,469 |
| `root-package6-selected4-stage-dispatch-v1/actual-v1/completion.json` | `ea30e0a6d44bbaf32ef307ffe2b2211b6891eb9e740bb0d6432ed7bfc9b2b976` | 1,457 |
| `root-three-extraction-probe-result-review-v1/review.json` | `44e23045307174853d318b55b7e443bfb9c10c7a4314da756d9ed6fc0d76fb51` | 2,100 |

Package6 build, final AVB/signing/FEC/VINTF/super/partition checks, OTA and device
boot remain pending. No phone operation or new full-suite result is claimed.

## Five recovery execution and two-super retirement — 2026-09-03

This earlier checkpoint records the then-pending stat-schema correction.

The V2 postcheck-recovery command runs **September 2 23:56:10.365629–September 3
00:08:48.554115 UTC**, exit **0**, with all **38 held files** unchanged. Its
receipt is verified by the native producer. The read-only export completes at
**00:32:42 UTC**: the 968,348-byte receipt matches the native output exactly,
and the 4,140,101-byte actions record matches its bound pin. The original
`c3cbe353…` failed result remains unchanged. No build is rerun, no output is
invalidated, and source/Android output is not modified by this recovery.
Host receipt-only `_originals`, `_postcheck_recovery` and summary validation
pass. The recovered receipt verifies **five fresh actions, all six unchanged
callback maps, strict descriptor metadata and the built/installed system copy**;
it does not verify whole hashtree/FEC payloads or a signed parent chain.
**Package6 `read_plan` remains blocked** by nine-field versus seven-field
verbose stat records: all seven shared values match, with only `uid/gid=0`
additional in the former. No filesystem drift is established; the narrow
consumer correction remains pending, not a native rerun. Fresh four-log readback
passes at **00:33:40 UTC**, without source/output writes or graph-capture
admission. No Package6 execution or signed-parent-chain success is established.

The exact two-target raw-super retirement runs **00:09:56–00:10:26 UTC**, exit
**0**, after complete reconstruction comparisons and fresh action guards.
Only the Xiaomi.eu and factory reconstructed `super.raw.img` leaves are removed.
The action freshly hashes **18 bodies / 54,089,758,304 bytes** and joins 309
controls before/after. Independent journal and dispatch review passes **158
checks and eleven negative cases**, including 320 outer-control joins. It checks
current metadata for all 38 retained/protected bodies, not another complete read
of those bodies or an audit of every workspace file.

Host availability is **128,594,862,080 → 152,120,836,096 bytes**, an observed
**23,525,974,016-byte (21.91 GiB)** operation-local gain; the candidates' prior
allocation is **23,537,713,152 bytes**. These are separate measurements, and the
difference has no proven specific cause. This is the historical action window,
not current free capacity or clearance of the full continuation budget.
Original archives, all sixteen sparse
inputs, LP sets and small receipts remain. The two earlier raw KEEP entries are
superseded only for this action: raw inspection and LP re-extraction now require
reconstruction and the historical full-hash check. LP images alone are not a
bit-identical restoration source. No VM, phone or recursive operation occurs
in this retirement.

Exact local evidence is relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-five-recovery-native-dispatch-v2/actual-v1/stdout.json` | `f84107c32716be85ce9e6d2764bf5b5a7bdf66ff173b61a2895ece4f8eca58b2` | 968,348 |
| `root-five-recovery-evidence-export-v1/actual-v1/selected-image-actions.json` | `3acfccf1b727f97ca4290119943f7a92194782ceca3c22659713383534205fa1` | 4,140,101 |
| `derived-super-retirement-v1/root-execution-v1/completion.json` | `bc272ef94cd2caf4b8eaae1575e13aca0ad3117cda6a2d8c06256abeba8e5aaa` | 237,744 |
| `root-two-super-retirement-acceptance-v1/review.json` | `1a234085c9f723a59989f08cb6863d8aa01b2071bf56375e50361c1deeb5f696` | 4,065 |
| `root-five-recovery-receipt-acceptance-v1/review.json` | `24736775ab65ad5513f6f017cc76756828afc67a2ad9a681b6688de7fe0f0560` | 4,539 |
| `package6/post-five-activation-preparation-v1/four-logs-v1/actual-v1/stdout.json` | `7fcba3232599da62f62f8ea7b7a02b4b3ca88e5f35cd42cc7fd4cba7afe59c25` | 80,384 |

Package6, final signing/AVB/FEC/VINTF/super/partition checks, OTA and device boot
remain separate gates. No new full-suite pass or flashable-ROM claim is made.

## Five recovery diagnostics and further cleanup — 2026-09-02

This earlier checkpoint ended with V2 in progress and the two raw supers retained.

Recovery v1 runs **23:37:10.386558–23:37:18.262120 UTC**, exit **1**, rejecting
the native postcheck callable before the recovered full postbuild guards and
recovery artifact writes. All **23 held inputs** and the original failed Five
result remain unchanged. At
**23:42:24 UTC**, a compile-only native Python 3.12 diagnostic finds identical
hook ASTs but a sole `co_code` difference between isolated-hook and full-bridge
compilation. It calls neither the native context nor build, writes no native
files, and preserves the original result and all three sidecars; recovery
artifacts remain absent.

V2 changes only the expected full-bridge compilation context, retaining the
complete callable-shape guard and all four postcheck substitutions. **14
independent test executions and 16 materializer tests pass**, and the root
reproduces the exact V2 packet with all 34 held files unchanged. These are
preparation proofs. **Native V2 starts at 23:56:10.365629 UTC and is in progress**,
with 38 host inputs held; neither a successful result nor promotion of the
original failure is established by this checkpoint. No rebuild or forced
output invalidation is authorized by this postcheck-only recovery.

At **23:46:11.993910 UTC**, exactly **12 old Images2–4 retained image leaves**
(recovery, mi_ext, vendor and ODM) are deleted after 16 complete hashes and 62
protected selectors. Review replays all 43 events and 26 durable journal records;
52 host inputs remain unchanged. Their **17,830,182,912 allocated bytes** are
not a host-space measurement. Historical original-inode replay is retired;
four SOURCE keepers, current output and Images5/6/Five remain protected.

The separately approved trim completes at **23:54:35 UTC**, with post-restart
review at **23:55:20 UTC**. Host availability rises **109,865,611,264 →
127,870,160,896 bytes**: an operation-local **18,004,549,632-byte (16.77 GiB)**
gain, distinct from the **18,010,460,160-byte** backing-allocation reduction.
The original builder/configuration, output alias, four logs and three sentinels
pass their checks; the temporary container is removed. This does not prove
every source/output file unchanged. Guest allocation, FITRIM output and earlier
cleanup gains are not added to this host delta.

Separately, at **23:45:30.560490 UTC**, both reconstructed stock supers pass
complete direct comparison against sparse reconstruction, with **84,691,400,288
bytes read**, 18 body stat records and 16 small controls stable. No image is
created or deleted by that comparison; sparse inputs and stock originals remain.
**Both supers remain KEEP pending exact-target retirement.**

Exact local evidence is relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`; the
[integration record](../research/workspace-integration.json) also pins the
diagnostic, completion and test receipts.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-five-recovery-v2-preparation-review-v1/review.json` | `038354d8861942e2fd30f428ae82a2811fec2501792d88c315546f7c0b06be5c` | 2,267 |
| `root-old-twelve-image-retirement-review-v1/review.json` | `b4e4e5a7c9c6757f0cf95c0e42f0974b82f472d9be952ef106c2e4aa417ae0a5` | 3,000 |
| `old-twelve-image-trim-v1/postrestart-v1/review.json` | `d9684751b1d0288c0f0754e27117e675d6377013ec2c1e1c19fcaa88a4ad212a` | 1,303 |
| `root-two-super-comparison-review-v1/review.json` | `f711af6484fe9aae4ae7dba99b82769eb2522af7a8f490b26e39913a66d80072` | 2,827 |

No recovered Five profile, Package6, final AVB/signing, ROM/boot success or phone
operation is established. A new full-suite result is not claimed here.

## Five native exit and protected-sidecar failure — 2026-09-02

The ordinary Five Ninja invocation runs **22:33:40.346762–22:36:05.236215 UTC**,
exit **0**, but the outer command closes at **22:40:08.639 UTC**, exit **1**.
Profile completion/validation are false and the postcheck is null, with
`selected image build changed protected sidecars`. Native exit 0 alone does
not verify fresh image actions or admit the resulting images.

All **56 held input hashes/nine-field stat records**, six complete before/after
callback returns and **254 configuration values** remain unchanged. Five
ordinary callback objects and the protected policy runtime also match Nothing11.
The three **65-byte sidecars** retain their full bytes, paths, original inodes,
permissions, mtime, all eight non-ctime stat fields and ancestor identities.
Only `ctime` changes, inside the actual native invocation window.

Captured `build_image.py` (`9397d764…`, 39,604 bytes) uses `CopyInputDirectory`
with `os.link` inside a `TemporaryDirectory`. The actual tool ZIP's checked-hash
cache header supports source binding; this makes temporary hardlinks a consistent
explanation, **not a syscall trace or proof of the exact cause**.

Exact local evidence is relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-five-native-dispatch-v1/stdout.jsonl` | `c3cbe3532f49dad400f5eae9d0a5ee3e6a3e8dd93958e27ad96c7f5272389cae` | 10,637,537 |
| `root-five-failed-profile-review-v1/review.json` | `adeda1d89032db33ed5c626db9dab41511d14db2da5e474153f10763ac76dcb7` | 5,135 |
| `root-five-sidecar-diagnostic-v1/stdout.json` | `50a7e9d10b54491d3413aa2680d828d39a2576d001cb1ade10dc473fc2259bd8` | 81,249 |
| `root-five-sidecar-cause-v2/stdout.json` | `cd7309816c4e041e33d5a7ed77b7ea10af47d9c616e15250ead0cb5a0d13fb09` | 268,198 |
| `root-five-sidecar-cause-v3/stdout.json` | `aca9df2ad41558d16ed514270a6f1383c809ce4c3720365396b74a9287f89cc7` | 594,954 |

The nine-file preparation review completed before launch; its 25 focused and
17 staging tests and the prior 4,508-test checkpoint are not a successful native
profile. **Recovery was preparation at this earlier checkpoint**, with the
original failure preserved,
no rebuild or forced output invalidation, and no phone operation. Recovered
profile, Package6, final AVB/signing, super, OTA and ROM/boot gates remain open.

## Vendor/ODM retirement and five-image preparation — 2026-09-02

The host-only retirement runs **22:13:10–22:14:08 UTC**, removing exactly
**eight vendor/ODM image leaves from four historical bundles**. Prior ten
candidate/keeper byte matches remain bound; 14 fresh full-body hashes cover
**39,667,392,512 bytes**. All **323 primary controls and 133 additional outer
inputs** remain unchanged, and all eight durable-intent/reader-barrier/unlink
sequences are verified. **54 offline mock tests pass**, separate from execution.

All parent directories, small manifests/receipts and six keeper images remain.
Stock/current runtime inputs, source checkouts, active output, working76 and
super images are not removed. **The four historical bundle manifests are now
incomplete until their matching image bodies are restored**; they are not
immediately reusable. Host availability rises from **158,860,337,152** to
**181,437,829,120 bytes**, an operation-local **21.03 GiB** increase. This is not
the allocated-byte count or an exclusive APFS attribution guarantee.

Separately, the actual five-image **read-only capture completes at 21:41:01 UTC**;
root review verifies both original query streams and all **13 retained original
files**. At **21:55:47 UTC**, five proof records totaling **1,081,817 bytes** are
staged and verified, with **115 held inputs unchanged**. Neither operation is
an image build. Host preparation first fails closed before I/O at a Nothing11
reader binding, then rejects the exact zero-byte graph shard. Shared-reader and
literal-empty-graph corrections preserve the original validators, all **16
graphs / 6,862,614,527 bytes**, all 19 roles and existing limits. **25 focused
host tests pass**, including genuine native-style validation; at that earlier
checkpoint final independent preparation review remains pending. **Five native rebuild not yet verified.**

Exact local evidence is relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `old-vendor-bundle-retirement-preparation-v1/root-execution-v1/completion.json` | `54e067713c37d45d8d95fea7c23db960afe7809cccce2145cdd3b09ae08b6198` | 164,383 |
| `root-eight-host-retirement-result-review-v1/review.json` | `6688911698de79bcdd5bb8b7f550bb4c57c136ba3276252a0d6b40387f27a020` | 22,000 |
| `root-five-query-result-review-v1/review.json` | `5e011a45a76243657265e181a839b176c710fa3dd933a8409364ce6744624894` | 18,758 |
| `root-five-proof-staging-v1/completion.json` | `590f086694b24f3b76e23286a41a2d298465d6154ca8a5deea4e21f3694eb3ab` | 1,013 |
| `root-five-proof-staging-v1/stdout.json` | `c8b742835795575eca9e128d0329ec2e67b3157039c3f5b732532e368df633d8` | 2,184 |

The retirement uses no VM or phone. Images6 remains the verified image-stage
checkpoint below; these later operations establish no Package6, signing, super,
OTA or boot result. No new full-suite pass or flashable-ROM claim is made.

## Images6 verified build result — 2026-09-02

The **Images6 native build, profile postcheck and complete
source/action/retention review pass**.
The root dispatch runs **21:01:54–21:13:01 UTC**, exit **0**; native execution
runs **21:06:06.519620–21:08:58.623094 UTC**, also exit **0**. Observed Ninja
uses the exact `-j8` invocation with verified limits and sandbox namespaces:
read-only source and writable work/output. No fallback or resource breach is
recorded.

All **seven installed-output actions are `fresh_success`**: vendor, ODM,
mi_ext and recovery images plus three policy SHA sidecars. Recovery has **two
verbose executions but one fresh installed-output row**; the other six actions
each have one verbose execution. Freshness is not inferred from matching bytes.
The four current images total **5,943,386,112 bytes** and match selected input
identities; recovery remains the working76 derivative (`a130ba75…`).

All **six complete callback maps match before/after and Nothing11's after-map**,
with **548 source files/fifteen projects** and the exact requested configuration.
The original validator replays all six metadata bodies byte-for-byte. Build
identity stays **`nezha.86e40fe309189fdcd20dff9b`**, epoch **1788144555**;
normal Android enforcing and strict 4 KiB checks remain unchanged.

Before building, four original images and three original sidecars were retained,
with three independent 65-byte sidecar copies. The separate **read-only native
supplement passes at 21:23:51 UTC**, after running **21:23:47–21:23:51 UTC**.
It reads the complete original before/after Ninja logs inside the VM and replays
the original verbose/action functions, reproducing **all seven action objects
exactly**. It hashes all **5,943,386,112 bytes** of the four retained original
images after the build, verifying their original inodes and modes, plus **nine
sidecars / 585 bytes** (three active, three originals, three independent copies).
All **24 observations** retain their final nine-field stat and ancestor seals.

The root and independent host retention reviews pass. All **four compact raw
records / 73,852 bytes** are replayed, including **12 image and 17 sidecar journal
events**. No large image or Ninja-log bodies are exported. This closes the supplement
left pending by the preserved primary review; `metadata_hook_verified`, runtime,
signed-parent-chain verification and image reproducibility remain unverified.

Fresh four-log capture also passes at **21:16:11 UTC**. Exact local evidence
below is relative to `reports/avb-sha256-20260902/`.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `native-preparation-v1/root-images-6-v1/stdout.jsonl` | `0feeedecf05e367e88911ae13c14b4f2e1af1e1644ba95af91c8aa6395e0df3e` | 10,699,989 |
| `native-preparation-v1/root-images-6-v1/exit.json` | `08d90f50db32bf66f4a4973313075ff47403883bec903d0b3ffa73bda2a9b172` | 64 |
| `resume-build-20260902-v1/root-images6-native-dispatch-v1/completion.json` | `cc899707e17552afa9d381b9f556050e43ff4c06b15a7a1089a0218d8b099590` | 610 |
| `resume-build-20260902-v1/root-images6-result-review-v1/review.json` | `b97892a72fe31ef592d4df5c098a54176bf28a006605fda931c54bda89148441` | 6,982 |
| `resume-build-20260902-v1/five-sha256/post-images6-four-logs-v1/actual-v1/stdout.json` | `d0aca70cc0327147f08c1bbe69bd32d88950545bf6e611a96b81f721a62d34ea` | 80,384 |
| `resume-build-20260902-v1/root-images6-supplement-dispatch-v1/stdout.json` | `93c50d697a2619ad5b540973444667c6b35395d91995de7bbd66ac427f976756` | 219,731 |
| `resume-build-20260902-v1/root-images6-complete-review-v1/review.json` | `3b8efcb6aa0f671cb3b0e56802b56f766340b157fee888384d87625db5c04202` | 6,280 |
| `resume-build-20260902-v1/images6/actual-retention-result-review-v1/review.json` | `84350f24d978c8d13b03905b596aa1d47ba8a1a458d197ef2e47adeaf7d327ce` | 12,786 |

At this earlier checkpoint the five-image query's host preparation is complete,
and its **fresh read-only native capture starts at 21:31:09 UTC** with the result
then pending; later verified query/staging is recorded above.
The no-invalidation five-image SHA-256 build, Package6, signing, complete
AVB/FEC/VINTF/super/partition checks, OTA and boot remain separate gates. No phone
operation or additional cleanup is part of this checkpoint, and the ROM is
**not flashable**.

## Host scratch and Package5 duplicate retirement — 2026-09-02

Two host-only retirements complete at **20:23:45 UTC** (six old TAR/synthetic
scratch files) and **20:31:31 UTC** (15 duplicate materialized Package5 images).
The retired v12e TAR belongs to a **successful historical predecessor**, not a
failed build; its logs and seed/source evidence remain preserved.

Before P5 removal, the root rehashes the complete retained ZIP and verifies
full-byte joins for **13 unique ZIP members plus two original stock inputs**.
All **507 controls**, keeper records and nine-field guards remain unchanged.
The **10,997,962,405-byte P5 ZIP** (`622073f3…`), original `countrycode`/`pvmfw`
inputs, all 15 small records and every directory are kept; only the 15 image
leaves and their historical inode identities are lost. **The old P5 input
manifest is historical/incomplete until all bodies are restored and freshly
validated.** No active body consumer or fallback is selected, and Package6 is
not used as a replacement.

The six scratch files occupied **1,159,380,992 allocated bytes**, with an
observed host-free increase of **1,148,145,664 bytes**. The P5 duplicates occupied
**9,671,483,392 logical/allocated bytes**, with a separate host-free increase of
**9,670,361,088 bytes**. The two observed deltas total **10,818,506,752 bytes
(10.08 GiB)**; final host availability is **165,457,305,600 bytes (154.09 GiB)**.
These operation-local observations may include concurrent host activity; do not
add allocation sizes again or attribute earlier cleanup gains to this step.

Evidence below is relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `small-host-scratch-retirement-v1/root-retirement-v1/completion.json` | `d4eb0fe0d188e097880a29bd95c8e159b5c39aa1735d0496badeee482de2ebf6` | 1,617 |
| `package5-materialized-duplicate-review-v1/root-body-replay-v2/replay.json` | `4b307c6305bad484f9d4b0cb15b0c55b80c16ab096ad93511b846918e5d8d881` | 1,349,445 |
| `package5-materialized-duplicate-review-v1/root-retirement-v1/completion.json` | `12b373bc88c736a372a34fc9399a7d6b462aa5002131ceec0077dcc77838b406` | 4,898 |
| `root-images6-capture-dispatch-v1/completion.json` | `025a4e6a6032c37b575af0bf99401398f6e079d20496536c8f023bcf593c86d1` | 1,719 |
| `root-images6-capture-review-v1/review.json` | `bde24a01d2b27b19680141a34aa811377519d242bd95d2317617eb44f46b4bad` | 10,743 |

The subsequent Images6 read-only capture closes successfully at **20:31:59
UTC**. Root replays its complete packet and outer/source joins, both guarded
Ninja query streams and unchanged before/after target and log observations;
all 143 held inputs remain unchanged. Recovery-specific proof and the actual
image rebuild still require their own results. These retirements and capture
run no image build or phone operation and establish no Package6, signing or ROM
result; the existing Selected4 and earlier cleanup checkpoints remain intact.

## Second old-output cleanup and trim — 2026-09-02

The approved historical-intermediate removal completes with native **exit 0**
at **20:06:51 UTC** and root completion at **20:06:52 UTC**. It deletes exactly
**169,727 descendant entries**—124,631 regular files, 45,092 directories and
four symlinks—from these two reviewed roots, leaving both root directories
present and empty:

- `/work/out/nezha-framework-20260827T1835Z/soong/.intermediates`
- `/work/out/twrp-nezha/soong/.intermediates`

The current user-policy output, source checkouts and installed tools are not
deleted. Historical TWRP intermediate-object replay is explicitly relinquished;
this does not remove the selected working76 recovery. The independent host
review joins all 169,727 manifest entries to the saved deletion counts and
metadata hashes, including all recorded progress prefixes. It verifies saved
evidence, not a fresh whole-filesystem or all-file-content integrity probe.

Guest availability increases from **392,391,049,216** to **408,497,520,640
bytes**, a **16,106,471,424-byte** recovery. The deletion receipt performs no
trim, and its concurrent host-free change is not attributed to the cleanup.

The separately approved free-block trim stops the idle original builder and
uses a temporary maintenance container, then restores the same sole writer.
Maintenance completes at **20:13:53 UTC**, with post-restart identity checks
completed at **20:14:46 UTC**. The temporary container is removed and the
original configuration remains identical (`c8898a8f…`). The output alias and
four complete log hashes/nine-field stat records match across the restart, as
do all three selected sentinel hashes and stat records. Full source
revalidation remains deferred to the next native phase.

The trim's measured **host-free increase is 16,114,458,624 bytes (15.01 GiB)**.
The backing allocation decreases by **16,135,897,088 bytes**, a different
measurement; its 1 TiB logical size is unchanged. Final host availability after
the post-restart checks is **154,373,144,576 bytes (143.77 GiB)**. Do not add the
guest deletion to the host trim delta, or count either operation again in the
earlier [229.28 GiB cleanup checkpoint](storage-cleanup.md). These are dated
observations, not reserved space or proof of a complete future build budget.

Exact local receipts below are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `old-output-prune-preparation-v1/actual-v1/completion.json` | `7bfecc6e5f6c5c0fd89405a5c9547d7e2454727bf546db9f0c2af657f98709ac` | 5,980 |
| `old-output-prune-preparation-v1/actual-review-v1/review.json` | `7d7e54ad412d1245e6bf0d2a7a0fd8e52761af212ffcb5368d630e43579dd8d6` | 6,677 |
| `old-output-trim-preparation-v1/actual-v1/completion.json` | `e99d128dbe86837d063b8b7263e8bf24567556f396abaeec6bcdf240b475ebba` | 1,207 |
| `old-output-trim-preparation-v1/second-trim-completion.json` | `27bbb26071f6f1dece3dac964253d3748f1340f8299408df727a31c57f73c567` | 2,424 |

**Images6 capture is in progress**, not a completed image build or admission.
The existing Selected4 result below is unchanged. This cleanup performs no
Android build or phone operation and does not establish image integrity,
signing, complete AVB/FEC/VINTF/super/partition checks, OTA or bootability.
The five-image SHA-256 stage and Package6 still need their own actual results.

## Selected4 component build — 2026-09-02

The **Selected4 native component build, profile validation and postcheck pass**.
Native execution runs **19:24:16.647368–19:25:59.283964 UTC**, exit **0**; the
genuine root wrapper runs **19:19:44–19:37:41 UTC**, also exit **0**. The result
contains **26 fresh producer actions and eight fresh strict library statuses**.
Ninja observation is required and passes, with verified argv, limits and sandbox
checks; no timeout, overflow, disk-floor breach or sandbox fallback is recorded.

The nine selected APKs are BCR and eight SystemUI Clocks. Their configured
signature/certificate and manifest-field checks pass through **36 recorded
command results**. Flex has a separately verified **current-equivalent prior
strict check**, not a ninth freshly produced status. The signature checks do
not establish verification of every embedded scheme; selected manifest fields
are not complete XML equivalence or runtime library compatibility.

Backup-first preparation and the postcheck verify **26 retained originals plus
26 independent copies**: nine built APKs, nine installed APKs and eight status
outputs in each set. This is scoped output retention, not a fresh archive of
the entire output tree. All **six complete source/input callback maps match**
before/after, preserving **548 selected source files** and **1,179 project
HEAD/origin matches**. Build identity remains
**`nezha.86e40fe309189fdcd20dff9b`**, epoch **1788144555**. Normal Android
enforcing, strict 4 KiB checks and the working76 recovery selection are unchanged.

The root's **19:39:52 UTC result review** checks the complete actual result,
its bound records and all 85 held controls. It does **not** independently replay
the raw signature/manifest stdout. Their separate export and raw-stream replay
remain outside this checkpoint; the command-record review must not be described
as that completed replay. The original result and preservation records remain
unchanged.

Actual local receipts below are relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`. The result's `.jsonl`
file contains one complete JSON object.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `selected4/activation-v1/bound-nothing11-selected-four-v1/root-selected4-native-v1/stdout.jsonl` | `21b352c65eb079ee8dd56689d34c2454783488705d5bd0ac8db212676264fd33` | 11,521,390 |
| `selected4/activation-v1/bound-nothing11-selected-four-v1/root-selected4-native-v1/exit.json` | `e7983de17dd7319d34b8b0a635daa339b4894064cf080b629bc2cf4d5359eebd` | 81 |
| `root-selected4-dispatch-v2/completion.json` | `01469750646df6cd0ae4a20dc3d5cd99bcb038c55d82f1aad93600fa75963955` | 1,366 |
| `root-selected4-result-review-v1/review.json` | `aba72b26ae59002ab23fcfd83ac26bf91efded21f065705afd66fc0d72e206eb` | 10,032 |

**Images6, the no-invalidation five-image SHA-256 stage and Package6 still need
their own actual results.** This component result admits no new images or
signed ROM. Signing, complete AVB/FEC/VINTF/super/partition checks, OTA and
device boot remain unverified. No source mutation, new private-key transfer or
phone operation occurs; the ROM is **not flashable**.

## Nothing11 passes after storage cleanup — 2026-09-02

This earlier checkpoint preserves its frontend-only scope and then-pending
Selected4 component work.

The resumed **Nothing11 native invocation and profile validation pass** after
the [completed cleanup](storage-cleanup.md). The genuine root wrapper runs
**17:46:40–17:56:39 UTC**, exit **0**; the native
`build/soong/soong_ui.bash --make-mode -j8 nothing` invocation runs
**17:51:18–17:53:01 UTC**, also exit **0**. Preflight, profile completion and
profile validation are true, with an empty postcheck-error list. The metadata
postcheck passes, including independently decoded and rehashed captures of all
six metadata files under **`nezha.86e40fe309189fdcd20dff9b`**, epoch
**1788144555**.

All **six complete before/after callback maps are identical**. The raw
**254-field** Soong configuration also remains identical, SHA-256
**`da93ab71dc9ad8d9d9cdf8327927ce29796f658bcf58292939a0bd48e819af6e`**,
**319,139 bytes**. It matches both frozen expected maps, including the top-level
system SHA-256 arguments and the five partition-qualified SHA-256 strings.
The earlier Nothing10 failure and its false profile flags remain unchanged;
this is a separate successful successor, not a rewritten failure.

Source checks retain **548 files/fifteen projects**, all **1,179 HEAD/origin
matches**, **1,170 clean projects** and **nine expected patched projects**.
The root completion verifies all **180 frozen host inputs** unchanged and all
three actual preparation files identical to the prepared copies. Strict ELF
and alignment checks, **4 KiB**, normal Android **enforcing** and **working76**
remain required.

Ninja is observed with verified limits and sandbox checks, but
`ninja_argv_verified=false` and `require_observed_ninja=false` remain explicit.
There is no timeout, output overflow, disk-floor breach or sandbox fallback.
This `nothing` profile does **not** verify fresh component/image producer
actions. Output invalidation/deletion and source-mutation requests remain
false. The observation and metadata scope flags retain their narrow meaning;
`complete_rom_ready`, `signed_flashable_rom_verified` and
`image_reproducibility_verified` are still false.

Actual local receipts below are relative to
`reports/avb-sha256-20260902/native-preparation-v1/`. The result's `.jsonl` suffix
is historical: its contents are one JSON object. These ignored receipts are
not distributed by the workspace.

| Receipt | SHA-256 | Bytes |
| --- | --- | ---: |
| `root-nothing-11-v1/stdout.jsonl` | `b1b49614410164dba641622eaf0cef94e2ded51f2a7c6dc7f65ae6f3c960f03f` | 10,627,550 |
| `root-nothing-11-v1/exit.json` | `0e4ba8d7f0b6b515dd2ef531dd9515939cbecfc297571aafe2ec6fb1ff55405c` | 66 |
| `root-nothing-11-dispatch-v1/completion.json` | `d0316a17510b33bae0e5184980288eb4d4b50e131dce9a0cc203fde4fb23d31a` | 764 |
| `root-nothing-11-review-v1/review.json` | `f07908ba753d6cb0c22e6332410d70b7ab232614dd1162f4d9795ba9a8a0c533` | 4,637 |

Backup-first Selected4/Images6, the no-invalidation five-image SHA-256 stage
and Package6 still need their own actual results. Signing, complete
AVB/FEC/VINTF/super/partition checks, OTA and device boot remain unverified.
No phone operation occurs and no flashable ROM is established.

## Nothing10 profile failure and host-storage hold — 2026-09-02

This section preserves the earlier hold and then-pending Nothing11 state;
the successful successor is recorded above.

Nothing10's native invocation runs **15:50:45–16:05:06 UTC** and **exits 0**, but
**profile completion and validation remain false**, with a null postcheck.
The genuine root wrapper runs **15:46:24–16:06:23 UTC** and exits **1**. The
original result, error records and completion are preserved without promotion.

Root diagnosis and full raw configuration comparison identify exactly **six
changed leaves** within the **254-field** configuration; every other value
and type is unchanged. `BoardAvbSystemAddHashtreeFooterArgs` becomes
`["--hash_algorithm", "sha256"]`; five nested `BoardAvbAddHashtreeFooterArgs`
strings become `"--hash_algorithm sha256"` for **product, system, system_dlkm,
system_ext and vendor_dlkm**. The request predicted only the top-level list.
Source-history and strict-settings postchecks reject the incomplete expected
map. The archive check then lacks current-phase source history; its dependent
error is **not proof of archive corruption**. The observed after-configuration
is `da93ab71…`, **319,139 bytes**, and is not admitted by the failed profile.

Ninja is observed, with verified limits and sandbox checks, but
`ninja_argv_verified=false` and `require_observed_ninja=false`; no fresh
component or image result is established. Output invalidation/deletion is
false. All **1,179 HEADs/origins** still match, with **1,170 clean projects and
nine expected patched projects**. The selected source still covers **548
files/fifteen projects** and uses the unchanged
**`nezha.86e40fe309189fdcd20dff9b`** identity; this failure does **not establish
six successful after-callbacks**. The successful
**16:16:08 UTC** four-log readback is bounded evidence, not graph admission.

Host-only Nothing11 check, bind and preparation commands close with exit 0 at
**16:25:28 UTC**. Root's separate **36 focused tests** (13 bridge, 17 source,
six caller cases) pass at **16:28:09 UTC**, with eleven held inputs unchanged.
These results neither dispatch Nothing11 nor establish native-wrapper
readiness or a successful successor profile.

At **16:26:15 UTC**, the maintained host reserve check fails: **63,488,000,000
bytes** are available against **107,374,182,400 bytes (100 GiB)** required.
The measured shortfall is about **40.87 GiB**. An additional **45 GiB** was
requested for the minimum reserve, not the complete follow-on budget. The
VM's roughly 267 GiB free does not clear the host-volume requirement. Native
work stays on hold; the guard is unchanged and the failed check starts no VM
operation or source/output mutation.

Nothing11, backup-first Selected4/Images6, the no-invalidation five-image
stage and Package6 remain pending. Normal Android enforcing, 4 KiB and
`working76` are preserved. Signing, full AVB/FEC/VINTF/super/partition checks,
OTA and device boot remain unverified; no phone operation or flashable ROM is
established. [Exact forward evidence](../research/workspace-integration.json)
retains the earlier source/query and Package5 failure history.

## SHA256 source adoption and Config13/context13 — 2026-09-02

The **reviewed SHA-256 producer correction is installed**, followed by two
successful native queries under **`nezha.86e40fe309189fdcd20dff9b`**, epoch
**1788144555**. All intervals below are September 2 UTC; each listed exit is 0.

| Phase | Recorded interval and completion scope |
| --- | --- |
| Source staging | Root command 14:26:29–14:35:35 |
| Source installation | Root command 14:38:12–14:50:37 |
| Config13 | Native query 15:07:30–15:08:27; direct host exit observed at 15:13:07 |
| Context13 | Native query 15:20:19–15:21:25; genuine wrapper 15:15:19–15:25:36 |

Full raw-record verification at **14:52:32 UTC** confirms **one 35-file
device-tree exchange and five journal events**. Only `BoardConfig.mk` changes
within **548 source files/fifteen projects**, adding the five explicit
SHA-256 hashtree footer arguments. The journal's **14:47:13 `commit_verified`**
event precedes final command completion. Other source bytes, metadata and
preserved image/recovery inputs remain unchanged; no image build is established.
Host identity projection verifies the actual installed records and eight
derived outputs before the query results establish the new build number.

Both queries pass their postchecks and six complete before/after callback-map
comparisons. All **1,179 HEADs/origins** match, with **1,170 clean projects and
nine expected patched projects**. The **254-field configuration is identical**
between Config13 and Context13. Config13 retains its direct-launch,
26-input byte-only closure scope: no outer wrapper timing, full outer streams or prelaunch-stat
snapshot is claimed. Neither query records observed Ninja or sandbox success.

The **15:27:28 UTC** readback verifies the complete **49,437-byte Soong writer**
against build/make commit `a438ca40c6ed779042f806142b1165ba1360a7b2` and the
installed **4,131-byte BoardConfig**. The expected single Soong field change,
`BoardAvbSystemAddHashtreeFooterArgs: [] → ["--hash_algorithm", "sha256"]`, is
source-derived only: no regenerated after-configuration is observed or admitted.

Nothing10, backup-first Selected4/Images6, the no-invalidation five-image stage
and Package6 require their own actual results. The earlier Package5 archive,
SHA-1 images and failed AVB/VINTF checkpoints remain historical evidence.
Normal Android enforcing, 4 KiB and `working76` are preserved. No source sync,
phone operation or private-key transfer to the VM occurs. Signing, complete
AVB/FEC/super/partition/VINTF, OTA and boot/hardware remain unverified; no
flashable ROM is established. The [forward checkpoint](../research/workspace-integration.json)
binds actual adoption, identity, query and writer-readback receipts.

## Package5 host inputs and AVB/VINTF failures — 2026-09-02

The complete **10,997,962,405-byte** Package5 ZIP is independently admitted on
the host with SHA-256 **`622073f36dd1c0f733f1ed1d09518380190a58a80f4615586c815430bd9768b4`**.
Copier v1 exits 1 at **12:40:56 UTC** with zero bytes and `EAGAIN`. Copier v2
copies the full archive but exits 1 at **13:09:49 UTC** on `input ancestor
changed` during final publication checks. Neither is marked successful; no
`transfer.json` or after-copy volume receipt is invented. Fresh independent
admission reuses the original held-file/ancestor and paired-result guards,
rehashes the whole host ZIP and verifies its native proof without another copy
or fresh volume check.

| Actual host phase | Result on September 2 UTC |
| --- | --- |
| Independent archive admission | 13:21:47–13:21:54; passes separately from the failed copier |
| Maintained input inventory | 13:23:12–13:24:04, exit 0; complete required-role inventory |
| Image materialization | 13:25:18–13:27:27, exit 0; 13 ZIP images plus two retained inputs |
| AVB plan | 13:28:30, exit 0; ready for public preparation, not a signing result |
| AVB public preparation | 13:28:31–13:28:43, exit 2; invalid hash/hashtree algorithm, digest or flags |

The materializer publishes **15 images**, its input manifest and receipt under
`artifacts/avb/nezha/package5-20260902-v1/inputs`. The returned result verifies
publication; the retained byte-verification receipt remains explicitly
prepublication evidence. Materialization is not image-format, signature,
partition-fit or compatibility verification.

Public preparation fails before private-key use. Read-only descriptor diagnosis
finds SHA-1 hashtrees with 20-byte digests in **product, system, system_ext,
system_dlkm and vendor_dlkm**, contrary to the reviewed SHA-256 profile. The
other **ten strict metadata parses pass**. The parser remains unchanged; this
metadata-only diagnosis does not rehash whole images or establish the complete
AVB chain, FEC or a finished public image set.

Separately, VINTF staging verifies **31 files** without running native checks.
Capture transport exits 1 at the original property parser:
`malformed property/metadata line: ODM/etc/build.prop`. Empty stdout contains
no ACK, and no successful capture completion is recorded. The exit receipt
does not verify guest termination or admit native success. These receipts have
no in-band start/end timestamps; no timing or VINTF compatibility result is
inferred.

The SHA-256 source-producer correction and faithful property-parser successor
are in progress, **not validated or adopted**. Normal Android enforcing, 4 KiB,
`working76` and prior Package5 history remain preserved. Private signing, a
complete 17-image public set, ZIP reconciliation, FEC, super-image/partition,
full VINTF, OTA and boot/hardware checks remain open. No phone operation occurs
and no flashable ROM is established. The [checkpoint record](../research/workspace-integration.json)
binds closed receipts without promoting failed or partial results.

## Package5 corrected supplement and complete evidence replay — 2026-09-02

The **separate corrected Package5 post-build verifier passes** in the VM's
Python supervisory harness, running **12:07:34–12:17:30 UTC**. Actual host
session **84870** exits 0, observed at **12:17:32 UTC**; polling does not supply
a separate process duration. No build, output preparation or verbose capture
is rerun. The original native-exit-0/host-exit-1 result, false profile flags,
null postcheck and `AttributeError` remain unchanged.

The checker correction has three literal changes: the existing
`_impl['_installation_report']` callback and defaults for two absent image-mode
keys. Its eight-test qualification passes. The actual supplement verifies
**two original fresh directory/ZIP producer actions**, fresh metadata-hook
execution, **205 metadata members** and **221 selected ZIP members**. The
native archive is **10,997,962,405 bytes**, SHA-256
**`622073f36dd1c0f733f1ed1d09518380190a58a80f4615586c815430bd9768b4`**,
with **9,154 entries**. These checks do not verify every member's contents or
complete archive semantics. Six complete callback return maps and 26 captured
native files match before/after; the root verifies 14 held host inputs.

The root's complete finite-evidence replay runs **12:33:17–12:33:21 UTC**,
exit 0. It verifies **242 files / 168,788,306 bytes**, all five export wires and
final nine-field seals, **286 held host inputs**, **219 expanded-member
bodies**, the original six-metadata validator, seven policy bodies and three
recomputed sidecars. Original producer objects, append-only logs, gzip/plain
equality and the separate supplement's original receipt verifier pass. Pure
consumer filesystem/process/network calls are blocked. Paired-result admission
is a **separate passing replay**, not a call made by this finite-body replay.

**ZIP and image bodies are not exported or read on the host**; archive identity
remains native postcheck evidence. The earlier root decode/native-review
receipts keep their then-pending replay flags as history. Neither the original
failed profile nor older image-only scope flags are rewritten.

Source **548/fifteen projects**, **`nezha.b429840950d789320b04847a`**, epoch
**1788144555**, normal Android enforcing, 4 KiB and `working76` remain unchanged.
Controlled ZIP transfer, final AVB/VINTF/partition, signing/rollback, OTA and
boot/hardware checks remain separate. No phone operation occurs and no complete
or flashable ROM is established. The [supplement record](../research/workspace-integration.json)
binds the native, paired-admission and complete finite-replay evidence.

## Package5 native exit and profile postcheck failure — 2026-09-02

**Package5's native Soong invocation exits 0; its original profile
postcheck fails.** Native execution runs **11:36:58–11:41:29 UTC**. Direct host
session **55609** exits 1, observed at **11:47:38 UTC**; no outer wrapper or
separate process duration is inferred from polling. Preflight, invocation and
native-process success are true, but **`profile_completed=false`**,
**`profile_validation_verified=false`** and **`postcheck=null`** remain in the
original result.

The only recorded postcheck error is **`AttributeError`**: module
`actual_nezha_target_files_verifier` has no `_installation_report` attribute.
This check runs in the VM's Python supervisory harness.
Native Ninja observation, argv, limits and sandbox checks pass, with
observation required. There is no output overflow, timeout, disk-floor breach
or sandbox fallback. All six complete callback maps match before/after; the
root verifies **28 held host files** with full hashes and nine-field stats.

Read-only native stream capture completes at **11:50:08 UTC**, with root decode
verification at **11:50:34 UTC**. The two complete files contain **801,876-byte
stdout and empty stderr**; two-pass seals and nine-field stats match. The
original traceback, result and failed profile flags remain preserved.
Full stream readback is **not archive admission, ZIP validation or proof of
the two fresh package actions**.

A proposed checker correction uses the existing
`tool._impl['_installation_report']` callback. Two absent-mode default lookups
are **separate static findings**, not errors observed in this native run.
Corrected-checker preparation and an actual supplementary postcheck remain
pending; no native source installation, rebuild or original-flag rewrite is
claimed.

Source **548/fifteen projects**, **`nezha.b429840950d789320b04847a`**, epoch
**1788144555**, normal Android enforcing, 4 KiB and `working76` remain unchanged.
Final AVB/VINTF/partition, signing/rollback, OTA and boot/hardware remain open.
No phone operation occurs and no complete or flashable ROM is established.
The [Package5 failure record](../research/workspace-integration.json) binds
exact original and full-stream receipts while preserving all prior history.

## Images5 and complete evidence replay — 2026-09-02

The **Images5 native build, postcheck and complete original replay pass**.
Native execution runs **10:53:23–10:56:15 UTC**, exit 0. Direct host session
**99619** is observed closed at **11:00:30 UTC**; no outer wrapper or separate
process-start/duration is inferred from polling. All five phase checks and
Ninja observation, argv, limits and sandbox checks pass, with observation
required. The postcheck verifies **seven fresh actions**, recomputes the
**plat/product/system_ext** sidecars and checks **mi_ext/odm/recovery/vendor**
images. Four original image inodes and three sidecar copies plus three
originals remain retained; `working76` remains the prebuilt recovery derivative.

The successful unchanged host replay finishes at **11:14:38 UTC**; the root's
independent repeat runs **11:15:18–11:15:20 UTC**, exit 0, with byte-identical
output and the full strict-stat check passing. Replay covers **56 complete
files / 144,374,566 bytes**, including both native build streams, **twelve
current/preserved metadata files**, **seven compiler/policy pairs**, nine
sidecar active/copy/original bodies with nine independent native inodes, twelve
image-journal events, seventeen sidecar-journal events and nine staged proofs.
The first host replay failed its final whole-file-stat check; its original
empty stdout and failure stderr remain preserved. Diagnostic and repeat runs
pass with unchanged code and guards. The cause is **unproven**; this retained
host replay failure is separate from the successful native Images5 build.

Large image and graph bodies are **not exported or read on the host**; image
hashes rely on the completed native postcheck, not host rehashing. Ordinary
**`postcheck.metadata.verified=true`** does not establish the image packaging
hook: **`images.metadata_hook_verified=false`**, runtime and signed-parent-chain
verification remain false. Neither replay nor byte equality establishes a
fresh metadata rewrite or image reproducibility.

All six complete callbacks match before/after Images5. Source **548/fifteen
projects**, **1,179 revisions/origins**, **254 configuration fields**,
**`nezha.b429840950d789320b04847a`**, epoch **1788144555** and the existing
**171,821,860-byte `.ninja_deps` guard** remain unchanged. Package5 is a separate
pending build/ZIP gate. Normal Android enforcing, 4 KiB, `working76`, kernel
warnings and `test-keys` remain unchanged. Final AVB/VINTF/partition,
signing/rollback, OTA and boot/hardware remain open; no phone operation occurs
and no complete or flashable ROM is established. The [Images5 record](../research/workspace-integration.json)
binds exact successful receipts and retains all prior failures and checkpoints.

## Selected3 and complete evidence replay — 2026-09-02

The **Selected3 native build, postcheck and complete original replay pass**.
Native execution runs **09:56:02–09:57:46 UTC**, exit 0. Direct host session
**50729** is observed closed at **10:09:29 UTC**; no outer wrapper or separate
process-start/duration is invented from its poll timing. All five phase checks
and Ninja observation, argv, limits and sandbox checks pass, with observation
required. The rebuild verifies **26 fresh producer actions, eight fresh strict
statuses and zero reuse**; the verified prior Flex check is separate, with no
fresh or reused Flex status claimed.

The original consumer replay passes at **10:22:42 UTC**. The root independently
repeats it at **10:23:17–10:23:24 UTC**, exit 0, reproducing all three products
byte-for-byte. The four complete two-pass exports retain original records and
nine-field seals for **203 files / 165,615,424 bytes**. Replay covers 200
evidence files, **227 held inputs**, 36 recorded verification attempts, all
72 attempt streams and both build streams. Consumer filesystem, process and
network access are blocked during replay.

Two retention-metadata files authenticate **26 native copies and 26 originals**;
the 52 retained binary bodies are **not exported or rehashed on the host**.
Freshness comes from native action evidence, not matching bytes. The host-only
Package5 source-context projection uses recorded component observations; it
is not a fresh physical Package5 observation or a package run.

All six complete callback maps match before/after Selected3. Source
**548/fifteen projects**, **1,179 revisions/origins**, **254 configuration
fields**, **`nezha.b429840950d789320b04847a`** and epoch **1788144555** remain
unchanged. The post-build collector retains `.ninja_deps` at **171,821,860
bytes** under the existing guard; this is not new graph or package admission.
Images5 and Package5 remain separate gates. Normal Android enforcing, 4 KiB,
`working76`, kernel warnings and `test-keys` remain unchanged. Final
VINTF/AVB/partition, signing/rollback, OTA and boot/hardware checks remain open;
no phone operation occurs and no complete or flashable ROM is established.
The [Selected3 record](../research/workspace-integration.json) preserves exact
receipts and all earlier source, query, component and packaging history.

## Config12/context12 and Nothing9 — 2026-09-02

The **two native queries, Nothing9 and complete host review pass** under
**`nezha.b429840950d789320b04847a`**, epoch **1788144555**. All times below are
September 2 UTC; every listed native/host exit is 0.

| Phase | Native invocation | Actual host completion evidence |
| --- | --- | --- |
| Config12 | 08:27:52–08:28:46 | Direct session 2103 exit observed at 08:32:16; separate byte-only closure |
| Context12 | 08:38:16–08:39:08 | Genuine wrapper 08:34:37–08:42:45 |
| Nothing9 | 08:52:20–09:04:46 | Genuine wrapper 08:48:44–09:08:22 |

Config12's closure checks **26 frozen byte pins** and three preparation files.
It does not establish an outer wrapper, process-start/duration, full outer
streams or prelaunch stat snapshot; its separate root review validates the
native result. Neither query records observed Ninja or a sandbox pass.
Nothing9 records Ninja observation, limit checks and sandbox success, but
**`ninja_argv_verified=false`** and **`require_observed_ninja=false`**. No fresh
component-action or metadata-rewrite claim follows from this run.

Actual full stream capture completes at **09:15:17 UTC**. Original host review
passes at **09:17:54 UTC**, followed by the independent root recheck at
**09:19:15 UTC**. They verify **18,460-byte stdout, empty stderr**, six physical
metadata values/newlines and all **six complete callback maps** before/after
and across both queries. **21 held host-review files** retain their full bytes
and nine-field stats; this does not upgrade Config12's launch evidence. The
original source validator confirms **548 files/fifteen projects**, **1,179
revision/origin matches**, **254 configuration fields** and strict 4 KiB.

The next native gates are the **fresh 26-action selected-component rebuild,
Images5, then Package5**; none is established here. Normal Android enforcement,
`working76`, kernel warnings and `test-keys` remain unchanged. Final
VINTF/AVB/partition, signing/rollback, OTA and boot/hardware checks remain open.
No phone operation occurs and no complete or flashable ROM is established.
The [query/Nothing9 record](../research/workspace-integration.json) binds exact
receipts while retaining all earlier source, component and Package4 history.

## Metadata-mode flags source installation — 2026-09-02

The **reviewed metadata-mode correction is installed**, with verified exit 0.
The root install command runs **08:09:40–08:19:10 UTC**; full readback completes
at **08:19:21 UTC**. The journal's **08:16:15 `commit_verified`** event is an
intermediate milestone, not the final command completion time. Earlier staging
exits 0 at **08:08:00 UTC**, with 975 independent observed inodes checked.

The original record validator accepts **nine journal events and three ordered
atomic exchanges**. Source remains **548 files in fifteen projects**, with
**seven existing content replacements**, preserved modes, expected local patch
statuses and all **1,179 revision/origin matches**. Image, kernel, recovery and
Makefile contents do not change. The installed checksum runtime is
**`c4029700d44fc0273c5716aafd4bc0389aa236084baaddce8afbefedb8d2aff2`**
(**222,151 bytes**), and its 205-file original metadata-source projection passes.

The retained **254-field configuration** remains unchanged;
**`nezha.a7db36604f45fcc657373f89`**, epoch **1788144555**, identifies the prior
native configuration/build outputs, not the newly installed source identity.
No successor identity calculation or config12/context12, Nothing9, Images5 or
Package5 success is included in this source-only checkpoint. Normal Android
enforcement, 4 KiB, `working76`, kernel warnings and `test-keys` remain unchanged.
Final VINTF/AVB/partition, signing/rollback, OTA and boot/hardware gates remain
open; no phone operation occurs and no complete or flashable ROM is established.
The [source-adoption record](../research/workspace-integration.json) retains exact
installation, journal and readback pins. Package3/Package4 failures and earlier
checkpoints remain historical evidence, not erased or promoted to success.

## Package4 build-metadata mode failure — 2026-09-02

The **Package4 native retry fails**, exit 1, running **07:13:33–07:15:57 UTC**.
The root's direct unified session **78585** also exits 1. Preflight and native
invocation occur; native success, profile completion and profile validation
are false, with no package postcheck or successful target-files ZIP verified.
Ninja observation, argv, limits and sandbox checks pass; no timeout, disk-floor
breach or output overflow explains the failure. All six complete callbacks
match before/after this run; no equality with Nothing8 is claimed.

Complete native stream readback finishes at **07:24:35 UTC**, exit 0, retaining
**45,834-byte stdout and empty stderr**. Full canonical payloads and nine-field
final seals match the native result. Stdout records the failed `.zip.list`
target, checksum `OK`, then **`native target-files mode differs`**. This guard
concerns packaging build metadata, not file permissions. The separate
**285-byte host transport stderr** is the failed-invocation/profile traceback,
not native build stderr.

The closed three-file metadata collector succeeds at **07:35:23 UTC**. It
retains **227,334 bytes**: `misc_info.txt` **6,930**, `kernel_version.txt` **52**
and `kernel_configs.txt` **220,352**. Two complete reads agree; quiescence,
canonical payloads and all nine stat fields pass. Misc-info bytes and stats
match the earlier diagnostic. Both `building_vendor_image` and
`building_odm_image` are absent, not empty strings; `ab_update=true` and
`vintf_enforce=true` remain present, while `allow_non_ab` is absent. The old
two-flag predicate fails; the host absent-default correction accepts these
flags without weakening the A/B or VINTF checks. Kernel metadata presence is
**not a VINTF compatibility result**.

Two earlier readback failures remain preserved separately from Package4:
collector V1 exceeded its **64 KiB** file bound; V2 failed JSON serialization
of a `Path` argument. V3 uses only the exact measured **220,352-byte** kernel
exception and a canonical relative alias argument; it is a successful
read-only collector, not a successful package retry.

The **current checksum adapter** correction is committed as
**`3e4f904b9118b112c809bb86b79e624f761e4acf`**, with six added regression tests
and **4,463 offline tests passing in 164.533 seconds**. The historical base and
ancestor sources remain byte-identical. Its generated helper and successor
metadata/mi_ext controls are **host-only candidates**, not an installed source
update or a native retry. The VM remains on **548 files/fifteen projects**,
**`nezha.a7db36604f45fcc657373f89`**, epoch **1788144555**.

Prior Package3 failure and Images4 success retain their original scope. Normal
Android enforcing, 4 KiB, `working76`, kernel warnings and `test-keys` remain
unchanged. Final VINTF/AVB/partition, signing/rollback, OTA and boot/hardware
checks remain open; no phone operation occurs and no complete or flashable
ROM is established. The [Package4 failure record](../research/workspace-integration.json)
binds the native result, full readbacks, collector history and committed host
fix without promoting any of them to source adoption or packaging success.

## Images4 and complete evidence replay — 2026-09-02

The **Images4 native phase, image postchecks and complete host replay pass**.
Native execution runs **06:23:50–06:26:44 UTC**, exit 0; all five phase checks
pass. The root's direct unified session **93425** also closes with exit 0 and
zero reported output tokens. No separately measured native outer-wrapper
interval is claimed. Ninja observation, argv, resource-limit and sandbox checks
pass, with **seven fresh actions, three recomputed framework sidecars and four
verified image outputs**. Freshness is established by observed actions, not
matching bytes. Recovery remains the pinned `working76` prebuilt derivative,
not a newly source-compiled recovery runtime.

Four original image inodes and three sidecar copies plus three originals are
retained. Complete host readback covers **56 files / 144,194,084 bytes**: four
live action-evidence files totaling **126,470,036 bytes**, plus 52 remaining
files totaling **17,724,048 bytes**. Original names, all nine stat fields and
final second-pass seals are retained. The root independently repeats the
complete replay at **06:46:10–06:46:12 UTC**, exit 0, reproducing the same
29,020-byte result.

Replay verifies all seven complete fresh-action records, **twelve current and
preserved metadata files**, seven compiler/installed policy pairs, nine staged
proofs, **twelve image-journal events** and **seventeen sidecar-journal events**.
Nine active/copy/retained sidecar bodies retain nine independent native inodes.
Metadata value verification does not establish fresh metadata writes.
**Large image and full graph bodies are not exported to the host**; their
binary-hash claims remain grounded in the completed native postchecks.

All **six complete callbacks match both before/after and actual Nothing8**;
selected-nine2's expanded protected-input callback remains a distinct earlier
scope. Source **548/fifteen projects**, **`nezha.a7db36604f45fcc657373f89`**,
epoch **1788144555**, normal Android enforcement, 4 KiB, `working76`, kernel
warnings and `test-keys` remain unchanged. The post-Images4 collector retains
output `.ninja_deps` at **171,758,884 bytes** and measures `.ninja_log` at
**63,158,114 bytes**; it does not grant package admission.

The metadata packaging hook, image reproducibility, signed parent chain and
runtime remain unverified. Package4 is the next build gate; preparatory
read-only capture is not execution or success. Final VINTF/AVB/partition,
signing/rollback, OTA and boot/hardware checks remain open. No phone operation
occurs and no complete or flashable ROM is established. The
[Images4 record](../research/workspace-integration.json) binds the native result,
full readback and replay receipts; earlier checkpoints retain their original
scope, including the Package3 failure and then-pending work.

## Selected-nine2 and retained-evidence replay — 2026-09-02

The **selected-nine2 native build, postcheck and complete host replay pass**.
Native execution runs **05:28:33–05:30:17 UTC**, exit 0; the genuine root wrapper
runs **05:24:51–05:41:09 UTC**, exit 0. The preceding read-only shared capture
covers 83 queries, and the seven-file proof stage passes before the component
run. The chosen rebuild is **forced fresh**, not a scheduler-skip, cached-status
or optional normal-`-n` result.

All **26 producer actions are fresh**, with **eight fresh strict statuses and
zero reused actions**. Flex's prior strict check is verified, without producing
or reusing a Flex status. Ninja observation, argv, limits and sandbox checks
pass for this component run; Nothing8's earlier argv limits remain historical.
The result intentionally records **`output_invalidated_or_deleted=true`**:
26 copies and 26 originals are retained while the selected outputs are rebuilt.
The independent retention-metadata replay passes at **05:50:38 UTC**, checking
all **109 journal events** and 26 copy/original inode pairs. Those **52 retained
file bodies are not exported or rehashed on the host**; their post-build binary
rechecks are native observations, distinct from host metadata replay.

The four complete exports and final nine-field stat seals cover **203 files /
165,002,879 bytes**. Full consumer replay passes at **05:52:30 UTC**, covering
36 recorded native verification attempts, all 72 attempt streams and both build
streams. The root's separate **05:53:11–05:53:17 UTC `--check-only`** run exits 0
and reproduces the consumer output, host-only package-source projection and
recorded component observations byte-for-byte. The consumer is blocked from
filesystem, process and network access.

All **six native callback results match before and after selected-nine2**.
Against Nothing8, **only five complete callbacks are identical**;
`verify_protected_inputs` contains the same **25 `ordinary_policy_runtime`
rows** plus **180 `selected_app_inputs` rows**. This expected expanded result
does not introduce a new guard. The build remains bound to
**`nezha.a7db36604f45fcc657373f89`**, epoch **1788144555**.

The host-only package-context projection does not execute Package4, reobserve
the 173 GMS prerequisite files or establish current package-time physical state.
The post-selected2 four-log readback retains output `.ninja_deps` at
**171,758,884 bytes** and `.ninja_log` at **63,151,029 bytes**; it is not image
admission. Images4, Package4, final VINTF/AVB/partition, signed-chain/rollback,
OTA and boot/hardware checks remain separate. Normal Android enforcement,
4 KiB, `working76`, kernel warnings and `test-keys` are unchanged; no phone
operation occurs and no complete or flashable ROM is established. The
[selected-nine2 record](../research/workspace-integration.json) binds exact
native, export, retention and full-replay evidence. Earlier checkpoints retain
their original scope and then-pending work.

## Config11/context11 and Nothing8 — 2026-09-02

The **native queries, ordinary Nothing8 and six physical metadata value checks
pass** on the installed 548-file/fifteen-project source. Their completion
evidence has distinct scopes; all times below are September 2 UTC.

| Phase | Native invocation | Actual host completion |
| --- | --- | --- |
| config11 | 03:42:13–03:43:08, exit 0 | Direct host exit 0 observed at 03:47:22; separate 26-pin byte-only closure |
| context11 | 03:57:21–03:58:14, exit 0 | Genuine wrapper 03:53:47–04:01:40, exit 0; 91 held byte/stat checks |
| Nothing8 | 04:12:29–04:25:20, exit 0 | Genuine wrapper 04:09:04–04:28:56, exit 0; root verifies 127 held launch inputs and three actual preparation files |

Config11's later closure verifies exact frozen bytes without inventing an
original wrapper, prelaunch stat snapshot, host start/elapsed time or full outer
streams. Its native result is verified separately. The retained queries contain
**21 config assignments and seven context assignments**; deferred `*_FROM_FILE`
expressions are not physical file readback. The original closure-pending record
remains intact alongside the completed, narrowly scoped closure.

Nothing8 executes **`build/soong/soong_ui.bash --make-mode -j8 nothing`**.
Ninja is observed and its limits and sandbox checks pass, but
**`ninja_argv_verified=false`** and **`require_observed_ninja=false`** remain
explicit. This is an ordinary Nothing8 pass, not fresh component-action or
subsequent app-build admission. All six complete guard maps agree within and
across all three phases; 548 source rows/fifteen projects, all **1,179 pinned
HEADs/origins**, nine reviewed patched projects and **254 configuration fields**
are preserved. The Nothing8 launcher check covers bytes and all nine stat fields
for its 127 held inputs, not a retrospective strengthening of config11.

Complete host review passes at **04:30:35 UTC**, binding **18,460 stdout bytes
and empty stderr** to the native logs. Six captured physical metadata bodies
verify build/file-name tag **`nezha.a7db36604f45fcc657373f89`**, epoch
**1788144555**, `nezha-builder` and the expected `BP4A.251205.006`
fingerprint/thumbprint ending in `test-keys`. Neither matching values nor this
readback proves fresh metadata rewrites or Ninja producer actions.

The read-only four-log/full-stream collector exits 0 at **04:29:28 UTC**.
Output `.ninja_deps` is now **171,758,884 bytes**, up **62,488** from the prior
measurement; `.ninja_log` is **63,144,717 bytes**. The exact newly measured
dependency-log exception and shared-graph capture/qualification remain pending;
these measurements do not grant full-build or component admission.

Next are qualified shared capture and fresh selected-nine2, Images4 and Package4
evidence. The historical Package3 failure, enforcing normal Android, 4 KiB,
`working76`, kernel warnings and `test-keys` remain unchanged. No phone operation
occurs and no complete or flashable ROM is established. Final
VINTF/AVB/partition, signing/rollback, OTA and boot/hardware gates remain open.
The [combined checkpoint](../research/workspace-integration.json) binds exact
query, closure, native, metadata, stream and collector receipts. Earlier entries
retain their original scopes and then-pending work.

## Checksum 0023 source installation — 2026-09-02

The **checksum 0023 source adoption and complete receipt review pass**. The
**root install command ran 03:23:44–03:33:54 UTC**, with exit 0 and verified
native exit 0. These are root-wrapper times, not separately measured native
start/end times.
The journal's **03:31:01 UTC `commit_verified`** event precedes final acceptance;
it is not the completion time. Complete readback exits 0 at **03:34:05 UTC**,
retaining the exact commit, installation, 15-event journal and staged receipt.
The frozen pure host verifier checks all six exchanges and agrees with the root
review; this replay makes no additional VM or phone call.

The installed source contains **548 files across fifteen projects**, with all
**1,179 pinned HEADs/origins** matching. The six exchanges carry **287 payload
files / 19,884,254 bytes**: ten existing source files change and three checksum
controls are added, with no removed source paths. Besides the additive Makefile
guard, the changes refresh metadata/runtime and device, mi_ext and recovery
provenance bindings. Source modes, retained originals and recorded image
observations are preserved. No image or public key is exchanged or rebuilt.

The new metadata runtime verifies the **205 original metadata payloads** and
selected product source, rehashing the selected vendor/ODM images. It does not
run the packaged seven-CIL/three-sidecar gate or admit target-files. The existing
**254-field generated configuration observed during installation remains the
prior `b51a6b56…` snapshot**.

The subsequent **host identity calculation over verified actual installed
records passes**, yielding build **`nezha.a7db36604f45fcc657373f89`** and identity
`a7db36604f45fcc657373f892797c28c4a21dd5bfa988eef41d412679fc91ea8`, with pinned
epoch **1788144555**. Independent replay reproduces all **eight output files**,
including the five descriptor roles, and verifies the exact ten-replacement /
three-addition source delta. Untouched descriptor rows and modes are preserved.
This host calculation does not reobserve live source/private inputs, perform a
native query or establish native `a7db` configuration, physical metadata, Ninja
producer results or a successful ZIP.

Next are config11/context11 and Nothing8 under the host-projected identity, followed
by fresh selected-nine2, Images4 and Package4 evidence. The historical Package3
checksum failure and earlier component/image results remain intact. Normal
Android enforcement, 4 KiB, `working76` **`a130ba75…`**, kernel warnings,
`test-keys` and false complete-ROM readiness are unchanged. Final
VINTF/AVB/partition, signing/rollback, OTA and boot/hardware gates remain open;
the ROM is **not flashable**. The
[source-adoption record](../research/workspace-integration.json) binds exact
source, root completion, readback, pure-review and host-projection identities.

## Earlier checkpoints

These dated records retain their original results and then-pending work.

**Package3 fails in the metadata-verifier checksum guard**, during the ordinary
target-files-directory recipe. Native execution runs from
**2026-09-02 01:54:42 to 02:09:50 UTC**, ending with exit 1; the actual host
launcher closes with exit 1 at **02:14:06 UTC**. Action **13,468/13,582**, producing
`lineage_nezha-target_files.zip.list`, reports
`sha256sum: Unknown option 'strict'`. The final parallel progress line is
13,475/13,582. Subsequent Metalava warnings belong to parallel work, not the
failed checksum action. The artifact postcheck is null and no current Package3
ZIP success is inferred.

Complete readback finishes at **02:16:27 UTC**, retaining all **three files /
12,917,575 bytes**: the native result, 1,982,156-byte stdout and empty stderr.
The native result equals the host result byte-for-byte; two complete hash/stat
passes agree. All six ordinary source/input guard maps are equal before/after,
as are both GMS and selected-app prerequisite summaries and all 254 configuration
fields. Runtime observations change with build activity and logs. The source
remains 545 files/fifteen projects, with build identity
**`nezha.b51a6b5609d2001e9ae1f7ae`**. Preflight, Ninja argv, resource limits and
sandbox checks pass, with no timeout, disk-floor or stream-overflow fault.

The read-only compatibility probe pins the actual build-selected Toybox binary
and verifies **14 expected outcomes**. The unsupported flag reproduces exit 1;
canonical lowercase 64-hex validation plus `sha256sum -c` accepts correct input
and fails closed for wrong bytes, malformed digests, missing files and tool
failure. The first probe fails its provenance lookup at `paths.go`; the corrected
probe reads `path.go`, preserving the failed attempt. Neither probe executes an
Android build or changes source/output files.

The exact rendered 0023 guard also passes **15 expected-outcome smoke cases**
under actual Bash and the pinned Toybox binary. Only the matching digest reaches
a test-only sentinel; malformed, injected, missing-file and command-failure
cases exit 1. No Make/Kati, metadata installer or build executes. A subsequent
read-only four-log collector passes at **02:21:39 UTC**, measuring output
`.ninja_deps` at **171,696,396 bytes** and `.ninja_log` at **63,144,601 bytes**.
Future captures must remeasure and rebind these files, not reuse the older
170,213,408-byte dependency-log pin.

Additive [patch 0023](../patches/evolution/0023-portable-target-files-metadata-checksum.patch)
is prepared without rewriting patch 0009 or its history. It is **not adopted in
the VM**, and no successful native retry is claimed. The current metadata bundle
also verifies the full Makefile identity (`bf6e0668…`); its runtime and source
composition require refreshed reviewed inputs. Source adoption, fresh
source/configuration/metadata receipts and a new packaging attempt remain next.
Images3 and the selected-app build retain their earlier verified scope;
the signed boot chain, final VINTF/AVB/partition checks and hardware tests remain
open. Normal Android enforcement, 4 KiB, working76 and false complete-ROM
readiness are unchanged. The [failure record](../research/workspace-integration.json)
and [metadata guide](target-files-metadata.md) retain exact evidence and limits.

The **Images3 native build, postcheck and retained-evidence replay pass** on the
545-file/fifteen-project source. Its exact `--make-mode -j8` invocation builds
`recoveryimage`, `mi_extimage`, `vendorimage`, `odmimage` and the three
`*_sepolicy_and_mapping.sha256` goals from **2026-09-02 01:12:09 to 01:13:56 UTC**,
with native exit 0. The actual host process completes with exit 0 at
**01:17:50 UTC**, independently of the guest transport receipt.

All **seven installed-output producers** have verified fresh Ninja rows and
verbose evidence; recovery has both required recipe executions and one fresh
installed-image row. The four image output hashes equal their selected source
hashes, including working76 recovery **`a130ba75…`**. The three framework SHA
sidecars are recomputed, with seven compiler-output/installed-policy pairs
verified against the selected ODM basis. These checks verify delivery of the
pinned prebuilt images, not newly compiled recovery or vendor runtimes.

Before rebuilding, the preservation transaction moves **four prior installed
images and three sidecars** into retained locations, preserving all original
inodes and three independent sidecar copies. The result explicitly and
intentionally records **`output_invalidated_or_deleted=true`**. The two known
vendor/ODM historical-archive absences remain recorded; all four active images
were present before preservation. No source change or phone operation occurs.

All six ordinary source/input guard maps equal Nothing7 before and after; all
254 configuration entries match admission. The 545 source rows and modes,
fifteen projects, 1,179 pinned revisions/origins and nine reviewed locally
patched projects remain unchanged. Six metadata bodies match
**`nezha.b51a6b5609d2001e9ae1f7ae`**, epoch **1788144555**, hostname and the exact
`BP4A.251205.006` fingerprint/thumbprint with `test-keys`. Native process,
Ninja argv, sandbox and resource-limit checks pass; retained stdout is 3,013
bytes and native stderr is empty.

Independent host replay verifies all **56 retained files / 138,925,847 bytes**.
The action/policy replay passes at **01:28:58 UTC**; the complete replay also
verifies seven fresh actions, seven compiler/installed policy pairs, three
recomputed sidecars and twelve current/preserved metadata files. It checks
twelve image-journal events, seventeen sidecar-journal events, nine independent
sidecar inode identities and all nine staged proofs. Original validators match,
complete native streams are retained, and preservation precedes the native build.
No native path stubs or new VM calls supply the host replay. Large image and
graph bodies are not read back to the host; their source/output hash equality
remains the completed native postcheck's evidence.

Package3 and its final VINTF/AVB/partition and signed boot-chain checks remain
separate, as do hardware validation and physical Evolution boot. Normal Android enforcement,
4 KiB, working76, selected-kernel warnings and false complete-ROM readiness are
unchanged. The [Images3 record](../research/workspace-integration.json) binds the
actual request/result, host completion, preservation and full replay evidence.
Earlier checkpoints below keep their original scope and failures.

The **selected-nine native build and full retained-evidence replay pass**, with
native execution at **2026-09-02 00:16:36–00:18:20 UTC**, exit 0, and actual host
completion at **00:27:52 UTC**, exit 0. The complete result and action receipt
agree on **26 fresh outputs, zero reused**: nine built APKs, nine installed APKs
and eight strict statuses. Each is absent before/present after. BCR uses its
normal strict route; seven corrected Clocks use explicitly qualified status
goals. Flex has fresh APK outputs and verified prior-check equivalence, without
new or reused status production. The earlier two-pass/seven-mismatch audit
retains its failed overall result.

The **36 successful native verification commands** comprise signature
and manifest checks on nine source APKs and nine installed APKs; they do not
verify intermediate APK signatures. BCR preserves its source signer, all eight
installed Clocks match the platform certificate, and nine manifest semantic
comparisons pass. Six captured metadata bodies match
**`nezha.b51a6b5609d2001e9ae1f7ae`**, epoch **1788144555**, hostname and the
expected `BP4A.251205.006` fingerprint/thumbprint ending in `test-keys`.

All **180 input pins** match admission and complete before/after guards. The
normalized six ordinary callbacks match Nothing7, preserving **545 files and
modes/fifteen projects**, **1,179 pinned HEADs/origins**, nine reviewed locally
patched projects and all **254 configuration fields**. Ninja argv, sandbox and
resource-limit checks pass without a process, timeout, disk-floor or stream
overflow fault. Recorded native stdout is 6,277 bytes; native stderr is empty.

The retained prelaunch Flex replay failure routed qualified large graphs through
a generic 1 GiB file bound. A narrow host adapter admits only exact qualified
graph path/hash/size rows within the graph bounds, retaining the generic limit,
original controls and full graph qualification. The original failure and
[repair evidence](../research/workspace-integration.json) remain recorded;
that failure makes no native call or source/output change.

All **201 retained files** are exported with exit 0. Independent host replays
finish at **00:44:13 UTC** and **00:45:22 UTC**, rehashing **186,601,892 bytes**
and producing identical output through the unchanged consumer. Its 198-file
proof closure includes the 191 action evidence files and required earlier/current
records; the export also retains the original native result and both build
streams. All 36 native attempts, 72 verifier streams and four final nine-field
stat seals pass replay. The observations are the captured component-end rows:
no fresh package-time VM observation, GMS prerequisite replay or Package3
execution is claimed. The full offline suite on
`d8591b7` passes **4,417 tests, zero skips, in 166.978 seconds**, before this
documentation delta. That suite is not Android build or hardware validation.

Images3, Package3 and final VINTF/AVB/partition and hardware checks remain open,
as do whole-ROM signing and boot validation. Selected-kernel warnings and
`test-keys` remain visible; normal Android enforcement, 4 KiB and working76 are
unchanged. No phone operation occurs and complete-ROM readiness remains false.
The [selected-nine record](../research/workspace-integration.json) binds exact
native, host, action, export and independent replay receipts. Earlier checkpoints
below keep their dated scope and failures.

The **completed shared capture qualifies the regenerated selected-app graph**,
without executing an app build or checker. Host session 70086 exits 0 at
**2026-09-01 23:58:47 UTC**, and complete replay review passes at
**2026-09-02 00:00:32 UTC**. All **83 queries** return exit 0 with untruncated,
authenticated streams: 14 GMS, five provider, six SignApk and 58 selected-prebuilt
queries. Six complete root callback identities match Nothing7 on the
545-file/fifteen-project source; before/after graph, log, native-result and
Ninja snapshots are equal. The 46,831-byte capture stderr retains its outer
observations and sandbox warnings; it is not described as empty query stderr.

At **00:01:42 UTC**, the separate raw readback exits 0 and verifies eight
nonempty Clock JSON bodies totaling **108,277 bytes**, each bound to its own
`g.android.rawFileCopy` declaration. The actual graph plans **26 outputs**:
18 built/installed APKs and eight fresh strict statuses. BCR uses its normal
status route, seven corrected Clocks require explicit detached goals, and Flex
requires genuine prior-read-only-check equivalence; its extra goal is rejected.
No planned output, copied configuration destination or new Flex equivalence is
proved by raw-payload readback.

The retained narrow control repairs set the `.ninja_deps` ceiling to its measured
**170,213,408 bytes** and allow a **65 MiB** combined JSON envelope for the
67,512,218-byte authenticated input. The envelope change leaves individual-file
bounds unchanged; both repairs retain original controls and query scope. The
initial host-only replay `KeyError: pins` is fixed by supplying the expected
wrapper without altering evidence or calling the VM.
The full offline suite on `c318579` passes **4,417 tests, zero skips**, before
this documentation checkpoint; it is not Android build validation.

Actual selected-app admission/build, eight fresh strict statuses and 36 native
signature/manifest invocations remain unverified. Images3, Package3, final
VINTF/AVB/partition checks and device tests are later gates. Neither read-only
operation changes source or Android output or accesses the phone. Normal
Android enforcement, 4 KiB, working76 and false complete-ROM readiness remain.
The [shared-capture record](../research/workspace-integration.json) retains exact
completion, replay, raw-payload and limit-repair receipts. Earlier checkpoints
below retain their original scope and failures.

The **ordinary `nothing7` graph/metadata checkpoint passes** on the
545-file/fifteen-project source. The exact
`build/soong/soong_ui.bash --make-mode -j8 nothing` command runs from
**2026-09-01 23:21:16 UTC to 23:24:12 UTC**, exiting native 0. The host launcher's
actual process completion is separately observed with exit 0; this is not
inferred from the guest transport receipt. Full retained-stream review finishes
at **23:30:31 UTC**, authenticating 2,049 stdout bytes and empty native stderr.
The stdout records Blueprint analysis, packaging-rule regeneration and the
`nothing` goal, while retaining the selected-kernel and sandbox warnings.

Six physical metadata-file bodies match build number
**`nezha.b51a6b5609d2001e9ae1f7ae`**, epoch **1788144555**, hostname
`nezha-builder` and the exact `BP4A.251205.006` fingerprint/thumbprint with
`test-keys`. All six source/input callback maps match before/after and both
predecessor queries; all 254 configuration entries match admission, and all
1,179 pinned revisions/origins match. Nine intentional locally patched projects
remain preserved. Ninja is observed with resource-limit and sandbox checks
passing; descendant argv and fresh individual producer actions are not claimed.

Native preflight measures **344,036,077,568 free bytes**, **17 available CPUs**
and **132,980,674,560 available memory bytes** on the same aarch64, case-sensitive
ext4 source/output filesystem. This is a dated capacity observation, not a
reservation. Four separate read-only collectors close with exit 0 at
**23:29:54 UTC**, retaining the full native streams, four Ninja-log measurements
and selected GMS/product/BCR dependency configurations or exact absences. They
do not admit an app build or establish that the whole output tree is unchanged.

Graph completion and matching metadata values do not prove fresh metadata
rewrites, corrected Clock status production or successful APK signatures.
Qualification of the regenerated Clock rules, strict module checks and fresh
ordinary producer/signature evidence remains next; Images3, Package3, the signed
boot chain and hardware checks remain separate. Normal Android enforcement,
4 KiB, working76 and false complete-ROM readiness are unchanged. The
[Nothing7 record](../research/workspace-integration.json) binds the source,
host-completion, metadata, full-stream review and four collector receipts.
Earlier checkpoints below retain their original scope and failures.

The **545-file/fifteen-project source passes config10 and context10**. The
ordinary native dumpvars queries run at **2026-09-01 22:59:23–23:00:17 UTC**
and **23:07:58–23:08:51 UTC**, both with exit 0. Their wrappers close with exit
0 at **23:03:16 UTC** and **23:11:57 UTC**. Host review decodes and binds both
complete streams to their native log identities, accepting 21 configuration
assignments and seven context assignments. It finds no unexpected diagnostics.

All six source/input guard maps match before and after each query and across
both queries. All 254 configuration entries match actual admission and one
another; all 1,179 pinned project revisions and origins match, preserving nine
reviewed locally patched projects. The native environment uses build number
**`nezha.b51a6b5609d2001e9ae1f7ae`** and epoch **1788144555**. Context10 reports
Xiaomi, Android 16, **`BP4A.251205.006`**, the testkey certificate path and
`test-keys`; this is not OEM signing trust. Each query retains the two exact
kernel warnings: input AVB verification failed, origin is unverified, and
kernel/module compatibility and device boot remain unverified.

The first context10 dispatcher fails with `KeyError: actual_source_review`
before a launch receipt, native directory or VM command. A separate recorded
host lookup correction reads the already authenticated review field; it does
not change the native caller, request or build settings. The corrected dispatch
produces the passing result above. Full host review finishes at **23:13:48 UTC**;
a supplemental review rechecks all 75 dispatcher-held input hashes and stat
identities and the cross-query guards.

These are native configuration results, not ordinary graph generation, physical
metadata-file verification or Ninja producer evidence. `nothing7`, regenerated
Clock checker rules, corrected strict status/module checks, current signatures,
Images3 and Package3 remain pending. Normal Android enforcement, 4 KiB,
working76 and false ROM readiness are unchanged. The
[Clock guide](systemui-clocks-optional-window-libraries.md) and
[native query checkpoint](../research/workspace-integration.json) retain exact
receipts. Earlier checkpoints and failures below keep their original scope.

The **Clock 0022 source adoption passes**, with native installation from
**2026-09-01 22:39:41 UTC to 22:47:17 UTC** and native/root exit 0. One exchange
produces five chronological journal events without rollback; `commit_verified`
at **22:44:52 UTC** precedes final acceptance. Complete readback finishes at
**22:47:23 UTC**. Host review of those actual records verifies the eight source
controls, exact staged replacement, retained originals and source/project delta.

The inventory is **545 files/fifteen projects**, preserving all 544 ancestral
rows and modes. The Clock Blueprint retains mode `0755`, CRLF and all original
bytes while adding the seven arrays; Flex stays unchanged. Native installation
guards preserve thirteen APKs, the existing BCR change, current configuration
and strict settings. Recorded image observations remain unchanged; this does
not supply a new image build or image admission.

The host identity projection finishes at **22:50:30 UTC**, producing
`b51a6b5609d2001e9ae1f7aeb22efbe1a124da299171ca53aae9b314840aad38`
and build number **`nezha.b51a6b5609d2001e9ae1f7ae`**, still using epoch
**1788144555**. It derives the successor from the actual installed union,
without verifying native configuration, metadata or binary outputs. config10,
context10, `nothing7`, corrected strict checks and fresh ordinary producer/signature
evidence remain pending before the current image/package sequence. The
[Clock guide](systemui-clocks-optional-window-libraries.md) and
[adoption checkpoint](../research/workspace-integration.json) retain exact
receipts. The 4 KiB baseline, normal Android enforcement, working76 and false
ROM readiness remain unchanged; earlier failed audits and builds keep their
original results below.

The **standalone nine-APK uses-library audit fails with two passes and seven
manifest mismatches**. Its root transport runs from **2026-09-01 21:42:55 UTC
to 21:49:21 UTC**, ending with exit 1. BCR and SystemUIClocks-Flex pass; the
seven other selected Clock imports fail because their manifests declare
optional `androidx.window.extensions` then `androidx.window.sidecar`, while
their build lists are empty. Flex's empty lists already match and must remain
unchanged.

All nine badging commands pass. Complete before/after guards cover all nine
source APKs, totaling **23,937,581 bytes**, with 54 input snapshots unchanged
and all six current root callback return maps matching Nothing6. No selected
APK is skipped, waived, omitted or unresolved. Completed failure review verifies
these results; there is no resource or transport failure. Source, APKs and OUT
are unchanged by this read-only audit. It produces no ordinary status stamp,
verifies no APK signature and does not constitute an ordinary BCR build.

The reviewed [0022 source patch](systemui-clocks-optional-window-libraries.md)
adds ordered optional-library arrays to exactly seven imports. Flex, all APKs,
signing choices, placement and existing dexpreopt settings remain unchanged.
Ten offline unit tests pass. Thirteen host synthetic-checker cases produce
eight expected passes and five expected failures, with zero skips; complete
source replay and twelve negative patch guards also pass. These host results
do not repair the failed native audit by themselves. Guarded source adoption,
regenerated rules and fresh ordinary producer evidence are still required;
an approved targeted build or packaging may supply that evidence.

The active source is still **544 files/fifteen projects with identity `f9`**;
no successor source inventory is adopted. The 4 KiB baseline, enforcing normal
Android policy and working76 remain selected. Current images, packaging,
AVB/rollback, boot and hardware checks remain open, with ROM readiness false.
The [audit and patch-preparation checkpoint](../research/workspace-integration.json)
retains exact receipts. Earlier checkpoints below preserve their results.

The **544-file/fifteen-project source passes config9, context9 and ordinary
`nothing6`**. The two queries finish with native exit 0 at
**2026-09-01 19:47:09 UTC** and **19:58:23 UTC**. The exact
`build/soong/soong_ui.bash --make-mode -j8 nothing` invocation runs from
**20:12:04 UTC to 20:23:46 UTC**, with native exit 0; its wrapper closes with
exit 0 at **20:26:41 UTC**. All three postchecks pass. Six complete source/input
guard maps remain equal before and after; all 254 configuration entries match
admission and both queries. All 1,179 pinned project HEADs and origins match.

Six physical metadata-file bodies verify build number
**`nezha.f9f678051a7b3de57c741ca2`**, build epoch **1788144555**, hostname,
fingerprint and thumbprint. Full readback verifies the 17,534-byte native stdout;
the native stderr is empty. Four separate read-only captures at **20:27:40 UTC**
retain log measurements and selected dependency configurations/absences, with
their final wrapper closing at **20:27:41 UTC**. Review binds these receipts to
the completed Nothing6 result. Matching metadata values do not establish fresh
rewrites or full binary provenance. The follow-up captures are read-only; the
build can write to OUT.

BCR's fresh strict status action, module/class-loader and APK-signature checks,
the combined non-GMS audit, Images3 and Package3 remain unverified. This graph
and metadata milestone supplies no signed AVB-chain, runtime, boot or hardware
success. The 4 KiB baseline, normal Android enforcement and working76 remain
selected, with complete-ROM readiness false. [BCR source integration](bcr-optional-window-libraries.md)
and the [native metadata checkpoint](../research/workspace-integration.json)
retain the evidence. Earlier dated checkpoints below remain unchanged.

The **BCR 0021 source adoption passes**, with the native installation running
from **2026-09-01 19:25:36 UTC to 19:32:56 UTC** and both native/root exits 0.
One file exchange produces five chronological journal events, with no rollback;
the `commit_verified` event at **19:30:36 UTC** precedes final acceptance.
Complete receipt readback finishes at **19:34:55 UTC**, and independent review
verifies the exact staged replacement, retained originals and source/project
delta. All 31 frozen host controls remain unchanged during installation.

The declaration grows from 310 to 395 bytes while preserving CRLF, mode and
every original byte. Its ordered optional Window pair changes no APK, signing,
privilege, placement or enforcement setting. The inventory is now **544 files
across fifteen projects**, with all 543 ancestral rows and modes retained.
The `vendor/extras` revision remains `c401d732…`, with exactly one modified path.
Existing configuration, namespace, metadata, strictness and source contracts,
constructor history and image-input evidence remain unchanged.

The separate host projection completes at **19:36:03 UTC**, producing identity
`f9f678051a7b3de57c741ca215072e7bac189e87304da06b47bc061c227e0db1`
and build number **`nezha.f9f678051a7b3de57c741ca2`**. Native config9, ordinary
`nothing6`, fresh strict BCR status/module and class-loader checks, Images3 and
Package3 are not verified by this adoption. The combined non-GMS audit remains
required before Package3. [BCR source integration](bcr-optional-window-libraries.md)
and the [adoption record](../research/workspace-integration.json) retain exact
receipts. The 4 KiB baseline, normal Android enforcement and working76 remain
selected; no ROM or boot success follows. Earlier checkpoints below keep their
original results and source identities.

The ordinary **Package2 attempt fails at BCR's strict uses-library check**.
`build/soong/soong_ui.bash --make-mode -j8 target-files-package` runs from
**2026-09-01 18:05:41 UTC to 18:08:23 UTC**, exiting 1; the wrapper closes with
exit 1 at **18:12:04 UTC**. The manifest's optional libraries are, in order,
`androidx.window.extensions` and `androidx.window.sidecar`, while the build's
optional list is empty. Both required lists are empty. The mismatch is retained
without relaxing the checker or class-loader requirements.

Full readback verifies the result, 44,438-byte native stdout and empty native
stderr: **three files totaling 10,404,689 bytes**. All six source/input guard maps
and all 254 configuration entries remain equal on the **543-file/fourteen-project
source**, build number
**`nezha.3c24f46cf801e6abd6d5361c`**. Observed Ninja arguments, sandbox, limits,
reaping and complete streams pass; no timeout, overflow, forced kill or disk-floor
fault occurred. `profile_completed` is false and the artifact postcheck is null.
This capture does not establish ZIP presence or absence, requalify current output
contents, or verify new images or a boot. Successful proof staging and the prior
GMS2/Images2 results remain separate evidence. BCR source capture and correction
are pending; no successor source has been adopted. Exact receipts are in the
[Package2 failure record](../research/workspace-integration.json).

The **ordinary Images2 phase passes its native build and postcheck** on the
543-file/fourteen-project source, with build number
**`nezha.3c24f46cf801e6abd6d5361c`**. Native execution runs from
**2026-09-01 17:08:14 UTC to 17:10:06 UTC**; the wrapper completes at
**17:13:46 UTC**, both with exit 0. Its exact `-j8` invocation builds
`recoveryimage`, `mi_extimage`, `vendorimage`, `odmimage` and the three
`*_sepolicy_and_mapping.sha256` goals.

All seven installed-output producers have fresh Ninja and verbose evidence.
Recovery additionally records both required recipe executions and one fresh
installed-image row. The four prebuilt image outputs match their pinned inputs;
working76 remains `a130ba75…`. Three freshly installed policy SHA sidecars are
recomputed against the selected ODM basis, and seven compiler-output and
installed-policy pairs match. This verifies delivery of those selected inputs,
without claiming newly compiled recovery or vendor runtimes.

Before execution, the reviewed preservation step moved four prior installed
images and three sidecars into retained locations and preserved their originals.
The result explicitly records **`output_invalidated_or_deleted=true`**.
All six complete source/input guard maps and all 254 configuration entries
remain equal; the 4 KiB profile, enforcing
normal Android policy and source identity are unchanged. CAP7, the four-record
recovery rule proof, nine staged proof records and the 68-input caller freeze
have separate admission records. A fresh read-only four-log measurement completes
at **17:16:00 UTC**, without itself admitting a package build.

Readback of all **56 planned evidence files, totaling 138,621,501 bytes**, passes.
A host decoder correction preserves each descriptive `name` field against the
original saved native records; no native capture is repeated. Independent replay
also verifies the seven fresh actions, full policy bodies and ordered sidecar
hashes, retention journals and twelve current/preserved metadata files. Large
image and graph bodies are outside this readback; the native postcheck supplies
the source/output image hash checks.
Package2 and its final VINTF/AIDL, image, AVB/rollback and partition checks remain
unverified, as do runtime behavior and a physical Evolution boot. The
[Images2 checkpoint](../research/workspace-integration.json) records exact
inputs, action counts, hashes and scope. The following paragraphs preserve
earlier checkpoints, including their then-pending work and original failures.

The **GMS2 native build and postcheck pass**, with native/root exit 0 on the
543-file/fourteen-project `3c24` source. Native execution finishes at
**2026-09-01 16:06:05 UTC**. Its proof records three fresh SignApk actions plus
CrossDevice's fresh build/install pair, with ten ordinary actions reused.
The four strict uses-library statuses are verified reuse, with zero fresh
status actions. All six input guard maps and the 254 configuration entries
remain equal; no source inputs or output trees are invalidated. Complete
readback of 94 retained files and independent replay pass. Eight strict
signature checks and eight manifest-badging commands all exited 0; host replay
does not establish a fresh observation of the physical APKs or JARs.

The preceding 25-query capture, host admission and both native input stages
have separate successful records. The original `73e92126…` capture and GMS1
overall failure stay intact. Images2, package2 and ROM readiness remain
unverified. See [GMS source integration](gms-source-integration.md).

The preceding boot-runtime documentation checkpoint was committed as
**901a925** after the coordinator's full suite passed **4,317 tests in 190.748
seconds with zero skips** at **15:34:14 UTC**. The four bound files stayed
unchanged and match that commit. This later capture/admission/component
documentation milestone is outside that run.

The **543-file source passes config8/context8 and ordinary `nothing5`** through
**2026-09-01 14:33:17 UTC**, with native/root exit 0 and successful postchecks.
All six input guard maps and 254 configuration entries remain equal before and
after each phase. The six metadata-file values match
**`nezha.3c24f46cf801e6abd6d5361c`**; the retained stdout shows 165 frontend steps
and one `nothing` action. The **14:37:58 UTC** read-only captures retain four log
measurements, two Window dependency-config bodies and four expected app-config
absences. New graph/action qualification, the corrected signer build and strict
GMS retry remain pending; the earlier CrossDevice failure is unchanged.
[GMS source integration](gms-source-integration.md) records the native evidence
and its limits. Images2, package2 and ROM readiness remain unverified.

The preceding source-adoption checkpoint was committed as **d53620c** after the
coordinator's full suite passed **4,317 tests in 209.206 seconds with zero
skips** at **14:00:08 UTC**. The six tested files stayed unchanged and match that
commit. This later native-metadata documentation milestone is outside that run;
the earlier checkpoints below retain their original scopes.

The corrected **0020 source installation passes at 2026-09-01 13:36:04 UTC**,
following successful staging at **13:22:20 UTC**. Both edits commit through
seven journal events without rollback; complete readback and independent
review pass. The source now contains **543 files across fourteen projects**.
Host projection calculates **`nezha.3c24f46cf801e6abd6d5361c`**, preserving the
prior identity as history. config8/context8 and generated metadata values have
not yet been verified for it. No SignApk, APK, image or package build has run
from this source. The next checks remain the native queries, regenerated rules
and strict component retry described in [GMS source integration](gms-source-integration.md).

The preceding rollback checkpoint was committed as **266e0e0** after the
coordinator's full suite passed **4,317 tests in 184.527 seconds with zero
skips** at **13:15:54 UTC**. All six bound files stayed unchanged. That run
does not cover this later source-adoption documentation milestone; the native
transaction is separate evidence. The earlier checkpoints below remain intact.

The first **0020 SignApk source stage passes at 2026-09-01 12:50:15 UTC**, but
installation fails at **12:56:39 UTC** and both source exchanges roll back with
verification. A retained history guard expected the old `build/make` status
after the intended edits. Fresh readback preserves fifteen input observations
and fourteen project contexts; only the two exchanged files' ctimes change.
The active 541-file source and `a2d9` identity remain unchanged. Correcting that
guard, adopting the source and rebuilding the signer remain required before
a strict component retry; no new component, image or package build occurred.

Separate read-only APK diagnostics finish at **12:26:06 UTC**: all sixteen
commands return, fifteen exit 0 and installed CrossDevice exits 1 with the
unchanged SourceStamp warning. Aggregate verification remains failed. A later
host parser correction passes 97 author tests and 97 independent repeat tests,
with zero skips, and accepts seven saved signature outputs and four saved
manifest pairs. This is not new native success. See
[GMS source integration](gms-source-integration.md) for both checkpoints.

The preceding failed-component/SignApk preparation checkpoint was committed as
**bb93933** after the coordinator's full suite passed **4,317 tests in 183.429
seconds with zero skips** at **12:22:44 UTC**. The ten bound files stayed unchanged
during that run. These later diagnostic, rollback and documentation changes are
outside its scope.

The targeted **four-module GMS attempt remains failed overall**. Native Soong
finishes with exit 0 at **2026-09-01 11:45:18 UTC**; its stdout records four strict
uses-library checks, four APK builds and four installs. The wrapper exits 1 at
**11:50:26 UTC** when installed CrossDevice verification emits
`WARNING: No SourceStamp signature` under `-Werr`. Complete artifact and action
qualification does not finish. The original source APKs, 541-file/fourteen-project
source, `a2d9` identity and all six source/input guard maps remain unchanged.
The SignApk source correction and a fully verified retry precede Images2 and
package2; [GMS source integration](gms-source-integration.md) records the scope.

The preceding capture/staging checkpoint was committed as **e8b2eff** after
the coordinator's full suite passed **4,305 tests in 178.190 seconds with zero
skips** at **11:51:27 UTC**. That run covers the six frozen capture/staging files,
not this failed-component documentation update or the new signing correction.

A separate read-only **Mac boot-tool runtime check passes at 11:49:34 UTC**,
rehashing all 193 declared file-backed runtime dependencies. It runs no image
commands and establishes neither complete dynamic runtime closure nor package,
image or boot compatibility. This is preparation for later artifact inspection.

The **2026-09-01 11:11:47 UTC corrected GMS read-only capture** passes with
native/root exit 0, nineteen complete query streams and unchanged guarded
source, graph and log observations. Six proof records are staged at
**11:21:37 UTC**, without source or Android-output changes. Host qualification
then covers the four modules' twelve own actions; their targeted build,
Images2 and package2 are pending at that checkpoint. The original capture and
earlier host admission failures remain retained. See [GMS source integration](gms-source-integration.md)
for the source-defined HTTP provider, precompilation and package-list scope.

The preceding metadata checkpoint was committed as **2d138b8** after the
coordinator's full suite passed **4,305 tests in 194.988 seconds with zero skips**
at **10:07:15 UTC**. That run covers the six frozen metadata-checkpoint files,
not this later capture/staging documentation change.

The **2026-09-01 09:46:14 UTC `nothing4` checkpoint** passes with native and
root exit 0 on the current 541-file/fourteen-project source and `a2d9` identity.
The preceding config7/context7 queries also pass, checking 21 and seven values
respectively. All three runs preserve the six complete source/input guard maps
and the 254-field configuration. `nothing4` verifies all six actual metadata-file
values; matching values do not prove fresh rewrites.

The full retained stdout shows **165 frontend steps and one `nothing` action**.
The exact frontend command is `build/soong/soong_ui.bash --make-mode -j8 nothing`.
Ninja is observed with passing limit and sandbox checks, while descendant argv
and component actions remain unqualified. All 1,179 source-lock HEADs and origins
match; the eight expected locally patched projects match their installed guards.
The post-run read-only measurement captures the complete stdout and log
identities; the later graph capture above is separate evidence. Four GMS module
builds, Images2 and package2 are pending at that checkpoint, with no Camera or
hardware success implied.
See [GMS source integration](gms-source-integration.md) for exact phase evidence.

The earlier six-file adoption checkpoint was committed as **8857312** after
the coordinator's full suite passed **4,305 tests in 182.264 seconds with zero
skips**. That run verified the frozen adoption documents, not this later
query/`nothing4` documentation milestone.

The adoption paragraphs below retain their earlier query-dispatch checkpoint;
the completed native query and metadata results above supersede that status.

The **2026-09-01 09:08:48 UTC four-file GMS source-adoption checkpoint** passes
with native and root exit 0. Staging finishes at 09:00:35 UTC; installation
records four exchanges and eleven journal events, with `commit_verified` at
09:06:54 UTC before final acceptance completes. Full stage/install readback
preserves the original Makefiles and eight image observations: six present
files and two exact archive absences. No image or module build occurred.
Independent stage/install reviews and separate host identity review pass.

The active source is now **541 files across fourteen projects**. Its host-derived
build number is **`nezha.a2d9ab6affbe09593d338212`**, while native configuration,
metadata values and generated rules remain unverified for that identity.
config7 dispatch is recorded at 09:13:54 UTC, without a completed result;
context7 and `nothing4` (ordinary `-j8 nothing`) remain pending.
The caller change preserves source/input guards and changes no installed source.
Ordinary GMS status actions, module/class-loader-context checks and target-files
remain separate. See [GMS source integration](gms-source-integration.md).

The seven omitted product-selected declarations are now classified from saved
evidence: three ETC gzip payloads, two JARs and the Bugle/Velvet APKs with
pre-existing strict-check waivers. None becomes a manifest pass. The planned
waiver-manifest capture has not run; no waiver is removed or relaxed here.

The previous seven-file audit/0019 checkpoint was committed as **6253533** after
the coordinator's full suite completed at **08:51:45 UTC**: **4,305 tests in
182.294 seconds, with zero failures, errors or skips**, and frozen files unchanged.
That earlier run excludes native adoption and this documentation milestone.

The proposal, audit and package paragraphs below preserve their earlier source
and validation scopes; they do not describe the now-installed four-file source.

The **2026-09-01 08:45:34 UTC corrected native proposal probe** passes all four
checks against the original APKs and dependency configurations, with native and
root exit 0, zero errors, unchanged guarded inputs and read-only source/output.
The 7.190-second run applies proposed optional-library lists only: it does not
install the four Makefiles, regenerate their commands or produce ordinary build
stamps. The other 91 original commands are not rerun, and the original audit
below remains 91 passes/four mismatches. This is separate from source adoption,
actual module integration, dexpreopt and package completion.

The **2026-09-01 08:31:40 UTC strict GMS audit** completes all 95 selected
original APK checks with **91 passes, four manifest mismatches and zero command
errors**. Native audit and root wrapper exit 1. The 101 native commands return;
all 216 guarded inputs remain unchanged, including 95 APKs totaling
2,017,701,815 bytes. Only the ordinary status-output argument is removed from
the captured checker commands to keep source and build output read-only.
Enforcement and dependency inputs remain intact. Seven omitted declarations
are not audited or passed; no ordinary status stamps or package success follow
from this audit. Independent review verifies the recorded audit within that scope.

The unchanged [0018 preparation](gms-customization-optional-library.md) and
new [0019 preparation](gms-prebuilt-optional-libraries.md) cover the four failing
Make declarations. Paired host replay and synthetic checker fixtures pass.
CrossDevice removes only its stale direct HTTP declaration: the product still
selects `org.apache.http.legacy`, and automatic SDK-28 compatibility stays intact.
Persistent adds optional `com.google.input.gia.giaservicemanager`; SafetyHub
prepends optional `wear-sdk` while retaining HTTP and both window libraries.
The one-file proposal was never installed. Four-file source-v2 adoption,
graph regeneration and fresh ordinary status actions remain pending; the
separate proposal probe above does not establish them. The active 537-file/
thirteen-project source, `8643` identity, 4 KiB baseline, normal Android
enforcement and working76 are unchanged.

The preceding seven-file package-failure/0018 checkpoint was committed as
**9a2135c** after the coordinator's full suite completed at **08:29:32 UTC**:
**4,305 tests in 182.279 seconds, with zero failures, errors or skips**, and all
seven tested files unchanged. That run excludes the later 95-module audit,
corrected proposal probe, 0019 preparation and this documentation update. Exact
receipts and the separate audit are in the
[checkpoint record](../research/workspace-integration.json).

The package1 and materializer paragraphs below preserve the earlier checkpoint;
the audit and recorded offline run above supersede their then-current status.

The **2026-09-01 08:03:01 UTC package1 checkpoint** records the first ordinary
`target-files-package` attempt failing with native and wrapper exit 1, after
native execution began at 06:11:54 UTC. Its only retained `FAILED:` entry is at
line 58,282 of 58,306, at 68% progress: `CustomizationBundlePrebuiltFullVersion`
omits the unchanged APK's optional `wear-sdk` from its Make declaration. Resource
checks, process cleanup and all six source/input guard groups pass, but the
package profile remains false and the artifact postcheck is null. No verified
target-files ZIP is established.

Complete result/stdout readback and all three action logs are retained. The
action logs total **124,472,273 bytes**; streamed decompression verifies the
verbose log's **361,487,676-byte** expanded identity without retaining another
uncompressed copy. The original failed result and earlier host review remain
unchanged, now paired with the complete native readback in the
[checkpoint record](../research/workspace-integration.json).

The [one-line GMS correction](gms-customization-optional-library.md) is prepared
and passes host replay and strict checker fixtures. Native source adoption,
graph regeneration and a fresh successful status action remain pending.
Read-only capture includes 95 actual GMS status-leaf commands and native badging
for the failing APK; the broader strict audit has not run. The selected 537-file/
thirteen-project source, `8643` identity and 4 KiB/enforcement/recovery settings
are unchanged. Full VINTF remains a separate final-package check: explicit final
SKU/vendor-API selection and current package inputs are required. Historical
220-source compatibility evidence does not qualify the final package.

Commit **0f09135** adds the tested
[target-files input materializer](target-files-materialization.md). Its 44
synthetic tests do not establish actual materialization. The persisted receipt
only verifies the checkpoint before publication; successful return is required,
and subsequent signing preparation supplies a distinct normalized-manifest
digest. The last full suite before this documentation update passes **4,305
tests in 202.826 seconds with zero skips**. The preceding four-document checkpoint
passes 4,261 tests in 179.563 seconds. No actual materializer publication or signing
is claimed.

The **2026-09-01 05:34:01 UTC AIDL component build** passes with native and
wrapper exit 0. The log has 341 main Ninja actions plus one bootstrap step.
Among 70 selected outputs, 38 have fresh action evidence and 32 display-config
checks are reused. The host auditor and seven NDK backends compile; auditor
execution, full definition coverage and runtime remain unverified. Independent
review of the captured action evidence passes. Source inputs and current recovery/mi_ext are
preserved; this callback does not verify current vendor/ODM output preservation.

The **2026-09-01 04:26:42 UTC images1 attempt** finishes with native exit 0
and wrapper exit 1. The sole validation failure is the combined Ninja graph's
pool-depth change from 15 to 8, explained by the pinned generator and observed
`-j8`. The old graph body is reconstructed to its sealed hash, not independently
captured; all six admission maps, 254 configuration fields and fifteen other
graphs match. The failed receipt remains unchanged. The **separate read-only
postcheck passes at 05:03:29 UTC**, checking four output images, three sidecars
and all seven producers' fresh action evidence without another build or output
write. Saved-receipt readback and independent artifact review pass, including
the sidecar-to-ODM join through prior delivery and raw-image/footer evidence.
There is no new host image extraction or read-only mount-namespace claim.
Target-files, signing and boot remain unverified.

The **2026-09-01 03:22:47 UTC ordinary `nothing3` checkpoint** passes graph
regeneration, all six source/input guard groups and the six metadata-file value
checks for `nezha.8643b579050aab0dd3218ae3`. The only change in the 254-field
configuration is the approved namespace-export list, from eight to ten entries.
Its 166 frontend steps plus one `nothing` phony are not component/image builds
or tests. Ninja and its sandbox are observed, but exact Ninja arguments are not
qualified by this profile; matching metadata values do not prove fresh rewrites.
The subsequent read-only producer capture, exact recovery-declaration review
and nine-proof staging are complete; those preparation steps execute no image
recipe. The later four-image/three-sidecar invocation is recorded above. The
first optional AIDL capture fails its bounded query; v2 completes read-only
capture of 1,163 nodes and 62 API-check descriptions without compiling or running
the component checks. Independent review verifies this scoped capture, not full
dependency closure. Kernel AVB/origin, signing, super/OTA and hardware gates remain. See
[current status](workspace-status.md) and the
[ordinary run and preparation evidence](../research/workspace-integration.json).

Commit **1ef9bf3** adds the maintained
[signed target-files reconciler](signed-target-files-reconciliation.md) and
streaming archive copier. Its 72 added tests use synthetic archives and mocked
cryptography; its full workspace suite passes 4,261 tests in 192.570 seconds,
with zero skips. The later preparation-document checkpoint passes 4,261 tests
in 204.808 seconds with zero skips. The earlier suite before the
artifact-review/component-build update passes 4,261 tests in 193.210 seconds,
with zero skips, against the four unchanged documents committed as `d072d06`.
No actual signing or target-files reconciliation has run.

The **2026-09-01 03:01:01 UTC product-query checkpoint** verifies the adopted
537-source/thirteen-project configuration with identity
`nezha.8643b579050aab0dd3218ae3`: config6 passes 21 values and context6 passes
seven, with all six source/input guards and the full 254-field generated
configuration unchanged. Reprojection binds the declared metadata-copy modes;
it does not chmod the source. These are ordinary product queries, with no
observed Ninja action or image build. Literal `FROM_FILE` references do not
qualify six metadata-file contents or freshness. The later `nothing3` result
above separately verifies their values; kernel AVB/origin warnings, packaging,
signed-chain and boot gates remain. See
[current status](workspace-status.md) and the
[query evidence](../research/workspace-integration.json).

The **2026-09-01 02:14:58 UTC maintenance checkpoint** clears the recorded
source-staging capacity blocker: the existing ext4 volume is now **1,024 GiB**,
with 402,047,229,952 bytes available against the unchanged 226,459,516,499-byte
budget. The same builder and then-current 539-source proof are verified after restart;
the retained 800 GiB APFS clone/swap state is not an independent physical backup.
This is environment maintenance, not a new Android build or source adoption.
See [current status](workspace-status.md), [environment details](apple-container.md)
and the [maintenance evidence](../research/workspace-integration.json). The
component and source checkpoints below retain their historical input scope.

The authored Nezha product has completed actual user and userdebug component
builds in the existing Apple Container source checkout. Built and inspected
outputs include boot, init_boot, vendor_boot, DTBO and both DLKM images across
their recorded input snapshots. ARM64 `libbase.so`, the nine selected Camera
dependency modules and the host VINTF/policy tools also built successfully.
The Camera APK itself is not included, and a complete ROM has not been built.
The earlier [OEM policy integration](oem-policy-integration.md) restores the
three missing service/file classifications through authored system_ext source,
Android-generated object roles and API mappings. The **v11b** native phase
passed at **2026-08-29 20:47:06 UTC**, completing 31 Ninja actions, including
the ownership guard, strict combined-policy compiler and all nine factory
context/structural checks. Independent v11 analysis passed at **20:54:46 UTC**:
all 6,366 assertions remain with their reviewed concrete coverage, effective
permissions change by exactly five additions and 47 removals, and three actual
policy binaries have zero permissive domains. Complete Treble labeling and
image adoption remain outstanding. The [v10 native integration](policy-source-integration.md)
first applied the reviewed helper M4 and Binder corrections; its independent
analysis preserved all 6,366 assertion statements and found zero permissive
domains in three binaries. Its three then-failing checks are preserved in that
record. The
[v9 source build](dsp-policy-build.md), [Binder experiment](binder-policy-correction.md)
and [helper projection](helper-policy-projection.md) retain their historical
results; later work does not rewrite those earlier failures or copied-CIL
proofs. The [v11 result record](../research/oem-policy-integration.json) binds
the source installation, failed first guard, correction and successful retry.
The product
selects Nezha, canoe, ARM64, 4 KiB kernel pages, shipping API 36 and board API
202504, with AVB enabled. The [build record](../research/build-progress.json)
contains the exact inputs, receipts and subsequent compilation results.

This is a `framework-checks` product. It permits configuration and module
compilation while keeping complete target-files, OTA, super-image and flash
admission false. Unknown physical capacities and bootloader state do not
prevent local source generation or compilation. They remain requirements for
any eventual device experiment, which needs separate user authorization.

## Installed source and inputs

| Source path | Current input |
| --- | --- |
| `device/xiaomi/nezha` | Authored product plus generated boot, partition-budget and enforcing first-stage fstab configuration |
| `kernel/xiaomi/nezha` | Stock-prebuilt integration wrapper, not a fabricated source-kernel tree |
| `vendor/xiaomi/nezha-kernel` | 950 hash-verified files, including the exact Image, DTB/DTBO, 914 module instances and preserved ordered load/block lists |
| `vendor/xiaomi/nezha` | Factory vendor/ODM EROFS inputs plus the nine byte-identical selected Camera dependencies and their [recorded XML derivations](camera-inputs.md) |
| `vendor/xiaomi/nezha-policy` | Separate private original policy/context corpus, exact-input derivation tools and native validation modules; no opaque image replacement |
| `vendor/lineage/config/common.mk` | Two recorded defaults made optional so Nezha can enforce privileged permissions and prohibit OTA downgrade |
| `system/sepolicy/private/su.te` | The unconditional permissive-su declaration removed; all permission grants and assertions retained |
| `system/sepolicy/private/init_dev_config.te` | Reviewed explicit capability gates two helper property SET permissions; other boards retain upstream undefined/true behavior |
| `system/core/init` | Known boot/build property masking helpers disabled; existing `ro.boot.*` values kept write-once |
| `build/make/core/Makefile` | Reviewed fail-closed consumer of the working76 recovery bundle |

This table describes the installed v11b checkpoint, not every authored change
in the workspace. The optional OEM properties and framework-provider policy,
the Camera runtime bundle/Soong patch, mi_ext/0007 packaging, 0006 A/B recovery
correction, and native EROFS exporter still require guarded guest adoption and
their own native results. See [current status](workspace-status.md) and the
[v11 milestone](oem-policy-integration.md). The selected VINTF input build has
separately passed; its [artifact audit](vintf-compatibility.md) still identifies
missing framework fragments and APEX packages before complete compatibility.

The public platform manifest and all its project revisions were preserved.
No second sync or replacement source checkout was created. The resolved
manifest describes the upstream base; local source/admission receipts and the
[vendor property patch](../patches/evolution/security-properties.json),
[SELinux enforcement patch](../patches/evolution/selinux-enforcement.json) and
[init property patch](../patches/evolution/init-boot-properties.json),
[helper capability](../config/nezha-init-helper-capability.json) and
[recovery consumer](../patches/evolution/prebuilt-recovery.json) describe
the additional inputs and four modified Repo projects. They must travel
together in any build provenance record. Historical source audits below
describe their own earlier checkpoints.

The initial transfer verified **975 files / 5,932,585,937 bytes** inside the
owning VM. No home directory, Downloads directory, credentials or phone
evidence was bind-mounted. `container cp` reported success in this runtime but
did not make the files visible under the mounted `/work` path; the accepted
transfer used `container exec` streaming, checked every hash and read back
every written file before installation. Existing attempts and inputs were
preserved. Always verify destination contents from the actual builder view.

## Regenerate without replacing existing evidence

The source templates are committed. The large input bundles and generated
receipts remain ignored. To reproduce the device configuration from existing
verified bundles, choose a new output path. The current factory profile uses
all three explicit factory-contract arguments together:

For the current native-policy profile, first stage a new private policy bundle
using the [OEM policy workflow](oem-policy-integration.md), including its
explicit `--oem-policy-contract config/nezha-oem-policy.json` option. The example below
expects that bundle at `artifacts/policy-inputs/nezha-factory-NEW` and adds its
explicit helper capability and receipt; it does not silently opt into them.

```sh
factory_analysis=artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b
python3 scripts/generate_device_tree.py generate \
  --variant user \
  --kernel-receipt artifacts/kernel-inputs/nezha-xiaomi-eu-candidate-v2/receipt.json \
  --vendor-receipt artifacts/vendor-inputs/nezha-factory-d2cf57fd-camera-v1/vendor-inputs.json \
  --firmware-layout "$factory_analysis/normalized-layout-v1/firmware-layout.json" \
  --vintf-contract "$factory_analysis/build-property-comparison-v2/analysis/vintf-properties.json" \
  --factory-boot-contract research/factory-boot-contract.json \
  --partition-metadata research/partition-metadata.json \
  --dsp-policy-contract research/dsp-policy-integration.json \
  --init-helper-capability-contract config/nezha-init-helper-capability.json \
  --oem-policy-contract config/nezha-oem-policy.json \
  --policy-inputs-receipt artifacts/policy-inputs/nezha-factory-NEW/policy-inputs.json \
  --fstab-source "$factory_analysis/boot-analysis/ramdisk-comparison-v2/text-members/vendor_boot-0001.txt" \
  --output artifacts/device-candidates/nezha-framework-NEW
python3 scripts/generate_device_tree.py validate \
  --output artifacts/device-candidates/nezha-framework-NEW \
  --purpose configuration
```

Generation rehashes the bound inputs and refuses existing output directories.
It does not mutate the Linux checkout or phone. `--purpose target-files` and
`--purpose flash` deliberately fail for this profile. The source retains the
required `mi_ext` mount; it does not pretend that omitting that image makes a
complete partition set.

The [kernel wrapper](../kernel/xiaomi/nezha/README.md) explains module packaging.
The [DTS recipe](../kernel/xiaomi/nezha/dts/README.md) produces private source for
all eight base DTBs and the Nezha overlay. Recompilation preserves all parsed
nodes/properties and fixups, corroborated independently with sorted DTC output.
Rebuilt binary layouts differ, so this is source preparation, not permission
to replace the stock DTs or a claim that a rebuilt kernel boots.

## Verified boundaries

The initial product check passed at `2026-08-27T18:28:40Z`, with no missing
dependency or security-check overrides. The first module-graph attempt exposed
missing Lineage Soong exports; the device now includes the complete
`BoardConfigLineage.mk` hook after its prebuilt selector and board values.
The [current build record](../research/build-progress.json) tracks later
errors and fixes without turning failed attempts into successful builds.

The third module attempt completed successfully at `2026-08-27T19:09:52Z`
after 4,591 Ninja actions. Independent ELF and SHA256 checks distinguish the
218,624-byte ARM64 `libbase.so` from the 6,179,856-byte x86-64 host checker.
The host checker subsequently executed; the Android library was not run on
the phone. This proves selected modules through the real Nezha product graph,
not a complete image set or a working native feature.

An independent post-build audit checked all 1,179 project HEADs and remotes.
Exactly 1,178 worktrees were clean; the only project change was the recorded
vendor property patch. Authored directories outside Repo have separate input
receipts. No unexpected project edits were found and no source sync was
repeated.

The actual Ninja process was observed under nsjail with separate mount,
network, PID and user namespaces. Its initial product configuration mounted
source **read-write**, unlike the earlier standalone read-only probe.
The later authored board setting explicitly requires read-only source for the
Camera build. Its actual Ninja mount table at `19:37:34 UTC` confirmed source
read-only and output read-write, with the same four separate namespaces.
The observation receipt has SHA256
`30916dc00013762cb2e8d05bbb86ab42e6f80f38f47c3f1bfade62c5926f977e`.
Neither observation should be substituted for the other, and the upstream
basic Soong/Kati sandbox remains unchanged. Observing the running process is
not a successful build result.

The v4 device admission selected Camera bundle v2 and that stronger
source setting. Both earlier installed source directories were preserved
outside the Android checkout before replacement; only 575,475 bytes of small
files crossed from the host. Vendor/ODM images were copied and reverified
inside the same VM with unchanged hashes. The Camera build is a separate
experiment; its current result is in the build record.

The first Camera attempt reached its one-hour probe deadline at `20:26:45 UTC`
and was cancelled. No compiler failure preceded the cancellation. All compiled
outputs were retained; the second attempt resumed in the same directory with
a two-hour bound and adds the Soong `secilc` and `sepolicy-analyze` host tools.
This is not a clean build or another source sync.

Device admission **v5** was installed at `20:46:42 UTC` by an atomic
directory exchange, preserving v4 outside the checkout. Only BoardConfig and
its README changed; the kernel and vendor bundles did not. The regenerated
dexpreopt configuration now has **`RelaxUsesLibraryCheck=false`**, while
`WithDexpreopt=true` and `DisablePreopt=false`. The effective-setting receipt
has SHA256 `a1288fd08e3e9238bc68fde278f0f6a6ebf66fa135c3d613a8a008072a15d82d`.
This corrects the inherited BCR relaxation without disabling preoptimization.
It establishes the generated configuration, not validation or installation of
the [Camera APK](camera-apk-integration.md), which remains outside the bundle.

The second Camera attempt **passed at 21:17:15 UTC**, completing 4,206
incremental Ninja actions without a timeout or sandbox fallback. The actual
Ninja observation at `20:58:32 UTC` again confirms four separate namespaces,
read-only source and read-write output. Its receipt is separate from the
first attempt's observation. The build receipt has SHA256
`890368868de6b6e9822f24bb79e358c84ba269f48a0898830e50388e2eb953b9`.

All nine installed dependency files match their admitted source hashes.
The four JARs also pass member-content and CRC comparison, and all four have
generated ARM64 ODEX and VDEX outputs. The JNI library's actual
`g.cc.checkElfFile` action completed with 20 shared-library inputs, the
16 KiB page-alignment check and no undefined-symbol exemption. The output
verification receipt has SHA256
`517abf483adf40ec5dcb0386231667f03be93771a73e0d6746096f4f8ee8d399`.
The built `secilc`, `sepolicy-analyze` and `checkvintf` files are x86-64 host
tools; none of these results proves Camera or Leica behavior on the phone.

Device admission **v6** was installed at `21:34:15 UTC`, preserving v5
and all existing outputs. Its only source change copies the stock
`system_dlkm.modules.blocklist` selector into vendor_dlkm, where the stock
loader expects it. This is separate from system_dlkm's own blocklist and
does not block the intended vendor ZRAM pair. The kernel and vendor input
receipts are unchanged. See the [ZRAM contract](zram-module-plan.md).
Installation receipt SHA256:
`ab7e791bca52cca3d0742a1179939e1ecc49c78cf0cb7857543da8947c6d59c7`.
The Camera pass above belongs to v5, not this later source installation.

The v6 [boot/DLKM build](boot-dlkm-build.md) subsequently passed at
`22:01:05 UTC`, producing boot, DTBO and both DLKM images plus the requested
framework policy inputs/tests. Independent inspection verifies the exact
kernel and DTBO payloads, internal AVB checks and all 484 module hashes inside
the EROFS images. The vendor-side system selector is present with its stock
hash. This is not a complete signed image set or a successful vendor-policy
compatibility result; those boundaries are explicit in that separate record.

Admission **v7** was installed at `22:26:29 UTC`, preserving v6.
It records the stricter `user` variant and registers that lunch choice alongside
the existing `userdebug` choice. Both remain framework-checks products; `eng`
and complete-ROM/flash admission remain rejected. The kernel/vendor bundles,
generated geometry and fstab are unchanged. Installation receipt SHA256:
`4e01f4ba023e07aaec605baf341b7b4bd696e09a67862f91b811a5ebde67c120`.

A separate user policy/tool build passed at `22:44:46 UTC` in the fresh output
`/work/out/nezha-user-policy-20260827T2220Z`, through its matching source-root
`out-nezha-user-policy-20260827T2220Z` alias. Reusing the userdebug output for a
variant switch could trigger install-clean behavior; this experiment does not
request that operation or reset the previous output. Its four verified images
and seven framework files were rehashed before and after: all eleven are
unchanged. The 2,788-action build included the framework neverallow, policy and
device-type tests. Build receipt SHA256:
`5dff46fcbbbe5ffd0d8a8a046ac93c070b61ebf2c63dc70c2ae3dd573df25fc8`.
Those source targets do not include the captured factory vendor/ODM CIL.
Combining that exact policy with the new user outputs is a separate check,
not a pass established by these successful framework targets. No live Ninja
namespace snapshot was captured for this attempt; its logs show no sandbox
fallback. Earlier sandbox observations retain their own attempt identities.

Admission **v8** was installed at `23:28:02 UTC`. It uses the separately
verified factory vendor/ODM images, factory API/property facts, factory fstab
flags and package GPT budgets. Its DTBO budget is now **32 MiB**, with the
unchanged 22 MiB stock input. All eight logical AVB declarations, five boot
verification rows, GSI key-path references, encryption fields and two inert
vold device-node patterns are retained. The existing kernel bundle keeps its
Xiaomi.eu provenance; equality with selected factory components does not
relabel its origin. See [factory input reuse](factory-input-reuse.md).

The same owning VM received 30 files totaling 5,727,927,659 bytes through a
hash-checked stream, with destination readback. Both old device/vendor trees
are preserved under `/work/candidates/nezha-factory-v8/`. All 950 kernel input
files and 18 historical output artifacts were checked unchanged. No output
directory was reset. Installation receipt SHA256:
`9775be640f7e37d722113e5c86d1774daa1da6ecafa8468637018ea62a6ea7dc`.

An independent read-only audit at `23:35:12 UTC` rehashed all 10 installed
device files and 17 vendor files, including both replacement images:
5,727,913,542 bytes, with no missing or extra files. It also checked the
admission and kernel receipt bindings, without repeating the full kernel
payload audit or accessing either output directory. Audit receipt SHA256:
`a3fab1746edcb26b9ec1e954451d524cfebaf2cc75c20691f700ac9b94d8d676`.

V8 also requires Treble labeling errors rather than warnings and rejects an
unreviewed tracking list. This alone does not schedule or pass the labeling
test at platform policy version `202504`. Separately, the pinned source's
unconditional `permissive su;` statement was removed at `23:29:36 UTC`, with
the original file preserved and all other policy statements unchanged.
The [patch](../patches/evolution/selinux-enforcement.json) binds both source
hashes. Its installation receipt SHA256 is
`f776922d1e1167fa53998d0bbf8983fea0f11a9a756b160f75b4e4405918542b`.
Those installation receipts precede compilation; the earlier user v7 result
remains a different policy snapshot. The later
[hardened user v8 build](user-security-build.md) passed at `00:17:18 UTC` on
August 28 after 6,551 Ninja actions, including init, init_boot, vendor_boot,
DTBO and source-policy targets. Both generated source-policy binaries then
passed an independent, unfiltered check with zero permissive domains.
The ten-file combination with exact factory vendor/ODM CIL still fails five
assertions and produces no binary. The generated precompiled policy is staged
under ODM; it has not replaced the policy inside the retained factory image.

The pinned init source was hardened at `23:49:25 UTC`. Both init-stage
defaults now use `SPOOF_SAFETYNET=0`; the previously unconditional release,
debug and vbmeta property helper calls now obey that guard. Existing
`ro.boot.*` values remain write-once even during vendor property initialization.
Property name/value, SELinux and socket checks are unchanged. The exact-source
patch and both resulting Git blobs passed isolated application checks before
installation. The original files and all 18 earlier output artifacts were
preserved. Installation receipt SHA256:
`e8893a3c2e26cd19ba5ad0b6c521d19a214de6f5ae295c3316701dd2736f02c3`.
This is source hardening, not a runtime property or bootloader-state result;
libinit hooks and initial property sources still need separate verification.
The subsequent complete source audit matched all 1,179 project HEADs and
remotes, with exactly three expected patched projects and 1,176 clean ones.
The audit and successful v8 build have separate receipts; the original source
installation receipt's compilation fields remain historical observations.

The v8 [boot-content inspection](factory-boot-build.md) subsequently passed
for the 8 MiB init_boot, 96 MiB vendor_boot and 32 MiB DTBO images. It verified
the packaged first-stage init, all 430 vendor-ramdisk modules, six metadata
files, admitted fstab, DTB and DTBO payloads. All three AVB hash descriptors
pass, but their algorithm is `NONE`: the individual blocks are unsigned and
do not establish a complete signed chain. The second-stage init was built
and inspected, but has not been verified inside a completed system image.

At the August 28 checkpoint, source admission **v9** was generated with the
explicit [DSP policy contract](dsp-policy-integration.md). Its installation changed
only the generated board wiring and two source-policy files. The v8 source
directory was preserved, all 63 output guards passed, and the vendor/kernel
receipts, six checked project revisions and four patched source files remained
unchanged. The 12 transferred source files total 24,435 bytes; control receipts
are separate. Installation SHA256:
`dae184a0129e4224e851b779e760a38c03a66559d114bf19e7b4590913543a76`.
This installation record does not itself establish the subsequent Soong or
full factory-policy result.

The subsequent [v9 policy build](dsp-policy-build.md) passed at `01:26:15 UTC`
on August 28 after 201 Ninja actions. The actual Soong outputs contain the
intended DSP attribute and isolated-compute membership. Both source-policy
binaries pass unfiltered permissive-domain checks. The strict combination of
all seven new framework CIL files and three unchanged factory files then failed
four assertion sites instead of five: two Binder conflicts and two init-helper
property conflicts remain. All 6,366 assertions are retained. No combined
policy binary or factory compatibility pass is claimed.

This incremental build preserved all 12 checked v8 boot/init artifacts, the
sealed v8 snapshot and eleven earlier userdebug artifacts. A fresh complete
source audit again matched all 1,179 project HEADs and remotes, with only the
three recorded patched projects. It did not repeat the earlier LFS payload
audit or inspect ignored files and authored directories outside Repo. The
source checkout and output directories were not reset, and the phone was not
accessed.

The subsequent [Binder comparison](binder-policy-correction.md) compiled the
same ten inputs twice, replacing only the private vendor CIL in the second
case. Removing 67 Binder grant occurrences that paired process domains with
service objects reduced the diagnostics from four assertion sites to two.
Both compiler invocations still failed with exit code 255 and produced no
binary. All 6,366 assertions, the related FD grants and valid process Binder
grants were retained. This is a separate prototype, not a modified factory
image or a later device source admission.

At that checkpoint, the remaining sites concerned the new `init_dev_config`
helper's APEX and media property writes. Its
[optional source capability](init-helper-capability.md)
has a tested patch that omits those two grants while preserving property reads,
socket access, existing init permissions and upstream defaults. The isolated
Git and host-M4 results are not an Android source build. The new definition had
not yet been installed, and absent literals in selected factory files do not
establish permanent helper nonuse or native-feature compatibility.

The subsequent [complete CIL comparison](helper-policy-projection.md) passed
for the projected inputs at `02:51:01 UTC` on August 28. Its unchanged baseline
still failed at the two helper assertions. Replacing only the platform CIL
with the exact two-SET projection produced a 1,515,046-byte policy binary;
the unfiltered analyzer exited successfully with no permissive domains.
The comparison retained all ten CIL inputs and all 6,366 assertions. The
Binder-derived vendor policy was identical in both cases. No image, source
admission, M4 build, init execution or native feature was validated by this
comparison.

A fresh source audit after that run again verified every one of the 1,179
project HEADs and remotes: 1,176 clean worktrees and exactly the three recorded
patched projects. No unexpected changes or local manifests appeared. This
audit did not rehash LFS payloads or cover ignored files and authored
directories outside Repo. The installed device admission was still v9 at that
August 28 checkpoint. The August 29 [native source integration](policy-source-integration.md)
subsequently installed v10c, admitted the helper capability through Android M4,
and reproduced the strict combined policy through a native vendor derivation.

The next local milestones before a complete device build are:

- Restore the missing OEM public service declarations, object roles and 202504
  mappings, and the framework classification of `offlinelog_file`. Review the
  permission effects and repeat the three failing factory context/structural
  checks recorded in the native integration evidence.
- Adopt the reviewed derived policy into images, preserving the original
  images, filesystem metadata, provenance and AVB requirements. The successful
  native combined-policy target is noninstallable and has not done that
  packaging.
- Assemble the Evolution framework VINTF inputs and every required partition,
  including `mi_ext`, and validate a complete engineering image set and boot
  chain. Individual component builds are not a complete target-files or OTA
  result.
- Resolve the Camera APK's signing, framework and native-library dependencies;
  the nine successfully built dependencies do not establish app compatibility.

The later [TWRP device tests](twrp-bringup.md) positively verified an unlocked
bootloader and booted `working76`, now the selected default recovery. That
recovery test used the installed stock companion boot, kernel and vendor stack;
it is not an Evolution boot or a complete ROM/OTA integration result. Future
phone tests still require selected-device/partition/rollback revalidation, a
return plan and specific user authorization. The [recovery plan](recovery-plan.md)
does not provide bootloader-corruption protection or verified data decryption.
See [current workspace status](workspace-status.md) for the consolidated gates.

The separate [SELinux contract](selinux-contract.md) captures the exact stock
policy inputs and reports seven neverallow failures using native tools from
pinned sources. Repeating the same ten unmodified CIL inputs with the actual
Soong-built x86-64 compiler returned the same seven neverallow failures.
No policy binary was produced, and no assertion was filtered. The later
[factory/user policy check](selinux-user-integration.md) reduced the combined
Evolution/vendor diagnostics to five assertion sites using actual `user`
outputs. It still failed and produced no policy binary. Building the compiler
tools or source policy alone does not establish factory-policy compatibility.

The built host checker also passed a [vendor/ODM VINTF load and merge](vintf-validation.md)
with the unchanged active APEX list and exact CAS/Widevine fragments. The
stock-framework check reports five HIDL definitions absent from this
validator's compiled metadata. Full compatibility with the assembled Evolution
framework remains a separate check; no matrix or APEX list was filtered to
produce a pass.

The second attempt found an upstream CI-packaging assumption about output
paths. With an absolute `OUT_DIR`, the host Perfetto path reached the normal
artifact-path validator and was correctly rejected. The accepted workaround
uses a source-root output symlink, which the pinned Soong sandbox supports:

```text
/work/evolution/out-nezha-framework-20260827T1835Z
  -> ../out/nezha-framework-20260827T1835Z
OUT_DIR=out-nezha-framework-20260827T1835Z
```

The link resolves to the same existing directory and inode, and its `.out-dir`
and `.top` markers were preserved. Nothing was deleted or reset. This pinned
CI code requires the relative name to begin with `out`; `../out/...` does not
avoid the bug. No Soong source, path validator or sandbox setting was changed.
This reproduces the default CI archive behavior, which already omits those
host packaging entries; it does not prove that Perfetto is in the CI archive.
[CI path handling](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/ci_tests/ci_test_package_zip.go#L300-L319),
[output symlink handling](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/ui/build/soong.go#L554-L572),
[sandbox resolution](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/ui/build/sandbox_linux.go#L77-L85).

Inside the existing owning VM, with the admitted inputs already installed,
the bounded module command is:

```sh
cd /work/evolution
test -L out-nezha-framework-20260827T1835Z
test "$(realpath out-nezha-framework-20260827T1835Z)" = \
  /work/out/nezha-framework-20260827T1835Z
env PATH="$PWD/prebuilts/build-tools/path/linux-x86:$PATH" \
  OUT_DIR=out-nezha-framework-20260827T1835Z \
  TARGET_PRODUCT=lineage_nezha TARGET_RELEASE=bp4a \
  TARGET_BUILD_VARIANT=userdebug \
  GOTOOLCHAIN=local GOENV=off GOPROXY=off GOSUMDB=off \
  GOCACHE=/work/cache/nezha-framework-go \
  build/soong/soong_ui.bash --make-mode -j12 libbase checkvintf
```

Do not run another build concurrently in this output directory. Preserve the
complete logs and fail sandbox validation if the build reports
`Build sandboxing disabled due to nsjail error.` A module build does not approve
the framework profile for complete image or device testing.

The Xiaomi.eu inputs retain their known AVB failures and unverified origin.
No old vbmeta is imported as a valid new chain. Engineering AVB configuration
uses an explicitly identified AOSP development key; this is not an OEM key,
production signing policy or an accepted flashable image set. Input hashes,
correctly generated signatures and device trust are separate questions.

The separately supplied factory-named TGZ is now readable under `sources/`.
Its [intake and image extraction](factory-firmware-intake.md) passed; the
earlier Downloads timeouts remain historical observations. It has its own
provenance and [passing selected AVB/filesystem checks](factory-firmware-validation.md).
The installed v8 candidate now uses its factory vendor/ODM images through the
explicit transfer and admission above. Earlier build results retain their
Xiaomi.eu input identities; the current kernel bundle retains that provenance
as well. No package has been silently relabelled as authenticated OEM input.

No ROM boot, camera/Leica function, IMS, fingerprint, charging, encryption or
other hardware behavior has been established on Evolution X. Run `make test`
for tooling changes; build results and eventual authorized hardware tests are
separate evidence.

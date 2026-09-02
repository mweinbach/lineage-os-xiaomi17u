# Nezha product and build progress

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

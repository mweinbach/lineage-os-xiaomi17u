# Nezha product and build progress

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

The five-image query's host preparation is complete, and its **fresh read-only
native capture starts at 21:31:09 UTC**; the capture result is not yet verified.
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

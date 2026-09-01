# Exact factory vendor/ODM policy image inputs

`scripts/policy_image_inputs.py` prepares two complete, byte-identical TAR sets
for the exact five reviewed policy replacements. It does not extract a
filesystem, execute an image writer, regenerate an AVB footer, sign anything,
adopt a vendor image, or authorize a device operation. The selected platform
remains Evolution X `bka` / `bp4a` and normal Android remains enforcing.

The public contract is `config/nezha-policy-images.json`. Its schema-2 profile
container preserves the original contract unchanged under `historical-v12` and
the separately selected `v12-export4` profile. The newer `v13h-policy-only`
profile binds the completed provider policy build and analysis described below.
The explicit `policy3-evolution` successor binds the ordinary Evolution source
composition and the separate native binary, public-freeze and installed-sidecar
evidence. It permits validation and TAR preparation for that exact snapshot;
its scoped source review alone cannot admit image preparation.
`historical-v12` remains the
default and remains blocked; selecting a newer profile is never implicit.
The export4 profile's contract ID is
`nezha-five-file-policy-image-inputs-v12-export4-v1`.

The originals remain the vendor and ODM images from factory package SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
Their image hashes, package budgets, five original file hashes, source tools,
native tool identities and reviewed native qualification records are pinned.
The export4 native policy analysis and both complete stock no-op reconstruction
proofs now exist. The three framework hash sidecars were absent from the selected
export4 snapshot. That profile therefore requires a captured producer recipe
and separate native validation before explicitly deriving those files from
the captured CIL and mapping inputs. The fresh native validation passed all
three known answers and all three specific negative cases, with zero skips;
its source, tools, isolation and exact results are pinned. Expected bytes alone
do not complete admission. Derived files are recorded as
derivations, never as captured native outputs or invented native paths.

The first native sidecar run is preserved under ignored
`artifacts/build-validation/nezha-policy-sidecar-native-v1-failed/`. It failed
during loader-output inspection before any sidecar recipe executed. Its result
is not admitted as a pass. The fresh v2 validation handles only the captured
initial AArch64 address-only record, preserves its text without assigning a
file origin or mapping type, and checks all named tool/runtime records with
the unchanged parser. Unknown output still fails.

The successful native receipt is
`artifacts/build-validation/nezha-policy-sidecar-native-v2/results/receipt.json`,
SHA256 `54e95463bcbc02f47bcca7c27b0d2089ad3da54f67a4ac4c37557b1ca5976865`
(41,444 bytes). It records fourteen executed commands and six passed checks.
The public profile separately binds its outer orchestration, sandbox and source
capture. The source recipe is the three `java_genrule` definitions in
`system/sepolicy/Android.bp` at revision
`e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27`, file SHA256
`17171fec6b4e253db277c351f817670077c6fd235ca07ac33be509c8faa4d2f8`.
The recorded implementation runs that recipe with the measured guest system
shell and hash tools against sealed export4 inputs. It does not claim that
Android's genrules executed or that installed sidecars were captured.

The selected export4 contract's canonical SHA256 is
`5c7e020cbf2101bc6ed5af412f1e667d41e75e3259547c0700090d2d1f10ffb4`.
This admits evidence validation and TAR preparation only. A separate native
export4 reconstruction subsequently passed nine checks and 38 commands with
zero skips, exactly one vendor and four ODM content changes, and identical
repeated raw images. Its receipt is
`artifacts/build-validation/nezha-policy-images-export4-v1/results/receipt.json`,
SHA256 `77b40170a55f15418f75d2bbe89ff7bb99c5024600f0d5aacee23c064f3f765e`.
Those images remain separate unsigned derivatives; they were not adopted and
do not carry the v13h provider policy.

```sh
python3 scripts/policy_image_inputs.py plan
python3 scripts/policy_image_inputs.py plan --profile v12-export4
python3 scripts/policy_image_inputs.py plan --profile v13h-policy-only
python3 scripts/policy_image_inputs.py plan --profile policy3-evolution
```

`plan` reports the selected profile and its missing prerequisites. It exits 2
while prerequisites remain missing; this is not a failed Android build or a
skipped native test. A profile selection does not change readiness flags,
authorize native execution, or adopt the later installed provider inputs.

## Scope and native evidence

The complete stock exports contain 3,910 vendor entries and 3,059 ODM entries.
Their manifest hashes are respectively
`2fc24e40afe13aadf7a21b8dc19f3a24d0d2a2c2310ce7c2c0756248edc27638`
and `715b3afae593217b31b0ccb4ed9636b5b10c3ea66756953ac3ac6f091745156f`.
Every inode and both superblocks have zero timestamp nanoseconds; neither
image contains empty xattr values. Both stock filesystems passed the native
metadata and xattr checks. These observations are specific to these originals.

The native reader qualification passed all eight shared-xattr checks. The
broader synthetic run recorded 25 passes, two failures and zero skips. Its
failures remain the pinned writer's nanosecond preservation and upstream
`fsck.erofs` empty-xattr compatibility. The complete synthetic TAR writer run
recorded 11 passes, six failures and zero skips, with exit status 1. All six
failures were upstream empty-xattr checks on two seeds and four derivatives;
the complete metadata, exact five changes and two independent image/TAR/export
derivations passed. No complete synthetic suite pass is claimed.

This workflow admits only the narrower observed stock profile. It rejects
nonzero nanoseconds and empty xattr values before writing TARs. It checks the
qualification's outer sandbox/run record against the exact inner receipt,
preserved helper inputs, source build, tools lock and prior qualification
records. All reviewed failures remain visible in its output.

`tools/erofs-metadata/full_tar.py` is a byte-identical promotion of the helper
used by that native experiment: SHA256
`ec487d93ea158fab7022f427793839211978790f01dbcfc9361a63b02b681daa`,
17,421 bytes. Its promotion is not another native qualification. The selected
EROFS source remains commit `2c190a73fceb29f00da0558e44bb88ce19ec5bf4`;
the metadata exporter source remains
`89d60827a44c1c808b8c9bb6f180b28aeaa0e440ff7180856e9c16180cab06b3`.

The complete original vendor and ODM no-op native reconstructions also passed:

| Native capture | Checks | Raw image bytes per independent build | Receipt SHA256 |
| --- | --- | ---: | --- |
| `nezha-erofs-full-vendor-v2` | 8 passed, 0 skipped | 941,744,128 | `a4afbf6be2f392c46f30bcc223bff92d6606854a2aa69c712877f6a09a473763` |
| `nezha-erofs-full-odm-v1` | 8 passed, 0 skipped | 4,678,053,888 | `762c7e7607658414b3feaf4d0a3ef5f8a0884d86810d68d5f6344d003aae35b7` |

Each capture under ignored `artifacts/build-validation/` retains its native
receipt, orchestration record, diagnostics and complete metadata exports. The
two TARs, raw images and exports are byte-identical within each partition's
independent builds. All original file bytes and semantic metadata match;
only physical inode/block locations are excluded from the comparison. Both
runs used zero replacements and passed structure, data and raw-xattr checks.
ODM processed its actual 6,004,780,032-byte TAR beyond the 4 GiB boundary.
These results qualify those exact stock no-op reconstructions, not the five
policy substitutions, equality with the original signed image, retained-kernel
mounting, AVB, partition fit or boot. Earlier failed attempts and synthetic
limitations remain preserved.

The selected policy proof is `analysis-v12f-export4-v1`, operation
`verify-native-oem-properties-v12f-export4`. Its captured receipt at
`artifacts/build-validation/nezha-analysis-v12f-export4-v1/receipt.json` is
342,300 bytes, SHA256
`dd338730212aadf7dde9847cd63f60e5023c3c1d5c2fae91ff3d199593219c95`.
It binds the successful `policy-v12f-export-1` native build, exact compiler
inputs and source-fixup chain; verifies source/M4 and API-202504 mapping
provenance, the fresh OEM guard and nine context/structural checks; and retains
all 6,366 assertions with the exact reviewed effects. All three analyzed
binaries have zero permissive domains. The framework provider profile remains
unselected. Full Treble APK labeling, later provider inputs and runtime
compatibility are not proven by this receipt.

## Explicit v13h provider policy snapshot

`v13h-policy-only` has contract ID
`nezha-five-file-policy-image-inputs-v13h-v1` and canonical profile SHA256
`39192f9272a222e4ca62caa501688e135ef227f1a2afe9e9a9a7c87dffdc53f0`.
The two earlier profile objects and their canonical digests remain unchanged.
Selecting the new profile does not upgrade their evidence or change the default.

The actual `policy-only-v13h-1` build requested 31 normal Android policy and
export goals for `lineage_nezha-bp4a-user`, with provider phase
`v13h-provider-policy-only-runtime-exports-v1`. Its captured result is
`artifacts/build-validation/nezha-policy-only-v13h-1/result.json`, SHA256
`1596843eca8377fdb17359e3a70009b84c95aad5a0219531f521e52e21659e5b`.
The independent native analysis is
`artifacts/build-validation/nezha-analysis-v13h-policy-only-v1/receipt.json`,
SHA256 `bb6e8f0218d1f4c61a3cd8221478007548e2a1950d048a9dd60d5d7842334b66`
(10,058,468 bytes). It binds the strict factory-combined binary SHA256
`44113598331ae410279432d39adb884db56fc1217ab5a35158c36fb3bee9f707`
(1,517,136 bytes), ten actual compiler inputs, nine fresh factory checks, the
fresh OEM guard and provider input producer, and three unfiltered policies
with zero permissive domains.

All 6,366 original assertions remain, with four reviewed provider registration
assertions added: 5,980 `neverallow` plus 390 `neverallowx` statements. Only the
system_ext CIL changes relative to export4; the other nine compiler inputs
remain byte-identical. The complete effect review is separately pinned at
`provider_complete_effect_review`, SHA256
`8037229ed752ec9e762ac6a2b624ffc0b76911a7dad068fdc9aa0f65dc325046`
(8,535,547 bytes). It includes inherited effects, 26 source allows, two
transitions and two deliberate dontaudit additions, while preserving the six
OEM public mappings, 105 property allow edges and zero helper property writes.
It does not claim unchanged denial logging.

Sixteen complete source, producer, context and semantic sections of the actual
analysis are pinned by canonical hash and length. This preserves the reviewed
nested details without adding a second CIL semantics implementation. Explicit
checks also bind their build, source, compiler inputs, factory-combined output,
raw OEM result and replacement files. The native provider contract differs
from the preserved semantic contract only at its input-profile hash; the
policy checker differs only at the corresponding single hash literal. Both
crosspin proofs are required. The nested semantic operation intentionally
remains `actual-v12f-to-v13f-provider-semantic-delta`; its limited inner scope
flags are not rewritten into native success claims.

Only this profile's `policy_analysis` and `provider_complete_effect_review`
JSON roles may use a 16 MiB reader bound. The generic 8 MiB bound and both old
profiles are unchanged. The exact identities and finite bounds apply on the
initial read and final re-read; no truncation or private-control limit override
is accepted.

The fresh native sidecar result is
`artifacts/build-validation/nezha-policy-sidecar-v13h-native-v1/results/receipt.json`,
SHA256 `d679acf232419b70c89c1fd05a48dd6647ca0a9d818f2dc9386db71669626630`
(41,770 bytes). Its 14 commands and six checks passed with zero skips, using
the same source recipe on the six actual v13h CIL/mapping inputs. The new
system_ext sidecar file SHA256 is
`04b3cfdefbc293724f48a4a6c0e6098d46aa944274c74928b9b9cd20b6709335`;
plat and product sidecars retain their earlier contents. All three remain
explicit 65-byte derivations, without installed-path or Android-genrule claims.
The old sidecar results cannot satisfy the new profile even when bytes agree.

The profile reuses the unchanged original-image, tool and complete no-op
EROFS qualifications. Its separate native reconstruction subsequently passed
nine checks and 38 commands with zero skips: both independent image pairs,
complete TARs and metadata exports matched, with exactly the five permitted
content replacements. The later keyless footer experiment is recorded
separately in [the current workspace status](workspace-status.md). Neither
result admits the later policy3 inputs, proves a signed parent AVB chain or
establishes a phone boot. This input profile itself does not establish provider
runtime, strict ELF execution, full Treble APK labeling, active ROM
compatibility or image adoption.

## Explicit ordinary Evolution policy3 snapshot

`policy3-evolution` uses contract ID
`nezha-five-file-policy-image-inputs-policy3-evolution-v1` and canonical profile
SHA256 `f49240bf1e128212b4f2e58092b37e4988fe6cf9a042d081bdb25a1411bd0b9a`.
The three earlier
profile objects, their canonical identities and the blocked historical default
remain unchanged. The selected platform is still `bka` / `bp4a`, with the
explicitly selected 4 KiB maximum page size and strict ELF and prebuilt alignment
checks enabled.

The actual `first-target-files-policy-3` ordinary Android build completed all
32 requested goals for `lineage_nezha-bp4a-user`, including `selinux_policy`.
The native build record is SHA256
`344ba909febe8be29479f5bf1d48d122e931e88fb1d4d71dbcdab08708483c18`
(10,165,316 bytes). Only this new profile's `policy_build` JSON role receives
a finite 16 MiB read bound. All other new roles keep the 8 MiB bound, and the
earlier profiles retain their existing limits. Initial and final reads apply
the same identity and size checks.

The scoped review under ignored
`reports/oem-policy-integration-20260829/ordinary-evolution-policy-transition-v1/policy3-actual-review-v1/`
is SHA256 `b2743829e4d6a74088208b0296e5989f53cb7f10c31333cb0b17f8410f193225`
(16,599 bytes). Its separate freeze is
`4547cb1bce20de5f1a2e8101d8d4d8d193a5b8cc25ab0c66de0e8749dc18d4c1`.
The profile binds all eight complete review sections, ten evidence records,
the six-member review freeze, the 89-body input capture and the full native
OEM semantic result. It requires the actual 539 source rows across thirteen
projects and all six before/after source and input guard groups.

The strict factory-combined policy is
`eef85951730890201b1d023ab68e7a44aab3a39f879d889f8eba1cadeb109270`
(1,537,590 bytes). Its ten compiler inputs are selected by exact runtime role,
actual native path, hash and size. Only the system_ext CIL and its 202504
mapping change relative to v13h; the other eight inputs and the reviewed
vendor Binder derivation are unchanged. The proof retains all 6,366 original
assertions, the four provider assertions and 29 Evolution assertions: 6,009
`neverallow` plus 390 `neverallowx` statements. It requires zero helper and
camera-init property writes and zero CIL permissive declarations.

The seven factory property-prefix languages retain their original labels and
string types. The three expected additional camera-property reader domains
are `mediashell_app`, `mosey_app` and `updater_app`; camera writers stay
`hal_camera_default` and `init`. The source composition contains 25 Evolution
and eight owned system_ext property-context rows. The earlier v12 property
edge-count budget is not reused as a substitute for reviewing this composition.

The source review deliberately does not claim all twelve binary permissive
checks, the public freeze comparison, installed sidecars, full recursive
producer provenance or complete Treble APK labeling. The successor requires
separate actual native evidence for the first three before preparation. It
does not require a recursive capture of the whole build graph or promote the
38 optional vendor source fragments into a mandatory factory runtime. Final
APK labeling and complete Treble checks remain later packaging gates.

The separate native binary result is
`932ba4bfd06f5278acb53a129abb90712202e4577791f1fab5d7bde5200f4c73`
(225,221 bytes), with independently replayed review
`bc1cc68b5ce15ad74056c6c1e66623b4713c323d81bc0a090997f51b877c7ba9`
(22,017 bytes). All twelve exact live/retained binary pairs passed unfiltered
`sepolicy-analyze ... permissive`: all 24 native output streams were empty,
both native and supervisor exits were zero, and diagnostics were complete and
separate. The source539 and complete configuration remained unchanged. The
seven upstream compatibility binaries retain their diagnostic compile scope;
they are not presented as strict neverallow enforcement. The strict factory
compiler proof remains independently bound by the scoped source review.

The focused public-freeze review is
`a6823c3fe63f29015d87d70f21d84c9bfb9d2291664083149bc50db9e24dff4e`
(16,928 bytes). It verifies the actual ordinary-build comparator action and,
separately, the current/API public CIL comparison using the captured checker
and parser sources. Both complete packaged Python bytecode members reproduce
from those sources. The 1,419 public types and 353 compared attributes match;
234 generated attributes are excluded by the upstream rule. This proves the
selected public-name interface, not whole-policy permission equivalence.
The captured stamp is not used alone as evidence of a successful comparison.

Unlike export4 and v13h, policy3 selects three actual installed sidecar files
in addition to the ten compiler inputs and factory-combined binary. Each must
be exactly the 65-byte hash of its ordered current CIL and mapping pair,
produced and installed through the ordinary Android build with captured
recipe, command and output evidence. Expected bytes or an empty stamp alone
cannot complete this proof. No locally derived file is assigned a native
installation path.

The successful read-only capture is
`85cc5fc4dbe586734402d4e014bc71d049947be178e53bd637974f40fe89fd30`
(2,112,990 bytes); its producer qualification is
`57e2191f1d948407dda3adf040edb3b58ce018adb6bb4a1d56471bb0226682fd`
(44,989 bytes). Both remain within the ordinary 8 MiB JSON bound. The nineteen
observations match before and after capture. Three genrules, three intermediate
copies and three installations are tied to the completed policy3 build, with
six appended Ninja success records. The qualification performs zero fresh
native producer actions. It binds the actual three 65-byte installed outputs
to the six captured compiler-input bodies and the exact sbox recipes.

The first capture failed on a private-view ownership check before its queries
ran and remains preserved in the ignored seven-producer capture directory.
The corrected capture checks the complete 539-row, thirteen-project source
proof in the original root context, retaining the owner/mode guards. Its
read-only namespace separately checks the selected configuration, inputs and
outputs; it records zero source-history rows checked there and explicitly
requires the root proof. The profile verifies both contexts and does not
relabel the earlier failure as a pass.

The profile now reports `ready_for_evidence_validation`, which is only the
prerequisite state for exact input validation and TAR preparation. Missing,
changed or mismatched records still stop preparation before output creation.
The later policy3 raw reconstruction and NONE footer/FEC stages pass their
separate repeated native comparisons. At **2026-09-01 02:37:56 UTC**, the reviewed
vendor/ODM leaves and metadata are selected by the **source-v2** transaction:
three tree exchanges, nine journal events and 537 verified source files across
thirteen projects, with independent installation review. This advances source
selection only; new output-image builds, packaged-policy checks, target-files,
the full signed chain and physical partition fit remain pending. The 205
metadata payloads retain their bytes and roles, while new private source copies
use declared mode 0600 and retained originals use 0644; build-identity validation
must bind that distinction before new product queries. See
[current status](workspace-status.md) and the
[installation record](../research/workspace-integration.json).

## Private input control

Keep the control JSON, original images, regular file bytes, native captures and
outputs in ignored private directories. The control requires schema version 1,
the selected profile's `contract_id`, its `contract_sha256`, and a simple
`artifact_set_id`. There is no `profile` field in the private control: the CLI
selects it, and mismatched control identities fail. `contract_sha256` hashes the
selected profile object serialized as sorted-key, two-space-indented JSON plus
one newline, not the whole schema-2 catalog. The historical contract ID remains
`nezha-five-file-policy-image-inputs-v1`; the explicit newer IDs are documented
with their profiles above.

| Map | Required entries |
| --- | --- |
| `records` | Exactly the keys of the selected profile's `native_records`; export4 has 29 roles, v13h adds `provider_complete_effect_review`, and policy3 has 39 roles for its separately bound ordinary source, native binary, public-freeze and sidecar proofs |
| `partitions` | `vendor` and `odm`; each has `image`, `manifest` and a separate, non-nested `staging_root` |
| `policy_files` | For export4 and v13h, exactly the ten runtime CIL/mapping inputs in `RUNTIME_INPUTS`, plus `combined`; historical-v12 and policy3 additionally require `plat_sha256`, `system_ext_sha256` and `product_sha256` as captured native outputs |
| `noop_manifests` | Export4, v13h and policy3: `vendor` and `odm`, each selecting the two complete native no-op manifests with ordinary `path` / `sha256` / `size_bytes` rows |

Every file selector contains `path`, `sha256` and `size_bytes`. A policy file
also contains `native_path`, the absolute physical producer path from the
current analysis. Local paths resolve relative to the private control. Native
paths are evidence, not commands to execute.

Every profile permits only these five content replacements:

| Partition | Exact path within that filesystem |
| --- | --- |
| vendor | `/etc/selinux/vendor_sepolicy.cil` |
| odm | `/etc/selinux/precompiled_sepolicy` |
| odm | `/etc/selinux/precompiled_sepolicy.plat_sepolicy_and_mapping.sha256` |
| odm | `/etc/selinux/precompiled_sepolicy.system_ext_sepolicy_and_mapping.sha256` |
| odm | `/etc/selinux/precompiled_sepolicy.product_sepolicy_and_mapping.sha256` |

The ODM binary must be the actual `nezha_factory_precompiled_sepolicy` output
consuming the exact ten reviewed compiler inputs. The source-only installed
`OUT/target/product/nezha/odm/etc/selinux/precompiled_sepolicy` is rejected as
the replacement even though its own zero-permissive analysis remains required.

The selected analysis must show the strict compiler and all 6,366 retained
assertions, plus four provider additions for v13h and policy3 and the further
29 Evolution additions for policy3. The older profiles bind three analyzed
policies; policy3 binds the twelve exact native binary checks above. Nine
fresh factory context tests and the source-bound OEM guard are required. The
helper property-write capability remains disabled. Each profile binds its
own reviewed effects; policy3 does not reuse the older property edge budget.
The independent vendor correction receipt must be the exact adjacent receipt
consumed by that analysis, including all original inputs and its five
preservation claims.

Each sidecar is independently recomputed as lowercase
`SHA256(framework CIL bytes || 202504 mapping bytes)` followed by one newline:
65 bytes. The source CIL/mapping selectors remain bound to the exact native
compiler inputs in the selected OUT. Historical-v12 also requires captured
sidecars at their native producer paths and remains blocked.

Export4 and v13h deliberately omit those absent native sidecar selectors. After the
required source-recipe capture and native known-answer validation are admitted,
preparation writes the three explicit derivations under the fresh output's
`derived-sidecars/`. Their provenance records the source-pair identities and
recipe/native-validation evidence. They do not receive a `native_path` or claim
that the corresponding installed native files existed. Missing validation
blocks preparation; byte agreement with a locally calculated hash alone cannot
satisfy it. No empty, stale or unrelated sidecar is substituted.

The staging roots supply only regular file bytes. They are not trusted for
ownership, mode, SELinux labels, capabilities, timestamps, symlink targets or
hardlinks. Those come from the complete native export, including byte paths
and exact xattrs. The helper verifies every original regular path, including
the five original replacement preimages and includes only manifest-listed
paths in the TAR; extra staging entries are not copied or rejected. It
uses no-follow directory/file access. It then substitutes the five selected
payloads while retaining the original metadata. Do not use a privileged
filesystem extraction/restore step as a substitute for this evidence.

```sh
python3 scripts/policy_image_inputs.py prepare --profile v12-export4 \
  --input artifacts/private-policy-inputs/control.json \
  --expected-sha256 CONTROL_SHA256 \
  --output-dir artifacts/policy-images/nezha/NEW_UNIQUE_RUN
```

The output must be a fresh child of the ignored policy-images directory. The
command hashes originals, verifies their existing AVB descriptor/profile
metadata, constructs both complete TAR sets independently, rehashes all four
TARs, and rechecks selected inputs and source identities before publishing
`preparation.json`. Incomplete output is retained without a success receipt.
No source-only policy, copied old AVB tail or fabricated new image hash can be
used to complete this stage.

This is a local-file preparation program, with no Container or device calls.
The controlling host may stage a complete small code/control bundle into a
fresh private Linux work directory and run it there against the existing
read-only guest originals and selected file bytes. The bundle needs the
pinned script dependencies and the AVB profile's three public evidence files;
its output stays under that bundle's `artifacts/policy-images/nezha`. This does
not require copying the 5.7 GB of original images to macOS, attaching another
VM, changing the source checkout, or transferring keys.

## Finite production execution parameters

The public contract records concrete limits for a subsequent native executor.
The full stock no-op runs exercised the pinned tools and these partition file
limits, but did not admit an executor for the five policy substitutions.
Do not change the frozen synthetic runner, whose mkfs limit is 16 MiB.

| Quantity before replacements | Vendor | ODM |
| --- | ---: | ---: |
| Unique regular bytes | 1,636,391,066 | 5,999,459,755 |
| Exact complete TAR bytes | 1,643,234,816 | 6,004,780,032 |
| Conservative scratch spool bytes at 64 KiB alignment | 1,767,243,776 | 6,120,144,896 |
| Fixed mkfs soft and hard `RLIMIT_FSIZE` | 2,147,483,648 | 6,442,450,944 |
| Largest original regular file | 66,595,226 | 238,324,108 |

The preparation report recomputes these bounds from the complete manifests
and actual replacement sizes. The fixed mkfs limit must cover both the TAR
and the sum of unique regular payloads rounded individually to 64 KiB, plus a
128 MiB construction allowance rounded up to a GiB. An exceeded limit blocks
the operation; it is not automatically raised. The allowance is conservative
construction headroom, not a compression or partition-fit proof.

Keep both staging trees, two TARs and two candidate images for each partition,
and execute native processes sequentially. The additional free-space bound is
the sum of original staging allocations, two exact TAR sizes and two fixed
image caps per partition, plus the largest scratch cap, selected replacement
source allocation and 2 GiB reserve. The minimum is 48 GiB of available space,
in addition to the original images and Android source/OUT already present.
Recompute using the actual payloads and recheck `f_bavail` on the actual work
filesystem before each phase. The baseline calculated peak including original
selected payload allocation is 48,717,800,448 bytes, below that 48 GiB floor.
No existing inputs may be deleted or pruned to satisfy it.

Regular-byte capture has a 512 MiB per-file and 2 GiB per-batch bound. The
current vendor requires at least one batch and ODM at least three. A fresh
private tree on the persistent ext4 work filesystem supplies the bytes; raw
case-sensitive or non-UTF8 names must not be restored onto a case-insensitive
host filesystem. A complete manifest-to-byte-path mapping remains required.

The production scratch directory must be private and on measured persistent
ext4, not a RAM-backed default `/tmp`. Measure the actual temporary-file
`st_blksize` and page size; the pinned disk buffer uses their maximum. Require
a power-of-two value no larger than 65,536. Under the exact native ABI and
sandbox, verify both 2/6 GiB soft and hard limits, the mkfs-specific ignored
`SIGXFSZ` fallback, rejected 2 TiB and limit-plus-one truncation without size
growth, rejected writes at the limit, and a bounded sparse write just below
the limit followed by truncation. The ODM test must exercise offsets above
4 GiB. A Python-only probe does not qualify the Rosetta native tool.

Capture stdout/stderr through bounded parent pipes, at most 16 MiB each;
metadata output has a separate 128 MiB bound. Overflow must fail and terminate
the whole child process group while retaining capped diagnostics. Merely
raising child `RLIMIT_FSIZE` would also permit multi-gigabyte redirected logs.
Do not count later log-size checks as an equivalent bound. Retain the source,
native binary, environment, signal, filesystem, limits and sandbox identities
in the production probe receipt before using these parameters on stock data.

## Gates after preparation

The emitted recipe uses the exact pinned mkfs tool with complete TAR input,
the original superblock time/UUID/label and reviewed compression flags. It
unsets `SOURCE_DATE_EPOCH`, preserves inode times, retains overlay xattrs and
does not reconstruct metadata from the staging tree. The recipe is data only;
this command never executes it.

Two actual native builds containing the five replacements must subsequently
pass complete metadata exports,
strict semantic comparison permitting exactly the five content changes,
unfiltered filesystem/xattr checks, and byte-identical image/export comparison.
The expected-after manifest and image identities must come from those actual
outputs. A new comparison contract is not fabricated during preparation.

The original AVB metadata is recorded solely as provenance. A changed EROFS
image needs fresh hash tree, FEC and footer data under the exact package
geometry and rollback/profile rules; copying the old tail is forbidden. The
2/6 GiB construction caps do not prove that the final signed partitions fit.
Use the separate host signing workflow and complete mixed-key AVB verifier
after real images and all chain members exist. Working76 recovery stays
unchanged. Source/vendor adoption, target-files/OTA packaging and an explicitly
authorized first Evolution boot remain separate gates.

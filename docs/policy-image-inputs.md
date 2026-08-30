# Exact factory vendor/ODM policy image inputs

`scripts/policy_image_inputs.py` prepares two complete, byte-identical TAR sets
for the exact five reviewed policy replacements. It does not extract a
filesystem, execute an image writer, regenerate an AVB footer, sign anything,
adopt a vendor image, or authorize a device operation. The selected platform
remains Evolution X `bka` / `bp4a` and normal Android remains enforcing.

The public contract is `config/nezha-policy-images.json`. Its schema-2 profile
container preserves the original contract unchanged under `historical-v12` and
adds the explicitly selected `v12-export4` profile. `historical-v12` remains the
default and remains blocked; selecting a newer profile is never implicit.
The current profile's contract ID is
`nezha-five-file-policy-image-inputs-v12-export4-v1`.

The originals remain the vendor and ODM images from factory package SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
Their image hashes, package budgets, five original file hashes, source tools,
native tool identities and reviewed native qualification records are pinned.
The export4 native policy analysis and both complete stock no-op reconstruction
proofs now exist. The three framework hash sidecars are absent from the selected
native OUT. The current profile therefore requires a captured producer recipe
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
This admits evidence validation and TAR preparation only. The changed-policy
EROFS images have not yet been built or adopted by this workflow.

```sh
python3 scripts/policy_image_inputs.py plan
python3 scripts/policy_image_inputs.py plan --profile v12-export4
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

## Private input control

Keep the control JSON, original images, regular file bytes, native captures and
outputs in ignored private directories. The control requires schema version 1,
the selected profile's `contract_id`, its `contract_sha256`, and a simple
`artifact_set_id`. There is no `profile` field in the private control: the CLI
selects it, and mismatched control identities fail. `contract_sha256` hashes the
selected profile object serialized as sorted-key, two-space-indented JSON plus
one newline, not the whole schema-2 catalog. The historical contract ID remains
`nezha-five-file-policy-image-inputs-v1`; the current ID is
`nezha-five-file-policy-image-inputs-v12-export4-v1`.

| Map | Required entries |
| --- | --- |
| `records` | Exactly the keys of the selected profile's `native_records`; export4 includes the bound native limit probe, both full no-op captures and their outer/sandbox records, and sidecar recipe/native validation evidence, in addition to the policy and EROFS prerequisites |
| `partitions` | `vendor` and `odm`; each has `image`, `manifest` and a separate, non-nested `staging_root` |
| `policy_files` | For export4, exactly the ten runtime CIL/mapping inputs in `RUNTIME_INPUTS`, plus `combined`; historical-v12 additionally requires `plat_sha256`, `system_ext_sha256` and `product_sha256` |
| `noop_manifests` | Export4 only: `vendor` and `odm`, each selecting the two complete native no-op manifests with ordinary `path` / `sha256` / `size_bytes` rows |

Every file selector contains `path`, `sha256` and `size_bytes`. A policy file
also contains `native_path`, the absolute physical producer path from the
current analysis. Local paths resolve relative to the private control. Native
paths are evidence, not commands to execute.

Both profiles permit only these five content replacements:

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

The current analysis must show the strict compiler, all 6,366 unchanged
assertions, zero permissive domains for all three analyzed policies, nine
fresh context tests and the source-bound OEM guard. The helper property-write
capability remains disabled. The four-property finite effect budget and
Binder correction are rebound to their reviewed public contracts and native
inputs. The independent vendor correction receipt must be the exact adjacent
receipt consumed by that analysis, including all original inputs and its five
preservation claims.

Each sidecar is independently recomputed as lowercase
`SHA256(framework CIL bytes || 202504 mapping bytes)` followed by one newline:
65 bytes. The source CIL/mapping selectors remain bound to the exact native
compiler inputs in the selected OUT. Historical-v12 also requires captured
sidecars at their native producer paths and remains blocked.

Export4 deliberately omits those absent native sidecar selectors. After the
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

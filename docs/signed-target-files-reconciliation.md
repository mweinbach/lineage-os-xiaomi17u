# Reconcile host-signed images into target-files

`scripts/reconcile_signed_target_files.py` places an already signed Nezha image
set into a fresh target-files ZIP. It preserves the original archive and every
unselected member. It does not sign, rebuild filesystems, invoke a VM, or access
private signing configuration. Its tests use inert images and mocked native
cryptography; promotion of the reviewed helper is not actual package admission.

The existing `bka` / `bp4a` signing contract, 17-image AVB profile, exact working76
recovery and partition budgets remain fixed. Normal Android remains enforcing.
The selected 4 KiB baseline and recovery exception are unchanged.

## Actual inputs and invocation

First preserve a completed native target-files archive, run the
[read-only inventory](target-files-avb-inventory.md), materialize its 13 final
data images plus the two explicit retained inputs, and complete the existing
[host signing workflow](avb-signing.md). A ZIP locator is not a signing input
file, and a synthetic test receipt cannot replace an actual result.

The request is a JSON object containing exactly `schema_version: 1`,
`operation: "reconcile-nezha-signed-target-files-v1"`, and these six fields. Each
field is an object with exactly `path`, lowercase `sha256`, and integer
`size_bytes`; paths are absolute or relative to the request's directory.

| Field | Required selected artifact |
| --- | --- |
| `target_files` | Original completed target-files ZIP and independently recorded identity |
| `inventory` | Complete unchanged inventory report for that exact ZIP and the same retained-input manifest |
| `retained_input_manifest` | Existing signing schema selecting exactly original `countrycode` and `pvmfw`, with their pinned factory extraction receipt |
| `signing_preparation` | Actual public-only `preparation.json` for the 15 materialized inputs |
| `signing_receipt` | Successful `signing-receipt.json`, including two identical signing passes and complete verification |
| `verification_manifest` | Actual 17-image `verification-manifest.json` beside the signing receipt, with canonical sibling image files and explicit approved public keys |

The preparation's adjacent `input-manifest.json`, all original input images and
source records, final signed images, public keys and pinned public tools must
remain available. Source records are hash-bound JSON objects, not automatically
authenticated provenance. Preserve the kernel's recorded input-origin warning.

```sh
python3 -B scripts/reconcile_signed_target_files.py \
  --request "$ACTUAL_RECONCILIATION_REQUEST" \
  --expected-sha256 "$ACTUAL_REQUEST_SHA256" \
  --output-dir "$FRESH_HOST_RECONCILIATION_DIRECTORY"
```

These variables denote actual selected inputs, not supplied artifacts. The
output must be a new child directory of ignored `artifacts/avb/nezha/`, with
existing nonsymlink parents. There is no latest-artifact selection, fallback
image, alternate profile, skip-check option or private-key argument.

## Checked transformation

The coordinator replays the original inventory exactly, joins preparation and
signing records to the original 15 inputs, binds both signing passes to the
final three derivatives, and preserves the other 14 inputs. It repeats the
existing [complete public-key AVB verification](avb-image-set.md) of all 17 final
images; a supplied receipt alone is insufficient.

Only the following existing members may change:

- `IMAGES/boot.img`, `IMAGES/vbmeta_system.img`, and `IMAGES/vbmeta.img`;
- every existing `BOOTABLE_IMAGES` and `PREBUILT_IMAGES` alias of those roles;
- only the existing `PREBUILT_IMAGES/dtbo.img`, when the proof below qualifies
  normalization to the unchanged canonical DTBO;
- `META/vbmeta_digest.txt`.

Each changed-role alias receives its canonical final image, even if its bytes
already match. Apart from the single proven DTBO exception below, other
recognized aliases must match their unchanged final image. No member is added
or removed. Original APK/APEX payloads, care maps, signing
metadata, symlink payloads, modes, timestamps, comments and member order stay
unchanged. Symlinks remain archive bytes and are never followed or extracted.

### Narrow DTBO alias normalization

DTBO is not a fourth signing or canonical replacement role: the changed-role
set stays exactly `boot`, `vbmeta` and `vbmeta_system`. Only an existing,
mismatched `PREBUILT_IMAGES/dtbo.img` may be replaced with the exact unchanged
`IMAGES/dtbo.img` bytes. An absent alias is not created, an identical alias stays
untouched, and other mismatched aliases still fail.

Both complete, equal-sized DTBO members must fit the unchanged profile budget
and 32 MiB bound. The read-only inspector compares every byte of their complete
declared payload, including table words, later entries and gaps, and recomputes
both salted SHA-256 digests. Both sides must pass strict unsigned `NONE`
metadata checks: zero flags and rollback fields, no authentication/key data,
one complete own `dtbo` hash descriptor, valid table/footer geometry and zero
padding. Only salt and `com.android.build.dtbo.fingerprint` value may differ,
with their derived digest/encoding lengths; raw-header conventions, release
bytes, descriptor order and all other properties remain invariant.

The proof binds the whole source archive and both members. The copier recomputes
it with type-exact equality rather than trusting a supplied boolean, requires
the replacement's full identity to equal the canonical image, and returns the
same recomputed proof to the reconciler. The reconciliation receipt records it
in `alias_normalizations`; the request schema is unchanged.
This unsigned metadata proof does not replace complete final AVB verification,
FEC checks, FDT/runtime validation or boot testing.

### Archive and digest preservation

The old vbmeta digest must match the original root and child metadata. The new
digest must agree between pinned `avbtool calculate_vbmeta_digest` and a bounded
independent calculation in root descriptor order, including its exact lowercase
hex and final LF. Digest calculation is separate from signature verification.

`scripts/target_files_archive_copy.py` streams every original member and
independently rereads every output member, checking full decoded sizes, CRCs,
SHA256 identities and DEFLATE termination. It preserves local and central
non-ZIP64 extras independently. ZIP framing, offsets, compression bytes and
mechanical flags may change; byte reproduction across runtimes is not claimed.
The receipt records Python and zlib versions and compression level 6.

Regular-file, single-link, nonsymlink-parent and inode-stability checks remain
active through final publication. JSON, archive and public-key selectors receive
header checks before generic hashing so a mistakenly selected private PEM is
rejected without reading its body. The copier requires a conservative complete
recompression bound plus 1 GiB reserve and rechecks space during output. Existing
public-verifier snapshot-space checks remain active. Failure retains any private
incomplete directory and cannot overwrite or publish a successful destination.

## Build metadata and output scope

`META/misc_info.txt` must select `ab_update=true`, `avb_enable=true` and
`avb_building_vbmeta_image=true`. `allow_non_ab` may be absent or `false`;
`boot_images` may be absent or exactly one `boot.img` token. Duplicate consumed
keys fail; unrelated repeated legacy keys are preserved.

The entire original build/signing recipe remains byte-for-byte unchanged. Do
not substitute public PEM paths for `avb_*_key_path` or partially update rollback
arguments: pinned releasetools consume them for private-key signing and image
regeneration. The output explicitly records
`original_build_metadata_preserved=true`, `signing_metadata_reconciled=false`
and `generic_resigning_supported=false`. The existing A/B/non-A/B recovery
two-step behavior is not altered.

The fresh directory contains `target-files.zip`, `receipt.json`, the original
request, public verification result, copy/readback report, native-digest evidence
and new inventory. The inventory names the immutable pre-publication staging
path; replay inventory at the published path before a later path-specific
consumer. The receipt binds the output ZIP by hash and size independently of
that path. Neither success nor a zero process exit makes an OTA or bootable ROM.

## Subsequent native gates

All eight logical images are retained. An existing ordinary super image may be
reused only after actual extraction proves that each logical image matches the
admitted manifest and reconciled archive. Otherwise, use the pinned ordinary
`build_super_image` path on fresh public input/output in the sole writer VM.
Require an actual output and valid complete LP metadata; the pinned CLI can exit
zero after skipping a missing image. Its direct-dict `force_non_sparse` argument
also does not reliably select nonsparse output. Use existing sparse reconstruction
and logical-partition inspection/extraction tools, with explicit identities and
the unchanged per-role, group and super budgets.

The six remaining FEC-content checks (`mi_ext`, `system`, `system_ext`, `product`,
`system_dlkm`, `vendor_dlkm`) remain required. Previous policy3 vendor/ODM FEC
proof applies only after rebinding their exact final identities. Complete
target-files, VINTF/APEX, snapshot, A/B and OTA validation remain separate work,
including explicitly selected OTA payload/container signing keys.

Do not substitute `sign_target_files_apks` or `add_img_to_target_files
--add_missing`: those paths can regenerate opaque images and APEX/care-map
metadata. See [delivery integration](target-files-delivery-integration.md) and
[source composition](target-files-source-composition.md) for the pinned build
context. Source-origin authentication, stored device rollback acceptance,
physical partition fit and hardware behavior remain unverified. No phone
operation is authorized by this tool or its success.

## Validation and derivation

```sh
python3 -B -m unittest tests.test_reconcile_signed_target_files \
  tests.test_target_files_archive_copy -v
python3 -m unittest discover -s tests -v
```

The original promotion's 72 focused tests used synthetic ZIPs, inert signatures
and mocked native operations. They cover receipt/manifest binding, unchanged
payload and metadata preservation, malformed archives, alias handling,
header-only rejection,
mutation races, disk limits and exclusive publication. Native Android builds,
real AVB verification and device tests are different evidence.

This promotion preserves the reviewed prototype's behavior while adapting its
imports and implementation-file paths to `scripts/`. The private development
record is
`reports/oem-policy-integration-20260829/boot-chain-next-check-v1/reconciliation-handoff-v1.json`
(`3fc7efae98710df6364cb214bdc994d2bda87d0c149866e44eb85f35e8e3c22f`).
Its cleared coordinator was `0f3e639fc7167243d480d38d4ebfde9391a53593ee4e293d607fe2399d5828fa`;
the streamed copier was `cd6b2526bf29fa246921ff62795d54fa91d18f9078f48c8652a279fd4d782926`.
The four existing pinned workspace dependencies and both public AVB contracts
are unchanged; their future changes require explicit compatibility review.

## DTBO correction checkpoint — September 2, 2026

Commit `db4d07cce161eb67be6b1ec2614501bbf1731eb0` adds the narrow DTBO proof and
alias normalization above, its negative tests, and the materializer's updated
copier pin. It does not change native source or output, signing roles, public
AVB/profile policies, the 548-file source baseline or historical freezes.

The actual **Package5 read-only inspection passes at 18:47:59 UTC**. Its
**10,997,962,405-byte** archive (`622073f36dd1c0f733f1ed1d09518380190a58a80f4615586c815430bd9768b4`)
was freshly hashed twice. The two 32 MiB DTBO members have identical complete
**1,495,111-byte payloads**, SHA-256
`ea20dfcbf78f80f5cda7d3ea964e711b96cd1dacfa3992ed7cd799f067349baa`, and pass the
strict unsigned metadata proof. The archive, image bodies and five changed
implementation/test files remain unchanged during inspection. No archive was
rewritten, no signing occurred, and no VM, phone, private key or local signing
configuration was accessed.

**258 focused offline tests pass** in 27.766 seconds. The root's independent
**4,508-test full offline suite passes** at **18:51:23 UTC**; all 585 tracked
files retain their bytes, types and nine-field stat records throughout the run.
The subsequent commit receipt binds the exact tested five-file diff. These
results do not establish an actual Package6 archive, signing, reconciliation,
complete AVB/VINTF/FEC/super validation, OTA or a bootable ROM. Fresh Package6
must supply its own archive, inventory, proof and all existing final gates.

The following ignored local evidence is relative to
`reports/avb-sha256-20260902/resume-build-20260902-v1/`. The original handoff's
pending full-suite/commit fields remain historical; the later root receipts
record those completed checks separately.

| Evidence | SHA-256 | Bytes |
| --- | --- | ---: |
| `final-avb/host-fix-v1/handoff.json` | `e70da3375244e7d498c9441d4dda334cb6c326b9599e84174fbd686d0d665336` | 7,533 |
| `final-avb/host-fix-v1/actual-package5-inspection-v1/proof.json` | `ed4ab52155ebe4ab347d9faea5c583c0e6d088206ce3b60e2362d44d8719e9fa` | 6,648 |
| `final-avb/host-fix-v1/actual-package5-inspection-v1/completion.json` | `4ade639118a83c1150de81fcf703512cc90e500a1be6aaaff40fb13315ba5016` | 6,686 |
| `final-avb/host-fix-v1/integrated-tests-v1/summary.json` | `f3045db2332ed8e0de1c1ead4ee5977aa99dd5444ab3878f302fcc6f4b2baec1` | 6,097 |
| `root-dtbo-host-validation-v1/actual-v1/summary.json` | `638511d410ff860821b634016e0281e696d824aa16d75928a20308f9274aa2ab` | 3,178 |
| `root-dtbo-commit-v1/completion.json` | `8fffc542b0d3596ee852887988bf6c4fb50fff7600d19f1718fa283d669393a1` | 923 |

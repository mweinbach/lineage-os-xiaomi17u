# Read-only target-files AVB input inventory

`scripts/target_files_avb_inventory.py` inventories a captured target-files ZIP
before a separate materialization and signing step. It does not extract,
rebuild, sign, repack or validate images. No real first-ROM target-files archive
has been admitted with this helper; the implementation tests use synthetic
archives and inert byte strings.

The helper uses the existing `config/nezha-avb-signing.json` and
`config/nezha-avb-image-set.json` loaders. Production callers cannot select a
different profile, recovery identity, role set or package budget. The existing
signer, verifier, construction gates and generated device tree are unchanged.

## Three distinct input roles

| Role | Required source | Inventory behavior |
| --- | --- | --- |
| 13 data images: `boot`, `dtbo`, `init_boot`, `mi_ext`, `odm`, `product`, `recovery`, `system`, `system_dlkm`, `system_ext`, `vendor`, `vendor_boot`, `vendor_dlkm` | Exact `IMAGES/<role>.img` ZIP entries | Stream and hash each entry; enforce its recorded file-byte budget. Recovery must match the contract's exact working76 image. Other hashes are observations, not image validation. |
| Two generated metadata images: `vbmeta`, `vbmeta_system` | Exact `IMAGES/<role>.img` ZIP entries | Record these construction outputs separately. They are not inputs to the Mac signer, which creates the final metadata images. |
| Two retained firmware inputs: `countrycode`, `pvmfw` | Explicit external manifest and real files | Use the existing signing-input schema, restricted to these two original identities and the pinned factory extraction receipt. No implicit firmware paths or ZIP fallback. |

The reviewed A/B list contains the 13 data roles and the two vbmeta roles. The
signer's 15-input list instead contains the 13 data roles and two retained raw
firmware roles. Inventorying countrycode/pvmfw does not add them to an OTA or
flash list.

`BOOTABLE_IMAGES/<role>.img` and `PREBUILT_IMAGES/<role>.img`, when present, are
hashed separately. Their records say whether their complete bytes match the
corresponding final image. Differences are permitted and remain visible; an
alias never fills a missing `IMAGES` role. This matters when a later tool prefers
a boot/prebuilt alias over the final image.

## API and CLI

```python
inspect_target_files(
    target_files: Path,
    expected_identity: dict,  # exactly sha256 and size_bytes from the capture
    *,
    retained_input_manifest: Path | None = None,
    expected_retained_manifest_sha256: str | None = None,
) -> dict
```

The external archive digest and size are mandatory. The optional manifest and
its separately recorded digest must be supplied together. This is the only CLI
operation:

```sh
python3 -B scripts/target_files_avb_inventory.py inspect \
  --target-files "$CAPTURED_TARGET_FILES" \
  --expected-sha256 "$CAPTURED_TARGET_FILES_SHA256" \
  --expected-size-bytes "$CAPTURED_TARGET_FILES_SIZE" \
  --retained-input-manifest "$RETAINED_TWO_IMAGE_MANIFEST" \
  --expected-retained-manifest-sha256 "$RETAINED_MANIFEST_SHA256" \
  --output "$FRESH_PRIVATE_INVENTORY_REPORT"
```

These variables are placeholders for actual captured inputs, not supplied
artifacts. The report's parent directory must already exist; the output file is
created exclusively with mode 0600 and is never overwritten. Keep manifests and
reports under ignored private locations because they contain local paths.

The retained manifest uses schema 1 from `avb_signing.load_input`, including its
real signing-contract SHA256 and an `artifact_set_id`. Its `images` dictionary
must contain exactly countrycode/pvmfw, with paths and their contract-exact
SHA256/size pairs. Its sole `source_records` entry must identify the factory
extraction receipt already pinned by `research/factory-firmware-validation.json`.
The helper reopens and hashes those files; supplying a JSON claim alone is
insufficient. It does not open the local recovery configuration, select tools,
resolve a private key or execute a native process.

The API returns a report with `status: complete` only when both the ZIP inventory
and the two retained inputs are present and consistent. Without that manifest,
`complete_zip_role_inventory` can be true while `complete_input_inventory` stays
false and `missing_retained_inputs` names the unresolved roles. Unsafe or
inconsistent inputs produce a blocked report. The CLI exits 0 only for a
complete inventory and 2 for a blocked inventory or an unsafe output path.

Every ZIP location is explicitly labeled
`zip-member-not-signing-filesystem-input`. This report is not a ready-to-run
signing manifest; independent materialization must produce actual files first.

## Metadata and archive bounds

The required metadata entries are `META/misc_info.txt`,
`META/ab_partitions.txt`, `META/dynamic_partitions_info.txt` and
`META/vbmeta_digest.txt`. The helper requires the exact 15 A/B roles, the exact
eight logical partition roles in both dynamic lists, and the existing AVB and
dynamic-partition enablement declarations. Duplicate partition-list roles or
duplicate consumed dictionary keys are rejected. Unrelated dictionary fields
are hashed without interpretation: pinned Android dump macros can legitimately
repeat unrelated settings. Text parsing uses literal LF and ASCII whitespace.
The recorded vbmeta digest has its text syntax checked, but is not recomputed.

Present APK/APEX key lists, APEX metadata, care-map records, OTA information and
known OTA public-key records are hashed with bounded reads. Their absence does
not establish or disprove signature validity; they are handoff observations.
These records cannot prove that projected metadata matches an opaque partition.

The ZIP is read through the existing stable, nonsymlink, singly linked regular
file reader. Its expected size and native ZIP prefix are checked before hashing
the archive. A bounded end-record scan supports ordinary single-disk ZIP and
fixed-size ZIP64 end records. The central directory is limited to 32 MiB and
250,000 actual framed entries before `ZipFile` builds its in-memory index. The
archive and total declared uncompressed contents are each limited to 128 GiB;
names are limited to 4,096 bytes/characters. Selected metadata is limited to
1 MiB per entry, while selected image reads use the existing per-role budgets
and a finite aggregate budget covering the three image locations.

Duplicate names, traversal, noncanonical paths, selected case aliases and
selected paths beneath file/symlink entries are rejected. Selected entries must
be regular files with stored or deflate compression, consistent local/central
header flags, CRC/size fields and data descriptors. Selected DEFLATE streams
also receive a bounded independent end-marker/length check: the standard ZIP
reader alone can accept truncated streams or clip extra decoded bytes to the
declared size. Stored entries must have equal compressed/uncompressed sizes.
All selected reads must finish with correct sizes and CRCs. Ordinary
unselected Android symlink entries remain untouched; no link target is read or
followed. Unselected file bodies are not decoded or claimed valid.

The entire archive is hashed before and after inspection, with descriptor and
path stability checked by the existing reader. Retained files and their
provenance/manifest records are rechecked as well. An input change prevents a
complete result. Prepending executables, concatenating ZIPs, multipart ZIPs and
ZIP64 extensible end records are outside this deliberately narrow reader.

## What a complete inventory does not establish

All image-format, signature, AVB-chain, FEC-payload, source-provenance, VINTF,
physical-fit, runtime, ROM-readiness and phone-admission fields remain false.
File-byte budget checks do not establish an image's filesystem extent, actual
partition geometry or signed parent chain. The current policy-image leaves have
their own derivation evidence; this helper does not replace it.

After actual target-files construction, preserve that archive and independently
materialize the inventoried inputs for the existing Mac signer. Its 17-image
output still needs complete intended-public-key verification. A later reviewed
step must reconcile changed signed images, aliases and vbmeta metadata into a
new target-files artifact and prove its logical images match any delivered
super image. Ordinary `sign_target_files_apks` discards/rebuilds image entries;
it is not an approved shortcut for metadata-only projections of retained opaque
partitions. APK/APEX, OTA, rollback, live partition fit and authorized first-boot
checks remain separate work.

Focused offline validation:

```sh
python3 -B -m unittest discover -s tests -p test_target_files_avb_inventory.py -v
```

These tests cover the reader and its failure boundaries. They are not native
Android builds, cryptographic verification or physical-device evidence.

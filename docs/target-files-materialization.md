# Materialize target-files inputs for host AVB signing

`scripts/materialize_target_files_inputs.py` copies the 13 final data images
from an explicitly selected target-files ZIP and the two retained factory
inputs into a fresh private directory. It produces the existing 15-input
[host signing manifest](avb-signing.md), with exact image and provenance
identities. This is byte materialization, not image validation or signing.
The original archive, retained inputs and existing pinned helpers are unchanged.

## Required actual inputs

Preserve the completed native target-files archive and independently record its
SHA256 and byte length. Run the [read-only inventory](target-files-avb-inventory.md)
at the archive's final host path, with the explicit two-input retained manifest.
The materializer replays that inventory and requires an exact complete match,
including the archive path. Moving an archive requires a fresh inventory at its
new path; editing a prior inventory is not an admissible substitute.

| Input | Requirement |
| --- | --- |
| Target-files ZIP | Explicit path, SHA256 and byte length; unchanged completed archive |
| Inventory JSON | Exact digest and a complete replay with both ZIP and retained inputs |
| Retained-input manifest | Exact digest; existing signing schema restricted to original `countrycode` and `pvmfw`, with their pinned factory extraction receipt |
| Artifact-set identifier | Explicit descriptive identifier, not an automatically selected latest build |
| Output directory | New child of ignored `artifacts/avb/nezha/`; existing nonsymlink parents |
| Additional source records | Optional explicit JSON path, SHA256 and byte length for each build, transfer or derivation record |

The copied ZIP roles are `boot`, `dtbo`, `init_boot`, `mi_ext`, `odm`, `product`,
`recovery`, `system`, `system_dlkm`, `system_ext`, `vendor`, `vendor_boot` and
`vendor_dlkm`. Each must come from its literal `IMAGES/<role>.img` entry.
`BOOTABLE_IMAGES` and `PREBUILT_IMAGES` aliases never supply a missing role.
The inventory's generated `vbmeta` and `vbmeta_system` images are not copied:
the signer creates their final replacements. The retained firmware roles are
copied separately from the manifest's real files, never from ZIP fallbacks.

The existing signing contract fixes all role budgets, the exact working76
recovery identity and both retained firmware identities. Materialization does
not change the A/B partition list or imply that retained firmware should be
flashed. Normal Android enforcement, the selected recovery exception and the
4 KiB build baseline remain unchanged.

## Invocation and output

```sh
python3 -B scripts/materialize_target_files_inputs.py \
  --target-files "$ACTUAL_TARGET_FILES" \
  --expected-sha256 "$ACTUAL_TARGET_FILES_SHA256" \
  --expected-size-bytes "$ACTUAL_TARGET_FILES_BYTES" \
  --inventory "$ACTUAL_COMPLETE_INVENTORY" \
  --expected-inventory-sha256 "$ACTUAL_INVENTORY_SHA256" \
  --retained-input-manifest "$ACTUAL_RETAINED_MANIFEST" \
  --expected-retained-manifest-sha256 "$ACTUAL_RETAINED_MANIFEST_SHA256" \
  --artifact-set-id "$EXPLICIT_ARTIFACT_SET_ID" \
  --output-dir "$FRESH_PRIVATE_INPUT_DIRECTORY" \
  --source-record "$ACTUAL_SOURCE_RECORD" "$ACTUAL_SOURCE_RECORD_SHA256" "$ACTUAL_SOURCE_RECORD_BYTES"
```

These variables are placeholders for actual selected inputs. Omit the optional
`--source-record` argument when there is no additional record, or repeat it for
up to 61 records. Each record must be a strict JSON object, have a `.json`
filename and fit within 1 MiB. This preserves the signer's maximum of 64 ordered
source records after adding three generated entries. Oversized production logs
or receipts need a separately reviewed, bounded linkage record; the helper does
not truncate them or authenticate the claims inside them. Keep all inputs,
outputs and captured command results in ignored private locations.

The API is `materialize(target_files, expected_archive, inventory_record,
expected_inventory_sha256, retained_manifest, expected_retained_sha256,
output_dir, artifact_set_id, *, source_records=())`. Archive identities contain
exactly `sha256` and `size_bytes`; additional source records also contain `path`.

The new directory contains:

- `images/`: exactly the 15 copied input images, with canonical role filenames;
- `provenance/`: unchanged inventory, retained manifest, factory extraction
  receipt and any selected additional JSON records;
- `materialization.json`: archive/member, retained-input, implementation and
  copied-file identities; source claims remain hash-bound observations;
- `input-manifest.json`: the existing `nezha-host-avb-signing-v1` schema with
  relative image and provenance paths;
- `receipt.json`: the independently verified byte checkpoint described below.

The manifest's ordered source records are `materialization.json`, the inventory,
the factory extraction receipt and then any additional records. The retained
manifest is separately copied and bound by the derivation. The derivation does
not include the later input-manifest digest, avoiding a cyclic hash dependency.

## Publication and failure boundaries

The helper uses the existing stable, nonsymlink, single-link input readers,
strict ZIP envelope and complete DEFLATE checks. The exact replay is followed
by guarded streaming extraction, size/CRC/SHA256 comparisons and complete
readbacks of all 15 images and every metadata file. Original inputs and pinned
implementations are rehashed before publication. JSON and ZIP header guards
reject a misplaced PEM before reading its body. The helper never opens local
signing configuration or resolves a private key.

Output directories are mode 0700 and files are mode 0600. Writes use fresh
exclusive files under a private incomplete sibling directory. The finite
output budget includes all 15 images, the actual copied JSON bytes and three
1 MiB generated-record allowances, plus a 1 GiB free-space reserve. Space is
checked at file boundaries, around metadata writes and at least every 64 MiB
of streamed image output. These are sampled checks, not a filesystem quota or
a reservation against other writers.

Every output file is flushed and synchronized, including the two retained raw
copies. Image/provenance directories and the staging root are synchronized
before the existing exclusive atomic publication. The published directory and
its parent are synchronized afterward, with final path, inode, mode and input
state checks. Unsupported or failed synchronization is an error; there is no
overwrite, non-atomic publication or synchronization fallback.

`receipt.json` deliberately records `status: verified-before-publication`,
`receipt_scope: prepublication-byte-verification` and
`publication_durability_claimed: false`. It cannot prove the later rename or
directory synchronization succeeded. Only a successful API return or CLI exit
0 provides `status: materialized-inputs-only`, exact receipt/manifest identities
and the completed publication checks. Preserve that returned result privately
along with the output bundle before using it downstream.

On failure, the CLI exits 2 and emits a bounded blocked result without success
JSON on stdout. A failure before rename retains any incomplete private sibling;
a failure after rename retains the canonical output and its checkpoint receipt.
Neither case supplies a successful publication result. Do not infer success
from directory or receipt existence, overwrite a failed attempt, or silently
reuse its destination. Review the failure and select a fresh output path.

## Signing and downstream admission

Pass the successfully returned input-manifest path and digest to the existing
signer's `plan` and `prepare` operations. Preparation normalizes its input
manifest to absolute paths and writes it beside `preparation.json`. That
normalized manifest has a different digest from this materializer's relative
manifest. The later [signed target-files reconciler](signed-target-files-reconciliation.md)
uses the preparation's adjacent normalized manifest and its bound digest;
do not substitute the earlier materializer digest. Ordered provenance and
image identities remain intact across normalization.

Materialization does not run native commands, reconstruct images, sign AVB,
re-sign OEM APKs or APEXes, repack the ZIP, access a guest or alter Android output.
Image-format, signature, complete-chain, FEC-content, source-origin, VINTF,
physical-fit, runtime and complete-ROM readiness remain false. In particular,
preserve the existing kernel source-origin warning and separate factory evidence.

Final-package META/XML/APEX/APK validation and image-to-tree policy/context
comparisons are outside this 15-input operation. The six remaining FEC-content
checks, exact vendor/ODM proof rebinding, all eight super extraction equalities,
partition/group/super budgets, AVB rollback constraints and OTA validation still
require their actual artifacts. No result authorizes a phone operation.

## Validation and derivation

```sh
python3 -B -m unittest discover -s tests -p test_materialize_target_files_inputs.py -v
python3 -m unittest discover -s tests -v
```

The focused tests use synthetic ZIPs and inert bytes. They exercise the real
bounded readers and publication helpers, malformed and changing inputs,
signer-schema normalization, provenance limits, full readbacks, private modes,
space loss during streams and metadata writes, synchronization failures and
exclusive publication. They cannot establish a native build, real image
validation or device behavior.

The helper promotes the reviewed local materializer draft from
`reports/oem-policy-integration-20260829/policy3-avb-next-gate-v1/materializer-draft-v1/`
(implementation SHA256
`ffc7e3fba4d888605fd9c5cce1eba68325e059e3b9b08366e9335f2f26e2fb40`).
The promotion adapts imports and implementation paths and adds guarded JSON
snapshots, private-mode checks, finite stream-space checks and explicit durable
publication. The existing inventory, signer, verifier, archive copier, exclusive
publisher and two public contracts remain unchanged and pinned. Implementation
promotion and offline tests are not evidence that an actual ROM archive has
been materialized with this tool.

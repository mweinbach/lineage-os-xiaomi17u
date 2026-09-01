# Final APK inventory preparation

[`scripts/final_apk_projection.py`](../scripts/final_apk_projection.py) implements
the record and payload join needed before the
`final-installed-apk-inventory-and-strict-treble-labeling` gate in
[`config/nezha-rom-construction.json`](../config/nezha-rom-construction.json).
It is read-only preparation, not a package admission or native checker runner.
Its only supported context is Nezha `lineage_nezha`, `bka`, `bp4a`, `user`, with
the selected 4096-byte baseline. No source, Android output, original image,
proprietary input or device is changed.

The implementation follows the audited
[`treble-plan/plan.json`](../reports/remaining-policy-contexts-20260829/treble-plan/plan.json),
especially `inventory_projection`, `factory_totals`, `native_entry_points` and
`policy_and_context_prerequisites`. It uses the original receipt formats from
[`erofs_inventory.py`](../scripts/erofs_inventory.py) and the confined, bounded,
no-follow reader from
[`target_files_metadata.py`](../scripts/target_files_metadata.py). It adds no VM,
native process, extraction, package, signing or filesystem publication framework.

## What the join checks

The input supplies a normalized vector of graph-selected platform install paths,
separate byte-bound graph/source records, all eight complete serialized EROFS
inventories and scans, and exact capture receipts with their local payloads.
The tool checks:

- Each scan binds the supplied inventory's full bytes and entry count. The
  inventory and capture records select the same image hash and byte count.
  Captures also bind the exact inventory and scan-receipt hashes and the same
  recorded EROFS tool identity. Recorded image and executable paths are never
  opened by this tool.
- Inventories contain the root and each entry's directory ancestry, unique
  paths, consistent inode types and no aliased directory inode. General EROFS
  names such as `/bin/[` remain legal; only projected APK paths must also be
  safe as native whitespace-delimited list entries.
- Every `.apk`-suffixed inventory entry, including exclusions, is a captured
  regular file. Its inode matches the inventory, its exact numeric capture
  output is retained, and its full payload hash and size match. Noncanonical
  `.APK` spellings and nonregular APK entries fail instead of disappearing.
- All rows in every supplied capture receipt are rehashed, including ancillary
  non-APK files. Authentic empty ancillary files are allowed; empty APKs fail.
  Permission modes use the producer's `0644` form, not a full `st_mode` value.
  A receipt's `total_bytes` must equal the sum of all its rows.
- The platform `app`/`priv-app` paths in the inventories exactly equal the
  supplied graph vector. Neither stale image APKs nor selected-but-absent APKs
  can be dropped. The combined platform scope must be nonempty. Deeper paths
  accepted by Make's `%` filter are retained; this does not substitute Soong's
  narrower path selection for the actual generated Make rule.
- The complete vendor and ODM APK path sets must retain all 19 factory paths
  recorded by the audited plan: eight vendor apps, two ODM apps, eight vendor
  overlay-location APKs and one ODM overlay-location APK. Historical image
  hashes and inode numbers are not imposed on a subsequent derived image.
  Actual image identity and derivation still require package admission.
- Duplicate APK basenames and equal-content files remain separate rows. A
  `basename_collisions` map reports every occurrence; package names and their
  collisions remain unverified until native `aapt2` evidence exists.

Input selectors must stay beneath one real input root. Symlink files or parents,
hardlinks, nonregular inputs, repeated evidence paths and physical file aliases
are refused. Reads stream payload hashes, and every input is reread and rehashed
before returning a result. SHA256 selectors are required; duplicate JSON keys,
non-finite JSON values, unknown fields, boolean counts and changed bytes fail.
The CLI emits no partial result on refusal.

## Eight inventories and five checker partitions

All eight logical partition keys are mandatory. An absent partition cannot be
treated as an empty image. A structurally complete supplied inventory with no
APK entries permits a zero APK count; that is still a claim about the supplied
record, not proof that a native scan of the admitted image was executed.

| Partition scope | Native APK selection | Inventory requirement |
| --- | --- | --- |
| `system`, `system_ext`, `product` | `app` and `priv-app`; exact supplied platform graph set | Full inventory, exact captures and explicit exclusions |
| `vendor`, `odm` | Retained eight and two factory app paths | All 19 factory APK paths, including nine explicitly excluded overlays |
| `mi_ext`, `system_dlkm`, `vendor_dlkm` | Outside this pinned native checker's partition scope | Full inventory even when empty of APKs; every APK must be captured and explicitly excluded |

Exclusions are per image path, never broad partition exemptions. The only
accepted reason is the one derived from its location:
`overlay-path-outside-app-scope`, `framework-path-outside-app-scope`,
`other-path-outside-app-scope`, or, for the three extra partitions,
`outside-native-partition-scope`. An in-scope APK cannot be excluded. Duplicate,
unused, nonexistent or incorrect exclusions fail. An overlay manifest does not
by itself exclude an APK installed under `app` or `priv-app`.

The extra-partition boundary describes this captured native checker and its
Make inputs. It makes no assertion that PackageManager ignores such APKs or
that another integration cannot expose them. APKs inside APEX containers are
also not discovered by an outer EROFS inventory. Separate APEX-content and
runtime package-scan accounting remains mandatory. Consequently
`complete_installed_apk_inventory_verified` and `apex_contained_apks_verified`
always remain false, even when all eight serialized inventories join.

## Input contract and invocation

The request has exactly these top-level fields:

| Field | Required value or role |
| --- | --- |
| `schema_version` | Integer `1` |
| `operation` | `prepare-nezha-final-apk-projection-v1` |
| `context` | Exactly the script's Nezha `CONTEXT` object |
| `package_binding` | `null`; non-null package admissions are not implemented here |
| `graph.selected_platform_install_paths` | Nonempty, unique normalized `/system/...`, `/system_ext/...`, `/product/...` APK paths under `app` or `priv-app` |
| `graph.source_records` | One to 32 relative file references to retained graph/query/source evidence; bytes are checked but the producer and selection semantics are not authenticated |
| `partitions` | Exactly `system`, `system_ext`, `product`, `vendor`, `odm`, `mi_ext`, `system_dlkm`, `vendor_dlkm` |

Each partition selects exactly `image`, `image_root`, `inventory`, `scan_receipt`,
`captures` and `exclusions`. `image` is `{sha256, size_bytes}`. Every file
reference is `{path, sha256, size_bytes}`, with a safe relative path under the
input root. `inventory` and `scan_receipt` must keep their original adjacent
`inventory.json` and `receipt.json` filenames. Every capture reference selects
its original `receipt.json`; original `files/0001` payloads are resolved relative
to that receipt, not renamed. No original receipt is edited to fit this schema.

`image_root` must be `/`, except that `system` may explicitly select `/system`.
The selected root must be an inventoried directory. APKs outside it fail. The
mapping strips only that declared image root and prefixes the partition once;
it does not guess whether a second `/system` should be removed. Exclusions are
objects with exactly `image_path` and `reason`.

After real inputs have been acquired, the read-only entrypoint is:

```sh
python3 scripts/final_apk_projection.py \
  --input-root "$apk_input_root" \
  --request request.json \
  --expected-sha256 "$apk_request_sha256"
```

Those variables must select actual locally retained inputs and the independently
recorded request hash. There is no committed runnable Package2 request or
placeholder success receipt. Keep any stdout capture under an ignored private
evidence directory. Exit zero means only that supplied records and payload
bytes joined under this contract.

Limits are explicit: eight inventories of at most 100,000 entries each, at most
32,768 APK rows overall, 128 capture batches per partition, 4096 files per batch,
512 MiB per file, 2 GiB per batch and 16 GiB of payloads overall. Each inventory
is at most 64 MiB, other JSON records 16 MiB, a request 8 MiB, each graph record
64 MiB and all metadata 256 MiB. The selected image identity is bounded at
16 GiB without reading image bytes. These are refusal limits, not observed
Package2 sizes. They do not raise the existing EROFS producer's limits.

## What remains before native and boot claims

The output is deliberately `supplied-record-and-payload-join-only`. It reports
missing admission roles and leaves package, graph producer, scan/capture
producer, tool, signature, permission, effective MAC/seapp label, native Treble,
APEX-content and ROM-readiness claims false. Hashing an arbitrary supplied graph
record does not prove the caller's normalized path vector came from the active
generated rule. Hashing an EROFS receipt does not authenticate its execution or
read the selected image. These cannot become pass flags merely by relabeling
the JSON output.

After successful actual Package2 inputs exist, the remaining work is concrete:

1. Bind the actual successful package, source and generated graph identity;
   capture the current selected Make rule and installed-artifact evidence.
   Acquire the eight exact final images through the existing package workflow.
   Preserve any source-identity change, including later Camera adoption, as a
   successor package that requires fresh consumer admission.
2. Use existing `erofs_inventory.py scan` for each admitted image and `capture`
   with explicit `--path` selections for every inventoried APK, including
   exclusions. Preserve the original scan/capture receipts and numeric payloads.
   Join the real image hashes and graph selection to this preparation separately;
   do not use unchanged factory inventory identities for new derived images.
3. Materialize an independently reviewed read-only native input layout that
   preserves each original APK basename. `planned_native_lists` contain proposed
   `/nezha-final-apk-projection/<partition>/...` paths only. They do not exist
   merely because this tool succeeded. Passing numeric `files/0001` directly to
   the checker would lose original APK names in diagnostics and basename
   identity. Strict seapp matching uses package names; this workflow prohibits
   optional allowlist exemptions. No list file, copy, symlink, hardlink or mount
   is created here.
4. Run the pinned `aapt2 dump packagename` on the actual APK payloads with exact
   exit/stdout/stderr evidence, requiring one nonempty package token. Keep
   duplicate names and cross-partition occurrences. Complete APEX and other
   runtime scan-scope accounting instead of treating these as empty.
5. Run the existing strict `treble_labeling_tests` with the current framework-only
   `precompiled_sepolicy_without_vendor`, exact factory-aware combined policy,
   three current platform seapp files, retained vendor/ODM seapp and file-context
   inputs, and pinned `aapt2`. Bind these bytes to the same admitted images.
   Preserve canonical context basenames. Do not enable warning mode, tracking
   exemptions or a debuggable bypass. The ordinary build target can succeed by
   skipping absent opaque-vendor inputs; its timestamp is not native pass proof.
6. Complete final APK signature, same-partition privileged-permission and
   effective signer-to-seinfo/seapp checks separately. The
   [factory Camera guide](factory-camera-apk.md) and
   [pinned resolver review](../reports/factory-camera-apk-20260829/resolver-review-v1/README.md)
   describe those boundaries. Native Treble labeling does not validate Android
   permission grants, actual runtime label selection, installation or hardware.

The focused offline test command is
`python3 -B -m unittest tests.test_final_apk_projection -v`. Its fixtures use
inert bytes, original producer-shaped receipts and temporary local files; native
process and network creation are blocked. Tests cover all eight partitions,
the exact factory path set, explicit exclusions, strict set equality, root
mapping, original basenames, empty ancillary files, hash/receipt mismatches,
unsafe paths, input aliases, replacement during validation and unchanged-input
readback. This test suite is not an Android build or device test.

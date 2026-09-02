# Metadata for retained vendor and ODM images

## September 2, 2026: Package3 checksum-hook failure

The native Package3 attempt exits 1 at **02:09:50 UTC**, followed by host exit 1
at **02:14:06 UTC**. The target-files-directory action reaches this hook and fails
with `sha256sum: Unknown option 'strict'`. The build-selected command resolves
to the pinned Toybox binary, which does not accept that flag. The artifact
postcheck does not run; the complete result/stdout/stderr readback preserves the
failure. Later parallel Metalava output is not the failed action.

A read-only native probe verifies all **14 expected outcomes** for the actual
tool. Canonical lowercase 64-hex digest validation followed by `sha256sum -c`
accepts the correct verifier and rejects wrong bytes, malformed digests, missing
files and checksum-command failure. The first probe's incorrect `paths.go`
provenance lookup remains preserved; the successful probe uses `path.go`.

The exact rendered 0023 guard separately passes **15 expected-outcome smoke
cases** under actual Bash and pinned Toybox. Only the matching digest reaches
the test sentinel. Wrong/malformed digests, newline/quote/substitution/backtick
injection, missing files and checker failure exit 1 without that sentinel. This
does not execute Make/Kati, the metadata installer or an Android build.

[Patch 0023](../patches/evolution/0023-portable-target-files-metadata-checksum.patch)
is an additive prepared correction; patch 0009 and its source history are not
rewritten. **No replacement source has been adopted in the VM.** The current
metadata bundle checks the complete Makefile identity (`bf6e0668…`), so its
runtime and source composition also require refreshed reviewed inputs. Fresh
source, configuration and metadata receipts and a successful packaging retry remain
separate work. The [failure checkpoint](../research/workspace-integration.json)
binds the actual failed result and probe. The earlier integration specification
below retains its original scope and pinned source identities.

Nezha currently selects opaque factory vendor and ODM images. The pinned
Android target-files recipe copies those images into `IMAGES/` but does not
populate their `VENDOR/` and `ODM/` metadata trees. Releasetools needs genuine
properties, VINTF XML and complete APEX packages from those trees. Missing
directories can prevent property loading or cause Treble compatibility work
to be skipped.

The [metadata profile](../config/nezha-target-files-metadata.json),
[projection tool](../scripts/target_files_metadata.py) and
[patch 0009](../patches/evolution/0009-prebuilt-target-files-metadata.patch)
provide an explicit content-only path. They preserve original metadata bytes
and original image bytes. They do not produce source-built vendor/ODM images,
complete filesystem trees, filesystem configuration files or an APK inventory.
No readiness or device-operation authorization changes.

## Exact input closure

All required inputs were already captured from the admitted factory archive
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
No new phone collection or image extraction was necessary for this slice.

| Category | Vendor | ODM | Total bytes |
| --- | ---: | ---: | ---: |
| Properties and property imports | 2 | 22 | 46,817 |
| VINTF XML | 141 | 37 | 65,163 |
| Complete APEX packages | 3 | 0 | 6,348,800 |
| Total | 146 | 59 | 6,460,780 |

The full path inventories contain 3,910 vendor entries and 3,059 ODM entries.
Their hashes, inventory-receipt hashes and five capture-receipt hashes are
pinned in the public profile. Each capture binds the original image, inventory,
path, inode number, content SHA256, byte count and successful readback. The
projection checks the entire selected path set against the full inventories;
it does not assume that a convenient subset is complete.

The old inventories record path, inode number and type. They do **not** provide
complete inode metadata or prove a filesystem rebuild preserves ownership,
permissions, labels, capabilities, timestamps or hardlinks. That is the separate
[EROFS metadata workflow](../tools/erofs-metadata/README.md).

The admitted image pair is:

| Partition | SHA256 | Bytes |
| --- | --- | ---: |
| Vendor | `c9c2a03b61cd7c96466f09ffebf723382f430fd1389b1b73186270f3e15dfb20` | 959,709,184 |
| ODM | `4a269421a596c1eb1d90c982ef5497591ed1091e424a21bb9e7a83cf1a943ff5` | 4,767,621,120 |

The real nested vendor property file remains
`VENDOR/odm_dlkm/etc/build.prop`. There is no invented `ODM_DLKM` partition.
ODM's two literal import statements and all 21 matching physical variants
are preserved. Their runtime selectors are not inferred or resolved. The
closure checker rejects absent import targets and cycles.

Shipping API `36` is evidenced by the unchanged ODM property file. Vendor
provides board API `202504` but no `ro.product.first_api_level`. No vendor
assignment is fabricated. The three complete vendor APEX packages include the
current factory Wi-Fi package, SHA256
`b76fe0135990383d5e635d4d53ac19ea172e0024ff5e72b0b70ba990a5ecbc2d`.
Preserving package bytes does not authenticate their signer or prove activation.

## Native source integration

The [new source contract](../patches/evolution/target-files-metadata.json)
extends the source composition explicitly through patches 0005, 0006, 0007,
0008 and 0009. `compose_sources()` validates the ordered patches, original
contracts, transition continuity and full final identities of nine source
files. It applies no patches and does not audit all 1,179 projects.

| Source | Required final SHA256 |
| --- | --- |
| `build/make/core/Makefile` | `af8af76a36d6d2303dba471545bc2e36e15347211d9c96a4145a1ea3c6351d8b` |
| `build/make/tools/releasetools/common.py` | `66c76097fafb6d4422e617b232babc1fc9f5da3d5e8f0d52d925c8841104792d` |
| `build/make/tools/releasetools/add_img_to_target_files.py` | `ef2e4014238ad323e8157a3bf80190d1795f01b6dd0c087b5e8c2cc167a43c51` |

Patch 0009 starts from the exact core produced by 0007. Its hook runs inside
the ordinary target-files directory recipe, immediately before `AddImages`
loads properties. All bundle files and both installed images are ordinary
target dependencies. No `required`-only module, side-effect stamp, `nodeps`
target or alternative image recipe is used.

Selection requires the actual Nezha device, both opaque prebuilt images and
the dedicated A/B mode. The selector, externally reviewed receipt digest,
verifier digest, fixed bundle path and dependency list become Kati read-only.
The three selectors are expanded and frozen before the guard, including its
unselected branch, so a later recursive alias cannot change selection. The
internal bundle path and dependency list override command-line assignments.
The recipe verifies the self-contained Python verifier's SHA256 **before
executing it**, then invokes isolated Python with user-site imports and bytecode
writes disabled. The expected receipt digest must come from reviewed device
admission; reading a digest from the same unverified bundle is not admission.

The verifier checks the images already copied into `IMAGES/`, the complete
metadata bundle and the actual composed source files. The existing `META`
mode must have present, empty `building_vendor_image` and `building_odm_image`
values, A/B enabled and VINTF enforcement enabled. A literal `false` value is
not equivalent to an empty Make variable in this pinned build. Both kernel
VINTF metadata files must be present and nonempty.

The native recipe resolves only the existing top-level target-files directory
to its physical path at execution time. This supports the builder's reviewed
`OUT_DIR` symlink alias without relaxing the tool's checks on internal metadata,
image and bundle paths. A missing output root fails canonicalization.

Only new `VENDOR/`, `ODM/` and `META/nezha_target_files_metadata.json` entries
are published. Existing paths, symlink ancestors, changed files, unlisted
bundle entries and mismatched images fail. Directory descriptors anchor
exclusive atomic publication; the report is staged before publication.
Final output hashes and inventories are checked, and rollback removes only
published names still identifying this invocation's inodes. The source images
are read-only inputs throughout. Existing `find` and `soong_zip -d` behavior
retains the real directory entries, including `VENDOR/`, in the eventual ZIP.

The older recovery and mi_ext contracts are unchanged. They intentionally
reject this new source composition until their explicit selection path is
extended, and their bundles, generated includes and device admission are
regenerated. Do not edit historical contracts or replace working76. This
authored hook has not been installed into the active Android source by this
change.

## Reproduction and evidence

Staging creates a new private bundle and streams both original image hashes.
It accepts the workspace as the root of the exact private input paths recorded
in the profile. Images remain external and are not copied into the bundle.

```sh
python3 scripts/target_files_metadata.py plan
python3 scripts/target_files_metadata.py stage \
  --inputs-root /path/to/workspace \
  --vendor-image /private/path/vendor_a.img \
  --odm-image /private/path/odm_a.img \
  --output /private/new-metadata-bundle
python3 scripts/target_files_metadata.py verify \
  --bundle /private/new-metadata-bundle \
  --expected-receipt REVIEWED_RECEIPT_SHA256 \
  --source-tree /path/to/prepared/composed/source \
  --vendor-image /private/path/vendor_a.img \
  --odm-image /private/path/odm_a.img
python3 scripts/target_files_metadata.py selection \
  --bundle /private/new-metadata-bundle \
  --expected-receipt REVIEWED_RECEIPT_SHA256
```

The selection command prints only the three explicit metadata variables.
Integrating that exact output requires the device generator's normal reviewed
capability path; it does not change ROM construction or verification gates.
The native hook uses the canonical private path
`vendor/xiaomi/nezha-target-files-metadata`.

The August 29 host bundle is
`artifacts/target-files-metadata/nezha-factory-20260829-v4`. Its 188,875-byte
receipt has SHA256
`f2a88ccbee8e03043dceddfc1b48abc15e469b5e886a3f227e1957215846f90c`.
The 205 metadata files total 6,460,780 bytes; 227 bundled files additionally
retain the full inventories, original capture receipts and public controls.
Both original images were streamed and rechecked during staging. Isolated
host verification also checked the images, bundle and all nine full files in
the prepared source slice. That slice is not a complete source checkout, and
this is not an Android build result.

The ignored authoring evidence is under
`reports/oem-policy-integration-20260829/target-files-metadata-authoring/`.
The independent 205-file input audit is under
`reports/oem-policy-integration-20260829/target-files-metadata-input-audit/`.
Synthetic independent review and rejected cases remain under
`reports/oem-policy-integration-20260829/target-files-metadata-review/`.
The first staging attempt correctly rejected a path character before any
bundle was published; the reviewed path validator now distinguishes canonical
unselected inventory names such as `/bin/[` from Make-safe selected paths,
including the original OEM VINTF filename containing `@`.

The focused offline suite currently passes **45 tests with zero skips**.
It exercises original-byte preservation, deterministic staging, source/image
binding, real nested partition paths, property imports, untrusted receipts,
changed inputs, duplicate and missing entries, symlink/hardlink rejection,
publication failures, final readback and safe rollback. These tests use inert
fixtures and no device, network or native build processes.

## Remaining gates

This projection is not complete target-files or VINTF evidence. Before native
adoption and final packaging:

- Select the new source composition through recovery, mi_ext and generated
  device admission; preserve every existing receipt and recovery image.
- Run native Kati/configuration checks and the ordinary target-files recipe
  after its complete input closure and construction capability are reviewed.
  `target-files-dir` and `target-files-package` remain blocked today; this
  hook does not authorize bypassing that gate.
- Complete the framework XML and APEX inventory, materialize the actual APEX
  manifests, and run the full compatibility comparison. The pinned VINTF
  wrapper reads shipping API only from vendor properties, so it still needs a
  separate reviewed path for the original ODM evidence. Kernel metadata
  presence alone is not kernel compatibility.
- Retain all original vendor/ODM APEX bytes through later packaging. Do not
  let a signing pass alter only the metadata copy while leaving an opaque
  image different. APK inventories, APEX-key treatment and OTA trust remain
  separate integration work.
- When the reviewed policy derivation produces new vendor/ODM images, select
  a new explicit image/content-equivalence contract and a fresh metadata
  bundle. Admission requires verified complete filesystem metadata and content
  derivation, including proof that all 205 projected metadata files remain
  unchanged. Merely changing the two expected image hashes is insufficient.
  This original-image profile intentionally rejects those policy-bearing
  derivatives until that proof is reviewed; it must remain unchanged.
- Validate the signed AVB chain, partition fit, super/A/B/snapshot/OTA artifacts
  and eventual authorized device boot separately. No phone was accessed here.

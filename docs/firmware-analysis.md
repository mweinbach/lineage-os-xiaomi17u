# Offline analysis of the supplied Xiaomi.eu package

On **2026-08-27**, the supplied modified package was extracted, reconstructed
and inspected without modifying the phone or executing its installers. All eight
populated logical images are readable EROFS filesystems. **This is not a valid
signed partition set:** the retained AVB metadata does not match the supplied
contents. Extraction integrity and filesystem integrity passed; publisher
authenticity, flash safety and Evolution X compatibility were not established.

The [provided-firmware record](provided-firmware.md) documents intake and the
filename/internal-incremental discrepancy. The original and immutable intake
copy both remain **9,914,891,416 bytes**, with SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Both were rehashed after extraction and remained unchanged during those reads.
Provenance remains `source_kind=user-provided`, `source_url=null`,
`origin_verified=false`; Xiaomi.eu is not untouched Xiaomi factory firmware.

The [sanitized machine-readable layout](../research/firmware-layout.json)
contains the sizes, hashes, metadata checksums, tables, extents and tool pins
below. It contains no firmware bytes, keys, serials or absolute host paths.
Raw inputs, outputs and detailed receipts remain ignored under:

```text
artifacts/firmware-analysis/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69/
```

| Private receipt below that directory | Verified result |
| --- | --- |
| `archive-images/receipt.json` | 66 image members copied from the verified intake; every image CRC and SHA256 readback passed; no installer extracted |
| `reconstructed/receipt.json` | Guarded reconstruction of the 15 explicitly inventoried sparse fragments |
| `upstream-crosscheck/receipt.json` | Separate reconstruction with pinned Lineage extraction code |
| `reconstruction-verification.json` | Complete raw hashes match; every sparse input hash matches its archive extraction receipt |
| `logical-partitions/receipt.json` | Eight explicit A partition images extracted from metadata slot 0; output hashes reread and verified |
| `lp-upstream-crosscheck/receipt.json` | Every logical image's full SHA256 and size matches a separate pinned Lineage LP extraction |
| `filesystem-validation/receipt.json` | All eight read-only EROFS checks exited 0 with superblock checksum verification enabled |
| `boot-analysis/avb-analysis-complete.json` | Retained AVB descriptors and the observed content-digest failure; not an approval to flash |

The sparse fragments share an address space; their serialized bytes must not be
concatenated. Each RAW/FILL chunk writes at its declared logical position.
DONT_CARE leaves other fragments' data intact, and never-written bytes in the
new raw output are zero. The guarded parser rejected overlapping write ranges
and verified the complete numbered inventory before producing an output.

| Sparse property | Observed value |
| --- | --- |
| Fragments | `super.img.0` through `super.img.14`, 15 total |
| Header magic / version | `0xed26ff3a` / `1.0` |
| File / chunk header sizes | 28 / 12 bytes |
| Block size / blocks per fragment | 4,096 bytes / 3,735,552 |
| Declared expanded address space | 15,300,820,992 bytes per fragment |
| Chunks across all fragments | 172 RAW, 5 FILL, 37 DONT_CARE; 214 total |
| Nonoverlapping writes | 177 ranges covering 11,049,590,784 bytes |
| Never-written zero bytes | 4,251,230,208 |
| Embedded sparse checksums | All header checksums zero; no CRC32 chunks |

Both implementations produced a **15,300,820,992-byte** `super.raw.img` with
SHA256 `25882bf770e43c6eaceb8b2209ed32b77145553a5d641c47966d7147be55ade7`.
The independent implementation was Lineage `extract-utils`, branch
`lineage-23.2`, commit `19a1e68e47bbe9ba446e167b2d402953bd7e0c87`.
This agreement establishes consistent reconstruction of this package, not
agreement with an authenticated factory image.

The LP inspector uses the pinned
[AOSP liblp format and reader](https://android.googlesource.com/platform/system/core/+/a3b721a32242006b59cb12bd62c9133632af3a2d/fs_mgr/liblp/).
It checks geometry, header and table SHA256 values; table sizes and indices;
metadata boundaries; physical extent ranges; names; and every primary/backup
pair. Partition membership comes from each record's `group_index`, not from a
presumed relationship between group number, metadata slot and A/B suffix.

| LP property | Verified value in this modified package |
| --- | --- |
| Metadata version / header size | 10.2 / 256 bytes |
| Sector / logical block size | 512 / 4,096 bytes |
| Geometry structure / copy offsets | 52 bytes / 4,096 and 8,192 bytes |
| Maximum metadata size / slot count | 65,536 bytes / 3 |
| Reserved region through end of metadata | 405,504 bytes |
| Header plus populated tables | 1,488 bytes per copy, including 1,232 table bytes |
| Header flags | `1`: Virtual A/B; no overlays-active or unknown flags |
| Tables | 16 partitions, 8 extents, 3 groups, 1 physical block-device declaration |
| Declared physical device | `super`, 15,300,820,992 bytes; matches this raw image |
| First logical sector / alignment | 2,048 / 1,048,576 bytes; alignment offset 0 |
| Geometry and metadata copies | Both geometry copies and all six metadata copies validated; all slots identical |

| Metadata slot | Primary offset | Backup offset |
| --- | ---: | ---: |
| 0 | 12,288 | 208,896 |
| 1 | 77,824 | 274,432 |
| 2 | 143,360 | 339,968 |

All three slots have metadata SHA256
`9f1487616c2b46dbc5c0164888e2e889ca4f2b21a738c667d938df2d27322484`.
Different slots are allowed to differ in general; this package happens to
contain identical copies. A primary/backup disagreement within a slot blocks
extraction instead of silently selecting one copy.

| Group | Maximum bytes | Allocated bytes |
| --- | ---: | ---: |
| `default` | 0, meaning unlimited | 0 |
| `qti_dynamic_partitions_a` | 15,290,335,232 | 11,049,185,280 |
| `qti_dynamic_partitions_b` | 15,290,335,232 | 0 |

Each A partition below has one LINEAR extent on device index 0 and the read-only
attribute. Its paired B record exists but has zero extents and size zero in this
package. **Empty logical B records do not establish the absence of physical B
partitions or describe the connected phone's current contents.** No B image was
created. Every extracted A image records the raw image SHA256 as its parent.

| Extracted partition | Bytes | SHA256 |
| --- | ---: | --- |
| `odm_a` | 4,679,843,840 | `cf342dadf1d8da6748c2cf6959bc04ce96226b27617e8bc16363eb51a2071d62` |
| `product_a` | 3,712,385,024 | `d23bfffe911ae205262dee779792deb43ec5312bf02547e0f13ee860252c81b9` |
| `system_a` | 850,591,744 | `f7d23fc0b3c471e4907bacc5ec53e63bc826a5305cf82e0e508ca3c57901a5c2` |
| `system_dlkm_a` | 16,506,880 | `5470344df2770d9ebb1c3341d36f771922556a13db5b1d8f37f219553de24d26` |
| `system_ext_a` | 685,998,080 | `b2937ccb0dd38290af629c19064d1bacf4d9167d5074fb86e972f4d30b4c54ef` |
| `vendor_a` | 941,506,560 | `29857df564130923b3786b11b4ad29a0c16522e1def37aed7fe09329d673da43` |
| `vendor_dlkm_a` | 53,035,008 | `514e5608592de4c3388a5a6bf3bc8a5c84554333cbee83aab3fdd001428f2cb1` |
| `mi_ext_a` | 109,318,144 | `c7c16f067719335d9878925417c4a551c6795c032afba912a75bcc92816ec9f8` |

All eight images contain EROFS magic `0xe0f5e1e2` at offset 1,024. Native
Homebrew `fsck.erofs` 1.9.4 subsequently scanned every image with `--extract`
and exited 0. Without `=directory`, this option decodes and checks inode data
without writing extracted filesystem contents. Superblock checksum verification
remained enabled; no checksum-bypass option was used. The tool binary SHA256 was
`69c81657d6c30c0fd598f1bfa3e0461984864549e3afaf6365f2197ffffd1fc6`.
This operation did not verify AVB signatures, kernel module compatibility or
native-feature behavior. Filesystem content/dependency analysis is separate.

The retained AVB failures are material. `vendor_boot` does not match its retained
content digest. `product_a` is 3,712,385,024 bytes, but its retained
`vbmeta_system` descriptor covers 4,850,307,072 data bytes before its hashtree.
The `system`, `system_ext`, `vendor` and `mi_ext` images also end before their
declared data ranges end. Both DLKM images stop at the beginning of their
declared hashtrees; `odm` lacks the complete declared tree as well. None of the
eight logical images contains its complete retained declared hashtree range.
The inspected first-stage fstab also lacks `avb`/`verify` flags. These modified
inputs must remain research material. Do not pad images or change their AVB
descriptors to hide these failures. This fstab is not an approved verification
policy for a new build. Detailed boot/kernel/AVB requirements are tracked
separately in `docs/boot-contract.md`.

Physical boot-partition geometry remains **unresolved**. The authorized phone
was revalidated before a separate read-only collection attempted `size` and
`start` for 15 named physical partitions. All 30 sysfs reads returned permission
denied; no privilege escalation or device modification followed. The private
result is `evidence/partition-sysfs-20260827T1631Z/geometry.json`. File lengths
inside this ZIP are not physical partition capacities, and the LP device table
is a package declaration. Do not promote either into a Nezha BoardConfig without
matching physical and authenticated baseline evidence. Bootloader state remains
unresolved as recorded in the [device baseline](device-baseline.md).

The following commands reproduce the offline stages into a **new** ignored
directory. Existing outputs and receipts are already present; do not reuse their
directories. Check free disk first: budget at least 40 GiB extra for archive
images, raw super and eight logical images, plus about 25 GiB if keeping separate
independent reconstruction/extraction outputs. No command below accesses a
phone, installs software on it or executes firmware code.

```sh
package_sha=b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69
raw_sha=25882bf770e43c6eaceb8b2209ed32b77145553a5d641c47966d7147be55ade7
analysis_dir=artifacts/firmware-analysis/NEW_REPRODUCTION
mkdir "$analysis_dir"

python3 scripts/firmware_images.py \
  --intake "artifacts/firmware/$package_sha" \
  --expected-sha256 "$package_sha" \
  --output "$analysis_dir/archive-images"

python3 scripts/sparse_images.py reconstruct \
  --expected-pieces 15 --parent-sha256 "$package_sha" \
  --max-output-bytes 15300820992 \
  --output-dir "$analysis_dir/reconstructed" \
  "$analysis_dir/archive-images"/super.img.*

python3 scripts/logical_partitions.py inspect \
  --image "$analysis_dir/reconstructed/super.raw.img" \
  --expected-sha256 "$raw_sha"

python3 scripts/logical_partitions.py extract \
  --image "$analysis_dir/reconstructed/super.raw.img" \
  --expected-sha256 "$raw_sha" --slot 0 \
  --partition odm_a --partition product_a --partition system_a \
  --partition system_dlkm_a --partition system_ext_a --partition vendor_a \
  --partition vendor_dlkm_a --partition mi_ext_a \
  --output "$analysis_dir/logical-partitions"
```

`firmware_images.py` extracts only supported image members and requires the
expected package hash and intact intake metadata. Its default extracted-image
limit is 64 GiB. It does not extract the package's installers or bundled platform
binaries. Archive extraction and sparse reconstruction publish new directories
atomically without replacing existing destinations, including empty directories.

`sparse_images.py` requires the expected piece count from a complete inventory,
numeric fragment ordering, matching geometry and disjoint RAW/FILL writes. It
supports sparse version 1.0 and rejects nonzero header checksums and all CRC32
chunks as unsupported. Defaults bound expanded output to 64 GiB, fragments to
1,024 and total chunks to 100,000. The parent package hash in this receipt alone
is caller-provided; the separate archive receipt comparison establishes linkage.
The format reference is the pinned
[AOSP sparse header](https://android.googlesource.com/platform/system/core/+/68be0c2c0006a0740d0b1809abe4717308f90d15/libsparse/sparse_format.h).

`logical_partitions.py` supports complete raw LP 10.0–10.2 images, LINEAR/ZERO
extents and one physical device for extraction. It requires explicit partition
names and a metadata slot; no suffix is added or removed. Every geometry and
metadata copy must validate and every primary/backup pair must agree. Unknown
header flags, active overlays, disabled selected partitions, unsafe names,
symlinks, source changes and existing outputs are refused. Limits are 256 GiB
per raw image, 4 MiB per metadata copy, 32 metadata slots and a 32 MiB total
metadata region. Reads and writes use bounded buffers. Outputs are restricted
to new directories below `artifacts/` or `evidence/`; a failed extraction may
leave partial files there without a successful receipt.

The workspace still has no approved Nezha lunch target, no full Evolution X
device build and no Evolution X hardware tests. The next integration work must
resolve the signed baseline and physical geometry, then validate the boot,
kernel/DLKM, VINTF, proprietary dependencies and enforcing SELinux contracts.
The [native-feature plan](native-features.md) retains device tests as the gate
for any claim of Xiaomi feature compatibility.

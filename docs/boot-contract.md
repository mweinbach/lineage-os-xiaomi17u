# Boot, kernel and AVB requirements from the supplied package

Read-only image inspection on **2026-08-27** established the package's boot
formats, kernel configuration, vendor ramdisk contents, device-tree identities,
and AVB descriptors. **The supplied Xiaomi.eu images are not a consistent AVB
image set:** `vendor_boot` fails its recorded hash; all eight extracted logical
partitions fail either descriptor bounds or root-hash checks. This is a material
input problem, not permission to disable verification.

The sanitized record is
[`research/boot-contract.json`](../research/boot-contract.json). The source is
the [user-provided Xiaomi.eu ZIP](provided-firmware.md), SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Its ZIP CRC and intake/readback SHA256 checks passed, but its download origin is
unknown and it is not authenticated Xiaomi factory firmware. Local integrity
does not make retained signing metadata agree with modified image contents.

## Evidence and inspection boundaries

Private outputs are under:

```text
artifacts/firmware-analysis/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69/boot-analysis/
```

`final-receipt.json` hashes 173 regular artifacts and records 19 safe links,
including unpacked components, decompressed CPIO bytes, selected text members,
module metadata, decoded trees, tool sources, and all AVB diagnostics. Its
SHA256 is
`3615d62f4e4a61a11ff476ca47a245fa63a462136c53e688db66979f437879db`.
The more focused `verification/receipt.json` has SHA256
`6a75bd65289e8d661b330bf4d007e680f5c377f8694c1c1af7ab847300fab54b`.
These artifacts, raw images, public-key blobs, and proprietary module contents
remain ignored by Git. The tracked record contains facts and hashes only.

The following AOSP tools were reviewed before use, with clean checkouts at the
recorded `android-16.0.0_r4` revisions:

| Inspector | Repository commit |
| --- | --- |
| `unpack_bootimg.py` | `954bc3ead5e679005fddf3484d247f2557b3c2c9` |
| `avbtool.py` | `c92ce4cb9a1b6d20a1bc11b7e5864af9f78615bb` |
| `mkdtboimg.py` | `10c6b5f81069d6d78c7ef3833458f4d51d02e2a6` |

Source-file hashes and local Python/LZ4/dtc/OpenSSL binary hashes are in the
receipts. Boot section bounds and vendor ramdisk names were checked before
unpacking. CPIO inspection rejects traversal, duplicate paths within an archive,
bad bounds, and invalid CRCs. It never materializes or follows archive links;
selected regular text files are saved under generated filenames. No bundled
firmware installer, executable, module, or init script was run. No phone or
container operation was needed for this analysis, and input hashes and file
timestamps remained unchanged.

## Image formats and size limits

These are **package file lengths**, not independently measured physical
partition capacities. The AVB covered length is another distinct value.

| Image | File bytes | Observed format/content | AVB original image bytes |
| --- | ---: | --- | ---: |
| `boot.img` | 100,663,296 | Boot v4; 39,963,136-byte kernel; no ramdisk | 39,985,152 |
| `init_boot.img` | 8,388,608 | Boot v4; 2,916,992-byte ramdisk; no kernel | 2,924,544 |
| `vendor_boot.img` | 100,663,296 | Vendor boot v4; 18,107,283-byte ramdisk; 4,496,880-byte DTB section | 22,618,112 |
| `recovery.img` | 104,857,600 | Boot v4; 30,407,261-byte ramdisk; no kernel | 30,412,800 |
| `dtbo.img` | 23,068,672 | DT table v0; one 1,495,047-byte overlay | 1,495,111 |
| `vbmeta.img` | 12,288 | Signed top-level VBMeta plus padding | Not a footer-bearing image |
| `vbmeta_system.img` | 4,096 | Signed chained VBMeta plus padding | Not a footer-bearing image |
| `pvmfw.img` | 1,048,576 | Boot v3 wrapper; 773,888-byte firmware payload; no ramdisk | 778,240 |
| `qtvm_dtbo.img` | 5,242,880 | DT table v0; two overlays | 522,832 |

The v3/v4 boot format uses 4,096-byte alignment, and this vendor boot header
explicitly declares 4,096-byte pages. The boot v4 headers are 1,584 bytes; the
vendor boot header is 2,128 bytes. Boot, init_boot, and recovery have empty
header command lines, zero OS-version/patch fields, and a zero-length v4 boot
signature section. That last field does not mean AVB is absent: boot and
recovery also have signed AVB footers. The separate `pvmfw` header declares
Android 16 and patch level `2026-07`.

The [existing phone baseline](device-baseline.md) independently lists A/B names
for boot, init_boot, vendor_boot, recovery, dtbo, vbmeta and vbmeta_system, with
`super` pointing to `/dev/block/sda33`. A later bounded sysfs attempt recorded
**zero successful physical-size reads** for those 15 names. Physical capacities,
start offsets, bootloader unlock state, and stored rollback counters remain
unverified. Do not convert this table into BoardConfig partition sizes.

## Kernel and module boundary

The extracted ARM64 kernel has SHA256
`4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8`.
Its release exactly matches the live baseline:

```text
6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k
```

The embedded 220,352-byte IKCONFIG was recovered and hashed:
`73fa878baa4c748b2139e7acb4ed396d2056ca8ed71b565ded6f96b3558a98cd`.
It enables `CONFIG_ARM64_4K_PAGES`, `CONFIG_MODULES`, `CONFIG_MODVERSIONS`,
`CONFIG_MODULE_SIG`, `CONFIG_ANDROID_VENDOR_HOOKS`, `CONFIG_BOOT_CONFIG`,
`CONFIG_DM_VERITY`, and `CONFIG_SECURITY_SELINUX`. The 16 KiB/64 KiB options and
`CONFIG_MODULE_SIG_FORCE` are not set. These are observations of this kernel,
not instructions to weaken signing or SELinux in a replacement build.

The vendor ramdisk contains **430 ELF64 AArch64 modules**. Every module's
`.modinfo` carries this vermagic:

```text
6.12.23-android16-5-g0cd5a311d2f7-mi-4k SMP preempt mod_unload modversions aarch64
```

The build suffix differs from the boot kernel's release. Treat that as a
requirement to check KMI symbols, version CRCs, signatures, and actual module
loading; this string difference alone does not establish whether the modules
will load. Android's KMI process compares kernel/module interfaces and symbol
lists, not only release labels.
[AOSP kernel ABI monitoring](https://source.android.com/docs/core/architecture/kernel/abi-monitor)

| Ramdisk list | Entries | Unique names | SHA256 |
| --- | ---: | ---: | --- |
| `lib/modules/modules.load` | 157 | 154 | `1101cd200b68b007b2dc039b55358dc8c9459023cbf30c2dfd13f591c805aa26` |
| `lib/modules/modules.load.recovery` | 435 | 424 | `91eacbd4a84618a9c3e9dab266286757099d2dd5c03d3b4dd2bd74e9d7d68de3` |

All named modules and the dependencies in the 430-line `modules.dep` resolve
within this ramdisk inventory. The lists contain duplicates; preserve their
observed order as evidence rather than silently rewriting them. This does not
test load order, symbol resolution, or compatibility with the separate
`system_dlkm` and `vendor_dlkm` images. Exact reproducible kernel sources and a
replacement kernel build remain outstanding.

## Ramdisk, fstab and bootconfig

The three ramdisks use legacy LZ4 and newc CPIO:

| Ramdisk | Expanded CPIO bytes | Entries | Kernel modules |
| --- | ---: | ---: | ---: |
| init_boot | 5,436,160 | 24 | 0 |
| vendor_boot | 48,236,800 | 440 | 430 |
| recovery | 53,929,472 | 1,036 | 0 |

The vendor ramdisk table has one 108-byte entry: type `1` (platform), empty
name, offset zero, and all 16 board-ID words zero. It has no separate type-3
DLKM fragment, even though this platform ramdisk contains modules. Header v4
permits multiple typed fragments; this package's observed single-fragment
layout must not be replaced with another device's layout by assumption.
[AOSP vendor boot format](https://source.android.com/docs/core/architecture/partitions/vendor-boot-partitions)

`first_stage_ramdisk/fstab.qcom` has SHA256
`1556b7e72c49c2a13ec4172e553279dcca672f2749834ac47630f2774c8a4bb7`.
It lists `system`, `system_ext`, `product`, `vendor`, `odm`, `system_dlkm`,
`vendor_dlkm`, and `mi_ext` as logical, slot-selected first-stage mounts, with
ext4 and EROFS alternatives. **Those entries contain no `avb` or `verify`
flags. Do not copy this modified fstab as an enforcing Evolution configuration.**
It also records F2FS metadata/userdata, wrapped-key encryption options,
firmware mounts, and Xiaomi overlay mounts; those are requirements to review,
not authorization to format or mount anything on the phone.

The 270-byte vendor bootconfig declares `androidboot.hardware=qcom`, parallel
module loading, USB controller `a600000.dwc3`, protected-VM support with
`gunyah`, `vendor.qspa=true`, and serial console disabled. All eight key/value
pairs and their hash are in the sanitized record. The vendor command line
includes the public `nezha:16/OS3.0.309.0.WPACNXM:user` build label. This package
metadata does not replace the unreadable live `/proc/bootconfig` evidence.

## Device trees

The vendor boot DTB section contains **eight concatenated FDTs**: Canoe and
CanoeP, v1/v2, and alternate thermal-profile variants. Their root compatibility
strings are `qcom,canoe` or `qcom,canoep`; the exact IDs and individual hashes
are recorded in the JSON. No single entry has been established as the one
selected by this phone's bootloader.

The single `dtbo.img` entry explicitly identifies:

```text
model = Qualcomm Technologies, Inc. Nezha based on SM8850
qcom,board-id = <8 0>
```

Its compatibility list includes Canoe/CanoeP MTP, and its FDT SHA256 is
`4bb4b31bca5de3e354a565304d1ea277ac6d9b70e2760a40147d9f151a691f99`.
The QTVM table has two entries, IDs `0x2d` and `0x31`, declaring Canoe SVM MTP
and Canoe OEMVM MTP. All **11** FDTs decoded with `dtc` exit `0`, with warnings
retained. Parsing and static model strings are not overlay-application or
hardware tests, and do not establish another model's compatibility.

## AVB results and rollback constraints

Signed boot, recovery, qtvm_dtbo, vbmeta and vbmeta_system metadata all verify
against their embedded RSA4096 public-key blob. The common key's SHA256 is
`e5c32182629bfa8657708e8cad3e3ef83c9764594a213f8a8824e06386b9c5e1`;
avbtool reports its SHA1 as `8256e695b81d1eb6dd0b1ce5d08b9c73cbb5e5b6`.
The parent chain descriptors match the actual child-image keys. **No independent
OEM trust root was supplied or verified.** Self-consistency of these signatures
does not authenticate the package publisher or establish what the phone trusts.

| Chained image | Rollback location declared by top vbmeta | Child rollback index |
| --- | ---: | ---: |
| boot | 3 | 1,769,904,000 |
| recovery | 1 | 1 |
| vbmeta_system | 2 | 1,769,904,000 |

Top vbmeta's rollback index is zero. The inspected VBMeta headers and chain
descriptors have flags zero. Child headers separately report location zero;
retain the distinction from locations declared by the parent chains. None of
these values measures the phone's stored rollback counters or proves downgrade
safety. The boot/init_boot AVB properties declare patch `2026-02-01`; the system
properties declare `2026-07-01`, consistent with the baseline's separate patch
levels rather than a single uniform package date.

Standalone boot, recovery and qtvm_dtbo checks pass their embedded signature and
content hash. The init_boot, dtbo and pvmfw leaf footers use algorithm `NONE`;
their hashes pass, including their copies in signed top-level metadata. An
unsigned leaf footer is not an independently authenticated image.

The vendor_boot failure is independently reproduced as
`SHA256(salt || first 22,618,112 image bytes)`:

| Field | Value |
| --- | --- |
| Salt | `4dcefe592c7dbe6d5ede4a7f3de84b31ff21ed0d627885fb4845e36fc8101c03` |
| Expected digest | `f0e73c5f16e761cbbc5b65a44787b87fabeb1e23df3087c9a960ac8d9ea4b0a2` |
| Calculated digest | `98dddd002f7e3d5959d8654a4018fcc6d32cb3382525d7c6301016430964e291` |
| Full input file SHA256 | `20349b30fe10cb30f75579f1f02f7dd26bcb3b0af543bd261a5877634991854d` |

Both the vendor_boot footer and signed top vbmeta contain that same expected
digest, salt and covered length. After supplying the actual child keys as
explicit expectations, top-level `avbtool verify_image` checks all three chain
descriptors and the countrycode/dtbo/init_boot/pvmfw hashes, then exits `1` on
vendor_boot. Its failure logs are retained without modifying any input.

The eight logical-image checks use the separately reconstructed super outputs,
whose readback hashes were checked again before and after inspection:

| Logical image | Actual file bytes | Signed descriptor data bytes | Result |
| --- | ---: | ---: | --- |
| mi_ext | 109,318,144 | 109,445,120 | Data range exceeds file |
| odm | 4,679,843,840 | 4,678,270,976 | Root hash mismatch |
| system_dlkm | 16,506,880 | 16,506,880 | Root hash mismatch |
| vendor | 941,506,560 | 941,649,920 | Data range exceeds file |
| vendor_dlkm | 53,035,008 | 53,035,008 | Root hash mismatch |
| product | 3,712,385,024 | 4,850,307,072 | Data range exceeds file |
| system | 850,591,744 | 895,102,976 | Data range exceeds file |
| system_ext | 685,998,080 | 699,715,584 | Data range exceeds file |

All eight declared tree and FEC ranges exceed the corresponding file lengths.
No AVB footer is recognized in these logical images. The absence of a leaf
footer alone would not establish failure; the contradictory data ranges and
hashes do. FEC correctness was not cryptographically tested.

For the five undersized files, verification fails at a bounded range check.
The pinned AOSP `generate_hash_tree` loop subtracts the length actually read
and does not stop on a zero-byte read before the declared data length, so
blindly using `--follow_chain_partitions` on these inputs could loop at EOF.
That unsafe call was not made. The three images with a complete declared data
range were checked with the AOSP descriptor verifier and failed. No image was
padded, no hashtree was accepted as zeroed, and no check was disabled.

Initial missing-chain and missing-logical-file diagnostics are also retained;
the follow-up checks above replace those temporary evidence gaps with actual
key comparisons and image-range/hash results. They do not turn the overall
AVB result into a pass.

## Requirements before a device target

1. Resolve this modified package's AVB inconsistency using authenticated,
   matching original inputs. Do not infer corruption during extraction: both
   extraction readback and input preservation checks passed.
2. Establish physical boot-partition geometry, bootloader authorization/unlock
   state, and stored rollback constraints separately. Image sizes cannot fill
   those gaps.
3. Review the Android 16, 4 KiB kernel strategy together with the full module
   sets, KMI/CRC/signature requirements, dependencies and load order.
4. Preserve the observed separation of boot, init_boot, recovery, vendor boot,
   DTB/DTBO and virtualization firmware. Derive Nezha-specific fstab, AVB and
   enforcing SELinux integration instead of copying this package's omissions
   or another phone's settings.
5. Complete device/common/vendor dependencies and VINTF checks before
   registering an Evolution lunch target. No ROM boot or native feature has
   been demonstrated by this inspection.

Fourteen synthetic CPIO/FDT/ELF parser safety tests passed without a phone or
network. The normal `make test` suite remains separate from these private
inspection checks, hardware validation, and a full Android build.

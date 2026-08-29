# Factory-named China image validation

The separately supplied China fastboot package now has a reconstructed super
image, eight extracted logical partitions, **passing internal AVB verification
for the selected Android image chain**, and passing read-only filesystem checks.
It provides usable local research inputs beyond the modified Xiaomi.eu package.
These results do not authenticate its download origin, establish an independent
Xiaomi trust root or authorize flashing.

The package is `nezha_images_OS3.0.309.0.WPACNXM_20260714.0000.00_16.0_cn_1081d3072b.tgz`,
12,778,943,953 bytes, SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
The [intake record](factory-firmware-intake.md) preserves the original and its
separately verified copy. Its provenance remains **user-provided, unknown URL,
unverified origin**. A matching filename and advertised length at Xiaomi's CDN
are not proof of this local file's acquisition path.

The [validation record](../research/factory-firmware-validation.json) binds
each operation and output to the package and preceding receipts. Raw images,
unpacked ramdisks, keys, private logs and proprietary contents remain ignored.
No installer or firmware executable was run, no image was mounted, and no
phone operation occurred.

All **19 images** in the user's extracted
`sources/nezha_images_OS3.0.309.0.WPACNXM_16.0/images/` directory were also
rehashed alongside the verified archive copies. All matched, with stable file
identities. This covers those 19 images, not arbitrary files or executables
elsewhere in the extracted directory. The [partition metadata audit](partition-metadata.md)
separately verifies its 37 inert GPT/XML files.

Review found a TAR edge case: Python's default reader can treat a malformed
later header as EOF. The shared bounded reader now rejects that case, truncated
headers and missing end markers, with regression tests. At **21:56:11 UTC**,
a fresh strict scan reverified the full package hash, all **127 member headers**,
the complete 15,325,941,760-byte gzip stream and TAR end padding. Streaming
hashes of all 19 images and 37 metadata files match the preserved extraction
receipts. No second large image copy was needed. The new corroboration receipt
is `362e50ef12a10ca2c648093e6049d170065bcad9490dbc1ac262fe1ba0016327`;
the old receipts were not overwritten to conceal the parser correction.

## Super and logical partitions

This package contains one **complete Android sparse `super.img`**, not the
15 numbered overlays in the Xiaomi.eu ZIP. It retains its original name.
The guarded sparse parser validates the chunk structure and writes RAW/FILL
ranges into a fresh output, preserving DONT_CARE semantics. It does not
concatenate sparse containers or overwrite an existing reconstruction.

| Representation | Bytes | SHA256 |
| --- | ---: | --- |
| Archived sparse super | 12,438,543,008 | `fe2c6b4abe4a36c871be184350132dfed1aa1b32ada0b051923a19835affa8f5` |
| Reconstructed raw super | 15,300,820,992 | `ce1c84662c00818ffc39217b61670cea5aadfd5952e4eafaacb9f2d64b9b7c09` |

The sparse header declares 4,096-byte blocks and 3,735,552 output blocks.
Its 220 chunks comprise 198 RAW, 13 FILL and nine DONT_CARE chunks. The header
checksum is zero and there are no CRC32 chunks; the tool rejects unsupported
checksum claims rather than silently ignoring them. The input hash was checked
against the image-extraction receipt, not just a caller-supplied package label.

An independent reconstruction used the pinned Lineage `unsparse_image`
implementation at `19a1e68e47bbe9ba446e167b2d402953bd7e0c87` in a second fresh
output. Its complete 15.3 GB output hash matches. Tool and source bytes remained
unchanged. Neither implementation byte-concatenated images.

The guarded logical-partition inspector validates both geometry copies and
all six metadata copies across three slots. Every primary/backup pair matches,
and the slots contain identical metadata. Version 10.2 declares Virtual A/B,
one physical super device, eight populated A partitions and eight empty B
entries. Empty B entries do not represent an independent complete fallback OS.

| Logical image | Bytes |
| --- | ---: |
| `odm_a` | 4,767,621,120 |
| `product_a` | 4,942,934,016 |
| `system_a` | 912,273,408 |
| `system_dlkm_a` | 16,912,384 |
| `system_ext_a` | 713,158,656 |
| `vendor_a` | 959,709,184 |
| `vendor_dlkm_a` | 54,132,736 |
| `mi_ext_a` | 111,198,208 |

The A group allocates 12,477,939,712 bytes against its declared
15,290,335,232-byte maximum. Each output was rehashed after extraction and is
bound to the raw super hash. A second logical extractor was not run in this
experiment; independent sparse reconstruction and the later AVB checks are
different corroboration. None of these values measures the phone's live GPT.

## Boot formats and AVB

The pinned AOSP unpacker inspected boot, init_boot, vendor_boot, recovery and
pvmfw as data. Both DTBO containers passed the pinned AOSP dumper. All selected
source images remained unchanged. Boot, init_boot, recovery, DTBO, vbmeta and
vbmeta_system are byte-identical to their Xiaomi.eu counterparts; vendor_boot
and the logical images are different. The old Xiaomi.eu AVB failures remain
recorded and are not rewritten as successes.

The main boot image uses header v4, a 39,963,136-byte kernel and no ramdisk.
Init_boot uses header v4 with a generic ramdisk and no kernel. Vendor_boot uses
header v4, 4 KiB pages, one 18,107,362-byte vendor ramdisk, a 4,496,880-byte DTB
area and 270 bytes of bootconfig. Recovery uses header v4, a 30,407,261-byte
ramdisk and **no kernel**. This supports the dedicated-recovery plan, not a
vendor_boot-only layout copied from another device.

The full selected root verification used pinned `avbtool` revision
`c92ce4cb9a1b6d20a1bc11b7e5864af9f78615bb`, expected chain partitions and
`--follow_chain_partitions`. It passed at **21:09:13 UTC**. The separate Qtvm
DTBO context also passed. A controlled filename alias maps the archive's
`qtvm-dtbo.img` to descriptor name `qtvm_dtbo.img` without changing its bytes.

All five inspected embedded RSA4096 signatures validate, all three child keys
match their parent descriptors, and every inspected AVB flags field is zero.
The chain assigns rollback locations **3 to boot, 1 to recovery and 2 to
vbmeta_system**. The child header's location field is not a substitute for the
parent's chain descriptor. Device-stored rollback counters were not read.

AVB checks covered the eight logical partition data/hash trees and the
selected boot-family hash descriptors. Data, tree and FEC ranges were bounded
before invoking the upstream tool. **FEC correction itself was not verified.**
No zeroed-tree acceptance, padding, image patch, signature bypass or rollback
relaxation was used. Initial root-chain checks deferred until super extraction
are preserved in the earlier boot receipt; the later chain receipt supplies
their completed results.

The embedded key is not independently authenticated as Xiaomi's OEM key.
Passing this selected Android chain is not authentication of every bootloader,
programmer or other firmware file in the TGZ, nor proof of device acceptance.

## Filesystems and use in the bring-up

All eight logical images passed trusted `fsck.erofs` 1.9.4 with `--extract`
**without an extraction destination**. That mode checks file-data decoding
without writing an extracted tree. Superblock checksums stayed enabled; the
tool reported no errors and source hashes remained unchanged. Filesystem
integrity is separate from AVB and from framework compatibility.

The first private filesystem driver stopped before invoking fsck because its
magic-number literal was wrong. That failed attempt is preserved. The second
driver compares the actual little-endian EROFS magic `0xe0f5e1e2`; it changes
no image or verification setting. Its eight checks passed at **21:13:46 UTC**.

At this intake checkpoint, the installed v6 build still used the explicitly
recorded Xiaomi.eu bundles. A new admission had to bind the factory images'
fstab, module ordering, VINTF, policy and proprietary dependencies before reuse.
No image was silently substituted into that running build. The later factory
admissions in the [build record](build-progress.md) keep that input boundary
explicit without rewriting this intake result.

The later [TWRP track](twrp-bringup.md) established `working76` as the selected
default recovery before completion of the ROM. Its device test used the
installed stock companion boot, kernel and vendor stack, not newly built
Evolution components. A recovery can help repair Android only while its
required boot chain still works; it does not prevent bootloader corruption.
Full ROM/OTA integration and Evolution native-feature tests remain separate
work; see [current workspace status](workspace-status.md).

| Operation receipt | SHA256 |
| --- | --- |
| Guarded sparse reconstruction | `cc046d08add4a0b2c194a925f2e65c0a26a25292ac32d64f1d25055e3082cd5f` |
| Independent sparse reconstruction | `e5feddf05ef3c0cec65e5e3cccd4e096c0b82ed94e455f0cd0e9f2815ebfb706` |
| Logical extraction | `a7c2fc5ab8f23f6a5dc723736b006e8293f4c07c0dd92a5f28cc1eca46e2fc95` |
| Initial AOSP boot inspection | `19a0cf859e91b283684c03ab1691f8469e3c87c5a01b8fc6a1eae1d5e65b1f37` |
| Selected AVB chain | `5f22d51a23ba989f71bf6a37844bbade71b5c02b17e36c3ca77290ab9a795c58` |
| Eight read-only EROFS checks | `339843cdc69f8247d19fdd3d29a0bc52f6e15296c318312e937002a551cd6318` |

The ordinary workspace tests validate record consistency offline. They do not
rerun these large private-image operations or simulate a booted ROM.

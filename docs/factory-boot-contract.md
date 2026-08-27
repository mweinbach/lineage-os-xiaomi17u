# Factory boot components and ramdisks

The factory-named China package has the **same kernel, DTB section, bootconfig,
init_boot ramdisk, recovery ramdisk and 430 vendor ramdisk module payloads** as
the preserved Xiaomi.eu baseline. The vendor ramdisk's only changed file
content is `first_stage_ramdisk/fstab.qcom`: the factory version retains AVB
declarations and GSI key-path references absent from the modified copy.
This establishes concrete factory inputs for the next integration steps,
without adopting the modified fstab or claiming a working ROM or recovery.

All **19 images** in
`sources/nezha_images_OS3.0.309.0.WPACNXM_16.0/images/` were hashed and compared
with the separately extracted archive images. Both directories match every
recorded SHA256, totaling **14,852,407,336 bytes per directory**. The parent
archive is
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
Its origin remains user-provided and unverified; local integrity is not an
authenticated Xiaomi trust root. The [factory intake](factory-firmware-intake.md)
and [strict archive corroboration](partition-metadata.md) remain separate
evidence. The Xiaomi.eu package and its original results were not replaced.

The [sanitized record](../research/factory-boot-contract.json) binds the image
readback, pinned AOSP header inspection, host LZ4 tool, bounded CPIO comparison
and independent output readback. Raw ramdisks, selected text, executable
payloads, logs and receipts remain in ignored directories. No phone or guest
VM was accessed by this comparison.

| Image | Header | Kernel bytes | Compressed ramdisk bytes |
| --- | ---: | ---: | ---: |
| `boot` | 4 | 39,963,136 | 0 |
| `init_boot` | 4 | 0 | 2,916,992 |
| `vendor_boot` | 4 | No kernel field in this format | 18,107,362 |
| `recovery` | 4 | 0 | 30,407,261 |

The image header fields were checked against the hash-bound output of AOSP
`unpack_bootimg` at `954bc3ead5e679005fddf3484d247f2557b3c2c9`.
The zero boot-signature size field is not a conclusion about AVB footers or
verified boot. Recovery is a separate ramdisk with no kernel; preserving its
image alone cannot protect against boot-chain or bootloader damage. See the
[recovery plan](recovery-plan.md) for that boundary and separately authorized
test requirements.

The factory vendor header uses 4,096-byte pages and a 2,128-byte header. Its
single 108-byte ramdisk-table entry is type 1, at offset zero, with an empty
name and sixteen zero board-ID words. The DTB section is 4,496,880 bytes and
the bootconfig is 270 bytes. These match the Nezha arrangement already
captured; no other device's fragment or partition layout was substituted.

The following component hashes match Xiaomi.eu exactly:

| Component | SHA256 |
| --- | --- |
| Kernel Image | `4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8` |
| Vendor DTB section | `1a5c30b75e816f33dd36caa114faa7bc656605e4ac9ffe786726538b37ada22d` |
| Vendor bootconfig | `bad92331bd65be0207c84a855cb0b9580a504acd89684e3222007b20b683805f` |

Bootconfig still declares Qualcomm hardware, parallel module loading,
`a600000.dwc3`, protected-VM support through Gunyah and the QSPA flag. All eight
literal declarations are recorded; this is not a new live bootconfig read.
The [package partition limits](partition-metadata.md), kernel source/ABI work
and live geometry remain distinct from component equality.

The factory ramdisk inspection completed on **2026-08-27 at 22:06:52 UTC**:

| Ramdisk | Expanded CPIO bytes | Entries | Comparison with Xiaomi.eu |
| --- | ---: | ---: | --- |
| init_boot | 5,436,160 | 24 | Entire compressed and expanded streams match |
| vendor_boot | 48,237,312 | 440 | 439 entries match checked contents/metadata; fstab differs |
| recovery | 53,929,472 | 1,036 | Entire compressed and expanded streams match |

All **430** vendor ramdisk `.ko` files have matching paths and whole-file
SHA256 hashes. All six module metadata files also match: `modules.alias`,
`modules.blocklist`, `modules.dep`, `modules.load`, `modules.load.recovery` and
`modules.softdep`. The normal load list has 157 entries and 154 unique names;
the recovery list has 435 entries and 424 unique names. Every listed filename
exists in this ramdisk. Ordering and duplicates are preserved. No module was
loaded, and these matches do not resolve kernel export CRCs, module-signature
trust, provider selection or actual loadability. DLKM images are a separate
comparison; the 430 count is only for vendor_boot.

The comparison checks file contents, kind, mode, UID, GID, link count and
symlink-target text. It does not compare CPIO timestamps or inode numbers.
Archive paths and links were not materialized; selected text was written
under generated filenames. A second pass rehashed **31 output artifacts,
108,712,012 bytes**, and every one of the **1,500 CPIO entry contents** without
reusing the CPIO parser.

The factory fstab is **13,661 bytes**, SHA256
`94a202513e73c5e05233fe6d0ef6d0de7b8fa6264562cff01723ec7f398bc535`.
The Xiaomi.eu copy is 13,076 bytes, SHA256
`1556b7e72c49c2a13ec4172e553279dcca672f2749834ac47630f2774c8a4bb7`.
Both have 61 active rows with identical source, mount point, filesystem and
mount options. Factory adds AVB flags to **21 rows** and adds `avb_keys`
to the two `/system` alternatives; all other flag order is retained.

| Normal first-stage entries | Factory verification declaration |
| --- | --- |
| `system`, `system_ext`, `product`, each ext4 and EROFS | `avb=vbmeta_system` |
| `mi_ext`, `vendor`, `odm`, `vendor_dlkm`, `system_dlkm`, each ext4 and EROFS | `avb=vbmeta` |
| `boot`, `init_boot`, `vendor_boot`, `dtbo`, `recovery`, each emmc | `avb=vbmeta` |

Both `/system` rows name seven GSI key paths, from `/avb/q-gsi.avbpubkey`
through `/avb/w-gsi.avbpubkey`. None of those paths was found in the three
inspected CPIO inventories. Other filesystem locations and key-loading stages
were not examined here. This limited absence does not establish a stock boot
failure or authorize deleting the key flags, supplying invented keys or
disabling verification.

Normal userdata declarations are unchanged between the two packages. They
specify F2FS with `inlinecrypt`,
`fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0`,
`metadata_encryption=aes-256-xts:wrappedkey_v0`, and
`keydirectory=/metadata/vold/metadata_encryption`, alongside the recorded
quota, checkpoint and mount options. These are requirements to preserve and
validate, not a decryption test or authorization to format data.

Two additional recovery fstabs were captured after the initial text selection:
`miui.factoryreset.fstab` (426 bytes) and `system/etc/recovery.fstab`
(3,709 bytes). Both are byte-identical to Xiaomi.eu. The regular recovery
fstab declares ext4-only logical mounts and legacy `fileencryption=ice` plus
`wrappedkey`; the factory-reset fstab has its own two-row layout. Their
literal declarations differ from the normal vendor fstab's EROFS alternatives
and explicit encryption algorithms. **Neither is adopted as a TWRP fstab, and
recovery decryption remains unverified.** Factory-reset init commands were
read only as text and never applied.

The private dependency inventory records snapuserd, recovery, fastbootd,
boot-control, fastboot and health services, plus init imports. Presence of an
executable as CPIO data is not evidence that its service runs. Property-based
imports, references to other partitions, and two literal recovery executable
paths absent from this CPIO remain recorded as limited static observations.

The first private LZ4 wrapper attempt failed with exit 44 because Python's
buffered stream was logically at byte zero while its inherited OS descriptor
was at byte 4,096. The input hash and LZ4 magic were correct; this was not
firmware corruption. The failed script, log and staging directory are preserved.
The second attempt explicitly rewinds the descriptor, passes a mocked
regression test and successfully decodes all three ramdisks with the pinned
LZ4 1.10.0 binary. Ten private wrapper tests and fourteen existing parser tests
pass; the decoder has a 120-second and 512 MiB limit per ramdisk.

| Receipt | SHA256 |
| --- | --- |
| Nineteen-image directory readback | `2c5c406b9374f7e1a191d994c0f6c4de25516e74ff857a3e4bde3e63c4b4eddb` |
| Headers, components and wrapper history | `534873e0b25e1ca48a9d1fc83c8a83c6d460146f7ac8070b0c5df4f3b3edf6f2` |
| Successful bounded ramdisk comparison | `138df4eff3d7f916bb6c24f9a91bd7e4ec2fae5c7a42bc5526bda1bf7c76330f` |
| Independent readback and recovery fstab followup | `fbdc7a9262b9fd6cf60f89d8e6a55fdeaf082109b3237e3d5ab72a55d37d990b` |

No build inputs were switched by this audit. The evidence supports reviewing
factory-derived boot inputs while preserving the existing kernel/module
contract; full signing, policy, VINTF, recovery and device tests remain separate.

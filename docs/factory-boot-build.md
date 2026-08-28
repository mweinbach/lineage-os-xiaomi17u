# Factory-based v8 boot component build

The v8 **USER** build produced `init_boot.img`, `vendor_boot.img`, `dtbo.img`
and both init binaries. Inspection of a sealed host snapshot passed on
**2026-08-28 at 01:01:19 UTC**. The images retain the admitted Nezha DTB/DTBO,
all 430 vendor ramdisk modules and the selected factory fstab declarations.
**All three generated AVB blocks are unsigned. This is not a complete ROM,
a flashable release, or a device boot test.**

The build completed 6,551 Ninja actions for `lineage_nezha`, release `bp4a`,
variant `user`. Its source-policy results and limits are recorded separately
in [the USER security build record](../research/user-security-build.json).
The [boot inspection record](../research/factory-boot-build.json) contains
exact hashes, component metadata, tool pins and preserved inspector failures.
Raw images, binaries, CPIO streams, compiler evidence and logs remain ignored.

| Generated image | Bytes | SHA256 |
| --- | ---: | --- |
| `init_boot.img` | 8,388,608 | `eae81b09a6b6f5ee7c1901fef654e407b8d3776a5ec7682a3291f86c76475e0f` |
| `vendor_boot.img` | 100,663,296 | `b10bdb2e9f4e12b126982924e2b754717e37da739da2ad4d6f4192742471db86` |
| `dtbo.img` | 33,554,432 | `b166ce78ee67b970feb71e10b6123204c30f225b6b867023b75582eedf82fa35` |

These sizes fit the 8, 96 and 32 MiB limits from the
[package partition metadata](partition-metadata.md). Live phone capacity and
bootloader acceptance remain unverified. No other phone's layout was used.

`init_boot` has a v4, 1,584-byte header, 4,096-byte pages, no kernel and a
3,727,924-byte compressed ramdisk. Its zero boot-signature field does not
establish the state of AVB. The vendor header is v4 with a 2,128-byte header,
4,096-byte pages and one 108-byte type-1 ramdisk entry, offset zero, empty name
and sixteen zero board-ID words. Its compressed ramdisk is 18,106,953 bytes.

The vendor DTB section is byte-identical to the admitted 4,496,880-byte input
and contains eight Canoe trees. The DTBO table and its single 1,495,047-byte
overlay also match the admitted input. The complete generated DTBO image
differs because its container padding and AVB metadata were regenerated;
whole-image equality is not claimed. The 270-byte bootconfig preserves all
eight admitted values with no extra keys. It matches the sealed generated
file, but its ordering differs from the raw stock reference. The observed
vendor command line contains `bootconfig` twice; this is recorded unchanged,
without inferring its runtime effect.

Each image has an AVB hash descriptor whose salted SHA256 digest was checked
directly against the sealed image bytes and corroborated with the pinned
AOSP `avbtool`. Descriptor framing, property terminators and header bounds
were also checked. All three report algorithm **`NONE`**, flags **0**,
rollback index **0**, no authentication block and no embedded signature.
There is no engineering-key signature to authenticate in these images.
The generated fingerprint's `user/test-keys` tag is not a signature.
The `init_boot` AVB properties report Android 16 and security patch
`2026-02-01`; these are generated metadata, not a new stock or phone read.
A complete signed vbmeta chain and device rollback acceptance are still
required. No verification or rollback setting was changed on the phone.

| Expanded ramdisk | Bytes | CPIO occurrences | Unique paths in that image |
| --- | ---: | ---: | ---: |
| init_boot | 7,159,296 | 42 | 41 |
| vendor_boot | 48,229,632 | 440 | 440 |

Both streams have one complete archive. The init stream contains two literal
`dev` directory entries at header offsets 0 and 728. Both are mode `040755`,
UID/GID 0, link count 1, timestamp 0 and empty payload, with zero device fields.
Only their inode numbers and positions differ. The pinned
[mkbootfs implementation](https://raw.githubusercontent.com/Evolution-X/system_core/241488ea392c01079941d86ddc458b8a0c9ae6e1/mkbootfs/mkbootfs.cpp)
emits the `-n` node list before scanning directories, while the pinned
[build rule](https://raw.githubusercontent.com/Evolution-X/build/a438ca40c6ed779042f806142b1165ba1360a7b2/core/Makefile)
also creates a `dev` directory. This explains the observed pattern as a
source-supported inference, not a separately captured packaging invocation.

The inspector preserves both occurrences. It permits repeated directories
only with the same spelling, archive and metadata, ignoring inode numbers
and positions. Repeated files, symlinks, aliases, changed directory metadata
and non-directory ancestor conflicts are rejected. The reviewed Linux
6.12.23 unpacker is a semantic reference, not authenticated source for the
device kernel. No CPIO pathname or link was materialized or followed.

All **430 modules, totaling 47,961,360 bytes**, match the admitted input
hashes and the separately bound factory inventory. Their mode `0100644` and
UID/GID 0 also match the factory metadata. All six files—`modules.alias`,
`modules.blocklist`, `modules.dep`, `modules.load`, `modules.load.recovery`
and `modules.softdep`—are byte-identical to both the admitted files and the
sealed build-stage files. The normal list retains 157 entries / 154 unique
names; the recovery list retains 435 entries / 424 unique names. Ordering and
duplicates are preserved, and every listed module exists. This does not
prove ABI compatibility, signature trust or successful loading.

The generated `first_stage_ramdisk/fstab.qcom` is **5,850 bytes**, SHA256
`f1406e41b969daed6156892e2abafea20293a9e3cd532b7e42de6bf7ca7a987e`.
Its 29 rows, including 13 AVB rows, exactly match the admitted selection.
Every selected row retains its factory mount options, verification and
encryption flags. The full raw factory fstab was not adopted wholesale.
The file remains mode `0100644`, UID/GID 0. No mount, formatting or decryption
operation was performed.

None of the seven referenced `/avb/q-gsi.avbpubkey` through
`/avb/w-gsi.avbpubkey` paths appears in either generated CPIO, including the
checked `first_stage_ramdisk` alternatives. This limited absence does not
prove boot failure: the pinned
[first-stage mount flow](https://raw.githubusercontent.com/Evolution-X/system_core/241488ea392c01079941d86ddc458b8a0c9ae6e1/init/first_stage_mount.cpp)
and [fs_mgr AVB implementation](https://raw.githubusercontent.com/Evolution-X/system_core/241488ea392c01079941d86ddc458b8a0c9ae6e1/fs_mgr/libfs_avb/fs_avb.cpp)
distinguish normal chained AVB from alternative key and DSU paths. Unreadable
preloaded keys can be skipped and normal verification can be attempted after
standalone verification fails. Error handling also depends on actual device
unlock state. Runtime key availability, unlock state and the complete chain
were not verified; no flags were removed or unauthenticated keys added.

| Built binary | Bytes | SHA256 |
| --- | ---: | --- |
| First-stage init | 2,713,472 | `e1f34b1dc3473646ac55e56a9731b505a75e6d35fa2366d4c7cf54f016dedd54` |
| Second-stage init | 2,708,392 | `3a0001d2b6383a5a97861c288eb82241ae5b88d18b3811f16d7960230abf8ca7` |

Both are bounded AArch64 ELF files. The `init_boot` CPIO's `init` is exactly
the sealed first-stage binary, normalized to mode `0100750`, UID/GID 0.
The second-stage binary was captured from `system/bin/init`; packaging it
into a completed system image was not tested here. Neither binary was run.

Read-only Ninja command capture shows `SPOOF_SAFETYNET=0` for both the ramdisk
`first_stage_init.cpp` object and the normal `property_service.cpp` object.
The latter binds to the applied source hash
`d82faacbbeb80256a416ca81cb9c877def16c3140aa57f4126db41889a67a887`.
Exact object hashes, commands, source bytes and pinned LLVM symbol reports
are retained. The latest matching rows in the cumulative `.ninja_log` agree
with object timestamps inside the build interval. No pre-build log offset
was captured, so this is not proof of invocation membership, independent
object-to-binary linkage or a reproducible build. Symbol presence or absence
does not establish runtime identity behavior.

The sealed configuration has `Debuggable=false`, `Eng=false`,
`SelinuxIgnoreNeverallows=false`, `EnforceSELinuxTrebleLabeling=true` and an
empty Treble tracking-list path. Dexpreopt and uses-library checks remain
enabled. These settings do not prove every Treble test ran or that stock
policy is compatible. The separate USER security record reports two source
policy binaries with zero permissive domains, but the complete v8-plus-factory
composition still fails at five neverallow assertion sites and produces no
combined policy binary. This image inspection neither compiled nor replaced
that policy.

The first inspector attempt stopped on the repeated `dev` directory. The
second passed the CPIO and image-component checks, then stopped because the
inspector expected inline factory inventory entries. The factory receipt
actually binds a separate inventory file. Revision 3 verifies that file's
hash, size and complete summary before inspection; it keeps revision 2's
CPIO parser unchanged. Both earlier drivers, failures and staging directories
remain preserved. Neither inspector failure established firmware corruption.
The revised validator passes 86 offline tests, including the earlier parser
and AVB regressions, and its remaining-schema preflight used the actual
preserved data before the successful run.

The collector sealed 29 guest files after the build stopped, transferred
only those copies, and added two host LLVM reports. All 31 snapshot files,
152,380,776 bytes, passed readback. Validation rechecked 498 inputs and
30 generated output files totaling 83,599,532 bytes, excluding the final
receipt. Source and OUT were not modified by collection or inspection.

| Evidence | SHA256 |
| --- | --- |
| Sealed host snapshot | `a3873195eb76155a502208af5bc037cdaf740acc5df574eab43ef47312ef21e6` |
| Collection receipt | `9b86aeb8b08552c917caab318d2b2489bf5fd5858174cbc4f3490363e6e04c60` |
| Successful v3 validation receipt | `cff12cd8e5fc60290758c3c6c2e2a70ebce4f1f22982d345feec4e4a83d9a8e3` |

The factory archive's origin remains user-provided and unverified. Byte
equality does not upgrade the historical Xiaomi.eu kernel bundle's failed
AVB result. See [factory boot inputs](factory-boot-contract.md) and
[input reuse](factory-input-reuse.md) for those provenance boundaries.
Complete policy/VINTF integration, release signing and boot-chain validation,
a full ROM build, recovery work and explicitly authorized device tests remain.
No TWRP image or native feature was tested, and a custom recovery would not
protect the bootloader itself; the [recovery plan](recovery-plan.md) retains
that distinction. The phone was not accessed by this build inspection.

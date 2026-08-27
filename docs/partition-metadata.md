# Factory-package partition metadata

The factory-named China archive now supplies a verified package layout for
Nezha: **160 fixed partition extents across six LUNs**, plus six unresolved
growth entries. The GPT, rawprogram XML and partition XML agree on the fixed
extents. This closes the gap between an image's length and its declared package
partition size. It does **not** measure the connected phone's capacities or
admit these GPT templates for flashing.

The input is the [intake-verified TGZ](factory-firmware-intake.md) with SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
Its origin remains recorded as user-provided and unverified. On 2026-08-27,
the earlier bounded capture preserved exactly **37 inert files, 805,356 bytes**:
six each of `gpt_mainN.bin`, `gpt_backupN.bin`, `gpt_bothN.bin`,
`gpt_emptyN.bin`, `rawprogramN.xml` and `patchN.xml`, plus
`partition_ext_p1.xml`. The complete archive stream passed TAR header and gzip
integrity checks during capture. Installers, programmer executables and other
files were not extracted by this operation.

The inspection completed at **21:35:57 UTC**. An independent implementation
then rechecked the header and array CRCs using explicit byte offsets, compared
every fixed extent against the XML and rehashed the capture. It also confirmed
that all 37 metadata files under the user's newly supplied
`sources/nezha_images_OS3.0.309.0.WPACNXM_16.0/images/` match the archive capture
byte for byte. That comparison covers only these metadata files, not the rest
of that directory.

The [sanitized record](../research/partition-metadata.json) includes all 166
named entries, their LUNs, LBAs, lengths and roles, with no raw disk or partition
identifiers. The complete parser output and all original files remain ignored.

| Partition names | Package LUN | Bytes per partition | Stored image bytes |
| --- | ---: | ---: | ---: |
| `boot_a`, `boot_b` | 4 | 100,663,296 (96 MiB) | 100,663,296 |
| `init_boot_a`, `init_boot_b` | 4 | 8,388,608 (8 MiB) | 8,388,608 |
| `vendor_boot_a`, `vendor_boot_b` | 4 | 100,663,296 (96 MiB) | 100,663,296 |
| `recovery_a`, `recovery_b` | 4 | 104,857,600 (100 MiB) | 104,857,600 |
| `dtbo_a`, `dtbo_b` | 4 | 33,554,432 (32 MiB) | 23,068,672 (22 MiB) |
| `vbmeta_a`, `vbmeta_b` | 4 | 131,072 (128 KiB) | 12,288 |
| `vbmeta_system_a`, `vbmeta_system_b` | 0 | 131,072 (128 KiB) | 4,096 |
| `super` | 0 | 15,300,820,992 | 12,438,543,008, sparse |

Both slots have equal package extents where listed. The image column refers
to the one image of that basename in the archive, not a measurement of either
live slot. In particular, the 22 MiB DTBO image must not be mistaken for a
22 MiB partition. The sparse super header's expanded length also matches the
package super extent; this metadata operation does not inspect its chunks,
logical partitions or filesystems.

The remaining fixed extents are recorded in full, including boot-chain
partitions, `metadata`, `persist`, modem calibration partitions and `rescue`.
Their presence is information for preserving the device layout, not a request
to overwrite them or include them in a ROM installation.

| Package LUN | Fixed extents | Terminal placeholder | GPT entry capacity |
| --- | ---: | --- | ---: |
| 0 | 33 | `userdata` | 64 |
| 1 | 9 | `last_parti` | 32 |
| 2 | 9 | `last_parti` | 32 |
| 3 | 3 | `last_parti` | 32 |
| 4 | 98 | `last_parti` | 128 |
| 5 | 8 | `last_parti` | 32 |

Here, LUN means the package XML's `physical_partition_number`. XML physical
partitions occur in the same order, and all six rawprogram files declare
**4,096-byte sectors**. This is not an independently observed mapping to the
phone's live block-device names.

The inspector validates each GPT header CRC with the header CRC field zeroed,
and each entry-array CRC over its declared count times entry size. It checks
the array's location relative to the header, reserved padding, partition name
encoding, identity consistency, extent ordering, XML sector/byte arithmetic
and the bounded fragment format. These semantics follow the
[UEFI GPT specification](https://uefi.org/specs/UEFI/2.11/05_GUID_Partition_Table_Format.html).
All **30 header/array CRC pairs** pass: 24 in the main, backup and combined
fragments, plus six in the empty templates. All six primary/backup entry
arrays match. Each `gpt_bothN.bin` exactly matches its corresponding main bytes
followed by backup bytes. This is an observed property of these GPT fragments,
not permission to concatenate Android sparse super fragments.

CRC integrity must be kept separate from usable geometry. The six empty GPT
templates declare first usable LBA 34, last usable LBA 0 and alternate header
LBA 0. Their named `empty` entry has a zero partition-type GUID, which marks it
unused; there is no active partition in those templates. Passing CRCs do not
make that reversed usable range a valid disk layout. The protective MBRs also
use `0xffffffff` sector counts, which are not capacity measurements.

The nonempty templates deliberately leave a terminal entry with start LBA one
greater than end LBA, yielding zero sectors. LUN 0's `userdata` has a nonzero
type GUID. The five `last_parti` entries have zero type GUIDs and are unused as
GPT partitions. The partition XML requests **15,032,385,536 bytes (14 GiB)**
for userdata, but also declares `GROW_LAST_PARTITION_TO_FILL_DISK=true`; its
GPT and rawprogram forms contain the zero-size placeholder. Neither the XML
request nor a template's last LBA establishes actual userdata or UFS capacity.

All six patch XMLs were parsed as inert data: **156 rows**, including
**102 rows referring to `NUM_DISK_SECTORS`** and **48 CRC recalculation
requests**. Their syntax is recognized by a small literal grammar. No disk
sector count was supplied, no expression was evaluated, no CRC update was
applied, and no GPT was repaired or rewritten. The inspector rejects malformed
or unsupported fields instead of guessing their meaning.

The reusable commands are:

```sh
python3 scripts/gpt_metadata.py capture \
  --intake artifacts/firmware/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b \
  --expected-sha256 d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b \
  --output artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b/gpt-metadata-capture-v1

python3 scripts/gpt_metadata.py inspect \
  --capture artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b/gpt-metadata-capture-v1 \
  --expected-sha256 d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b \
  --expected-capture-sha256 3b97ce32e078481b80f4ff1c460193f70cf1a711549e85f937f71edfab489386 \
  --output artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b/gpt-metadata-analysis-v1
```

Both example outputs now exist and are deliberately refused on rerun. A new
inspection must use a new ignored output directory. A newly repeated capture
also has its own receipt hash, which must be supplied to its inspection. The
original capture receipt is preserved despite the later addition of the
inspection code.

The tool bounds each metadata input to 1 MiB and the 37-file total to 2 MiB.
It accepts only regular files, validates source hashes and file identity,
rejects symlink paths and unsafe archive members, and atomically publishes a
fresh output without replacing an existing directory. XML is UTF-8 only, with
bounded element counts, depth and attributes; DTDs, entities and unsupported
schemas are refused. Tests use synthetic GPT/XML/TAR inputs and cover corrupt
CRCs, overflow, expressions, inconsistent descriptions, mutations, symlinks,
FIFOs and publication races without a phone or network.

Review found that Python's TAR iterator can treat a corrupt later header as
end-of-archive. The shared reader now propagates malformed, truncated and
missing header errors instead; only a genuine zero end-marker retains EOF
behavior. A regression test places a bad-checksum header after all 37 selected
members and confirms that no successful output is published. This fix also
protects the image-only fastboot extractor.

At **21:55–21:56 UTC**, a separate strict pass rehashed the original TGZ and
verified all **127 cataloged members**, the full **15,325,941,760-byte** gzip
output, two end-markers and zero padding. It streamed hashes for all **37
metadata files and 19 images**, matching the original receipts. It made no
new image or metadata copies. The original capture, inspection and image
receipts remain unchanged; this additional receipt corroborates their actual
inputs with the corrected reader.

| Receipt | SHA256 |
| --- | --- |
| Original 37-file capture | `3b97ce32e078481b80f4ff1c460193f70cf1a711549e85f937f71edfab489386` |
| Bounded inspection | `18c98f119761417a0ff11a7a107a713fce6fd7a99b9bb1288b300387fa7fcf3d` |
| Complete inspection output | `f979ef51db85fa97556d68bdd00140bf3a731024899441a0d5f2785caa5a84cb` |
| Independent checks and extracted-directory comparison | `94b3525a182a1576e0ec0d8910318f37a80693714c9bcf2beac41bff0d100cd1` |
| Strict full-archive corroboration after TAR reader fix | `362e50ef12a10ca2c648093e6049d170065bcad9490dbc1ac262fe1ba0016327` |

These package sizes can now support reviewed device and recovery image
budgets without borrowing another phone's layout. No existing build inputs
were changed by this audit. Live capacity, slot behavior, unlock status,
rollback constraints and a separately authorized recovery test remain distinct
requirements before any phone modification. No phone, guest VM or firmware
executable was accessed by this metadata inspection.

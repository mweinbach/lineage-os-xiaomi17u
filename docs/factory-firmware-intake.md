# Factory-named China firmware intake

On **2026-08-27 at 20:55–20:59 UTC**, the complete fastboot TGZ now present in
`sources/` passed local intake, full TAR/GZIP validation and guarded image
extraction. Its original and separate intake copy match. All **19 image files**
passed SHA256 readback, then an independent pass rehashed the original and every
published image again. Nothing was installed or executed, and the phone and
build guest were not accessed.

The filename is
`nezha_images_OS3.0.309.0.WPACNXM_20260714.0000.00_16.0_cn_1081d3072b.tgz`.
It is **12,778,943,953 bytes**, with SHA256:

```text
d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b
```

The matching [Xiaomi CDN reference URL](https://bigota.d.miui.com/OS3.0.309.0.WPACNXM/nezha_images_OS3.0.309.0.WPACNXM_20260714.0000.00_16.0_cn_1081d3072b.tgz)
and its advertised length were recorded in the earlier
[firmware source investigation](firmware-source.md). They do not prove that
this particular local file came from that URL. Intake therefore records
`source_kind: user-provided`, `source_url: null`, and
`origin_verified: false`. No independently published SHA256 or authenticated
Xiaomi signing-key identity has been obtained. Device/build/region fields are
declared labels at this stage, not a verification of embedded build properties.
“Factory-named” describes the archive label, not an authenticity conclusion.

This result supersedes the earlier inability to read the completed-looking
Downloads file. It does not replace or relabel the partial CLI downloads or
the separately supplied [modified Xiaomi.eu package](provided-firmware.md).

The preserved copy is under `artifacts/firmware/` in the directory named by the
full digest above. The image output is:

```text
artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b/archive-images/
```

The [intake tool](firmware-intake.md) checked a regular nonsymlink input,
stable file identity, bounded copies and a separate copy's readback hash. It
had 1,389,409,792,000 bytes free before intake. Original inode, size, mtime and
ctime stayed unchanged through intake and extraction; ordinary access-time
behavior is not controlled.

The [TAR extractor](fastboot-extraction.md) checked the entire
**15,325,941,760-byte decompressed stream**, gzip CRC/length trailer, TAR header
checksums and zero end padding. Its catalog contains **127 members**: 125 files
and two directories. Only regular image members were written: 19 files totaling
**14,852,407,336 bytes**. Installers, programs, links and TAR ownership/mode
metadata were not applied. A successful run atomically published a fresh
directory; existing outputs were not overwritten. The source and every image
also passed an independent check after publication at 20:58:39–20:58:51 UTC.

The exact operations were:

```sh
python3 scripts/firmware.py \
  sources/nezha_images_OS3.0.309.0.WPACNXM_20260714.0000.00_16.0_cn_1081d3072b.tgz \
  --device nezha --build OS3.0.309.0.WPACNXM --region CN \
  --source-kind user-provided

python3 scripts/firmware_tar.py \
  --intake artifacts/firmware/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b \
  --expected-sha256 d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b \
  --output artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b/archive-images
```

The second command intentionally refuses the now-existing output; any separate
reproduction must use a new ignored directory. The orchestration bounded intake
to 600 seconds and extraction to 900 seconds. Both exited zero well inside
those limits. Extraction retained the tool's 64 GiB image-total, 128 GiB
decompressed-stream, 20,000-member and 1 MiB trailing-padding limits.

The important image-level observations are:

| Image | Stored bytes | Comparison with the Xiaomi.eu image of the same name |
| --- | ---: | --- |
| `boot.img` | 100,663,296 | Exact SHA256 match |
| `init_boot.img` | 8,388,608 | Exact SHA256 match |
| `vendor_boot.img` | 100,663,296 | Different SHA256 |
| `dtbo.img` | 23,068,672 | Exact SHA256 match |
| `recovery.img` | 104,857,600 | Exact SHA256 match |
| `vbmeta.img` | 12,288 | Exact SHA256 match |
| `vbmeta_system.img` | 4,096 | Exact SHA256 match |
| `super.img` | 12,438,543,008 | One sparse image; Xiaomi.eu instead supplied 15 overlays |

The new `vendor_boot.img` hash is
`c98aebae56e098eee6e758b8ac387ffd6dd5ec2cf051b389e97ae77d7a3404d3`.
The Xiaomi.eu counterpart's retained hash is
`20349b30fe10cb30f75579f1f02f7dd26bcb3b0af543bd261a5877634991854d`.
This is a concrete difference to investigate with the
[boot/AVB tooling](boot-contract.md); these observations do not claim its AVB
signature or image digest was checked by the intake operation.

The new `super.img` hash is
`fe2c6b4abe4a36c871be184350132dfed1aa1b32ada0b051923a19835affa8f5`.
Its sparse **header only** declares version 1.0, 4,096-byte blocks, 3,735,552
expanded blocks, 220 chunks and checksum zero, for 15,300,820,992 expanded
bytes. Sparse chunks, logical metadata and filesystems require separate
validation. Neither this expanded length nor a boot image's length measures
the phone's physical partition capacity. The stored `vm-bootsys.img` also
differs in hash and length; the TGZ representation is sparse while the earlier
Xiaomi.eu image was raw, so the difference alone does not establish different
expanded contents.

The catalog contains **37 inert geometry candidates** under
`nezha_images_OS3.0.309.0.WPACNXM_16.0/images/`: six each of
`gpt_mainN.bin`, `gpt_backupN.bin`, `gpt_bothN.bin`, `gpt_emptyN.bin`,
`rawprogramN.xml`, and `patchN.xml` for N=0–5, plus `partition_ext_p1.xml`.
Their exact names and lengths are in the public record. They were not extracted
or parsed by this image-only intake. A separate bounded review can inspect
their checksums and package layout without applying XML patch instructions.
`qsahara_device_programmer.xml` was cataloged but not extracted or executed.

The [sanitized record](../research/factory-firmware-intake.json) binds every
image hash and tool hash to the ignored receipts. Key receipt SHA256 values are:

| Receipt | SHA256 |
| --- | --- |
| Intake run | `0528661ff1663d5266108721dbc42f80326d0ba04fae69009e59bc717310d29f` |
| Immutable intake metadata | `db2ba223b00c75522e7252eaff27729305876a187f16c7407a8471f844df53eb` |
| Archive image extraction | `c0686eab1092809faad2c865662a8616e9eea5492c7afd0e7bfcae8447a74567` |
| Independent original/image readback | `e926dab3183de7d0d3fb36321b30cfbc89c605b8ba7b0fca8e45618c430582ba` |

These checks establish local bytes and archive integrity. They do not admit a
flashable partition set, establish OEM provenance, verify phone fit, or prove
kernel, SELinux, VINTF or feature compatibility. No existing build inputs or
the modified-baseline evidence were changed by this intake.

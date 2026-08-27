# Firmware intake

`scripts/firmware.py` preserves an existing local firmware package and its
provenance for bring-up research. It does not download firmware, connect to a
phone, extract images, run included programs, unlock a bootloader, or flash
anything. A successful intake does not establish that a package belongs to this
phone, authenticate its publisher, or establish that Evolution X can boot it.
Stock and modified ROM packages must keep distinct provenance.

## Select an exact stock baseline

Before obtaining a package, verify the physical phone's product/device identity,
hardware variant, firmware region, and installed build from stock evidence. Do
not infer the region from a language setting, shipping address, or the name
"Xiaomi 17 Ultra" alone. Keep the package URL, original filename, full build
identifier, and any independently published checksum together. This tool records
the supplied identity; it cannot prove that the identity matches the package.

Do not download a guessed regional variant. Do not substitute a related phone's
firmware, partition table, kernel, or vendor blobs. An official bootloader unlock
path remains a separate prerequisite before attempting a custom ROM; intake does
not authorize or perform an unlock.

Package labels are significant, but inspect the contents rather than trusting the
filename extension:

| Package | What to establish before using it for research |
| --- | --- |
| Stock fastboot package, commonly a `.tgz`/`.tar.gz` | Confirm which partition images it contains and whether dynamic partitions are bundled in a `super` image. Treat any included `.bat` or `.sh` flashing scripts as evidence to inspect later, never as intake commands. Do not assume the package contains every partition. |
| Stock recovery/OTA package, commonly a `.zip` | Determine whether this is a full package or an incremental update and whether images are represented by an update payload. An incremental package can depend on an exact source build and is not interchangeable with a complete set of images. |

Android documents the separation between
[fastboot partition operations](https://android.googlesource.com/platform/system/core/+/refs/heads/main/fastboot/README.md)
and [OTA update processing](https://source.android.com/docs/core/ota/ab).
Xiaomi's [MIUI security white paper](https://trust.mi.com/docs/miui-security-white-paper-global/2/6)
describes package integrity and signature checks during stock updates; it is
background on MIUI's updater, not evidence of this phone's current HyperOS
partition layout or supported recovery procedure.

## Preserve a package

From the workspace root, replace every example value with verified evidence:

```sh
python3 scripts/firmware.py '/absolute/path/to/original-stock-package.tgz' \
  --device 'VERIFIED_STOCK_PRODUCT' \
  --build 'EXACT_STOCK_BUILD' \
  --region 'VERIFIED_FIRMWARE_REGION' \
  --source-url 'https://official-source.example/original-stock-package.tgz'
```

If a checksum is available from an independent trusted source, add
`--expected-sha256` followed by its 64 hexadecimal characters. This is optional
because not every publisher supplies SHA256. A locally computed checksum detects
changes to the package; by itself it does not establish authenticity. The default
provenance mode is `--source-kind url`, which requires `--source-url`. That URL
must use HTTPS and must not contain user credentials or a fragment. Use a stable
provenance URL without login tokens or expiring signed credentials. The tool
records the supplied URL but does not verify that the file was downloaded there.

### A user-provided package with unknown download origin

If the user supplies a local file and its download origin is not known, select
that provenance explicitly rather than inventing a URL:

```sh
python3 scripts/firmware.py '/absolute/path/to/user-provided-package.zip' \
  --device 'VERIFIED_PRODUCT' \
  --build 'DECLARED_FIRMWARE_BUILD' \
  --region 'VERIFIED_BASELINE_REGION' \
  --source-kind user-provided \
  --inspect
```

Only `--source-kind user-provided` permits an omitted URL. Its schema-version-2
metadata records `source_kind: "user-provided"`, `source_url: null`, and
`origin_verified: false`. An optional supplied URL must still pass the same
HTTPS checks and does not change `origin_verified` to true. This mode is not a
claim of official firmware, trustworthy authorship, or verified download origin.
Device, build, and region values remain declared provenance and must be compared
with embedded metadata; a matching filename is not independent verification.

Default URL-mode metadata retains the existing schema version 1 and remains
compatible with previously accepted packages. A repeated intake cannot silently
change the provenance mode, add a previously unknown origin, or rewrite the
original receipt. See [the provided Xiaomi.eu package](provided-firmware.md) for
a concrete record that distinguishes its filename/build label from embedded
metadata and from official Xiaomi firmware.

The destination is fixed relative to this repository, regardless of the current
working directory:

```text
artifacts/firmware/<sha256>/
  <original-basename>
  metadata.json
```

`artifacts/` is ignored by Git. Keep proprietary packages and reports there and do
not force-add them. Intake preserves the input file's contents and modification
time; normal filesystem access-time behavior is outside its control. It creates
a separate copy, so allow at least the package's size in free disk space.

Metadata contains the original basename, SHA256, byte length, declared device,
build, region, source URL (or explicit null for unknown user-provided origin),
schema version, and UTC collection timestamp. User-provided metadata additionally
records its provenance mode and the unverified origin status. JSON
printed to stdout includes those fields, output paths, and whether an existing
copy was reused. Input paths are not stored in metadata.

Copying and hashing use bounded chunks. The tool writes a temporary directory
beside the final checksum directory, checks that the input remained stable, and
rehashes the temporary copy to verify its integrity. It then publishes the
completed directory with an atomic rename. It never overwrites a previously accepted package or
metadata. Ordinary failures remove the temporary copy, not the input.

Repeating the same command rehashes both the input and stored package and preserves
the original metadata. A conflicting filename or provenance for identical bytes
is rejected instead of creating another copy or silently changing the first
record. Corrupted stored bytes or metadata require investigation; the tool does
not silently replace evidence. It also rejects empty inputs, nonregular files,
input symlinks, symlinks in destination paths, control characters in metadata,
unsafe basenames, and the reserved basename `metadata.json`.

The process exits nonzero on a checksum mismatch, invalid metadata, copy failure,
integrity failure, or unsupported archive inspection. A checksum mismatch is
detected before creating the artifact directory. A per-checksum lock prevents
concurrent intake of the same package. If the process is forcibly killed, it may
leave an ignored `.lock` file and temporary `.intake-*` directory. Preserve these
until confirming no intake process is running; inspect and remove only that
interrupted tool's temporary state before retrying. These checks are designed for
a local workspace, not a filesystem being changed by an adversarial process.

## Inventory without extraction

Add `--inspect` to the same intake command to include ZIP or TAR member metadata
in the stdout JSON. `.tgz`/`.tar.gz` are supported. The report lists entry names,
sizes, types, and lexical path hazards. TAR link targets are listed; ZIP symlinks
are identified from metadata without reading their target contents.

Inspection never extracts files or runs flashing scripts. An `unsafe_path` flag
identifies paths such as `../outside`, absolute paths, and Windows drive paths.
The absence of a flag does not mean a member is safe to extract or execute.
Archive parsing is not a firmware signature check, payload validation, or device
compatibility check.

Inventories are limited to 20,000 entries. ZIP parsers still read the central
directory, and scanning compressed TAR archives can require reading and
decompressing the whole archive to reach subsequent headers. Inspect trusted
packages on a host with sufficient time, memory, and disk capacity. Inventory
output is not added to immutable metadata; request it again on a later intake
without recopying the package. A package successfully copied before an inspection
error remains preserved, while the command exits nonzero for the inspection
failure.

## What comes next

Intake is not a complete phone backup. It does not collect personal data,
device-specific calibration, modem state, keys, or any other live partition.
Keeping a vendor firmware archive is not evidence that a phone can be restored
after a failed flash.

The next separate task is to inspect the exact package format and plan a verified,
offline extraction pipeline. Payloads, sparse images, dynamic partitions, and
filesystems need different tools; Android's
[dynamic partition documentation](https://source.android.com/docs/core/ota/dynamic_partitions/implement)
explains the logical partitions contained in `super`. This intake tool deliberately
does not implement extraction.

Every later extracted APK, library, configuration file, or image should point
back to this package SHA256 and record its own hash and extraction method. Keep
an entire stock dependency set tied to one exact device, region, and build;
mixing camera apps, HALs, framework components, and firmware from different
releases can hide the actual compatibility problem. Stock camera, display,
charging, haptics, and other feature retention remain unverified until tested
reproducibly on the exact device. Keep SELinux enforcement and verified-boot and
rollback constraints in the design.

## Offline tests

```sh
python3 -m unittest discover -s tests -v
```

Firmware tests create temporary local fixtures and exercise checksums,
idempotence, corruption, filename and metadata validation, explicit unknown-origin
provenance, legacy URL metadata compatibility, symlink rejection, partial-copy
cleanup, concurrency locks, and ZIP/TAR inventories. They require
only Python's standard library and neither a network connection nor a phone.

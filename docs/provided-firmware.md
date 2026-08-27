# User-provided Xiaomi.eu firmware

On **2026-08-27**, the user supplied
`sources/xiaomi.eu_NEZHA_OS3.0.309.0.WPACNXM_16.zip`. It was preserved with the
[firmware intake tool](firmware-intake.md), inventoried, and checked locally.
**This is a user-provided Xiaomi.eu package with an unverified download origin,
not an authenticated official Xiaomi factory package.** No URL was invented.

The original remains in `sources/`. Intake verified its contents, copied them
atomically, and rehashed the separate copy. The original's inode, size,
modification time, and change time remained unchanged. No installer, bundled
fastboot executable, or script was executed; no phone or container was accessed.
No image was extracted to a file.

## Exact receipt

| Field | Recorded value |
| --- | --- |
| Original basename | `xiaomi.eu_NEZHA_OS3.0.309.0.WPACNXM_16.zip` |
| Full package size | **9,914,891,416 bytes** |
| Full package SHA256 | `b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69` |
| Provenance | `source_kind=user-provided`, `source_url=null`, `origin_verified=false` |
| Metadata schema | `2` |
| Declared device / build / baseline region | `nezha` / `OS3.0.309.0.WPACNXM` / `CN` |
| ZIP entries | **84** |
| Total declared uncompressed member bytes | **12,086,043,767** |
| Full ZIP CRC verification | **Passed for all 84 entries**, streaming to memory in 20.66 seconds |

The preserved package and immutable `metadata.json` are under:

```text
artifacts/firmware/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69/
```

Detailed ignored receipts are:

```text
artifacts/provided-firmware/intake-20260827T160808Z.json
artifacts/provided-firmware/inspection-20260827T161034Z.json
```

The CRC check used 4 MiB buffers and a 120-second bound. It completed normally;
no verification process remains running. The central directory contains no
duplicate names, paths flagged as unsafe by the intake checker, or encrypted
entries. The stored package's file metadata remained unchanged throughout
inspection. CRC and SHA256 demonstrate local integrity, not publisher
authenticity, signing-key ownership, flash safety, or ROM compatibility.

## Embedded identity and its limits

Only small text entries and short sparse-image headers were inspected for
identity/layout. Installer text was read only for device assertions and ROM
labels, never executed.

`META-INF/com/android/metadata` is 727 bytes and has SHA256
`be7a4225b2313f406fd2afabe564c3d9e74d5d4fb013d941ce70a0f73349aae9`.
It records:

| Embedded field | Value |
| --- | --- |
| `pre-device` | `nezha` |
| Android / `post-sdk-level` | Android `16` in the build fingerprint / `36` |
| `post-security-patch-level` | `2026-07-01` |
| `post-build-incremental` | `16OS3.1.260714.203507406.QCPECN.S` |
| `ota-type` | `AB` |

The full recorded build fingerprint is:

```text
Xiaomi/nezha/nezha:16/BP2A.250605.031.A3/16OS3.1.260714.203507406.QCPECN.S:user/release-keys
```

The updater script and the small Linux/macOS/Windows upgrade scripts assert
`nezha`. Upgrade-script text identifies Xiaomi.eu. The public build label
`OS3.0.309.0.WPACNXM` was **not found in the inspected small text metadata**;
it is the supplied filename's label and matches the connected installation's
reported build in the [device baseline](device-baseline.md). Keep that declared
public label separate from the embedded internal incremental above. The `CN`
receipt records the target hardware/base-build region, not a claim that this
modified package is official China firmware.

## Actual package layout

| Archive area | Observed contents |
| --- | --- |
| `images/` | 66 entries: 51 `.img` files and 15 numbered sparse `super` fragments |
| Boot chain inputs | `boot.img`, `init_boot.img`, `vendor_boot.img`, `dtbo.img`, `recovery.img`, `vbmeta.img`, `vbmeta_system.img`, and other firmware images |
| Dynamic partition input | `images/super.img.0` through `images/super.img.14` |
| `META-INF/` | Four update metadata/installer entries |
| `bin/` | Five bundled platform binaries/libraries; none executed |
| Root scripts | Nine Linux/macOS/Windows format, install, and upgrade scripts; none executed |
| `payload.bin` | **Absent** |
| Monolithic `images/super.img` | **Absent** |

Every numbered `super` member begins with an Android sparse version 1.0 header,
uses 4,096-byte blocks, and declares 3,735,552 blocks: **15,300,820,992 bytes** of
expanded address space. They are not plain consecutive byte slices. Do not
blindly concatenate their ZIP member contents into one image.

The retained OTA metadata includes payload byte-offset fields naming
`payload.bin`, `payload_properties.txt`, and other entries that are not in this
ZIP's central directory. Those fields are inconsistent with the actual repacked
layout and must not be used as extraction offsets or treated as evidence that
an OTA payload is present.

## Next agent boundary

This receipt is ready for offline bring-up research. A separate reviewed task
must reconstruct the sparse `super` representation with tooling that supports
this format, inspect its logical partition metadata, and plan any filesystem
extraction. Record each resulting file's hash and its parent package SHA256.
No reconstruction or filesystem extraction has happened yet.

Keep this modified-ROM package and the live Xiaomi.eu camera/application
snapshot distinct from the [official Xiaomi firmware source](firmware-source.md).
The package is not a complete backup of the phone or device-specific calibration.
Do not mix its images with another device, region, or build, disable signature or
artifact checks, or infer that any native feature already works on Evolution X.

The tooling change adds explicit `--source-kind user-provided` while preserving
the previous default URL mode and schema-1 receipts. **41 firmware unit tests
passed** after that code change. The parent workflow owns the final full-suite
run and commit; there are no ongoing edits or hardware operations from this
intake task.

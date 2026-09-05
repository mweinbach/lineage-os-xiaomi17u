# Authorized Android preflight — September 5, 2026

The user confirmed the connected Nezha in direct response to the request for a
read-only USB preflight. One matching USB ADB device was identified and its
serial/transport pinned in private evidence. **No flashing, wiping, rooting,
rebooting, unlocking or slot change was requested or performed.** No VM or
signing operation was needed.

The phone is running Android, not recovery or bootloader mode. The base
collector finished with `partial-observations`, exit 3, and no collection
errors. Unsupported reads were not counted as passed checks.

| Observation | Current evidence |
| --- | --- |
| Device | Xiaomi / `nezha` / `canoe`, SM8850, reported `CN` hardware |
| Running slot | A |
| Android state | Boot complete; zygote and SurfaceFlinger running |
| Existing ADB privilege | UID 2000; no elevation attempted |
| Page size / SELinux | 4,096 bytes / Enforcing |
| Framework and vendor version | Both report `OS3.0.309.0.WPACNXM` |
| Data | File-based encryption reported; `/data` and `/metadata` mounted |
| Battery | Reports 54%, charging; no stopped-updates marker |
| Android lock properties | `locked`, flash lock `1`, verified-boot state `green` |

The Android lock values **do not independently establish bootloader state**.
They must not be treated as proof that this development-key bundle can be
flashed. Matching version strings likewise do not prove retained firmware
payload identity or that an unmodified factory ROM is running.

## What this mode could not supply

All 19 direct physical-capacity reads and `/proc/bootconfig` were denied to the
existing Android shell. The partition symlinks and block-device major/minor
tuples were readable; the denials do not mean partitions are absent or too small.

A separate bounded supplement attempted only the ten relevant A/retained/Super
sysfs `dev`, `size` and `partition` attributes, twice. It tied decimal device
numbers to the already observed hexadecimal stat tuples and rechecked device,
mode, region, slot, USB transport and physical-node identity. All 60 sysfs reads
were denied. **Every capacity therefore remains unknown.** No raw block bytes
were read and no alternative privileged access was attempted. The supplement
uses Linux's read-only [partition attributes](https://github.com/torvalds/linux/blob/v6.12/block/partitions/core.c);
it does not modify the base collector or suppress its unknowns.

The base collector records 106 commands / 212 streams. The supplement records
131 commands / 262 streams, including 71 successful commands and 60 denied
sysfs reads. Independent review rehashed every saved stream, with no mismatch
or truncation. This is real device observation, distinct from the earlier
4,602-test offline tooling run; no unrelated test suite was rerun for this
read-only collection and documentation change.

Private evidence, containing serials and raw logs, remains ignored:

- `evidence/device-preflight-20260905T031715Z-android-a/manifest.json`:
  `49b19887a58313c3daf4e794c1548871999ff8ba6e9f06966f3adea00b800819`
  (90,216 bytes).
- `evidence/device-sysfs-preflight-20260905T032149Z/manifest.json`:
  `84f139965da75431ba6f5a09a5280efc567b674e5b2095cd888f0288f52994d4`
  (106,868 bytes).

## Next gate

An explicitly authorized reboot into the proprietary bootloader is needed to
read its independent unlock state, next-boot slot, capacities and supported
snapshot status. No mode transition has been authorized by the read-only
collection request. Bootloader entry would not authorize flashing, wiping,
unlocking, slot changes or recovery transitions.

Retained firmware payloads, LP/snapshot state, secure rollback uncertainty,
bootloader return behavior, backups and data handling remain separate gates.
An already mounted `/metadata` does not prove snapshot idleness. Package7's
verified bundle is unchanged; `flash_ready` and `complete_rom_ready` remain false.

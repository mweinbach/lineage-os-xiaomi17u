# Collecting private stock evidence

`scripts/collect_stock.py` captures the currently installed firmware through
read-only ADB commands. It does **not** unlock, relock, reboot, root, flash,
install software, write settings, or change the phone. It requires Python 3 and
Android platform-tools on the host. ADB must already be authorized on the
specific phone the user has selected; the collector cannot authorize itself.

This is an inventory and research snapshot, **not a phone backup, a complete
firmware dump, a proprietary-blob extraction, or a ready-to-build device tree**.
Running it on Xiaomi.eu records Xiaomi.eu's current system alongside whatever
vendor/ODM firmware is installed. It does not establish that the phone is
running untouched OEM firmware, that its bootloader is officially unlockable,
or that any feature will work on Evolution X.

## Select and verify the phone

Both `--serial` and `--expected-device` are required. The collector never picks
the first attached phone, even if only one is connected. It checks the selected
device is authorized, rejects emulators, verifies the manufacturer is Xiaomi,
and compares `ro.product.device` exactly with the supplied expected codename.
It stops before collecting other evidence if any of those checks fail.

Use a codename independently corroborated for the exact phone and variant;
matching a string is not a substitute for establishing its identity. For an
explicitly identified phone, these commands are read-only and help verify its
currently reported identity:

```sh
adb devices -l
adb -s YOUR_DEVICE_SERIAL shell getprop ro.product.manufacturer
adb -s YOUR_DEVICE_SERIAL shell getprop ro.product.device
adb -s YOUR_DEVICE_SERIAL shell getprop ro.product.model
```

Do not post the device inventory: it contains serials. Recheck physical identity
if the reported model or codename disagrees with the expected device. Never copy
a different phone's partition layout, kernel, or firmware to get past a mismatch.

Previewing the collection needs neither ADB nor a connected phone and creates
no files:

```sh
python3 scripts/collect_stock.py \
  --serial PREVIEW \
  --expected-device VERIFIED_CODENAME \
  --dry-run
```

After replacing both placeholders with verified values, run:

```sh
python3 scripts/collect_stock.py \
  --serial YOUR_DEVICE_SERIAL \
  --expected-device VERIFIED_CODENAME
```

The default destination is a new timestamped directory inside ignored
`evidence/`. `--output evidence/your-collection-name` selects another **new**
directory; existing directories are refused to avoid mixing or overwriting
evidence. `--adb /path/to/adb` selects a platform-tools installation. Each command
times out after 30 seconds by default; `--timeout SECONDS` changes that limit,
and directory/APK pulls have a minimum timeout of 120 seconds.

## What is collected

The default collection is deliberately bounded:

- An allowlist of product identity, board/SoC, Android/version/security-patch,
  system/vendor/ODM fingerprints and incremental versions, Xiaomi region/build
  markers, current slot, and verified-boot/lock-state properties. It never runs
  an unrestricted `getprop`. Modified firmware may mask boot-state properties;
  a reported `locked` or `green` value does not establish the actual bootloader state.
- Kernel identity, memory page size, SELinux mode, read-only partition listings and `lpdump`,
  device-tree model/compatible strings, system features, system package paths,
  overlays, Android services, and `lshal` where permitted.
- Copies of VINTF and permission XML directories under `system`, `system_ext`,
  `product`, `vendor`, and `odm`. ADB permission failures and absent directories
  are recorded; the collector does not try to gain more privilege.

An empty property means the property returned no value. It does not prove a
feature is unsupported, a partition is absent, or a boot-state claim is true.
Package names and service names provide leads for dependency research, not proof
that transplanting an APK will retain a feature.

For deeper hardware diagnosis, explicitly add `--include-dumpsys`. It captures
only the named camera, display, sensors, audio/audio-policy, thermal, power, and
battery services. These reports may expose client package names, recent activity,
or other personal information. Neither the default nor this option runs full
`dumpsys`, `logcat`, or a bugreport.

Private APK copies are also a separate opt-in:

```sh
python3 scripts/collect_stock.py \
  --serial YOUR_DEVICE_SERIAL \
  --expected-device VERIFIED_CODENAME \
  --pull-stock-apks
```

This attempts `com.android.camera` only. To select from the fixed allowlist,
repeat `--apk-package com.android.camera` and/or
`--apk-package com.miui.gallery` with `--pull-stock-apks`. These package names
are candidates, not a claim they exist on every firmware. A package must first
appear in the **system** package inventory, and every returned APK path must be
under an allowlisted stock partition. `/data/app` updates, user-installed apps,
app data, traversal paths, and arbitrary package names are refused. Split APKs
are copied when all returned paths pass validation. Missing requested packages
are marked skipped and make the collection partial.

The APK option does not collect dependent native libraries, framework code,
signatures, calibration, licenses, or app data. Camera retention requires
separate analysis of the exact device's camera HAL, vendor dependencies,
framework hooks, permissions, and SELinux policy, followed by hardware tests.

## Provenance, privacy, and incomplete reads

`manifest.json` records the selected device serial, expected and observed
identity, timestamps, collector script SHA-256, options, every command and exit
status, and SHA-256/size receipts for captured output and pulled files. The
manifest is updated as collection progresses. Every command has separate stdout
and stderr files, including failures and partial output from timeouts. Partial
pulls are retained and hashed without treating them as complete transfers.

Evidence directories are private to the host account, output files use mode
`0600`, and each collection contains a defensive `.gitignore`. Do not force-add
these files to Git or upload them without review and permission. The collector's
terminal summary redacts the selected serial; the private manifest and raw ADB
inventory deliberately retain local provenance and may include other connected
device serials. Your shell history may also contain the serial you supplied.

The final status and exit code have distinct meanings:

| Exit | Status | Meaning |
| --- | --- | --- |
| `0` | `complete` | Every requested command/pull succeeded. This does not certify feature support or firmware authenticity. |
| `0` | dry run | No phone access and no files written. |
| `2` | `preflight_failed` or local error | Device selection/identity failed, ADB was unavailable, options were invalid, or output could not be written. |
| `3` | `partial` | At least one command/pull failed, timed out, produced no expected output, or an explicitly requested APK was skipped/refused. |
| `130` | `interrupted` | Collection was interrupted; keep and inspect the evidence already saved. |

Permission-denied reads such as `lpdump`, unavailable `lshal`, and missing ODM
directories can legitimately produce `partial` on a healthy phone. Review the
manifest instead of treating those errors as reasons to root or modify the
device. An abruptly killed process or a full disk can leave `collecting` without
a completion timestamp; that is also incomplete evidence, never a success.

Offline tests mock every process call, including directory and APK transfers:

```sh
python3 -m unittest discover -s tests -v
```

These tests verify collection safety and bookkeeping. They do not validate a
ROM build or replace testing hardware behavior on the exact Xiaomi 17 Ultra.

# Evolution X for Xiaomi 17 Ultra

An unofficial bring-up workspace for **Xiaomi 17 Ultra (`nezha`), China hardware**,
starting from **Evolution X Android 16 QPR2 (`bka`)** and investigating retention
of Xiaomi's camera and other native features.

**The research/setup tooling works. A complete ROM source sync, a buildable
Nezha device tree, and a flashable ROM are not present yet.** No phone should be
unlocked, wiped, or flashed as part of workspace setup.

## What is already here

- Nine pinned source/reference checkouts, including Evolution X's official
  manifest and product configuration, Lineage extraction and Xiaomi hardware
  tools, Google's Repo launcher, and clearly labeled incomplete device/common
  tree references. Exact URLs and revisions are in
  [`config/sources.json`](config/sources.json).
- Tested source-fetch, host-check, Linux initialization/sync, firmware-intake,
  and read-only phone-collection tools. No third-party Python packages are needed
  for workspace tests.
- A real read-only baseline from the connected phone: `nezha`, SM8850 / `canoe`,
  HWC `CN`, Xiaomi.eu `OS3.0.309.0.WPACNXM`, Android 16, 6.12.23 kernel, 4 KB
  pages, and enforcing SELinux. See
  [`docs/device-baseline.md`](docs/device-baseline.md).
- Private local evidence: the camera APK, 432 XML files, hardware/service/package
  inventories, and 575 verified hash receipts. The collection accurately records
  three permission-denied reads as incomplete. Raw evidence and proprietary
  files are ignored by Git.
- Source-gap research and a concrete feature dependency/test matrix. Camera
  preview or APK installation alone will not establish Leica feature parity.
- Matching official China firmware URLs and acquisition receipts. Download
  attempts were stopped because the official CDNs were too slow; only clearly
  labeled partial files exist. No full firmware package has been accepted yet.

The local Mac is the control/research host. Full Android builds require Linux
on x86-64 and a case-sensitive filesystem. The current Mac/ARM64/APFS directory
does not pass those requirements; no full platform sync or emulated build was
started here. The [build-host guide](docs/build-host.md) covers the Linux path.

## Start here

```sh
make help
make test
make doctor
make verify
make source-plan
```

`make refs` reproduces the small reference checkouts without downloading the
full Android platform. It verifies existing checkouts instead of discarding
local changes. Reference downloads skip Git LFS assets; build-source sync does
not. Do not mistake these references for a complete Android source tree.

On an appropriately provisioned Ubuntu 24.04 x86-64 build host:

```sh
bash scripts/setup-linux.sh --install
make refs
make doctor SOURCE_DIR=/srv/android/evolution
make init SOURCE_DIR=/srv/android/evolution
make sync SOURCE_DIR=/srv/android/evolution JOBS=8
```

This gets the **platform**, not a complete Nezha product. `init` and `sync`
enforce the host checks and preserve local work. The platform manifest is pinned;
its branch-based project revisions become fully recorded after a successful
sync saves a resolved manifest. No unverified device manifest is activated.

## Stock evidence and native features

Preview collection without touching a device:

```sh
make stock-plan
```

For a verified, authorized phone, replace the serial placeholder explicitly:

```sh
python3 scripts/collect_stock.py --serial YOUR_DEVICE_SERIAL --expected-device nezha
```

The collector does not choose the first attached phone, elevate privileges,
reboot, flash, or pull user data. Camera APK copies and detailed dumpsys reports
are separate options. Do not publish raw evidence. The installed Xiaomi.eu
system is a modified baseline; its global-looking model and reported boot-state
properties do not independently establish physical variant or bootloader state.

| Guide | Purpose |
| --- | --- |
| [Device baseline](docs/device-baseline.md) | Sanitized findings from this phone |
| [Source research](docs/device-research.md) | Verified branches, device-tree defects, kernel gaps |
| [Native features](docs/native-features.md) | Camera/Leica, IMS, fingerprint, charging, display, audio, accessories |
| [Captured camera](docs/camera-baseline.md) | Actual APK, native library dependencies, framework hooks and camera HAL declarations |
| [Stock collection](docs/stock-evidence.md) | Read-only capture, privacy, and partial-result handling |
| [Firmware intake](docs/firmware-intake.md) | Preserve local ROM packages and provenance without executing scripts |
| [Matching firmware](docs/firmware-source.md) | Verified Xiaomi CDN URLs, partial download status, and safe resumption requirements |
| [Build host](docs/build-host.md) | Linux requirements, platform sync, and future build gates |

## What must happen before building or testing the ROM

1. Establish the exact official China firmware baseline and extraction inputs,
   separately from the Xiaomi.eu app snapshot.
2. Complete the Nezha product/common/vendor/kernel dependencies. The public
   Nezha scaffold has a missing product makefile, stale model identity, and
   absent vendor/kernel inputs. Other-device partition/AVB settings must not
   be copied into an active configuration.
3. Sync the platform on a supported Linux x86-64 host, integrate reviewed device
   sources, and validate VINTF, kernel-module compatibility, and enforcing policy.
4. Compile and test hardware features in stages, with a separately authorized
   recovery/backup plan before any device changes. No native feature is currently
   claimed to work on Evolution X.

The Git history keeps the setup, source tools, firmware intake, collector, and
verified research in separate commits. This folder intentionally retains its
original `lineage-os-xiaomi17u` name; the selected ROM is Evolution X.

Setup validation on 2026-08-27: **108 offline tests passed**, all **nine** pinned
reference checkouts verified clean, and a real **manifest-only** Repo
initialization passed with signature verification and matching manifest/Repo
commits. That metadata smoke test did not sync projects or compile Android.

# Evolution X for Xiaomi 17 Ultra

An unofficial bring-up workspace for **Xiaomi 17 Ultra (`nezha`), China hardware**,
starting from **Evolution X Android 16 QPR2 (`bka`)** and investigating retention
of Xiaomi's camera and other native features.

**The research/setup tooling and local Apple Container builder work. Evolution X
has fully synced in its Linux volume, with all 1,179 project revisions verified. A
buildable Nezha device tree and a flashable ROM are not present yet.** No phone
should be unlocked, wiped, or flashed as part of workspace setup.

## What is already here

- Twelve pinned source/reference checkouts, including Evolution X's official
  manifest and product configuration, Lineage extraction and Xiaomi hardware
  tools, Google's Repo launcher, AOSP boot/AVB/DTBO inspectors, and clearly labeled incomplete device/common
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
- Matching official China firmware URLs and acquisition receipts. Official CDN
  attempts remain partial. The user separately supplied a Xiaomi.eu ZIP under
  `sources/`; its separate intake copy and all 84 ZIP entries passed integrity
  checks. Its download origin is unverified, and it is not authenticated Xiaomi
  factory firmware. See [the supplied-package receipt](docs/provided-firmware.md)
  for its hash and the difference between its filename and embedded build label.
- Verified extraction of all 66 supplied image members, reconstruction of the
  15 sparse super overlays, and extraction of eight populated logical images.
  Independent tools produced matching hashes, and all eight EROFS checks passed.
  **Retained AVB metadata fails against vendor_boot and all eight logical
  images.** These are modified research inputs, not a valid signed image set.
- Exact boot/kernel/DTBO and module evidence, plus 13 camera dependency seeds
  with file/image hashes. The package's Camera APK matches the live snapshot.
  Physical boot-partition sizes, module ABI compatibility and a viable device
  product remain unresolved.

This Mac can also host the Linux build environment through **Apple Container +
Rosetta**. The working configuration uses a pinned Ubuntu 24.04 ARM64 image,
amd64 runtime libraries, 16 vCPUs, 128 GiB RAM and an 800 GiB persistent ext4
volume. An x86-64 probe and a freshly crosscompiled program ran successfully.
The actual AOSP Android 16 Ninja prebuilt, with its matching bundled libraries,
also built a small x86-64 C program that executed successfully under Rosetta.
After sync, the downloaded Clang/LLD, Ninja, JDK 21 and Go passed 13 standalone
checks, including compilation and execution of C, Java and Go programs.
Source lives at `/work/evolution` inside that volume, with output and cache
alongside it. This verifies useful Android host-tool execution, not a full
Android 16 ROM build or compatibility with every prebuilt. See the
[Apple Container guide](docs/apple-container.md) for the receipt and sync checks.

## Start here

```sh
make help
make test
make doctor
make verify
make apple-status
make apple-plan
```

`make apple-status` inspects the latest operation without attaching another VM.
The source sync is already complete; do not repeat setup or sync to resume this
checkout. For a new environment only, with an idle volume, the setup sequence is:

```sh
make apple-setup
make apple-init
make apple-sync-bg JOBS=8
make apple-status
```

Only a generated control bundle is mounted read-only. Source/output/cache stay
on Linux ext4; no host home directory, credentials, or phone evidence is shared.
The wrapper refuses a second writer VM. Do not prune or delete the named volume.

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

Both container and native Linux workflows get the **platform**, not a complete
Nezha product. `init` and `sync` enforce their explicit host checks and preserve
local work. The platform manifest is pinned;
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
| [Supplied Xiaomi.eu package](docs/provided-firmware.md) | Verified local integrity, unverified origin, embedded identity and sparse super layout |
| [Firmware analysis](docs/firmware-analysis.md) | Verified sparse reconstruction, logical layout and filesystem checks |
| [Boot/kernel/AVB contract](docs/boot-contract.md) | Exact boot formats, modules, DTs and retained verification failures |
| [Nezha integration plan](docs/nezha-integration.md) | Future device/vendor/kernel boundaries and product activation gates |
| [Build host](docs/build-host.md) | Linux requirements, platform sync, and future build gates |
| [Apple Container](docs/apple-container.md) | Verified local Rosetta workflow, persistent storage, task status and limits |

## What must happen before building or testing the ROM

1. Establish the exact official China firmware baseline and resolve the
   supplied modified package's AVB inconsistencies. Preserve the Xiaomi.eu app
   snapshot and dependency evidence separately; do not repair verification
   failures by disabling checks or copying its modified fstab.
2. Complete the Nezha product/common/vendor/kernel dependencies. The public
   Nezha scaffold has a missing product makefile, stale model identity, and
   absent vendor/kernel inputs. Other-device partition/AVB settings must not
   be copied into an active configuration.
3. Validate Android build orchestration on the prepared host, integrate reviewed
   device sources into the verified platform checkout, and validate VINTF,
   kernel-module compatibility, and enforcing policy.
4. Compile and test hardware features in stages, with a separately authorized
   recovery/backup plan before any device changes. No native feature is currently
   claimed to work on Evolution X.

The Git history keeps the setup, source tools, firmware intake, collector, and
verified research in separate commits. This folder intentionally retains its
original `lineage-os-xiaomi17u` name; the selected ROM is Evolution X.

The offline suite covers source safety, both host modes, container boundaries,
firmware intake, and private device evidence. All twelve pinned references were
verified. The completed platform sync preserved signature checks and the
manifest/Repo pins. Every project HEAD, clean worktree and remote matched the
[resolved snapshot](research/source-snapshots/evolution-bka-20260827.xml), and all
99 Git LFS files passed content-hash verification. The
[source verification record](research/source-sync.json) remains separate from
device build results; no complete Android ROM build has been claimed.

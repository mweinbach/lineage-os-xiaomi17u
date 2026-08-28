# Evolution X for Xiaomi 17 Ultra

An unofficial bring-up workspace for **Xiaomi 17 Ultra (`nezha`), China hardware**,
starting from **Evolution X Android 16 QPR2 (`bka`)** and investigating retention
of Xiaomi's camera and other native features.

**Evolution X has fully synced in its Linux volume, with all 1,179 project
revisions verified. An authored Nezha product passes Soong/Kati configuration
and has built ARM64 libbase, all nine selected Camera dependency modules and
the host VINTF/policy tools. Boot, DTBO and both DLKM images also build and
pass their recorded content checks. A flashable ROM is not present.** No phone
should be unlocked, wiped, or flashed as part of workspace setup.

## What is already here

- Fourteen pinned source/reference checkouts, including Evolution X's official
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
- Matching official China firmware URLs and acquisition receipts. Earlier CLI
  downloads remain partial. The separately supplied factory-named TGZ is now
  readable under `sources/`; its full archive and all 19 extracted images passed
  integrity checks. Its selected Android AVB chain and all eight logical
  filesystems pass, without establishing an authenticated Xiaomi trust root.
  See [factory validation](docs/factory-firmware-validation.md). The earlier
  [Xiaomi.eu ZIP](docs/provided-firmware.md) remains a separate modified input,
  with its own provenance, hashes and embedded build-label discrepancy.
- Verified extraction of all 66 supplied image members, reconstruction of the
  15 sparse super overlays, and extraction of eight populated logical images.
  Independent tools produced matching hashes, and all eight EROFS checks passed.
  **That Xiaomi.eu package's retained AVB metadata fails against vendor_boot and all eight logical
  images.** These are modified research inputs, not a valid signed image set.
- Exact boot/kernel/DTBO and module evidence, plus 13 camera dependency seeds
  with file/image hashes. The package's Camera APK matches the live snapshot.
  Factory GPT/XML now supplies exact package partition extents, including
  32 MiB DTBO despite its 22 MiB image. Live phone capacities and complete module
  ABI compatibility remain unresolved.
- An authored product with `lineage_nezha-bp4a-userdebug` and
  `lineage_nezha-bp4a-user` choices, verified private vendor/kernel bundles, and
  exact Nezha DTS source roundtrips. Both variants have completed their recorded
  framework checks. The current candidate explicitly adopts factory vendor/ODM
  images and factory fstab flags; earlier builds retain their original inputs.
  See [build progress](docs/build-progress.md) for results and the separate
  complete-ROM/device-testing gates.
- A [complete captured-module CRC/provider audit](docs/module-provider-audit.md):
  every recorded expectation has a matching kernel or module candidate across
  the captured pool. Stage availability, actual loading, signature trust and
  full ABI compatibility remain separate checks.

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
| [Community bring-up](docs/community-bringup.md) | Later XDA release, Leica port reports, private-tree and firmware limits |
| [MiCode kernel review](docs/micode-popsicle-review.md) | Exact shared kernel/KMI evidence and remaining Nezha board gaps |
| [Kernel configuration audit](kernel/xiaomi/nezha/config-audit/README.md) | All 812 explicit ACK requests match stock; separate DDK comparisons and preservation assertions |
| [Native features](docs/native-features.md) | Camera/Leica, IMS, fingerprint, charging, display, audio, accessories |
| [Captured camera](docs/camera-baseline.md) | Actual APK, native library dependencies, framework hooks and camera HAL declarations |
| [Stock collection](docs/stock-evidence.md) | Read-only capture, privacy, and partial-result handling |
| [Firmware intake](docs/firmware-intake.md) | Preserve local ROM packages and provenance without executing scripts |
| [Fastboot extraction](docs/fastboot-extraction.md) | Bounded TAR/GZIP image extraction with hashes and full-stream integrity checks |
| [Matching firmware](docs/firmware-source.md) | Verified Xiaomi CDN URLs, partial download status, and safe resumption requirements |
| [Factory intake](docs/factory-firmware-intake.md) | Separate user-provided China TGZ, preserved original and verified extraction |
| [Factory validation](docs/factory-firmware-validation.md) | Independent sparse reconstruction, logical layout, passing selected AVB chain and EROFS checks |
| [Factory boot contract](docs/factory-boot-contract.md) | Exact ramdisks, headers, DTs, enforcing fstab differences and preserved module bytes |
| [Factory framework contract](docs/factory-framework-contract.md) | VINTF/XML and policy comparison without assuming framework compatibility |
| [Factory input reuse](docs/factory-input-reuse.md) | Receipt-bound factory inputs, unchanged dependencies and explicit mixed provenance |
| [Partition metadata](docs/partition-metadata.md) | Verified package GPT/XML extents, growth placeholders and live-capacity limits |
| [Supplied Xiaomi.eu package](docs/provided-firmware.md) | Verified local integrity, unverified origin, embedded identity and sparse super layout |
| [Firmware analysis](docs/firmware-analysis.md) | Verified sparse reconstruction, logical layout and filesystem checks |
| [Boot/kernel/AVB contract](docs/boot-contract.md) | Exact boot formats, modules, DTs and retained verification failures |
| [VINTF and permissions](docs/vintf-contract.md) | Guarded filesystem captures, exact live XML matches and framework compatibility gates |
| [Actual VINTF validation](docs/vintf-validation.md) | Successful vendor/ODM and active APEX load/merge; separate framework-definition and compatibility limits |
| [Vendor APEX dependencies](docs/apex-dependencies.md) | Guarded CAS, Widevine and Wi-Fi payload inspection and matching active-package evidence |
| [SELinux contract](docs/selinux-contract.md) | Exact stock policy inputs and seven strict neverallow failures; no policy or device pass claimed |
| [User policy integration](docs/selinux-user-integration.md) | Five remaining combined-policy assertion sites, source ownership and enforcing-policy requirements |
| [Hardened user build](docs/user-security-build.md) | Actual v8 component build, two unfiltered zero-permissive source binaries and separate factory-policy failure |
| [Build progress](docs/build-progress.md) | Authored Nezha product, actual Kati result, module compilation and private input receipts |
| [Boot/DLKM build](docs/boot-dlkm-build.md) | Four built engineering images, exact kernel/overlay and 484 preserved module payloads |
| [Nezha integration plan](docs/nezha-integration.md) | Device/vendor/kernel boundaries and remaining complete-ROM gates |
| [Camera build inputs](docs/camera-inputs.md) | Narrow system-ext dependency selection, requested ELF checks and unresolved APK class-loader requirements |
| [Camera APK integration](docs/camera-apk-integration.md) | Verified signature/layout and exact Java, privilege and packaging requirements before importing the APK |
| [DEX runtime provider](docs/dex-import-uses-library.md) | Tested strict Soong patch for DEX shared libraries; guest integration still pending |
| [ZRAM module plan](docs/zram-module-plan.md) | Distinct vendor/GKI providers, ordered loader behavior and selector requirements |
| [Kernel exports](docs/kernel-export-contract.md) | Independently decoded stock kernel exports and selected module CRC matches |
| [Module providers](docs/module-provider-audit.md) | All 914 captured instances, matching global provider candidates and stage/loading limits |
| [Recovery plan](docs/recovery-plan.md) | TWRP after core ROM bring-up, correct Nezha layout and bootloader-protection limits |
| [Build host](docs/build-host.md) | Linux requirements, platform sync, and future build gates |
| [Apple Container](docs/apple-container.md) | Verified local Rosetta workflow, persistent storage, task status and limits |

## What remains before a complete ROM or phone test

1. Complete source authentication and live partition/bootloader verification.
   The supplied factory package already passes its selected AVB chain and
   filesystem checks; that does not authenticate its origin or measure this
   phone. Preserve the Xiaomi.eu failures separately. The current candidate
   uses the factory fstab declarations without disabling verification.
2. Complete the authored Nezha product's hardware, policy and signing integration.
   Safe framework/module checks already have a registered product. The public
   Nezha scaffold has a missing product makefile, stale model identity, and
   absent vendor/kernel inputs. Other-device partition/AVB settings must not
   be copied into an active configuration.
3. Extend the successful Android module and partial-image builds to a complete
   product, resolving assembled-framework VINTF, module stage/dependency
   requirements and the remaining enforcing-policy failures.
4. Compile and test hardware features in stages, with a separately authorized
   recovery/backup plan before any device changes. No native feature is currently
   claimed to work on Evolution X.

The Git history keeps the setup, source tools, firmware intake, collector, and
verified research in separate commits. This folder intentionally retains its
original `lineage-os-xiaomi17u` name; the selected ROM is Evolution X.

The offline suite covers source safety, both host modes, container boundaries,
firmware intake, and private device evidence. All fourteen pinned references were
verified. The completed platform sync preserved signature checks and the
manifest/Repo pins. Every project HEAD, clean worktree and remote matched the
[resolved snapshot](research/source-snapshots/evolution-bka-20260827.xml), and all
99 Git LFS files passed content-hash verification. The
[source verification record](research/source-sync.json) remains separate from
device build results; no complete Android ROM build has been claimed.

# Build host and source workflow

The earlier claim that this Mac could only be a control/research host was too
narrow. **Apple Container with Rosetta is now configured and has passed the
workspace's execution and filesystem checks on this Mac.** It runs an ARM64
Linux guest with translated x86-64 Linux tools and a named ext4 source volume.
An actual AOSP Android 16 Ninja prebuilt and its matching bundled libraries
also built a standalone x86-64 C program that then executed successfully.
The full platform sync completed there; all 1,179 project revisions, clean
worktrees and remotes, plus all 99 LFS payload hashes, passed independent
verification. The unmodified Soong entry point also compiled four x86-64 host
tools and successfully queried `OUT_DIR`. The authored Nezha product now also
passes Soong/Kati configuration and has built ARM64 `libbase.so` plus the
x86-64 host `checkvintf` tool. The actual Ninja process was observed under nsjail.
A complete Android 16 ROM build is not yet verified. See the
[Apple Container workflow](apple-container.md) for the observed configuration,
Ninja artifact hashes, receipt, commands, and status checks.

Native Linux x86-64 remains the default host mode and the environment described
by [AOSP's requirements](https://source.android.com/docs/setup/start/requirements).
The Apple route is an explicit experiment, not native x86-64 execution or
official AOSP support for macOS. The ordinary Mac APFS checkout is still case
insensitive; the Android checkout lives on the guest's ext4 volume, not this
host directory. The original Ninja test used the guest's
`x86_64-linux-gnu-gcc` cross-compiler. A subsequent set of 13 checks used the
downloaded Clang/LLD, Ninja, JDK 21 and Go to compile and execute standalone host
programs; Clang also produced an Android ARM64 object. All passed, with hashes
and source commits in [the host-tool record](../research/apple-host-tools.json).
Neither test built an Android module. The later
[Soong bootstrap record](../research/soong-bootstrap.json) establishes compilation
of `soong_ui`, `mk2rbc`, `rbcrun` and `release-config`, plus execution of `soong_ui`.
It used a fresh output directory and the existing prebuilt Toybox `uname` through
a command-scoped PATH. Native guest architecture remained `aarch64`; no source
or system tool was patched. All 1,179 source projects remained clean at their
resolved revisions afterward.

That `OUT_DIR` query uses a fast path without Kati or product configuration.
Normal Soong startup includes source discovery, but this probe did not capture
a separate finder artifact receipt. The subsequent Nezha product query did
exercise Kati and returned the expected device, architecture and API levels.
A later
[standalone sandbox test](../research/apple-sandbox.json) ran Ninja/Clang and a
host program under the upstream nsjail arguments, with source writes refused
and network interfaces isolated. A subsequent real Nezha module build passed;
the actual Ninja namespace observation found source mounted read-write under
the initial product configuration. The newer board setting requires read-only
source for subsequent checks. The shell `lunch` helper, remaining host tools and
a complete ROM still need separate validation. The pinned Soong
source disables its basic dumpvars/Kati/Soong sandbox upstream and permits a
Ninja fallback after an nsjail failure. No sandbox setting was changed by the
probe, and a future fallback must count as failed sandbox validation. See the
[bootstrap proof and repeat command](apple-container.md#soong-bootstrap-proof-and-sandbox-limit)
for exact receipts, source references and limits.

For the native route, use Ubuntu 24.04 LTS with 64 GiB RAM
and at least 400 GiB free on a case-sensitive filesystem. Budget 600 GiB or more
for the source, outputs, firmware, and compiler cache. These are conservative
workspace checks; AOSP specifies x86-64 Linux, 400 GB disk, and 64 GB RAM.
Source includes host JDK
and other prebuilts; do not choose a random system Java version to fix builds.

## Use the prepared Apple Container environment

Start with status, because a detached sync may already be using the volume:

```sh
python3 scripts/apple_container.py status
python3 scripts/apple_container.py sync --jobs 8 --detach --dry-run
```

The preview does not launch a second sync. The actual wrapper rejects another
VM attachment while the project volume is in use. Use the
[full runbook](apple-container.md) for setup, smoke tests, synchronization and
an interactive shell. The initial sync's older immutable bundle could report
zero projects before `.repo/project.list` existed; that display was not evidence
of an empty download. The original task has now completed and stopped naturally.
For later running tasks, inspect logs and Git storage in the owning VM before
diagnosing a failure. Do not run the native Ubuntu package installer on macOS.
The wrapper selects `--host-mode apple-rosetta` inside the verified Linux guest;
the default `workspace.py` mode remains `native`.

## Prepare a native Linux machine

Copy or clone this small Git repository to the Linux machine. Do not copy a
partially populated Android tree from a case-insensitive volume. The reference
checkouts are ignored and can be reproduced there.

```sh
bash scripts/setup-linux.sh --print
bash scripts/setup-linux.sh --install
make refs
make test
make doctor SOURCE_DIR=/srv/android/evolution
python3 scripts/workspace.py doctor --source-dir /srv/android/evolution --require-build-host
```

The package installer targets Ubuntu 24.04 and checks the OS/CPU before running
APT. GnuPG is required so Repo signature verification cannot silently be skipped.
It does not change global Git configuration, enable swap, start containers,
or install packages on macOS. Choose a directory writable by your build user.
The doctor is a prerequisite check, not a guarantee every Android dependency is
installed or enough resources are assigned inside a container.

## Fetch the platform on native Linux

The selected platform is Evolution X **Android 16 QPR2, branch `bka`**. The
[upstream README](https://github.com/Evolution-X/manifest/blob/bka/README.mkdn)
documents `repo init`, `lunch lineage_codename-bp4a-userdebug`, and `m evolution`.
The manifest's default branch is now `cnb` (Android 17). This workspace explicitly
pins `bka`; it does not silently follow the default branch or the removed `bq2`
branch found in older search results.

```sh
make source-plan SOURCE_DIR=/srv/android/evolution
make init SOURCE_DIR=/srv/android/evolution
make sync SOURCE_DIR=/srv/android/evolution JOBS=8
```

`init` pins the exact manifest and Google's Repo tool commits in
[`config/sources.json`](../config/sources.json). It retains Repo's signature
verification. Initialization runs without an interactive terminal; configure
your normal Git author identity on the Linux host beforehand.
`sync` downloads the full platform, including Git LFS objects,
without destructive force flags, manifest updates, or Repo self-updates. It
verifies both the installed `.repo/repo` implementation and manifest origin/SHA,
not only the external launcher. It saves a `repo manifest -r` snapshot under
ignored `reports/` only after sync succeeds. The Apple wrapper uses the same
checks; its reports live in the selected control snapshot on the persistent
volume, as described in [apple-container.md](apple-container.md).
The initial manifest pin is **not**
a complete dependency lock: most upstream project entries reference branches.
Preserve the resolved snapshot with each build, and review it before committing
a sanitized version for reproducible handoff.
The completed 2026-08-27 checkout now has an
[exact archival snapshot](../research/source-snapshots/evolution-bka-20260827.xml)
and [verification record](../research/source-sync.json). It remains outside the
active manifest selection; it does not register a Nezha target.

Reference fetches (`make refs`) deliberately skip large Git LFS assets. They
are useful for review and are **not** the complete build checkout. Existing
references with changed revisions, remotes, or local edits are rejected instead
of reset. Preserve your local edits in a branch or a separate checkout before
refreshing a pin. New reference fetches are staged and verified before publication;
a failed transfer does not leave an incomplete checkout at its final path.
Retry `make refs` after a network failure. An interrupted **platform init** can
still leave incomplete `.repo` metadata; preserve that directory for diagnosis
and use a new empty source directory instead of resetting it.

The source wrapper currently allows only the pinned `default.xml` and refuses
unreviewed `.repo/local_manifests` or a legacy local manifest. It also refuses
nested Repo trees. Adding a real device manifest requires a deliberate update
to that validation policy after the device dependencies are reviewed; never
delete an existing user's manifest merely to get past a preflight failure.

## Complete ROM requirements and current module checks

The platform workflow now accepts a verified native Linux host or the explicitly
selected Apple/Rosetta experiment. The authored Nezha profile passes product
configuration; a complete Xiaomi 17 Ultra ROM is not yet verified. The public
candidate `nezha` and `sm8850-common`
checkouts under `upstream/` are quarantined references. They are **not** copied
to `device/` and no local manifest activates them. See
[`device-research.md`](device-research.md) for the concrete defects.

Before adding a device manifest, derive and verify all of the following against
this phone and its matching stock package:

1. A complete `device/xiaomi/nezha` product and compatible SM8850 common tree,
   including VINTF manifests, overlays, init files, and enforcing SELinux policy.
2. Exact boot-chain/partition/slot layout, page size, dynamic-partition groups,
   firmware requirements, and rollback constraints.
3. A matching kernel/GKI strategy, device DTB/DTBO, and loadable vendor modules.
   A kernel release for another Xiaomi 17 model is not sufficient evidence.
4. Proprietary vendor/device blobs extracted from the selected, recorded stock
   firmware, including camera/IMS dependencies and their compatibility fixes.
5. Evolution product integration. The selected manifest installs
   `Evolution-X/vendor_evolution` at **`vendor/lineage`**, not `vendor/evolution`.

The authored framework profile is already installed and its product
configuration passed. The checks above still govern a complete ROM, not
whether local compiler validation may proceed. Inside the existing owning
Apple Container VM, this command repeats the verified product query:

```sh
cd /work/evolution
env PATH="$PWD/prebuilts/build-tools/path/linux-x86:$PATH" \
  OUT_DIR=out-nezha-framework-20260827T1835Z \
  TARGET_PRODUCT=lineage_nezha TARGET_RELEASE=bp4a \
  TARGET_BUILD_VARIANT=userdebug \
  build/soong/soong_ui.bash --dumpvars-mode \
  '--vars=TARGET_DEVICE TARGET_ARCH TARGET_BOARD_PLATFORM BOARD_AVB_ENABLE'
```

See [build progress](build-progress.md) for module checks and subsequent fixes.
Do not invoke full-ROM/OTA targets on this framework-only profile; its complete
partition and signing integration has not been admitted.

Do not run copied device-tree extraction or build scripts until their contents
have been reviewed. A successful compilation is not permission to flash. Device
testing requires a separate recovery/backup plan and explicit user instruction.

For native-feature work, Android's [VINTF documentation](https://source.android.com/docs/core/architecture/vintf)
explains how framework and vendor requirements must agree. The
[GKI overview](https://source.android.com/docs/core/architecture/kernel/generic-kernel-image)
describes the kernel/vendor-module boundary. Neither makes arbitrary vendor
images or another model's kernel modules interchangeable.

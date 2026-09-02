# Apple Container and Rosetta build environment

**The Mac can run this project's experimental Linux build environment.** The
previous native-Linux-only conclusion was too broad. ARM64 Ubuntu tools run in
Apple Container, while Rosetta handles x86-64 Linux executables. Source and
output live on a persistent Linux ext4 volume. This preserves the distinction
between a usable local environment and a verified complete Android 16 ROM build.

At the **2026-09-02 17:45:04 UTC cleanup checkpoint**, host availability is
**293,727,363,072 bytes (273.56 GiB)**. After 40 exact obsolete guest scratch
files were removed, the user-approved temporary `CAP_SYS_ADMIN` maintenance
container successfully trimmed already-free ext4 blocks. The same builder was
restored with its original configuration and the temporary container removed;
the active raw volume remains 1,024 GiB. This adds **164.93 GiB of observed host
free space**, separate from the guest's 99.18 GiB deletion. The earlier
unprivileged trim failed and remains recorded as a failure. See the
[cleanup record](storage-cleanup.md) for bounded preservation checks and exact
space accounting; this is not a new Android build or complete integrity proof.

At the **2026-09-02 17:16:46 UTC host-cleanup checkpoint**, the detached old
800 GiB raw snapshot has been **deleted with explicit approval to lose that
rollback copy**. The current managed 1,024 GiB volume and small maintenance
receipts remain intact. Removing the snapshot and ten verified duplicate
crosscheck image bodies leaves **122,636,726,272 bytes (114.21 GiB)** available
on the host at that checkpoint. This exceeds the unchanged 100 GiB reserve,
not the full follow-on build budget. See the [cleanup record](storage-cleanup.md)
for exact deletions, preservation checks and measured APFS space recovery.

The historical **2026-09-01 02:14:58 UTC maintenance checkpoint** expanded the
existing `evolution-nezha-work` volume from **800 to 1,024 GiB** offline, then
restarted the same builder, `twrp-nezha-upstream74-20260829`. The original 800 GiB
raw image and volume metadata were retained through APFS clone/swap; this was
**not an independent physical backup**. Initial preen exits 1 and remains
failed; separate confirmation, growth and postcheck return native exit 0.
Complete old/grown raw-image hashes
are recorded, without claiming semantic equivalence of every filesystem object.
Post-restart checks verify aarch64, case-sensitive ext4, Rosetta Ninja, the same
539 source files across thirteen projects, strict 4 KiB settings, and unchanged
inactive staged inputs. Available space is **402,047,229,952 bytes**, above the
unchanged **226,459,516,499-byte** staging budget including its **200 GiB reserve**.
This is a dated capacity observation, not reserved space. The same builder is
the sole observed volume user; no replacement VM, source sync, adoption or
Android build is part of this maintenance. The
[maintenance evidence](../research/workspace-integration.json) preserves the
receipts and limits; [current status](workspace-status.md) tracks the pending
source adoption and packaging. The older setup observations below remain dated.

At the **2026-08-29 cleanup checkpoint**, the sole active source-volume VM was
`twrp-nezha-upstream74-20260829`, using the same image and `evolution-nezha-work`
volume recorded below. `/work/evolution` remains present; the manifest, Repo
and all 1,179 project revisions/remotes were checked. The existing three
patched projects were preserved, and `build/make` now also carries the reviewed
prebuilt-recovery consumer. The [integration record](../research/workspace-integration.json)
binds this audit to the recovery changes. This is not a new source sync or a
complete ROM build. The host's
`last-task.json` still names an older removed shell, so use the live
`active_volume_users` field from `status` to find the attached VM. The wrapper
does not replace that historical receipt or adopt the active VM. The private
inspection receipt is `reports/workspace-integration/host-source-preflight.json`.

## Verified setup and current limits

Observed on **2026-08-27**:

| Item | Observed configuration or result |
| --- | --- |
| Host | macOS 27 on Apple silicon / ARM64 |
| Runtime | Apple Container `1.0.0`, commit `ee848e3ebfd7c73b04dd419683be54fb450b8779` |
| Guest image | `evolution-nezha-builder:ubuntu24.04-v1`; Ubuntu 24.04 ARM64 with amd64 runtime libraries |
| Completed image index digest | `sha256:82960bf5b04070ffa323bb37eaa4e77d1b189f7bdcd0c31204d5d8ac092d36ca` |
| Source/build VM allocation | 16 vCPUs, 128 GiB RAM; guest reported 125.7 GiB RAM |
| Persistent storage | Named ext4 volume `evolution-nezha-work`, 800 GiB capacity; 787.4 GiB free at the preparation check |
| Configured source / output / cache defaults | `/work/evolution` / `/work/out/evolution` / `/work/cache/ccache`; module experiments use the separate output recorded below |
| Rosetta execution | Direct x86-64 ELF probe passed; a freshly cross-compiled C program also executed successfully |
| Actual AOSP host tool | Android 16 Ninja `1.9.0.git`, with matching bundled libraries, built a small x86-64 C program that executed successfully |
| Filesystem | ext4 and case-sensitive file behavior verified |
| Repo initialization | Completed in `/work/evolution`, with manifest and Repo implementation pins verified and signature checks enabled |
| Full sync | Completed at `2026-08-27T16:56:02Z`, exit `0`; all 1,179 project HEADs, clean worktrees and remotes verified afterward |
| Soong bootstrap | Unmodified entry point compiled four x86-64 host tools and successfully queried `OUT_DIR`; no product or Android module build |
| Nezha Android modules | Real product graph built ARM64 `libbase.so` and x86-64 host `checkvintf`; output hashes and actual Ninja namespace observation recorded |
| Complete ROM / device support | No complete Android 16 ROM or functional Nezha build established |

Disk and memory figures are measurements from that check, not reserved free
resources or promises about future builds. The separate image-build VM uses
8 vCPUs and 16 GiB RAM. Configuration is in
[`config/apple-container.json`](../config/apple-container.json).

The official Ubuntu base is pinned by digest, and its registry manifests were
hashed. Normal Ubuntu APT signature checks remain enabled for both ARM64 and
amd64 repositories; the resulting package inventory is recorded inside the
image. A base-image digest is not a claim that the locally built image is
cryptographically signed or that moving APT repositories are a frozen package
snapshot. See the [image recipe and provenance](../containers/apple/README.md).

The Android source pins are unchanged:

- Evolution X `bka` / Android 16 QPR2 manifest:
  `cc4ebb8db9750afba6049825127304b09327f7c1`.
- Google Repo implementation:
  `b85886fa9f5b4e2189cc5b2f40bd0a80459d4c77`.

Both are recorded in [`config/sources.json`](../config/sources.json). The completed
checkout now has an [archival resolved manifest](../research/source-snapshots/evolution-bka-20260827.xml)
and [sanitized verification record](../research/source-sync.json). The snapshot
records all 1,179 project commits. The reviewed
[source-lock descriptor](../config/evolution-source-lock.json) makes those exact
XML bytes an explicit input to a new locked checkout; see the
[source-lock workflow](source-lock.md). It does not activate a device manifest
or convert the existing checkout's guarded `default.xml` selection.

## Completed source verification

The original task `evolution-nezha-sync-20260827155847261123` finished after
**57m 15.296s** and stopped naturally. No second sync was started and no source
checkout was reset or discarded. After confirming exclusive volume ownership,
a follow-up shell independently checked the completed ext4 checkout at
`2026-08-27T17:05Z`, before the later authored product and recorded vendor patch:

- All **1,179** project HEADs equal the resolved manifest's full commit IDs.
- All **1,179** worktrees were clean, including untracked-file checks; all project
  remote URLs match the manifest. `.repo/project.list` matches exactly.
- Manifest and Repo origins, commits, clean status, and the sole `default.xml`
  selector passed before and after the audit. No local device manifest exists.
- All **99 Git LFS payloads** in five projects were materialized. Hashing their
  **3,608,373,955 bytes** matched every recorded LFS object ID.
- A fresh host preflight passed with **610.0 GiB free** on the shared ext4 source/
  output volume and 125.7 GiB guest RAM. Those are dated observations.

The resolved manifest is 287,546 bytes with SHA256
`a7b9b5aec7f07a4d351771dbb834f4c4561c26564c7292930409f3f5968edeac`.
The original remains under
`/work/control/8ef07db7e8ccd6dbf9ad6be3c5af0981453b783b6b308acca72dabb4a2bed3cc/reports/resolved-manifest-20260827T165601Z.xml`.
The committed snapshot has identical bytes; all used project URLs were checked
as public HTTPS without credentials. Upstream's unused `private` remote
declaration has no projects in this checkout.

The full per-project receipt is
`/work/validation/source-audit-20260827T1705Z/receipt.json`, SHA256
`62f0113668c4c8d904134b6eb69b699ece1cba05babbf0c277edb17b9297e87c`.
Its separate `lfs-content-verification.json` has SHA256
`a633c3807f9ce7411be1d45d880ba9f9e4af067b25767760e9a6deb1c30711b2`.
Matching host copies are in ignored `reports/source-sync-20260827/`.
The sync completion log and task backup are also retained under `reports/`;
`.tools/apple-container/last-task.json` describes the latest operation, which
may be the later verification shell rather than this completed sync.

## Actual AOSP Ninja proof

The test under `/work/validation/aosp-ninja-20260827T160141Z` used AOSP's
`platform/prebuilts/build-tools` tag **`android-16.0.0_r4`**, including
`linux-x86/bin/ninja` and its matching `linux-x86/lib64/libjemalloc5.so` and
`libc++.so`. The receipt records the source URLs, Git blob IDs, file sizes,
SHA256 hashes and ELF machine `62` (x86-64) for all three inputs. Their hashes
were rechecked from the existing guest and match the receipt:

| Artifact | SHA256 |
| --- | --- |
| `linux-x86/bin/ninja` | `b3c53a693d6496f3214464fac05fe53ba155489cc071861d9414e2128913c1a2` |
| `linux-x86/lib64/libjemalloc5.so` | `5e156eed108c3ab4bd0122e7cdb6de06de633890366f0bf37093c0003bd2949c` |
| `linux-x86/lib64/libc++.so` | `debd1e923abe6fe535980b69be8d1b66ca3a214ab865b46f4e3ce5c929d158f0` |

Ninja reported `1.9.0.git`. Its build rule invoked `x86_64-linux-gnu-gcc` on a
standalone C program. Both the Ninja build and the resulting executable exited
with code `0`; the program printed `aosp-ninja-rosetta-build-ok`. The compiler
was the guest's cross-compiler, not an AOSP Clang build. This proves execution
of this real Android host prebuilt and its libraries under Rosetta, rather than
only a synthetic probe. It does **not** prove Soong/Clang/JDK compatibility, a
completed platform sync, an Android module/ROM build, or a working Nezha target.

The matching local log is `reports/apple-aosp-ninja-smoke.log`; the persistent
guest receipt is
`/work/validation/aosp-ninja-20260827T160141Z/receipt.json`. Both explicitly record
`full_android_build_tested=false`. These ignored/private build-host artifacts
are separate from offline workspace unit tests. No phone was used for this
proof.

## Downloaded Clang, JDK and Go proofs

After the completed source audit, **13 standalone checks passed** using the
actual downloaded host tools. Input files were hashed before and after use;
the selected executables were verified as x86-64 ELF. Their owning project
commits match the resolved manifest. The
[machine-readable evidence](../research/apple-host-tools.json) records all
tool/input/output hashes and exact project revisions.

| Downloaded tool | Verified operation under Rosetta |
| --- | --- |
| Android Clang `r563880c`, 21.0.0, and LLD 21.0.0 | Compiled and linked a tiny x86-64 C executable; the executable ran successfully |
| AOSP Ninja `1.9.0.git` | Ran that Clang/LLD build with its matching bundled libraries |
| The same Android Clang | Produced an ELF AArch64 object for `aarch64-linux-android36` |
| Android OpenJDK `21.0.4+-12414455` | `javac` compiled a Java class and `java` executed it successfully |
| Downloaded Go `1.24.1 linux/amd64` | Built a standalone Go program, which executed successfully; network module/toolchain downloads were disabled for this probe |

The C host link used the guest's GCC runtime files. The ARM64 result is a
freestanding object only, with no Bionic link or phone execution. These tests
do not establish an Android module, kernel or ROM build, nor compatibility with
every host prebuilt. No firmware executable was involved.

The guest receipt is
`/work/validation/synced-host-tools-20260827T1709Z/receipt.json`, SHA256
`bab0c41f1299f477b1cd8827b0762cb45a26226ed358bdccb4195d2fc40486d2`.
Its byte-identical host copy is `reports/source-sync-20260827/host-tools.json`;
the invocation log is `reports/synced-host-tools-smoke.log`. Build orchestration
and sandbox behavior remain separate checks.

## Soong bootstrap proof and sandbox limit

The original `build/soong/soong_ui.bash --dumpvar-mode OUT_DIR` entry point
passed on **2026-08-27**, using a previously absent output directory:
`/work/out/soong-bootstrap-20260827T1721Z`. It compiled `soong_ui`, `mk2rbc`,
`rbcrun` and `release-config`; all four outputs are ELF machine `62` (x86-64).
The newly compiled `soong_ui` executed and printed that exact output path with
a newline, exit `0`, and empty stderr. This does not establish independent
execution of the other three tools. Their sizes, hashes, input hashes and five
owning project revisions are in the
[Soong bootstrap record](../research/soong-bootstrap.json).

The command prepended the existing
`/work/evolution/prebuilts/build-tools/path/linux-x86` directory to its own
`PATH`. Its existing `uname` symlink points to `../../linux-x86/bin/toybox`;
this x86-64 tool reported `x86_64` under Rosetta while `/usr/bin/uname -m`
still reported the guest's native `aarch64`. No shim, source patch, replacement
of `/usr/bin/uname`, or global PATH change was made. This matters because the
[pinned microfactory script](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/scripts/microfactory.bash)
sets `GOROOT` from `uname -m`, overwriting an inherited value. The selected
checkout supplies `prebuilts/go/linux-x86`, not `prebuilts/go/linux-arm64`.

For a deliberate repeat, first use the wrapper's status and host/source checks
and obtain the sole volume-owning guest shell. Use a **new** output directory;
do not reuse the recorded proof directory. The command shape is:

```sh
# Inside the guarded guest shell, not on macOS or in another writer VM.
(
  set -eu
  cd /work/evolution
  soong_probe_validation="$(mktemp -d /work/validation/soong-repeat.XXXXXXXX)"
  soong_probe_out="/work/out/$(basename "$soong_probe_validation")"
  test ! -e "$soong_probe_out"
  test ! -L "$soong_probe_out"
  PATH="$PWD/prebuilts/build-tools/path/linux-x86:$PATH" \
    OUT_DIR="$soong_probe_out" GOCACHE="$soong_probe_validation/go-cache" \
    GOTOOLCHAIN=local GOENV=off GOPROXY=off GOSUMDB=off \
    GIT_OPTIONAL_LOCKS=0 GIT_TERMINAL_PROMPT=0 \
    build/soong/soong_ui.bash --dumpvar-mode OUT_DIR
)
```

The recorded probe additionally captured hashes and before/after source status;
a later repeat needs its own evidence. No build checks were disabled by this
probe. In the pinned source, [`OUT_DIR` is a fast path](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/ui/build/dumpvars.go)
that does not invoke Kati or product configuration. The
[normal entry path](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/cmd/soong_ui/main.go)
includes output setup and source discovery before that query. The probe did
not set a finder-skip flag, but no separate finder artifact receipt was
captured. It did not build an Android module, kernel or ROM, run Ninja build
actions, select a product, or register a Nezha target.

**The standalone Ninja sandbox now passes runtime checks.** The follow-up
[sandbox record](../research/apple-sandbox.json) uses the pinned AOSP `nsjail`,
Ninja and Clang with the supported read-only-source form of the upstream Ninja
sandbox arguments. It built and ran
an x86-64 program inside the jail and produced an Android ARM64 object. A
deliberate source write was rejected with `EROFS`, the jail exposed only the
loopback network interface, and its hostname/UID matched the requested
namespace settings. The guest receipt is
`/work/out/nsjail-ninja-20260827T1814Z/receipt.json`, SHA256
`d5b7fbe849aa6061934cbfbcbdf40708e301be85fc1ac38e44bfd0570062db37`.
This is a standalone test, not a Soong-generated Android module graph or ROM.

The subsequent Nezha `libbase checkvintf` build passed through 4,591 Ninja
actions. Its actual Ninja process ran under nsjail in separate mount, network,
PID and user namespaces, without a fallback. That initial product selected a
**read-write** source mount; the standalone probe above did not establish the
product's mount mode. The later authored board setting requires read-only
source for the Camera build. The [build record](../research/build-progress.json)
binds these distinct observations to their input versions, output hashes and
receipts. The product output is physically
`/work/out/nezha-framework-20260827T1835Z`, reached through its recorded relative
source-root alias.

At Soong commit
`cbcbea9e65503ca15b363a0b06dda88fdbcb0154`, upstream
[`sandbox_linux.go`](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/ui/build/sandbox_linux.go)
already has `basicSandbox.Enabled=false` for dumpvars, Kati and Soong. Ninja's
sandbox is enabled in that source, but an unsuccessful nsjail probe logs
`Build sandboxing disabled due to nsjail error.` and can fall back to execution
without that sandbox. Those upstream settings were not changed. The probe
retains the upstream cgroup-namespace exception; root in the guest maps to
`nobody` inside the user namespace, which nsjail reports explicitly. A fallback
in an actual build must still count as **failed
sandbox validation**, even if the build exits successfully; do not weaken
checks or add broad capabilities to conceal it.

The bootstrap's private guest receipt is
`/work/validation/soong-bootstrap-20260827T1721Z/receipt.json`, SHA256
`5baaded71c7f0794520af150fb339ab24a429a5eb8bdde568667fe56badf4c8d`.
Its verified host copy is `reports/source-sync-20260827/soong-bootstrap.json`;
the invocation log is `reports/soong-bootstrap.log`. A subsequent complete
source audit again found all **1,179** HEADs, clean worktrees and origins
matching the resolved manifest, with the manifest/Repo guards intact. Its
guest receipt is `/work/validation/source-audit-20260827T1730Z/receipt.json`,
SHA256 `0005ba649db46dfd58420a3725886b3d6e49bcef36dfdc4ecf0ab6c9a07584fb`;
the verified copy is `reports/source-sync-20260827/post-bootstrap-source-audit.json`.
No phone was accessed.

## Commands from the Mac repository root

Use the project wrapper, not a second manually mounted VM. All operations accept
`--dry-run`, which prints a plan without starting services/VMs or changing
images, volumes, or source files. `--jobs` defaults to 8; `--detach` is valid
only for `sync`. `--source-lock` is valid only for `init` and `sync` and accepts
the reviewed `config/evolution-source-lock.json` descriptor, either relative to
this repository or as its absolute path inside the repository.

The current `/work/evolution` checkout and active VM are already populated.
Preserve them. The initialization/download sequence below is for a deliberately
configured **new empty source directory** when no VM owns the volume, not a
request to repeat setup or sync the existing checkout.

```sh
# Inspect actual volume users and the historical task receipt first.
python3 scripts/apple_container.py status

# Preview a new environment without changing anything.
python3 scripts/apple_container.py setup --dry-run

# For a new configured source directory, with no VM owning the volume:
python3 scripts/apple_container.py setup
python3 scripts/apple_container.py doctor
python3 scripts/apple_container.py smoke
python3 scripts/apple_container.py init --source-lock config/evolution-source-lock.json

# Download in the background, retaining the named task for status and logs.
python3 scripts/apple_container.py sync --source-lock config/evolution-source-lock.json --jobs 8 --detach
python3 scripts/apple_container.py status

# Open only when no other VM is using the volume; requires an interactive terminal.
python3 scripts/apple_container.py shell
```

Do not rerun this sequence while the existing VM owns the volume; use
`status`. These commands are also exposed as `make apple-setup`,
`make apple-doctor`, `make apple-smoke`, `make apple-init`, `make apple-sync`,
`make apple-sync-bg`, `make apple-status`, and `make apple-shell`.
The Make init/sync targets select the reviewed source lock by default.
`make apple-sync-bg JOBS=8` is the detached form; use the Python form when
choosing `--dry-run` explicitly. Direct Python commands without `--source-lock`
retain the original pinned-manifest workflow for an existing checkout; they
do not gain fixed per-project revisions merely because the XML is archived.

| Operation | What it does |
| --- | --- |
| `setup` | Starts the Container service, creates or validates the project volume, builds the image, then runs the guest smoke test. It does not sync Android or select a product. |
| `build-image` | Rebuilds the image only. Use deliberately after changing its recipe; this can produce a new image digest. |
| `doctor` | Checks the selected guest host mode, required resources/filesystem and Rosetta runtime contract. |
| `smoke` | Runs the doctor, builds and executes a small x86-64 C program, checks case behavior and ext4, and creates/rechecks a persistence marker. |
| `init` | Initializes Repo with the pinned manifest and verified Repo tool, optionally selecting the reviewed project lock for a new checkout. |
| `sync` | Runs the guarded full platform download with the selected manifest or exact source lock; foreground by default, or detached with `--detach`. It does not compile a ROM. |
| `status` | Reports actual active volume users separately from the last recorded task, retains known task outcomes and logs, and inventories only an already running recorded task attached to this volume. |
| `shell` | Opens a persistent source shell. It does not source `envsetup.sh`, select a lunch target, or build automatically. |

The source guard keeps `native` as the default. The wrapper explicitly passes
`--host-mode apple-rosetta` **inside** the ARM64 Linux builder. This mode requires
the expected image marker, actual x86-64 ELF/loader checks and successful probe
execution in addition to disk, RAM and filesystem checks. Selecting the flag
on the macOS host does not make those checks pass.

With `--source-lock`, the immutable control bundle contains exactly two additional
inputs: the reviewed descriptor and its existing resolved-manifest XML. Both
paths and file hashes participate in the bundle identity. The guest verifies
the descriptor's manifest/Repo pins and XML hash before forwarding the descriptor
under `/work/control/<control-id>/config/evolution-source-lock.json` to the
workspace command. It never forwards a host path or mounts the host source tree.
Legacy four-file bundles remain readable. A partial pair, changed snapshot,
symlinked input or unrecorded extra lock cannot silently select another source
revision. A previously populated checkout is not reset or converted to fit a lock.

## Read sync status correctly

The historical local task receipt is `.tools/apple-container/last-task.json`.
It records the last operation launched by this wrapper, not every VM that may
later attach the source volume. `status` independently enumerates the actual
active volume users, even when that receipt is absent or refers to a removed
container. It does not write a replacement receipt, infer an external VM's
source-operation success, or start another VM to inspect it. For detached
work, `launch_exit_code=0` means the container was launched, not that Repo sync
succeeded. A running container or a growing project count is progress only.

Use `python3 scripts/apple_container.py status` to inspect both views.
The completed task `evolution-nezha-sync-20260827155847261123` used an older
immutable control bundle. Its inventory could show zero listed/checked-out
projects before Repo creates `.repo/project.list` during the initial fetch.
That does not mean no data has downloaded. The current host code distinguishes
an absent list from zero projects, but it does not replace a running VM's
control bundle. Do not restart a healthy sync to update that display.

At the **`2026-08-27T16:16:23Z` checkpoint**, the same VM was running with `27G`
under `/work/evolution/.repo`, 383 Git directories under `.repo/projects`,
377 under `.repo/project-objects`, and `745G` free on `/work`. These are dated
fetch-progress observations, not counts of successfully downloaded or checked
out projects, and not a percentage of the final source tree.

The completed task's logs remain available. For future running tasks, use their
actual state when the summary is ambiguous:

```sh
container logs -n 80 evolution-nezha-sync-20260827155847261123
# Replace RUNNING_TASK with the actual running entry in active_volume_users.
container exec RUNNING_TASK du -sh /work/evolution/.repo
container exec RUNNING_TASK df -h /work
```

For a later inspection, use the live volume-user entry instead of assuming
`last-task.json` or a dated example names the current VM. A VM created outside
the wrapper may have no `/control` mount, so status does not attempt wrapper
inventory inside it. `container exec` inspects the already running VM; do not
attach the volume to a second VM for status checks.
Growing Git storage indicates activity, not that every fetch succeeded.

The guest wrapper emits `EVOLUTION_TASK_RESULT` with `operation`, `status`, and
`exit_code` when the source operation ends. Confirm a final successful sync
result, preserved manifest/Repo pins, and the resolved manifest before declaring
the checkout complete. A stopped task alone is not evidence of success.

After successful synchronization, the resolved manifest is written on the
volume under `/work/control/<control-id>/reports/resolved-manifest-*.xml`.
The receipt identifies the control ID. Preserve the task logs, image digest,
package inventory and this manifest with subsequent build evidence; they are
not automatically committed to the small host repository.

If a task fails, retain its logs and volume and diagnose the actual error. The
wrapper preserves local source changes and does not use force-sync, update the
pinned manifest, or silently replace the Repo implementation. Start a later
operation only after the current VM is no longer using the volume; do not
disable the volume ownership check to run concurrent writers.

## Storage and trust boundaries

`evolution-nezha-work` is an **Apple-managed named volume outside this Git
checkout**. `/work/evolution` is therefore not the Mac's `sources/evolution`
directory. Source, output and cache survive foreground container removal.
Keep the active volume; do not prune or delete it as routine cleanup. Its
current capacity is 1,024 GiB; the 800 GiB setup observations above are historical.
Filesystem capacity is not necessarily current physical disk usage.
Apple documents sparse ext4 named volumes and warns that pruning can destroy
their data. [Apple volume documentation](https://github.com/apple/container/blob/main/docs/volumes.md)

The only host share is a narrow, read-only control bundle of approved configs,
scripts and the verified Repo checkout. It is copied into a hash-identified
snapshot on ext4 and checked before use. The host home directory, source tree,
device evidence, firmware, SSH agent and credentials are not mounted. No second
VM may write the project volume concurrently. These boundaries do not provide
offline isolation: source synchronization still needs network access.

A normal writable virtiofs bind mount shares host files; it must not be assumed
to provide an automatic temporary copy. This workspace instead uses an explicit
read-only control share and named ext4 source storage. Apple documents `bind`
(`virtiofs`) separately from named volumes and an explicit `readonly` option.
[Apple mount options](https://github.com/apple/container/blob/main/docs/volumes.md#mount-options)

The runtime does not request `--cap-add ALL`, patch Android source at startup,
remove product definitions, or downgrade artifact-path checks. A failing build
must be investigated rather than hidden by weakening these checks. Nothing in
this environment authorizes unlocking, rebooting, or flashing a phone.

## What the external references establish

Apple's [multiplatform guide for the installed CLI revision](https://github.com/apple/container/blob/ee848e3ebfd7c73b04dd419683be54fb450b8779/docs/how-to.md#build-and-run-a-multiplatform-image)
documents Rosetta execution. The requested
[firsthand AOSP article](https://personaldevblog.web.app/en/blog/running-aosp-builds-on-mac-with-apple-container-en)
(2026-06-13) reports Android **14 module builds**, not a complete Android 16
Evolution X ROM. Its [linked implementation](https://github.com/wangchauyan/aosp-container/tree/8466fe2ff573160e8f199a5a1b2bafbe64703313)
is useful reference material, not a recipe adopted unchanged. This workspace
does not adopt its verification bypasses, startup source edits, broad runtime
capabilities, or copy-on-write assumption.

The authored Nezha product now passes actual Soong/Kati configuration. The
[current build record](build-progress.md) tracks Android module compilation and
its failures and fixes; a complete ROM and the full kernel/vendor/framework
integration remain unverified. All nine selected Camera dependency modules
have now built, with four JARs preoptimized and the JNI ELF check observed.
The actual Camera Ninja sandbox has read-only source and read-write output.
Earlier command-line Xiaomi CDN downloads remain partial. The separately
supplied factory-named TGZ under `sources/` now has [verified intake and image
results](factory-firmware-validation.md), including the selected AVB chain.
It has not silently replaced the explicitly bound Xiaomi.eu build inputs.
The separately supplied [Xiaomi.eu package](provided-firmware.md) has passed local
SHA256 and full ZIP CRC checks, but its origin is unverified and it is not
authenticated factory firmware. Its extraction requirements and embedded
identity must be kept separate from the official baseline. No stock-feature
parity, complete ROM, build duration, or Rosetta compatibility with every
prebuilt is promised.

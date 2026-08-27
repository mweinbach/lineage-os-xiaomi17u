# Apple Container and Rosetta build environment

**The Mac can run this project's experimental Linux build environment.** The
previous native-Linux-only conclusion was too broad. ARM64 Ubuntu tools run in
Apple Container, while Rosetta handles x86-64 Linux executables. Source and
output live on a persistent Linux ext4 volume. This preserves the distinction
between a usable local environment and a verified complete Android 16 ROM build.

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
| Source / output / cache | `/work/evolution` / `/work/out/evolution` / `/work/cache/ccache` |
| Rosetta execution | Direct x86-64 ELF probe passed; a freshly cross-compiled C program also executed successfully |
| Actual AOSP host tool | Android 16 Ninja `1.9.0.git`, with matching bundled libraries, built a small x86-64 C program that executed successfully |
| Filesystem | ext4 and case-sensitive file behavior verified |
| Repo initialization | Completed in `/work/evolution`, with manifest and Repo implementation pins verified and signature checks enabled |
| Full sync | Completed at `2026-08-27T16:56:02Z`, exit `0`; all 1,179 project HEADs, clean worktrees and remotes verified afterward |
| Android build / device support | No full Android 16 compilation or functional Nezha ROM established |

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
records all project commits; it does not activate a device manifest or change
the guarded `default.xml` selection.

## Completed source verification

The original task `evolution-nezha-sync-20260827155847261123` finished after
**57m 15.296s** and stopped naturally. No second sync was started and no source
checkout was reset or discarded. After confirming exclusive volume ownership,
a follow-up shell independently checked the completed ext4 checkout:

- All **1,179** project HEADs equal the resolved manifest's full commit IDs.
- All **1,179** worktrees are clean, including untracked-file checks; all project
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

## Commands from the Mac repository root

Use the project wrapper, not a second manually mounted VM. All operations accept
`--dry-run`, which prints a plan without starting services/VMs or changing
images, volumes, or source files. `--jobs` defaults to 8; `--detach` is valid
only for `sync`.

```sh
# Inspect the existing task first; a detached sync may already be active.
python3 scripts/apple_container.py status

# Preview a new environment without changing anything.
python3 scripts/apple_container.py setup --dry-run

# For initial setup, or deliberate revalidation when no task owns the volume:
python3 scripts/apple_container.py setup
python3 scripts/apple_container.py doctor
python3 scripts/apple_container.py smoke
python3 scripts/apple_container.py init

# Download in the background, retaining the named task for status and logs.
python3 scripts/apple_container.py sync --jobs 8 --detach
python3 scripts/apple_container.py status

# Open only when no other VM is using the volume; requires an interactive terminal.
python3 scripts/apple_container.py shell
```

Do not rerun this entire sequence while the existing sync is active; use
`status`. These commands are also exposed as `make apple-setup`,
`make apple-doctor`, `make apple-smoke`, `make apple-init`, `make apple-sync`,
`make apple-sync-bg`, `make apple-status`, and `make apple-shell`.
`make apple-sync-bg JOBS=8` is the detached form; use the Python form when
choosing `--dry-run` explicitly.

| Operation | What it does |
| --- | --- |
| `setup` | Starts the Container service, creates or validates the project volume, builds the image, then runs the guest smoke test. It does not sync Android or select a product. |
| `build-image` | Rebuilds the image only. Use deliberately after changing its recipe; this can produce a new image digest. |
| `doctor` | Checks the selected guest host mode, required resources/filesystem and Rosetta runtime contract. |
| `smoke` | Runs the doctor, builds and executes a small x86-64 C program, checks case behavior and ext4, and creates/rechecks a persistence marker. |
| `init` | Initializes Repo with the pinned manifest and verified Repo tool. |
| `sync` | Runs the guarded full platform download; foreground by default, or detached with `--detach`. It does not compile a ROM. |
| `status` | Reports service/volume and latest task state, shows recent logs, and inventories source progress in an already running task. |
| `shell` | Opens a persistent source shell. It does not source `envsetup.sh`, select a lunch target, or build automatically. |

The source guard keeps `native` as the default. The wrapper explicitly passes
`--host-mode apple-rosetta` **inside** the ARM64 Linux builder. This mode requires
the expected image marker, actual x86-64 ELF/loader checks and successful probe
execution in addition to disk, RAM and filesystem checks. Selecting the flag
on the macOS host does not make those checks pass.

## Read sync status correctly

The local task receipt is `.tools/apple-container/last-task.json`. For detached
work, `launch_exit_code=0` means the container was launched, not that Repo sync
succeeded. A running container or a growing project count is progress only.

Use `python3 scripts/apple_container.py status` to inspect the current task.
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
# Replace RUNNING_TASK with the current, running VM from last-task.json.
container exec RUNNING_TASK du -sh /work/evolution/.repo
container exec RUNNING_TASK df -h /work
```

For a later task, take its name from `.tools/apple-container/last-task.json`
instead of reusing this checkpoint's name. `container exec` inspects the
already running VM; do not attach the volume to a second VM for status checks.
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
Keep the volume; do not prune or delete it as routine cleanup. Its 800 GiB is
the filesystem capacity, not necessarily its current physical disk usage.
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

The remaining work is still concrete: validate Android build orchestration
under Rosetta and complete the Nezha device/common/
kernel/vendor integration. Official Xiaomi CDN downloads remain partial. The
separately supplied [Xiaomi.eu package](provided-firmware.md) has passed local
SHA256 and full ZIP CRC checks, but its origin is unverified and it is not
authenticated factory firmware. Its extraction requirements and embedded
identity must be kept separate from the official baseline. No stock-feature
parity, complete ROM, build duration, or Rosetta compatibility with every
prebuilt is promised.

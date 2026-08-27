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
| Filesystem | ext4 and case-sensitive file behavior verified |
| Repo initialization | Completed in `/work/evolution`, with manifest and Repo implementation pins verified and signature checks enabled |
| Full sync | Detached sync launched at `2026-08-27T15:58:47Z`; completion not yet verified in this record |
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

Both are recorded in [`config/sources.json`](../config/sources.json). Individual
Android projects still follow manifest refs until a successful sync produces a
resolved manifest. Repo initialization is not a completed source checkout.

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
`make apple-status`, and `make apple-shell`. Use the Python form when choosing
`--detach` or `--dry-run` explicitly.

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

The remaining work is still concrete: finish and verify the Android 16 sync,
test the actual Android build tools, complete the Nezha device/common/kernel/
vendor integration, and obtain the fully verified matching firmware package.
The firmware CDN download remains partial. No stock-feature parity, complete
ROM, build duration, or Rosetta compatibility with every prebuilt is promised.

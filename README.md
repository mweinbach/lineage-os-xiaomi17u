# Evolution X for Xiaomi 17 Ultra

An unofficial bring-up workspace for Xiaomi 17 Ultra (`nezha`, SM8850 / `canoe`),
using Evolution X Android 16 QPR2 (`bka`) and the recorded stock/Xiaomi.eu inputs.
Xiaomi camera and other native features remain part of the bring-up plan.

**TWRP is working on the phone and is our selected default recovery. Evolution X
is still a bring-up target, not a completed or flashable ROM.** Start with
[current status](docs/workspace-status.md) for the evidence and remaining gates.

| Area | What is established |
| --- | --- |
| Recovery | `working76` boots with visible UI, responsive touch, root USB ADB and log access using the installed stock companion boot/kernel/vendor stack. |
| Recovery defaults | Permissive SELinux and zero action/button/keyboard vibration apply at recovery startup. The working runtime, drivers and firmware are preserved. |
| Platform | A recorded 1,179-project Evolution X checkout and authored Nezha product passed configuration and selected framework, Camera dependency, boot and DLKM builds. |
| ROM readiness | Full target-files, OTA and super packaging remain blocked. Policy integration, `mi_ext`, VINTF, complete signing and device compatibility still need work. |
| Security scope | Normal Android must retain enforcement and its verification checks. Permissive recovery is an explicitly authorized development choice, not a release-security claim. |

The recovery is adapted from the supplied `fix22ZJ-touchfix18` image; we do not
claim to have rebuilt its TWRP executable from source. Display/touch success in
that recovery does not establish compatibility with the newly built Evolution
boot chain, data decryption, OTA installation or Xiaomi feature parity.

## Start here

These commands do not start a source sync, build Android or change the phone:

```sh
make help
make test
make recovery-plan
make recovery-logs-plan
make apple-status
```

`make twrp-plan` now selects the working recovery workflow. The earlier full
TWRP source experiment is preserved under `make twrp-source-plan` and in the
[bring-up history](docs/twrp-bringup-history.md); it is not the selected baseline.

## Build and verify the working recovery

On the configured workstation, `.tools/recovery-local.json` stores paths to the
preserved baseline image, pinned tools and existing local development key.
It contains no key material and stays ignored. A fresh clone needs those
private inputs; see the [build instructions](recovery/twrp-working/README.md).

```sh
make recovery-build
make recovery-verify RECOVERY_IMAGE=/absolute/path/to/the/new/recovery.img
```

Each default build uses a new timestamped directory under
`artifacts/twrp/nezha/builds/`. Set `RECOVERY_OUTPUT` to choose another new output
directory. Existing outputs are never replaced. The build checks the fixed
source/patch/tool identities, unchanged archive members, compression round trip,
header, development-key AVB signature and exact expected image hash. Signing
keys stay in their existing private location; never copy them into the build VM.

The [August 29 validation](research/workspace-integration.json) reproduced the
image twice and passed two actual Evolution `recoveryimage` target runs with
the same bytes and a verified AVB signature. The repeat Android target took
about 25 seconds using its existing build graph; this is not a full ROM build.

The [ROM recovery workflow](docs/twrp-bringup.md) describes the reviewed build-core
patch and the private `vendor/xiaomi/nezha-recovery` input bundle. On the Linux
build host, with its public verification tools configured:

```sh
make recovery-stage SOURCE_DIR=/work/evolution RECOVERY_IMAGE=/work/inputs/recovery.img
make recovery-inputs-verify SOURCE_DIR=/work/evolution
```

Staging requires the reviewed build-core patch and an exact verified image.
The device configuration must reject missing or mismatched inputs instead of
silently substituting another recovery. The private bundle includes the
matching public key for the recovery chain; the signing key stays on the Mac.
Staging and building do not flash a phone or admit a complete ROM. Full-ROM
packaging gates remain in place.

## Resume or reproduce the platform sources

The existing Apple Container ext4 volume already contains the platform source,
outputs and cache. Inspect its actual active VM with `make apple-status`;
do not repeat setup or attach another writer to resume work. The last wrapper
task and the current volume owner are separate pieces of state.

New source setup uses `config/evolution-source-lock.json`, which binds the
reviewed 1,179-project snapshot to the pinned manifest and Repo versions. The
manifest commit alone does not freeze branch-based project revisions.

```sh
make source-plan
make apple-plan
make source-check SOURCE_DIR=/work/evolution
```

Run the source check where that source path exists. It reads project revisions,
origins and worktree state without resetting or patching anything. Expected
local patches remain visible as differences; a matching base revision does not
mean a pristine checkout or a complete build input set. Existing selectors are
not silently converted. See [source-lock handling](docs/source-lock.md) and the
[Apple Container guide](docs/apple-container.md) before a fresh initialization.

Native Linux x86-64 and the verified Apple Container ARM64/Rosetta path require
adequate disk/RAM and a case-sensitive Linux source filesystem. Host, manifest,
signature, artifact and compatibility checks remain enabled. Generated device,
vendor and kernel inputs and reviewed local patches are required in addition
to the source lock; no single sync command creates a ready-to-flash Nezha ROM.

## Workspace layout and handling

| Location | Role |
| --- | --- |
| `config/`, `device/`, `kernel/` | Selected contracts and authored device/build integration |
| `recovery/twrp-working/` | The small patch applied to the verified working recovery |
| `scripts/`, `tests/` | Build/inspection tooling and offline standard-library tests |
| `docs/workspace-status.md` | Current results and next build/boot gates |
| `research/`, `patches/` | Sanitized evidence records and reviewed source changes |
| `artifacts/`, `evidence/`, `reports/`, `.tools/`, `sources/`, `upstream/` | Ignored local inputs, outputs, logs, tool copies and reference checkouts |

The original recovery, stock inputs and historical experiments remain preserved.
Raw dumps, proprietary APKs/blobs, serials, logs and keys must not enter Git.
Collection requires an explicit authorized device and is read-only. Reboots,
flashes, wipes, unlocking/relocking and slot changes require a separate explicit
request; there is no automatic flash target in this workflow.

Use the [documentation index](docs/README.md) for firmware, partitions, kernel,
VINTF, policy, Camera/native features and historical build reports. Make small
commits as work passes validation and run `make test` before completing changes.

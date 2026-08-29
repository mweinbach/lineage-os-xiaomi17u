# Evolution X for Xiaomi 17 Ultra

This repository is the bring-up workspace, not a flashable ROM or a completed
device tree. Keep verified facts separate from assumptions and unresolved work.

## Working rules

- Make small, descriptive commits as useful work is completed. Run tests before
  completing a change. Use `python3 -m unittest discover -s tests -v`.
- Check upstream branches and record commit IDs before depending on them.
- Do not copy a different phone's partition layout, kernel, firmware, or device
  identity into a Xiaomi 17 Ultra build. Verify the exact variant from stock.
- Never unlock, relock, wipe, reboot, flash, or change the connected phone unless
  the user explicitly asks. Collection tools must be read-only and choose an
  explicitly identified, authorized device.
- Do not request account credentials or suggest bypassing Xiaomi's bootloader
  authorization. An officially unlockable bootloader is a bring-up prerequisite.
- Keep raw stock dumps, proprietary APKs/blobs, serials, logs, personal data,
  signing keys, and source checkouts in ignored directories. Record provenance
  and hashes; do not redistribute proprietary files without permission.
- Recovery bring-up may use permissive SELinux, as explicitly authorized by
  the user, while boot, touch, USB and logging are established. Preserve denial
  logging and restore enforcement as a later milestone; do not disable SELinux
  in the kernel or change normal Android's SELinux mode. Keep verified-boot and
  rollback constraints. Magisk is a possible later task, not part of this
  authorization. Do not claim a stock feature works without a device test.
- `upstream/` contains reference checkouts. Full source checkouts belong on a
  case-sensitive Linux filesystem: native Linux x86-64, or the explicitly
  verified Apple Container ARM64 + Rosetta path. The latter uses a persistent
  ext4 named volume and remains an experimental Android build environment.
- Apple Container bind mounts are not assumed to be copy-on-write. Share only
  the generated control bundle read-only; keep source, output and cache in the
  named volume. Do not mount home directories, phone evidence, or credentials.
- Never attach the same ext4 source volume to concurrent writer VMs. Do not
  prune volumes or delete existing source checkouts. Keep signature, artifact
  path and device-compatibility checks enabled in container builds. Record
  whether the recovery policy is enforcing or intentionally permissive.
- Do not start a full source sync or build without checking disk, OS,
  architecture, filesystem case sensitivity, and the selected manifest.
- Favor available Codex tools and relevant skills. Coordinate file ownership
  when delegating work; never overwrite another agent's uncommitted changes.

## Validation

Tests must run offline with Python's standard library and must not need a phone.
Mock device commands and network/process calls. Keep hardware validation and a
full Android build separate from tests of this workspace's tooling.

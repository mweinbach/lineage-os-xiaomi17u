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
- Retain SELinux enforcement and verified-boot/rollback constraints in the
  design. Do not claim a stock feature works without a reproducible device test.
- `upstream/` contains reference checkouts. `sources/` is reserved for the large
  Android repo checkout on a supported Linux x86-64, case-sensitive filesystem.
- Do not start a full source sync or build without checking disk, OS,
  architecture, filesystem case sensitivity, and the selected manifest.
- Favor available Codex tools and relevant skills. Coordinate file ownership
  when delegating work; never overwrite another agent's uncommitted changes.

## Validation

Tests must run offline with Python's standard library and must not need a phone.
Mock device commands and network/process calls. Keep hardware validation and a
full Android build separate from tests of this workspace's tooling.

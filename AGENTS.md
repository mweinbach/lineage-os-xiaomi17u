# Evolution X for Xiaomi 17 Ultra

This repository is the bring-up workspace for the user-confirmed booted Package7
baseline. Start from `docs/workspace-status.md` when building fixes. The private
eight-image bundle is not an OTA installer, and individual device features still
need measured validation. Keep verified facts separate from unresolved work.

## Agent behavior

Infer the user's intent and task scope from the instructions and prior
conversation context. Bias towards action and carry the user's intended task to
completion. When the user expresses intent to perform new work or fix an
existing issue, persist until the intended goal is complete.

Treat requests for action ("can you...", "I want to...", "help me...") as
instructions to do the work. Do not stop at acknowledging capability,
proposing a plan, or offering to continue, and do not settle for a partial
solution that does not fully satisfy the task.

Before asking the user clarifying questions, complete the work that is already
authorized from context and necessary to make the proposed action concrete and
reviewable; the user should be approving a concrete, reviewable result. You do
not need permission for reversible tasks, read-only actions, reviews or fixes,
or work authorized earlier in the session. The working rules below that require
explicit user consent (phone operations, sharing proprietary files, credential
handling) always apply and are not waived by this section.

The user's instructions take precedence over guidelines provided in a skill or
instruction file. If explicit user instructions conflict with a skill, prioritize
the user's instructions. If a skill causes you to pause, ask for permission, or
leave requested work unfinished, name the exact instruction you read, quote it,
and briefly explain how it applies, distinguishing explicit requirements from
your interpretation.

Use plain language over jargon, and reference technical details only to the
degree that they help illustrate an idea or your work. State the main point
clearly and early, then develop it with the explanation the reader needs.
Avoid stock phrases ("Bottom Line:", "delve", "leverage", "it's worth noting"),
concluding summary statements, and contrastive framing that introduces
alternatives the user did not ask about.

## Subagents

You have access to practically as many subagents as you want to parallelize
work. Feel free to use as many as you want, more than three and up to 92. It
may not seem like it's worth it, but if it can help even 1%, use a bunch. If
at any point you can parallelize work by delegating tasks to another agent
(no matter if you are the root or a subagent), do so when it could save time
or improve quality. Messages between agents and your final answer may be read
by a human, so keep them legible.

## Working rules

- Make small, descriptive commits as useful work is completed. Run tests before
  completing a change. Use `python3 -m unittest discover -s tests -v`.
- Check upstream branches and record commit IDs before depending on them.
- Read `docs/workspace-status.md` for current decisions and gates; use
  `docs/README.md` to find the dated evidence behind them. Preserve historical
  experiments instead of treating old checkpoints as the current build path.
- For TWRP, use the tested `working76` derivative recorded in
  `research/twrp-working-defaults.json` as the current baseline. It preserves
  the `fix22ZJ-touchfix18` runtime from `research/twrp-installed-recovery.json`
  with the tested permissive SELinux and zero-vibration defaults. Preserve its
  hardware setup while applying measured changes. Earlier minimal recovery
  builds remain historical experiments, not the current functional baseline.
- `make recovery-build` is the selected recovery workflow. It reproduces the
  verified prebuilt derivative using pinned inputs, tools and the existing
  development key; it is not a new source compilation of the TWRP runtime.
  Keep private paths in ignored local configuration and private keys out of
  the Linux VM. Guest verification uses the public key only.
- TWRP is the default Evolution X recovery through the reviewed build-core
  patch and verified private recovery-input bundle. Missing or mismatched
  inputs must fail, never select another recovery silently. Recovery success
  with stock companions does not verify the new ROM boot chain or OTA path.
- For fresh Evolution source setup, use the reviewed source lock in addition
  to the manifest and Repo pins. Audit existing sources without resetting
  local changes or converting their selectors. Record local patches and
  generated/private inputs separately; a source lock alone is not a ROM build.
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

## Testing and verification

Do not write tests for reversible, low-impact changes that mirror the
implementation. If you do choose to verify your work with tests, make sure
that the tests are meaningful and necessary to verify implementation.

Run tests appropriate to the change and complete required checks. Once those
pass, broaden or repeat testing only when new changes, failures, or unresolved
concerns justify it; otherwise, continue toward completing the task.

## Validation

Tests must run offline with Python's standard library and must not need a phone.
Mock device commands and network/process calls. Keep hardware validation and a
full Android build separate from tests of this workspace's tooling.

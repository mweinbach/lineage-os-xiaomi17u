# Reviewed patches in supplementary TWRP sources

The native Nezha recovery profile sometimes needs a source change in a project
that is not part of the original Repo manifest. A mixed Blueprint file can
provide a required production library and an unrelated test in the same file;
excluding the file would also remove the library. This contract lets a reviewed
patch target an explicitly pinned supplementary project. It does not authorize
a particular test exclusion or make a recovery image safe to boot or flash.

The frozen Repo XML, its original project count, and every existing project pin
remain unchanged. Supplementary owners stay in `config/twrp-dependencies.json`.
The build runner combines those identities with the frozen Repo identities only
for patch-owner lookup. Overlapping owners and paths under the controlled Nezha
target are rejected. Existing source entries cannot be replaced during revision.

Patches retain the existing `patches/twrp/series.json` format. A supplementary
entry must name its exact project path, pinned commit and repository URL, plus
the before and after Git blob IDs, SHA-256 hashes and byte lengths for every
changed file. The payload hash and declared file closure must match. Only text
edits to existing regular files at the same path are supported. Adding, deleting,
renaming or changing file mode is rejected. The old patch entries must remain
an exact unchanged queue prefix. An already patched file requires an explicit
immediate predecessor and exact postimage continuity under the
[linear patch-chain contract](twrp-linear-patch-chains.md); implicit overlap is
rejected. Every chain is rehearsed forward and backward in isolated copies
before applying its live suffix.

`scripts/twrp_patch_state.py` holds the shared read-only checks. It never fetches,
applies a patch, writes a receipt, acquires a writer lock or resets a checkout.
The original base-only receipts and queues remain valid without a migration.
The two runners retain their common `build-operation.lock`; a replaced or stale
lock is not automatically removed. A new control bundle must include the shared
helper alongside both runners and their existing workspace helpers.

| Operation | Required supplementary state |
| --- | --- |
| Fetch without previous controls | Every existing checkout and every new clone must be pristine. The proposed queue never permits local changes. |
| Fetch with `--previous-control-root` | The previous bundle must exactly match the active preparation receipt, staged target, output alias, frozen base and prior patch state. Only those prior patches may be present; newly proposed patches remain unapplied. |
| Initial prepare | Every owner starts pristine and each supplementary patch preimage matches its pinned Git blob. Complete source, supplementary, target and output checks run again after application and before the preparation receipt is published. |
| Revise | The old receipt and bundle authorize the old postimages. First touches require untouched pinned preimages; linked successors require the exact immediate predecessor. Patches and source evidence are archived before application. The whole new state must pass before the receipt advances. |
| Build check, graph and build | The active bundle must match the receipt, and all source owners must match their recorded phase. Successful build commands receive the same source checks afterward. |

Standalone supplementary `verify` remains pristine by default. Supplying
`--previous-control-root` makes it validate an exact active prepared state; it
does not adopt changes or publish a new receipt. The build runner also uses an
internal explicit phase when checking a transition. It never chooses a phase
by seeing whether file contents happen to match a proposed patch.

For a patched supplementary project, verification requires its original HEAD,
origin, standalone Git metadata, ordinary tracked-file flags, unchanged index,
and exactly the declared unstaged modifications. NUL-delimited Git status is
read without trimming its leading index/worktree columns. Staged changes,
conflicts, renames, extra tracked changes, untracked or ignored files, hidden
index flags, symlinks, unexpected modes, or wrong bytes all fail verification.
Patched file permissions must remain the pinned canonical `0644` or `0755`.
Verified patched checkouts are reported as `clean: false`, with their approved
patch IDs and phase; they are never relabeled pristine.

Fetch never applies patches, recreates a missing prepared checkout, or advances
`build-state.json`. Its previous-bundle authorization is rechecked after source
publication, before the fetch report is written. A failed preparation or
revision preserves the prior receipt, journal, archives, output and partial
source changes for inspection. It does not roll back or retry by accepting a
mixture of old and new postimages.

The offline standard-library tests in `tests/test_twrp_supplement_patches.py`
exercise synthetic owners and mock every Git/process operation. They cover
raw status, pins, origins, permissions, blob identities, phase separation,
receipt-bound fetch, pristine new checkouts, append-only revision and failed
postvalidation. Existing build and dependency tests continue to cover the
base-only workflow. These tests do not prove Android compilation, SELinux or
signature validation results, or recovery behavior on a phone.

# Evolution X upstream source lock

[`config/evolution-source-lock.json`](../config/evolution-source-lock.json)
selects the reviewed 1,179-project
[`evolution-bka-20260827.xml`](../research/source-snapshots/evolution-bka-20260827.xml).
It binds that file's exact SHA256, byte size and project count to both the
Evolution manifest origin/commit and Google Repo origin/commit in
[`config/sources.json`](../config/sources.json). The original
[`source-sync.json`](../research/source-sync.json) remains a historical receipt;
it is not rewritten to claim a new sync or a current checkout audit.

This locks the upstream platform base, not all ROM inputs. Recorded patches,
generated device and vendor trees, private stock firmware and signing inputs,
materialized Git LFS files, and the build environment still need their own
provenance and validation. A matching base does not prove a complete or
bit-for-bit reproducible Evolution X build.

For a **new empty** source directory, preview the guarded setup with:

```sh
python3 scripts/workspace.py init \
  --source-dir /srv/android/nezha-evolution \
  --source-lock config/evolution-source-lock.json --dry-run
python3 scripts/workspace.py sync \
  --source-dir /srv/android/nezha-evolution \
  --source-lock config/evolution-source-lock.json --jobs 8 --dry-run
```

Removing `--dry-run` authorizes initialization or download on a supported build
host and still requires all normal host, filesystem, path and Repo checks.
Apple Container use must go through its guarded wrapper and exclusive named
volume; do not attach a second writer or run these commands against a host bind
mount of the source tree. The low-level workspace commands require an explicit
`--source-lock`; omitting it retains the historical `default.xml` behavior.

Fresh initialization first uses the original pinned manifest and Repo, with
Repo signature verification retained. After verifying that initialization,
it atomically installs the exact lock bytes as `.repo/manifest.xml`. The
manifest Git checkout stays clean and keeps its original URL. That URL matters:
the snapshot's `github` remote uses `fetch=".."` relative to the Evolution
manifest origin. All used project URLs are checked as public HTTPS without
credentials; the unused upstream `private` remote is not fetched.

This behavior follows the pinned Repo implementation
[`manifest_xml.py`](https://github.com/GerritCodeReview/git-repo/blob/b85886fa9f5b4e2189cc5b2f40bd0a80459d4c77/manifest_xml.py#L1205):
it parses `.repo/manifest.xml` as a complete manifest, resolves remotes against
the manifest repository's origin, and gives each project's explicit SHA
precedence over branch defaults. The guarded sync retains
`--no-manifest-update` and disables Repo self-update; it does not pass force
checkout or force sync options. Its completion audit reports whether the
result is a clean match to the requested base.

Do not run bare `repo init` to switch an existing tree: Repo's
[`Link` implementation](https://github.com/GerritCodeReview/git-repo/blob/b85886fa9f5b4e2189cc5b2f40bd0a80459d4c77/manifest_xml.py#L486)
rewrites the selector. The workspace's `init --source-lock` never converts an
existing selector, resets projects, or removes local patches. It accepts an
existing tree only when that tree already selects the exact same lock. A tree
using the original `default.xml` must be preserved and audited separately, or
a new empty directory used for the locked setup.

To check the existing source tree on its current host without initialization,
download, a host probe, or modifying the checkout:

```sh
python3 scripts/workspace.py check-source \
  --source-dir /work/evolution \
  --source-lock config/evolution-source-lock.json
```

The JSON report identifies `active_selector` as `default.xml` or `source-lock`,
checks the project list and each project's HEAD, Git metadata, configured
remote URL, and tracked/untracked status, and reports local changes without
resetting them. `base_revisions_match` means all recorded project HEADs and
origins match; `clean_base_checkout` additionally requires no reported local
changes or other issues. Exit status is 0 for a clean base and 2 for drift or
local changes, with the audit JSON retained. Invalid control metadata fails
before project inspection. Git audits disable optional index locks, filesystem
monitor hooks, and implicit lazy fetching.

An audit of an existing `default.xml` tree does not turn it into a locked tree.
Run the audit while no other process is changing the checkout. Ignored files,
out-of-manifest trees, patch replay, LFS payload bytes, generated/private inputs,
and build reproducibility are explicitly outside this check; preserve and
record those separately before describing a whole build as repeatable.

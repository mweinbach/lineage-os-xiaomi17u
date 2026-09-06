# Input closure manifest

`scripts/input_closure.py` records every non-upstream input a Nezha build
selects, by hash, in one manifest. The [source lock](source-lock.md) pins the
1,179 upstream projects; this tool covers the rest of what a clean machine
would need to reproduce a build. It is the first step of the
[roadmap's](roadmap-20260906.md) reproducibility workstream.

## What it records

| Section | Contents | Check performed |
| --- | --- | --- |
| `upstream` | Source-lock manifest and Repo pins, snapshot identity, the reference pins from `config/sources.json` | The snapshot file is rehashed and must match the lock |
| `patches` | Every `.patch` under `patches/` with size and SHA256, and the JSON contracts that pin each one | A contract's declared patch hash must match the file; a contract naming a missing patch fails |
| `authored` | Every regular file under `Makefile`, `config/`, `device/`, `kernel/`, `policy/`, `recovery/`, `patches/`, `containers/`, `templates/`, `tools/`, `manifests/` and `scripts/` | Symlinks are refused; caches are skipped; files with ignored artifact suffixes are listed separately and never hashed |
| `environment` | Base image digests from `containers/apple/base-image.json` and the builder image and volume names | Presence only |
| `private_receipts` | For each receipt the caller names: path, size, SHA256, a few declared totals and the row count of its file list | The receipt must be a JSON object inside the workspace; its file list and bytes are never copied |

The `closure_sha256` is the hash of the canonical manifest body. Two manifests
with the same closure hash selected the same inputs. That does not prove a
build from them is bit-identical; the roadmap's clean-machine rehearsal is the
separate step that measures that.

## Commands

```sh
python3 scripts/input_closure.py generate \
  --output artifacts/input-closure/<identity>/closure.json \
  --private-receipt artifacts/kernel-inputs/<bundle>/receipt.json \
  --private-receipt artifacts/vendor-inputs/<bundle>/vendor-inputs.json \
  --private-receipt reports/<run>/source-installed.json

python3 scripts/input_closure.py verify \
  --manifest artifacts/input-closure/<identity>/closure.json
```

`generate` refuses to overwrite an existing output. `verify` recomputes the
manifest from the current tree and the same receipts, rejects a manifest whose
recorded closure hash no longer matches its own body, and lists added, removed
and changed authored files, patches and receipts. Exit status is 0 on a match,
1 on a difference and 2 on invalid input. Neither command runs Git, a build, a
container or a device command.

Name the receipts that actually fed the build: the kernel bundle, the vendor
bundle, the recovery bundle, the policy and `mi_ext` input bundles, and the
installed-source record for the identity. Keep the generated manifest under
ignored `artifacts/`; it names private paths.

Offline tests: `python3 -m unittest discover -s tests -p 'test_input_closure.py' -v`.
The workspace test generates a manifest from the real tree and requires every
declared patch contract to bind to its patch file.

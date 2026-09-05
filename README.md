# Evolution X for Xiaomi 17 Ultra

**Package7 is booted and working on Xiaomi 17 Ultra (`nezha`).** This workspace
now starts from that build to fix device issues and improve feature support.
The platform is Evolution X Android 16 QPR2 (`bka` / `bp4a`) on SM8850 / `canoe`.

Start with [current status](docs/workspace-status.md) for the selected build,
artifact hashes, development workflow and remaining feature work. The user
confirmed the working boot on September 5, 2026; the
[first-boot record](docs/package7-first-boot-20260905.md) preserves the earlier
retained-data failure and successful authorized clean-data retry.

## Build from the working baseline

| Keep using | Entry point |
| --- | --- |
| Package7 source and private inputs | [Build identity and preserved bundle](docs/workspace-status.md#working-baseline) |
| Existing Linux source volume | [Apple Container workflow](docs/apple-container.md) and `make apple-status` |
| Reviewed source revisions and local patches | [Source lock](docs/source-lock.md) |
| Device/kernel integration | [Device](device/xiaomi/nezha/README.md), [kernel](kernel/xiaomi/nezha/README.md) |
| Working76 recovery | [Recovery build instructions](recovery/twrp-working/README.md) and `make recovery-build` |
| Feature fixes | [Native features](docs/native-features.md) |

```sh
make help
make apple-status
make test-current
```

These commands inspect the workflow or run offline tooling tests. Inspect the
current source-volume owner before resuming a build; keep the existing checkout
and never attach concurrent writer VMs. Check disk, host, case sensitivity and
source selection before source syncs or builds.

Use `make test-current` while iterating, then run the full offline suite with
`python3 -m unittest discover -s tests -v` before completing changes.

Keep the installed Package7 bundle, signed archive, working76 rescue, stock return
inputs and private signing/build inputs. Build successors separately so a fix can
be compared with the booted baseline. Normal Android retains enforcing SELinux;
working76's permissive recovery defaults are a separate development choice.
The working76 workflow reproduces the tested prebuilt derivative, preserving its
runtime and hardware setup.

## Workspace layout

| Location | Role |
| --- | --- |
| `config/`, `device/`, `kernel/`, `patches/` | Build contracts, authored integration and reviewed source changes |
| `recovery/twrp-working/` | Selected working76 recovery patch and workflow |
| `scripts/`, `tests/` | Workspace tooling and offline tests |
| `docs/workspace-status.md` | Current baseline and next development steps |
| `docs/README.md`, `research/` | Reference index and sanitized evidence |
| `artifacts/`, `evidence/`, `reports/`, `.tools/`, `sources/`, `upstream/` | Ignored private inputs, outputs, logs, tools and checkouts |

The [documentation index](docs/README.md) keeps historical experiments available
without making them the current build path. Raw dumps, proprietary files, serials,
logs, personal data and signing keys stay out of Git. Device collection requires
an identified authorized phone; flashing, wiping, rebooting, restoring or changing
slots requires an explicit user request.

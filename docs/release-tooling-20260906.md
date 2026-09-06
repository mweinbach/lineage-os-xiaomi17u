# Release tooling landed on September 6, 2026

Four host-side tools from the [detailed plans](next-steps-plan-20260906.md),
written while the build VM was occupied by the userdebug build. Each is an
offline, stdlib-only script with tests; none dispatches a build, signs, or
contacts a phone. The section for each names what it does, what it does not
establish, and what remains before it is used on a real identity.

## Signing orchestrator (plan 5)

`scripts/release_signing.py` replaces the per-build f9e signing driver with a
selection JSON pinned by hash. `plan` validates the selection and prints the
six stage invocations; `run --execute-host-signing` performs them and writes
the same `stage-logs/` layout the f9e run left, so `release_workflow.py check`
recognizes the result.

```sh
make release-sign-plan SELECTION=/abs/selection.json SELECTION_SHA256=<retained hash>
python3 -B scripts/release_signing.py run --selection ... --expected-sha256 ... --execute-host-signing
```

The selection carries the artifact set, build number, the source record pin
with its entry count, byte total and transaction, the target-files pin, the
package admission and transfer pins with their expected operation names, the
retained input manifest pin and the local configuration path. Validation
repeats every assertion the f9e driver made: the admission and transfer must
be verified records for this build, bind the same source record, name the same
archive, and assert no writes, phone access or readiness. `plan` hashes the
small records but defers the archive hash to `run`.

Not established: any signing result. The stages are the existing maintained
scripts; the orchestrator only sequences them. The f9e driver stays untouched
as evidence.

## Kernel bundle provenance kind (plan 4)

`scripts/kernel_inputs.py` contracts and receipts now carry
`provenance.kind`, either `prebuilt` or `source`. Absent means `prebuilt`, so
the two existing bundles and their receipts are unchanged and still validate.
A `source` contract must carry a complete `source_build` block (ACK, vendor
and device-tree repositories with full commits, the defconfig hash, build
config, Kleaf target, toolchain and builder host), and its
`parent_package_sha256` must equal the canonical hash of that block. The
generated `kernel-inputs.mk` states `NEZHA_KERNEL_PROVENANCE_KIND` and, for
source bundles, the ACK commit, vendor commit and defconfig hash.

`kernel/xiaomi/nezha/stock-prebuilt.mk` defaults the kind to `prebuilt`
before including the bundle, compares it with
`NEZHA_EXPECTED_KERNEL_PROVENANCE_KIND`, and branches: prebuilt bundles keep
the package, AVB and origin checks; source bundles are checked against the
expected ACK commit `f1bdb135…`, vendor commit `45705be1…` and a defconfig hash
the caller must set. The release check applies to both kinds. Everything below
the provenance checks is shared. A test recomputes the expected commits from
the config-audit recipe.

Not established: any source kernel. No producer for source bundles exists yet;
that is plan 4 item 4 and needs a Linux x86-64 Bazel host.

## OTA package inspector (plan 2)

`scripts/ota_package.py inspect` opens an A/B package and reports its
`metadata`, `payload_properties.txt`, payload header and manifest, recomputing
the payload and metadata hashes the properties claim. With
`--published-inventory` it compares every partition's manifest hash and size
with the signed image inventory, so a package is tied to the bundle's bytes.
It reports whether the whole-file signature footer is present and states that
it did not verify the signature.

```sh
make ota-inspect OTA_PACKAGE=/abs/ota.zip PUBLISHED_INVENTORY=/abs/published-inventory.json
```

Exit status is 0 when the properties agree with the payload and, if given, the
inventory matches; 1 on a mismatch; 2 on a malformed package. The manifest
reader is a minimal protobuf wire decoder for the fields needed: block size,
minor version, partitions with their operation types, dynamic partition
metadata including the COW version, timestamp and security patch level.

Not established: signature validity, which stays with the pinned
`check_ota_package_signature.py` in the guest; whether `update_engine` accepts
the package; anything on the device. No real package exists yet; the guest
still has to build `otatools` and run `ota_from_target_files`.

## Both-physical-slot route (plan 1)

`scripts/delivery_route.py derive` validates a version-1 delivery plan with the
maintained bundle validator and derives the version-2 route: Super written
once and single-copy, then the seven physical images to slot B, then to slot A
in the f9e order. `validate` re-checks a route document. The route reads back
`countrycode` and `pvmfw` on both slots and lists the B-slot fastboot
variables the preflight must add.

```sh
python3 scripts/delivery_route.py derive --plan <plan.json> --expected-plan-sha256 <sha> --output <route.json>
python3 scripts/delivery_route.py validate --route <route.json>
```

Not established: the bundle assembler still produces version-1 bundles, the
preflight does not yet read the B-slot variables, and no install runner
consumes a route. Those changes wait until the other thread finishes with the
assembler and preflight. The route generates no fastboot commands.

## Tests

The four new or extended modules are in `make test-current`:
`test_release_signing`, `test_ota_package`, `test_delivery_route` and
`test_kernel_inputs`. Every stage, process and payload in them is synthetic.

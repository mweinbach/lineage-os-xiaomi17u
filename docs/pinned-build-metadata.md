# Pinned Evolution build metadata

The proposed [version-date patch](../patches/evolution/0012-pinned-version-date.patch)
lets the two Evolution date strings use an explicit build epoch. It is an
opt-in source preparation, **not installed in the guest**, and does not prove
reproducible images or a bootable ROM. Its [contract](../patches/evolution/pinned-version-date.json)
pins the vendor revision, full source preimages and postimages, helper, patch
and source-order evidence. Existing patches and source compositions are unchanged.

The observed midnight Kati regeneration came from two independent
`$(shell date +%Y%m%d)` expressions in `vendor/lineage/config/version.mk` at
revision `11d2966a3294a0a692fc958127c770cfe9c00a3c`. Those expressions consult
the process timezone and wall clock; they do not use `BUILD_DATETIME`.
Regeneration itself does not establish that policy CIL or images changed.

## Explicit date capability

With `NEZHA_USE_PINNED_BUILD_DATETIME=true`, the patch requires `BUILD_DATETIME`
to originate in the environment supplied to `soong_ui`. It invokes one fixed
helper path with `python3 -I -S -B`; the helper reads that environment directly,
without placing epoch text in a shell command. Isolated Python ignores Python
environment and site initialization, and bytecode writing is disabled.

The epoch must be canonical nonnegative ASCII decimal seconds: `0` or a
nonzero first digit followed by digits, at most `253402300799`. This upper
bound is the last second of UTC year 9999, keeping the existing eight-digit
date form. It is not an Android release, OTA or rollback validity bound.
Signs, leading zeros, whitespace, fractions, Unicode digits and overflow fail.
Missing input never falls back to the clock, a date file or `SOURCE_DATE_EPOCH`.
An unavailable or failed helper stops Make configuration instead of selecting
the legacy date.

The helper computes one UTC `YYYYMMDD` value per evaluation of `version.mk`.
Both `LINEAGE_VERSION` and `LINEAGE_DISPLAY_VERSION` consume that same value.
Unset, empty or `false` capability retains both original upstream date
expressions, in their original branch; other values fail. Private scratch
variables reject external overrides. Make reads the raw capability with
`$(value ...)`, so expressions such as `$(strip true)` or `$(shell printf true)`
are rejected rather than evaluated into an accepted value. The capability does not select itself in
the device product or change the source lock.

## Why this input is available during product evaluation

The pinned Soong revision is `cbcbea9e65503ca15b363a0b06dda88fdbcb0154`; the
Make revision is `a438ca40c6ed779042f806142b1165ba1360a7b2`. The contract records
the byte identities and capture provenance of these source files:

1. `ui/build/config.go:newConfig` copies the invoking process environment and
   consumes explicit `BUILD_DATETIME` before product configuration. Its
   fallback epoch remains an internal field; it does not invent an exported
   `BUILD_DATETIME` for this capability.
2. `ui/build/exec.go:Command` copies that environment into child processes.
   `dumpvars.go` invokes Kati on `build/make/core/config.mk`; ordinary
   `kati.go` retains `BUILD_DATETIME` too. Build number and hostname are the
   metadata variables that ordinary Kati explicitly removes from its environment.
3. `core/config.mk:422` includes `core/envsetup.mk`, whose line 351 includes
   `core/product_config.mk`. Product import evaluates the inherited vendor
   `config/common.mk`, which includes `config/version.mk`.
4. `BUILD_DATETIME_FROM_FILE` is assigned later at `core/config.mk:874`.
   `DATE_FROM_FILE` is assigned in `core/main.mk` only after including
   `config.mk`. Neither later Make helper is suitable here. Standalone dumpvar
   evaluation also need not have called `SetupOutDir` to create a date file.

This establishes the Soong-to-Kati source path. Native adoption must still
verify Kati's actual helper environment in both dumpvars and build configuration.
Normal `SetupPath` places pinned build-tools before the host tool interposer;
record the actual Python executable and runtime used. A successful host helper
test is not a substitute for that native check.

## Record the remaining build inputs

Set these inputs only in the environment of a reviewed build invocation;
do not change host clocks or global shell configuration. Choose the epoch and
build identifier as explicit release inputs, and keep them unchanged across
every phase of that build. This patch does not choose values for the current
bring-up or alter active jobs.

| Input | Existing supported behavior and effect |
| --- | --- |
| `BUILD_DATETIME` | Unix epoch written to `$OUT_DIR/build_date.txt`; generated partition dates and several boot-image AVB salts consume it. |
| `BUILD_NUMBER` | Explicit single-word filename-safe source identifier; without it, Soong independently uses current time in an engineering identifier. Avoid an `eng.` prefix for the pinned identifier because property generation substitutes the epoch for such incremental versions. |
| `BUILD_USERNAME` | Explicit metadata username; otherwise the current OS user supplies `ro.build.user`. |
| `BUILD_HOSTNAME` | Explicit metadata hostname; otherwise the OS hostname supplies `ro.build.host`. |
| `EVO_BUILD_TYPE` | Keep the recorded `Unofficial` selection; the existing accepted values are `Official` and `Unofficial`. |
| `WITH_GMS`, `LINEAGE_BUILD` | Record the selected version variant and device value; neither independently fixes a date. |

The Evolution dates reach `ro.evolution.build.version` and
`ro.evolution.display.version` in product properties, and the eventual
Evolution ZIP filename and JSON name/download fields. OTA JSON separately
reads `ro.system.build.date.utc`. No OTA or signing behavior is changed here.

`android/build_prop.go` deliberately treats the date file as an **order-only
dependency**. Updating the environment or seeing a new `build_date.txt` does
not prove old `build.prop` files or images were regenerated. Do not remove a
checkout, reset source or invalidate unrelated outputs to make metadata agree.
A later baseline must use a reviewed rebuild plan and inspect actual outputs.

Record the invocation metadata, source and tool pins, exact date/number/hostname
files, fingerprint files, and date/version properties from every completed
partition. Bind each image to the phase that produced it and state when an
output was reused. Preserve historical build dates as observed evidence;
never relabel them as outputs of this new capability.

## Validation and adoption gates

The offline tests execute the actual helper extracted from the public patch,
including UTC midnight and leap-day boundaries, hostile/noncanonical inputs,
missing alternative sources, clock independence and failure output. They also
bind both full source files and preserve the unchanged legacy/property regions.
Run `python3 -m unittest discover -s tests -v` with the workspace suite.

Before a guest installation, verify exact source preimages, absence of the new
helper, unchanged existing security-property patch 0001, patch replay without
fuzz, and both postimages. Extend an explicit source composition separately.
Use pinned native Kati fixtures for enabled, disabled, invalid capability,
missing/malformed epoch and helper-failure cases, with no image recipes. Then
check the actual `lineage_nezha-bp4a-user` product through dumpvars and ordinary
configuration, recording the helper runtime and child environment. Test a
second identical-epoch invocation across a different actual UTC date without
changing the system clock. These native checks have not yet run.

Even after those checks, complete-ROM reproducibility requires separate
verification of proprietary and generated inputs, image metadata, tools,
signatures, rollback settings and packaging. A fixed version date alone makes
no claim about those outputs, first boot or hardware support.

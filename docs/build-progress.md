# Nezha product and build progress

The authored `lineage_nezha-bp4a-userdebug` product now passes actual
Soong/Kati configuration and has built Android ARM64 `libbase.so` plus the
x86-64 host `checkvintf` tool in the existing Apple Container source checkout. It
selects Nezha, canoe, ARM64, 4 KiB kernel pages, shipping API 36 and board API
202504, with AVB enabled. The [build record](../research/build-progress.json)
contains the exact inputs, receipts and subsequent compilation results.

This is a `framework-checks` product. It permits configuration and module
compilation while keeping complete target-files, OTA, super-image and flash
admission false. Unknown physical capacities and bootloader state do not
prevent local source generation or compilation. They remain requirements for
any eventual device experiment, which needs separate user authorization.

## Installed source and inputs

| Source path | Current input |
| --- | --- |
| `device/xiaomi/nezha` | Authored product plus generated boot, partition-budget and enforcing first-stage fstab configuration |
| `kernel/xiaomi/nezha` | Stock-prebuilt integration wrapper, not a fabricated source-kernel tree |
| `vendor/xiaomi/nezha-kernel` | 950 hash-verified files, including the exact Image, DTB/DTBO, 914 module instances and preserved ordered load/block lists |
| `vendor/xiaomi/nezha` | Unchanged vendor/ODM EROFS inputs plus nine selected Camera dependency files and their [recorded XML derivations](camera-inputs.md) |
| `vendor/lineage/config/common.mk` | Two recorded defaults made optional so Nezha can enforce privileged permissions and prohibit OTA downgrade |

The public platform manifest and all its project revisions were preserved.
No second sync or replacement source checkout was created. The resolved
manifest describes the upstream base; local source/admission receipts and the
[pinned property patch](../patches/evolution/security-properties.json) describe
the additional inputs and modified vendor file. They must travel together in
any build provenance record.

The initial transfer verified **975 files / 5,932,585,937 bytes** inside the
owning VM. No home directory, Downloads directory, credentials or phone
evidence was bind-mounted. `container cp` reported success in this runtime but
did not make the files visible under the mounted `/work` path; the accepted
transfer used `container exec` streaming, checked every hash and read back
every written file before installation. Existing attempts and inputs were
preserved. Always verify destination contents from the actual builder view.

## Regenerate without replacing existing evidence

The source templates are committed. The large input bundles and generated
receipts remain ignored. To reproduce the device configuration from existing
verified bundles, choose a new output path:

```sh
python3 scripts/generate_device_tree.py generate \
  --kernel-receipt artifacts/kernel-inputs/nezha-xiaomi-eu-candidate-v2/receipt.json \
  --vendor-receipt artifacts/vendor-inputs/nezha-xiaomieu-b29afecc-camera-v2/vendor-inputs.json \
  --output artifacts/device-candidates/nezha-framework-NEW
python3 scripts/generate_device_tree.py validate \
  --output artifacts/device-candidates/nezha-framework-NEW \
  --purpose configuration
```

Generation rehashes the bound inputs and refuses existing output directories.
It does not mutate the Linux checkout or phone. `--purpose target-files` and
`--purpose flash` deliberately fail for this profile. The source retains the
required `mi_ext` mount; it does not pretend that omitting that image makes a
complete partition set.

The [kernel wrapper](../kernel/xiaomi/nezha/README.md) explains module packaging.
The [DTS recipe](../kernel/xiaomi/nezha/dts/README.md) produces private source for
all eight base DTBs and the Nezha overlay. Recompilation preserves all parsed
nodes/properties and fixups, corroborated independently with sorted DTC output.
Rebuilt binary layouts differ, so this is source preparation, not permission
to replace the stock DTs or a claim that a rebuilt kernel boots.

## Verified boundaries

The initial product check passed at `2026-08-27T18:28:40Z`, with no missing
dependency or security-check overrides. The first module-graph attempt exposed
missing Lineage Soong exports; the device now includes the complete
`BoardConfigLineage.mk` hook after its prebuilt selector and board values.
The [current build record](../research/build-progress.json) tracks later
errors and fixes without turning failed attempts into successful builds.

The third module attempt completed successfully at `2026-08-27T19:09:52Z`
after 4,591 Ninja actions. Independent ELF and SHA256 checks distinguish the
218,624-byte ARM64 `libbase.so` from the 6,179,856-byte x86-64 host checker.
The host checker subsequently executed; the Android library was not run on
the phone. This proves selected modules through the real Nezha product graph,
not a complete image set or a working native feature.

An independent post-build audit checked all 1,179 project HEADs and remotes.
Exactly 1,178 worktrees were clean; the only project change was the recorded
vendor property patch. Authored directories outside Repo have separate input
receipts. No unexpected project edits were found and no source sync was
repeated.

The actual Ninja process was observed under nsjail with separate mount,
network, PID and user namespaces. Its initial product configuration mounted
source **read-write**, unlike the earlier standalone read-only probe.
The later authored board setting explicitly requires read-only source for the
Camera build. Its actual Ninja mount table at `19:37:34 UTC` confirmed source
read-only and output read-write, with the same four separate namespaces.
The observation receipt has SHA256
`30916dc00013762cb2e8d05bbb86ab42e6f80f38f47c3f1bfade62c5926f977e`.
Neither observation should be substituted for the other, and the upstream
basic Soong/Kati sandbox remains unchanged. Observing the running process is
not a successful build result.

The v4 device admission selected Camera bundle v2 and that stronger
source setting. Both earlier installed source directories were preserved
outside the Android checkout before replacement; only 575,475 bytes of small
files crossed from the host. Vendor/ODM images were copied and reverified
inside the same VM with unchanged hashes. The Camera build is a separate
experiment; its current result is in the build record.

The first Camera attempt reached its one-hour probe deadline at `20:26:45 UTC`
and was cancelled. No compiler failure preceded the cancellation. All compiled
outputs were retained; the second attempt resumes in the same directory with
a two-hour bound and adds the Soong `secilc` and `sepolicy-analyze` host tools.
This is not a clean build or another source sync.

Current device admission **v5** was installed at `20:46:42 UTC` by an atomic
directory exchange, preserving v4 outside the checkout. Only BoardConfig and
its README changed; the kernel and vendor bundles did not. The regenerated
dexpreopt configuration now has **`RelaxUsesLibraryCheck=false`**, while
`WithDexpreopt=true` and `DisablePreopt=false`. The effective-setting receipt
has SHA256 `a1288fd08e3e9238bc68fde278f0f6a6ebf66fa135c3d613a8a008072a15d82d`.
This corrects the inherited BCR relaxation without disabling preoptimization.
It establishes the generated configuration, not validation or installation of
the [Camera APK](camera-apk-integration.md), which remains outside the bundle.

The separate [SELinux contract](selinux-contract.md) captures the exact stock
policy inputs and reports seven neverallow failures using native tools from
pinned sources. No policy binary was produced, and no assertion was filtered.
Actual Soong-tool corroboration and a combined Evolution/vendor policy check
are subsequent experiments, not implied by building the compiler tools.

The built host checker also passed a [vendor/ODM VINTF load and merge](vintf-validation.md)
with the unchanged active APEX list and exact CAS/Widevine fragments. The
stock-framework check reports five HIDL definitions absent from this
validator's compiled metadata. Full compatibility with the assembled Evolution
framework remains a separate check; no matrix or APEX list was filtered to
produce a pass.

The second attempt found an upstream CI-packaging assumption about output
paths. With an absolute `OUT_DIR`, the host Perfetto path reached the normal
artifact-path validator and was correctly rejected. The accepted workaround
uses a source-root output symlink, which the pinned Soong sandbox supports:

```text
/work/evolution/out-nezha-framework-20260827T1835Z
  -> ../out/nezha-framework-20260827T1835Z
OUT_DIR=out-nezha-framework-20260827T1835Z
```

The link resolves to the same existing directory and inode, and its `.out-dir`
and `.top` markers were preserved. Nothing was deleted or reset. This pinned
CI code requires the relative name to begin with `out`; `../out/...` does not
avoid the bug. No Soong source, path validator or sandbox setting was changed.
This reproduces the default CI archive behavior, which already omits those
host packaging entries; it does not prove that Perfetto is in the CI archive.
[CI path handling](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/ci_tests/ci_test_package_zip.go#L300-L319),
[output symlink handling](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/ui/build/soong.go#L554-L572),
[sandbox resolution](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/ui/build/sandbox_linux.go#L77-L85).

Inside the existing owning VM, with the admitted inputs already installed,
the bounded module command is:

```sh
cd /work/evolution
test -L out-nezha-framework-20260827T1835Z
test "$(realpath out-nezha-framework-20260827T1835Z)" = \
  /work/out/nezha-framework-20260827T1835Z
env PATH="$PWD/prebuilts/build-tools/path/linux-x86:$PATH" \
  OUT_DIR=out-nezha-framework-20260827T1835Z \
  TARGET_PRODUCT=lineage_nezha TARGET_RELEASE=bp4a \
  TARGET_BUILD_VARIANT=userdebug \
  GOTOOLCHAIN=local GOENV=off GOPROXY=off GOSUMDB=off \
  GOCACHE=/work/cache/nezha-framework-go \
  build/soong/soong_ui.bash --make-mode -j12 libbase checkvintf
```

Do not run another build concurrently in this output directory. Preserve the
complete logs and fail sandbox validation if the build reports
`Build sandboxing disabled due to nsjail error.` A module build does not approve
the framework profile for complete image or device testing.

The Xiaomi.eu inputs retain their known AVB failures and unverified origin.
No old vbmeta is imported as a valid new chain. Engineering AVB configuration
uses an explicitly identified AOSP development key; this is not an OEM key,
production signing policy or an accepted flashable image set. Input hashes,
correctly generated signatures and device trust are separate questions.

The official-named fastboot TGZ is visible in Downloads at the expected full
length, but normal content reads timed out. It has not been hashed, validated
or admitted. See [acquisition status](firmware-source.md). It can replace the
modified baseline only after normal access, intake and image verification.

No ROM boot, camera/Leica function, IMS, fingerprint, charging, encryption or
other hardware behavior has been established on Evolution X. Run `make test`
for tooling changes; build results and eventual authorized hardware tests are
separate evidence.

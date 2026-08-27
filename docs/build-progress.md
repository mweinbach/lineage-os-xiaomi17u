# Nezha product and build progress

The authored `lineage_nezha-bp4a-userdebug` product now passes actual
Soong/Kati configuration and has built Android ARM64 `libbase.so` plus the
x86-64 host `checkvintf` tool in the existing Apple Container source checkout.
The nine selected Camera dependency modules and the Soong policy tools have
also built successfully, with output hashes and actual checker execution
verified. The Camera APK itself is not included. The product
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
| `vendor/xiaomi/nezha` | Factory vendor/ODM EROFS inputs plus the nine byte-identical selected Camera dependencies and their [recorded XML derivations](camera-inputs.md) |
| `vendor/lineage/config/common.mk` | Two recorded defaults made optional so Nezha can enforce privileged permissions and prohibit OTA downgrade |
| `system/sepolicy/private/su.te` | The unconditional permissive-su declaration removed; all permission grants and assertions retained |

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
outputs were retained; the second attempt resumed in the same directory with
a two-hour bound and adds the Soong `secilc` and `sepolicy-analyze` host tools.
This is not a clean build or another source sync.

Device admission **v5** was installed at `20:46:42 UTC` by an atomic
directory exchange, preserving v4 outside the checkout. Only BoardConfig and
its README changed; the kernel and vendor bundles did not. The regenerated
dexpreopt configuration now has **`RelaxUsesLibraryCheck=false`**, while
`WithDexpreopt=true` and `DisablePreopt=false`. The effective-setting receipt
has SHA256 `a1288fd08e3e9238bc68fde278f0f6a6ebf66fa135c3d613a8a008072a15d82d`.
This corrects the inherited BCR relaxation without disabling preoptimization.
It establishes the generated configuration, not validation or installation of
the [Camera APK](camera-apk-integration.md), which remains outside the bundle.

The second Camera attempt **passed at 21:17:15 UTC**, completing 4,206
incremental Ninja actions without a timeout or sandbox fallback. The actual
Ninja observation at `20:58:32 UTC` again confirms four separate namespaces,
read-only source and read-write output. Its receipt is separate from the
first attempt's observation. The build receipt has SHA256
`890368868de6b6e9822f24bb79e358c84ba269f48a0898830e50388e2eb953b9`.

All nine installed dependency files match their admitted source hashes.
The four JARs also pass member-content and CRC comparison, and all four have
generated ARM64 ODEX and VDEX outputs. The JNI library's actual
`g.cc.checkElfFile` action completed with 20 shared-library inputs, the
16 KiB page-alignment check and no undefined-symbol exemption. The output
verification receipt has SHA256
`517abf483adf40ec5dcb0386231667f03be93771a73e0d6746096f4f8ee8d399`.
The built `secilc`, `sepolicy-analyze` and `checkvintf` files are x86-64 host
tools; none of these results proves Camera or Leica behavior on the phone.

Device admission **v6** was installed at `21:34:15 UTC`, preserving v5
and all existing outputs. Its only source change copies the stock
`system_dlkm.modules.blocklist` selector into vendor_dlkm, where the stock
loader expects it. This is separate from system_dlkm's own blocklist and
does not block the intended vendor ZRAM pair. The kernel and vendor input
receipts are unchanged. See the [ZRAM contract](zram-module-plan.md).
Installation receipt SHA256:
`ab7e791bca52cca3d0742a1179939e1ecc49c78cf0cb7857543da8947c6d59c7`.
The Camera pass above belongs to v5, not this later source installation.

The v6 [boot/DLKM build](boot-dlkm-build.md) subsequently passed at
`22:01:05 UTC`, producing boot, DTBO and both DLKM images plus the requested
framework policy inputs/tests. Independent inspection verifies the exact
kernel and DTBO payloads, internal AVB checks and all 484 module hashes inside
the EROFS images. The vendor-side system selector is present with its stock
hash. This is not a complete signed image set or a successful vendor-policy
compatibility result; those boundaries are explicit in that separate record.

Admission **v7** was installed at `22:26:29 UTC`, preserving v6.
It records the stricter `user` variant and registers that lunch choice alongside
the existing `userdebug` choice. Both remain framework-checks products; `eng`
and complete-ROM/flash admission remain rejected. The kernel/vendor bundles,
generated geometry and fstab are unchanged. Installation receipt SHA256:
`4e01f4ba023e07aaec605baf341b7b4bd696e09a67862f91b811a5ebde67c120`.

A separate user policy/tool build passed at `22:44:46 UTC` in the fresh output
`/work/out/nezha-user-policy-20260827T2220Z`, through its matching source-root
`out-nezha-user-policy-20260827T2220Z` alias. Reusing the userdebug output for a
variant switch could trigger install-clean behavior; this experiment does not
request that operation or reset the previous output. Its four verified images
and seven framework files were rehashed before and after: all eleven are
unchanged. The 2,788-action build included the framework neverallow, policy and
device-type tests. Build receipt SHA256:
`5dff46fcbbbe5ffd0d8a8a046ac93c070b61ebf2c63dc70c2ae3dd573df25fc8`.
Those source targets do not include the captured factory vendor/ODM CIL.
Combining that exact policy with the new user outputs is a separate check,
not a pass established by these successful framework targets. No live Ninja
namespace snapshot was captured for this attempt; its logs show no sandbox
fallback. Earlier sandbox observations retain their own attempt identities.

Current admission **v8** was installed at `23:28:02 UTC`. It uses the separately
verified factory vendor/ODM images, factory API/property facts, factory fstab
flags and package GPT budgets. Its DTBO budget is now **32 MiB**, with the
unchanged 22 MiB stock input. All eight logical AVB declarations, five boot
verification rows, GSI key-path references, encryption fields and two inert
vold device-node patterns are retained. The existing kernel bundle keeps its
Xiaomi.eu provenance; equality with selected factory components does not
relabel its origin. See [factory input reuse](factory-input-reuse.md).

The same owning VM received 30 files totaling 5,727,927,659 bytes through a
hash-checked stream, with destination readback. Both old device/vendor trees
are preserved under `/work/candidates/nezha-factory-v8/`. All 950 kernel input
files and 18 historical output artifacts were checked unchanged. No output
directory was reset. Installation receipt SHA256:
`9775be640f7e37d722113e5c86d1774daa1da6ecafa8468637018ea62a6ea7dc`.

V8 also requires Treble labeling errors rather than warnings and rejects an
unreviewed tracking list. This alone does not schedule or pass the labeling
test at platform policy version `202504`. Separately, the pinned source's
unconditional `permissive su;` statement was removed at `23:29:36 UTC`, with
the original file preserved and all other policy statements unchanged.
The [patch](../patches/evolution/selinux-enforcement.json) binds both source
hashes. Its installation receipt SHA256 is
`f776922d1e1167fa53998d0bbf8983fea0f11a9a756b160f75b4e4405918542b`.
No build or zero-permissive-domain result for these new inputs is claimed
yet; the earlier user v7 result remains a different policy snapshot.

The separate [SELinux contract](selinux-contract.md) captures the exact stock
policy inputs and reports seven neverallow failures using native tools from
pinned sources. Repeating the same ten unmodified CIL inputs with the actual
Soong-built x86-64 compiler returned the same seven neverallow failures.
No policy binary was produced, and no assertion was filtered. A combined
Evolution/vendor policy check remains a separate experiment; building the
compiler tools alone does not establish policy compatibility.

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

The separately supplied factory-named TGZ is now readable under `sources/`.
Its [intake and image extraction](factory-firmware-intake.md) passed; the
earlier Downloads timeouts remain historical observations. It has its own
provenance and [passing selected AVB/filesystem checks](factory-firmware-validation.md).
The installed build still uses the
explicit Xiaomi.eu bundles above; no new factory image was silently substituted.

No ROM boot, camera/Leica function, IMS, fingerprint, charging, encryption or
other hardware behavior has been established on Evolution X. Run `make test`
for tooling changes; build results and eventual authorized hardware tests are
separate evidence.

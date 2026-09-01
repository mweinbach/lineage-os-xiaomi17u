# Nezha product and build progress

The **2026-09-01 04:26:42 UTC images1 attempt** finishes with native exit 0
and wrapper exit 1. The sole validation failure is the combined Ninja graph's
pool-depth change from 15 to 8, explained by the pinned generator and observed
`-j8`. The old graph body is reconstructed to its sealed hash, not independently
captured; all six admission maps, 254 configuration fields and fifteen other
graphs match. The failed receipt remains unchanged. The **separate read-only
postcheck passes at 05:03:29 UTC**, checking four output images, three sidecars
and all seven producers' fresh action evidence without another build or output
write. Saved-receipt readback matches; independent artifact review remains pending;
target-files, signing and boot remain unverified.

The **2026-09-01 03:22:47 UTC ordinary `nothing3` checkpoint** passes graph
regeneration, all six source/input guard groups and the six metadata-file value
checks for `nezha.8643b579050aab0dd3218ae3`. The only change in the 254-field
configuration is the approved namespace-export list, from eight to ten entries.
Its 166 frontend steps plus one `nothing` phony are not component/image builds
or tests. Ninja and its sandbox are observed, but exact Ninja arguments are not
qualified by this profile; matching metadata values do not prove fresh rewrites.
The subsequent read-only producer capture, exact recovery-declaration review
and nine-proof staging are complete; those preparation steps execute no image
recipe. The later four-image/three-sidecar invocation is recorded above. The
first optional AIDL capture fails its bounded query; v2 completes read-only
capture of 1,163 nodes and 62 API-check descriptions without compiling or running
the component checks. Independent review verifies this scoped capture, not full
dependency closure. Kernel AVB/origin, signing, super/OTA and hardware gates remain. See
[current status](workspace-status.md) and the
[ordinary run and preparation evidence](../research/workspace-integration.json).

Commit **1ef9bf3** adds the maintained
[signed target-files reconciler](signed-target-files-reconciliation.md) and
streaming archive copier. Its 72 added tests use synthetic archives and mocked
cryptography; its full workspace suite passes 4,261 tests in 192.570 seconds,
with zero skips. The later preparation-document checkpoint passes 4,261 tests
in 204.808 seconds with zero skips, before this image-attempt/capture update.
No actual signing or target-files reconciliation has run.

The **2026-09-01 03:01:01 UTC product-query checkpoint** verifies the adopted
537-source/thirteen-project configuration with identity
`nezha.8643b579050aab0dd3218ae3`: config6 passes 21 values and context6 passes
seven, with all six source/input guards and the full 254-field generated
configuration unchanged. Reprojection binds the declared metadata-copy modes;
it does not chmod the source. These are ordinary product queries, with no
observed Ninja action or image build. Literal `FROM_FILE` references do not
qualify six metadata-file contents or freshness. The later `nothing3` result
above separately verifies their values; kernel AVB/origin warnings, packaging,
signed-chain and boot gates remain. See
[current status](workspace-status.md) and the
[query evidence](../research/workspace-integration.json).

The **2026-09-01 02:14:58 UTC maintenance checkpoint** clears the recorded
source-staging capacity blocker: the existing ext4 volume is now **1,024 GiB**,
with 402,047,229,952 bytes available against the unchanged 226,459,516,499-byte
budget. The same builder and then-current 539-source proof are verified after restart;
the retained 800 GiB APFS clone/swap state is not an independent physical backup.
This is environment maintenance, not a new Android build or source adoption.
See [current status](workspace-status.md), [environment details](apple-container.md)
and the [maintenance evidence](../research/workspace-integration.json). The
component and source checkpoints below retain their historical input scope.

The authored Nezha product has completed actual user and userdebug component
builds in the existing Apple Container source checkout. Built and inspected
outputs include boot, init_boot, vendor_boot, DTBO and both DLKM images across
their recorded input snapshots. ARM64 `libbase.so`, the nine selected Camera
dependency modules and the host VINTF/policy tools also built successfully.
The Camera APK itself is not included, and a complete ROM has not been built.
The earlier [OEM policy integration](oem-policy-integration.md) restores the
three missing service/file classifications through authored system_ext source,
Android-generated object roles and API mappings. The **v11b** native phase
passed at **2026-08-29 20:47:06 UTC**, completing 31 Ninja actions, including
the ownership guard, strict combined-policy compiler and all nine factory
context/structural checks. Independent v11 analysis passed at **20:54:46 UTC**:
all 6,366 assertions remain with their reviewed concrete coverage, effective
permissions change by exactly five additions and 47 removals, and three actual
policy binaries have zero permissive domains. Complete Treble labeling and
image adoption remain outstanding. The [v10 native integration](policy-source-integration.md)
first applied the reviewed helper M4 and Binder corrections; its independent
analysis preserved all 6,366 assertion statements and found zero permissive
domains in three binaries. Its three then-failing checks are preserved in that
record. The
[v9 source build](dsp-policy-build.md), [Binder experiment](binder-policy-correction.md)
and [helper projection](helper-policy-projection.md) retain their historical
results; later work does not rewrite those earlier failures or copied-CIL
proofs. The [v11 result record](../research/oem-policy-integration.json) binds
the source installation, failed first guard, correction and successful retry.
The product
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
| `vendor/xiaomi/nezha-policy` | Separate private original policy/context corpus, exact-input derivation tools and native validation modules; no opaque image replacement |
| `vendor/lineage/config/common.mk` | Two recorded defaults made optional so Nezha can enforce privileged permissions and prohibit OTA downgrade |
| `system/sepolicy/private/su.te` | The unconditional permissive-su declaration removed; all permission grants and assertions retained |
| `system/sepolicy/private/init_dev_config.te` | Reviewed explicit capability gates two helper property SET permissions; other boards retain upstream undefined/true behavior |
| `system/core/init` | Known boot/build property masking helpers disabled; existing `ro.boot.*` values kept write-once |
| `build/make/core/Makefile` | Reviewed fail-closed consumer of the working76 recovery bundle |

This table describes the installed v11b checkpoint, not every authored change
in the workspace. The optional OEM properties and framework-provider policy,
the Camera runtime bundle/Soong patch, mi_ext/0007 packaging, 0006 A/B recovery
correction, and native EROFS exporter still require guarded guest adoption and
their own native results. See [current status](workspace-status.md) and the
[v11 milestone](oem-policy-integration.md). The selected VINTF input build has
separately passed; its [artifact audit](vintf-compatibility.md) still identifies
missing framework fragments and APEX packages before complete compatibility.

The public platform manifest and all its project revisions were preserved.
No second sync or replacement source checkout was created. The resolved
manifest describes the upstream base; local source/admission receipts and the
[vendor property patch](../patches/evolution/security-properties.json),
[SELinux enforcement patch](../patches/evolution/selinux-enforcement.json) and
[init property patch](../patches/evolution/init-boot-properties.json),
[helper capability](../config/nezha-init-helper-capability.json) and
[recovery consumer](../patches/evolution/prebuilt-recovery.json) describe
the additional inputs and four modified Repo projects. They must travel
together in any build provenance record. Historical source audits below
describe their own earlier checkpoints.

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
verified bundles, choose a new output path. The current factory profile uses
all three explicit factory-contract arguments together:

For the current native-policy profile, first stage a new private policy bundle
using the [OEM policy workflow](oem-policy-integration.md), including its
explicit `--oem-policy-contract config/nezha-oem-policy.json` option. The example below
expects that bundle at `artifacts/policy-inputs/nezha-factory-NEW` and adds its
explicit helper capability and receipt; it does not silently opt into them.

```sh
factory_analysis=artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b
python3 scripts/generate_device_tree.py generate \
  --variant user \
  --kernel-receipt artifacts/kernel-inputs/nezha-xiaomi-eu-candidate-v2/receipt.json \
  --vendor-receipt artifacts/vendor-inputs/nezha-factory-d2cf57fd-camera-v1/vendor-inputs.json \
  --firmware-layout "$factory_analysis/normalized-layout-v1/firmware-layout.json" \
  --vintf-contract "$factory_analysis/build-property-comparison-v2/analysis/vintf-properties.json" \
  --factory-boot-contract research/factory-boot-contract.json \
  --partition-metadata research/partition-metadata.json \
  --dsp-policy-contract research/dsp-policy-integration.json \
  --init-helper-capability-contract config/nezha-init-helper-capability.json \
  --oem-policy-contract config/nezha-oem-policy.json \
  --policy-inputs-receipt artifacts/policy-inputs/nezha-factory-NEW/policy-inputs.json \
  --fstab-source "$factory_analysis/boot-analysis/ramdisk-comparison-v2/text-members/vendor_boot-0001.txt" \
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

Admission **v8** was installed at `23:28:02 UTC`. It uses the separately
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

An independent read-only audit at `23:35:12 UTC` rehashed all 10 installed
device files and 17 vendor files, including both replacement images:
5,727,913,542 bytes, with no missing or extra files. It also checked the
admission and kernel receipt bindings, without repeating the full kernel
payload audit or accessing either output directory. Audit receipt SHA256:
`a3fab1746edcb26b9ec1e954451d524cfebaf2cc75c20691f700ac9b94d8d676`.

V8 also requires Treble labeling errors rather than warnings and rejects an
unreviewed tracking list. This alone does not schedule or pass the labeling
test at platform policy version `202504`. Separately, the pinned source's
unconditional `permissive su;` statement was removed at `23:29:36 UTC`, with
the original file preserved and all other policy statements unchanged.
The [patch](../patches/evolution/selinux-enforcement.json) binds both source
hashes. Its installation receipt SHA256 is
`f776922d1e1167fa53998d0bbf8983fea0f11a9a756b160f75b4e4405918542b`.
Those installation receipts precede compilation; the earlier user v7 result
remains a different policy snapshot. The later
[hardened user v8 build](user-security-build.md) passed at `00:17:18 UTC` on
August 28 after 6,551 Ninja actions, including init, init_boot, vendor_boot,
DTBO and source-policy targets. Both generated source-policy binaries then
passed an independent, unfiltered check with zero permissive domains.
The ten-file combination with exact factory vendor/ODM CIL still fails five
assertions and produces no binary. The generated precompiled policy is staged
under ODM; it has not replaced the policy inside the retained factory image.

The pinned init source was hardened at `23:49:25 UTC`. Both init-stage
defaults now use `SPOOF_SAFETYNET=0`; the previously unconditional release,
debug and vbmeta property helper calls now obey that guard. Existing
`ro.boot.*` values remain write-once even during vendor property initialization.
Property name/value, SELinux and socket checks are unchanged. The exact-source
patch and both resulting Git blobs passed isolated application checks before
installation. The original files and all 18 earlier output artifacts were
preserved. Installation receipt SHA256:
`e8893a3c2e26cd19ba5ad0b6c521d19a214de6f5ae295c3316701dd2736f02c3`.
This is source hardening, not a runtime property or bootloader-state result;
libinit hooks and initial property sources still need separate verification.
The subsequent complete source audit matched all 1,179 project HEADs and
remotes, with exactly three expected patched projects and 1,176 clean ones.
The audit and successful v8 build have separate receipts; the original source
installation receipt's compilation fields remain historical observations.

The v8 [boot-content inspection](factory-boot-build.md) subsequently passed
for the 8 MiB init_boot, 96 MiB vendor_boot and 32 MiB DTBO images. It verified
the packaged first-stage init, all 430 vendor-ramdisk modules, six metadata
files, admitted fstab, DTB and DTBO payloads. All three AVB hash descriptors
pass, but their algorithm is `NONE`: the individual blocks are unsigned and
do not establish a complete signed chain. The second-stage init was built
and inspected, but has not been verified inside a completed system image.

At the August 28 checkpoint, source admission **v9** was generated with the
explicit [DSP policy contract](dsp-policy-integration.md). Its installation changed
only the generated board wiring and two source-policy files. The v8 source
directory was preserved, all 63 output guards passed, and the vendor/kernel
receipts, six checked project revisions and four patched source files remained
unchanged. The 12 transferred source files total 24,435 bytes; control receipts
are separate. Installation SHA256:
`dae184a0129e4224e851b779e760a38c03a66559d114bf19e7b4590913543a76`.
This installation record does not itself establish the subsequent Soong or
full factory-policy result.

The subsequent [v9 policy build](dsp-policy-build.md) passed at `01:26:15 UTC`
on August 28 after 201 Ninja actions. The actual Soong outputs contain the
intended DSP attribute and isolated-compute membership. Both source-policy
binaries pass unfiltered permissive-domain checks. The strict combination of
all seven new framework CIL files and three unchanged factory files then failed
four assertion sites instead of five: two Binder conflicts and two init-helper
property conflicts remain. All 6,366 assertions are retained. No combined
policy binary or factory compatibility pass is claimed.

This incremental build preserved all 12 checked v8 boot/init artifacts, the
sealed v8 snapshot and eleven earlier userdebug artifacts. A fresh complete
source audit again matched all 1,179 project HEADs and remotes, with only the
three recorded patched projects. It did not repeat the earlier LFS payload
audit or inspect ignored files and authored directories outside Repo. The
source checkout and output directories were not reset, and the phone was not
accessed.

The subsequent [Binder comparison](binder-policy-correction.md) compiled the
same ten inputs twice, replacing only the private vendor CIL in the second
case. Removing 67 Binder grant occurrences that paired process domains with
service objects reduced the diagnostics from four assertion sites to two.
Both compiler invocations still failed with exit code 255 and produced no
binary. All 6,366 assertions, the related FD grants and valid process Binder
grants were retained. This is a separate prototype, not a modified factory
image or a later device source admission.

At that checkpoint, the remaining sites concerned the new `init_dev_config`
helper's APEX and media property writes. Its
[optional source capability](init-helper-capability.md)
has a tested patch that omits those two grants while preserving property reads,
socket access, existing init permissions and upstream defaults. The isolated
Git and host-M4 results are not an Android source build. The new definition had
not yet been installed, and absent literals in selected factory files do not
establish permanent helper nonuse or native-feature compatibility.

The subsequent [complete CIL comparison](helper-policy-projection.md) passed
for the projected inputs at `02:51:01 UTC` on August 28. Its unchanged baseline
still failed at the two helper assertions. Replacing only the platform CIL
with the exact two-SET projection produced a 1,515,046-byte policy binary;
the unfiltered analyzer exited successfully with no permissive domains.
The comparison retained all ten CIL inputs and all 6,366 assertions. The
Binder-derived vendor policy was identical in both cases. No image, source
admission, M4 build, init execution or native feature was validated by this
comparison.

A fresh source audit after that run again verified every one of the 1,179
project HEADs and remotes: 1,176 clean worktrees and exactly the three recorded
patched projects. No unexpected changes or local manifests appeared. This
audit did not rehash LFS payloads or cover ignored files and authored
directories outside Repo. The installed device admission was still v9 at that
August 28 checkpoint. The August 29 [native source integration](policy-source-integration.md)
subsequently installed v10c, admitted the helper capability through Android M4,
and reproduced the strict combined policy through a native vendor derivation.

The next local milestones before a complete device build are:

- Restore the missing OEM public service declarations, object roles and 202504
  mappings, and the framework classification of `offlinelog_file`. Review the
  permission effects and repeat the three failing factory context/structural
  checks recorded in the native integration evidence.
- Adopt the reviewed derived policy into images, preserving the original
  images, filesystem metadata, provenance and AVB requirements. The successful
  native combined-policy target is noninstallable and has not done that
  packaging.
- Assemble the Evolution framework VINTF inputs and every required partition,
  including `mi_ext`, and validate a complete engineering image set and boot
  chain. Individual component builds are not a complete target-files or OTA
  result.
- Resolve the Camera APK's signing, framework and native-library dependencies;
  the nine successfully built dependencies do not establish app compatibility.

The later [TWRP device tests](twrp-bringup.md) positively verified an unlocked
bootloader and booted `working76`, now the selected default recovery. That
recovery test used the installed stock companion boot, kernel and vendor stack;
it is not an Evolution boot or a complete ROM/OTA integration result. Future
phone tests still require selected-device/partition/rollback revalidation, a
return plan and specific user authorization. The [recovery plan](recovery-plan.md)
does not provide bootloader-corruption protection or verified data decryption.
See [current workspace status](workspace-status.md) for the consolidated gates.

The separate [SELinux contract](selinux-contract.md) captures the exact stock
policy inputs and reports seven neverallow failures using native tools from
pinned sources. Repeating the same ten unmodified CIL inputs with the actual
Soong-built x86-64 compiler returned the same seven neverallow failures.
No policy binary was produced, and no assertion was filtered. The later
[factory/user policy check](selinux-user-integration.md) reduced the combined
Evolution/vendor diagnostics to five assertion sites using actual `user`
outputs. It still failed and produced no policy binary. Building the compiler
tools or source policy alone does not establish factory-policy compatibility.

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
The installed v8 candidate now uses its factory vendor/ODM images through the
explicit transfer and admission above. Earlier build results retain their
Xiaomi.eu input identities; the current kernel bundle retains that provenance
as well. No package has been silently relabelled as authenticated OEM input.

No ROM boot, camera/Leica function, IMS, fingerprint, charging, encryption or
other hardware behavior has been established on Evolution X. Run `make test`
for tooling changes; build results and eventual authorized hardware tests are
separate evidence.

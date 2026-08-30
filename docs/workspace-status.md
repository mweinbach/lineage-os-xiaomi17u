# Current Nezha workspace status

The selected target is **Evolution X Android 16 QPR2 `bka` for Xiaomi 17 Ultra
(`nezha`, SM8850 / `canoe`)**, with **TWRP `working76` as the default recovery**.
The ROM remains a `framework-checks` product, not a complete or flashable ROM.
The recovery has a separate successful device test using the installed stock
companion boot, kernel and vendor stack; it does not establish that it works
with newly built Evolution components or that Evolution X boots. This page
consolidates recorded evidence through **August 30, 2026 UTC** (August 29 in
New York). It does not assert that a historical builder VM is still running.

The latest successful native policy build is **policy-v12f-export-1**, completed
at **2026-08-30 00:16:57 UTC**, with 35 Ninja actions after configuration. Its
25 ordinary goals installed the missing runtime CIL/mapping outputs and freshly
reran all 11 preserved compiler/guard/check outputs. Source inputs remained
unchanged and the read-only source sandbox was verified. The earlier stale
system_ext exports now match the compiler inputs.

Independent verification then **failed while hashing a build tool**, before
semantic analysis: the 19,226,918-byte `build_sepolicy` exceeded the 16 MiB
policy-reader bound. Export2 fixes that resource handling, but its launch is
held after host rehearsal identified three aggregate membership forms omitted
by the earlier model. The host proof finds exactly the unchanged platform
members plus four restored property types, with all 6,366 assertions and the
reviewed 105 allow, 7,190 dontaudit and 28,604 neverallow effect budgets intact.
The corrected export3 host rehearsal then passed the complete property delta,
public exports and recomputed OEM record. This remains host evidence only;
export3's native verification awaits an idle component build and remains the
leading policy gate. Export2 must not be launched with its known-failing model.
The prior
[v11b analysis](oem-policy-integration.md) remains the latest
completed native semantic comparison: all 6,366 assertions retained, the reviewed
permission delta and zero permissive domains in three binaries. The
[native integration record](native-rom-integration.md) keeps these evidence
levels separate from complete Treble labeling and image adoption.

The earlier **v12e** integration was installed into the existing guest source at
**22:10:41 UTC**. It adds the four OEM property sources, exact Camera runtime
inputs and their Soong patch, factory `mi_ext`, and the A/B recovery/custom-image
packaging patches. Its first native policy attempt failed at **22:19:27 UTC**
in Kati: `build/make/core/Makefile:4776` reads the undefined
`BOARD_MI_EXT_IMAGE_NO_FLASHALL`. No policy compiler or context-check action ran
in that attempt. The [native ROM integration record](native-rom-integration.md)
binds the successful installation and failed build separately. The correction
passed all **99 native Kati fixture cases**, including the reproduced original
failure, then was installed as **run-v12fa** at **23:22:28 UTC**. Its seven
changes include the corrected C source, while retaining the property policy
bundle and original images. The actual v12f retry now passes; the v12e failure
and earlier stage-only run-v12f remain preserved. The next work is independent
policy analysis and the current Camera runtime, mi_ext and working76 component
builds. **components-v12f-1** is running at this checkpoint; it is not a component
or image pass. Native DEX provider fixtures pass, but the current Camera
artifacts have not yet been verified.

The latest coordinator workspace suite passed **3,517 tests in 176.383 seconds
with zero skips**. This is offline tooling evidence, separate from Android
builds, host policy proofs and physical-device tests.

The immediate destination remains a reproducible, working Evolution baseline;
that baseline will support a maintainable platform fork without mixing future
framework features into device bring-up.

The observed phone reports `nezha` and CN hardware-country information. Its
physical sales region is not independently established. During the authorized
August 29 tests, the bootloader positively reported `unlocked: yes`,
`secure: yes`, slot `a`, and 100 MiB recovery slots, despite Android properties
reporting a locked state. Use the [bootloader observations](../research/twrp-boot-attempts.json)
for that checkpoint; older unresolved-bootloader statements are historical.
Recheck the selected device before a future authorized operation.

## Build baseline and provenance

| Input | Selected baseline and evidence |
| --- | --- |
| Platform | Evolution `bka`, manifest `cc4ebb8db9750afba6049825127304b09327f7c1`, release configuration `bp4a`; [source selection](../config/sources.json) |
| Project revisions | [Resolved 1,179-project snapshot](../research/source-snapshots/evolution-bka-20260827.xml), SHA256 `a7b9b5aec7f07a4d351771dbb834f4c4561c26564c7292930409f3f5968edeac`; [source verification](../research/source-sync.json) |
| Product | Authored `device/xiaomi/nezha`, `lineage_nezha-bp4a-user` and `userdebug`; ARM64, 4 KiB kernel pages, shipping API 36, board API `202504`; [generation contract](../device/xiaomi/nezha/README.md) |
| Kernel and modules | Exact stock-prebuilt Nezha bundle, with its original Xiaomi.eu provenance retained; [kernel wrapper](../kernel/xiaomi/nezha/README.md), [factory comparison](../research/factory-input-reuse.json) |
| Vendor/ODM | Reviewed factory-named `OS3.0.309.0.WPACNXM` archive, SHA256 `d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`; [factory intake and validation](factory-firmware-validation.md) |
| Recovery | `working76`, SHA256 `a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e`; [working-image contract](../research/twrp-working-defaults.json), [build and handling instructions](../recovery/twrp-working/README.md) |

The manifest commit alone does not lock every project: its upstream entries
include branches. The [reviewed source-lock workflow](source-lock.md) now uses
the exact resolved snapshot for fresh initialization and sync. It never
converts an existing selector or resets local changes. `make source-check`
audits existing HEADs, remotes and worktree state against that lock. The earlier
August 28 audit matched all 1,179 HEADs/remotes, with 1,176 clean projects and
three expected patched projects; see [build progress](../research/build-progress.json).
The [August 29 integration audit](../research/workspace-integration.json) again
matched all 1,179 HEADs/remotes, with 1,175 clean projects. The fourth patched
project is now `build/make`, for the verified prebuilt-recovery consumer. The
audit deliberately returns status `2` for those local changes; it does not
reset them or describe the checkout as pristine. A source lock does not
include the remaining build inputs below.

The [v11 preflight](../research/oem-policy-integration.json) rechecked all
1,179 revisions and origins at 19:37:51 UTC, with 1,175 clean projects and the
same four patched projects. The [v12e installed-source audit](../research/native-rom-integration.json)
again matches all 1,179 revisions and origins, now with **1,174 clean projects
and five reviewed patched projects**: `build/make`, `build/soong`, `system/core`,
`system/sepolicy` and `vendor/lineage`. The fifth project carries the strict
DEX uses-library provider patch. The v12fa installation reconfirmed those same
counts; its successful v12f build verified the corrected inputs unchanged.
Neither source verification nor a successful input
transaction is a component-build result.

Those local changes are part of the build inputs: the
[Evolution property patch](../patches/evolution/security-properties.json),
[SELinux enforcement patch](../patches/evolution/selinux-enforcement.json), and
[init property patch](../patches/evolution/init-boot-properties.json), together
with the [prebuilt-recovery consumer](../patches/evolution/prebuilt-recovery.json),
the [A/B recovery correction](recovery-packaging.md),
[direct-root custom-image integration](mi-ext-inputs.md),
[DEX provider correction](dex-import-uses-library.md),
the [scoped helper capability](policy-source-integration.md), authored
device/kernel sources and hash-bound private vendor bundles. The helper patch
is applied in the existing `system/sepolicy` project; the additional v12e
project is `build/soong`. The snapshot alone does not include these changes.
Factory archive origin and OEM
trust remain unauthenticated; passing internal AVB checks does not authenticate
the archive. Matching factory bytes do not relabel the older kernel bundle.

The verified local host route is Apple Container ARM64 plus Rosetta, with
`/work/evolution` on the persistent ext4 volume `evolution-nezha-work`.
Native Linux x86-64 is also supported by the workspace preflight. Recheck host,
disk, architecture, case sensitivity, source pins and volume ownership before
work; never attach the same volume to concurrent writer VMs. Preserve source,
output and cache. The [build-host guide](build-host.md) and
[container workflow](apple-container.md) distinguish component-build evidence
from a full build and require destination hash verification after transfers.

## What has actually passed

| Validation level | Result | Primary record |
| --- | --- | --- |
| Native source configuration and modules | User/userdebug product checks; ARM64 `libbase.so`; nine selected Camera dependencies, including four JARs with ODEX/VDEX; host VINTF and policy tools | [Build progress](../research/build-progress.json) |
| Native component builds and inspection | Boot, DTBO and both DLKM images in the recorded userdebug snapshot; factory-based user v8 init_boot, vendor_boot and DTBO preserve admitted DT/module/fstab inputs | [Boot/DLKM](../research/boot-dlkm-build.json), [factory boot](../research/factory-boot-build.json) |
| Native user v9 source policy | DSP membership integrated through Soong; both source-policy binaries have zero permissive domains | [DSP source build](../research/dsp-policy-build.json) |
| Strict policy prototype | Derived Binder correction plus two helper-permission removals compile as combined CIL with zero permissive domains; all 6,366 assertions retained | [Helper projection](../research/helper-policy-projection.json) |
| Native user v10 source and factory policy | The reviewed helper patch now runs through Android M4; a native genrule reproduces the Binder correction and the strict combined policy target builds successfully, including its user permissive-domain guard | [Source integration](../research/policy-source-integration.json) |
| Independent v10 analysis | Native combined binary matches the earlier prototype exactly; all 6,366 assertion statements remain, with only the intended 69 allow removals; three binaries have zero permissive domains | [Source integration](../research/policy-source-integration.json) |
| Native user v11b OEM policy | Authored system_ext declarations, object roles and generated API mappings; strict combined compilation, OEM ownership guard and all nine factory context/structural checks pass | [OEM policy integration](../research/oem-policy-integration.json) |
| Independent v11b analysis | All 6,366 assertions retained with reviewed concrete coverage; exactly five added lookup permissions and 47 removed vendor_init file permissions; zero permissive domains in three binaries | [OEM policy integration](../research/oem-policy-integration.json) |
| v12e source and private-input installation | Durable ten-operation transaction; pinned sources and exact installed inputs verified; original vendor/ODM, kernel and working76 bytes preserved | [Native ROM integration](../research/native-rom-integration.json) |
| v12fa correction installation | Seven committed exchanges, exact corrected source and receipt identities, same pinned project bases and preserved original image inputs | [Native ROM integration](../research/native-rom-integration.json) |
| Native v12f policy and exporter build | 73 Ninja actions after configuration; source/combined policy compilation, OEM guard, five context checks, two seapp checks and two structural checks pass; corrected C exporter compiled and linked | [Native ROM integration](../research/native-rom-integration.json) |
| Expanded native policy-output build | 25 ordinary goals, 35 Ninja actions; runtime CIL/mapping installation and all 11 preserved compiler/guard/check outputs freshly executed; independent analysis subsequently stopped on its tool-reader bound | [Native ROM integration](../research/native-rom-integration.json) |
| Native recovery-mode fixtures | Twelve isolated Kati guard cases pass, including required diagnostic failures; the first full v12e configuration separately failed on mi_ext before the later v12f correction passed | [Native ROM integration](../research/native-rom-integration.json) |
| Native custom-image correction fixtures | 99 expected outcomes: one reproduced historical failure, five corrected positive cases and 93 specific negative cases; full custom-image region parsed, with no image recipes or Ninja execution | [Native ROM integration](../research/native-rom-integration.json) |
| Native DEX provider fixtures | Five top-level tests and 11 subtests pass in the pinned Linux Soong test binary; no full Java-suite stamp, actual Camera artifact build or dex2oat execution | [Native DEX fixtures](../research/dex-import-native-fixtures.json) |
| Native EROFS inventory-tool build | Actual compile/link/install passes with source read-only; subsequent metadata qualification has unresolved failures and is not an image-adoption pass | [Native ROM integration](../research/native-rom-integration.json) |
| Native production file-size primitives | Four checks pass with zero skips, including finite 2 GiB/6 GiB limits and bounded log-overflow termination; production mkfs and image writing remain unqualified | [Native ROM integration](../research/native-rom-integration.json) |
| Original factory Camera packaging | Unchanged APK passes strict privileged/preprocessed and uses-library checks; no APK selection, permission-grant, effective-label or hardware result | [Factory Camera APK](../research/factory-camera-apk.json) |
| Static vendor VINTF | Vendor/ODM manifest load and merge, including captured active vendor APEX fragments | [VINTF validation](../research/vintf-validation.json) |
| Native VINTF build inputs | Selected framework XML, host tools and stock-kernel requirements built; the graph audit identifies the still-missing framework fragments and APEX artifacts rather than treating the partial inventory as complete compatibility | [VINTF build closure](../research/vintf-compatibility.json) |
| Recovery device test | `working76` installed to recovery_a; matching readback; visible UI and fast touch confirmed by the user; root ADB, logs and automatic defaults verified | [Working recovery](../research/twrp-working-defaults.json) |
| Recovery reproduction and ROM build target | Two fresh Mac rebuilds match working76 byte for byte; Linux public-key staging/verification and two actual `recoveryimage` target runs pass with unchanged output bytes | [Workspace integration](../research/workspace-integration.json) |

TWRP preserves the working `fix22ZJ-touchfix18` executables, libraries, drivers,
firmware and policy. Exactly two text files change: early recovery startup sets
SELinux permissive, and theme vibration defaults are zero. Its AVB footer is
signed with the local development key, flags zero, recovery rollback index 1
and location 1. This is a verified repack of a prebuilt runtime, not a proven
source compilation or OEM signature. The exception is recovery-only; normal
Android enforcement and denial checks remain required. Saved TWRP settings can
override theme defaults. No Magisk integration is included.

## Gates before a complete ROM

- **Policy:** v11b restored the two evidenced Xiaomi system_ext service
  declarations, object roles and generated API mappings, plus the framework
  offlinelog classification. Strict combined compilation, the ownership guard
  and all nine factory checks pass. Independent v11 comparison verifies the
  reviewed effective permission and assertion coverage changes; unfiltered
  analysis finds zero permissive domains in all three policy binaries.
  The [four-property source contract](../config/nezha-oem-properties.json) now
  passes the actual v12f policy build after the Kati correction. Its independent
  comparison against v11b, including the permission and dontaudit effects,
  first stopped because the runtime system_ext CIL and API mapping were stale.
  The expanded ordinary build installed those outputs, and the next analysis
  verified runtime/compiler equality before failing on its build-tool reader
  bound. Host rehearsal subsequently verified the exact three aggregate
  assignments and all reviewed effects, but the original verifier still rejects
  their source form. The export3 host rehearsal passes the complete property,
  public-export and OEM-record checks; export2 remains held. No final native
  semantic or three-binary permissive pass is claimed.
  The [framework-provider policy](../config/nezha-framework-provider-policy.json)
  remains a separately authored, host-verified follow-up. Neither is part of
  the successful v11b policy result.
  Full labeling needs the actual complete Evolution APK inventory; a missing
  artifact skip or API-202504 touch-only target is not a pass. The corrected
  policy is a non-installable validation output: retained vendor/ODM images
  still contain their original policy. A reviewed derivation must replace the
  vendor CIL and the ODM combined policy plus its three matching framework
  digests while preserving every other file and its metadata. The authored
  [EROFS inventory tool](../tools/erofs-metadata/README.md) has built natively.
  The corrected exporter now passes all six read-only stock checks, exporting
  3,910 vendor and 3,059 ODM entries, and all eight shared-xattr regression
  cases. Its latest synthetic qualification still records 25 passes and two
  writer/upstream-fsck failures. The earlier exporter failures remain preserved.
  The synthetic writer round-trip run records **11 passes and six failures**:
  repeated exact five-file derivations pass, but all six upstream empty-xattr
  checks fail. No actual factory image was derived. Complete factory
  metadata/content preservation and image adoption remain unverified.
  The [five-file policy-image preparation](policy-image-inputs.md) now binds
  complete stock manifests, exact replacements, repeated TAR construction and
  finite production limits. Its plan correctly remains blocked on seven
  missing reviewed policy record pins; no actual factory TAR, image, AVB or
  source/vendor adoption result follows from that preparation code.
  The native production-size primitive probe now passes four checks with zero
  skips, using finite 2 GiB/6 GiB file limits and bounded log-overflow handling.
  Its 59-file capture is verified; the first failed attempt remains preserved.
  It did not execute mkfs or qualify its production fallback, full spool I/O,
  disk headroom, partition fit or AVB.
- **Complete partition and OTA packaging:** retain `mi_ext`, both DLKM sets,
  the dedicated A/B recovery layout, factory encryption/AVB fstab declarations
  and measured Nezha budgets. The [mi_ext input and build path](mi-ext-inputs.md)
  and [A/B-only recovery packaging correction](recovery-packaging.md) are
  installed in v12e. Twelve isolated recovery-mode Kati cases pass; the full
  build failed on the uninitialized mi_ext variable above. The installed v12f
  correction uses the pinned read-only initialization macro, preserving the
  override checks and empty optional values. The actual policy build now gets
  through configuration successfully; it requested no images.
  The current Camera/mi_ext/recovery component build is running, with no completed
  result yet. Native component and packaging checks remain necessary. The A/B correction
  removes the inapplicable non-A/B two-step requirement only for A/B-only
  products; never fabricate a `recovery-two-step.img` from the kernel-free
  working76 image. Target-files, OTA, super-image and flash admission remain
  false. Selecting TWRP does not prove an OTA contains, preserves or restores
  it correctly on either slot. The new [target-files metadata projection](target-files-metadata.md)
  binds 205 original property, VINTF and APEX files to the retained images;
  host source admission and 43 isolated native Kati cases pass, but it is not
  installed in v12fa or a target-files pass.
  The new [combined source composition](target-files-source-composition.md)
  joins patches 0005–0011 through explicit ten-file identities, with fresh
  host-verified metadata/recovery/mi_ext admission. It is not installed in
  the guest; earlier isolated Kati results do not validate its full build.
  Later policy-bearing images require a new complete derivation proof and
  metadata bundle; changing expected image hashes alone is insufficient.
- **Signing and boot chain:** the inspected v8 generated boot components have
  AVB algorithm `NONE`, despite AVB being enabled in configuration. A complete
  signed chain, key availability, rollback compatibility and partition fit
  still need validation. The recovery bundle supplies its matching public key
  instead of using the generic engineering test key for that chain descriptor;
  this configuration is not proof of a completed, trusted vbmeta chain.
  The [new public-key image-set verifier](avb-image-set.md) has checked four
  prior components with real avbtool/OpenSSL; complete verification remains
  blocked by 13 absent roles. A leaf footer using `NONE` can be covered by its
  signed parent, but no complete signed parent chain has yet been established.
  The [host signing workflow](avb-signing.md) now supplies a tested recipe using
  the existing development key and 15 final input images. Its planning and
  unsigned descriptor-carrier checks have run; private-key signing and the
  complete 17-role output-chain verification have not. Keys remain on the Mac.
  The [pinned build-metadata capability](pinned-build-metadata.md) is authored
  and tested, but not installed or enabled. It cannot relabel earlier build
  dates or establish reproducible images without native and artifact checks.
  Working recovery's development signature does not sign the ROM or authorize
  relocking. Its kernel-free image depends on the intact device boot chain and
  is not protection against bootloader damage.
- **Framework/vendor compatibility:** the [native closure audit](vintf-compatibility.md)
  built selected XML and kernel inputs but still found ten required framework
  fragments and all 36 selected framework APEX artifacts absent at its
  checkpoint. Complete those inputs, materialize the actual APEX manifests,
  and run the full comparison with explicit kernel requirements. The pinned
  compatibility CLI does not enforce every framework-provider expectation in
  the factory matrix. The authored [Sigma and QCC provider bundle](framework-providers.md)
  therefore also needs strict native ELF, policy, linker and service checks;
  [v13 source admission](framework-provider-source-admission.md) reproduces a
  host candidate with its 31 payloads, 27 installable modules and private policy.
  It is not installed in v12fa or validated by the v12f policy build.
  A captured current Soong configuration selects maximum ELF page size 16,384
  with the prebuilt check enabled; static inspection finds 22 of 26 provider
  ELFs have 4 KiB load alignment. Resolution remains under review, with no
  configuration decision or native checker pass inferred from this snapshot.
  The [original-ODM shipping-API patch](vintf-shipping-api.md) passes source-bound
  host probes without fabricating vendor properties; it is authored but not
  installed in v12fa and is not a complete native compatibility result.
- **Runtime and stock features:** no Evolution boot or native feature is
  verified. Module stage loading/signature behavior, storage, telephony, audio,
  thermals, sensors, camera/Leica and accessories require separate tests. The
  Camera APK itself is not packaged; strict signing and uses-library integration
  remain open despite its nine dependencies building. The new
  [exact Camera runtime-library bundle](camera-runtime-inputs.md) and reviewed
  Soong provider patch are installed in v12e. The current names and strict
  class-loader integration still need their native rebuild now that Kati passes;
  five native provider fixture tests and 11 subtests now pass, but they do not
  execute the generated Camera build rules or dex2oat. The older dependency-build
  result does not validate this new input set.
  The [earlier APK admission review](camera-apk-inputs.md) verifies the unchanged
  signature, ZIP contents and exact library names, while reproducing both
  packaging failures: target SDK 35 needs preprocessed handling, and privileged
  preprocessed handling rejects the compressed DEX entries. The APK remains
  unselected; no signing or privilege exception was introduced.
  The distinct [original factory Camera APK](factory-camera-apk.md) passes the
  strict privileged/preprocessed check unchanged, resolving that input's DEX
  compression blocker. Its ten always-privileged requests, rising to eleven
  across feature branches, still need actual grant and effective
  SELinux-label validation. Neither APK is selected or hardware-tested.
- **Recovery completeness:** encrypted `/data`, backup/restore coverage,
  additional reboot/Android round trips, A/B and OTA behavior, ADB host
  authentication and restoring recovery SELinux enforcement remain unverified.

Keep `SELINUX_IGNORE_NEVERALLOWS`, relaxed uses-library validation, VINTF
bypasses, AVB bypass flags and writable-source exceptions out of the ROM
workflow. A permissive recovery or successful component build does not waive
these gates. [Integration sequencing](nezha-integration.md) records the next
source work; [recovery handling](recovery-plan.md) records recovery boundaries.

## Current entry points and historical evidence

| Use now | Keep for diagnosis; do not treat as the current default |
| --- | --- |
| This status page and [Nezha integration](nezha-integration.md) | Detailed dated checkpoints in `docs/build-progress.md` and the individual component-build records |
| [Working TWRP instructions](../recovery/twrp-working/README.md) and [current recovery guide](twrp-bringup.md) | [Recovery history](twrp-bringup-history.md): earlier minimal builds, RAM-boot attempts and `provided75` before persistent defaults |
| [OEM policy integration](oem-policy-integration.md) and its [current record](../research/oem-policy-integration.json) | [v10 source-policy integration](policy-source-integration.md), v7/v8/v9 builds and copied-CIL prototypes remain dated evidence; their original results are preserved |
| [Native ROM integration](native-rom-integration.md) and its [current record](../research/native-rom-integration.json) | Preserved v12 staging history and first Kati failure; the successful policy build and host provider, metadata and signing inputs are not completed native ROM builds |
| Current factory vendor/ODM input receipts | Modified Xiaomi.eu package, earlier candidates, outputs and failed AVB results with their original provenance |

Run `make test` before completing workspace changes. Generate into new ignored
candidate directories, validate configuration admission, preserve separate
user/userdebug output directories, and bind each build to its source snapshot,
patches, input receipts, tool hashes and artifact hashes. Offline tests neither
compile Android nor test a phone. Cleanup and local builds do not authorize
device changes; any future flash, reboot or restore needs its own explicit
user instruction and selected-device preflight.

The v10 native result, independent analysis and three failed context checks
remain in their original record. The first v11 build resolved those checks but
failed its new ownership guard because Android retains inherited platform
members in generated attribute sets. The corrected guard requires that exact
platform membership plus only the reviewed additions; it does not allow
arbitrary widening. The v11b retry archived the ten previous validation outputs
and reran the combined compiler and all nine checks, completing 30 main Ninja
actions after one bootstrap step (31 cumulative progress entries), with source
read-only and user output writable. No check was waived. The
independent analysis then bound the ten real compiler inputs, M4 sources,
public exports, mappings, inherited semantics and executed native checks to
the successful phase. Its three permissive analyses ran with inputs read-only.
The original factory images, working76, four existing upstream patch projects and
complete-ROM gates were preserved. No new source sync, image adoption or device
operation occurred in this policy milestone.

# Current Nezha workspace status

The selected target is **Evolution X Android 16 QPR2 `bka` for Xiaomi 17 Ultra
(`nezha`, SM8850 / `canoe`)**, with **TWRP `working76` as the default recovery**.
The ROM remains a `framework-checks` product, not a complete or flashable ROM.
The recovery has a separate successful device test using the installed stock
companion boot, kernel and vendor stack; it does not establish that it works
with newly built Evolution components or that Evolution X boots. This page
consolidates recorded evidence through **August 30, 2026** in UTC and New York.
Earlier UTC milestones before 04:00 on August 30 occurred on August 29 in
New York. This page does not assert that a historical builder VM is still running.

The latest successful native policy build is **policy-only-v13h-1**, completed
at **2026-08-30 05:40:07 UTC**, with 31 goals and 273 Ninja actions after
configuration. Source inputs remained unchanged, the native sandbox was verified,
and all eleven preserved policy outputs and eleven protected runtime outputs
were verified. Provider runtime/ELF actions and images were not requested.
The subsequent native analysis now verifies the provider policy's exact
assertions, effects and source provenance.

The latest native analysis, **analysis-v13h-policy-only-v1**, passed at
**13:12:51 UTC**. It retains all **6,366 original assertions plus four provider
assertions**, verifies nine fresh context/structural checks, and finds **zero
permissive domains in three binaries**. Against v12f/export4, the reviewed
ordinary delta is exactly **12,005 allow**, **1,883 dontaudit** and **3,291,674
neverallow coverage effects added**, with none removed. The complete review also
binds extended-permission changes. Two new dontaudit statements are recorded;
denial logging is not claimed unchanged. Helper property-set permissions remain
zero, normal Android stays enforcing, and all guarded inputs remain unchanged.
The independent capture review has no findings: all 208 captured files and the
complete reviewed effect inventory match, with only four validated generated
assertion-name roles normalized for comparison. This does not modify policy.

This establishes the current v13ha policy baseline. The earlier v12f/export4
analysis and [v11b analysis](oem-policy-integration.md) remain separate dated
evidence. The earlier v13f provider inputs were
installed, but their first 31-goal policy build failed during Soong bootstrap
at **02:36:44 UTC**. `nezha_framework_libmiracastsystem`'s emitted static variant
depends on Audio AIDL V2 directly and V4 through `libaudiofoundation`. No new
policy compiled or context check passed in that failed attempt. The later
v13ha transaction installed the reviewed correction at **04:52:42 UTC** through
three exchanges and a verified nine-event journal; its native policy build now
passes. The first missing-ancestor snapshot failure remains preserved.
Three native Soong fixtures reproduce the expected graph outcomes and show
that selecting only the shared variant does not resolve the mixed V2/V4
dependency. The first compile-only audio-layout probe failed in its AST parser;
the corrected v2 probe passes two cases and four compilations, matching all
15 measured factory layout constraints. Static review also verifies the two
selected descriptor-vtable CFI checks without requiring CFI suppression. Neither
result admits the complete caller ABI or proves runtime routing. Commit
`364ab89` includes the v7 Miracast correction and verified host producer/consumer
bindings now installed as v13ha. The analysis binds the actual provider-input
genrule: 42 original inputs and 31 payloads, with 30 unchanged and one exact
one-byte dependency derivation. This is input-production evidence; provider
ELF compatibility, runtime installation and service behavior remain unverified.
Retained vendor/ODM images still contain
their original policy. Provider compatibility, complete Treble APK labeling,
current-provider policy-image integration and the remaining ROM build gates are
still open.
Earlier tool-bound, aggregate-model
and M4-guard failures remain preserved in the
[native integration record](native-rom-integration.md); they are not relabeled
as passes.

The matching **policy-sidecar-v13h-native-v1** derivation passes six native
checks and fourteen commands with zero skips. It derives three digest files
from the sealed current-policy inputs; the system_ext digest changes while
platform and product remain unchanged. These are validation outputs; installed
digest files, Android genrule execution and image adoption remain separate.
The read-only VINTF graph capture
now binds 21 XML inputs, including both provider fragments, and 36 APEX inputs.
Its `check-vintf-all` alias still omits full compatibility. The three-goal
**vintf-v13h-1** build timed out at **16:32:28 UTC** after its configured
10,800 seconds, with logged progress at 58,702/61,802. It returned exit 1;
no forced kill or remaining build process was reported. The failed result,
logs and nine available XML outputs are preserved. A fresh capture at
**16:42:27 UTC** verifies the same source history, graph and strict settings.
The incremental **vintf-v13h-2** retry finished at **16:58:47 UTC**, without a
timeout, but failed the frozen level-5 `vintffm` check because
`android.hidl.allocator` is mandatory and not declared in the manifest. All
57 selected XML/APEX artifacts are present; presence is not compatibility.
The next blocker is actual allocator compilation and producer/context checks,
followed by the unchanged strict VINTF checks. Commit `1647192` adds the
[host-verified allocator capability](framework-allocator.md), selecting the
existing upstream service while retaining its init, SELinux and `max-level="8"`
manifest behavior. The **v13i** transaction installed that device selection at
**18:48:34 UTC**, preserving 24 guarded inputs and 112 prior outputs. All 1,179
base revisions and origins still match. The 37-goal **allocator-v13i-1**
service/policy build is running, with no result verified yet; installed inputs
do not resolve the VINTF failure by themselves.
The separate packet for a full 39-APEX comparison is staged with all 221 files
verified. Staging does not execute native compatibility checks or materialize
the required generated APEX inputs.

Ninja query captures were held pending qualification of the pinned query
modes under read-only mounts. The second footer capture accepted the valid empty
Soong shard, then failed its first jailed query while trying to open a build log
on a read-only filesystem. Earlier unconfined provider queries and the memfd
fixture therefore do not prove absence of source-root or OUT log writes. Small
source-root `.ninja_log` and `.ninja_deps` files are recorded and preserved in
place; their writer is not established. No original project payload change is
known. This caveat does not invalidate the VINTF builds' separately verified
source guards or relax their compatibility checks.
The actual query qualification v1 remains failed: four checks pass and two fail,
with zero skips. Its positive `-n` known answers pass, but the help-stream and
corrupt-dependency negative-fixture expectations fail. The corrected **query
qualification v2 passes all six checks**, with eleven commands and zero skips,
including the expected read-only failure controls. Independent review releases
only the exact reviewed footer-capture recipe; other graph-capture recipes are
not automatically admitted, and earlier no-write claims remain unproven.

The actual **footer-tools-native-v3** capture passes with 28 commands, two query
depths and zero skips. Independent review verifies all 81 captured files, eight
observed Ninja/loader jails, unchanged graph identities and all four tracked log
files. This captures tool identities, producer descriptions and loader mappings;
it does not execute the `avbtool`/`fec` entrypoints or prove a fresh producer build.
The following v4 host admission failed because its runtime-closure comparison
omitted the separately recorded interpreter. The narrow v5 correction passes
host admission. **policy-footer-qualify-v1** then passes four native checks
across seven commands, including payload/tree corruption rejection and a
separate regenerated-FEC comparison; zero skips. Independent review is clear.

The current **policy-images-v13h-v1** native reconstruction passes **nine checks
and 38 commands with zero skips**, including 18 fsck checks. Both independent
TAR/image/export sets are byte-identical, with exactly one vendor file and four
ODM files changed; every other content digest and semantic metadata field is
preserved under the explicit physical-layout exclusions. Independent review
of the 97-file capture has no findings. The raw vendor image matches export4;
the ODM image carries the sealed v13h policy and matching digests. These outputs
remain unadopted, with original images and staging preserved.

The subsequent **policy-footer-produce-v1** run completes at **18:49:27 UTC**
with six native checks, sixteen commands and zero skips. Two independent
vendor/ODM pairs are byte-identical, preserve the raw EROFS prefixes, and pass
hashtree, independently regenerated FEC and exact factory-package size checks.
These are keyless `NONE` leaf footers; physical partition fit, a signed parent
chain, current-source compatibility, adoption and boot remain unverified.
Independent review of all 110 captured files is clear. The host review does not
reopen the large native image or FEC outputs.

The latest Camera source capture still fails before any Ninja query: its graph
reader rejects the shared bootstrap `builddir` variable. A bounded diagnostic
identifies the exact expression. The narrow shared helper is now frozen after
72 offline checks; Camera/provider recipe admission and acceptance of the
current graph remain pending. No Camera APK selection, build or runtime result
follows.

The earlier **policy-images-export4-v1** native reconstruction passes
**nine checks and 38 commands with zero skips**. Both independent TAR/image/export
sets match, with exactly one vendor policy file and four ODM files changed;
all other contents and semantic metadata are preserved. Independent review
reparses all six complete manifests and verifies the 97-file host capture and
77 staged packet files, with no findings. This qualifies the raw five-file
derivation for sealed v12/export4
inputs; it does not adopt those images, validate current source, regenerate AVB/FEC,
establish partition fit or prove a kernel mount or boot.

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
and earlier stage-only run-v12f remain preserved. **components-v12f-1 passed at
02:03:33 UTC**, after 102 minutes 20 seconds, with unchanged source inputs and
verified sandboxing. All eleven installed outputs were captured and inspected:
the nine Camera runtime payloads match their inputs, and recovery/mi_ext retain
their exact expected bytes. The bounded producer review verifies four fresh
DEX invocations and matching installed ODEX/VDEX outputs, the fresh JNI checks
including 16 KiB alignment, a fresh guarded working76 copy, and fresh mi_ext
NONE-footer/hashtree verification. The coordinator reproduced the review receipt
byte for byte. Native checkers were not independently replayed, and complete
checker-input recapture and runtime API validation remain separate. No Camera
APK was built, and this is not a complete ROM, signed-chain or boot result.

The latest coordinator full workspace suite passed **3,711 tests in 158.487
seconds with zero failures, errors or skips**, covering the optional
[mi_ext care-map source path](mi-ext-care-map.md), committed as `8144704`.
That capability is inactive: authentic ODM imports and the final Evolution
SYSTEM property input still require qualification. The preceding allocator
suite passed 3,665 in 156.924 seconds. The previous suite passed 3,651 in
156.391 seconds, executed by the
target-files metadata agent;
the coordinator independently verified its complete log. The separate previous
coordinator run passed 3,651 in 160.426 seconds after the raw-image milestone.
Those earlier runs used unchanged public code from the profile run, which passed 3,651
tests in 158.950 seconds at `78376c7`. The preceding v13ha integration
run passed 3,634 in 152.111 seconds. The previous v7 run passed 3,634 in
156.509 seconds, and the previous profile
checkpoint passed 3,591 tests in
152.682 seconds. The earlier coordinator component
checkpoint passed 3,558 tests in 163.269 seconds; the separate page-size agent run
passed 3,558 in 153.985 seconds. These are offline tooling results, separate from
Android builds, host policy proofs and physical-device tests. This checkpoint records
code and documentation through `8144704`. The active guest inputs are v13i;
`analysis-v13h-policy-only-v1` remains the latest verified policy baseline.

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
The v13ha snapshot still matches all 1,179 revisions and origins, with **1,173
clean projects and six reviewed modified projects**. The additional project is
`external/mdnsresponder`, carrying the scoped provider visibility change.
The successful v13h build verifies its 182 selected source files unchanged.
The v13i preinstallation audit reconfirms all 1,179 revisions/origins and the
same six modified projects; its device selection changes no project source.
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
| v13f provider input installation | Four committed exchanges verified; original vendor/ODM, Camera runtime, mi_ext and working76 preserved; provider policy build and independent verification remain separate | [Native ROM integration](../research/native-rom-integration.json) |
| v13ha correction and native policy verification | Three exchanges commit; 31 native goals pass; analysis retains 6,370 assertions, exact reviewed effects and three zero-permissive binaries; provider runtime/ELF and image adoption remain open | [Native ROM integration](../research/native-rom-integration.json) |
| v13i allocator input installation | One device-tree exchange commits, preserving 24 guarded inputs and 112 prior outputs; service compilation and VINTF remain pending | [Native ROM integration](../research/native-rom-integration.json) |
| Native v12f policy and exporter build | 73 Ninja actions after configuration; source/combined policy compilation, OEM guard, five context checks, two seapp checks and two structural checks pass; corrected C exporter compiled and linked | [Native ROM integration](../research/native-rom-integration.json) |
| Expanded native policy-output build | 25 ordinary goals, 35 Ninja actions; runtime CIL/mapping installation and all 11 preserved compiler/guard/check outputs freshly executed; independent analysis subsequently stopped on its tool-reader bound | [Native ROM integration](../research/native-rom-integration.json) |
| Preserved independent v12f policy analysis | Export4 verifies source/M4/mapping and fresh-check provenance, all 6,366 assertions and exact reviewed effects; three unfiltered zero-permissive binaries; provider policy unselected | [Native ROM integration](../research/native-rom-integration.json) |
| Native v13h policy sidecars | Six checks and fourteen commands pass, zero skips; three current-policy digest files derive from sealed inputs, without Android genrule execution or image adoption | [Native ROM integration](../research/native-rom-integration.json) |
| Current Camera/mi_ext/recovery build | Eleven goals complete; captured producers verify four fresh DEX invocations, matching ODEX/VDEX, strict JNI checks, working76 copy and mi_ext integrity; APK/runtime and signed-chain gates remain open | [Native ROM integration](../research/native-rom-integration.json) |
| Native recovery-mode fixtures | Twelve isolated Kati guard cases pass, including required diagnostic failures; the first full v12e configuration separately failed on mi_ext before the later v12f correction passed | [Native ROM integration](../research/native-rom-integration.json) |
| Native custom-image correction fixtures | 99 expected outcomes: one reproduced historical failure, five corrected positive cases and 93 specific negative cases; full custom-image region parsed, with no image recipes or Ninja execution | [Native ROM integration](../research/native-rom-integration.json) |
| Native DEX provider fixtures | Five top-level tests and 11 subtests pass in the pinned Linux Soong test binary; no full Java-suite stamp, actual Camera artifact build or dex2oat execution | [Native DEX fixtures](../research/dex-import-native-fixtures.json) |
| Native EROFS inventory-tool build | Actual compile/link/install passes with source read-only; subsequent metadata qualification has unresolved failures and is not an image-adoption pass | [Native ROM integration](../research/native-rom-integration.json) |
| Native production file-size primitives | Four checks pass with zero skips, including finite 2 GiB/6 GiB limits and bounded log-overflow termination; this probe did not execute mkfs | [Native ROM integration](../research/native-rom-integration.json) |
| Native unchanged-vendor round trip | Eight checks pass, zero skips; two identical raw images preserve all 3,910 entries and 3,389 regular-file contents under the exact 2 GiB vendor recipe; not policy/image adoption | [Native ROM integration](../research/native-rom-integration.json) |
| Native unchanged-ODM round trip | Eight checks pass, zero skips; two identical raw images preserve all 3,059 entries and 2,925 regular-file contents under the exact 6 GiB ODM recipe; no policy replacements, AVB or boot result | [Native ROM integration](../research/native-rom-integration.json) |
| Native v12/export4 policy-image reconstruction | Nine checks and 38 commands pass, zero skips; two identical complete TAR/image/export sets preserve all but the exact five policy payloads; raw derivation only, no adoption or AVB | [Native ROM integration](../research/native-rom-integration.json) |
| Native v13h policy-image reconstruction | Nine checks and 38 commands pass, zero skips; independent review confirms both exact five-file derivations and all other semantic metadata; unsigned raw outputs remain unadopted | [Native ROM integration](../research/native-rom-integration.json) |
| Native v13h keyless leaf footers | Six checks and sixteen commands pass, zero skips; identical repeated vendor/ODM leaves preserve raw prefixes and pass hashtree, FEC and exact package budgets; no physical fit, signed parent chain or adoption | [Native ROM integration](../research/native-rom-integration.json) |
| Native pinned-date fixtures | All 33 expected outcomes verified: nine positive/legacy cases and 24 diagnostic-specific negatives, zero skips; live product unchanged | [Native date checks](../research/pinned-build-metadata-native.json) |
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

- **Policy and policy-image integration:** v11b restored the two evidenced Xiaomi system_ext service
  declarations, object roles and generated API mappings, plus the framework
  offlinelog classification. Strict combined compilation, the ownership guard
  and all nine factory checks pass. Independent v11 comparison verifies the
  reviewed effective permission and assertion coverage changes; unfiltered
  analysis finds zero permissive domains in all three policy binaries.
  The [four-property source contract](../config/nezha-oem-properties.json) now
  passes the actual v12f policy build after the Kati correction. Its independent
  comparison against v11b now passes in export4, including exact permission,
  dontaudit and neverallow coverage, all 6,366 assertions, M4/API producer
  provenance, nine fresh checks and three zero-permissive binaries. Earlier
  stale-export and analysis-adapter failures remain preserved; export4's exact
  newline-interleaved source check does not change policy or waive checks.
  The [framework-provider policy](../config/nezha-framework-provider-policy.json)
  now passes the actual v13h source build and native analysis against export4:
  6,370 assertions, nine fresh checks, three zero-permissive binaries and the
  complete reviewed effect delta. Neither later addition was part of v11b.
  Commit `78376c7` adds the explicit matching `v13h-policy-only` image-input
  profile, eligible for evidence validation. Earlier profiles and the blocked
  default are unchanged. The separate `policy-images-v13h-v1` raw reconstruction
  and independent review now pass; image adoption remains unverified.
  Full labeling needs the actual complete Evolution APK inventory; a missing
  artifact skip or API-202504 touch-only target is not a pass. The corrected
  policy is a non-installable validation output: retained vendor/ODM images
  still contain their original policy. The qualified raw derivation replaces
  the vendor CIL and the ODM combined policy plus its three matching framework
  digests while preserving every other file and semantic metadata field under
  explicit physical-layout exclusions. Its adoption is a separate gate. The authored
  [EROFS inventory tool](../tools/erofs-metadata/README.md) has built natively.
  The corrected exporter now passes all six read-only stock checks, exporting
  3,910 vendor and 3,059 ODM entries, and all eight shared-xattr regression
  cases. Its latest synthetic qualification still records 25 passes and two
  writer/upstream-fsck failures. The earlier exporter failures remain preserved.
  The synthetic writer round-trip run records **11 passes and six failures**:
  repeated exact five-file derivations pass, but all six upstream empty-xattr
  checks fail. That synthetic run derived no factory image. The later vendor/ODM
  results below are separate; policy-image adoption remains open.
  The [five-file policy-image preparation](policy-image-inputs.md) now binds
  complete stock manifests, exact replacements, repeated TAR construction and
  finite production limits. Commit `35324b4` adds an explicit `v12-export4`
  profile with the reviewed native records; the historical default retains its
  original seven-pin blocker. The coordinator's complete unmocked admission
  replay passes, without running TAR preparation, opening images or executing
  native tools. This profile does not admit the active v13ha provider policy.
  The separate native sidecar v2 run now passes six checks and fourteen commands
  with zero skips, deriving all three framework digest files from the sealed
  v12f/export4 inputs and pinned recipe. These are validation derivatives, not
  captured installed outputs or executed Android genrules. No image, policy or
  source adoption follows; the first loader-parser failure remains preserved.
  The native production-size primitive probe now passes four checks with zero
  skips, using finite 2 GiB/6 GiB file limits and bounded log-overflow handling.
  Its 59-file capture is verified; the first failed attempt remains preserved.
  It did not execute mkfs or qualify its production fallback, full spool I/O,
  disk headroom, partition fit or AVB.
  The subsequent full-vendor no-change attempt remains failed: two checks and
  original fsck extraction completed, then the harness rejected that operation's
  completion diagnostic before TAR construction or mkfs image creation. The
  corrected v2 then passed all eight native checks with zero skips. Its two
  941,744,128-byte raw images are identical to each other and preserve all
  original content and nonphysical metadata, including UUID/features. This
  qualifies the unchanged-vendor 2 GiB recipe. The subsequent original-ODM run
  also passes eight native checks with zero skips under its 6 GiB limit. Its two
  4,678,053,888-byte raw images match each other and preserve all 3,059 paths,
  2,925 regular-file contents and nonphysical metadata. Both runs make zero
  policy replacements and do not themselves qualify changed policy inputs.
  The later **policy-images-export4-v1** run now qualifies the exact five-file
  raw derivation, with nine checks, 38 commands and zero skips. Its repeated
  vendor and ODM images are respectively 941,744,128 and 4,678,025,216 bytes;
  only the reviewed policy payloads change. Complete exports and diagnostics
  are captured; the large TARs/images remain guest-only and were not reopened
  by the host collector. The later v13h footer run separately verifies hashtree,
  FEC and exact package budgets; signing, physical partition fit, source
  adoption, retained-kernel mounting and boot remain unverified.
- **Complete partition and OTA packaging:** retain `mi_ext`, both DLKM sets,
  the dedicated A/B recovery layout, factory encryption/AVB fstab declarations
  and measured Nezha budgets. The [mi_ext input and build path](mi-ext-inputs.md)
  and [A/B-only recovery packaging correction](recovery-packaging.md) are
  installed in v12e. Twelve isolated recovery-mode Kati cases pass; the full
  build failed on the uninitialized mi_ext variable above. The installed v12f
  correction uses the pinned read-only initialization macro, preserving the
  override checks and empty optional values. The actual policy build now gets
  through configuration successfully; it requested no images.
  The current Camera/mi_ext/recovery component build now passes, with inspected
  unchanged recovery/mi_ext payloads. Its bounded producer review confirms the
  fresh guarded recovery copy and mi_ext NONE-footer/hashtree check; complete
  packaging and signed-chain evidence remain necessary. The A/B correction
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
  The [optional mi_ext care-map path](mi-ext-care-map.md) is committed but
  inactive. Qualify the authentic ODM import closure and final Evolution
  SYSTEM marker before composing it into the ordinary packaging path.
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
  The [pinned build-metadata capability](pinned-build-metadata.md) now verifies
  33 expected isolated native Kati outcomes, but is not installed or enabled.
  The first diagnostic-harness failure remains preserved. It cannot relabel earlier build
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
  The v13f provider packet was staged at **02:18:20 UTC**, then installed in four
  verified exchanges at **02:34:51 UTC**. Earlier inputs and outputs were
  preserved. The 31-goal `policy-only-v13f-1` phase failed in Soong bootstrap on
  the direct Audio AIDL V2 versus transitive V4 conflict above, before any new
  policy compilation. The strict 16 KiB settings remain enabled, but no provider
  ELF actions ran. The later v13ha correction is installed and its 31-goal
  native policy build and independent analysis now pass. This closes the policy
  verification slice, not provider ELF, runtime or complete VINTF compatibility.
  The new read-only VINTF graph capture binds 21 XML and 36 APEX inputs, but
  confirms the all-target alias lacks the full compatibility action. Its
  first three-goal build timed out and remains failed. The incremental
  `vintf-v13h-2` retry completed without timeout but failed the mandatory
  `android.hidl.allocator` declaration at frozen level 5. All 57 selected XML/APEX
  artifacts are present; service integration and a successful unchanged check
  remain required. The separate full-check packet is staged, with 221
  files verified and 39 APEX packages required; native materialization and
  compatibility checks remain unexecuted. Its 44 coordinator offline tests
  pass with zero skips, separately from the native build.
  A captured current Soong configuration selects maximum ELF page size 16,384
  with the prebuilt check enabled; static inspection finds 22 of 26 provider
  ELFs have 4 KiB load alignment. The [optional 4 KiB experiment](nezha-page-size.md)
  in `84d63c2` and its host v13g candidate are **on hold and unadopted**.
  Lowering the threshold does not resolve the 16 KiB/VSR requirement and must
  not suppress the failures. Both the failed v13f build and successful v13h
  policy-only build retain `16384` and the enabled check, without provider ELF actions;
  the 4 KiB path is not approved as the next integration.
  The [original-ODM shipping-API patch](vintf-shipping-api.md) passes source-bound
  host probes without fabricating vendor properties; it is authored but not
  installed by the v13f provider transaction and is not a complete native compatibility result.
- **Runtime and stock features:** no Evolution boot or native feature is
  verified. Module stage loading/signature behavior, storage, telephony, audio,
  thermals, sensors, camera/Leica and accessories require separate tests. The
  Camera APK itself is not packaged; strict signing and uses-library integration
  remain open despite its nine dependencies building. The new
  [exact Camera runtime-library bundle](camera-runtime-inputs.md) and reviewed
  Soong provider patch are installed in v12e. The current names and strict
  class-loader integration now has a successful component build and byte-matched
  runtime outputs. The producer review binds four fresh DEX invocations to their
  raw Soong inputs and matching installed ODEX/VDEX, and verifies the fresh JNI
  action with SONAME, dependency, symbol and 16 KiB checks enabled. The absent
  `dexpreopt.config` targets are not counted as passes; the observed library-import
  configuration does not verify the Camera APK's uses-library contract. Runtime
  APIs and linker access remain unverified. The five native provider fixtures and 11 subtests remain
  separate evidence, and none establishes the Camera APK or hardware behavior.
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
  The [factory permission-grant review](../research/factory-camera-permission-grants.json)
  traces three pure-signature requests through captured evaluator and service
  source. Allowlisting or a debuggable build cannot replace signing eligibility;
  a denied grant is distinguished from an installation error. Effective signing,
  flags, permission grants and Camera call behavior remain unverified. The
  coordinator's 30 focused tooling tests pass; no grant or permission definition
  was changed and no APK was installed.
  The [build-only Camera packet](camera-apk-build-admission.md), committed as
  `117261c`, reproduces on the host and its content-verifying producer passes.
  Its separate namespace is not installed in the guest or exported to Make;
  product selection, permissions, MAC labeling and real APK outputs remain open.
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

# Workspace documentation

Start with [current status](workspace-status.md), the [TWRP guide](twrp-bringup.md),
and the [source lock](source-lock.md). They distinguish current decisions from
older experiments. A passed host test, component build, policy prototype or
recovery boot is not a complete Evolution X ROM test.

The table below preserves the detailed research index. Many entries describe
dated checkpoints; their original evidence and limitations remain intact.
The [TWRP history](twrp-bringup-history.md) contains the earlier recovery trials.

| Current workflow | Purpose |
| --- | --- |
| [Workspace status](workspace-status.md) | Verified results, selected inputs and remaining ROM gates |
| [Package6 discovery and failed-archive retirement](build-progress.md#package6-discovery-admission-and-failed-archive-retirement--2026-09-03) | Shared discovery-v3 and independent admission pass for preserved sources and observed query edges; one obsolete failed ZIP is retired, while producer/runtime, native EROFS, FEC and final ROM gates remain open |
| [Package6 archive and reader corrections](build-progress.md#package6-archive-and-reader-corrections--2026-09-03) | Reconciliation and published inventory pass with all 9,154 members read back, 17-role image joins and canonical aliases; ZIP64 and opt-in compact-EOF fixes pass 4,512 offline tests, while native reader qualification and final ROM gates remain pending |
| [Package6 public preparation and signing](build-progress.md#package6-public-avb-preparation-and-signing--2026-09-03) | Public preparation and host signing pass for the 17-role AVB set, with two-pass derivatives, 14 unchanged leaves and working76 preserved; reconciliation is not yet admitted, and FEC/VINTF/fit/OTA/boot remain separate gates |
| [Package6 inputs and P5 host retirement](build-progress.md#package6-input-materialization-and-p5-host-retirement--2026-09-03) | Fifteen inputs materialized, old P5 host ZIP retired, builder restored and VINTF capture read back; semantic admission, public preparation, signing and compatibility remain pending, and 20 native leaves are only metadata-probed |
| [Verified storage cleanup](storage-cleanup.md) | 51 exact obsolete files removed and approved free-block trim completed; original builder restored, 273.56 GiB host free at the dated checkpoint, and bounded preservation checks kept separate from build readiness |
| [Native ROM integration](native-rom-integration.md) | Current source, scoped policy3/VINTF/metadata verification and remaining image-delivery, packaging and boot gates; earlier failures remain preserved |
| [Source lock](source-lock.md) | Exact platform revisions for fresh setup and read-only existing-source audits |
| [Pinned build metadata](pinned-build-metadata.md) | Explicit UTC epoch capability and retained isolated Kati qualification; active product and metadata-file results are recorded in current status |
| [Working recovery build](../recovery/twrp-working/README.md) | Fixed inputs, deterministic image assembly, local signing and verification |
| [Recovery logs](recovery-logs.md) | Bounded collection from an explicitly selected recovery device |
| [OEM policy integration](oem-policy-integration.md) | Current three-type source integration, native ownership/context checks, independent semantic verification and remaining image gates |
| [Explicit Evolution policy base](evolution-policy-base.md) | Policy3 source build, scoped semantic/M4 review, twelve unfiltered binary checks and public-name freeze pass; image delivery, packaging and final APK/Treble gates remain |
| [Camera property write capability](camera-property-vendor-init-write.md) | Installed correction clears the strict compile failure; scoped policy3 review verifies the intended property effects without hardware or image claims |
| [Factory property-prefix preservation](factory-property-contexts-capability.md) | Policy3 review verifies all seven full prefix regions retain factory labels; current image delivery and hardware behavior remain unverified |
| [Helper and Binder source integration](policy-source-integration.md) | Preserved v10 native result, guarded helper admission and reproducible factory derivation |
| [VINTF build closure](vintf-compatibility.md) | Preserved factory/APEX input closure and original matrix-coverage failure; later scoped comparison results and remaining limits are in native ROM integration |
| [Exact framework matrix](framework-matrix.md) | Installed source produces all 155 tuples; a reviewed distinct postcheck accepts canonical default-version omission and verifies current outputs, without full compatibility or runtime claims |
| [AIDL metadata name audit](../tools/vintf-definition-audit/README.md) | The host auditor compiles and links; the historical metadata capture lacked 134 matrix names, while auditor execution and complete compatibility remain unverified |
| [Optional Qualcomm AIDL namespace exports](../config/nezha-qti-aidl-namespaces.json) | Reviewed auditor/seven-NDK build verifies 38 fresh actions and 32 reused display-config checks; auditor execution and complete definition coverage remain pending |
| [Framework allocator selection](framework-allocator.md) | Preserved v13i compilation and current 4 KiB alignment/producer capture; guest prerequisite verification passes, without source-to-binary equivalence, full VINTF or runtime registration |
| [Original ODM shipping API](vintf-shipping-api.md) | Reviewed wrapper forwarding with original property bytes; native source adoption and complete compatibility remain separate |
| [Factory mi_ext integration](mi-ext-inputs.md) | Reviewed prebuilt admission and direct-root AVB packaging path; native adoption tracked in current status |
| [Optional mi_ext care-map source](mi-ext-care-map.md) | Committed inactive successor binds all 22 original ODM property files and exact imports; native tools, final Evolution SYSTEM marker, packaging and OTA coverage remain unqualified |
| [A/B recovery packaging](recovery-packaging.md) | Exact dedicated working76 payload without an inapplicable non-A/B two-step image |
| [AVB image-set verification](avb-image-set.md) | Explicit per-role public keys, complete descriptor coverage and partial-result limits |
| [Boot-image validation](boot-image-validation.md) | Verified source543 public runtime and retained raw-v6 omission; final-package inputs, native image checks and physical boot remain pending |
| [Host AVB signing preparation](avb-signing.md) | Reproducible development-chain recipe, public preparation and Mac-only private signing; no completed signed ROM claim |
| [Target-files AVB inventory](target-files-avb-inventory.md) | Read-only bounded ZIP/retained-input inspection with 42 synthetic tests; no actual target-files admission, extraction, image validation or signing |
| [Target-files input materialization](target-files-materialization.md) | Copies thirteen ZIP images and two retained inputs; 44 synthetic tests, with publication, normalized signer-manifest identity and actual materialization kept separate |
| [Final APK inventory preparation](final-apk-projection.md) | Read-only join of supplied graph, eight image inventories and captured APK payloads; package/producer admission, native Treble labeling, APEX coverage, signatures and effective permissions remain unverified |
| [Initial GMS optional-library correction](gms-customization-optional-library.md) | Preserved 0018 preparation and package-failure checkpoint; the later audit and four-file source adoption are recorded separately below |
| [Additional GMS optional-library corrections](gms-prebuilt-optional-libraries.md) | Preserved 0019 preparation and the original 91-pass/four-mismatch audit; later four-file adoption is recorded separately below |
| [GMS source integration](gms-source-integration.md) | GMS2 native/postcheck and complete retained-evidence replay pass, with fresh SignApk/CrossDevice actions, four verified reused strict statuses and sixteen native APK checks; image/package/runtime gates remain separate |
| [Ordinary Images2 build](build-progress.md) | Native build/postcheck and retained-evidence readback/replay pass for four pinned prebuilt image outputs and three policy SHA sidecars, with seven fresh installed producers and retained originals; packaging, the signed chain and physical boot remain separate gates |
| [SignApk source-stamp correction](signapk-source-stamp.md) | Frozen two-file patch removes obsolete stamp metadata before APK signing and restores the normal signer dependency; its preparation record is preserved, with later adoption, rebuild and strict artifact results recorded above |
| [BCR source integration](bcr-optional-window-libraries.md) | One-file 0021 adoption and config9/context9/Nothing6 pass; six physical metadata values match the successor build identity, while strict BCR status/module, APK and package checks remain separate |
| [SystemUI Clock library correction](systemui-clocks-optional-window-libraries.md) | Historical selected-nine/Images3 passes and later Package3 checksum failure; complete failure readback and a 14-case Toybox compatibility probe are preserved, with subsequent checksum adoption recorded below |
| [Signed target-files reconciliation](signed-target-files-reconciliation.md) | Sole DTBO prebuilt-alias normalization requires full-payload and strict unsigned-metadata proof; Package5 inspected read-only, 258 focused/4,508 offline tests pass, with Package6 signing and reconciliation still unverified |
| [Five native exit and protected-sidecar failure](build-progress.md#five-native-exit-and-protected-sidecar-failure--2026-09-02) | Native exit 0 but profile exit 1 on ctime-only sidecar changes; bytes and source guards stay unchanged, hardlink cause remains an inference, and recovery/Package6/final ROM verification remain pending |
| [Vendor/ODM retirement and five-image preparation](build-progress.md#vendorodm-retirement-and-five-image-preparation--2026-09-02) | Eight old image leaves retired with 21.03 GiB observed host recovery; historical manifests need restoration, read-only queries/proof staging pass, and the Five native rebuild is not yet verified |
| [Images6 verified build result](build-progress.md#images6-verified-build-result--2026-09-02) | Native/profile and complete source/action/retention review pass, including full native-log replay and retained-original hashes; image metadata hook, five-image/Package6 and final ROM gates remain separate |
| [Host scratch and Package5 duplicate retirement](build-progress.md#host-scratch-and-package5-duplicate-retirement--2026-09-02) | Six scratch files and 15 proven P5 duplicates retired; ZIP/stock sources retained, old P5 manifest inactive until full restoration and fresh validation, and 10.08 GiB operation-local host recovery |
| [Second old-output cleanup and trim](build-progress.md#second-old-output-cleanup-and-trim--2026-09-02) | 169,727 historical intermediate descendants removed while retaining both roots; approved trim adds 15.01 GiB host free, restores the original builder and preserves bounded identities; Images6 capture is not an image result |
| [Selected4 component build](build-progress.md#selected4-component-build--2026-09-02) | Native/profile postcheck pass with 26 fresh actions, eight fresh strict statuses and nine configured APK checks; Flex prior equivalence and raw-stream replay remain distinct, while Images6/Package6 and boot gates stay open |
| [Nothing11 passes after storage cleanup](build-progress.md#nothing11-passes-after-storage-cleanup--2026-09-02) | Native and profile exit 0, all six callback maps and 254 configuration fields stable, and six metadata values verified; no fresh component/image, Package6 or boot claim |
| [Nothing10 profile failure and historical host-storage hold](build-progress.md#nothing10-profile-failure-and-host-storage-hold--2026-09-02) | Native exit 0 but profile exit 1 after six configuration changes; preserves the earlier below-reserve hold and then-pending Nothing11 state, before cleanup and the successful successor above |
| [SHA256 source adoption and Config13/context13](build-progress.md#sha256-source-adoption-and-config13context13--2026-09-02) | One BoardConfig change installed and both queries pass under 86e40; 254 fields stay unchanged and the Soong AVB transition awaits Nothing10; component/image/Package6 and final ROM gates remain pending |
| [Package5 host inputs and AVB/VINTF failures](build-progress.md#package5-host-inputs-and-avbvintf-failures--2026-09-02) | Whole host ZIP independently admitted and 15 inputs materialized; copier publication remains failed, AVB preparation rejects five SHA-1 descriptors, and VINTF capture fails at the property parser; no signing or ROM claim |
| [Package5 corrected supplement and complete evidence replay](build-progress.md#package5-corrected-supplement-and-complete-evidence-replay--2026-09-02) | Separate verifier and full 242-file replay pass for two original fresh actions, metadata and selected ZIP members; original failure preserved; no host ZIP/image-body transfer or complete-ROM claim |
| [Package5 native exit and profile postcheck failure](build-progress.md#package5-native-exit-and-profile-postcheck-failure--2026-09-02) | Native exit 0 but original profile postcheck fails on a missing checker callback; full native streams retained; corrected supplement, ZIP admission and fresh package-action proofs remain pending |
| [Images5 and complete evidence replay](build-progress.md#images5-and-complete-evidence-replay--2026-09-02) | Seven fresh actions, three sidecars and four image checks pass with full 56-file replay; metadata values pass but the image packaging hook remains unverified; Package5 and runtime remain separate |
| [Selected3 and complete evidence replay](build-progress.md#selected3-and-complete-evidence-replay--2026-09-02) | 26 fresh actions and eight fresh statuses pass; full 203-file replay reproduces three products without host export of 52 retained binaries; Images5 and Package5 remain separate |
| [Config12/context12 and Nothing9](build-progress.md#config12context12-and-nothing9--2026-09-02) | Queries and Nothing9 pass under b429 with full stream/metadata review; Config12 direct-launch limits and unverified Ninja argv remain explicit; fresh selected components, Images5 and Package5 remain separate |
| [Metadata-mode flags source installation](build-progress.md#metadata-mode-flags-source-installation--2026-09-02) | Three atomic exchanges install seven replacements within 548 source files; exact records and source lock pass; successor identity, configuration, builds and Package5 remain separate |
| [Package4 build-metadata mode failure](build-progress.md#package4-build-metadata-mode-failure--2026-09-02) | Checksum passes, then absent prebuilt-image flags fail the metadata guard; full failure streams and three metadata bodies retained; committed host fix is not VM adoption or package success |
| [Images4 and complete evidence replay](build-progress.md#images4-and-complete-evidence-replay--2026-09-02) | Seven fresh actions, three recomputed sidecars and four image checks pass; full 56-file evidence replay preserves native-only image-hash scope; Package4 and runtime remain unverified |
| [Selected-nine2 and retained-evidence replay](build-progress.md#selected-nine2-and-retained-evidence-replay--2026-09-02) | Forced-fresh 26-action build and full 203-file replay pass; 109 retention-journal events verified without exporting 52 retained file bodies; host-only package projection is not Package4 or fresh GMS observation |
| [Config11/context11 and Nothing8](build-progress.md#config11context11-and-nothing8--2026-09-02) | Native queries/Nothing8 and six physical metadata values pass under `a7db`; config11's byte-only closure limits remain, while shared capture and successor component/image/package evidence stay separate |
| [Checksum 0023 source and identity](build-progress.md#checksum-0023-source-installation--2026-09-02) | Historical 548-file/fifteen-project adoption and eight-output host identity replay; later query/Nothing8 results are recorded above, without promoting the source milestone to image or packaging success |
| [Target-files metadata](target-files-metadata.md) | Historical 205-file projection, ordinary recipe hook and Package3 unsupported-Toybox-flag failure; 14 compatibility and 15 rendered-guard cases pass; the separate source-install checkpoint above does not establish packaging success |
| [Maintained policy-image delivery](policy-image-delivery.md) | Explicit 4 KiB successor repeats 247-file host bundles bound to the actual component result; metadata hook and source/image selection remain pending, with signed-chain/rollback/fit gates retained for final artifacts |
| [Policy3 delivery source selection](../config/nezha-policy-image-delivery-policy3.json) | Reviewed adoption verifies 537 source files; images1 retains native 0/wrapper 1, while its separate artifact postcheck, receipt readback and independent review pass; packaging remains unverified |
| [Device delivery integration](target-files-delivery-integration.md) | Committed opt-in generator and matching 47-file 4 KiB delivery candidates; isolated Kati fixture passes 60 cases, while ordinary product execution and source/image selection remain pending |
| [ROM construction prerequisites](rom-construction.md) | Committed inspection-only consumer reports five unbound native input/coverage roles and refuses construction; no BoardConfig or blocked target is enabled |
| [Combined packaging source composition](target-files-source-composition.md) | Explicit ten-file closure for patches 0005–0011, preserving older contracts and original metadata; native adoption remains pending |
| [Policy-image input preparation](policy-image-inputs.md) | Repeated policy3 raw/NONE-footer inputs and separate ordinary-image postchecks are verified; the signed parent chain, physical fit and packaging remain pending |
| [Binder correction](binder-policy-correction.md) | Preserved intermediate correction prototype |
| [Helper policy projection](helper-policy-projection.md) | Preserved passing copied-CIL prototype preceding native source integration |

| Guide | Purpose |
| --- | --- |
| [Device baseline](device-baseline.md) | Sanitized findings from this phone |
| [Source research](device-research.md) | Verified branches, device-tree defects, kernel gaps |
| [Community bring-up](community-bringup.md) | Later XDA release, Leica port reports, private-tree and firmware limits |
| [MiCode kernel review](micode-popsicle-review.md) | Exact shared kernel/KMI evidence and remaining Nezha board gaps |
| [Kernel configuration audit](../kernel/xiaomi/nezha/config-audit/README.md) | All 812 explicit ACK requests match stock; separate DDK comparisons and preservation assertions |
| [Native features](native-features.md) | Camera/Leica, IMS, fingerprint, charging, display, audio, accessories |
| [Captured camera](camera-baseline.md) | Actual APK, native library dependencies, framework hooks and camera HAL declarations |
| [Stock collection](stock-evidence.md) | Read-only capture, privacy, and partial-result handling |
| [Firmware intake](firmware-intake.md) | Preserve local ROM packages and provenance without executing scripts |
| [Fastboot extraction](fastboot-extraction.md) | Bounded TAR/GZIP image extraction with hashes and full-stream integrity checks |
| [Matching firmware](firmware-source.md) | Verified Xiaomi CDN URLs, partial download status, and safe resumption requirements |
| [Factory intake](factory-firmware-intake.md) | Separate user-provided China TGZ, preserved original and verified extraction |
| [Factory validation](factory-firmware-validation.md) | Independent sparse reconstruction, logical layout, passing selected AVB chain and EROFS checks |
| [Factory boot contract](factory-boot-contract.md) | Exact ramdisks, headers, DTs, enforcing fstab differences and preserved module bytes |
| [Factory framework contract](factory-framework-contract.md) | VINTF/XML and policy comparison without assuming framework compatibility |
| [Factory input reuse](factory-input-reuse.md) | Receipt-bound factory inputs, unchanged dependencies and explicit mixed provenance |
| [Partition metadata](partition-metadata.md) | Verified package GPT/XML extents, growth placeholders and live-capacity limits |
| [Supplied Xiaomi.eu package](provided-firmware.md) | Verified local integrity, unverified origin, embedded identity and sparse super layout |
| [Firmware analysis](firmware-analysis.md) | Verified sparse reconstruction, logical layout and filesystem checks |
| [Boot/kernel/AVB contract](boot-contract.md) | Exact boot formats, modules, DTs and retained verification failures |
| [VINTF and permissions](vintf-contract.md) | Guarded filesystem captures, exact live XML matches and framework compatibility gates |
| [Actual VINTF validation](vintf-validation.md) | Successful vendor/ODM and active APEX load/merge; separate framework-definition and compatibility limits |
| [Vendor APEX dependencies](apex-dependencies.md) | Guarded CAS, Widevine and Wi-Fi payload inspection and matching active-package evidence |
| [SELinux contract](selinux-contract.md) | Historical stock policy inputs and seven strict neverallow failures; see current status for later work |
| [User policy integration](selinux-user-integration.md) | Historical user-policy conflicts, source ownership and enforcing-policy requirements |
| [Hardened user build](user-security-build.md) | Actual v8 component build, two unfiltered zero-permissive source binaries and separate factory-policy failure |
| [DSP policy source](dsp-policy-integration.md) | Explicit factory-bound source option, preserved assertions and separate compiler-fixture scope |
| [DSP policy build](dsp-policy-build.md) | Actual user build, two zero-permissive source binaries and four remaining factory-policy assertion sites |
| [Build progress](build-progress.md) | Authored Nezha product, actual Kati result, module compilation and private input receipts |
| [Boot/DLKM build](boot-dlkm-build.md) | Four built engineering images, exact kernel/overlay and 484 preserved module payloads |
| [Factory-based boot build](factory-boot-build.md) | Inspected user init_boot/vendor_boot/DTBO, 430 retained ramdisk modules and unsigned AVB-block scope |
| [Nezha integration plan](nezha-integration.md) | Device/vendor/kernel boundaries and remaining complete-ROM gates |
| [Camera build inputs](camera-inputs.md) | Narrow system-ext dependency selection, requested ELF checks and unresolved APK class-loader requirements |
| [Camera APK integration](camera-apk-integration.md) | Verified signature/layout and exact Java, privilege and packaging requirements before importing the APK |
| [Earlier Camera APK admission](camera-apk-inputs.md) | Preserved Xiaomi.eu/live input checks and two reproduced packaging failures |
| [Original factory Camera APK](factory-camera-apk.md) | Unchanged factory input passes strict privileged/preprocessed packaging; permission grants, effective SELinux label and product selection remain unverified |
| [Factory Camera permission grants](../research/factory-camera-permission-grants.json) | Captured source distinguishes pure-signature grant denial and service enforcement; effective grants, installed signing state and Camera behavior remain unverified |
| [Factory Camera build-only packet](camera-apk-build-admission.md) | Prerequisite and complete target/alias inventory reviews pass for v13ja; a fresh post-matrix baseline and ten extra protected policy leaves are required before activation or APK builds |
| [DEX runtime provider](dex-import-uses-library.md) | Strict Soong patch and native fixtures; current component build and bounded producer/output review pass, without Camera APK or runtime API closure |
| [Camera runtime inputs](camera-runtime-inputs.md) | Exact JAR module names and XML registrations without relaxing class-loader checks |
| [Factory framework providers](framework-providers.md) | Captured Sigma/QCC providers and strict native dependency admission; runtime and ABI limits |
| [Miracast audio correction evidence](../research/framework-provider-audio-compatibility.json) | Exact v7 dependency derivation installed as v13ha; policy source build passes, without complete ABI or runtime admission |
| [Framework-provider source admission](framework-provider-source-admission.md) | Reproducible host v13 candidate, private policy and verified payload consumers; not installed in the v12fa checkpoint |
| [Current 4 KiB bring-up profile](nezha-page-size-v2.md) | Authorized baseline bound to the compiled stock kernel and current v7 providers; component build and 26 fresh ELF/symbol checks pass with checks enabled, while full compatibility and hardware remain unverified |
| [Current-provider 4 KiB source integration](nezha-page-size-v2-integration.md) | Corrected v13ja installation, native 37-goal build and separate 26-provider checks pass; first-stage failure and 16 KiB evidence preserved, without full compatibility or image-adoption claims |
| [Historical 4 KiB experiment](nezha-page-size.md) | Preserved v1 descriptor and unadopted v13g candidate; superseded by the separate current-provider preparation, without resolving 16 KiB/VTS compatibility |
| [OEM property contract](../config/nezha-oem-properties.json) | Optional four-property source and permission budget; native validation separate from v11b |
| [Framework-provider policy contract](../config/nezha-framework-provider-policy.json) | Bounded enforcing source for the two selected providers; no implied native or hardware pass |
| [EROFS metadata inventory](../tools/erofs-metadata/README.md) | Read-only complete metadata evidence required before a policy-image derivation |
| [ZRAM module plan](zram-module-plan.md) | Distinct vendor/GKI providers, ordered loader behavior and selector requirements |
| [Kernel exports](kernel-export-contract.md) | Independently decoded stock kernel exports and selected module CRC matches |
| [Module providers](module-provider-audit.md) | All 914 captured instances, matching global provider candidates and stage/loading limits |
| [Module boot stages](module-stage-closure.md) | Exact selected closures, conditional earlier-stage providers and stock-loader limits |
| [TWRP bring-up](twrp-bringup.md) | Current working TWRP baseline, repeatable build and safe recovery handling |
| [Recovery review](recovery-plan.md) | Selected TWRP default, dedicated recovery layout and remaining ROM compatibility gates |
| [Build host](build-host.md) | Linux requirements, platform sync, and future build gates |
| [Apple Container](apple-container.md) | Verified local Rosetta workflow, persistent storage, task status and limits |

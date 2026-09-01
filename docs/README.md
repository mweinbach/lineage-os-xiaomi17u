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
| [Initial GMS optional-library correction](gms-customization-optional-library.md) | Preserved 0018 preparation and package-failure checkpoint; the later audit and four-file source adoption are recorded separately below |
| [Additional GMS optional-library corrections](gms-prebuilt-optional-libraries.md) | Preserved 0019 preparation and the original 91-pass/four-mismatch audit; later four-file adoption is recorded separately below |
| [GMS source integration](gms-source-integration.md) | GMS2 native/postcheck and complete retained-evidence replay pass, with fresh SignApk/CrossDevice actions, four verified reused strict statuses and sixteen native APK checks; image/package/runtime gates remain separate |
| [SignApk source-stamp correction](signapk-source-stamp.md) | Frozen two-file patch removes obsolete stamp metadata before APK signing and restores the normal signer dependency; its preparation record is preserved, with later adoption, rebuild and strict artifact results recorded above |
| [Signed target-files reconciliation](signed-target-files-reconciliation.md) | Maintained reconciler and streaming copier require an already verified signed image set and preserve the original archive; 72 synthetic tests, with actual archive/signing/reconciliation still pending |
| [Target-files metadata](target-files-metadata.md) | Exact 205-file projection for retained factory images and ordinary recipe hook; native packaging and policy-image admission remain separate |
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

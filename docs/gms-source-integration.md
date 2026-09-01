# GMS source integration

The corrected **0020 source transaction succeeds at 2026-09-01 13:36:04 UTC**,
with native/root exit 0, following the successful **13:22:20 UTC** stage.
Two source exchanges and seven journal events complete without rollback.
`commit_verified` is recorded at **13:33:51 UTC**, before final acceptance and
process exit. The complete installation and journal readback passes independent
review; `actual-commit.json` is an exact copy of the returned bytes, not a
reserialized receipt.

The active inventory is **543 files across fourteen projects**. It preserves
all prior 541 source rows and adds the two reviewed `build/make` postimages:
`SignApk.java` and `core/app_prebuilt_internal.mk`. The patch and source contract
are unchanged. The installed SignApk code excludes the obsolete stamp digest
before APK re-signing, and ordinary non-`PRESIGNED` prebuilts gain a normal signer dependency.
These are installed source changes; regenerated dependency edges and corrected
APK behavior still require native build and strict verification evidence.

The history correction selects the exact before/after `build/make` status at
each history call while preserving the six Git queries, three allocator-project
predicates and seven historical rows. The real native stage/install execute the
full history checks, including both installation phases, alongside complete
543-file/mode and fourteen-project checks. The canonical predecessor-history
identity remains `73499a4d…` / 312,989 bytes. The separate full host history-chain
fixture replay remains pending and is not counted as a pass.

Host projection from the completed installation calculates identity
`3c24f46cf801e6abd6d5361cd840875eca0230aea6c648d8c7248d951e995b7e`
and proposed build number **`nezha.3c24f46cf801e6abd6d5361c`**. All five descriptor
vectors retain their prior rows and modes; only the source vector adds two inputs.
The calculation does not recheck live private inputs or authorize dispatch;
native configuration and metadata observations remain unset. config8/context8,
the next ordinary frontend run, rebuilt SignApk, strict GMS retry, Images2 and
package2 remain pending at this checkpoint.

Eight projects still carry intentional patches; no upstream revision changes.
Original GMS APKs and eight image observations (six present files/two exact
absences) remain protected. `bka`, `bp4a`, `user`, `WITH_GMS`, epoch `1788144555`,
4 KiB, normal Android enforcement and working76 are unchanged. No image, APK,
package or hardware success follows from source adoption. The earlier failed
attempts and host-only preparations below retain their original scopes.

The first **0020 SignApk source-install attempt is rejected, with both exchanges
rolled back and verified** at **2026-09-01 12:56:39 UTC**. The preceding stage
passes at **12:50:15 UTC**, including full readback and independent review of
the two original files, preserved copies and staged replacements. Its 543-entry
candidate does not become active: the source remains **541 files/fourteen
projects**, with build number `nezha.a2d9ab6affbe09593d338212`.

After both intended edits, the retained `_allocator_project_history` check
still expects the old live `build/make` status. The eleven-event journal records
two forward and two reverse exchanges; `rollback_finished` has `verified=true`
and no errors. The failure record, staged inputs and `INCOMPLETE` marker remain;
neither `installation.json` nor `failed-installation-receipt.json` exists.
Fresh readback at **12:58:10 UTC** confirms unchanged bytes and presence for all
fifteen inputs (thirteen present files and two exact absences). The fourteen
project revision/status contexts, two captured origin reports and both
source/output roots also match. Original
source inodes, bytes, modes and mtimes return; only the two exchanged files'
ctimes differ. This is not a full output-tree comparison or a new source identity.
The additive history-guard correction remains preparation, not a verified adoption.

Separate **read-only APK diagnostics complete all sixteen native commands** at
**12:26:06 UTC**. Seven signature commands and all eight manifest-badging commands
exit 0; installed CrossDevice signature verification alone exits 1 with the same
`No SourceStamp signature` warning under `-Werr`. The aggregate remains 1, with
no completed artifact admission. All six full guard maps and the installed APK
observations remain unchanged. The original validators also reject the pinned
tools' source-stamp timestamp line and `minSdkVersion` spelling; their failed
result and all sixteen command receipts remain intact.

The later host parser correction recognizes those captured formats without
relaxing native exit, warning, signer or manifest requirements. Its 97 author
tests and 97 independent repeat tests pass with zero skips. Saved-output replay
accepts seven signature outputs and four source/installed manifest pairs, while
still rejecting installed CrossDevice. These are host checks of retained
541-source diagnostics, not new native APK verification or proof of the proposed
543-source candidate. Source adoption, a rebuilt SignApk and a complete strict
ordinary component retry remain required before Images2 and package2.

The targeted **GMS component attempt failed overall**, despite native Soong
exit 0 at **2026-09-01 11:45:18 UTC**. Its stdout records four strict uses-library
checks, four APK builds and four installs. The wrapper exits 1 at **11:50:26 UTC**
because installed CrossDevice verification reports `No SourceStamp signature`
under `-Werr`. The complete postcheck does not finish. The source remains
541 files/fourteen projects with build number `nezha.a2d9ab6affbe09593d338212`;
no signing-source correction has been adopted at this checkpoint.

The earlier **corrected GMS read-only graph capture passes with native/root
exit 0** at **2026-09-01 11:11:47 UTC**. All nineteen query streams are complete and
independently reviewed. Six proof records are staged at **11:21:37 UTC**.
The later host qualification covers twelve own actions for the four GMS
modules; their targeted build, Images2 and package2 are pending at that checkpoint.
Provider runtime bytes, registration and final package selection remain separate.

The preceding native baseline passes **config7, context7 and `nothing4`**, with
native/root exit 0 through **2026-09-01 09:46:14 UTC**. It selects 541 source
files across fourteen projects and build number `nezha.a2d9ab6affbe09593d338212`.
The four GMS module builds, Images2 and package2 are then pending; these successful
queries and the ordinary `nothing` run do not establish their status actions,
class-loader contexts, images or package outputs.

The four Makefile corrections from [0018](gms-customization-optional-library.md)
and [0019](gms-prebuilt-optional-libraries.md) are installed in the existing
Evolution checkout. Native and root installation exit 0 at **2026-09-01
09:08:48 UTC**. This is source adoption with complete receipt readback, not an
ordinary GMS module build or a successful target-files package. The frozen
patch contracts retain their earlier preparation scope; they are not rewritten
to claim later native results.

| Phase (native unless noted) | Started UTC | Finished UTC | Result |
| --- | --- | --- | --- |
| Stage | 08:56:41.613955 | 09:00:35.538351 | Native/root 0; four original copies and four postimages retained |
| Install and accept | 09:02:19.958339 | 09:08:48.856056 | Native/root 0; four file exchanges and eleven journal events |
| config7 | 09:16:31.165545 | 09:17:23.663493 | Native/root 0; 21 configuration values pass |
| context7 | 09:24:10.391849 | 09:25:02.663108 | Native/root 0; seven context values pass |
| nothing4 | 09:34:56.316554 | 09:46:14.038756 | Native/root 0; six metadata-file values pass |
| Corrected read-only graph capture (root interval) | 10:58:17.868611 | 11:11:47.896959 | Native/root 0; fourteen GMS and five provider queries |
| Six-proof staging (root interval) | 11:21:37.252232 | 11:21:37.544322 | Native/root 0; proof files only, no build |
| Four-module Soong build | 11:43:38.788335 | 11:45:18.351575 | Native 0; four strict checks, four builds and four installs logged |
| Component attempt including postcheck (root interval) | 11:41:00.052091 | 11:50:26.236978 | Root 1; installed CrossDevice fails strict SourceStamp verification |
| Read-only APK diagnostics (root interval) | 12:20:22.282856 | 12:26:06.770618 | Root 1; sixteen commands complete, fifteen native 0 and installed CrossDevice signature 1 |
| SignApk source stage (root interval) | 12:46:12.282056 | 12:50:15.260121 | Exit 0; two replacements staged, no source adoption |
| SignApk source install (root interval) | 12:52:33.046595 | 12:56:39.065377 | Exit 1; both exchanges reversed and rollback verified |
| Fresh post-rollback input capture (root interval) | 12:58:05.761870 | 12:58:10.457568 | Exit 0; scoped original bytes, absences and project state restored |
| Corrected SignApk source stage (root interval) | 13:18:08.601814 | 13:22:20.092088 | Exit 0; two replacements staged with native history checks |
| Corrected SignApk source install (root interval) | 13:28:32.839407 | 13:36:04.974906 | Exit 0; two exchanges, seven journal events and final acceptance |
| Full corrected-installation readback (root interval) | 13:39:28.428797 | 13:39:28.663033 | Exit 0; complete installation/journal bodies and exact commit bytes retained |

The component command is `build/soong/soong_ui.bash --make-mode -j8` with
`CrossDeviceAccessServicePrimary`, `CustomizationBundlePrebuiltFullVersion`,
`PersistentBackgroundServices` and `SafetyHubPrebuilt`. All six complete
source/input guard maps and 254 configuration values match before and after;
Ninja argv, limits and sandbox checks pass. These source checks do not imply
unchanged Android build outputs. The full failed result retains `postcheck=null`,
`profile_completed=false` and `profile_validation_verified=false`; the native
action rows are not a completed artifact or freshness qualification.

The original postcheck completes CrossDevice's original-APK signature verification and
manifest badging with exit 0. Installed-APK verification prints v3 signature
success, then exits 1 because of the SourceStamp warning. Subsequent checks are
not counted as passes in that attempt; the later sixteen-command diagnostics
above have separate receipts. The retained full result, diagnostic receipts and raw
stdout/stderr remain authoritative; this failure is not promoted to success.

Read-only structure inspection finds the same original CrossDevice APK
(`c92b8276…`, 16,962,727 bytes). Built and installed copies match
(`f3a86078…`, 16,954,535 bytes). All three contain the same 32-byte
`stamp-cert-sha256` entry, but the built/installed APK signing block lacks the
original SourceStamp signature pair. The APK signing block itself remains
present. This inspection does not independently verify any signature.

Captured SignApk source discards the incoming APK signing block; the actual
output confirms that the old certificate entry survives this signing path.
Captured verifier source explains why the unmatched entry triggers the warning.
The [host-prepared correction](signapk-source-stamp.md) removes the stale entry
before new APK signatures and adds a normal `SIGNAPK_JAR` dependency for
non-`PRESIGNED` prebuilts so an updated
signer triggers their incremental rebuild. Whole-file/OTA signing, `PRESIGNED`
handling, original proprietary APKs and strict `-Werr` behavior must remain
unchanged. Source adoption, a rebuilt signing tool and an ordinary component
retry are still required; the proposal is not an observed fix.
Images2, package2 and all final ROM gates remain unverified.

The journal's final `commit_verified` event is **09:06:54.418454 UTC**, before
the complete installation acceptance finishes. Full readback binds the stage,
installation, journal and actual commit receipts. Separate independent reviews
clear the recorded stage and installation, including source/image/history joins.
The [machine record](../research/gms-source-integration.json) contains exact
paths, hashes and these scope limits.

The retained source vector grows from **537 files/thirteen projects** to
**541 files/fourteen projects**, adding the four corrected GMS Makefiles under
the existing pinned `vendor/gms` revision. Original source rows and project
contexts are preserved. Original APKs, source-file modes, strict checks,
signing and package-placement settings remain unchanged. HTTP remains selected;
CrossDevice removes only its stale explicit HTTP declaration, preserving the
automatic SDK-28 compatibility handling. SafetyHub retains HTTP and prepends
Wear in the manifest's order. No provider or library registration is fabricated.

Eight image observations remain unchanged: **six present files and two exact
archive absences**. This is preservation evidence, not eight built images or
a new image reproducibility result. The 4 KiB baseline, working76 recovery and
normal Android enforcement are unchanged; no phone operation occurs.

Host reprojection produces identity
`a2d9ab6affbe09593d3382120be86d02f453c4f2c82dce1aef2a68910b16d488`
and proposed build number `nezha.a2d9ab6affbe09593d338212`. It consumes the
captured installation and preserves prior descriptor rows and modes. Independent
host review replays all eight projection files, preserving the previous rows,
runtime inputs, modes and seed while changing the build number. It does
not rerun live source/private-input checks, admit native dispatch or verify
generated configuration and metadata values. The previous `8643` identity and
all failed package evidence remain historical inputs.

The later native queries and `nothing4` preserve all six complete source/input
guard maps, the full 254-field configuration, aliases, source history and strict
settings. `nothing4` separately verifies six metadata-file values for the new
identity; config7's literal `FROM_FILE` references alone do not establish those
contents. None of these value checks proves fresh metadata rewrites.

The actual frontend command is exactly
`build/soong/soong_ui.bash --make-mode -j8 nothing`. Its full stdout contains
165 frontend steps followed by one `nothing` action, not four successful GMS
module builds. Ninja, its limits and sandbox are observed; descendant Ninja
argv and native component actions remain outside this profile's qualification.
The post-run read-only measurement retains that complete stdout and log
measurements, without a module-info content claim. The later graph capture and
bounded host qualification below are separate evidence; neither replaces the
later component attempt's required artifact and freshness checks.

The corrected capture retains all **fourteen GMS queries and five provider
queries**, with **sixteen graph files totaling 6,862,572,001 bytes** and **four
log files totaling 230,711,288 bytes** unchanged before and after. Six complete
source/history callback returns are compared at real root before hashing,
covering 541 source files across fourteen projects. The capture does not retain
all raw callback maps inside its JSON. Three additional provider source bodies
are checked inside the read-only jail; this is not the complete source vector.
No build recipe or manifest checker executes during the capture.

Actual pinned source defines the HTTP runtime alias
`org.apache.http.legacy.impl`, whose captured forward path reaches the installed
`system/framework/org.apache.http.legacy.jar` producer. The earlier selector
incorrectly expected the SDK API alias to reach that installed JAR. Its failed
`49d383f3` capture remains unchanged, including the error and incomplete-result
fields. The corrected capture does not by itself qualify producer actions,
all transitive recipes, installed provider bytes or runtime registration.

The existing `DONT_DEXPREOPT_PREBUILTS := true` source branch disables
precompilation for these four APKs, without disabling their four strict
uses-library checks. Their app `dexpreopt.config` files are not
produced by this configuration; no substitute files or generated class-loader
contexts are fabricated or counted as passes. The two AndroidX Window dependency
configs used by the strict checks are present and verified separately. These
absence observations are scoped to the pre-build read; parent-directory metadata
is not required to remain unchanged across a future build.

The captured `product_packages.txt` is the raw `PRODUCT_PACKAGES` request list
before override filtering, not an installed-app inventory. The original host
admission's EmergencyInfo rejection is preserved. A corrected source-based
interpretation now passes host admission while retaining SafetyHub's override;
actual installed or archived EmergencyInfo absence is not yet verified.

A separate hash-only observation at **11:12:45 UTC** verifies all four original
source APKs and their `0644` modes unchanged; it runs no APK signature checker.
The six staged proof files total **9,768,787 bytes**, with `0400` modes and
root ownership, in a dedicated validation directory. This stage writes only
proof records, not source, images or Android output. The actual host admission
qualifies the four modules' twelve own actions and preserves strict checks;
it remains preparation for the ordinary build, not an execution result.

The source audit matches all **1,179 pinned HEADs and origins**. Eight projects
carry intentional local patches: `build/make`, `build/soong`,
`device/lineage/sepolicy`, `external/mdnsresponder`, `system/core`,
`system/sepolicy`, `vendor/gms` and `vendor/lineage`. The corrected root review
checks each reported status against its installed guard rather than requiring
a pristine checkout. The earlier review assumption of no audit issues is not
treated as a source regression or used to hide those patches.

The original 95-APK audit remains **91 passes/four mismatches**. The later
four-correction native probe passes against original APKs with proposed lists,
but remains read-only proposal evidence, without generated commands or ordinary
build stamps. Source adoption does not retroactively turn either into ordinary
module or package success.

The seven omitted declarations appear in the captured raw product request
inventory; their final installed selection is not established here. They are three
compressed full APK payloads packaged as `ETC`, two `JAVA_LIBRARIES` JARs, and
`PrebuiltBugle`/`Velvet` APKs with pre-existing explicit uses-library waivers.
The separate stub APK passes do not cover the three full compressed payloads.
Neither the omissions review nor ordinary packaging qualifies these seven as
manifest passes. The read-only Bugle/Velvet manifest capture completes at
**2026-09-01 09:29:53 UTC**, with native/root exit 0, two successful `aapt2`
commands and all five input guards unchanged. Neither original APK declares a
required Java uses-library. Bugle omits four optional declarations; Velvet omits
six, with HTTP already declared. The exact capture and independent review are
pinned in the machine record. No strict checker ran against either APK, and no
signature or provider-presence validation is implied. The saved Makefiles and
badging do not explain the waivers' rationale; both waivers remain unchanged.

Current VINTF, Camera APK/runtime, packaged-policy, signed-chain, partition-fit,
OTA and hardware gates remain separate. The first target-files attempt remains
failed; no complete or flashable ROM is admitted by this source transaction.

# Current Nezha workspace status

**Installed phone: v11r1 userdebug (`nezha.130611bac9232625e0066968`),
slot A, boot completed with SELinux Enforcing.** The approved eight-image
installation completed without a wipe or slot change. Xiaomi Camera now saves
ordinary rear/front photos, main and telephoto 50 MP photos, and a 200 MP photo
with fully decoded Ultra HDR. Xiaomi Pro RAW and all three physical rear RAW
sensors fully decode. Aperture saves all ten rear/front effect cases while
switching modes in one running app process; nine decode as Ultra HDR, while
front HDR has a neutral-gainmap metadata interoperability failure. See the
[v11 installation and validation record](camera-v11-install-validation-20260908.md).

Ultra RAW saves its companion JPEG but leaves an empty DNG because the app's
framework save API is missing. Early boot diagnostics identify AIDL audio flag
and usage conversion failures before audio policy initialization. Video remains
unverified on v11 and failed on v10 with a null audio policy manager.
**Full camera acceptance remains incomplete.**

A [successor source candidate](camera-save-audio-compat-20260908.md) adds the
compressed-DNG save APIs, repairs the measured neutral HDR metadata and admits
the two rejected audio enum values. Its host checks pass and source revision 8
(`nezha.efda11d09f81d7685c018d03`, 668 rows) is installed in the build VM.
The component/full build, signing and successor phone validation are pending.

The installed source includes the guarded [vendor-key discovery fix](camera-vendor-key-discovery-20260908.md),
[CameraX cache backport](camerax-extension-cache-20260908.md) and
[factory stream-sizing repair](camera-stream-sizing-20260908.md). Its 661 source
rows, full Android build, signed archive and eight-image bundle are recorded
in the [v11 package checkpoint](camera-v11-package-20260908.md). That checkpoint's
uninstalled state is historical; the runtime record above follows the separately
approved installation. [V10](camera-v10-install-validation-20260908.md) remains
a preserved predecessor.

V9 (`nezha.393aae12fba9ebe8627cdc38`), v8
(`nezha.f2e3feac321f56f92d2ad7ea`) and v7
(`nezha.c6ad60080698a987390afc40`) remain preserved predecessor bundles.
The [f9e installation](package7-f9e-install-20260906.md),
[a6d installation](package7-feature-successor-install-20260905.md) and
[original Package7 first boot](package7-first-boot-20260905.md) remain historical
device evidence. The [status archive](workspace-status-history-20260905.md)
preserves earlier checkpoints; its pending gates are not current selections.

## Working baseline

| Item | Selected value |
| --- | --- |
| Device/platform | Xiaomi 17 Ultra `nezha`, SM8850 / `canoe`; Evolution X Android 16 QPR2 `bka` / `bp4a`, 4 KiB pages |
| Installed build identity | `nezha.130611bac9232625e0066968` (userdebug, delivery set v11r1) |
| Installed source receipt | 661 rows; `reports/camera-completion-20260907/source-revision-6/source-installed.json`, SHA256 `0f14265c8112793c263b4149a627fd9098fba4f2451073cbfb2881ff41e8466c` |
| Private installed bundle | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v11r1/` |
| Bundle manifest SHA256 | `b6966d7e2071e23de371d74e1e295d4e7c8277465ae8f50f3ee5ac96a5b64d80` |
| Reconciled signed target-files SHA256 | `dbdfefb26e4acdbd2081175412de3935527b5a07dab6b4da312913fdb88c1c02` |
| Signing/reconciliation result | Passed signing, reconciliation and eight-payload verification; receipts in the [package checkpoint](camera-v11-package-20260908.md) |
| Installation observed | Shared Super plus seven A-chain writes acknowledged; no wipe or slot change; normal boot completed in 25.3 s |
| Android runtime observed | `_a`, `sys.boot_completed=1`, `userdebug`, adb UID 0, SELinux `Enforcing`; final cleanup reconfirmed build, slot and policy |
| Camera acceptance observed | Five Xiaomi photos fully decode as Ultra HDR, including main/telephoto 50 MP and telephoto 200 MP; ten warm Aperture JPEG saves (nine Ultra HDR decodes) and three physical RAW captures pass; Xiaomi Pro RAW decodes. Ultra RAW save and audio/video remain incomplete |
| Camera app data | All 512 CE and five DE members unchanged before first launch; active APK and signer unchanged; no claim about all userdata |
| Recovery | TWRP `working76`; preserve its `fix22ZJ-touchfix18` runtime/hardware setup, permissive recovery policy and zero-vibration defaults |
| Normal Android policy | Enforcing source/build baseline; measured current state is recorded above |

The private eight-image bundles and target-files ZIPs are not OTA or TWRP
installers. Preserve the predecessor bundles, original Package7, working76
rescue, stock return inputs, signing key and private build inputs. Artifact
checks, installation results and feature validation are separate evidence.

## Resume development

The selected camera-completion source extends the
[merged feature source](feature-candidates-build-merge-20260906.md),
[explicit userdebug opt-in](build-variant-opt-in-20260906.md),
[QTI camera XML selection fix](camera-xml-selection-20260907.md) and
[HyperOS camera-framework port](camera-framework-port-20260907.md).
`user` remains the default build variant. Userdebug requires its explicit
invocation opt-in, and normal Android SELinux must remain enforcing.

The [native camera hook record](camera-native-hook-20260907.md) preserves the
v8 implementation and installed baseline. The new [completion record](camera-completion-20260907.md)
adds measured v8 capture results and the selected CameraOpt source candidate.
Its original factory verifier and native boot hook remain unchanged. V10
resolves the measured vendor-key discovery failure and saves ordinary Xiaomi
photos. CameraOpt still has explicitly unported methods, including
`reclaimMemoryForCamera`, which is observed during successful captures too.
The installed v11r1 sizing repair resolves the measured telephoto output
truncation and Pro RAW configuration failure. Ultra RAW reaches the app save
step and now exposes a separate missing framework API.

The latest full offline suite passed 4,885 tests in 192.417 seconds plus shell
checks; `make test-current` passed 939 tests in 27.858 seconds during v11
validation. The sizing C++ harness passed 89 assertions across disabled
and enabled configurations with the undefined-behavior sanitizer. The earlier
vendor-key Java harness passed 35 assertions, and the CameraX cache harness
passed 24 with the actual rebuilt classes. The full Android package and final
signed artifact checks are recorded separately in the v11 package record.
The v11 runtime record contains the current measured device evidence.

1. Read [source-lock handling](source-lock.md),
   [device integration](../device/xiaomi/nezha/README.md) and the
   [build host guide](apple-container.md). Run `make apple-status` before resuming
   the existing `twrp-nezha-upstream74-20260829` VM and persistent
   `evolution-nezha-work` ext4 volume. Only one VM may write that volume. Recheck
   disk, OS, architecture, filesystem case sensitivity, manifest and source state
   before a sync or build; do not reset local source selections.
2. Continue from `/work/evolution` and the preserved
   `/work/out/nezha-feature-fixes-20260905-v1` output when preflight passes. Adopt
   a fresh identity and source/artifact records for each change, retain
   intermediates, and let Ninja invalidate changed edges. Use the
   [build/cache lessons](feature-successor-build-lessons-20260905.md); do not
   prune source volumes or delete protected source, output or rollback inputs.
3. Make a focused change supported by the reported behavior. Run
   `make test-current` while iterating, affected module tests when outside that
   selection, and `make test` before completion. Offline tests must not need a
   phone. Record build, package and device evidence separately.
4. Record each observed device result in a focused issue note and update this
   selection when the evidence warrants it. Phone collection and changes need
   the authorized device and scope. The explicit v11r1 approval
   covered its installation, reboot, camera tests and root diagnostics without
   a wipe or slot change. It does not authorize flashing the next bundle.

For recovery changes, use `make recovery-build` and the
[working recovery instructions](../recovery/twrp-working/README.md). This
reproduces the pinned working76 prebuilt derivative, not a fresh runtime source
compilation. TWRP remains the required default recovery; missing or mismatched
inputs must fail. Recovery success with stock companions does not prove the
successor ROM boot chain or OTA behavior.

## Remaining feature work

- **Camera:** V11 passes ordinary Xiaomi photos, main/telephoto 50 MP and
  telephoto 200 MP Ultra HDR, Xiaomi Pro RAW, all ten warm Aperture JPEG saves
  (nine Ultra HDR decodes) and three physical RAW sensors. Front HDR needs neutral-gainmap metadata
  interoperability work. Ultra RAW reaches the missing
  `DngCreator.writeLossLessJpeg` save API and leaves an empty DNG. Implement the
  measured factory compressed-DNG container contract and validate it after
  separately approved successor installation. Useful effect quality and
  sensor-native resolution remain unverified. Preserve the
  [v11 runtime record](camera-v11-install-validation-20260908.md) and
  [v10 predecessor](camera-v10-install-validation-20260908.md).
- **Video and audio:** Early v11 boot logs identify AIDL output-flag and usage
  conversion failures, then a null audio policy manager. The factory mapping
  for output index 19 is legacy `0x40000000`; Bluetooth SCO usage is 19.
  Repair the measured conversions and validate policy/output initialization
  before repeating video. No valid video has been verified.

- **Retained userdata, UDFPS and shade:** Camera apps opened and new JPEGs were written after dismissing the keyguard; retained personal userdata, UDFPS authentication and shade visual acceptance remain unverified.
  The user confirmed fingerprint enrollment on a6d; f9e loaded the measured
  pixel-pitch correction and shade configuration. Their
  [source/build measurements](package7-ui-camera-followup-20260905.md) and
  [installation results](package7-f9e-install-20260906.md) remain preserved.
  Those results do not establish current rendering, authentication or userdata
  behavior. Preserve the approved normal status-bar geometry when refining shade.
- **IMS and telephony:** the Android IMS provider is not integrated. VoLTE,
  VoWiFi and emergency calling remain unverified. The workload classifier also
  remains disabled; selected display, Dolby, haptics, camera-scheduling and
  refresh candidates still need their own measured device results.
- **Other hardware and lifecycle:** track networking, display/touch, audio,
  fingerprint, sensors, storage/encryption, charging and thermals separately.
  OTA/update behavior and stock restoration remain untested. The
  [roadmap](roadmap-20260906.md) retains the private audience, eventual both-slot
  coverage and source-kernel design goal with the prebuilt kernel selectable.

Use [native features](native-features.md), the [documentation index](README.md)
and [build history](build-progress.md) for the underlying research and dated
experiments. The [cleanup record](workspace-cleanup-20260905.md) identifies
retired duplicate expansions; historical replay must rematerialize them from
their retained archives before following an old path.

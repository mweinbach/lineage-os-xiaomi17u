# Current Nezha workspace status

**Installed phone: v12 userdebug (`nezha.0a0b5c6187d711a32aa3e46e`),
slot A, boot completed with SELinux Enforcing.** The approved eight-image
installation completed without a wipe or slot change. All ten warm rear/front
Aperture effect captures fully decode as Ultra HDR. Xiaomi ordinary rear/front,
main and telephoto 50 MP, telephoto 200 MP, Pro RAW and all three physical RAW
sensors also pass their independent decoders. See the
[v12 installation and validation record](camera-v12-install-validation-20260908.md).

UltraRAW now reaches the implemented writer, but the measured capture uses
compressed Bayer format 32; the installed writer supports linear RGB format 15.
Early boot audio diagnostics advance past the previous flag/usage errors and
now reject the factory multiroute device. Audio policy remains null, so video
was not retried. **Full camera acceptance remains incomplete.**

A [successor source candidate](camera-bayer-audio-compat-20260908.md) adds the
measured compressed Bayer path and multiroute/MIHC audio mappings and validators.
Its host image and conversion checks pass; it still needs build and phone validation.

Source revision 9 has 668 rows. Its component/full build, signed archive and
eight-image bundle are recorded in the [v12 package checkpoint](camera-v12-package-20260908.md).
That checkpoint's pending-installation state is historical; the runtime record
above follows the separately approved installation. The installed source includes
the [save/audio compatibility changes](camera-save-audio-compat-20260908.md),
[stream-sizing repair](camera-stream-sizing-20260908.md),
[vendor-key discovery fix](camera-vendor-key-discovery-20260908.md) and
[CameraX cache backport](camerax-extension-cache-20260908.md).
[V11r1](camera-v11-install-validation-20260908.md) and
[v10](camera-v10-install-validation-20260908.md) remain preserved predecessors.

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
| Installed build identity | `nezha.0a0b5c6187d711a32aa3e46e` (userdebug, delivery set v12) |
| Installed source receipt | 668 rows; `reports/camera-completion-20260907/source-revision-9/source-installed.json`, SHA256 `ef5452f69c340ce714849f467c4cfe106e31769bc4c40d286d8e9cb0f4a26245` |
| Private installed bundle | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v12/` |
| Bundle manifest SHA256 | `45e4b0b034807b5f4f21a138f7a04244332fb698d8c661c55dc20367eabd28c8` |
| Reconciled signed target-files SHA256 | `113b87cd7466590580e3a359d50c065bca623b6bdff2e5ad201e916d6ae3abc2` |
| Signing/reconciliation result | Passed signing, reconciliation and eight-payload verification; receipts in the [package checkpoint](camera-v12-package-20260908.md) |
| Installation observed | Shared Super plus seven A-chain writes acknowledged; no wipe or slot change; normal boot completed in 25.5 s |
| Android runtime observed | `_a`, `sys.boot_completed=1`, `userdebug`, adb UID 0, SELinux `Enforcing`; final cleanup reconfirmed build, slot and policy |
| Camera acceptance observed | Five Xiaomi photos fully decode as Ultra HDR, including main/telephoto 50 MP and telephoto 200 MP; all ten warm Aperture JPEG/Ultra HDR decodes, Xiaomi Pro RAW and three physical RAW captures pass. UltraRAW Bayer save and audio/video remain incomplete |
| Camera app data | All 513 CE and five DE members unchanged before first launch; active APK and signer unchanged; no claim about all userdata |
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
The retained v11r1 sizing repair resolves the measured telephoto output
truncation and Pro RAW configuration failure. V12 adds the save APIs; the
traced UltraRAW Bayer format requires a separate container-path repair.

The completed v12 runtime record passes 67 evidence-pin checks. The full
offline suite passes 4,892 tests in 186.830 seconds plus shell checks;
`make test-current` passes 939 tests in 28.347 seconds. The [save/audio source record](camera-save-audio-compat-20260908.md)
contains the focused host behavior and full-image decoder evidence. The actual
component, full ROM, signed archive and eight-image bundle checks are recorded
in the [v12 package record](camera-v12-package-20260908.md). The installed v12
runtime record contains the current measured device evidence.

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
   the authorized device and scope. The explicit v12 approval
   covered its installation, reboot, camera/audio/video tests and root diagnostics without
   a wipe or slot change. It does not authorize flashing the next bundle.

For recovery changes, use `make recovery-build` and the
[working recovery instructions](../recovery/twrp-working/README.md). This
reproduces the pinned working76 prebuilt derivative, not a fresh runtime source
compilation. TWRP remains the required default recovery; missing or mismatched
inputs must fail. Recovery success with stock companions does not prove the
successor ROM boot chain or OTA behavior.

## Remaining feature work

- **Camera:** V12 passes ordinary Xiaomi photos, main/telephoto 50 MP,
  telephoto 200 MP Ultra HDR, Xiaomi Pro RAW, all ten warm Aperture JPEG/Ultra
  HDR cases and three physical RAW sensors. Implement the measured compressed
  Bayer format 32 path for UltraRAW; its two-component lossless JPEG tiles
  require CFA metadata and matching dimensions. Useful effect quality and
  sensor-native resolution remain unverified. Preserve the
  [v12 runtime record](camera-v12-install-validation-20260908.md).
- **Video and audio:** V12 startup advances beyond the prior AIDL output-flag
  and usage errors but rejects the factory multiroute descriptor. Audit its
  factory mapping (`0x20000004`), the MIHC format (`0x40000000`) and their
  validation paths before building the next repair. Audio policy remains null;
  no valid video has been verified.
- **Wallpaper process:** A concurrent crash during the first UltraRAW capture
  reports a missing `ClockProviderPlugin` dependency. Camera process identities
  remain unchanged. This separate failure remains unresolved.

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

# Current Nezha workspace status

**Installed phone: v10 userdebug (`nezha.0c10ad024d3033691a2825cc`),
slot A, boot completed with SELinux Enforcing.** Its approved eight-image
installation completed without a wipe or slot change. Xiaomi Camera now saves
ordinary rear/front photos and a 50 MP main-camera photo with fully decoded
Ultra HDR. Aperture saves all ten rear/front effect cases while switching
modes in one running app process. See the [v10 installation and validation
record](camera-v10-install-validation-20260908.md).

Telephoto 50 MP and 200 MP files are truncated. Xiaomi Pro RAW fails mock-camera
stream configuration, Ultra RAW restarts the provider, and video fails audio
initialization. **Full camera acceptance remains incomplete.** Physical RAW
captures from all three rear sensors independently decode on the host.

The installed v10 source combines the guarded [vendor-key discovery fix](camera-vendor-key-discovery-20260908.md)
and [CameraX cache backport](camerax-extension-cache-20260908.md). Its 659 rows,
full Android build, signed archive and eight-image bundle are recorded in the
[v10 package record](camera-v10-package-20260908.md). The [factory stream-sizing successor](camera-stream-sizing-20260908.md),
`nezha.130611bac9232625e0066968`, has 661 source rows and passes its native
component build, full package, signed archive and eight-image bundle checks.
The corrected [v11r1 package](camera-v11-package-20260908.md) is ready for
separate flash/reboot approval; it is not installed or device-admitted.

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
| Installed build identity | `nezha.0c10ad024d3033691a2825cc` (userdebug, delivery set v10) |
| Installed source receipt | 659 rows; `reports/camera-completion-20260907/source-revision-5/source-installed.json`, SHA256 `657fd91cc57d1df0d46c26fb2940886b8221ed438ec3c577492cfed7b0b2dedb` |
| Private installed bundle | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v10/` |
| Bundle manifest SHA256 | `739acc4ffad8d5eaf3828af4ead90d9387bc646251f5f9f3a74468877ca886f9` |
| Reconciled signed target-files SHA256 | `8963528914383eeed5769af44e7b6c091d76974b66e0bcef066b73803912fa21` |
| Signing/reconciliation result | Passed signing, reconciliation and eight-payload verification; signing receipt SHA256 `94daa3be1f7a5cc598dfc34e799cec31a1555e5b43a429ce95acac72ba346430` |
| Installation observed | Shared Super plus seven A-chain writes acknowledged; no wipe or slot change; normal boot completed in 25.5 s |
| Android runtime observed | `_a`, `sys.boot_completed=1`, `userdebug`, adb UID 0, SELinux `Enforcing`; final cleanup reconfirmed build, slot and policy |
| Camera acceptance observed | Five Xiaomi photos fully decode as Ultra HDR, including 50 MP main; ten warm Aperture effect cases fully decode as Ultra HDR; three physical RAW captures decode. Xiaomi telephoto high resolution, RAW/Ultra RAW and video still fail |
| Camera app data | All 508 CE and five DE members unchanged before first launch; active APK and signer unchanged; no claim about all userdata |
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
The sizing repair in the prepared v11r1 bundle is supported by separate v10
device and factory evidence. Its effects still need measured device validation.

The latest full offline suite passed 4,885 tests in 194.538 seconds plus shell
checks; `make test-current` passed 939 tests in 29.001 seconds after the v11r1
image admission. The sizing C++ harness passed 89 assertions across disabled
and enabled configurations with the undefined-behavior sanitizer. The earlier
vendor-key Java harness passed 35 assertions, and the CameraX cache harness
passed 24 with the actual rebuilt classes. The full Android package and final
signed artifact checks are recorded separately in the v11 package record.
The installed v10 runtime results remain the current measured device evidence.

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
   the authorized device and scope. The explicit v10 approval
   covered its installation, reboot, camera tests and root diagnostics without
   a wipe or slot change. It does not authorize flashing the next bundle.

For recovery changes, use `make recovery-build` and the
[working recovery instructions](../recovery/twrp-working/README.md). This
reproduces the pinned working76 prebuilt derivative, not a fresh runtime source
compilation. TWRP remains the required default recovery; missing or mismatched
inputs must fail. Recovery success with stock companions does not prove the
successor ROM boot chain or OTA behavior.

## Remaining feature work

- **Camera:** V10 establishes ordinary Xiaomi Photo saves, a valid main-camera
  50 MP Ultra HDR output, all ten warm Aperture effect cases and three physical
  RAW captures. Telephoto high-resolution output is truncated; Xiaomi RAW and
  Ultra RAW fail. The measured stock mock-camera/custom-size behavior is
  restored in the prepared v11r1 package; install only after new approval and
  repeat those paths with full output decodes. Useful effect quality and sensor-native
  resolution remain unverified. Preserve the
  [v10 runtime record](camera-v10-install-validation-20260908.md),
  [vendor-key diagnosis](camera-vendor-key-discovery-20260908.md) and
  [earlier capture evidence](camera-completion-20260907.md).
- **Video and audio:** The v10 video attempt cannot create AudioRecord. Audio
  HAL services exist, but the audio policy manager is null and AudioFlinger
  has no hardware threads. Capture startup diagnostics from the next approved
  boot before deciding on a repair. No valid video was saved.

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

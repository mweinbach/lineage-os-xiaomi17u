# Current Nezha workspace status

**Installed phone: v9 userdebug (`nezha.393aae12fba9ebe8627cdc38`),
slot A, boot completed with SELinux Enforcing.** The approved eight-image
installation completed without a wipe or slot change. Xiaomi Camera retained
its app ID and byte-identical app data before first launch, and now passes its
original CameraOpt verifier. Its first rear Photo capture still failed to save.
See the [v9 installation and validation record](camera-v9-install-validation-20260908.md).

The selected development source is `nezha.0c10ad024d3033691a2825cc`, combining
the guarded [vendor-key discovery fix](camera-vendor-key-discovery-20260908.md)
and [CameraX cache backport](camerax-extension-cache-20260908.md). All 659
source inventory rows are verified. The vendor-key framework component passed
on its 658-row predecessor; the combined source's Aperture build passed and full target-files build is in progress.
This successor has not been installed. The installed v9 and prior v8/v7 bundles
remain preserved.

Aperture Ultra HDR and RAW, three rear physical RAW captures, and all 20
platform extension combinations were measured on v8. V9 regression tests have
again saved and decoded Bokeh Ultra HDR and telephoto RAW, and all ten Aperture effect cases (five modes on rear and front) saved and
fully decoded Ultra HDR photos. Xiaomi capture, 50/200 MP, processed Ultra
RAW and full camera acceptance remain **not device-admitted**.

This page selects the current development baseline. Delivery set v8
(`nezha.f2e3feac321f56f92d2ad7ea`) is the retained immediate predecessor; v7
(`nezha.c6ad60080698a987390afc40`) also remains a rollback package. The [f9e installation](package7-f9e-install-20260906.md),
[a6d installation](package7-feature-successor-install-20260905.md) and
[original Package7 first boot](package7-first-boot-20260905.md) remain historical
device evidence. The old [status archive](workspace-status-history-20260905.md)
preserves earlier checkpoints; its pending gates are not current selections.

## Working baseline

| Item | Selected value |
| --- | --- |
| Device/platform | Xiaomi 17 Ultra `nezha`, SM8850 / `canoe`; Evolution X Android 16 QPR2 `bka` / `bp4a`, 4 KiB pages |
| Installed build identity | `nezha.393aae12fba9ebe8627cdc38` (userdebug, delivery set v9) |
| Installed source receipt | 652 rows; `reports/camera-completion-20260907/source-revision-3/source-installed.json`, SHA256 `3136b92e8f651f139e57b21f682f0ad7b1ba0164724cd4749143a1cf2697a2f5` |
| Development source | `nezha.0c10ad024d3033691a2825cc`, 659 rows; `reports/camera-completion-20260907/source-revision-5/source-installed.json`, SHA256 `657fd91cc57d1df0d46c26fb2940886b8221ed438ec3c577492cfed7b0b2dedb`; Aperture component passed; full target-files build in progress |
| Installed v9 bundle | Installed; manifest SHA256 `9db1e3e3e07411f9d884a7c25817e3a164f8e89ddfcf8ad7d2f43dd13c3da958` |
| Private installed bundle | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v9/` |
| Bundle manifest SHA256 | `9db1e3e3e07411f9d884a7c25817e3a164f8e89ddfcf8ad7d2f43dd13c3da958` |
| Reconciled signed target-files SHA256 | `d38d841c96893f24cfa8068101612da2b62bac63a7aa8fa645611dc41ece854e` |
| Signing/reconciliation result | Passed signing, reconciliation and eight-payload verification; signing receipt SHA256 `ad608c216854a086feb6a553410761278b40b943bccff2f4f83aca75e7e43dcf` |
| Installation observed | Shared Super plus seven A-chain writes acknowledged; no wipe or slot change; normal boot completed in 25.3 s |
| Android runtime observed | `_a`, `sys.boot_completed=1`, `userdebug`, adb UID 0, SELinux `Enforcing`; final acceptance snapshot reconfirmed identity/slot/policy |
| Camera acceptance observed | Original CameraOpt verifier true; Xiaomi rear Photo save failed; v9 Bokeh Ultra HDR and telephoto RAW decoded, all ten Aperture effect cases saved and decoded Ultra HDR. Full acceptance incomplete |
| Recovery | TWRP `working76`; preserve its `fix22ZJ-touchfix18` runtime/hardware setup, permissive recovery policy and zero-vibration defaults |
| Normal Android policy | Enforcing source/build baseline; measured current state is recorded above |

The private eight-image bundles and target-files ZIPs are not OTA or TWRP
installers. Preserve the v7 rollback bundle, original Package7 and later booted
predecessors, working76 rescue, stock return inputs, signing key and private
build inputs. An artifact receipt proves only the checks it performed; the
separate installation record supplies authorized writes and device observations.

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
Its original factory verifier and native boot hook remain unchanged. On v9 the
boot callback and original verifier succeed, but the first Xiaomi Photo still
times out. The vendor-key successor addresses a measured metadata-discovery
mismatch. CameraOpt still has explicitly unported methods, including the
`reclaimMemoryForCamera` call observed during that capture.

The latest full offline suite passed 4,881 tests in 190.625 seconds plus shell
checks; `make test-current` passed 939 tests. A separate host Java harness passed
35 behavior assertions for vendor-key filtering and merging; the CameraX
cache harness passed 24 assertions with the actual rebuilt classes. These checks do
not establish the successor Android build or device behavior. V9's component,
full target-files, signed archive and installation evidence remain preserved.

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
   the authorized device and scope. The explicit v9 approval
   covered its installation, reboot, camera tests and root diagnostics without
   a wipe or slot change. It does not authorize flashing the next bundle.

For recovery changes, use `make recovery-build` and the
[working recovery instructions](../recovery/twrp-working/README.md). This
reproduces the pinned working76 prebuilt derivative, not a fresh runtime source
compilation. TWRP remains the required default recovery; missing or mismatched
inputs must fail. Recovery success with stock companions does not prove the
successor ROM boot chain or OTA behavior.

## Remaining feature work

- **Camera:** V8 established rear/front Aperture Ultra HDR and RAW, three rear
  physical RAW captures and 20 platform extension combinations. V9 adds original
  CameraOpt verifier success and further capture regressions, while Xiaomi
  rear Photo still fails to save. The selected vendor-key framework build passed. The CameraX metadata-cache
  backport is staged in the combined source; its app build passed; full target-files build is in progress. Its installation, 50/200 MP, processed Ultra RAW,
  useful effect quality and video remain separate gates. Preserve the
  [v9 runtime record](camera-v9-install-validation-20260908.md),
  [vendor-key diagnosis](camera-vendor-key-discovery-20260908.md) and
  [earlier capture evidence](camera-completion-20260907.md).

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

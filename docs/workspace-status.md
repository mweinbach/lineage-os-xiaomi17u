# Current Nezha workspace status

**Installed phone: v8 userdebug (`nezha.f2e3feac321f56f92d2ad7ea`),
slot A, boot completed with SELinux Enforcing.** Aperture has now saved rear/front
Ultra HDR and RAW photos. Standard RAW from all three rear physical sensors and
all 20 platform extension combinations also passed capture and pixel decoding.
Aperture Bokeh + Ultra HDR is measured separately. Xiaomi Camera capture,
50/200 MP modes and processed Ultra RAW remain unverified; full camera acceptance
is **not device-admitted**. See the [camera completion record](camera-completion-20260907.md).

The selected development source is `nezha.393aae12fba9ebe8627cdc38`, which adds
the guarded CameraOpt service and native compatibility, platform-signed original
Camera input, auxiliary-package selection and JPEG_R default. Its affected
Android component and full target-files builds passed. The transferred archive
passed Camera APK, JAR/API, classpath, native, configuration and normal policy
compilation checks. The final signed archive and eight-image v9 bundle are
verified. Read-only preflight reconfirmed v8, slot A and Enforcing; explicit
v9 flash/reboot approval remains pending. No successor installation is claimed. The earlier product-configuration
and dex-preoptimization failures and their one-file corrections are retained.
The phone remains on v8, with Aperture effects
and RAW off, Ultra HDR on, the original auxiliary property restored and USB
stay-awake off.

This page selects the current development baseline. Delivery set v7
(`nezha.c6ad60080698a987390afc40`) is the retained immediate predecessor and
rollback package. The [f9e installation](package7-f9e-install-20260906.md),
[a6d installation](package7-feature-successor-install-20260905.md) and
[original Package7 first boot](package7-first-boot-20260905.md) remain historical
device evidence. The old [status archive](workspace-status-history-20260905.md)
preserves earlier checkpoints; its pending gates are not current selections.

## Working baseline

| Item | Selected value |
| --- | --- |
| Device/platform | Xiaomi 17 Ultra `nezha`, SM8850 / `canoe`; Evolution X Android 16 QPR2 `bka` / `bp4a`, 4 KiB pages |
| Installed build identity | `nezha.f2e3feac321f56f92d2ad7ea` (userdebug opt-in, delivery set v8); last user-variant install remains `nezha.f9e30611efe01b882f9ed0cb` |
| Installed source receipt | 613 rows; `reports/camera-native-hook-20260907/source-revision-2/source-installed.json`, SHA256 `254b42243742a8b3945fb064156a84a2b0d1e19db1990403f6da4d094fa1f651` |
| Development source | `nezha.393aae12fba9ebe8627cdc38`, 652 inventory rows; `reports/camera-completion-20260907/source-revision-3/source-installed.json`, SHA256 `3136b92e8f651f139e57b21f682f0ad7b1ba0164724cd4749143a1cf2697a2f5`; full build, signed archive and bundle verified; installation approval pending |
| Prepared v9 bundle | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v9/`; manifest SHA256 `9db1e3e3e07411f9d884a7c25817e3a164f8e89ddfcf8ad7d2f43dd13c3da958`; not installed |
| Private installed bundle | `artifacts/flash/nezha/variant-opt-in-userdebug-20260906-v8/` |
| Bundle manifest SHA256 | `2f0d1a033596a3649a674ae6a0359324c48cd3ec3b0234ec0947bf76f43f9631` |
| Reconciled signed target-files SHA256 | `f34b286df2748e4b8f5958c6b905d2d4a3e396cf9b16ede31d34a5a3768e8da1` |
| Signing/reconciliation result | Passed signing, reconciliation and eight-payload verification; signing receipt SHA256 `409f958385fac3e9bedc928fafa92e00ba55f0c5c7ca73de42eabfb38cf0931d` |
| Installation observed | Shared Super plus seven A-chain writes acknowledged; no wipe or slot change; normal boot completed in 25.5 s |
| Android runtime observed | `_a`, `sys.boot_completed=1`, `userdebug`, adb UID 0, SELinux `Enforcing`; final acceptance snapshot reconfirmed identity/slot/policy |
| Camera acceptance observed | v8 native tags and ordinary JPEGs; rear/front Aperture Ultra HDR and RAW; three rear physical RAW captures; 20 extension cases and Aperture Bokeh + Ultra HDR decoded. Xiaomi capture and 50/200 MP remain unverified; not device-admitted |
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
Its original factory verifier and native boot hook remain unchanged; 22 service
methods are explicitly unported. Final artifact signatures passed; installed
package, runtime and high-resolution proof remain separate gates. The current generated product selects the five new
guarded options in addition to `NEZHA_CAMERA_SESSION_INJECT`.

The latest full offline suite passed 4,866 tests in 205.601 seconds plus shell
checks. The final classpath qualification passed 268 affected tests, and
`make test-current` passed 939 tests. The affected Android component build also
passed, with identical 652-row before/after inventories. It compiled and
preoptimized the service, built the native query export, and signed the original
Camera payload with the platform key. Final signed-archive and bundle checks
also passed; installation and device validation remain separate gates.

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
   the authorized device and scope. The September 7 v8 installation request
   covers slot A through the established route, without a wipe or slot change;
   it does not authorize later phone mutations.

For recovery changes, use `make recovery-build` and the
[working recovery instructions](../recovery/twrp-working/README.md). This
reproduces the pinned working76 prebuilt derivative, not a fresh runtime source
compilation. TWRP remains the required default recovery; missing or mismatched
inputs must fail. Recovery success with stock companions does not prove the
successor ROM boot chain or OTA behavior.

## Remaining feature work

- **Camera:** Rear/front Aperture Ultra HDR and RAW, three physical rear RAW captures,
  20 platform extension combinations, and Aperture Bokeh + Ultra HDR are measured
  on v8. The new source integrates the normal CameraOpt verifier, native query
  ABI and platform-signed original Camera input; the component build passed.
  Full target-files build, unsigned artifact and normal policy checks passed;
  the final bundle is verified and installation approval remains pending. Xiaomi
  capture, 50/200 MP, processed Ultra RAW and video
  require their own measured results. The dark extension test scene establishes
  capture and file decoding, not visual quality. Preserve the
  [v7 diagnosis](camera-capture-diagnosis-20260907.md),
  [v8 native hook](camera-native-hook-20260907.md) and
  [current completion record](camera-completion-20260907.md) as separate evidence.

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

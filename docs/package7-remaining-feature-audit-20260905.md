# Package7 remaining feature audit — September 5, 2026

Package7 is the installed, booted Xiaomi 17 Ultra baseline. The current source
successor has separate fixes for fingerprint enrollment, Aperture admission,
status-bar geometry and the original Xiaomi Camera candidate. This audit asks a
different question: **what important integration or qualification work remains
beyond those active fixes?**

The successor's framework-res, SystemUI, services, Aperture and Xiaomi Camera
component build passed under source identity `nezha.a6d3109ae93158c498bb30b0`.
Its full target-files result was still pending at this checkpoint, and it has
not been installed. Component success therefore cannot close any runtime result
below. See the [feature-successor record](package7-feature-successor-20260905.md).

The answer is not that every untested subsystem is missing. Package7's live
service capture contains the core audio, camera, GNSS, NFC, secure-element,
power, power-stats, sensors, thermal and vibrator services, plus many Qualcomm
and Xiaomi extensions. The two strongest additional omissions are the Android
IMS provider stack and the exact-panel luminance/HBM configuration. Other
concrete source gaps affect power accounting, Xiaomi `mi_ext` startup behavior
and OEM charging controls. Most remaining hardware areas need measured device
qualification before a source change is justified.

This was a read-only audit of existing source, artifact records, exact-stock
captures and the Package7 service/display snapshots. It did not run a build,
change the build VM or output tree, query the phone, or authorize a successor
installation.

## Evidence classes

- **Verified omission** means an expected device-specific component or selected
  configuration is absent from Package7 and the current successor source, or a
  required authorization contract is known not to be satisfiable as packaged.
- **Plausible runtime risk** means static or point-in-time evidence identifies a
  credible failure path, but no user-visible failure has been measured.
- **Present but unqualified** means a package, service or HAL is delivered or
  registered, but that fact does not establish hardware behavior or stock
  parity.

These classes must not be promoted merely because a component compiles, a
manifest declares a HAL, or a Binder service appears in one snapshot.

## Prioritized queue

| Priority | Area | Current classification | Why it comes next |
| --- | --- | --- | --- |
| P0 | Android IMS and emergency calling | Verified omission | No Android `ImsService` provider is packaged; VoLTE, VoWiFi and IMS emergency operation cannot work through the intended framework path. |
| P1 | Panel brightness, HBM and automatic brightness | Verified Package7/source omission | The phone uses generic display configuration even though exact-stock calibration for the active physical display is retained. |
| P1 | Xiaomi `mi_ext` startup and effective overlays | Verified loader omission; overlay state untested | The retained partition is not equivalent to executing its init/property contract or applying its Telecom/TeleService/STK overlays. |
| P1 | Power accounting and OEM charging controls | Verified source omissions; behavior untested | No Nezha power profile is authored, and the current property slice intentionally excludes the WLC/reverse-charge client contract. |
| P1 | Camera feature closure | Active narrow fixes; runtime unqualified | Aperture admission does not create a front-camera selector, and Xiaomi Camera packaging does not prove its JNI/algorithm or lens paths. |
| P1 | Daily-driver hardware qualification | Present but unqualified | Radio, audio/mics, suspend, charging, thermals, sensors, haptics, GNSS, NFC, Wi-Fi and Bluetooth still lack controlled Package7/successor results. |
| P2 | CNE/TxPwr and Miracast client integration | Plausible runtime risks | OEM apps cannot receive several requested platform permissions; Sigma/WFD lacks a demonstrated client/start path. |
| P3 | Dormant HyperOS shared libraries | Verified dormant omission | Declared HyperOS runtime libraries have no provider, but no currently selected APK requires them. |

## P0: Android IMS is absent

The native radio stack must not be confused with Android IMS integration.
Package7's live service list contains both Qualcomm IMS-radio HAL instances,
but the retained 480-manifest application audit found no APK advertising
`android.telephony.ims.ImsService`. `ImsServiceEntitlement` is present, but it
provides entitlement support rather than MMTEL service. The current status and
[flash-readiness review](flash-readiness.md) preserve this limitation.

The exact-stock candidate is `org.codeaurora.ims`, but it is not a standalone
APK import. Its known contract includes all of the following:

- `/system_ext/framework/qti-telephony-hidl-wrapper.jar`;
- `/system_ext/framework/qti-telephony-utils.jar`;
- `/product/framework/ims-ext-common.jar`;
- resolved `libimscamera_jni.so` and `libimsmedia_jni.so` Java/native closures;
- a legitimate signer and permission design, including pure-signature requests;
- the `vendor_qtelephony` `seapp` selection, domain and mapping policy;
- an effective Nezha MMTEL provider selector and carrier configuration.

The retained packaged defaults also disable device VoLTE, VT and WFC and leave
the MMTEL, RCS and GBA provider selectors empty. A broad telephony overlay is
therefore not an independent fix: the provider and its complete dependency,
signing and policy slice must exist before enabling the matching capability
resources. A privileged allowlist cannot grant a pure-signature permission,
and blindly re-signing an OEM telephony app would change its trust relationship.

**User impact:** there is no defensible VoLTE, VoWiFi, IMS video-call or IMS
emergency-call claim. Ordinary circuit-switched voice, SMS and mobile data may
still work, but have not been tested and must not be inferred from HAL
registration.

**Focused implementation:** continue from the retained, disabled IMS candidate;
resolve its missing Telephony API semantics, three registered Java libraries,
JNI/ELF closure, signing/permissions, source-owned `vendor_qtelephony` policy,
and Nezha MMTEL selector as one vertical slice. Keep RCS and GBA separate until
a real consumer requires them.

**Promotion gate:** strict app/dexpreopt, required-library, ELF, signer,
permission, SELinux and signed-image-content checks; then, only after an
authorized install, live MMTEL registration, provisioning and ordinary
incoming/outgoing carrier calls. Emergency behavior requires a carrier- or
authority-approved procedure; never place an unsolicited emergency call.

## P1: exact-panel brightness and HBM data are not selected

The existing Package7 display snapshot identifies physical display
`4630946639341352083`, native 1200 x 2608 geometry and advertised
24/30/60/90/120 Hz modes with HDR types. That is useful HAL evidence, but the
same snapshot shows that Android loaded generic `<config.xml>` display data:

- backlight, nits and raw mapping arrays are null;
- the nits-to-backlight spline is null and the brightness mapping is linear;
- HBM data is null;
- lux, thermal-brightness and power-throttling maps are empty;
- framework automatic brightness is unavailable.

This is stronger than a generic “display untested” finding. The exact-stock
product image contains
`/product/etc/displayconfig/display_id_4630946639341352083.xml`, SHA-256
`71949a144918a4e31036806d213aba4d3454c06348d578a9bdf810b9463d9605`.
It matches the live physical-display ID and supplies a nine-point 1–3500-nit
map, HBM transition/lux/thermal parameters and HDR ratio data. The retained
exact-stock framework overlay also sets automatic brightness available and
contains the associated brightness resources.

The [current Nezha overlay](../device/xiaomi/nezha/overlay/README.md) deliberately
copies only the eight status-bar/cutout/corner resources. It does not install
the display-device file or brightness/automatic-brightness resources. Thus the
active geometry correction is valid but incomplete for panel behavior.

**User impact:** automatic brightness remains unavailable in Package7, while
manual brightness may use an uncalibrated curve and Android lacks the retained
HBM policy. Incorrect low-brightness response, outdoor boost, HDR luminance or
thermal interaction is plausible. Advertised refresh/HDR modes do not establish
correct presentation.

**Focused implementation:** add the hash-bound display-device XML at its exact
product path and derive only the compatible framework brightness/automatic-
brightness resources from the exact Nezha overlay. Review names against the
pinned framework before admission. Do not copy the entire Xiaomi overlay or a
different panel's arrays; it also contains unrelated telephony and system
defaults.

**Promotion gate:** resource/path/hash and target-files delivery checks, then
manual and automatic brightness sweeps, minimum-brightness rendering, outdoor
HBM with temperature observation, HDR dataspace/metadata, measured presentation
at each exposed refresh rate, and suspend/AOD entry and exit.

## P1: retained `mi_ext` content is not a startup contract

The Package7 artifact retains a `mi_ext` image, but the static boot audit found
no import of `/mi_ext/etc/init/init.miui.mi_ext.rc` in the retained vendor/ODM
RC set. Standard Android property loading also does not read
`/mi_ext/etc/build.prop`. The historical package review found valid resource
overlays in the partition, but their presence does not prove that OverlayFS
mounts, idmaps or runtime resource selection succeeded.

This matters because those sources contain Xiaomi-specific audio, Bluetooth,
Wi-Fi antenna, thermal/power and other properties, plus overlays targeting
Telecom, TeleService and STK. It does **not** justify executing all HyperOS
initialization inside Evolution: some mounts and properties assume Xiaomi
framework consumers that are intentionally absent.

**User impact:** selected OEM behavior may remain at generic defaults, and
telephony/location/number-verification resources may not resolve as stock did.
No individual symptom is yet proven.

**Focused implementation:** split this into independent measured slices:
required mounts, required properties, and each resource overlay. Reproduce only
the values tied to an observed failure in source-owned product/init
configuration, with duplicate-property, idmap and SELinux checks.

**Promotion gate:** final-image path inspection, then bounded runtime checks of
`/mnt/vendor/mi_ext`, effective properties, OverlayFS mounts, overlay/idmap state
and the exact resolved target resources.

## P1: power accounting and OEM charging controls are incomplete

These are two separate issues.

First, the authored Nezha overlay has no device-specific `power_profile.xml`.
The selected source tree therefore has no reviewed Nezha battery-component
model, even though the device overlay is active. A separate maintainer report
also flags a missing Nezha power profile, but that report is only a lead; exact
values must come from the hash-bound Nezha factory resources, not another ROM or
device. This omission affects Android accounting, not the charger hardware
contract itself.

Second, the current OEM-property restoration record explicitly excludes
`vendor_wlc_app`, private `vendor_wlc_prop`, the `vendor_dpmd` provider and
related system/system-server reads. It therefore records both
`vendor_wlc_private_property_or_app_restored: false` and
`wireless_charging_support_inferred: false` in
[`config/nezha-oem-properties.json`](../config/nezha-oem-properties.json).
Factory and the supplied framework also differ in `power-save-conf.xml`, with
no Nezha reconciliation selected.

Package7's live services do include standard health, power, power-stats and
thermal HALs, Xiaomi MiPower and MiCharge, and the framework power/thermal
services. Those registrations argue against speculative changes to the base
HALs or thermal tables.

**User impact:** BatteryStats/component energy estimates may be wrong. Basic
wired or Qi charging may still work, while stock charge limits, battery-aging
controls, reverse charging, or OEM power coordination may be absent or
different. None of those behaviors has been qualified.

**Focused implementation:** derive an exact Nezha power profile as an isolated
resource change. Separately inventory the factory WLC/PowerKeeper client,
private-property, permissions and sysconfig dependencies before restoring any
charging-control slice. Do not copy another device's power values or bypass
temperature/charge protections.

**Promotion gate:** effective `PowerProfile`/BatteryStats resource inspection;
then certified wired, wireless and reverse-power tests, controlled charging and
temperature curves, charge-limit behavior, suspend/resume and screen-off idle
drain. Stop on abnormal heat.

## P1: the camera fixes still need feature closure

The current Aperture change correctly filters processing-only logical cameras
before CameraX constructs their malformed stream maps. It does not create a
separate front-camera selector: the front physical sensor remains under logical
camera 0. Initialization success would therefore not prove selfie selection,
physical lens switching, focus, stabilization, still capture or video.

The original Xiaomi Camera candidate is a careful packaging result, not a
runtime result. Its APK and uses-library checks pass, but its forty embedded
AArch64 libraries refer to twenty external names, including private vendor/ODM
algorithm and DSP libraries. System-ext placement supplies the intended bundled
native-library namespace; actual JNI loads, symbols, dynamic loads, camera
services and model-specific algorithms remain untested. The OEM app also cannot
receive `CONTROL_DEVICE_STATE`, `CONTROL_DISPLAY_BRIGHTNESS` or `INJECT_EVENTS`
without a legitimate matching signing relationship. The candidate correctly
does not bypass that boundary.

**User impact:** Aperture may start yet expose incomplete front/rear controls or
fail during capture. Xiaomi Camera may install but fail at startup, preview,
capture, lens transitions, video, HDR/LOFIC, Leica, RAW or high-resolution
modes. Permission-dependent preview-brightness or display-state behavior may be
degraded.

**Focused implementation:** qualify Aperture's public logical camera and
logical-to-physical mapping first. For Xiaomi Camera, close linker and service
dependencies in failure order, preserving exact calibration/tuning and signer
boundaries. Do not synthesize camera IDs or invent frame timings.

**Promotion gate:** rear and front still/video output files, lens enumeration,
focus/stabilization/transitions and metadata in Aperture; then Xiaomi Camera
startup/linker/permission state followed by each OEM mode independently.

## P1: registered hardware is still unqualified

The Package7 service snapshot is an important negative check against speculative
“missing HAL” conclusions. It contains 480 registered services, including:

| Area | Package7 registration evidence | What remains unknown |
| --- | --- | --- |
| Radio | Dual-slot Android radio and Qualcomm data/IMS-radio extensions | SIM readiness, registration, data, SMS, circuit-switched voice, DSDS and handover |
| Audio | Core config; default, USB, Bluetooth and remote-submix modules; effect factory; Dolby DMS/DVS | Earpiece/speakers, every mic route, calls, recordings, USB/Bluetooth routing, effects and hotword |
| Display | Composer-facing display config/AIQE and Xiaomi DisplayFeature; modes/HDR advertised | Measured frame pacing, color, HDR, touch, doze/AOD and the brightness gap above |
| Sensors/haptics | Base sensors, Xiaomi CIT/ToF, vibrator HAL and framework vibrator manager | Enumeration quality, calibration, auto-rotate, proximity, ALS, suspend/resume and waveform behavior |
| Power/thermal | Health, power, power-stats, thermal, MiPower and MiCharge | Deep sleep, wake sources, idle drain, charge curves, temperature accuracy and throttling |
| Location | Android `IGnss/default` | Cold/warm fix, assisted/standalone behavior, accuracy, navigation and resume |
| NFC/secure element | NFC HAL, SIM1/SIM2/eSE1 and both OMAPI service names | Tag I/O, permitted secure-element operation and payment certification |

In particular, the live OMAPI and secure-element registrations close the earlier
static question about whether Package7 enabled the framework service. They do
not establish usable secure-element applications or payment eligibility.
Likewise, GNSS and basic audio should not receive source edits until a measured
failure points to a configuration, firmware, policy or routing defect.

The smallest useful successor acceptance pass is therefore behavior-first:
single-SIM/data/SMS/non-emergency voice; reference audio playback and each mic
route; sensor enumeration plus rotation/proximity/ALS; suspend and controlled
charging/thermal observation; GNSS fixes and a short track; owned NFC tag I/O;
and Wi-Fi/Bluetooth association, reconnect, audio and suspend behavior. Record
each result independently rather than promoting “boots” to hardware parity.

## P2: targeted vendor-framework risks

### CneApp and TxPwrAdmin permissions

The retained vendor/ODM authorization audit proves that OEM-signed ordinary
`/vendor/app` packages cannot receive several requested platform
`signature|privileged` permissions. CneApp lacks restricted-network and packet-
keepalive-offload access; TxPwrAdmin lacks precise-phone-state, permission-
observer, media-control and restricted-network access. Some startup failures
are caught, but later keepalive/observer paths may not be.

This is a verified grant gap and only a plausible runtime feature risk. Measure
package grants, `SecurityException`, AVC and relevant CNE/Tx logs during a real
failure before changing packaging. If a required path fails, preserve the OEM
signer and create only the necessary source-owned vendor-privileged delivery and
same-partition allowlist. Do not weaken the platform permission definition or
grant additional access to factory-test applications.

### Miracast, Sigma and QCC

The static framework-provider work packages Sigma/QCC binaries and a guarded
one-byte Miracast audio-interface correction. Package7's live snapshot registers
both QCC AIDL services, so QCC itself must not be reported missing. Sigma remains
disabled/oneshot and no complete WFD client/server start, signing, permission and
narrow Binder/SELinux path has been demonstrated; WFD session services were not
registered in the snapshot. Point-in-time absence does not prove that a lazy
service cannot start.

Treat Miracast as unsupported until an actual sink session proves provider
startup, linker closure, client access and synchronized audio/video. Change the
short QCC init-interface spelling only if a restart trace shows that it is
wrong; the live registrations show that a speculative correction is not
currently justified.

### Missing-at-capture optional services

A comparison of the 155 generated VINTF expectations against the live snapshot
finds optional or specialized services absent at that instant, including
SeaAudio, some QTI display color/demura/post-processing services, sensor
calibration/AON helpers and WFD session services. Core audio, display, sensors
and camera services are present. Disabled, conditional and lazy services may be
absent until a client requests them, so this list is a diagnostic filter, not a
verified omission list. Investigate one only when the corresponding feature
fails or its required start trigger is known.

## P3: dormant HyperOS library declarations

The retained `mi_ext` data declares `hyperos.rustruntime.v3` and `.v4` against
`/system_ext/framework/hyperos.rustruntime.jar`, which is absent. The retained
`miui-uninstall-empty.jar` is also not a usable DEX provider. No currently
selected audited APK requires these names, so there is no demonstrated Package7
impact.

Keep these declarations inactive. If a future Xiaomi/HyperOS application has a
real required-library dependency, import and validate the exact runtime JAR,
XML registration, hidden-API contract and class-loader behavior as part of that
application's own feature slice.

## Evidence anchors

The findings above are traceable to the following retained records. Paths under
`artifacts/`, `evidence/` and `reports/` are ignored/private inputs or captures;
their conclusions and hashes are recorded here without publishing proprietary
payloads or personal device data.

| Evidence | Scope used by this audit |
| --- | --- |
| [Current status](workspace-status.md) and [native feature matrix](native-features.md) | Booted Package7 boundary, known IMS omission and the unrun hardware acceptance matrix |
| `evidence/package7-feature-triage-20260905T155732Z/services.txt` | Package7's 480-service point-in-time registration snapshot |
| `evidence/package7-feature-triage-20260905T155732Z/display.txt` | Physical display ID/modes and generic `DisplayDeviceConfig` brightness/HBM state |
| `artifacts/display-stock-20260905/device-config/receipt.json` and captured file `files/0002` | Readback-verified exact-stock display XML, path, size and SHA-256 |
| `artifacts/display-stock-20260905/product-overlays/` | Exact-stock automatic-brightness and associated framework resources |
| `reports/flash-ready-20260904/deadline-radio/` | 480-manifest IMS absence, retained factory provider and APK/JAR/JNI/signing/policy import contract |
| `reports/flash-ready-20260904/deadline-mi-ext/` | Init/property-loader, overlay and dormant-library review |
| [OEM property contract](../config/nezha-oem-properties.json) | Explicit boundaries around WLC, DPM and private property restoration |
| [Framework providers](framework-providers.md) and `evidence/.../services.txt` | Sigma/WFD static limits plus the corrective live QCC registration result |
| [Xiaomi Camera candidate](xiaomi-camera-product-candidate.md) and [Aperture admission](aperture-camera-admission-20260905.md) | Packaging, linker, signature-permission and logical/physical camera limits |

## Recommended order of work

1. Close the two broadest verified feature gaps in isolated changes: IMS and
   exact-panel display configuration. They have independent inputs and tests.
2. Add an exact Nezha power profile, then inspect `mi_ext` and OEM charging
   contracts only against measured behavior.
3. Finish the already selected camera/fingerprint/geometry successor and its
   signed target-files verification without claiming device success.
4. After separate installation authorization, run the smallest daily-driver
   acceptance matrix above and capture the first failure in each subsystem.
5. Promote only measured failures into source work. Keep certification and
   ecosystem outcomes—emergency calling, payment/DRM/integrity, maximum charging
   rates and stock Xiaomi cloud/AI features—separate from basic HAL success.

This ordering preserves the booted Package7, the working76 rescue path, normal
Android enforcing policy and exact-device provenance. It also avoids replacing
working vendor components merely because their behavior has not yet been tested.

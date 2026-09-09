# Tier 1 source work, September 9, 2026: IMS provider, dim level, QMI daemon

**Source revision 13 (`nezha.81c1b93277a1fa371a3efbb3`) carries the exact-stock
IMS provider with its restored SELinux domain and the corrected display dim
level. It builds, its policy compiles with every neverallow check, the IMS app
passes strict uses-library and dexpreopt, and the MMTEL selector is compiled
into TeleService.** The QMI daemon denial is diagnosed but not fixed in this
revision; the reason is below. Nothing here is a device result: no phone was
touched, and delivery set v15 needs its own installation approval.

## Dim level (done in source)

The [tier 0 session](hardware-ledger-v14-20260909.md) found the display's dim
policy driving the panel to its minimum. The cause was ours: the display
packet generator wrote `config_screenBrightnessDimFloat` as `0` in the
brightness overlay, while the framework default is `0.05`. The generator now
emits `0.05` under contract `nezha-normal-brightness-v2`; on this panel that is
about 26 nits, against about 100 nits for the default level. The calibration
XML is byte-identical to the installed one, so only the overlay and the Make
guard changed. The regenerated packet replaced the guest copy in revision 12,
and the guest build compiles the value into `framework-res`, which the
delivery gates read back with `aapt2`.

## IMS provider (built, not yet installed)

What the earlier plans called five gates reduced to less than expected once the
retained stock evidence was read side by side with the installed build:

| Gate | Finding |
| --- | --- |
| OEM API `TelephonyBaseUtilsStub.isMiuiRom()` | Already in the guest framework source since the feature merge and compiled into v14's `framework.jar` (`classes4.dex`). Nothing to do. |
| `vendor_qtelephony` domain and mapping | The stock system_ext policy declares the type and selects `org.codeaurora.ims` into it; the stock versioned public policy inside vendor.img still declares the type, but the shipped build had no mapping, so the vendor rules keyed to `vendor_qtelephony_202504` applied to nothing. Declaring the type in our system_ext public policy restores the mapping, the same way `vendor_hal_atfwd_hwservice` already coexists with its stock duplicate. |
| Selector and seinfo | The exact factory selector line is now in our system_ext seapp contexts. The Xiaomi signer already maps to `platform` seinfo through the retained vendor MAC permissions; no signer change. |
| Java libraries | Evolution's tree builds `ims-ext-common`, `qti-telephony-utils` and `qti-telephony-hidl-wrapper` from CodeAurora source (`vendor/codeaurora/telephony`, QSSI 16.0.r1-13200). The app's references into them were re-checked with the retained DEX reader: 33 library types, 146 members found, 4 delegated to platform supers, none missing, identical to the result on the stock jars. The in-tree modules and their registration XMLs are selected; the exact-stock DEX copies stay in the private bundle unselected. |
| JNI library | The camera-framework bundle already installs a byte-identical `libimscamera_jni.so`; the app link now requires that module, and `NEZHA_IMS` requires `NEZHA_CAMERA_FRAMEWORK`. |

The restored domain follows the retained stock system_ext policy: an ordinary
platform-signed application domain (`app_domain`, `net_domain`,
`coredomain`), a telephony HAL client, Binder and HwBinder use, and the same
nine service lookups. Two stock pieces are deliberately not restored because
the shipped vendor policy declares neither: membership in
`vendor_hal_atfwd_client` and `vendor_hal_imsvthal_client`, and the `dpmd`
socket grants. If the app needs them, the denials will say so on the phone.

Integration is a guarded product fragment, `device/xiaomi/nezha/ims.mk`,
selected with `NEZHA_IMS := true` in the guest product file. It pins the
private verified-input bundle, the activated module file, the privileged
allowlist, the AUDIO and DIAG group projection and the MMTEL-only TeleService
selector. The fragment is hash-pinned in the device tree generator like the
CameraOpt fragment. Tests cover the fragment guards, the activated module set
against the reviewed templates, the policy text and the pins.

### Build evidence in the guest

| Step | Result |
| --- | --- |
| Revision 12 configuration build | Kati refused: duplicate install rules for the three Java libraries and the JNI library |
| Revision 13 configuration build | passed |
| `selinux_policy` with neverallow and seapp checks, `precompiled_sepolicy` | passed; system_ext policy declares the type, maps it, lists it in `hal_telephony_client`, and carries the selector |
| `ims`, `nezha_ims_lib_imsvt`, the three Java libraries and their XMLs | installed; `ims.odex` and `ims.vdex` present, both JNI links present |
| `TeleService` | `config_ims_mmtel_package` = `org.codeaurora.ims` |

The private inputs came from the retained bundle through
`scripts/ims_inputs.py prepare`, twenty files, 3,899,108 bytes, every hash
matching the contract.

## QMI daemon (diagnosed, deferred)

`vendor_qmipriod` is a QMI data-priority helper that programs iptables chains
for `nicmd`. It starts because `persist.vendor.data.qmipriod_load=1` is
persisted in userdata from HyperOS; no build file on the phone or in the ROM
sets it. On start it is denied `search` on its own data directory, which is
correctly labeled, and exits with status 255; init restarts it every five
seconds. The stock vendor policy has the same four allow rules and no data-file
grant, so the daemon would loop on stock too once that property is set.

A ROM-side fix is one vendor CIL addition, but every vendor policy change goes
through the vendor policy derivation and the policy image rebuild, a cycle this
revision did not open. The immediate remedy is on the device: clearing the
persisted property to `0` stops the loop and is a state change that needs
your authorization. The rule addition is queued for the next vendor policy
image cycle.

## Delivery

Delivery set v15 follows the same host stages as v14: package, transfer,
guest and host gates, package admission and cascade, tests, retained manifest,
signing, signed gates, bundle. The gates additionally require the exact-stock
IMS APK bytes, the twelve native libraries, the registered libraries, the
restored policy and selector in the signed archive, the unchanged calibration
XML and the packet delivery check. Their results are recorded in the
[status page](workspace-status.md) once the bundle exists.

## What this does not prove

No IMS registration, call or SMS has happened; the phone still reports no
SIM. The dim level is measured only as a compiled resource. The lexical library
comparison is not ART resolution, hidden-API policy or class-loader order. The
QMI daemon still loops on the installed v14.

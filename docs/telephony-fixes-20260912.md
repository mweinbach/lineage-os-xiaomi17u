# Telephony, notification and display fixes, September 12, 2026

**The three requested telephony fixes are implemented, and a fourth confirmed
fault in Xiaomi display-device routing has a factory-backed fix.** The earlier
notification-shade patch is also adopted. Source revision 30 is
`nezha.a22a7b1e3294c491ae5d03db`, with 736 recorded input files. The ordinary
SystemUI, telephony, framework-resource and source-policy component build passed;
the full target-files build is in progress. These changes have not been
installed. The connected phone remains on v25, and collection in this work was
read-only.

The [measurement record](../research/telephony-fixes-20260912.json) binds the
private evidence under `reports/telephony-fixes-20260912/`. The
[preceding audit](log-audit-20260912.md) preserves the initial measurements.

## Implemented changes

| Fault | Change | Validation and remaining device test |
| --- | --- | --- |
| VoLTE and carrier video capability disabled | The guarded IMS framework overlay sets `config_device_volte_available` and `config_device_vt_available` to the factory values, both true. | Both are true in the compiled framework APK. Carrier, GBA, provisioning and user gates remain. IMS registration, a call and SMS still need a device test. |
| IWLAN provider not selected | The framework names the retained `vendor.qti.iwlan` network, data and qualified-network services, including their exact classes. | All six strings are in the compiled APK. The retained APK, JNI and AIDL libraries, vendor native-library search path, existing SELinux client role and two live modem services were checked. Service binding remains untested. Fi currently disables WFC in carrier configuration; this does not establish Wi-Fi calling. |
| QMI helper restart loop | An explicit derivative adds two rules for its own log directory and file: directory `search write add_name`, file `create open write getattr`. | Disassembly shows `fopen(log.txt, "w")` failure returns `-1` at startup. The strict retained-user corpus compiles with the addition and has zero permissive domains. Two complete vendor reconstructions match; all 3,910 entries preserve their other data and metadata. The image hash tree verifies. Helper survival and any subsequent denials still require a device run. |
| Display command failures | Restore the exact factory `mi_display` subsystem directory and `/dev/mi_display/*` permissions in ueventd. | Live nodes incorrectly exist at `/dev/disp_feature` and `/dev/disp_log`, with generic labels and 0600 root permissions. The factory library opens the nested path once, then rejects calls before ioctl when its descriptor is invalid. The current vendor policy already grants the display HAL access to the correctly named/labeled nodes. Patch replay matches the expected bytes; correct boot-time nodes and display behavior remain device gates. |
| Missing notification cards | Adopt the reviewed change that clears the lockscreen count when an unlocked shade permits unlimited notifications, even while interaction tracking stays active. | The prior exact-method coroutine harness passes six cases, and the new SystemUI component compiles. The Android multivalent tests and recurrence test on the phone have not run. |

The QMI policy contract is [here](../config/nezha-qmipriod-policy.json), and its
measured vendor image selection is [here](../config/nezha-qmipriod-image.json).
The new unsigned vendor leaf is 959,709,184 bytes, SHA-256
`a721dfa9bdebdf49bef12ebb18595fe47d31892b56cb2730a8845a3cc6efe453`.
Only `/etc/selinux/vendor_sepolicy.cil` changes inside the filesystem; the
original footer geometry and build properties remain. Outer signing is a
separate delivery step.

The active build remains the existing explicit **userdebug** profile. Its normal
metadata selection already uses init's split-policy compilation because the
retained ODM precompiled-policy hashes differ from the framework hashes. The
new image selector requires this same explicit profile; it rejects a user build.
The default user-profile image admission is not extended by this work.

A requested additional strict factory-policy component failed on the current
userdebug corpus. Repeating the exact compilation with the old vendor CIL
produced identical diagnostics, involving existing debug `su` rules. The QMI
addition separately passed strict compilation against the retained complete user
corpus, and the baseline recompile reproduced its original binary hash. No
assertion, enforcement setting, or compiler check was weakened. The ordinary
product component build passed afterward; that does not turn the extra
userdebug/factory strict check into a pass.

## Remaining log findings

The cellular drops originate in modem-reported registration state. Three search
intervals lasted **16.220, 19.129 and 19.033 seconds**, approximately twelve
minutes apart, with no reported rejection cause in those intervals. A separate
brief event at 20:21:28 reported `MS_IDENTITY_CANNOT_BE_DERIVED_BY_NETWORK` and
then `PLMN_NOT_ALLOWED`; LTE registration returned by 20:21:29.983. These are
PHONE0 records. In the same separate event, the modem reports `EMM_DETACHED`
at 20:21:28.119 and a normal data setup succeeds at 20:21:31.258. The retained
RILJ lines contain no radio-power, network-selection, allowed-network-type or
explicit data-deactivation request. The logs do not establish whether
provisioning, network state or modem behavior caused the drops. Verify IMS after
the capability fix before changing radio policy.

The exact retained factory IMS APK resolves the previously unexplained extra
codes: **4001 means packet service attached; 4002 means not attached**.
`ImsRegistrationUtils.convertToPsAttachedCode` maps the service-domain values,
and `ImsRegistrationController.maybeNotifySrvDomainChange` emits them while IMS
is already deregistered. The six PHONE0 callbacks match loss and recovery of
packet service; they do not establish a new SIP rejection or its cause.

Two additional warnings come from handled reporting paths. The analytics
subscription lookup catches a null lookup and returns `INVALID_SUB_ID`; its
error line does not identify which slot failed. The physical-channel parser
logs unknown modem band data and continues without setting a band. Neither
message by itself establishes another broken cellular feature.

The Settings-to-audio Binder denial corresponds to transaction **1599295570**,
`_SPR` / `SYSPROPS_TRANSACTION`. The local SettingsLib `SystemPropPoker` sends this
property-refresh transaction to registered services from an AsyncTask and ignores
remote failures. This is consistent with the warning context and does not establish
an audio playback failure. No new audio HAL permission was added.

The QMI crash loop remains the measured trigger for most of the long-property
errors in the earlier capture. The current libcutils source and the readable
installed library already use the callback property API; a new generic property
reader patch is not justified by these logs alone. No claim is made that the
QMI correction removes every other property warning.

## Validation

Before source adoption, `make test-current` passed 1,132 tests and `make test`
passed all 5,111 tests. The IMS tests, policy derivation/staging tests, exact patch
replays, native policy checks and complete vendor filesystem comparisons supply
the focused evidence above. Hardware and carrier results remain separate from
source, component, filesystem and package validation.

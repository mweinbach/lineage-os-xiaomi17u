# V26 installation and validation, September 12, 2026

**V26 is installed on slot A and boots with SELinux Enforcing.** The eight
approved writes completed without a wipe, data clear or slot change. Android
reported boot complete in **25.3 seconds** as
`nezha.a22a7b1e3294c491ae5d03db`, with ADB remaining shell UID 2000.
Notification cards are visible and user-confirmed; the physical Fi SIM now
registers with IMS over LTE and advertises voice and SMS support.

The [measurement record](../research/v26-install-validation-20260912.json)
binds the private installation and observation evidence. The
[source and package record](telephony-fixes-20260912.md) preserves the preceding
implementation, build and signing checks. Evidence timestamps cross midnight
UTC; the installation and phone observations are September 12 in New York.

## Installation

The user's explicit approval covered the exact v26 bundle, installation to the
existing slot A and reboot while preserving userdata. Fresh Android checks
matched the expected v25 predecessor. Fresh bootloader checks established the
correct device, unlocked state, slot A, no snapshot update and sufficient
physical capacity for every payload. Bundle bytes and the complete AVB chain
were reverified immediately before delivery.

| Item | Verified value |
| --- | --- |
| Source revision | 30, 736 recorded inputs |
| Installed build | `nezha.a22a7b1e3294c491ae5d03db` |
| Predecessor | v25 `nezha.b2c99443fe9e90a4a7954eac` |
| Bundle manifest SHA-256 | `883ead802b615175e31fb572889ada5d502adfb829b659530051303e1ae98225` |
| Signed target-files SHA-256 | `cc1a63491b5ab867dd382baf0a9241544c30d6fe05cc0310211a877c31599207` |
| Payload route | Shared Super, then `dtbo_a`, `init_boot_a`, `vendor_boot_a`, `recovery_a`, `boot_a`, `vbmeta_system_a`, `vbmeta_a` |
| Result | All eight commands acknowledged success; each input unchanged and rehashed after delivery |
| Super transfer | 20 sparse chunks, 512 MiB limit; expanded size 15,300,820,992 bytes |
| Android | Slot A, userdebug, boot completed, SELinux Enforcing, ADB UID 2000 |

No userdata or metadata partition was written. The user subsequently unlocked
the phone and confirmed existing notification cards. This establishes retained
working user state; it is not a byte-for-byte audit of all userdata. No root
transition, security-mode change or additional reboot was performed during
post-installation collection. The private eight-image bundle is not an OTA.

## Measured fixes

| Area | V26 observation | Limit |
| --- | --- | --- |
| IMS / VoLTE | Both compiled device capability booleans resolve true on the phone. `isVolteEnabledByPlatform=true`; the physical-SIM IMS callback reports connected over LTE at 22:58:35.891. MmTel advertises voice and SMS. | A completed call and SMS exchange have not been tested. |
| Video / Wi-Fi calling | The device video capability is restored, while the effective video and WFC platform gates remain false under the current configuration. | Device capability alone does not override carrier or user gates. Neither service is claimed working. |
| IWLAN | All six selectors resolve to the retained `vendor.qti.iwlan` classes. Network, data and qualified-network services each have live telephony bindings for both slots. | Service binding does not establish Wi-Fi calling. |
| QMI helper | Corrected vendor CIL hash is installed; the process runs under `vendor_qmipriod`. All 31 samples across 900.01 seconds retain the same PID, and final process elapsed time is 19:29. | This establishes bounded survival after boot. |
| Xiaomi display | `/dev/mi_display/disp_feature` and `disp_log` are created as 0666, root:graphics, with the existing vendor display feature/log labels. The installed ueventd file matches the candidate hash. Feature 20 calls appear without the earlier invalid-descriptor errors. | Brightness, refresh-rate and other display features were not separately exercised. |
| Notification cards | Screenshot shows a full notification card; the user confirms cards work. The unlocked shade reports unlimited notifications and `maxDisplayedNotifications=-1`. | The capture has interaction=false. The exact stale-interaction branch was tested in the source harness; a live download progress notification and long-term recurrence remain untested. |
| Audio policy | The live policy retains 15 volume groups and 75 populated device-category curves. | This session did not perform a listening or mute test. |

The installed vendor policy SHA-256 is
`7c1e7d01681b90a11f85ddd7f196143701ee1fcc580307201b16d75f95c49f54`;
`/system/etc/ueventd.rc` is
`e93c71810440010b90f6929ea905bc18be91ef146a2436d5a8fd154a4b27c96a`.
Both match the verified source-revision-30 package.

## Bounded stability observation

The monitor completed **31 samples over 900.01 seconds**, with one unchanged
boot identity and QMI PID. The final process elapsed time is **19 minutes,
29 seconds**. The collected logs contain no QMI-domain denial or helper exit,
no `flags_health_check` cascade, no matched legacy property-reader error and no
recurrence of the earlier display invalid-parameter failure. No Java/native
fatal crash or ANR appears in the retained snapshots.

The final radio buffer retains **22:58:13.097 through 23:17:39.348**. After IMS
connected at 22:58:35.891, it contains no later IMS disconnect callback, no
PHONE0 service loss and none of the earlier `EMM_DETACHED`,
`MS_IDENTITY_CANNOT_BE_DERIVED_BY_NETWORK` or `PLMN_NOT_ALLOWED` messages. This
spans the previously observed twelve-minute cellular cycle. The earlier drops
did not recur in this window; their cause and long-term reliability are not
established by one boot and a bounded observation.

The Android shell cannot read `init.svc.vendor.qmipriod`: `getprop` returns an
empty value and emits an access-denied warning. That is a collector limitation,
not a stopped daemon. Process IDs, process elapsed time and SELinux labels are
available without root and provide the survival evidence. The initial `ps`
column selection was unsupported; subsequent collection uses `ps -AZ`. The
initial Qualcomm IMS service dump supplies no private service dump, so IMS
results use the telephony dump and registration callbacks.

## Remaining error investigation

**DeviceLock has a measured package-selection mismatch.** The effective
`config_systemFinancedDeviceController` resolves through
`/product/overlay/GoogleConfigOverlay.apk` to
`com.google.android.devicelockcontroller`. The installed DeviceLock APEX contains
`com.android.devicelockcontroller`. The financed-device-controller role has no
holder. The app requests `MANAGE_DEVICE_POLICY_APPS_CONTROL`, but it is not
granted; its boot/unlock policy call fails with the matching SecurityException.

The local DeviceLock source at
`f93460221d41b5b82dc3de2576e8a64c816d83af` shows that even the unprovisioned path
tries to protect the controller package using `setUserControlDisabledPackages`.
The PermissionController role definition grants that permission to the selected
controller. These facts explain the logged failure. Resolving the product's
DeviceLock package/feature selection is separate work; this installation did
not grant device-management powers or change its provisioning state.

Other startup errors include unavailable radio-interface methods, optional DSP
and driver probes, application hidden-API probes, and denials involving existing
vendor services. These require a demonstrated affected operation before a new
permission or driver change is justified. The earlier cellular attachment-code
analysis remains in the [source investigation](telephony-fixes-20260912.md).

## Workspace verification

After installation and the final status update, `make test` passed **5,111 tests in 209.419 seconds** and the
remaining Makefile checks completed successfully. `make test-current` passed
**1,132 tests in 32.377 seconds**. The historical
camera-delivery assertion now preserves its recorded successor without requiring
that older build to remain the current installation. The preceding source delivery
also passed `make test-current`, the full Android target-files build, all 46
unsigned and 45 signed archive checks, and the final bundle/AVB verification.
Documentation and evidence-integrity checks are recorded separately from these
source and package checks.

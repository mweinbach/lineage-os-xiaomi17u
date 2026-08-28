# TWRP upstream baseline for Nezha

The Android 16 TWRP test tree is the current source candidate for the separate
Nezha recovery. This review identifies its revisions and integration requirements;
it does not establish that the recovery boots, decrypts data, or can restore the
phone. The existing [recovery plan](recovery-plan.md) remains the source of stock
layout and prior community-tree findings. The [upstream record](../research/twrp-upstream.json)
contains exact branch heads and observations checked on 2026-08-27 local time
(2026-08-28 UTC).

The official [Xiaomi device index](https://twrp.me/Devices/Xiaomi/) did not list
Nezha, and a GitHub repository search for `nezha` in TeamWin returned no matches.
These are bounded observations, not proof that no port exists. The
[official compilation guide](https://twrp.me/faq/howtocompiletwrp.html) still points
to its Android 12.1+ manifest, while the official repositories also expose newer
14 and 14.1 branches. An available branch is not a Nezha compatibility result.

| Source | Branch | Verified commit |
| --- | --- | --- |
| [Official minimal manifest](https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp) | `twrp-12.1` | `6dc117d9cbd08430daa16db2013560e1c4017fa8` |
| [Newer official minimal manifest](https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp) | `twrp-14.1` | `cb31ddec08f495d3f70631b22140642d0045ba0d` |
| [Official recovery](https://github.com/TeamWin/android_bootable_recovery) | `android-14.1` | `426b747737e7ce9e9e17da5b4d2ba883f296aec7` |
| [Experimental Android 16 manifest](https://github.com/TWRP-Test/platform_manifest_twrp_aosp) | `twrp-16.0` | `d2188a9345857fb078c391e8cb3e259a21e941e5` |
| [Experimental Android 16 recovery](https://github.com/TWRP-Test/android_bootable_recovery) | `twrp-16.0` | `b70f8e998b302381ecefc6e7f46df1614bd61afc` |

All listed revisions and all 36 GitHub project overrides in the record were
checked with `git ls-remote`. The experimental manifest defaults to AOSP
`android-16.0.0_r1`, includes `twrp-default.xml`, then includes
`remove-minimal.xml`. Its 990 baseline projects become 392 after removing 26
baseline entries, adding 36 fork/support entries, and removing 608 unused entries.
The completed Linux sync selects **391** of those projects: Repo omits only
`prebuilts/bazel/darwin-x86_64`, whose groups are
`notdefault,platform-darwin,darwin,pdk`. Every other expanded project path is
present. The source configuration records that exact exclusion; the count is
not relaxed to accept arbitrary missing projects.
The final removals select projects by **path**, not by
name. There are no nested project elements or relative remote fetch URLs in
the reviewed manifests. File hashes and Git blob identifiers are recorded.
[Pinned manifest files](https://github.com/TWRP-Test/platform_manifest_twrp_aosp/tree/d2188a9345857fb078c391e8cb3e259a21e941e5).

The 356 retained AOSP projects still use a tag in this research record; the
remaining 36 use the recorded fork commits. This is not a complete transitive
commit lock. Before a build is admitted, a separate source receipt must bind
every project's actual commit, remote and local patch state. A transplanted
`bootable/recovery` folder in the Evolution checkout would omit the selected
build, Soong, init, policy, storage and vendor integration forks.

The [upstream README](https://github.com/TWRP-Test/platform_manifest_twrp_aosp/blob/d2188a9345857fb078c391e8cb3e259a21e941e5/README.md)
uses release configuration `bp2a` and identifies `recoveryimage` as the target
for a dedicated recovery partition. Its `eng` example and
`ALLOW_MISSING_DEPENDENCIES=true` instruction are not adopted here. The local
target can use `twrp_nezha-bp2a-userdebug` with strict dependency and policy
validation; selecting a build variant does not by itself establish safe ADB.

The [pinned build rules](https://github.com/TWRP-Test/android_build/blob/3b5b2b43b8e2200ef92b7b814a84c8dde8b74121/core/Makefile)
support a dedicated recovery with no embedded kernel. The corresponding
[board selection rules](https://github.com/TWRP-Test/android_build/blob/3b5b2b43b8e2200ef92b7b814a84c8dde8b74121/core/board_config.mk)
require explicit `PRODUCT_BUILD_RECOVERY_IMAGE := true` when
`TARGET_NO_KERNEL := true`; automatic selection otherwise skips recovery.
`BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE := true` omits the kernel and its
default command line. Use `BOARD_RECOVERY_MKBOOTIMG_ARGS` for header v4 and any
explicit measured stock command line. Preserve LZ4 and the package-derived
104,857,600-byte recovery bound. Do not move recovery into `vendor_boot` or
substitute another device's boot arrangement. The actual phone's geometry
remains unmeasured, and the kernel and required vendor ramdisk remain external
dependencies. This does not demonstrate that `fastboot boot` accepts the image.

The current upstream sources require several explicit safeguards:

| Finding | Required treatment |
| --- | --- |
| [AOSP recovery adbd](https://android.googlesource.com/platform/packages/modules/adb/+/ce023afef190b0cea7f8939e9dd5ee3ee79b137b/daemon/main.cpp) sets `auth_required=false` on unlocked or debuggable devices. | Patch and verify the daemon's recovery authentication path. `ro.adb.secure=1` alone is ineffective, including on an unlocked `user` build. Review trade-in-mode exceptions too. |
| [TWRP common product config](https://github.com/TWRP-Test/android_vendor_twrp/blob/b53296dfc420ce65fffe712de380d5abf6c4c2f1/config/common.mk) adds rescue-disabling properties, a Lineage certificate and a broad package bundle. | A minimal product can omit this include; review any properties, trust keys and tools subsequently added. `ro.build.selinux=1` is not proof of enforcement. |
| [TWRP Soong config](https://github.com/TWRP-Test/android_vendor_twrp/blob/b53296dfc420ce65fffe712de380d5abf6c4c2f1/config/BoardConfigSoong.mk) enables MTP by default and makes crypto also enable FBE and property replacement. | Explicitly exclude MTP. Keep crypto, OMAPI, property replacement, fastbootd, repacking and network features outside the initial recovery contract. |
| [Init enforcement](https://github.com/TWRP-Test/android_system_core/blob/9292e0ddea6c1e8ff95abc8d3fedd6dd0c722f31/init/selinux.cpp) defaults to enforcing but debuggable builds can honor a permissive boot property. | Retain enforcing boot properties, checked policy, neverallow validation and no permissive domains. Do not mask failures with future security-patch dates. |
| [The debug `su` policy](https://github.com/TWRP-Test/android_system_sepolicy/blob/f0270686ee017f4de42e1032aca7527031bcc484/private/su.te) explicitly declares `su` permissive. | Remove that declaration in the reviewed patch queue and require an empty, unfiltered `sepolicy-analyze permissive` result on the built recovery policy. |
| [Vendor envsetup](https://github.com/TWRP-Test/android_vendor_twrp/blob/b53296dfc420ce65fffe712de380d5abf6c4c2f1/build/envsetup.sh) truncates a VTS makefile when sourced. | Remove or explicitly account for that mutation in the reviewed patch queue. Do not claim an untouched source tree after sourcing it unmodified. |

These checks are necessary but not a complete runtime audit. In particular,
an empty recovery fstab does not prevent startup bootloader-message writes,
pending recovery/ORS commands or later fstab discovery. Those paths must be
blocked before a separately authorized device test. Do not describe a compiled
diagnostic image as read-only merely because no persistent mounts are listed.

The [selected first-stage init](https://github.com/TWRP-Test/android_system_core/blob/9292e0ddea6c1e8ff95abc8d3fedd6dd0c722f31/init/first_stage_init.cpp)
selects `modules.load.recovery` in recovery mode, falling back to `modules.load`
only when the mode-specific file cannot be `stat`ed. It loads modules from
`/lib/modules` before deciding whether to mount normal Android partitions.
This matches the reviewed vendor-ramdisk loader contract; adding a second
full module-load sequence later in an RC file is not justified. Matching source
logic does not prove module signature admission, successful loading or touch.

The Android 16 baseline is useful for newer secure-service interfaces, but it
does not prove Nezha decryption. Its README calls out Weaver, StrongBox and
OMAPI, and explicitly excludes FDE. TeamWin distinguishes platform crypto work
from [device-specific firmware and blob integration](https://twrp.me/faq/encryptionsupport.html).
Keep initial logs on temporary storage without automatically mounting or
decrypting `/data` or `/metadata`.

Later encryption work must retain the measured filesystem and encryption
format, actual OS/vendor/boot patch levels, and the phone's KeyMint, Gatekeeper,
Weaver and secure-element routing. Metadata decryption precedes access to the
filesystem; credential-encrypted data is a separate stage. The normal and
recovery stock fstabs disagree and must be reconciled, not copied wholesale.
[AOSP FBE](https://source.android.com/docs/security/features/encryption/file-based)
and [metadata encryption](https://source.android.com/docs/security/features/encryption/metadata)
describe these separate contracts. Current AOSP documentation distinguishes
Android 17's `wrappedkey` from Android 11+'s legacy `wrappedkey_v0`, and requires
already-launched devices to retain `wrappedkey_v0` for compatibility.
[Hardware-wrapped keys](https://source.android.com/docs/security/features/encryption/hw-wrapped-keys).
No credential handling, persistent key upgrades, successful data decryption,
backup coverage or restore capability was demonstrated by this review.

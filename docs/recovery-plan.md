# Nezha recovery plan

TWRP is now an independent bring-up track, at the user's request; it does not
wait for a complete Evolution X ROM. Follow the [active TWRP work](twrp-bringup.md)
for source, build and test status. The observations and machine-readable record
below preserve the earlier review checkpoint, before a TWRP target existed.

A tested recovery can help restore an unbootable Android system,
but **it cannot prevent bootloader corruption or start without a working boot
chain**. Nezha's recovery is not self-contained: the captured image has no
kernel. Keeping recovery intact therefore does not protect against damage to
the bootloader, required boot images, partition tables or hardware-backed
security state. This follows the [AOSP bootloader responsibilities](https://source.android.com/docs/core/architecture/bootloader)
and [dedicated A/B recovery design](https://source.android.com/docs/core/architecture/partitions/generic-boot).

This is an engineering plan, not a recovery release. At the review checkpoint,
no TWRP target had been registered and no recovery build or device test had
passed. No phone change is authorized by that review. The existing Evolution source and output
must stay intact. The [machine-readable record](../research/recovery-plan.json)
separates source observations, factory-package evidence and future tests.

The new China fastboot package has SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
Its existing extraction, AOSP boot inspection and full selected AVB-chain
receipts were checked again for this review; no firmware was re-extracted or
executed. The selected chain and Qtvm check pass without verification bypasses.
The supplied archive's origin and an independent OEM trust root remain
unverified. That result is separate from the modified Xiaomi.eu package's
retained AVB failures.

| Image | Verified package contents | Recovery requirement |
| --- | --- | --- |
| `boot` | Header v4; 39,963,136-byte kernel; no ramdisk | Keep the matching kernel available through the boot chain |
| `init_boot` | Header v4; generic ramdisk; no kernel | Preserve the generic first-stage init dependency |
| `vendor_boot` | Header v4; 4 KiB page field; vendor ramdisk and DTBs | Preserve Nezha's DT selection and required module dependencies |
| `recovery` | Header v4; 30,407,261-byte compressed ramdisk; no kernel | Build a dedicated recovery ramdisk, not a replacement vendor_boot layout |

The recovery image is 104,857,600 bytes (100 MiB), with SHA256
`a6f2c77608026fcfe6221e5191c501b0ac880658f76c55231879ed198ce8a0f9`.
Image length is not a live partition measurement. The separately checked
package GPT, rawprogram and partition XML agree on 100 MiB for both recovery
slots, 96 MiB each for boot/vendor_boot, 8 MiB for init_boot, and 32 MiB for
DTBO. The DTBO file is only 22 MiB, demonstrating why file lengths cannot
substitute for partition extents. These are package-derived limits, not a
measurement of this phone. GPT growth placeholders remain unresolved; no
flashable GPT layout is admitted. The independent analysis receipts are
bound in the recovery record.
The recorded recovery chain has rollback location 1 and index 1;
`vbmeta_system` uses location 2. Keep those roles distinct from the values in
a generic recovery tree. The phone's stored rollback counters and actual
bootloader authorization remain unresolved.

The later [factory ramdisk comparison](factory-boot-contract.md) confirms that
the captured recovery ramdisk and its payloads match the earlier input. Its
two recovery fstabs still contain ext4 and legacy ICE/wrapped-key settings
that differ from the normal EROFS/FBE layout; they are evidence to reconcile,
not a ready-to-use TWRP decryption configuration. The
[module-provider audit](module-provider-audit.md) supplies matching captured
CRC candidates. The later [boot-stage audit](module-stage-closure.md) accounts
for the recovery list's 435 rows and 424 unique requested modules. Its hard
dependency closure contains 426 modules, adding `hdcp_qseecom_dlkm` and
`smmu_proxy_dlkm`; all 20,345 recorded CRC expectations have matching kernel
or local predecessor candidates, with no missing hard path or dependency
cycle. One soft dependency names the absent `phy-msm-snps-hs`; that alone does
not establish a required-import failure, and no substitute was invented.
This uses the captured inputs and pinned loader semantics. The stock loader's
source identity, successful loading, signature admission and TWRP behavior
remain unverified.

The recovery build should retain the separate A/B recovery arrangement,
header v4, LZ4 ramdisk format and exclusion of the kernel from recovery.
It needs a reviewed module closure for display, touch, storage, USB and
security services. Preserve the [ZRAM provider and loader contract](zram-module-plan.md):
vendor and GKI modules with the same basename are not interchangeable. Do not
assume a ramdisk-only recovery image supports temporary boot, or infer a
safe test procedure from another device's instructions.

Two first-hand community trees are useful, but neither is admitted wholesale:

| Reference | Pinned revision | What to retain as research |
| --- | --- | --- |
| [MissMyTime SM8850](https://github.com/MissMyTime/twrp_device_sm8850/tree/17525a886e43c26c350fb3db9b260c55e4360dc8) | `17525a886e43c26c350fb3db9b260c55e4360dc8` | Nezha-specific ramdisk layout, secure-element routing, manual decryption and USB work |
| [antocorvo3000 Xiaomi 17 series](https://github.com/antocorvo3000/twrp-xiaomi-17-series/tree/4a35185d43782b4dd460a7f456d674c0976c0859) | `4a35185d43782b4dd460a7f456d674c0976c0859` | Reported boot/touch results and a synthetic-password authentication fix to review independently |

MissMyTime's [Nezha BoardConfig](https://github.com/MissMyTime/twrp_device_sm8850/blob/17525a886e43c26c350fb3db9b260c55e4360dc8/device/xiaomi/nezha/BoardConfig.mk)
matches the dedicated recovery layout, but relaxes missing-dependency,
duplicate-rule, ELF-copy and plugin checks. Its included
[recovery policy](https://github.com/MissMyTime/twrp_device_sm8850/blob/17525a886e43c26c350fb3db9b260c55e4360dc8/device/xiaomi/nezha/sepolicy/recovery.te)
declares permissive recovery and vibrator domains. BoardConfig also uses a
fake platform version and security patch dates in 2099. These settings are
not acceptable inputs to this project. The device's
[vold work](https://github.com/MissMyTime/twrp_device_sm8850/blob/17525a886e43c26c350fb3db9b260c55e4360dc8/patches/nezha/README.md)
addresses installed-system KeyMint parameters and persistent key upgrades;
its safety and correctness need independent tests before any port. One build
guide sentence puts the kernel in vendor_boot, contradicting that tree's own
Nezha BoardConfig and the stock headers above; use the measured arrangement.

The other tree's [active board settings](https://github.com/antocorvo3000/twrp-xiaomi-17-series/blob/4a35185d43782b4dd460a7f456d674c0976c0859/twrp_device_xiaomi_nezha/BoardConfig.mk)
retain SM8750 identity, disable a separate recovery target, move recovery
resources into vendor_boot, and assign `vbmeta_system` rollback location 1.
Its init fstab labels metadata as ext4. Those are not Nezha defaults to copy.
The maintainer [reports boot and touch but unconfirmed decryption](https://github.com/antocorvo3000/twrp-xiaomi-17-series/blob/4a35185d43782b4dd460a7f456d674c0976c0859/twrp_device_xiaomi_nezha/README.md),
with StrongBox removed and Gatekeeper switched away from SPU operation.
Neither change establishes the correct security route for this phone. The
AES-GCM patch adds authentication-result checks; evaluate it against the
chosen source base with valid, truncated and corrupted synthetic fixtures,
without using a real user's keys or disabling authentication.

TeamWin's [compilation guide](https://twrp.me/faq/howtocompiletwrp.html) still
links its Android 12.1+ minimal manifest. That manifest is pinned here at
`6dc117d9cbd08430daa16db2013560e1c4017fa8`; official recovery source is
`5c3d206a5eeb3d446bcda8248a405a4b278bab5c` on `android-12.1`.
MissMyTime instead documents the experimental
[TWRP-Test Android 16 manifest](https://github.com/TWRP-Test/platform_manifest_twrp_aosp/tree/d2188a9345857fb078c391e8cb3e259a21e941e5),
pinned at `d2188a9345857fb078c391e8cb3e259a21e941e5`. These are different
source bases. Their full transitive project revisions have not been resolved
or synced here. Nezha was not listed in [TeamWin's Xiaomi device index](https://twrp.me/Devices/Xiaomi/)
when inspected on 2026-08-27; a community claim is not an official support or
local compatibility result.

Use the Nezha-specific layout as a reference for an isolated recovery product
and a small reviewed patch queue. Do not run either repository's setup,
patching or installer scripts in the Evolution checkout. Resolve the chosen
manifest completely before building, with its own source and output paths,
the existing host checks and no concurrent writer on the ext4 volume.

The work proceeds in these stages:

| Stage | Required result before proceeding |
| --- | --- |
| Independent local recovery integration | Factory-derived fstab and size constraints; exact boot/module inputs; strict build, ELF, VINTF, SELinux and AVB checks; inspected recovery output |
| Separately authorized boot test | Verified boot chain and return plan; display/touch and USB/ADB tests; no automatic data decrypt/format, slot changes or snapshot mutation |
| Separately authorized encrypted-storage test | Correct secure services, metadata and CE/DE access; credential failure stays a failure; no persistent key upgrade; Android remains able to access its data afterward |
| Separately authorized rescue validation | Proven backup/restore scope, internal-media coverage, slot/OTA behavior and stock-return procedure |

Encrypted data requires more than a working UI. Reconcile the new factory
fstab instead of importing the modified Xiaomi.eu fstab's missing verification
flags. Confirm the factory filesystem and encryption formats; the earlier
captured baseline uses F2FS and wrapped keys. Preserve the confirmed formats,
real OS/vendor/boot patch levels and the correct KeyMint, Gatekeeper, Weaver
and secure-element dependencies. Metadata decryption must precede filesystem
access; credential-encrypted data is a separate stage. Do not select a route
from an unrelated Xiaomi model or a masked Android property. See the
[AOSP FBE requirements](https://source.android.com/docs/security/features/encryption/file-based),
[metadata encryption requirements](https://source.android.com/docs/security/features/encryption/metadata)
and [hardware-wrapped key design](https://source.android.com/docs/security/features/encryption/hw-wrapped-keys).
TeamWin also explicitly treats [device-specific decryption](https://twrp.me/faq/encryptionsupport.html)
as separate integration work.

Virtual A/B does not provide two independent complete super images. Recovery
must understand the actual snapshot/merge state and boot-control interface;
an initial smoke test must not merge snapshots or alter slots automatically.
[AOSP describes the shared base and snapshot arrangement](https://source.android.com/docs/core/ota/virtual_ab).
Keep bootloader firmware, GPT and persistent-security partitions outside
initial write support. Recovery cannot undo every hardware-backed state change.

Backups must live off the phone and have verified coverage and hashes.
TeamWin's ordinary data backup [excludes internal media](https://twrp.me/faq/backupexclusions.html),
so photos and other `/data/media` content need separate coverage. A backup
file is not a demonstrated restore path, and a spare slot is not proven
bootable merely because it exists. Do not promise protection until the
appropriate restore tests are separately authorized and pass.

The private review receipt is
`artifacts/source-contracts/nezha-recovery-plan-v1/receipt.json`, SHA256
`f07607300c58473b9cb698e26c40859e23a785623f1f5ebdeb89a397defa33d9`.
It binds 45 text files from five pinned repositories, ten primary web pages
and the checked stock-header observations. All source-file Git blob hashes
and SHA256 hashes matched. This bounded review did not download or execute
the repositories' prebuilt binaries, review every source file, build TWRP,
or access the phone or guest.

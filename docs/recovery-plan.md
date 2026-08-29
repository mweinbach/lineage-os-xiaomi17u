# Nezha recovery plan

**TWRP is the selected default recovery for Evolution X.** The current
`working76` baseline was tested on the Xiaomi 17 Ultra with visible UI,
responsive touch, root USB ADB and private recovery/kernel log capture. It is a verified
adaptation of the supplied `fix22ZJ-touchfix18` prebuilt, not a new source build
or proof of Evolution X ROM installation, target-files or OTA compatibility.
Use the [current TWRP guide](twrp-bringup.md) and its
[working-image evidence](../research/twrp-working-defaults.json) for the active
identity and local workflow.

Selecting a default recovery does not authorize a phone operation. Reboot,
flash, unlock/relock, wipe and slot changes require an explicit user request,
fresh identification of the authorized physical device, and a reviewed return
path. Local building and staging do not perform those actions.

## Boot-chain and security boundaries

A recovery **cannot prevent bootloader corruption** or start without a working
boot chain. Nezha's dedicated recovery has no kernel; it relies on the matching
`boot` kernel and the required vendor ramdisk, DTBs, modules and firmware.
Preserve the [factory boot contract](factory-boot-contract.md), not another
phone's layout or a community BoardConfig's incompatible settings.

| Component | Required arrangement |
| --- | --- |
| `boot` | Matching stock kernel; the measured input kernel is 39,963,136 bytes |
| `init_boot` | Separate generic ramdisk; do not overwrite it to install this recovery |
| `vendor_boot` | Matching vendor ramdisk and DTBs; do not move recovery into it |
| `recovery_a`, `recovery_b` | Dedicated kernel-free header-v4 recovery, 100 MiB per slot; working76 was tested on `recovery_a` only |

The [module-stage audit](module-stage-closure.md) records the captured recovery
closure and CRC candidates. Static module matching is not proof that a new
kernel, driver set or full ROM works. The working derivative preserves its
prebuilt runtime, drivers, firmware and policy while changing only two text
files.

Working76 intentionally starts **recovery** in global permissive mode, as
explicitly authorized for bring-up. Keep SELinux present and denial logging
available; restoring recovery enforcement is a separate gate. Normal Android
must remain enforcing. Root USB ADB and an empty TCP ADB property do not prove
host authentication or the absence of every network listener. Trust the
connected host and keep recovery access physically controlled.

Its local development-key AVB verification uses recovery rollback index `1`,
location `1` and flags `0`; it does not establish OEM trust. Do not substitute
the separate `vbmeta_system` location `2`, bypass verification, alter rollback
roles, or relock a phone on the assumption that local signing is OEM approval.

## Remaining acceptance gates

| Gate | Evidence still required |
| --- | --- |
| Recovery enforcement | Review actual denials and loaded policy, then verify the necessary recovery functions with enforcement restored |
| Encrypted storage | Correct factory filesystem/FBE and metadata handling, KeyMint/Gatekeeper/Weaver dependencies, credential failure behavior and continued Android access |
| Persistence and stock return | Another recovery reboot and an Android-to-recovery round trip; retain the exact installed image and readbacks |
| Backup and restore | Off-device hashes, explicit coverage including `/data/media`, and a separately authorized restore test |
| Evolution X integration | The standalone `recoveryimage` target now preserves the verified image in two native runs; target-files, two-step recovery, installation and the resulting Android boot remain unverified |
| Virtual A/B and OTA | Review real boot-control and snapshot/merge state; test packaging, slots and update behavior without assuming a spare slot is bootable |

Do not make a decryption test pass by formatting data, accepting incorrect
credentials, upgrading persistent key blobs or removing verification. A UI and
readable logs do not establish decryption, backup coverage or rescue safety.
Virtual A/B is not two independent complete super images; do not merge
snapshots or change slots as an automatic smoke-test step. Keep bootloader
firmware, GPT and persistent-security partitions outside initial write support.
Magisk has not been installed and remains separate work.

The [workspace integration record](../research/workspace-integration.json)
documents the repeatable build and schema-2 input bundle. The bundle includes
the verified public PEM for recovery chain metadata; it never includes the
private signing key. This aligns the configured recovery key with working76,
but does not establish a complete trusted vbmeta chain or OTA compatibility.

## Preserved research provenance

The [original recovery review](../research/recovery-plan.json) and
[full review text](twrp-bringup-history.md#original-recovery-review) describe the
2026-08-27 checkpoint before a local recovery target or device test existed.
Their false build/device fields remain historical facts; they do not describe
the current working76 baseline or grant authorization for later operations.

That review's stock recovery image was 104,857,600 bytes, SHA-256
`a6f2c77608026fcfe6221e5191c501b0ac880658f76c55231879ed198ce8a0f9`.
Image length is **not a live partition measurement**. The package GPT and later
live bootloader observations are separate evidence; do not infer current
geometry or stored rollback counters from a filename or image length.

The original five reviewed source snapshots remain pinned below. They are
research references, not source-provenance claims for the supplied binary.

| Reference | Reviewed commit |
| --- | --- |
| MissMyTime SM8850 | `17525a886e43c26c350fb3db9b260c55e4360dc8` |
| antocorvo3000 Xiaomi 17 series | `4a35185d43782b4dd460a7f456d674c0976c0859` |
| TeamWin recovery | `5c3d206a5eeb3d446bcda8248a405a4b278bab5c` |
| TWRP-Test Android 16 manifest | `d2188a9345857fb078c391e8cb3e259a21e941e5` |
| Official minimal manifest | `6dc117d9cbd08430daa16db2013560e1c4017fa8` |

The original bounded review receipt has SHA-256
`f07607300c58473b9cb698e26c40859e23a785623f1f5ebdeb89a397defa33d9`.
Its source-file and stock-header checks are distinct from subsequent source
builds, the failed RAM trials and the successful prebuilt adaptation. All
research records, private evidence and earlier images remain preserved.

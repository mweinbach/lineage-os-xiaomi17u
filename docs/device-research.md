# Xiaomi 17 Ultra source and device research

Research date: **2026-08-27**. These are public-source findings, not results from
booting Evolution X on this phone. The user reports a **China edition running
xiaomi.eu**. Read-only Android identity collection now reports `nezha`, Xiaomi,
SM8850 / `canoe`, and `ro.boot.hwc=CN`; the modified system exposes model
`2512BPNDAG` and `nezha_xiaomieu_global`. These are observations from the current
modified installation, not a reason to select global firmware. The sanitized
device record is [device-baseline.md](device-baseline.md).

Keep three evidence categories separate: the user's reported China hardware,
the currently installed xiaomi.eu system, and the matching official China
firmware. A xiaomi.eu build fingerprint alone is not an official stock baseline.
Record both the current modified system and its underlying vendor/firmware
versions before selecting a stock package. Both system and vendor incremental
properties report `OS3.0.309.0.WPACNXM`; the reported system security patch is
2026-07-01 but the vendor patch is 2026-02-01. Resolve that distinction when
matching the vendor stack; do not rewrite vendor patch metadata to the system
date. The collected kernel release is
`6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k`, and SELinux reports
`Enforcing`. These identify the running baseline, not a validated Evolution X
kernel or security posture.

## What is established

- Xiaomi's global specifications identify Snapdragon 8 Elite Gen 5, HyperOS 3,
  a 6.9-inch 2608 × 1200 display with 1–120 Hz refresh, ultrasonic fingerprint,
  6000 mAh typical battery, and 90 W wired / 50 W wireless charging. These are
  **global stock-product specifications**, not the user's China-edition battery
  specification or configuration values to copy into a ROM. Do not infer
  China-edition capacity, modem bands, eSIM support, or firmware from this page.
  [Xiaomi global specifications](https://www.mi.com/global/product/xiaomi-17-ultra/specs/)
- Public recovery maintainers identify Xiaomi 17 Ultra as **`nezha`**, with
  **SM8850 / `canoe`** as its platform. This is useful corroboration from the
  developers of those trees, now corroborated by the connected phone's Android
  readback. Final hardware configuration must still be checked against the
  exact China firmware and physical variant, not just modified system props.
  [Nezha recovery tree, pinned README](https://github.com/EkinStrop/twrp_device_xiaomi_nezha/blob/7ad14e492e3ca25a63dfdb39b2fa50e0074a0910/README.md),
  [SM8850 recovery maintainer's device inventory](https://github.com/MissMyTime/twrp_device_sm8850/blob/main/README.md)
- An early public Nezha Lineage device scaffold exists, but the inspected
  revision is incomplete. It is not a ready-made Evolution X port.
  [Inspected device scaffold](https://github.com/zeng-chenxi/android_device_xiaomi_nezha/tree/6ca312b757597bc052782ade1682b965d9d64dfd)

The base Xiaomi 17, 17 Pro, 17 Pro Max, 15 Ultra, Redmi K90 family, and Leica
Leitzphone are not interchangeable build targets. In particular, a common SoC
does not establish compatible panel, camera, charging, firmware, or partition
configuration. Leica documents a physical Camera Ring on the Leitzphone; do not
assume an ordinary Xiaomi 17 Ultra has it.
[Leica Leitzphone specifications](https://leica-camera.com/en-US/mobile/leitzphone-powered-by-xiaomi/technical-specification)

## Public source inventory

Refs below were checked through GitHub on the research date. The commit IDs
identify the inspected versions, not versions certified for this phone.

| Source | Inspected ref / commit | What it can establish |
| --- | --- | --- |
| [Nezha Lineage scaffold](https://github.com/zeng-chenxi/android_device_xiaomi_nezha/tree/6ca312b757597bc052782ade1682b965d9d64dfd) | `lineage-23.2`; `6ca312b757597bc052782ade1682b965d9d64dfd`, 2026-03-23 | Proposed Nezha structure and dependency names; incomplete, see audit below. |
| [Xiaomi SM8850 common tree](https://github.com/xt0032rus/device_xiaomi_sm8850-common/tree/b3defe64905f10f2ddd7906f31c112fad5759c5e) | `lineage-23.2`; `b3defe64905f10f2ddd7906f31c112fad5759c5e`, 2026-04-08 | HAL, extraction, init, and policy examples. README lists only Myron / POCO F8 Ultra. Not a verified dependency of the Nezha scaffold. |
| [Another SM8850 common tree](https://github.com/lolipuru/android_device_xiaomi_sm8850-common/tree/814de530e0c31256ffaf47d1367dcf35904d0f7a) | `lineage-24.0`; `814de530e0c31256ffaf47d1367dcf35904d0f7a`, 2026-08-26 | A newer reference. Its README lists other devices, not Nezha; its platform branch must not be mixed into a different Evolution X branch without review. |
| [Nezha TWRP tree](https://github.com/EkinStrop/twrp_device_xiaomi_nezha/tree/7ad14e492e3ca25a63dfdb39b2fa50e0074a0910) | `main`; `7ad14e492e3ca25a63dfdb39b2fa50e0074a0910`, 2026-07-20 | Maintainer-reported recovery boot, input, and decryption work. A recovery tree does not supply a complete Android device/vendor tree or prove ROM compatibility. |
| [Evolution X SM8850 common repository](https://github.com/Evolution-X-Devices/device_xiaomi_sm8850-common) | Repository exists; branch listing returned `[]`; `cnb` branch returned 404 | No usable revision could be pinned at this check. Do not create an active dependency just because the repository name exists. |
| [Evolution X camera integration example](https://github.com/Evolution-X-Devices/device_xiaomi_peridot-miuicamera/tree/5f2bdfecdbd12c5deaf9ccf94b365e1fc4596426) | `bka`; `5f2bdfecdbd12c5deaf9ccf94b365e1fc4596426`, 2026-03-05 | An example of packaging stock camera dependencies for **Peridot**, not a Nezha camera port. |

Repository searches for `nezha` in `Evolution-X`, `Evolution-X-Devices`, and
`LineageOS` returned no repositories on 2026-08-27; `sm8850` in `LineageOS` also
returned no repositories. These are bounded observations of those public
organizations, not a claim that no port exists anywhere. Search results can
change, private work is not covered, and a maintainer's recovery README mentions
LineageOS testing without providing a complete ROM dependency manifest.
[Evolution X device organization](https://github.com/Evolution-X-Devices),
[LineageOS organization](https://github.com/LineageOS)

### Why the public Nezha scaffold is not buildable as inspected

The following issues were verified at commit
`6ca312b757597bc052782ade1682b965d9d64dfd`:

1. `AndroidProducts.mk` names `lineage_nezha.mk`, but the repository contains
   `lineage_popsicle.mk` instead. That file sets `PRODUCT_MODEL := 2509FPN0BC`
   without establishing that this is the target phone's model.
2. There is no `lineage.dependencies` and no `proprietary-files.txt` in the
   inspected tree. Its `proprietary-firmware.txt` attributes firmware to
   `OS3.0.15.0.WPACNXM`; that is the author's provenance claim, not a verified
   match for the user's phone.
3. It requires `device/xiaomi/sm8850-common/BoardConfigCommon.mk` and `common.mk`,
   plus `vendor/xiaomi/nezha/BoardConfigVendor.mk` and `nezha-vendor.mk`.
   These dependencies are not included or pinned.
4. It also expects `device/xiaomi/nezha-kernel` to contain a kernel, kernel
   headers, DTB, DTBO, and several sets of modules and load lists. Those files
   are absent. An embedded kernel module version string is not enough to
   establish a compatible kernel ABI or stock build.

Evidence:
[product declaration](https://github.com/zeng-chenxi/android_device_xiaomi_nezha/blob/6ca312b757597bc052782ade1682b965d9d64dfd/AndroidProducts.mk),
[product file](https://github.com/zeng-chenxi/android_device_xiaomi_nezha/blob/6ca312b757597bc052782ade1682b965d9d64dfd/lineage_popsicle.mk),
[board configuration](https://github.com/zeng-chenxi/android_device_xiaomi_nezha/blob/6ca312b757597bc052782ade1682b965d9d64dfd/BoardConfig.mk),
[device inheritance](https://github.com/zeng-chenxi/android_device_xiaomi_nezha/blob/6ca312b757597bc052782ade1682b965d9d64dfd/device.mk),
[firmware list](https://github.com/zeng-chenxi/android_device_xiaomi_nezha/blob/6ca312b757597bc052782ade1682b965d9d64dfd/proprietary-firmware.txt).

Both common-tree revisions above contain fixed partition sizes, AVB test keys,
and `BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS += --flags 3`. Those settings are not
accepted defaults for this workspace. Do not copy them into an active Nezha
configuration. Establish the real layout, AVB chain, rollback constraints,
signing policy, and SELinux behavior separately.
[Older common board file](https://github.com/xt0032rus/device_xiaomi_sm8850-common/blob/b3defe64905f10f2ddd7906f31c112fad5759c5e/BoardConfigCommon.mk),
[Newer common board file](https://github.com/lolipuru/android_device_xiaomi_sm8850-common/blob/814de530e0c31256ffaf47d1367dcf35904d0f7a/BoardConfigCommon.mk)

## Xiaomi's released kernel sources

The [MiCode release index](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/62444eb540a7468f7e329a1bb417dd95c07ac8ab/README.md)
was inspected at `README` commit `62444eb540a7468f7e329a1bb417dd95c07ac8ab`
(2026-08-11). It lists `popsicle-w-oss` for Xiaomi 17 / 17 Pro / 17 Pro Max,
with base `release-w-qcom-sm8850`; it does not list Xiaomi 17 Ultra / Nezha.
Branch searches for `nezha` in `Xiaomi_Kernel_OpenSource` and
`kernel_devicetree` returned no matches. This audit therefore has **not verified
an exact Ultra kernel source release**. It has not proven that all Nezha code is
absent from every shared branch.

These related official repositories do have `popsicle-w-oss`. Each inspected
commit explicitly describes the 17 / 17 Pro / 17 Pro Max, not the Ultra:

| Component | Commit on `popsicle-w-oss` (all 2026-03-09) |
| --- | --- |
| [Kernel](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/commit/45705be1220b4cfa8100516ad86711656c0b634e) | `45705be1220b4cfa8100516ad86711656c0b634e` |
| [Kernel device tree](https://github.com/MiCode/kernel_devicetree/commit/667482462e15458b602a2688a94efd47a5010141) | `667482462e15458b602a2688a94efd47a5010141` |
| [Camera kernel](https://github.com/MiCode/vendor_qcom_opensource_camera-kernel/commit/59d5dae93faae1974004788236f6c0b3ec747476) | `59d5dae93faae1974004788236f6c0b3ec747476` |
| [Display drivers](https://github.com/MiCode/vendor_opensource_display-drivers/commit/6def61b29a39710078287416afd3b62f43729c37) | `6def61b29a39710078287416afd3b62f43729c37` |
| [Display device tree](https://github.com/MiCode/vendor_qcom_opensource_display-devicetree/commit/0ba7253b16c3bed277656ea3d090fcf1cacae68c) | `0ba7253b16c3bed277656ea3d090fcf1cacae68c` |
| [WLAN](https://github.com/MiCode/vendor_qcom_opensource_wlan/commit/36df473046706a5259942e1bf7222108dbbb860f) | `36df473046706a5259942e1bf7222108dbbb860f` |
| [Touch driver](https://github.com/MiCode/vendor_xiaomi_proprietary_touch-driver/commit/c286ab85f4982c9b5967e18405f4e2da0332ce4d) | `c286ab85f4982c9b5967e18405f4e2da0332ce4d` |

The same branch name returned 404 in `MiCode/vendor_qcom_opensource_audio-kernel`
and `MiCode/vendor_qcom_proprietary_camera-devicetree`. Do not fabricate a
matching branch or substitute another model's binaries. These public kernel
sources do not provide the closed Xiaomi/Qualcomm userspace HALs or Leica image
processing stack.

## Confirm the existing bootloader state

Because xiaomi.eu is already installed, an unlocked bootloader is plausible but
must not be inferred solely from the ROM name. The collected Android properties
report `ro.boot.flash.locked=1`, `ro.boot.vbmeta.device_state=locked`, and
`ro.boot.verifiedbootstate=green`. A modified ROM can alter reported properties;
these values and the xiaomi.eu installation therefore do not independently
prove the real bootloader state. Keep it **unresolved** until stronger evidence
is reconciled. Do not reboot merely to check it without explicit authorization.
If an existing unlocked state is confirmed, **no new unlock application or
unlock operation is part of setup**. Do not relock or change its boot state.

The following policy research matters if the phone turns out to be locked,
or if a different development unit is proposed; it is not a request to unlock
the user's already modified phone.

Xiaomi's official pages are inconsistent at this check. Its
[UK unlock FAQ](https://www.mi.com/uk/support/faq/details/KA-07238/) describes
limited HyperOS eligibility, outside-mainland account/device restrictions,
and Xiaomi Community as the official application route, while its
[UK safety notice](https://www.mi.com/uk/support/faq/details/KA-533394/) says
unlocking is not supported. Older generic instructions on the same support
site are not proof of present eligibility.

For a locked phone, the decision gate is current official authorization for
**this exact variant, region, and account**. Do not promise a waiting period,
quota, or a successful unlock based on this document. If the phone is locked and
official authorization is unavailable, physical custom-ROM testing is blocked;
source research can continue. This
workspace does not request account credentials, automate unlocking, recommend
paid unlock services, or provide bypasses. Unlocking can erase data and change
device security; it is outside the setup task.

## Evidence required before creating a real build target

| Gate | Required evidence | Current state |
| --- | --- | --- |
| Device identity | Product/device/model, hardware SKU/region, SoC/board, system and vendor fingerprints; compare with the label and exact official firmware package. | Android reports Nezha, SM8850/canoe, HWC CN, and xiaomi.eu; model property is modified. Exact firmware/physical-variant cross-check still required. |
| Authorized development device | Explicitly selected target and observed bootloader state; official eligibility is only an additional gate if it is locked. | Read-only target identified. Current Android locked/green properties are not independent proof of actual bootloader state. No boot-state change authorized. |
| Stock baseline | Matching official China package and current xiaomi.eu package/extraction recorded separately; origin URL, region, build, SHA-256, and acquisition date. | Running incremental is `OS3.0.309.0.WPACNXM`; matching official package is still required. Do not substitute global firmware. |
| Boot and kernel contract | Boot/init_boot/vendor_boot/recovery headers, DTB/DTBO, module lists and kernel ABI, first-stage mounts, dynamic partition metadata, AVB/rollback metadata. | Running kernel version recorded; full contract still missing. Derive from the stock package without running its flash scripts. |
| Vendor contract | VINTF manifests/matrices, vendor API/FCM, HAL services, proprietary file list, ELF dependencies, init and SELinux policies. | Current Xiaomi.eu VINTF/permissions and camera dependencies captured; full extraction and Evolution X compatibility validation remain pending. |
| Native feature baseline | Repeatable stock tests and private artifacts for the features in [native-features.md](native-features.md). | No device tests run. |
| Build host | Native Linux x86-64, or explicitly verified Apple Container ARM64/Rosetta with case-sensitive storage and adequate disk/RAM. | Apple Container's ext4 volume, x86-64 execution, and pinned Repo initialization passed here. Full Android 16 compilation remains unverified; see [Apple Container](apple-container.md). |

Android's [VINTF documentation](https://source.android.com/docs/core/architecture/vintf)
explains the compatibility contract between system and vendor. Matching the
marketing Android version alone is not enough. Keep candidate trees in
`upstream/`; activate a local manifest only after its complete dependency graph
and stock compatibility have been established. Keep firmware, blobs, APKs,
logs, serials, and personal data in ignored storage, with non-sensitive hashes
and provenance recorded separately.

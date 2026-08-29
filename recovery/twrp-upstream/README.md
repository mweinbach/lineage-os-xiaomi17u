These patches preserve the source-integration work against the Nezha subtree
of `antocorvo3000/twrp-xiaomi-17-series` at
`4a35185d43782b4dd460a7f456d674c0976c0859`. They do not produce the currently
installed recovery. The device-tested, user-supplied image is the functional
baseline documented in `../twrp-working/` and `../../docs/twrp-bringup.md`.

For a future source build, preserve the old minimal target outside the device
tree, stage this upstream subtree at `device/xiaomi/nezha`, and apply the patches
there. Select `twrp_nezha_upstream-ap2a-eng` using ordinary device-directory
discovery. Do not pass `TARGET_DEVICE_DIR` through `soong_ui`: the attempted
build rejected that manual override during product configuration.

The first patch keeps the complete upstream product while selecting Nezha,
canoe and a dedicated 100 MiB recovery image with header v4 and no embedded
kernel or DTB. Other partition-image outputs are disabled. Recovery AVB uses
the public AOSP development key with rollback index 1/location 1, not OEM trust.
Recovery-only permissive mode is explicitly authorized for bring-up.

The second patch imports the real Qualcomm boot-control provider. Stage
`LineageOS/android_hardware_qcom_bootctrl` at
`846dfb0652cc142e1783cbe085783527bbe4a190` under `hardware/qcom-caf/bootctrl`.
Without this provider, the graph lacks the QTI boot-control defaults module.

The geometry comes from the recorded Nezha factory `OS3.0.309.0.WPACNXM`
package; no repartitioning is enabled. Removing make-time version overrides
does not replace the upstream root's baked properties or binaries. Its DTB
and DRM module differ from the current stock inputs and are not claimed
compatible. Patch replay passed, but this source build remains unvalidated.

# Nezha engineering product

This is authored Android device source for `lineage_nezha-bp4a-userdebug` on
Evolution X `bka`, using verified local input hashes and the exact stock-prebuilt
kernel strategy. It does not inherit another phone's common BoardConfig.

Generate the complete device directory into a new ignored staging root:

```sh
python3 scripts/generate_device_tree.py generate \
  --kernel-receipt artifacts/KERNEL_BUNDLE/receipt.json \
  --vendor-receipt artifacts/VENDOR_BUNDLE/vendor-inputs.json \
  --output artifacts/device-candidates/nezha-001
```

The optional `--device-baseline`, `--boot-contract`, `--firmware-layout` and
`--vintf-contract` arguments select new sanitized records. Values and image
hashes are derived from those records, not hardcoded to the initial Xiaomi.eu
package. `--fstab-source` can explicitly select the receipt-verified source
fstab; otherwise the kernel bundle's `roles.fstab` reference is used.
The boot contract's `evidence.private_directory` must also contain its hashed
`final-receipt.json` and `logs/unpack-vendor_boot.stdout.txt`. The generator
reads that report without running an unpacker, and reproduces the observed
vendor-boot addresses using a zero base and explicit offsets.

The generator copies this authored source and writes `generated/` includes,
an authored AVB-enabled fstab, the reviewed property patch, and `admission.json`.
It does not copy kernel or
vendor binaries, execute Make, contact a phone, alter the platform checkout or
activate workspace metadata. A separate staging step must supply:

- `kernel/xiaomi/nezha/stock-prebuilt.mk` from this workspace;
- the complete kernel bundle at `vendor/xiaomi/nezha-kernel`;
- the complete private vendor tree at `vendor/xiaomi/nezha`.

The initial **framework-checks** profile permits product/Kati and selected
module/image compilation. All recorded logical mounts, including `mi_ext`,
remain in the fstab with AVB enabled. `mi_ext` is not yet packaged by this
profile; complete target-files, OTA and super-image goals are blocked. No
result from this profile is admitted for flashing, including when compilation
succeeds. Unknown physical capacities or bootloader state do not prevent
configuration generation; they remain separate flash-promotion gates.

The product explicitly makes the source tree read-only inside Ninja's sandbox
with `BUILD_BROKEN_SRC_DIR_IS_WRITABLE := false`. The pinned `bka` release's
default allowed source writes; a standalone read-only sandbox probe did not
establish that the product used that mode. Actual build observations must record
the selected mode separately. This does not change the upstream basic
Soong/Kati sandbox setting or grant any writable-source exceptions.

Boot-image budgets use supplied image lengths and super/group declarations.
They are candidate build budgets, not measurements of physical partitions.
Dynamic framework partitions size themselves during the build. Public AOSP
engineering AVB keys sign newly built artifacts; they are not Xiaomi keys and
must not be enrolled or represented as OEM authentication. Existing source AVB
failures, module ABI/signature uncertainty and required signing/repacking of
raw vendor/ODM inputs remain visible in the admission record.

The pinned Evolution vendor common configuration has two unconditional
defaults that conflict with this product's stricter policy. Integration must
make `ro.ota.allow_downgrade=true` and `ro.control_privapp_permissions=log`
optional (`?=`), without enabling `BUILD_BROKEN_DUP_SYSPROP`. The exact patch
and its before/after source hashes are copied under `patches/evolution/` in
the staging root. The generator records this requirement; it does not patch
platform sources itself. Verify the resulting property outputs before claiming
those policies are effective.

`validate --output PATH --purpose configuration` rechecks generated hashes and
policy, and refuses unlisted files or symlinks. `--purpose target-files` and
`--purpose flash` fail for this profile.
Tests use synthetic receipts and files, Python's standard library, and no
phone, network or Android checkout.

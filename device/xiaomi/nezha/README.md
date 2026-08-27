# Nezha framework-checks product

This is authored Android device source for `lineage_nezha-bp4a-userdebug` and
`lineage_nezha-bp4a-user` on Evolution X `bka`, using verified local input hashes
and the exact stock-prebuilt kernel strategy. It does not inherit another
phone's common BoardConfig.

Generate the complete device directory into a new ignored staging root:

```sh
python3 scripts/generate_device_tree.py generate \
  --kernel-receipt artifacts/KERNEL_BUNDLE/receipt.json \
  --vendor-receipt artifacts/VENDOR_BUNDLE/vendor-inputs.json \
  --output artifacts/device-candidates/nezha-001
```

`plan` and `generate` default to `--variant userdebug`. Add `--variant user`
to select the stricter user variant and record that selection in
`admission.json`. Both commands accept only the exact values `user` and
`userdebug`; validation also rejects missing or invalid receipt variants.
BoardConfig requires exactly one of these variants and rejects `eng`, which
weakens upstream AVB policy. Both variants retain the same AVB, SELinux, APK
validation, source-sandbox and packaging gates. Registering the user lunch
choice does not itself establish build or boot success, or authorize flashing.
The separately recorded user framework policy/tool build now passes; factory
vendor compatibility remains a separate check. Keep user validation in a
separate `OUT_DIR` to preserve existing userdebug outputs.

The optional `--device-baseline`, `--boot-contract`, `--firmware-layout` and
`--vintf-contract` arguments select new sanitized records. Values and image
hashes are derived from those records, not hardcoded to the initial Xiaomi.eu
package. `--fstab-source` can explicitly select the receipt-verified source
fstab; otherwise the kernel bundle's `roles.fstab` reference is used.
The boot contract's `evidence.private_directory` must also contain its hashed
`final-receipt.json` and `logs/unpack-vendor_boot.stdout.txt`. The generator
reads that report without running an unpacker, and reproduces the observed
vendor-boot addresses using a zero base and explicit offsets.

Factory-derived candidates additionally require `--factory-boot-contract`,
`--partition-metadata` and an explicit `--fstab-source` together. Select the
factory layout and matching factory vendor bundle; the existing kernel bundle
keeps its original Xiaomi.eu provenance. The generator binds the comparison
receipts and checks that kernel, DTB, DTBO and bootconfig bytes match. Package
extents must agree with both hash-bound GPT copies and the LP super size.
The factory DTBO budget is 32 MiB, not its stored image's 22 MiB length.

This mode selects the observed logical filesystem rows and retains their
factory AVB and GSI key-path flags, all five boot verification rows, exact
userdata encryption settings and physical/vold storage declarations. Device
node patterns stay inert text; the generator never expands or executes them.
Other logical filesystem alternatives and stock framework overlay/bind mounts
are not selected. Original leading notices are retained. No successful source
comparison promotes package origin, live partition fit, key trust, full policy
compatibility or flash admission.

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

The board also requires `RELAX_USES_LIBRARY_CHECK := false` after inherited
board configuration and rejects a conflicting command-line value. The pinned
Evolution telephony product includes BCR, whose makefile globally sets this
relaxation to `true`. Product inheritance precedes BoardConfig, and dexpreopt
locks the value later. Setting only `PRODUCT_BROKEN_VERIFY_USES_LIBRARIES=false`
would not undo an already defined `RELAX_USES_LIBRARY_CHECK`. Verify the
generated dexpreopt JSON reports `RelaxUsesLibraryCheck: false`, with dexpreopt
still enabled, after installing this source. This setting preserves the check;
it does not supply missing Camera shared-library declarations or prove APK
compatibility.

Without the explicit factory profile, boot-image budgets use supplied image
lengths and super/group declarations. Factory mode uses verified package GPT
extents. Both are candidate build budgets, not live partition measurements.
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

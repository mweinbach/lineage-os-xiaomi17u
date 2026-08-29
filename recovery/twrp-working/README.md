# Working Nezha recovery defaults

This patch is based on the user-supplied
`twrp-3.7.1_16-nezha-antocorvo3000-fix22ZJ-touchfix18.img`, SHA-256
`56029c8109e3ff1bcbb69ef38e8ae36355713340482d9f77405cdf6009bcd323`.
The preserved local copy is `artifacts/twrp/nezha/provided75/recovery.img`.
It is a prebuilt baseline, not source-reproduced TWRP. Use this image's archive,
not a different upstream Git snapshot. Its supplied baseline is unsigned;
local development signing does not establish OEM trust.

The user authorized permissive SELinux for recovery bring-up. The existing
`early-init` action writes `0` to `/sys/fs/selinux/enforce`; SELinux remains
active, the policy remains loaded, and denial logging remains available.
This changes recovery startup only, not normal Android. Restoring enforcement
remains a later bring-up milestone.

Three ordinary theme variables default action, button, and keyboard vibration
to zero. They load before saved settings, so a saved setting can intentionally
override these defaults. No custom service, page action, touch-driver change,
or executable patch is added.

Only `system/etc/init/hw/init.rc` and `twres/ui.xml` change. The assembly used
these steps, with fresh outputs and the original image/archive preserved:

1. Verify the image hash above and the original `recovery.cpio` SHA-256
   `24ed8a66b5dc947cf0531287b4aa73a00e42ceabfa92e3c2a96d662b0f2c6030`.
   Stage only the two original text members. Run `git apply --check` and
   `git apply` with this patch and the staging directory; verify both expected
   preimage and postimage hashes.
2. Call `replace_files(original_cpio, replacements)` from
   `scripts/twrp_cpio_overlay.py`, where each replacement maps its archive path
   to `(original_bytes, patched_bytes)`. Do not recreate the archive from an
   extracted filesystem. Check membership/order, member metadata apart from
   changed lengths/offsets, and every unselected payload remain unchanged.
3. Compress with native LZ4 1.10.0 and verify an exact decompression round trip:

   ```sh
   lz4 -l -12 --favor-decSpeed recovery.cpio recovery.lz4
   lz4 -d recovery.lz4 roundtrip.cpio
   cmp recovery.cpio roundtrip.cpio
   ```

4. Use `system/tools/mkbootimg` at
   `808ecd09666ffe0ff5800f02af693abce56eb395`: header **4**, no kernel argument
   (kernel size **0**), the new ramdisk, empty command line, OS `16.0.0`, patch
   level `2026-02-01`, and page size **4096**. Verify the header matches the
   original except for ramdisk length, and the embedded ramdisk matches.
5. Use `external/avb` at `5ac0c3a071d811846a62412383dd6e259f341e6e`.
   Run `avbtool.py add_hash_footer` for partition `recovery`, size **104857600**,
   hash `sha256`, algorithm `SHA256_RSA4096`, the local development key,
   rollback index **1**, location **1**, and flags **0**. Record a fresh 32-byte
   salt and recovery properties `os_version:16` and
   `security_patch:2026-02-01` under `com.android.build.recovery`.
   Run `info_image`, then `verify_image` with the matching public key. Confirm
   the final size, footer, unchanged unsigned payload and unchanged original.

Fresh AVB salt changes the signed image hash. These steps reproduce the
assembly procedure; they do not establish a source build or hardware behavior.
Keep private keys and local evidence out of version control.

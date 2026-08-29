# Working Nezha recovery

The maintained baseline is the tested `working76` derivative recorded in
[`research/twrp-working-defaults.json`](../../research/twrp-working-defaults.json).
It is a repack of the user-supplied
`twrp-3.7.1_16-nezha-antocorvo3000-fix22ZJ-touchfix18.img`, not source-reproduced
TWRP. The original image SHA-256 is
`56029c8109e3ff1bcbb69ef38e8ae36355713340482d9f77405cdf6009bcd323`;
the required derivative SHA-256 is
`a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e`.
The supplied original has an unsigned (`Algorithm NONE`), stale AVB footer.
Its exact image hash identifies the baseline; that footer does not establish
trust. Local development signing does not establish OEM trust.

The two-file patch adds a recovery `early-init` write of `0` to
`/sys/fs/selinux/enforce` and ordinary zero defaults for action, button and
keyboard vibration in `twres/ui.xml`. SELinux remains active with policy and
denial logging; normal Android is unchanged. Saved settings can override the
vibration defaults. Binaries, drivers, firmware, policy and touch setup remain
unchanged. Restoring enforcement is a later bring-up milestone.

Use the maintained CLI from the repository root:

```sh
python3 scripts/twrp_working.py plan
python3 scripts/twrp_working.py build \
  --local-config .tools/recovery-local.json \
  --output-dir artifacts/twrp/nezha/rebuild-01
python3 scripts/twrp_working.py verify \
  --local-config .tools/recovery-local.json \
  --image artifacts/twrp/nezha/rebuild-01/recovery.img
```

`plan` reads only the public profile and patch. The optional, ignored local JSON
contains paths under these keys: `baseline_image`, `key`, `mkbootimg`, `avbtool`,
`lz4`, `openssl`, `public_key`. Relative defaults resolve against the JSON's
directory; explicit CLI arguments override them. Unknown fields are rejected.
Keep that file private and never put key material in JSON or version control.
Without it, pass the corresponding hyphenated flags explicitly. `--output-dir`
and `--image` always remain explicit. Verification accepts a **PEM public key**,
not a private key or the binary AVB key blob.

[`config/twrp-working.json`](../../config/twrp-working.json) pins the complete
construction: original archive, patch, postimages, compressed ramdisk, tools,
public-key identity, AVB salt and final image. The build replays the two text
hunks in memory and uses `scripts/twrp_cpio_overlay.py` without extracting or
executing archive paths. It checks every unchanged frame and member's metadata,
compresses with native legacy LZ4, verifies the decompression round trip, and
uses pinned mkbootimg for a kernel-free v4 image. Header bytes remain unchanged
except for ramdisk length.

AVB uses the existing approved development key, `SHA256_RSA4096`, recovery
rollback index **1**, location **1**, flags **0**, and the recorded fixed salt.
Signature, descriptor, key identity and exact final hash must all pass; a
different key or merely equivalent image is rejected. Current build support
uses the pinned Darwin ARM64 LZ4/OpenSSL tools. Verification also accepts the
pinned Linux AArch64 OpenSSL binary; this does not claim Linux build portability.

Build safely creates missing output parents, rejects symlink/file ancestors,
requires a fresh leaf directory, and preserves the original. Outputs use
directory mode `0700` and file mode `0600`: `recovery.img`, `build-report.json`,
`verification-report.json`, `SHA256SUMS`, intermediates and native-result hashes.
Failures preserve partial outputs; retry in a new directory. Native calls use
argument arrays, output/file-size limits and timeouts. Selected native tools
and private-key locations must remain trusted and stable during a build.
`verify` uses private temporary snapshots and prints JSON; it does not persist
a receipt. Neither command accesses a phone. Offline tests mock every native
operation; actual reproduction and hardware behavior remain separate checks.

Any future image change requires an explicit profile/code update and fresh
validation. It must not inherit `working76`'s recorded hardware results.

# Local AVB image-set verification

`scripts/avb_image_set.py` verifies the complete Android AVB image set against
independently selected public keys before a future signing or packaging stage
can claim that milestone. It never signs, reads a private-key payload, changes
an input image, accesses a VM, or operates a phone. A successful complete check
still leaves ROM readiness, physical partition fit, device rollback
compatibility, OEM trust and boot validation false.

The maintained [profile](../config/nezha-avb-image-set.json) binds the current
factory GPT/LP evidence and working76 recovery. It requires all 17 image roles:

| Signed metadata | Required coverage |
| --- | --- |
| `vbmeta` | Chains to `boot` at rollback location 3, `recovery` at 1 and `vbmeta_system` at 2; direct hash descriptors for `countrycode`, `dtbo`, `init_boot`, `pvmfw`, `vendor_boot`; direct hashtree descriptors for `mi_ext`, `odm`, `system_dlkm`, `vendor`, `vendor_dlkm` |
| `boot` | Its own boot payload, rollback index 1769904000 |
| `recovery` | Exact working76 payload and signature, rollback index 1 |
| `vbmeta_system` | Hashtree descriptors for `system`, `system_ext`, `product`, rollback index 1769904000 |

Top-level rollback index remains 0. Chain locations are separate from child
header locations: working76's header location is 1; the currently selected boot
and vbmeta_system header locations are 0. The checker preserves this distinction.
It does not change rollback storage or infer the phone's stored counters.

Unsigned `NONE` leaf footers remain admissible under their required signed
parent descriptors. Signed roles require SHA256_RSA4096 and an explicit expected
public key. Hashes and root digests must be full SHA256 values; persistent/empty
digests, disabled verification/hashtree flags, unexpected descriptor kinds,
unknown descriptors and unreviewed kernel-command-line descriptors fail. The
known AOSP engineering public key is refused as an intended signer. The working76
image, public PEM and AVB public-key fingerprints are fixed by the profile.

The native verification calls deliberately verify each signed image separately
with its own `--key`. The root also receives all three
`--expected_chain_partition` arguments. No call uses `--follow_chain_partitions`:
the pinned avbtool recursively reuses the root key in that mode, which does not
correctly represent a set with distinct child keys. The wrapper explicitly
compares each parent chain key with both its independently selected public key
and the child's embedded key. The pinned target-files validator also omits its
selected root key from its recursive command, so that validator's success alone
does not establish the expected root key.

Create an ignored local JSON manifest with exactly these top-level fields:

```json
{
  "schema_version": 1,
  "profile_id": "nezha-avb-image-set-v1",
  "profile_sha256": "SHA256 of the maintained profile",
  "artifact_set_id": "a-descriptive-build-or-derivation-id",
  "images": {
    "recovery": {
      "path": "/private/local/path/to/recovery.img",
      "size_bytes": 104857600,
      "sha256": "a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e"
    }
  },
  "public_keys": {
    "recovery": {
      "path": "/private/local/path/to/public-key.pem",
      "size_bytes": 800,
      "sha256": "50784f7b5ccd4cfde172f5cbce06f54e33547d1081c7d28b55e494aa37ab0967",
      "avb_sha256": "020d7559b8ddedf153e77cc4a02af26c666e3746408a230650ef8cd1e8f09b03"
    }
  },
  "tools": {
    "avbtool": "/local/path/to/pinned/avbtool.py",
    "openssl": "/local/path/to/pinned/openssl"
  }
}
```

This abbreviated example is not a complete image set and contains placeholder
paths/profile digest. Add every required image with its exact hash and size,
and a separately pinned public PEM plus exported AVB-key digest for every signed
image present. Relative paths are resolved against the manifest's directory.
Keys must be selected independently of the images they authenticate; the tool
does not extract an embedded key and treat it as a trust anchor. A manifest
digest binds the caller's selections but does not itself establish their origin
or source-build provenance. Preserve the source lock, patch records, image
derivation receipts and signing-role decision separately.

The two operations have distinct results:

```sh
python3 scripts/avb_image_set.py verify \
  --manifest /private/local/complete-image-set.json \
  --expected-manifest-sha256 REVIEWED_MANIFEST_SHA256 \
  --output reports/avb-complete-new.json

python3 scripts/avb_image_set.py inspect \
  --manifest /private/local/partial-image-set.json \
  --expected-manifest-sha256 REVIEWED_MANIFEST_SHA256 \
  --output reports/avb-partial-new.json
```

`verify` returns exit 2 and a blocked receipt when roles are missing, before
running native tools. Native or structural failures also return exit 2 and
never publish a success receipt. `inspect` can verify available component
payloads but always sets `complete_chain_verified` false, including when all
roles happen to be supplied. Raw leaves without a self-contained descriptor are
listed separately from native-verified artifacts. No missing check is counted
as a passing check. Existing output files are never replaced.

Verification copies selected regular, singly linked inputs into a private
temporary directory with canonical partition names. It rejects symlinks,
hardlink aliases, nonregular inputs, mutation, invalid JSON types and unknown
fields. It requires free space for the copies plus 1 GiB, then removes only its
own temporary copies. Original images and public keys remain unchanged. The
script copy actually executed, the original pinned tools, image copies, source
images and public-key copies are rechecked before reporting success. Only public
keys reach native tools. The profile pins avbtool commit
`c92ce4cb9a1b6d20a1bc11b7e5864af9f78615bb` and the accepted OpenSSL executables.

Image checks include package budgets, exact descriptor ownership, no duplicate
partition descriptors, header/descriptor flags, rollback roles, Android v4
payload coverage, DTBO entry bounds, vendor-ramdisk fragment bounds and EROFS
data-block coverage. Hashtree and FEC ranges must fit before the leaf metadata;
the native tool verifies the payload/hash tree. **FEC contents are not verified**
by this avbtool path and remain explicitly unverified in receipts. The wrapper
does not claim filesystem semantic validation, kernel compatibility, VINTF,
SELinux correctness, OTA support or firmware outside this Android root chain.

The `system_ext` logical override keeps its existing 778,199,040-byte maximum.
Above-stock images are admitted only by exact measured image identity and the
corresponding native package-admission receipt. The original a6d image remains
admitted at 778,199,040 bytes. The f9e image is separately admitted at
778,190,848 bytes, SHA256
`707442120ef680143b653d765c6148617482fa196b951998844d7ed8edfa7432`,
through the pinned f9e package-admission record. This adds no bytes to the
logical maximum, physical Super size, dynamic group, or any physical partition.

On September 6 the explicit userdebug opt-in build measured system_ext at
783,491,072 bytes, SHA256
`9d96b82b7123cd1373141aeeae13c5425dc6f18a900536b2b23e92d28624649c`
(the debug variant adds 5,300,224 bytes). It is admitted as a second measured
image through its own package-admission record, and the logical maximum is now
exactly that largest admitted image. The dynamic group and every physical
partition are unchanged; the admitted logical set totals 9,481,801,728 bytes
against the 15,290,335,232-byte group.

On September 7 the rebuilt userdebug opt-in package (identity `nezha.88dd3098…`,
now with `ro.debuggable=1`) measured system_ext at the same 783,491,072 bytes
with SHA256
`da5ae04b78369864a5023febf8e9bf03b649a08cb8d8dac1027a6cae34f6c6d2`. It is
admitted as a third measured image through its own package-admission record;
the logical maximum and every physical partition are unchanged.

On September 7 the same source identity was rebuilt with `WITH_SU=true` in the
userdebug opt-in environment, adding the `adb_root` service to system_ext. The
image measured 783,507,456 bytes, SHA256
`4848f4dabcbaf9669ca8bcf7e74963db81b02538df42d3d122fb359200420761`, 16,384
bytes above the previous maximum. It is admitted as a fourth measured image
through its own package-admission record, and the logical maximum is now
exactly that image. The dynamic group and every physical partition are
unchanged.

On 2026-08-29 the new wrapper inspected the prior v8 `user` init_boot,
vendor_boot and dtbo artifacts plus working76 using real pinned avbtool/OpenSSL.
All four component payload checks passed with unchanged input hashes. Attempting
complete verification of the same manifest was blocked with 13 missing roles.
The ignored evidence is under
`reports/oem-policy-integration-20260829/avb-adoption-audit/`; these remain prior
component artifacts, not a newly signed ROM or an Evolution boot test.

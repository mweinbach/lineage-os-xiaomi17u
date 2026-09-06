# Host AVB signing preparation

`scripts/avb_signing.py` supplies a concrete preparation and signing recipe for
the [verified Nezha AVB layout](avb-image-set.md). It does not sign anything as a
side effect of planning or preparation. Actual signing is a separate operation
that the coordinator can run after the final image inputs are ready.

The [signing contract](../config/nezha-avb-signing.json) reuses the existing
working76 development key for boot, vbmeta_system and root vbmeta. No new AVB key
is technically required for this local development chain. Recovery retains its
existing signature and exact image bytes. These remain separate image/key roles
even though this recipe uses the same public key for all four. A future release
key policy can be reviewed separately; this tool does not generate keys or sign
APKs, APEXes, OTA packages or payloads. **Never relock the bootloader on this
development key.** A locally valid chain is not proof of bootloader acceptance.

The existing `.tools/recovery-local.json` remains unchanged. Preparation reads
its public-key and OpenSSL selectors; its private-key selector is not resolved
or inspected on the filesystem. It is normalized as text only to reject public
input or tool paths that select the same file. Tool aliases are checked before
their payloads are read; hardlinks and files outside the exact approved tool
sizes are refused. JSON inputs reject an accidentally selected PEM before
reading its payload. These protect against accidental selection mistakes; they
are not a sandbox against a hostile process running under the same user.
Only the explicit `sign` operation resolves and checks that private
file's metadata, then delegates key reading to the pinned native host tools.
Python never reads or copies its payload. No key path or key bytes are included
in receipts. Native command records substitute a fixed redacted label for the
private key path. Signing is restricted to the ARM64 Mac and the existing
approved OpenSSL binary; it cannot run as a Linux guest operation.

The signing tool is pinned separately to avbtool commit
`c92ce4cb9a1b6d20a1bc11b7e5864af9f78615bb`. This does not change the older avbtool
selector used by the reproducible recovery builder. The existing AVB verifier
profile is bound by SHA256
`95c11d61b71362e5dac2aa490eba9cc11f78b4129f7e46a71f6d56453475d3bd`.
That profile retains the stock physical bounds and carries the measured,
admission-pinned successor `system_ext` logical-image allowance described in
[successor-logical-budget.md](successor-logical-budget.md).
Maintained policy-image preparation selects
`config/nezha-policy-images-successor.json`; the unversioned policy catalog
retains its prior bytes for hash-bound historical metadata reconstruction.

An ignored input manifest selects **15 final input images**. Root vbmeta and
vbmeta_system are intentionally absent: they are new outputs, and no old root
metadata is imported. The manifest schema is:

```json
{
  "schema_version": 1,
  "contract_id": "nezha-host-avb-signing-v1",
  "contract_sha256": "SHA256 of config/nezha-avb-signing.json",
  "artifact_set_id": "a-descriptive-final-input-set-id",
  "images": {
    "boot": {
      "path": "/private/local/path/to/boot.img",
      "sha256": "REVIEWED_IMAGE_SHA256",
      "size_bytes": 100663296
    }
  },
  "source_records": [
    {
      "path": "/private/local/path/to/image-provenance.json",
      "sha256": "REVIEWED_RECORD_SHA256",
      "size_bytes": 1234
    }
  ]
}
```

This abbreviated example has placeholders and is deliberately incomplete. Add
`countrycode`, `dtbo`, `init_boot`, `pvmfw`, `vendor_boot`, `recovery`, `mi_ext`,
`odm`, `system`, `system_ext`, `product`, `system_dlkm`, `vendor` and `vendor_dlkm`
with their exact hashes and lengths. Relative paths are resolved against the
manifest directory. The source records bind the actual component-build and
image-derivation receipts; their bytes are checked, but this signing tool does
not reinterpret their policy, filesystem or source-build assertions as proof.

All logical inputs must already have correct rebuilt hashtrees, FEC and unsigned
AVB footers. In particular, an adopted vendor/ODM policy changes filesystem
bytes and needs new tree/FEC descriptors before this workflow. An unsealed EROFS
payload is refused. This tool neither invents a host FEC executable nor drops
FEC to make signing proceed. Original and derived proprietary inputs remain
separate under their existing provenance records.

The three operations are:

```sh
python3 scripts/avb_signing.py plan \
  --input /private/local/nezha-inputs.json \
  --expected-sha256 REVIEWED_INPUT_MANIFEST_SHA256

python3 scripts/avb_signing.py prepare \
  --input /private/local/nezha-inputs.json \
  --expected-sha256 REVIEWED_INPUT_MANIFEST_SHA256 \
  --local-config .tools/recovery-local.json \
  --output-dir artifacts/avb/nezha/prepared-UNIQUE_ID

python3 scripts/avb_signing.py sign \
  --input artifacts/avb/nezha/prepared-UNIQUE_ID/preparation.json \
  --expected-sha256 REVIEWED_PREPARATION_RECEIPT_SHA256 \
  --local-config .tools/recovery-local.json \
  --output-dir artifacts/avb/nezha/signed-UNIQUE_ID
```

`plan` does not open images, provenance records, local signing configuration or
native tools. Missing roles produce a blocked result and exit 2. `prepare`
requires all 15 inputs and their provenance records, copies them into a private
temporary verification directory, and performs keyless payload/signature checks.
The known source engineering or factory embedded boot key may be inspected as
an input; it is never accepted as the new development signer. Recovery is
verified against its independent approved public key. Preparation publishes only
the input manifest and public preparation receipt, not a signed image set.

Actual signing rechecks the entire preparation, including the workflow source
identity, input hashes, source records, public key, local configuration identity
and native tool identities. It then creates new outputs under the ignored
`artifacts/avb/nezha/` directory. Existing output directories are refused, including
failed prior attempts. Original images, prepared records and keys are unchanged.
Temporary image copies require substantial disk; both snapshot and output space
are checked before their corresponding work.

The native recipe is fixed:

| New output | Input and recipe |
| --- | --- |
| `boot.img` | Copy only the validated original payload prefix into a fresh file; preserve its salt and property bytes/order; add a SHA256_RSA4096 hash footer with flags 0, rollback index 1769904000, header location 0, and the 96 MiB package budget |
| `vbmeta_system.img` | Import only the final system, system_ext and product leaf descriptors; sign with flags 0, rollback index 1769904000 and header location 0 |
| `vbmeta.img` | Import the ten direct leaves and add only boot:3, recovery:1 and vbmeta_system:2 chain descriptors; sign with flags/index/header location 0 |

Both metadata images use the pinned build's 4096-byte native padding followed by
zero extension to 65536 bytes, within their 131072-byte package partitions. All
other **14 input images are retained byte for byte**, including working76.

The raw countrycode and pvmfw images need descriptor carriers, not new signatures.
Preparation copies exactly 32 and 778240 payload bytes respectively into fresh
files and uses `add_hash_footer --algorithm NONE --output_vbmeta_image
--do_not_append_vbmeta_image`. Their preserved salts and resulting sole descriptor
must exactly match the recorded factory descriptor. This avoids importing
unrelated descriptors from old root vbmeta.

These precautions address actual pinned-tool behavior. `add_hash_footer`
truncates an existing footer before signing and cannot restore its old signature
on failure, so it never receives an original image here. Its detached mode also
fails on an existing footer despite opening the input read-only. Descriptor
imports do not verify payloads and can silently replace duplicate partition
descriptors or retain duplicate properties. The workflow validates inputs first,
forbids old root/boot metadata imports, and uses the independent complete-set
verifier on the final output.

The explicit signing operation generates the three changed images twice from
the same pinned payloads, salts, properties, key and tool bytes. It compares their
complete image hashes, verifies the 14 unchanged copies, and binds the final
verification manifest to those exact identities. A successful signing receipt
therefore establishes reproduction of these signing derivatives, not two full
Android source builds. Native or comparison failure leaves no success receipt.
Original inputs, provenance records, public key and local configuration are
checked again after complete-set verification and before publishing success.
The receipt retains both the repeated public preflight commands and the signing
commands, with private paths redacted.

Implementation validation has not accessed a private key or signed a ROM.
Real pinned-tool tests derived and verified the two **unsigned** raw descriptor
carriers, with exact factory descriptor hashes and unchanged inputs. Planning
with the four prior v8/working76 artifacts correctly reports 11 missing input
roles. The private evidence is under
`reports/oem-policy-integration-20260829/avb-adoption-audit/signing-preparation/`.
Actual private-key signing and complete-chain execution remain for the
coordinator after final inputs are ready. No phone operation is authorized by
any result from this workflow.

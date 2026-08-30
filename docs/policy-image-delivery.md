# Policy-bearing vendor/ODM metadata delivery

The explicit delivery path connects the reviewed vendor/ODM policy derivatives
to target-files metadata while preserving the factory-image path. It does not
admit a complete ROM. The original
[`target_files_metadata.py`](../scripts/target_files_metadata.py) and
[`target_files_metadata_combined.py`](../scripts/target_files_metadata_combined.py)
remain byte-for-byte unchanged; their existing selectors still require the
original factory images.

Two maintained adapters preserve the reviewed candidate's separate stages:

| Maintained source | Explicit descriptor | Purpose |
| --- | --- | --- |
| [`target_files_metadata_policy_images.py`](../scripts/target_files_metadata_policy_images.py) | [`nezha-policy-image-delivery-basis.json`](../config/nezha-policy-image-delivery-basis.json) | Binds the original metadata and final leaf derivation. Its missing-current-policy install gate still fails. |
| [`target_files_metadata_delivery.py`](../scripts/target_files_metadata_delivery.py) | [`nezha-policy-image-delivery.json`](../config/nezha-policy-image-delivery.json) | Adds the exact current v13i policy evidence and actual independent guest-copy receipt. Installation requires actual packaged inputs. |

The descriptors preserve the reviewed schema-1 and schema-2 bytes, respectively.
They record identities and metadata paths, not proprietary file contents. The
actual delivery descriptor pins the 61,136-byte selected-copy receipt
`dd11cdbee4b5d9193dfeb875ff2bfbfd5410cc4e2de14213577b386545b4c4ab` and the
85,108-byte current-policy record
`8ec546ed3e3e9992cce543c3c1cb80103edc2f8a1adc2fc496b5f343571a008d`.
Those private records, their complete native evidence, images and source
checkouts stay in ignored locations.

The final images differ from their factory originals:

| Role | Admitted final SHA256 | Package bytes |
| --- | --- | ---: |
| vendor | `ce11f1c6dfc87c29ade267e53d968426cb1e4fa7ce7decca9b1ee85dcb5c7a43` | 959,709,184 |
| ODM | `854c0047709496136557fbdaf2f3ee0a124fa6a18c1bfaddd063d2a3d006d257` | 4,767,621,120 |

The original image identities remain distinct in every metadata receipt. The
reviewed chain binds exactly five policy-file replacements, the complete
original/new filesystem export comparison, all 205 unchanged metadata payloads,
two raw image reconstructions, two final keyless AVB leaf derivations and
independently regenerated FEC. Package-budget fit does not prove physical
partition fit, and an AVB leaf using algorithm `NONE` is not a signed parent
chain. The actual copy operation also rehashed 204 source inputs, 13 policy
outputs and 11 protected runtime outputs before and after copying. Its capture
establishes a private validation bundle, not source adoption or a read-only
source namespace.

Staging reads the original small metadata bundle and the exact proof/current/
copy records. It does not need image bodies or target-files output. It preserves
all 205 payloads, their original capture NIDs and the property-import closure:
24 property files, 178 VINTF files and three vendor APEX files, totaling 6,460,780
bytes. It does not project an ODM SELinux tree, invent properties, include a
complete APK inventory, or claim filesystem reconstruction.

Host staging, verification and selection require both `--source-contract` and
`--image-contract`. Native installation obtains the exact copied selectors from
the externally admitted bundle receipt. A typical local stage uses the following
inputs, with a fresh ignored output directory:

```sh
python3 -B scripts/target_files_metadata_delivery.py stage \
  --original-bundle artifacts/target-files-metadata/nezha-factory-combined-20260829-v1 \
  --expected-original-receipt 8c1c78d19d786fee2be6c92a3f93fd28677ab24500f74da3bb911f96e6de89df \
  --source-contract patches/evolution/target-files-source-composition.json \
  --image-contract config/nezha-policy-image-delivery.json \
  --delivery-proof reports/oem-policy-integration-20260829/target-files-v13h-image-admission/delivery-v1/replay-v2.json \
  --current-policy-evidence reports/oem-policy-integration-20260829/target-files-v13h-image-admission/delivery-v1/current-policy/report-v2.json \
  --selected-delivery-evidence reports/oem-policy-integration-20260829/target-files-v13h-image-admission/delivery-v2/dispatch-host-v2/guest-receipt.bin \
  --output artifacts/target-files-metadata/nezha-policy-delivery-local
```

Use the resulting receipt's externally recorded SHA256 for `verify`, `selection`
and the build selector. The generated `tools/target_files_metadata.py` embeds
exactly four maintained source modules. It does not import code from ignored
reports or adjacent unbound Python files. Its copied controls include the
canonical descriptors, profile and source-patch contracts. Changes to source
paths or code alter the generated checker and bundle receipt; the earlier
private candidate receipt is not reusable for the maintained bundle. Preserve
old bundles and record each new derivation.

The generator's `--policy-image-delivery-contract` is a separate opt-in, paired
with the metadata receipt/SHA256 and combined source contract. The factory
image bundle remains unchanged. A root-owned installation must independently
copy and hash the selected leaves into a separate
`vendor/xiaomi/nezha-policy-images` input bundle. The validation-copy paths in
the receipt provide provenance; later regular files at other paths can be
verified only against the exact final identities. This does not permit implicit
image substitution or replacement of the original proprietary images.

The unchanged build-core hook invokes the generated verifier before metadata
publication. It requires all ten final source-file hashes from the explicit
0005–0011 composition, the exact `IMAGES/vendor.img` and `IMAGES/odm.img`, seven
actual framework CIL/mapping/genfs inputs, and three actual framework digest
sidecars. The sidecars must equal SHA256 of each ordered CIL/mapping pair with
the required newline. Missing, changed or aliased files fail before publication;
changes during publication trigger rollback of only the newly owned metadata.
There is no override for missing policy evidence. A complete target-files
package is not required before source adoption, but these actual packaging
checks remain mandatory when the hook runs.

Offline tests use inert fixtures and mock process/network actions. They cover
explicit selectors, changed receipts, stale inputs, source and image guards,
all seven policy inputs and three sidecars, alias rejection, preserved originals,
atomic rollback and standalone checker assembly. Host staging and isolated
Python verification are separate from real Android packaging. Complete VINTF,
target-files/super/OTA behavior, signed AVB/rollback compatibility, physical fit,
runtime functionality and the first authorized Evolution X boot remain open.

# Nezha VINTF and framework contract

The supplied Xiaomi.eu files now establish a **static interface and dependency
baseline**, not a compatible Evolution X product. All **209 VINTF XML files**
parse, and all **432 previously captured VINTF/permissions XML files** match the
extracted package at the same runtime path and SHA256. No effective device
manifest, full `checkvintf` result, or Evolution X hardware behavior has been
verified. This analysis did not access or change the phone.

The [machine-readable record](../research/vintf-contract.json) preserves selected
declarations, source hashes, inode mappings, receipt hashes and explicit limits.
It refers to the user-provided package with SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Its origin remains unverified. Local integrity and matching XML do not
authenticate Xiaomi factory firmware or resolve the package's
[AVB failures](boot-contract.md).

## Verified collection scope

All eight populated logical images were inventoried with the guarded
[EROFS tool](../scripts/erofs_inventory.py). The inventories contain **16,038
entries**. Eight contract-capture batches copied **1,306 regular files**, totaling
**343,023,223 bytes**, with file SHA256 readback. These batches include metadata,
selected dependencies and module evidence; they are not complete filesystem
exports. The separate seven-file vendor camera batch and 13 manual native
dependency seeds are not included in the 1,306 count.

| Logical image | Inventory entries | Contract-capture files |
| --- | ---: | ---: |
| `odm_a` | 3,052 | 104 |
| `product_a` | 2,229 | 41 |
| `system_a` | 3,371 | 125 |
| `system_dlkm_a` | 306 | 118 |
| `system_ext_a` | 2,677 | 146 |
| `vendor_a` | 3,878 | 382 |
| `vendor_dlkm_a` | 396 | 388 |
| `mi_ext_a` | 129 | 2 |

Image hashes match the [logical extraction record](../research/firmware-layout.json).
Each capture receipt links its image hash, inventory hash and inventory-receipt
hash to the selected inode, original image path, flat output filename and output
hash. The source-file table in the VINTF record links the published findings to
those private receipts. Raw XML, JARs, modules and other proprietary bytes remain
ignored under `artifacts/firmware-analysis/<package-sha256>/`.

The comparison used the earlier read-only baseline in
`evidence/xiaomi-eu-20260827T1530Z/manifest.json`: **209 VINTF XML plus 223 permission
XML files**, with every original receipt and captured file hash checked. It does
not establish complete OS identity, active APEX contents, effective manifest
selection, service registration or feature behavior.

The corrected private summary is `vintf-analysis-v2.json`. Its properties retain
their complete source paths. Do not use the initial summary's property
aggregation: it overwrote `/vendor/build.prop` with the nested
`/vendor/odm_dlkm/etc/build.prop` data. The original summary was preserved as
evidence rather than silently replaced.

## What the XML counts mean

| XML role | Files | HAL elements | Formats |
| --- | ---: | ---: | --- |
| Device manifests | 177 | 221 | 220 AIDL, 1 native |
| Framework manifests | 22 | 37 | 19 AIDL, 17 HIDL, 1 native |
| Framework compatibility matrices | 9 | 859 | 528 AIDL, 328 HIDL, 3 native |
| Device compatibility matrix | 1 | 3 | 3 AIDL |

These are unmerged XML elements, not counts of running services. In particular,
22 device-manifest elements are empty `override="true"` declarations in nested
`manifest/qspa/qspa-modem.xml` and `qspa-nav.xml` profiles. The former names 21
radio/IMS HALs; the latter names GNSS. Their activation is unverified. They must
not be flattened into either an active provider list or a claim that the running
phone has disabled those services.

AOSP defines manifest overrides and selection/merging across vendor, ODM,
fragments and vendor APEX manifests. Those rules must be applied to the actual
selected files, not every XML file found on disk. [AOSP VINTF objects](https://source.android.com/docs/core/architecture/vintf/objects)

Compatibility matrices express expectations in the other direction; they are
not evidence of a device provider. None of the 862 captured matrix HAL elements
has an `optional` attribute. AOSP documents that attribute as ineffective after
Android 15, so do not label these entries optional by assumption. [AOSP compatibility matrices](https://source.android.com/docs/core/architecture/vintf/comp-matrices)

One concrete trap is `vendor.xiaomi.hardware.campostproc` HIDL 1.0,
`IMiPostProcService/default`, in the system framework matrix. No captured device
manifest declares that name. The observed device declaration is the separate
AIDL `vendor.xiaomi.hardware.postprocservice` service. The legacy matrix entry
alone does not justify adding or expecting a legacy HIDL provider.

## Target level and API properties

Both `/vendor/etc/vintf/manifest_canoe.xml` and `manifest_alor.xml` declare XML
schema version `9.0`, device target level **202504**, and SELinux version
**202504**. Neither contains an explicit `<kernel>` element. The `canoe` board
property makes the canoe file a candidate; it does not prove that libvintf
selected it. Neither `ro.boot.product.vendor.sku` nor
`ro.boot.product.hardware.sku` was collected in the previous baseline.

| Source file | Selected exact values |
| --- | --- |
| `/vendor/build.prop` | `ro.board.platform=canoe`; `ro.board.api_level=202504`; `ro.board.first_api_level=202504`; `ro.board.api_frozen=true`; vendor SDK `36`; vendor security patch `2026-02-01` |
| `/odm/etc/build.prop` | `ro.product.first_api_level=36` |
| `/system/build.prop` | SDK `36`; `ro.llndk.api_level=202504`; system security patch `2026-07-01` |

`ro.vendor.api_level` was not present in the nine captured `build.prop` sources
and was not recorded from the live phone. Do not present an inferred value as a
live result. Board/vendor API levels use a different scheme from SDK integers;
the runtime vendor property is derived by Android initialization rules. [AOSP vendor API flags](https://source.android.com/docs/core/architecture/api-flags)

The system incremental remains `16OS3.1.260714.203507406.QCPECN.S`, while vendor,
ODM and the product's public label record `OS3.0.309.0.WPACNXM`. These are
separate observed values from a modified package, not reasons to rewrite its
properties or infer a different phone. See the
[embedded identity limits](provided-firmware.md#embedded-identity-and-its-limits).

## Selected interface requirements

The JSON record retains 63 selected device HAL elements with exact source file,
format, declared versions, instances and override attributes. The following
table highlights feature dependencies; every row still needs its implementation,
init rules, libraries and policy. Versions below are explicitly declared AIDL
integers unless marked omitted.

| Area | Observed declarations |
| --- | --- |
| Main camera | `android.hardware.camera.provider` v3, `ICameraProvider/vendor_qti/0` |
| External camera | Same AIDL name, version omitted, `ICameraProvider/external/0` |
| Camera extensions | Offline camera v2 `IOfflineCameraService/default`; quick camera v1 `IQuickCameraService/default`; Xiaomi postproc version omitted `IPostProcService/default` |
| Other camera hooks | Xiaomi mivimessage, synthetic camera, always-on, sensor camera and secure camera declarations; exact names and instances in JSON |
| Biometrics | Fingerprint v4 `IFingerprint/default`; face v4 `IFace/default` |
| Audio | Core v3: `IConfig/default`, `IModule/default`, `r_submix`, `usb`, `bluetooth`; effects v3 `IFactory/default`; Bluetooth audio v5 |
| Graphics | Allocator v2; composer3 v4; native `mapper` with fqname `@5.0/qti` |
| Power and sensors | Power v6; power statistics v2; thermal v3; health v4; sensors v3; light v2; vibrator v2 with an explicit override |
| Connectivity | Wi-Fi v3, hostapd v3, supplicant v4, GNSS v4, NFC v2, Bluetooth ranging v2; base Bluetooth, USB, USB gadget and UWB versions omitted |
| Radio | Config v4/default; data, messaging, modem, network, SIM and voice v4 on `slot1` and `slot2`; SAP version omitted on both slots |
| Qualcomm IMS | Radio IMS v20 on `imsradio0` and `imsradio1`; data channel v3/default; IMS factory version omitted/default |
| Security | Default KeyMint device v4 and remote provisioning v3; StrongBox device/provisioning v3; secretkeeper v2; Weaver v2; other exact declarations retained in JSON |

An empty `declared_versions` array in JSON means the `<version>` element was
absent; it is not a measured runtime version. AOSP's AIDL schema default is 1
when the version is omitted. Keep that schema interpretation distinct from the
bytes captured and from querying a running implementation. [AOSP manifest schema](https://source.android.com/docs/core/architecture/vintf/objects)

The device compatibility matrix also expects framework-side AIDL names:

| Device matrix name | Matching static framework declaration |
| --- | --- |
| `android.frameworks.sensorservice` | System manifest: `ISensorManager/default` |
| `vendor.qti.hardware.sigma_miracast_aidl` | System-ext fragment: `ISigma_miracast/default` |
| `vendor.qti.qccsyshal_aidl` | System-ext fragment: `IQccsyshal/default` |

The matrix records system SDK `36`; these three version elements are omitted.
The system manifest also has a legacy HIDL sensorservice entry capped at
`max-level=8`; that does not replace the AIDL declaration for this candidate
target. Matching static names is not a complete matrix check. Evolution X needs
reviewed framework/system-ext counterparts as well as vendor/ODM services.

## Kernel, SELinux and AVB gates

The shipped system matrix at level **202504** specifies a **6.12.0 minimum** and
kernel level **202504** in 11 kernel fragments: one unconditional set of **260
config requirements**, plus ten conditional sets containing another **32**.
The 292 config elements are not 292 simultaneous requirements. For example,
`CONFIG_ARM64=y` selects a 14-entry conditional set, while the ARM and x86 sets
have separate conditions. The JSON preserves every condition and set count.

Selected unconditional requirements include Binder IPC/Binderfs, `DM_VERITY`,
`MODULES`, `MODVERSIONS` and `SECURITY_SELINUX`, all `y`. The extracted kernel
release matches the live baseline:
`6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k`. Its patch number exceeds
the matrix's numeric minimum, but effective kernel FCM selection and all
applicable configs have not been matched. Kernel version, level and conditional
configuration must be checked together. [AOSP VINTF matching rules](https://source.android.com/docs/core/architecture/vintf/match-rules)

The unnumbered system framework matrix records kernel SELinux policy version
`30` and accepted policy versions through `202504`. Its `vbmeta-version=1.0`
field is metadata, not verification of this package. The actual boot/AVB and
DLKM evidence, including the module CRC disagreement and unresolved kernel
exports/signature acceptance, belongs in the [boot contract](boot-contract.md).
Do not relax SELinux, signature or rollback checks to satisfy this XML.

## Unresolved postproc Java path

The permission file
`/system_ext/etc/permissions/vendor.xiaomi.hardware.postprocservice-V1-java-permission.xml`
declares library `vendor.xiaomi.hardware.postprocservice-V1-java` at
`/system/framework/vendor.xiaomi.hardware.postprocservice-V1-java.jar`.

The inventoried regular JAR is instead under `/system_ext/framework/`, with
SHA256 `7078503117b60cf8cce688fd742908a73a7cd284aafae6327cbef9b3d6138c56`.
No matching entry or alias was observed in the system-image inventory at the
declared path. Runtime path resolution has not been tested. Do not claim a
working symlink alias or silently rewrite the permission file. The
[camera dependency evidence](camera-baseline.md) records the captured JAR and
the wider framework/native dependency work still needed.

## Guarded read-only reproduction

The existing inventories and captures are complete; do not repeat them merely
to resume the workspace. For an additional batch, use the recorded logical-image
hash and a **new** private destination. For example, these commands would create
new review outputs rather than replace the completed records:

```sh
firmware_analysis=artifacts/firmware-analysis/b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69
python3 scripts/erofs_inventory.py scan \
  --image "$firmware_analysis/logical-partitions/vendor_a.img" \
  --expected-sha256 29857df564130923b3786b11b4ad29a0c16522e1def37aed7fe09329d673da43 \
  --output "$firmware_analysis/erofs/vendor-review-inventory"
python3 scripts/erofs_inventory.py capture \
  --image "$firmware_analysis/logical-partitions/vendor_a.img" \
  --expected-sha256 29857df564130923b3786b11b4ad29a0c16522e1def37aed7fe09329d673da43 \
  --inventory "$firmware_analysis/erofs/vendor-review-inventory" \
  --output "$firmware_analysis/erofs/vendor-review-capture" \
  --path /build.prop \
  --path /etc/vintf/manifest_canoe.xml
```

Selectors are canonical paths **inside the image**, not Android mount paths.
For this package, vendor `/etc/vintf/...` maps to runtime `/vendor/etc/vintf/...`;
the system image already contains `/system/...`. Use the inventory mapping
rather than blindly adding or removing a prefix.

The tool runs installed `dump.erofs` 1.9.4, records its resolved binary and SHA256,
and uses argument arrays with no shell. It hashes the image once per batch,
holds the verified image descriptor open, and checks input/tool identity during
and after processing. It bounds directory depth, entry count, subprocess time
and output sizes. Malformed listings, loops and unexpected metadata fail closed.

No filesystem is mounted and no firmware binary is executed. Symlinks are
inventoried but never followed or materialized. Only regular files whose path,
type and inode match the inventory can be captured; hardlink aliases whose
reported canonical path differs are rejected. Files are stored as flat names
such as `files/0001`, with original paths in receipts. Existing destinations,
symlinked directories and failed readbacks are rejected; completed directories
are published without replacing another output.

Workspace tests use small offline fixtures and mocked subprocesses. They check
tool safety and record consistency, not device compatibility. Before a first
device build, the remaining work is an authenticated baseline, effective
manifest/SKU/APEX resolution, an assembled Evolution X `checkvintf` evaluation,
proprietary dependency closure and enforcing policy. Hardware and VINTF/VTS tests
remain separate, explicitly authorized device work; no lunch target is invented
by this record.

# Unlevelled framework-matrix AIDL name audit

`nezha_unlevelled_aidl_metadata_audit` checks whether the AIDL names in the
selected Nezha framework-matrix extension occur in the build's VINTF-stable AIDL
metadata. It reads the matrix without changing its bytes or unspecified FCM
level. Missing names are reported with every affected instance tuple and cause
a nonzero exit. It does not alter the production `checkvintf` implementation.

**Native compilation, linking and execution are pending.** Source review and
offline workspace tests are separate from those native results. This tool does
not yet supply a successful definition check or complete compatibility claim.

## Pinned source and input scope

The parser and lookup rule come from `system/libvintf` revision
`69c456ea4aa2f503a2904cfbc11f279a3b2efb09`. The metadata API and generators come
from `system/tools/aidl` revision
`3747384b876442e7ea0c355fe5adc75b29362833`. Their captured source receipts are
retained under the ignored
`reports/oem-policy-integration-20260829/source-visibilityvintfaidlv1/` directory.
The earlier scoped full VINTF result and its uncovered definition skip remain
unchanged; this audit would produce a distinct result.

This initial implementation deliberately accepts only:

```text
/work/out/nezha-user-policy-20260827T2220Z/target/product/nezha/system/etc/vintf/compatibility_matrix.device.xml
```

The file must be 30,492 bytes with SHA256
`dc91ab1640e532a1bf42cb7aa99ca471b0f7a71e30c27e754bf0d3dc04fab353`.
It must remain a framework matrix with unspecified level, containing exactly
155 AIDL instance tuples, 140 distinct package/type names and 130 packages.
The reader refuses symlink traversal, bounds the read, hashes the complete
file and reads it again after the audit. Changed input requires a separately
reviewed source binding; do not remove the hash or shape checks to admit it.

## Native build and invocation

The reviewed source transaction should install only `Android.bp` and
`audit.cpp`, both mode 0644, at:

```text
device/xiaomi/nezha/tools/vintf-definition-audit/
```

This README stays in the workspace. The two source files inherit the existing
device namespace, already exported through `PRODUCT_SOONG_NAMESPACES`. No
parent Blueprint, Makefile, BoardConfig, policy file or product package selector
needs changing. Both new files must nevertheless appear in the exact device
tree and source inventory. Preserve the predecessor receipts; do not hide
additional files from a closed tree verifier or modify its historical result.

Build the single ordinary host target
`nezha_unlevelled_aidl_metadata_audit` through the existing guarded build path,
using the selected bka/bp4a configuration and sole authorized source-volume
owner. Do not add the tool to `PRODUCT_PACKAGES`. No replacement source sync,
second writer VM, visibility override or relaxed build check is part of this
workflow. Normal graph and output-log changes require fresh input qualification
before later checks that depend on those records.

The Blueprint follows the pinned `checkvintf` static host linkage and adds
BoringSSL `libcrypto` for SHA256. Its direct libraries are `libaidlmetadata`,
`libvintf`, `libcrypto`, `libbase`, `liblog`, `libutils` and `libtinyxml2`, with
static libc++. It is a 64-bit Linux host target, not an Android partition
component.

Use the real AIDL metadata producer chain:

```text
aidl_metadata_json -> aidl_metadata_parser -> metadata.cpp -> libaidlmetadata
```

Record the actual generated paths, identities, compiler/link inputs and host
binary from the ordinary build. The metadata library's private generators
remain internal dependencies; this tool does not need them made public.
Never create metadata entries from the matrix or vendor manifest to manufacture
a pass. The singleton includes dependencies exported to Make, so a missing name
means absent from this build's metadata, not necessarily absent from every
source directory.

After qualifying the actual executable and dependencies, use the existing
bounded native observer with read-only source, OUT and inputs:

```text
nezha_unlevelled_aidl_metadata_audit /work/out/nezha-user-policy-20260827T2220Z/target/product/nezha/system/etc/vintf/compatibility_matrix.device.xml
```

The enclosing runner must bind the real executable path and hash, source and
metadata provenance, exact argv, complete stdout/stderr, native exit status,
sandbox observations and input postchecks. It must enforce finite memory, CPU,
wall-time and output bounds. `AidlInterfaceMetadata::all()` constructs its
vector before the audit can check metadata sizes, so application limits alone
are insufficient. This invocation does not access a phone.

## Result and limits

The tool writes one JSON object. A completed audit includes the matrix identity,
actual metadata counts, matching provider modules and every missing name with
its affected tuples. The operation is
`audit-unlevelled-device-matrix-aidl-name-presence` and `schema_version` is 1.

| Exit | Meaning |
| --- | --- |
| 0 | Completed audit with no missing names |
| 65 | Missing names, or an input/shape error; inspect `audit_completed` |
| 64 | Wrong argument or path |
| 74 | I/O failure |

Only a complete zero exit with `audit_completed=true`,
`metadata_name_presence_passed=true`, no missing names and valid enclosing
evidence establishes this scoped result. A completed audit with missing names
sets the first field true and the second false. An input error sets
`audit_completed=false`; it is not a completed definition check. Truncated
output, signals, resource failures and failed postchecks cannot supply a pass.

The lookup reproduces the pinned upstream name-set rule: include metadata
types only when their module's stability is `vintf`. Duplicate type rows are
counted and deduplicated; multiple provider modules remain visible. Duplicate
module names are rejected because the pinned generator emits one row per map
key. Metadata processing is bounded to 100,000 modules, 1,000,000 type rows,
4,096 bytes per identifier and 64 MiB of aggregate identifier text; matching
provider text is additionally bounded to 1 MiB.

This metadata also contains user-defined types. Name presence does not prove
interface kind, AIDL versions or hashes, instance existence, method/transaction
ABI, service registration or hardware behavior. These fields, along with AVB,
complete input compatibility and ROM readiness, remain false in the result.
Kernel policy capability, bootloader AVB support, signed image-chain admission,
OTA and an explicitly authorized first boot require separate evidence.

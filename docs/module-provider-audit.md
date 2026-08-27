# Nezha static module provider audit

Every recorded symbol-version expectation across all **914 captured module
instances** has a CRC-matching candidate in the captured kernel or module set.
This covers **637 distinct module binaries and 36,963 expectations**. It does
not prove that the candidate provider is available at the consumer's loading
stage, selected by the loader, or compatible beyond its recorded CRC.

The [aggregate record](../research/module-provider-audit.json) extends the
[selected kernel-export check](kernel-export-contract.md) and
[ZRAM provider plan](zram-module-plan.md); their historical records remain
unchanged. The kernel and modules still come from the user-provided modified
Xiaomi.eu ZIP, SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Its origin and URL remain unverified, and its recorded AVB failures are
unchanged. This analysis does not adopt firmware or change build inputs.

The exact 39,963,136-byte kernel Image has SHA256
`4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8`.
The audit reuses its corroborated 8,897-export map. Module parsing deduplicates
only whole-file SHA256 values, including appended signatures: 277 binaries
occur twice and 360 once. Every location/path remains separate: 430 vendor
ramdisk instances, 381 vendor_dlkm instances and 103 system_dlkm instances.
The original request order and duplicate load-list entries are retained.

The candidate pool includes the kernel and **all three module locations**.
These counts therefore describe consumers, not proven stage availability:

| CRC comparison | Per distinct binary | Per captured instance |
| --- | ---: | ---: |
| Matching kernel export | 31,686 | 42,946 |
| One matching module payload | 5,259 | 7,466 |
| Multiple matching module payloads | 18 | 27 |
| Total | 36,963 | 50,439 |

The first total contains 36,326 ELF undefined symbols plus 637 synthetic
`module_layout` expectations; the second counts the same evidence once per
captured copy. There are 6,684 distinct symbol names and 6,685 name/CRC pairs.
No expectation lacks a matching captured provider. That does not mean every
candidate is interchangeable: the only ten duplicated export names are the
two zsmalloc families' shared `zs_*` names. Nine CRCs agree across families;
`zs_malloc` is `0x1804f5bc` for vendor and `0x36f39fe1` for GKI. The two zram
binary variants, occupying three captured instances, retain this wrong-family
conflict. The existing pair-selection requirement is not relaxed.

The module reader accounts for all **4,828 exports**: 2,872 normal and 1,956
GPL exports, including 437 data objects and 4,391 functions. It checks all
14,484 export relocations against the pinned ACK format at
`f1bdb13583da85a47fcf1632a78ef52d6e6da651`. Each record has three AArch64
PREL32 RELA references. CRC words are direct little-endian 32-bit data;
`__crc_*` symbol values are section offsets, not checksum values. Normal and
GPL symbol/CRC tables pair by their separately sorted indexes. Unsupported
layouts and nonallocated export, CRC or version tables are rejected. Different
payloads sharing the consumer's internal module name are retained in the
inventory but excluded as external providers; none affected this stock audit.
[Export encoding](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/include/linux/export-internal.h),
[module linker ordering](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/scripts/module.lds.S),
[loader section and identity handling](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/kernel/module/main.c).

All 637 binaries have basic and extended version tables, and every basic
entry agrees with its extended counterpart. Extended records take precedence.
Rust binder has 166 basic and 226 extended entries: its 60 additional names
are 56–117 bytes long and cannot fit the basic name field. There are no weak
undefined references or undefined symbols lacking a recorded CRC in this
corpus. Missing version evidence and optional weak references would be
different findings from a CRC mismatch, not permission to bypass checks.
[Version generation](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/scripts/mod/modpost.c),
[loader version checks](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/kernel/module/version.c).

Among CRC-matching candidates, all required nonempty namespaces have exact
`import_ns` declarations, and no GPL declaration conflicts were found.
Repeated license fields retain their order: modpost checks every declaration,
while the loader uses the first. These checks establish static declarations,
not actual licensing compliance, loader admission or signature trust. The
public source pin describes the formats; it does not identify the exact
source that produced the stock binaries.
[Accepted license strings](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/include/linux/license.h).

An independent format census agrees on all 637 payloads and 914 instance
bindings. All 914 earlier import-audit records also match. Pinned NDK
28.2.13676358 `llvm-readobj`, SHA256
`37e565359be0c9f2868348dd314416a420d137ee84c891ec8474cf7d29cfd995`,
separately corroborated every export CRC, class, index and both table-label
file offsets across 290 exporting binaries. Its 625 commands did **not**
independently verify export relocations or namespace string values.

The final observer rehashed 943 distinct input files covering 1,859 receipt
references, plus all 1,250 LLVM stdout/stderr files, and independently recounted
the classifications without importing either producer. This is output
corroboration, not another firmware acquisition or a fresh ELF parse.

Private evidence is under
`artifacts/source-contracts/nezha-full-module-audit-v1/`:

| Final receipt | SHA256 |
| --- | --- |
| `result-v2/receipt.json` | `a19a8da010446dfaba4f5e902091912efd54f57cb1ee1de05db43925e5a64a99` |
| `llvm-readback-v1/receipt.json` | `c58781b550608defd5552c6d6eda4ed786915d35d34a854abe71d8de0012d581` |
| `final-readback-v1/receipt.json` | `31fa6168b902a14b89ef34ff72f543a29af97e4211b7bce94e9f450b14bfd015` |

The provisional `result-v1`, frozen producer, failing regression logs and
unused mixed JSON/hex LLVM probe remain intact. The final reader adds the
allocated-section and same-name-provider guards found during review; actual
stock results are unchanged. It passed 40 synthetic tests, the LLVM observer
passed 12, and the sealed private audit includes 1,029 workspace tests plus
shell syntax validation. Tracked tests check only public metadata and require
no firmware, LLVM tool, phone, guest or network.

Module signatures, protected-symbol/KMI policy, dependency closure and load
ordering, actual provider selection, full ABI behavior and device operation
remain unverified. No firmware, module or signature bytes were changed, and
no phone, guest, mounted image or module execution was used. Native-feature
compatibility still requires corresponding device tests.

# Nezha kernel export CRC contract

The exact captured kernel exports CRCs matching **all 244 remaining vendor
zram/zsmalloc expectations and all 115 GKI expectations** from the earlier
[provider plan](zram-module-plan.md). None is missing or mismatched. These are
359 family expectations covering **263 distinct kernel symbols**, with 96
symbols shared between the families. This closes the selected CRC-evidence
gap; it is not full kernel ABI compatibility or a successful module load.

The [aggregate record](../research/kernel-export-contract.json) is additive.
The historical ZRAM record and its private receipts remain unchanged, including
their earlier statements that kernel exports had not yet been checked. Its
ten pair-owned allocator expectations per family remain separate from this
kernel comparison. Mixing the vendor and GKI pairs still fails on `zs_malloc`.
No CRC, module, load list or kernel byte was patched.

The input is the 39,963,136-byte ARM64 `Image` with SHA256
`4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8`, release
`6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k`. Its captured IKCONFIG
has SHA256 `73fa878baa4c748b2139e7acb4ed396d2056ca8ed71b565ded6f96b3558a98cd`
and enables KALLSYMS, KALLSYMS_ALL, PREL32 export references and MODVERSIONS.
The input provenance remains the user-provided modified Xiaomi.eu ZIP,
SHA256 `b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Its URL and origin are unverified; its recorded AVB failures are unchanged.
This result does not authenticate the package or adopt different build inputs.

Two independently written readers decoded the same Image using the pinned ACK
format at `f1bdb13583da85a47fcf1632a78ef52d6e6da651`. They agree on all
**8,897 exports: 3,375 normal and 5,522 GPL exports**, including every CRC,
record, target, name and namespace offset. They share an input and format
reference, not independent firmware acquisitions. The source reference does
not establish which exact source produced the captured kernel.

Each reader validates all 125,924 compressed kallsyms names, 492 name markers,
256 token strings/indexes and the complete sorted 24-bit name-index
permutation. Both readers cross-check eight kallsyms self-symbols and `_text`
to map file offsets. The primary reader additionally checks `_end` against
the declared memory extent. The raw relative-base pointer is not trusted for
that mapping: ARM64 build flags can leave absolute relocations unapplied.
[Kallsyms generator](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/scripts/kallsyms.c),
[ARM64 flags](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/arch/arm64/Makefile).

The recovered linker boundaries are file offsets; ends are exclusive:

| Section | Start | End | Records | Bytes per record |
| --- | ---: | ---: | ---: | ---: |
| `__ksymtab` | 25,714,272 | 25,754,772 | 3,375 | 12 |
| `__ksymtab_gpl` | 25,754,772 | 25,821,036 | 5,522 | 12 |
| `__kcrctab` | 25,821,036 | 25,834,536 | 3,375 | 4 |
| `__kcrctab_gpl` | 25,834,536 | 25,856,624 | 5,522 | 4 |

An export record has three signed 32-bit displacements, each relative to its
own field at offsets 0, 4 and 8. CRC records are direct little-endian unsigned
32-bit values, not addresses or displacements. The linker sorts each normal
or GPL symbol/CRC table by name, allowing pairing by index. Every recovered
export also matches its `__ksymtab_<name>` label and target symbol in kallsyms.
Individual `__crc_*` names are filtered out of kallsyms, so their addresses are
not the CRC evidence.
[Export encoding](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/include/linux/export-internal.h),
[linker tables](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/include/asm-generic/vmlinux.lds.h),
[symbol filtering](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/scripts/mksysmap).

For example, `module_layout` occupies normal-table index 1,983. Its export
record is at file offset 25,738,068 and its CRC at 25,828,968. Both readers
recover `0xe976b219`, matching both selected module families.

Merged export strings may share suffixes. Also, 58 export targets lie beyond
the file bytes but within the Image's declared 40,697,856-byte memory extent,
which includes BSS. These are valid value references; names and namespaces
must remain file-backed. That memory extent is not a physical partition
capacity measurement. The readers reject unsupported or ambiguous layouts
instead of guessing an address or CRC.

The only nonempty namespace among the selected kernel imports belongs to
vendor zram's `si_swapinfo`: `MINIDUMP`. A separate bounded read of the exact
vendor zram ELF `.modinfo` section finds `import_ns=MINIDUMP` and
`license=Dual BSD/GPL`. This establishes the static declaration, not namespace
or GPL license admission by a running loader.

Private artifacts remain under
`artifacts/source-contracts/nezha-kernel-exports-v1/`. The record binds the
producer hashes, ten pinned source files, complete private export maps and
comparison outputs. The final corroboration rehashes 29 bound input records:

| Receipt | SHA256 |
| --- | --- |
| `result-v1/receipt.json` | `840959f47afc410c5bab307275badbb91fa225cf8b4e305d42946fc615948943` |
| `independent-v1/receipt.json` | `0c0440a6ed599c711e8df304d89e34df127ef3cdbeb053a99e61a4aa691d6a1b` |
| `corroboration-v1/receipt.json` | `4ae03a7d08afe2a16e91f5e6f38068906882ee56ff0788555f4e24e77d2072f2` |

The primary reader passed 15 synthetic tests, the independent reader passed
18, and the `.modinfo` observer passed two synthetic checks. Tracked workspace
tests check this public record's bindings, arithmetic and limits using only
the standard library. They do not repeat private firmware parsing.

Signature trust, protected-symbol policy, complete ABI behavior, loader
admission and actual loading remain unverified. No phone, guest or mounted
image was used, and neither firmware nor kernel source was executed. The
selected comparison does not cover all 914 stock module instances or prove
that any native feature works.

A later complete audit can reuse the kernel export map, deduplicate parsing
by module payload hash and retain every instance's loading stage. It must
also inspect module-provider exports: a symbol absent from the kernel may
come from another module. Provider ambiguity, namespaces, load dependencies
and signature policy need separate checks. That larger inventory has not
been started by this slice.

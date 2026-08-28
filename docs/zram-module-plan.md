# Nezha zram and zsmalloc provider plan

The captured vendor `zram` and `zsmalloc` form a matching pair, and the captured
GKI modules form a separate matching pair. **All ten allocator-symbol CRCs
match within each pair. Mixing the pairs fails on `zs_malloc`.** The integration
plan keeps the vendor pair for vendor and recovery loading and excludes the
GKI pair from normal system-module loading, following the captured selection
policy. This is a static provider and loader contract, not a successful module
load or kernel compatibility test.

The inputs remain the user-provided, modified Xiaomi.eu package, SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Its origin is unknown and its retained AVB checks fail as described in the
[boot contract](boot-contract.md). Nothing in this analysis authenticates that
package or changes those failures.

The sanitized [record](../research/zram-module-plan.json) contains all four
module hashes, six installed-file instances, list hashes and positions, source
pins, export evidence, and requirements. New private evidence is under
`artifacts/source-contracts/nezha-zram-plan-v1/`. Its additive receipt has SHA256
`44669f2a0d2830957f3227ced8bd79d155b82a32c82e00bd3462b3b4c38efa41`.
It hashes 84 artifacts, including reviewed inspectors, selected inert module
bytes, 13 stock lists, two safely captured loader scripts, and 34 pinned source
files. Original boot and CRC receipts were preserved.

| Pair | zram bytes | zsmalloc bytes | `zs_malloc` import and provider export | Provider CRC file offset |
| --- | ---: | ---: | --- | ---: |
| Vendor ramdisk / vendor_dlkm | 266,528 | 56,296 | `0x1804f5bc` | 236 |
| GKI system_dlkm | 77,338 | 62,066 | `0x36f39fe1` | 208 |

The vendor ramdisk and vendor_dlkm copies are byte-identical within each
module name. The system modules have the same internal names but different
bytes; those names are not interchangeable provider identities. Both zram
variants declare `depends=zsmalloc`. No other captured module imports a `zs_`
symbol or declares a dependency on either name.

This extends the earlier import-versus-import comparison. The new inspector
reads `__crc_zs_malloc` from the provider's unrelocated `__kcrctab_gpl`, checks
its corresponding `__ksymtab` record and all three AArch64 PREL32 relocations,
and resolves the exported name to a defined global function. It repeats this
for every export in the six instances. NDK 28.2 `llvm-readobj` independently
agrees on all **36 export records**, their symbol offsets and CRC bytes. The
basic and extended importer tables also agree with the original audit.
[The pinned ACK encoding](https://android.googlesource.com/kernel/common/+/f1bdb13583da85a47fcf1632a78ef52d6e6da651/include/linux/export-internal.h)
stores these CRCs as direct 32-bit values; they are not symbol addresses.

The other nine allocator CRCs agree across both families. Vendor zsmalloc
also exports `zs_lookup_class_index` and `zs_map_object_straddle_info`; the
captured GKI provider does not. Both captured zram variants import the same
ten `zs_` names. Consequently, a vendor zram/GKI zsmalloc combination, or the
reverse combination, is rejected by this static CRC comparison even though
nine allocator symbols agree. Do not patch CRCs to make those combinations
appear valid.

The required loading stages are:

| Stage | Captured requests and selection | Required pair behavior |
| --- | --- | --- |
| Normal first-stage ramdisk | Neither name occurs in the 157-entry `modules.load`, or its captured hard/soft dependency closure | Keep neither pair in this stage's requested loads |
| Recovery first-stage ramdisk | Vendor `zram` occurs at request 152 and `zsmalloc` at 408 of 435 | Use the ramdisk vendor copies; dependency loading must insert zsmalloc before zram |
| Normal system_dlkm | Its 82-entry list includes GKI zsmalloc at 3 and zram at 13, but the vendor-supplied system selector excludes both | Keep the GKI payloads separate and excluded from loading |
| Normal vendor_dlkm | Vendor zram is request 1 and zsmalloc is 257 of 576 | Use the vendor_dlkm copies; zram's dependency must select the matching vendor allocator first |

Positions count nonempty, noncomment entries, not physical text-file lines.
The raw lists retain their order and duplicates. The three `modules.dep` files
explicitly pair each local zram with its local zsmalloc. A regenerated dependency
index must preserve that pairing after Android flattens installation paths.
For the candidate's first-stage implementation, the pinned Evolution
[dependency loader](https://github.com/Evolution-X/system_core/blob/241488ea392c01079941d86ddc458b8a0c9ae6e1/libmodprobe/libmodprobe.cpp#L63)
loads hard dependencies before inserting the requested module. This source
reference does not identify the stock vendor modprobe executable.

The captured `init.qti.kernel.rc` configures `exec_start gki.modprobe` before
`start vendor.modprobe` during `early-init`. Its two scripts provide more detail
than the lists alone:

- The system script requires a `modules.load` file to exist, then discovers
  **all** module files in that directory tree. It filters the two names using
  `/vendor_dlkm/lib/modules/system_dlkm.modules.blocklist`. There are 103
  captured modules under its selected `/lib/modules` tree and **101 eligible
  paths after that filter**, including 21 not in `modules.load`. Discovery
  order is not recorded. A successful first modprobe call is required before
  the script attempts the remaining paths concurrently; eligibility is not
  a count of successful loads.
- The vendor script reads `modules.load`, retains one numbered occurrence per
  module name using its sort pipeline, restores numeric order, and applies
  general and audio blocklists. It invokes its first selected module
  synchronously and the remainder concurrently. Neither pair member is in
  the captured general blocklist. Its readiness-property write after waiting
  does not independently prove every child load succeeded.

The scripts were captured as two regular EROFS files with input and output
hash checks. They were read as text, never executed. Neither the stock vendor
modprobe implementation nor any runtime trace was validated. Do not turn the
script's parallel work into a claim of a fully ordered or successful boot.

The inspected v5 product snapshot did not request the vendor-side selector
copy. Its device makefile was 822 bytes with SHA256
`81f49aa8ece7f367457094684b159b9a2182557c298262b2eb5d3c692b57be9f`;
that historical observation is retained in the record. The later authored
fix, commit `3de727e76a5d7fb92bf25682aabe0ffc3c0235bd`, reads the verified
kernel input makefile at product scope and requests the exact vendor-side
copy, while preserving the separate system-stage blocklist. It rejects a
missing selector instead of silently dropping it. See the
[kernel wrapper](../kernel/xiaomi/nezha/README.md) and
[device product](../device/xiaomi/nezha/device.mk). The fixed makefile is
1,611 bytes with SHA256
`81243400a8c5bbd2e8fb83d3f250ccffcd4fa60f4be5b4bb1266d5cc0a07adac`.
At this review checkpoint, the fix had not been installed in the guest or
verified in a completed target image. An authored copy rule is not a loader
or runtime result.

Later checks resolve two parts of that historical checkpoint. The
[v6 boot/DLKM image inspection](boot-dlkm-build.md) verifies the vendor-side
selector and all 484 DLKM module payloads inside the built images. The
[factory comparison](factory-input-reuse.md) finds those DLKM bytes unchanged.
The [kernel-export check](kernel-export-contract.md) and
[full module-provider audit](module-provider-audit.md) find CRC-matching
captured candidates for the remaining imports. They retain the two-family
`zs_malloc` conflict and do not establish stage availability or actual loading.

The candidate integration needs these concrete checks before replacing or
shipping module images:

1. Preserve all four distinct payloads, their signatures, and their separate
   ramdisk/vendor/system identities. Keep the normal ramdisk list unchanged;
   use the vendor pair in recovery and vendor_dlkm. Do not flatten different
   families into one staging directory or choose one by basename alone.
2. Install the two-name selector at
   `vendor_dlkm/lib/modules/system_dlkm.modules.blocklist` for the retained
   stock script, and the same exclusions at
   `system_dlkm/lib/modules/modules.blocklist` for a loader using the system
   directory's blocklist. The existing kernel wrapper's
   `BOARD_SYSTEM_KERNEL_MODULES_BLOCKLIST_FILE` request alone does not prove
   installation at the stock script's different vendor-side filename.
   Read both paths back from completed target images. **Do not add these two
   exclusions to the general vendor blocklist:** that would block the selected
   vendor pair too.
3. Generate dependency indexes for each installed stage and verify that a
   zram request selects the corresponding allocator before insertion. Check
   normal boot and recovery separately. If replacing the stock system script
   with list-driven loading, explicitly review the 21 additional discovered
   modules; `modules.load` is not an equivalent description of its behavior.
4. Compare remaining imports against authoritative kernel and module-provider
   exports, namespaces and KMI lists. Beyond exports within the pair, there
   are 244 distinct vendor import expectations and 115 GKI expectations still
   outside this check, including `module_layout`. Their providers may be the
   base kernel or other modules. The observed 4 KiB kernel config sets both
   `CONFIG_ZRAM=m` and `CONFIG_ZSMALLOC=m`; it is not a kernel export table.
5. Verify signature trust, protected-symbol policy and actual loading before
   claiming compatibility. Vendor modules have no appended signature marker;
   the system pair has previously inspected signature envelopes, not verified
   trust. Keep MODVERSIONS, signing, KMI, SELinux and AVB checks enabled.

For a source replacement, the reviewed MiCode reference remains
`45705be1220b4cfa8100516ad86711656c0b634e`, with its declared ACK base
`f1bdb13583da85a47fcf1632a78ef52d6e6da651`. These are source inputs to adapt,
not established source identity for the captured binaries. Its
[`mm/zsmalloc` rule](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/mm/modules.bzl)
and [zram rule](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/drivers/block/zram/modules.bzl)
give concrete provider and consumer targets. Build both together using the
chosen base's generated headers and `Module.symvers`, then check the outputs
against this contract. The published zram rule also declares a QPaCE dependency;
the Canoe dictionary requests its config as `n` and the header contains disabled
stubs. No captured qpace module or zram qpace import was found. That is a source
dependency to account for, not permission to invent a runtime driver or infer
an effective Nezha configuration from a sibling dictionary.

One exact source gap remains: the captured vendor zram exports
`wakeup_xswapds` with CRC `0xd272d446`, while a search of every tracked file at
the pinned MiCode commit finds no such symbol. Rebuilding its published rule
alone therefore does not establish equivalence to the captured vendor module.
Both reference headers have the same literal `zs_malloc` prototype; the cause
of the different binary CRCs has not been established from that text. The
[configuration audit](../kernel/xiaomi/nezha/config-audit/README.md) provides
separate stock-derived assertions without adopting sibling signing reductions.

The new provider inspector passed 11 synthetic offline tests. The tracked
tests check record consistency, pair selection, load positions, provenance,
the two required blocklist paths, and explicit validation limits. These tests
do not require firmware, a phone, a container, or a kernel build.

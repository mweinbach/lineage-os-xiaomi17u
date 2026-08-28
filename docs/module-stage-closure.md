# Module dependencies by boot stage

The selected stock module sets have CRC-matching kernel or module candidates
within their dependency graphs, with **732 vendor expectations depending on
earlier stages**. This advances the [global provider audit](module-provider-audit.md)
to stage selection and static dependency order. It does not prove successful
loading, full ABI compatibility, signature trust, or a booting ROM.

| Scenario | Requests / unique | Hard closure | Kernel CRC matches | Local hard predecessors | Earlier-stage conditions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Normal first stage | 157 / 154 | 154 | 6,732 | 810 | 0 |
| Recovery first stage | 435 / 424 | 426 | 17,457 | 2,888 | 0 |
| Normal system loader | 101 / 101 | 101 | 5,070 | 529 | 0 |
| Normal vendor loader | 380 / 380 | 380 | 19,787 | 3,197 | 732 |

Counts include one implicit `module_layout` expectation per consumer. Normal
and recovery are alternative trajectories, so these rows are not a disjoint
population census. Recovery adds `hdcp_qseecom_dlkm` and `smmu_proxy_dlkm` beyond
its listed set. No selected closure has a missing hard path, hard/pre cycle,
or ambiguous local CRC-matching provider.

The 732 vendor expectations span 144 consumers, 289 symbols and 51 provider
payloads. Of these, 718 require selected normal-ramdisk providers; 14 require
system providers: `rfkill` for `btpower`/`cfg80211` and `libarc4` for
`mac80211`. Eligibility in an earlier stage does not establish that a provider
was successfully admitted before its consumer.

The captured system script treats `modules.load` as an existence gate, then
discovers 103 paths. Its vendor-side selector excludes GKI `zram`/`zsmalloc`,
leaving **101 eligible paths: 80 listed and 21 additional paths**. The 82-entry
file is not the complete selection. Discovery order is unknown. Vendor's 576
rows contain 381 names; filtering excludes only `ipclite_test`, leaving 380.
Its unique first request is `zram.ko`; retained positions of duplicate rows
are unproven. Both scripts gate concurrent remaining requests on one
synchronous request, but do not check every background result. System can exit
zero without successful loads; vendor readiness does not establish them either.

One recovery and 15 vendor soft-pre requests lack a local target. Six of the
nine vendor target names occur in the selected normal ramdisk. The other three
are `phy-msm-snps-hs`, `qcom-arm-smmu-mod` and `subsys-pil-tz`, with no captured
module or matching alias. The reference loader ignores soft-dependency failures;
this does not prove an optional hardware function works or justify substituting
another device's driver.

Recovery and vendor each have ten `zs_*` expectations satisfied by their local
vendor allocator predecessor. Nine also have global GKI matches, but
`zs_malloc` differs: vendor requires `0x1804f5bc`, while GKI provides
`0x36f39fe1`. Preserve the vendor pair and system selector; mixing families
remains incompatible with this recorded expectation.

The model uses [Evolution system_core at the pinned revision](https://github.com/Evolution-X/system_core/tree/241488ea392c01079941d86ddc458b8a0c9ae6e1).
Hard requests recurse in reverse recorded order; raw soft owners, aliases,
cache state and sequential/parallel blocklist policies remain distinct. The
packaged bootconfig requests parallel loading, but runtime `/proc/bootconfig`,
dynamic callers and scheduling were not observed. Sequential traces are
counterfactual diagnostics. `EEXIST` cannot identify the active payload.

Factory scripts and module metadata match the corresponding Xiaomi.eu captures.
An inert inode read confirms `/vendor/bin/modprobe` points to `toolbox`, and
`/vendor/lib/modules` points to `/vendor_dlkm/lib/modules`. All 381 vendor module
dependency paths map within that captured namespace. The stock toolbox source,
runtime mounts and access remain unverified. Package origin remains unauthenticated;
the [factory validation](factory-firmware-validation.md) and
[modified Xiaomi.eu input](provided-firmware.md) retain separate provenance.

All 950 bundle files, including 914 module instances, were freshly hashed.
An independent graph implementation agrees on all four closures and all 732
vendor consumer/symbol/CRC/provider tuples. Final readback checked 1,001 inputs
and six outputs twice, also preserving the prior results. Validation passed
46 model tests, 13 inode-reader tests, seven independent graph tests, 11 final
checks, and the then-current 1,061 repository tests plus shell syntax checks.
The public [record](../research/module-stage-closure.json) binds the private
receipts and preserved provisional results; its offline tests check that public
metadata without requiring firmware or host tools.

This slice changes no build inputs and performs no module loading, firmware
execution, image mounting, phone access, or guest/source/OUT modification.
Namespace/GPL declarations do not establish runtime admission. Full ABI,
signature trust, successful stage availability, native features and recovery
remain separate gates. The recovery closure proves neither TWRP operation nor
protection against bootloader corruption.

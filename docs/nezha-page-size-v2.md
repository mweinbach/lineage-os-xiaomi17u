# Current-provider 4 KiB bring-up profile

The user explicitly authorized a 4 KiB bring-up path: “We don’t need 16kb if
it’s hard.” The separately versioned
[`nezha-stock-4k-bringup-v2`](../config/nezha-page-size-profile-v2.json) binds
that development choice to the selected stock kernel and current v7 framework
provider inputs. It does not establish a native 4 KiB build or boot result.

The later **v13ja installation and `pagesize-v13j-1` component build passed**
on August 31, 2026 UTC (August 30 in New York). That separate native evidence
verifies the generated 4096 maximum and unchanged strict checks; the descriptor's
original evidence scope remains unchanged. See the
[current integration checkpoint](nezha-page-size-v2-integration.md) and
[workspace status](workspace-status.md) for the remaining gates.

This changes the selected build maximum from 16384 to 4096. It does **not** fix
the 22 known 16 KiB ELF alignment failures or pass their VTS requirements.
Those remain recorded, including the vendor API 202504 compatibility gap.
The pinned build uses the same maximum for new source linking and preserved
prebuilt checking, so this choice affects newly linked platform binaries too.
The source analysis is retained in the [historical profile documentation](nezha-page-size.md).

The historical v1 descriptor and its adoption-hold evidence remain unchanged.
Its SHA256 is `9d180aeeb13e0c04a4f2726bf94ad6651e1052cb5f9162359c147814bc6607ca`
(13,226 bytes). The v2 descriptor records that predecessor explicitly and has
SHA256 `bed228b0595ef2dc1dd814e98c0966ba9b9452b542de50354db522e2420bed1e`
(15,567 bytes). Select v2 explicitly through the existing generator option:

```sh
--page-size-profile config/nezha-page-size-profile-v2.json
```

Omitting the option preserves previous rendering. The
[consumer integration note](nezha-page-size-v2-integration.md) describes
generator admission and its separate native-build gate. Existing image
delivery evidence predates this page-profile change and cannot be combined
with it as though a current native build had already passed.

The profile retains these settings, with their existing value and duplicate
definition guards:

```make
PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 4096
PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE := true
PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO := true
```

ELF and symbol checks remain required. This profile introduces no ELF header
or opcode changes, ignore flags, fake API levels, low-RAM exceptions, boot-mode
properties, or VTS filters. Normal Android SELinux remains enforcing; the
existing recovery-only exception is unchanged. Complete-ROM readiness,
native-build, hardware, 16 KiB and VSR claims remain false in the descriptor.

## Exact current inputs

Independent host inspection rehashed the actual kernel receipt, Image and
configuration, then separately parsed the arm64 header and embedded IKCONFIG.
The selected Image is also byte-identical to the extracted factory package
kernel. Header flags 10 encode 4096-byte pages; the complete embedded config
exactly matches the reference file and uniquely records `CONFIG_PAGE_SHIFT=12`,
`CONFIG_ARM64_4K_PAGES=y`, and disabled 16K/64K page options. This establishes
the compiled Image configuration, not the page size of a running phone.

| Input | Bytes | SHA256 |
| --- | ---: | --- |
| Kernel Image | 39,963,136 | `4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8` |
| Kernel config | 220,352 | `73fa878baa4c748b2139e7acb4ed396d2056ca8ed71b565ded6f96b3558a98cd` |
| Kernel receipt | 457,217 | `4ce149410ba2ab5f24653ebd8c4020a7401ba5172e2648c19f3c8bf726a7e9bb` |
| Current provider contract | 30,596 | `7e514674abbf7739efb2e7520d79e7c1f302de773a3e49c0d683aba7c51fc8a7` |
| Current v7 provider receipt | 13,737 | `c8d2ec1822e45181f45af57fd2389a9939eb635e14866dce41b85736fe65513e` |

`providers.files` preserves all 26 original native payload identities and
their recorded `PT_LOAD` alignments. `providers.payload_derivations` exactly
matches the current provider contract and receipt. One
`providers.effective_file_overrides` row binds the already reviewed Miracast
output separately: original SHA256 `45880ab976336616c2ff91753d176d3d10e175564005d51266359316ad965541`
becomes `06ffed0abd8cd7258c44e672e7fde4377f39626dddbed59eef70f60426c08082`.
Both are 119,560 bytes. That existing v7 recipe changes only the dependency
version byte at offset 17588 (`V2` to `V4`); its
[audio compatibility review](../research/framework-provider-audio-compatibility.json)
remains the authority for that derivation. V2 does not select another blob or
authorize another transformation.

The actual provider proof reran the existing complete private-bundle verifier,
rehashed all 31 outputs from the prior host producer receipt, and inspected all
26 original/effective ELF layouts. The existing Miracast recipe reproduced its
already captured output in memory, with no file writes. ELF headers, complete
program-header tables and all `PT_LOAD` fields remained identical for every
original/effective pair. All 26 have alignment divisible by 4096; four have
alignment divisible by 16384 and 22 do not. This is static layout evidence,
not the complete native ELF, symbol or dependency check.

## Evidence and remaining verification

Ignored evidence is under `reports/nezha-page-size-20260830-v2/`:

- `independent-kernel-review.json`: SHA256
  `8f72c0ff90296e9d4311467b4efae8948987d76331686733fcd9a03408187814`,
  14,951 bytes. It includes direct header/IKCONFIG checks, the existing actual
  kernel admission helper, and 24 historical offline tests with zero skips.
- `current-provider-profile-proof.json`: SHA256
  `ec6e1c278d62e87c97d6b0541ff914e2ca2b02a15c4836fa0b05a968538ac946`,
  73,174 bytes. It binds 70 rehashed unchanged inputs and the read-only
  `verify_current_provider_profile.py` replay.

Eight public cross-contract tests in
`tests/test_page_size_profile_v2_contract.py` pass with zero skips. They check
the immutable predecessor, current contract/receipt, original inventory,
reviewed derivation/evidence, effective override, and retained compatibility
gaps without reading private artifacts. Generator admission tests are separate.

The later native result and captured product variables now prove that the
explicit profile is selected and the other checks remain active. The separate
26-provider ELF checks still require fresh successful native actions.
Packaging, AVB, complete-ROM compatibility, first boot and hardware validation
remain separate gates. No phone operation is authorized by this profile.

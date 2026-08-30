# Nezha stock-kernel 4 KiB bring-up profile

**Adoption is on hold. This is an unadopted experiment, not an approved
compatibility fix or the next native build path.** The active guest retains
the 16 KiB maximum and its strict checks; v13g is a host-only candidate.
Using `--page-size-profile` requires a separately resolved scope and
authorization. The user's requirement not to suppress failing checks remains
in force.

The optional `nezha-stock-4k-bringup-v1` profile was authored to match the
admitted stock kernel's actual 4 KiB runtime pages. That kernel evidence does
**not** justify lowering the required 16 KiB ELF threshold. Keeping the
checker enabled while lowering its threshold still removes the currently
failing 16 KiB requirement; it must not be presented as fixing those failures.
The authored profile and its historical tests are preserved for review, with
complete target-files and flash admission still false.

This profile does **not** resolve the known 16 KiB compatibility gap: 22 of the
26 preserved native framework providers have 4 KiB `PT_LOAD` alignment. The
pinned VTS tests require 16 KiB alignment for init and non-exempt arm64 ELF
files at this device's vendor API level, 202504. Those failures must remain
visible until a compatible kernel/userspace arrangement is established.

## Kernel and source evidence

The independently rehashed factory `boot/kernel` and both admitted kernel
bundles contain the same 39,963,136-byte Image:
`4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8`.
Its embedded IKCONFIG is 220,352 bytes with SHA256
`73fa878baa4c748b2139e7acb4ed396d2056ca8ed71b565ded6f96b3558a98cd`.
The extracted configuration explicitly contains:

```text
CONFIG_PAGE_SHIFT=12
CONFIG_ARM64_4K_PAGES=y
# CONFIG_ARM64_16K_PAGES is not set
# CONFIG_ARM64_64K_PAGES is not set
```

The raw arm64 Image header independently encodes 4 KiB pages. The kernel
release is `6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k`. This proves
the selected image's configuration, not every capability of the SoC or an
unexamined alternative kernel. Boot-image container page size and ELF segment
alignment are separate values.

The source audit used these pinned revisions; no upstream source is changed:

| Project | Revision | Relevant behavior |
| --- | --- | --- |
| `build/make` | `a438ca40c6ed779042f806142b1165ba1360a7b2` | `core/config.mk` derives the target maximum from `PRODUCT_MAX_PAGE_SIZE_SUPPORTED`; otherwise modern arm64 defaults to 16384. It separately accepts `PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE`. |
| `build/soong` | `cbcbea9e65503ca15b363a0b06dda88fdbcb0154` | `cc/config/arm64_device.go` uses the maximum for source linker flags; `cc/linker.go` passes the same maximum to the prebuilt checker. |
| `test/vts-testcase/kernel` | `8f4ac61303661ceb0d13609ba6007841ee4d17f2` | `pagesize_16kb/Vts16KPageSizeTest.cpp` requires init alignment divisible by 16384 for this vendor API, separately from kernel page-size checks. |
| `system/memory/libmeminfo` | `b12ca21f4a74714f00c12ef2a7db67ab1afb2692` | `libelfutils/tests/page_size_16kb/elf_alignment_test.cpp` checks non-exempt 64-bit ELF alignment at vendor API 202404 or later; there is no general OEM/system_ext exception. |

The current product-variable snapshot before selection used arm64/armv8-a,
vendor API 202504, maximum 16384, alignment checking true and no-Bionic-page-
size-macro true. The pinned build has no standard separate maximum for
platform linking and preserved-prebuilt checking. Therefore choosing 4096
also changes newly linked platform ELFs; it cannot guarantee a 16 KiB-aligned
init or other platform binary. No module ignore flag, fake API level, low-RAM
setting, boot-mode property or test filter is introduced.

Android's documentation also distinguishes the kernel's runtime page size
from the ELF maximum: 16 KiB-aligned ELF files can run on 4 KiB kernels, but
the reverse is not a general guarantee. See the [16 KiB build documentation](https://source.android.com/docs/core/architecture/16kb-page-size/16kb?hl=en)
and [page-size system properties](https://source.android.com/docs/core/architecture/16kb-page-size/system-properties?hl=en).
The exact pinned source above takes precedence for this checkout.

## Experimental interface, not approved for adoption

The following interface is documented for reproducibility of the existing
host-only experiment. Do not add it to the active build or treat it as the
default next step while the scope and authorization remain unresolved:

```sh
--page-size-profile config/nezha-page-size-profile.json
```

The Python API is `generate(..., page_size_profile=Path(...))`. It requires the
existing explicit factory and paired framework-provider capabilities plus the
already required kernel/vendor receipts. No receipt can implicitly select it.
The reviewed profile binds the exact kernel Image, extracted config, kernel
receipt, provider contract, provider receipt and all 26 native provider hashes.
It retains the list of all 22 known 16 KiB alignment gaps.

The only device payload change is in `generated/device-candidate.mk`:

```make
PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 4096
PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE := true
PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO := true
```

Each assignment has a value guard. The generator rejects duplicate or
contradictory page-size settings outside its exact rendered product and
rejects ignore flags and fabricated runtime properties. It rehashes the
actual Image/config and rejects missing, duplicate or contradictory kernel
symbols; these checks run again before candidate publication. Existing
provider verification still checks the entire private bundle.

The candidate also copies `config/nezha-page-size-profile.json` and adds the
portable `admission.json.page_size_profile` binding. That record explicitly
keeps 16 KiB/VSR compatibility, native component build, hardware and complete
ROM admission false. Portable validation verifies the copied contract and
bindings; it does not claim to re-inspect private inputs or a live kernel.
Without the option, previous payload rendering and admission fields remain
unchanged, and the new profile file is not read or copied.

Historical candidates retain their original control/receipt versions. A new
candidate must preserve that provenance or record a deliberately reviewed
control overlay; changing the generator does not authorize accepting old
private receipts under unrelated newer tool hashes. Native product-variable
output must be regenerated by the normal build, not prefilled to match this
profile. If a separately authorized experiment is established, its native
checks would need to confirm the selected values and retain all other strict
checks. Such an experiment would still not pass or waive the 16 KiB/VSR gate.

## Validation evidence and limits

Ignored evidence is under `reports/nezha-page-size-20260829/`:

- `independent-kernel-review.json` records direct Image/IKCONFIG/header checks.
- `provider-alignment-probe-v1.json` rehashes all 26 actual payloads and runs
  the exact pinned checker's alignment method at both maxima: all 26 satisfy
  4096; four satisfy 16384 and 22 fail it. This is **not** a full ELF checker,
  symbol/dependency, native component build or hardware test.
- `investigation-v1.json` binds the captured source and investigation inputs.
- `adoption-hold-v1.json` records the subsequent constraint review and hold;
  it does not alter the frozen profile, generator, tests or authoring receipts.

Offline tests in `tests/test_page_size_profile.py` cover explicit selection,
default payload identity, exact receipt/payload binding, kernel config
contradictions, duplicate selectors, false readiness claims, late input
changes and configuration-only admission. They use inert private fixtures;
real native build results and first Evolution boot must be recorded separately.
No phone mutation is authorized by this profile.

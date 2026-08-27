# Nezha source configuration audit

This recipe turns the captured Nezha IKCONFIG and pinned ACK/MiCode text into
reproducible, private configuration comparisons. **All 812 explicit assignments
in the pinned ACK GKI defconfig match the captured kernel configuration.** This
supports using that exact ACK configuration as a source reference; it does not
identify the complete source of the installed kernel or prove binary, KMI or
module compatibility.

The [auditor](../../../../scripts/kernel_config_audit.py) reads literal values
only. It never runs Starlark, Kconfig, Make, a compiler or a source script. It
does not resolve defaults, dependencies, `select` statements or generated
build flags. A symbol absent from a file remains **not observed**, never an
implicit `n`. Numerically equivalent values with different spelling remain
literal differences. Original file hashes and source line numbers are retained.

| Input | Exact pin |
| --- | --- |
| Captured stock IKCONFIG | SHA256 `73fa878baa4c748b2139e7acb4ed396d2056ca8ed71b565ded6f96b3558a98cd`, 220,352 bytes, 6,405 explicit symbols |
| Original boot inspection receipt | SHA256 `3615d62f4e4a61a11ff476ca47a245fa63a462136c53e688db66979f437879db`; its `kernel.config` artifact must match |
| ACK common | `f1bdb13583da85a47fcf1632a78ef52d6e6da651`, tag `android16-6.12-2025-06_r8` |
| ACK `arch/arm64/configs/gki_defconfig` | SHA256 `9cc3451168d5bfcffb1399696ff935263b48b5453c198a42d55e8af479feadab`, 20,882 bytes |
| MiCode vendor layer | `45705be1220b4cfa8100516ad86711656c0b634e`, `popsicle-w-oss` |

[recipe.json](recipe.json) binds all 17 selected input files by SHA256 and byte
length, with Git blob IDs for the copied MiCode sources. The local MiCode
checkout was clean and matched its pin; ACK files were retrieved from their
exact commit over HTTPS. The copied `android/ACK_SHA` must match the recipe's
ACK commit and tag. No VM, phone, Downloads file or existing source tree was
modified during this work.

The captured kernel is
`6.12.23-android16-5-g75e9b1c7ae7c-abogki463945075-4k`. Its parent remains the
modified, user-provided Xiaomi.eu package with SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
The origin is unverified and the package's AVB failures are unchanged. Matching
configuration text cannot authenticate that package. See the
[boot contract](../../../../docs/boot-contract.md) and
[MiCode review](../../../../docs/micode-popsicle-review.md) for those boundaries.

The completed audit on 2026-08-27 found:

| Comparison profile | Explicit requests | Same as stock | Different literal | Not observed in stock |
| --- | ---: | ---: | ---: | ---: |
| ACK GKI defconfig | 812 | 812 | 0 | 0 |
| Canoe vendor DDK dictionary | 441 | 4 | 40 | 397 |
| Canoe + Popsicle, comparison only | 449 | 4 | 41 | 404 |
| Canoe + Pudding, comparison only | 445 | 4 | 41 | 400 |
| Canoe + Pandora, comparison only | 444 | 4 | 41 | 399 |

There are 5,593 captured stock settings not explicitly requested by the ACK
defconfig. They are retained in the stock symbol map; this audit does not
explain their defaults or build-time derivation. Each sibling composition
overrides four common dictionary entries, with original and replacement source
locations recorded. None is adopted as a Nezha configuration.

A separate parser rehashed all 17 input files and reproduced every count in
all five profiles. Its private record is
`reports/kernel-config-independent-counts.json`, SHA256
`8a7cb863c9b19cbf014fcd7fe20d5aae73657b98b9b8afa7c3e5ba37ea119e9a`.
That check also did not execute the sources, evaluate Kconfig or verify a build.

The distinction between GKI and DDK is required by the source. MiCode
`kleaf-scripts/modules_register.bzl` generates the dictionary as a fragment for
`ddk_config` against a separate base kernel. The performance base defaults to
`//common:kernel_aarch64`; the dictionaries do not replace that kernel's
defconfig. The auditor rejects a profile that merges ACK base requests with
vendor/sibling DDK requests. It reads a single named dictionary of string
literals, not the surrounding Starlark build system.
[Pinned module configuration](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/45705be1220b4cfa8100516ad86711656c0b634e/kleaf-scripts/modules_register.bzl#L71-L83)

One recorded difference is `CONFIG_MODULE_SIG_ALL`: the Canoe DDK dictionary
requests `n`, while the captured GKI has `y`. Its `assertion_conflicts` entry
means a difference from the selected **GKI preservation values**, not a verdict
that the separate DDK configuration is invalid. It is a reason not to paste
that dictionary into a replacement GKI defconfig. The auditor generates no
signing-reduction fragment and does not alter module signing, KMI trimming or
verification policy. The 397 unobserved vendor settings likewise do not prove
that their drivers or external modules are missing.

The private run is
`artifacts/source-contracts/nezha-kconfig-audit-v1/result-v1/`. Its receipt SHA256
is `88b60ea98f6069dd286d6491f07e96c4493ab6fd82158186a6e0aa99d49dfbb5`.
The source-intake receipt is the sibling `intake.json`, SHA256
`b386673c9899d6abfc8d0171f75badf475798d206c0102a15aa761360fbd061a`.
The run produces only four JSON files:

- `stock-symbols.json`: all 6,405 observed values and their original line numbers.
- `literal-deltas.json`: every explicit request, stock observation, profile
  scope, comparison and ordered source override.
- `assertions.json`: 20 selected stock-derived GKI preservation checks covering
  4 KiB pages, MODVERSIONS formats, signing support, symbol trimming, CFI,
  SELinux, verity, vendor hooks and bootconfig.
- `receipt.json`: pinned input hashes, output SHA256 readbacks, counts and
  explicit non-build/non-compatibility results.

Existing evidence is immutable. Repeat the comparison into a new directory:

```sh
config_audit=artifacts/source-contracts/nezha-kconfig-audit-v1
python3 scripts/kernel_config_audit.py \
  --source-root "$config_audit/inputs" \
  --output "$config_audit/result-review-new"
```

To check later candidate GKI configuration text, add `--candidate-config PATH`
and `--expected-candidate-sha256 SHA256`, still using a new output directory.
The command exits `2` if any selected assertion is missing or differs, and
preserves that result in its new receipt. It exits `1` for invalid inputs and
`0` for a completed audit whose optional assertions passed. A completed audit
alone is not a compatibility pass. No candidate check was requested in the
recorded run; passing these selected assertions later would not establish a
complete or effective `.config`.

The recipe and tool reject duplicate assignments, duplicate dictionary keys,
calls, imports, comprehensions, implicit string concatenation, unsupported
syntax, source hash/size/commit disagreements, symlinked inputs, unsafe paths
and existing output directories. Offline tests use synthetic fixtures; they
need neither private firmware nor native tools, a phone or network.

The resulting source inputs still need the actual complete pinned Kleaf,
toolchain and external-module workspace before a kernel build. This slice
does not invent those modules, run a config solver or generate a Nezha build
target. It preserves the evidence needed to check the next generated GKI
configuration alongside the private Nezha DTS bundle, module CRC/signature
requirements and the recorded zram/zsmalloc selection policy.

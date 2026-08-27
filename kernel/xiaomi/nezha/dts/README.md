# Private Nezha device-tree source round trip

[recipe.json](recipe.json) pins the local DTC binary and the two MiCode
references used to prepare a private source baseline from **eight concatenated
stock DTBs and one Nezha DTBO entry**. It does not add raw DTS/DTB files to Git,
modify the reference checkouts, or define a working kernel build target.

From the repository root, with a new output directory:

```sh
python3 scripts/device_tree_sources.py \
  --kernel-bundle artifacts/kernel-inputs/nezha-xiaomi-eu-candidate-v2 \
  --expected-receipt-sha256 4ce149410ba2ab5f24653ebd8c4020a7401ba5172e2648c19f3c8bf726a7e9bb \
  --output artifacts/source-contracts/nezha-stock-dts-v1
```

The defaults are this recipe, `config/sources.json`, and
`/opt/homebrew/bin/dtc`; explicit overrides use `--recipe`, `--source-config`
and `--dtc`. The installed tool resolves to
`/opt/homebrew/Cellar/dtc/1.7.2/bin/dtc`, reports `Version: DTC 1.7.2`, and has
SHA256 `f826ffc72ecf7c44fed8e027e0851d4525df47bc1586f4ce395634aee3de9998`.
No installation or VM is needed for this local conversion. A different tool
requires a reviewed recipe update; a matching version string alone is not
enough.

The expected input receipt hash binds this command to the already captured
kernel bundle. Keep that input unchanged. A different firmware baseline needs
its own verified receipt and identity review, not a substituted path with the
old expected hash. The output remains private under ignored `artifacts/`.

The command above completed on **2026-08-27**: all nine complete graphs
matched after 19 successful DTC invocations. The receipt is
`artifacts/source-contracts/nezha-stock-dts-v1/receipt.json`, SHA256
`c6b20d9c8f4a38452f53cafd494bb223dc54373cdf4dacf33b8fdf5ccdc05410`.
It records 68 artifacts totaling 74,579,543 bytes, including 2,111,546 bytes
of retained compiler diagnostics. All nine rebuilt binaries differ from the
original bytes despite graph equality. The existing `v1` directory is evidence;
use a new output name for a repeat instead of replacing it.

Each `trees/dtb-0000/` through `trees/dtb-0007/` directory, plus
`trees/nezha-overlay-0000/`, contains `original.dtb`, expanded `source.dts`,
`rebuilt.dtb`, original/rebuilt graph JSON, and DTC diagnostics. The original
concatenated vendor DTB and complete DTBO image remain under
`originals/vendor.dtb` and `originals/dtbo.img`. The output receipt records
provenance and artifact/graph hashes; inspect its results and retained warnings
before using any derived source.

DTC decompiles with `-I dtb -O dts` and recompiles with `-I dts -O dtb`.
There is no forced output, warning suppression, or `-@` symbol generation.
The graph comparison covers every node and property byte, child order,
memory-reservation entries, boot CPU ID, phandles, and existing `__symbols__`,
`__fixups__`, and `__local_fixups__`. It must not discard fixup metadata merely
to obtain a match. Binary layout may differ even when these graphs agree;
byte equivalence is a separate result and requires matching actual bytes or
full hashes.

Each `rebuilt.dtb` is a bare FDT, not a flashable partition image. The
`dtbo-table.json` offsets and sizes describe the original image; a later DTBO
packing step must recalculate them for the rebuilt bytes while preserving the
reviewed entry IDs, revisions and custom fields. No physical partition size is
inferred from these files.

The overlay must retain the exact Nezha model on SM8850,
`qcom,board-id=<8 0>` and **`xiaomi,miboard-id=<5 0>`**. The reviewed sibling
overlays use Xiaomi IDs 1, 2 and 3, so shared Canoe compatibility and Qualcomm
board ID 8 are not enough. QTVM overlays are outside this nine-tree recipe.
See the [MiCode review](../../../../docs/micode-popsicle-review.md) and
[boot contract](../../../../docs/boot-contract.md).

Expanded DTS is a representation of compiled data. It does not recover the
original labels, macros, include structure, comments or license notices.
Existing symbol strings can survive in `__symbols__`, but that does not
reconstruct the original authored source. Keep generated files private and
record proven source provenance and notices separately when adapting them.

## Adapt these sources to a complete build

1. Preserve the unedited private source bundle and receipt as the comparison
   baseline. Start Nezha-specific changes in a separate workspace; keep the
   eight base entries in their original order and the Nezha overlay separate.
2. Resolve a complete pinned Kleaf workspace: GKI/common, build rules, this SoC
   layer, the DT tree, matching toolchain, and required external modules. Review
   the actual DT build interface before introducing a Nezha target. The two
   references below do not by themselves supply those dependencies.
3. Feed the Nezha-derived sources through that reviewed interface without
   changing their graph initially. Do not rename a Popsicle defconfig into a
   Nezha one, substitute its overlay, invent a BUILD label, or copy debug
   signing/KMI changes. Source labels and includes may be reconstructed only
   as explicit, reviewed changes checked against the baseline graph.
4. Record the resulting sources, build definitions, tool versions, graph
   comparisons and warnings in a new receipt. Kernel/module builds,
   overlay-application checks, bootloader DT selection and device tests remain
   separate validation steps; a successful local DTC round trip proves none
   of them.

Both references are pinned to `popsicle-w-oss` in `config/sources.json`:

| Reference | Commit | Read-only local checkout |
| --- | --- | --- |
| [MiCode kernel/vendor layer](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/tree/45705be1220b4cfa8100516ad86711656c0b634e) | `45705be1220b4cfa8100516ad86711656c0b634e` | `upstream/micode-popsicle-review` |
| [MiCode device-tree reference](https://github.com/MiCode/kernel_devicetree/tree/667482462e15458b602a2688a94efd47a5010141) | `667482462e15458b602a2688a94efd47a5010141` | `upstream/micode-popsicle-devicetree-review` |

Their local HEADs, `origin/popsicle-w-oss` refs and origin URLs matched these
pins on 2026-08-27, with clean worktrees. These observations do not claim that
the remote branches remain at those commits indefinitely. The current source
bundle still derives from the modified Xiaomi.eu package: graph preservation
does not authenticate its origin, repair its AVB failures, grant redistribution
permission, or establish kernel/module or hardware compatibility. The
coordinating workflow owns any later guarded source-volume staging; this
conversion performs none.

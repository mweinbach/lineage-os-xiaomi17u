The reviewed Nezha policy integration now has a reproducible source and private
input path. It remains a **`framework-checks` component workflow**. Staging,
candidate validation and a native policy build are separate checks; none admits
target-files, changes the retained vendor/ODM images, or establishes an
Evolution boot. See [current workspace status](workspace-status.md) for measured
build results and remaining gates.

The integration separates three maintained inputs:

| Layer | Reviewed input and responsibility |
| --- | --- |
| Evolution source | The [helper patch](../patches/evolution/0004-gate-init-dev-config-property-writes.patch) gates exactly two property SET permissions in `system/sepolicy/private/init_dev_config.te`. Retain the pinned `bka` / `bp4a` base and the other reviewed source patches. |
| Nezha configuration | The [capability contract](../config/nezha-init-helper-capability.json), device generator and [Make guard](../device/xiaomi/nezha/init-helper-capability.mk) admit `target_init_dev_config_property_writes=false` only with the reviewed factory and DSP profiles. |
| Private factory integration | The [derivation contract](../config/vendor-policy-correction.json), [bundle contract](../config/nezha-policy-inputs.json) and [native module template](../policy/nezha/Android.bp) reproduce the vendor correction and validate it with current framework outputs. |

The helper's undefined and `true` M4 branches retain upstream behavior. Its
`false` branch removes only SET access to `apexd_select_prop` and
`media_variant_prop`; property reads, socket permissions and existing
`init`/`vendor_init` authority remain. Admission rehashes the bound factory scan
and source evidence and rejects uncontracted helper selections, labels,
invocations and alternate init hooks in its checked inputs. Make rejects
duplicate or malformed definitions and command-line/environment overrides,
freezes recursive values, and prevents later Kati writers. This bounded check
does not prove that no runtime provider can exist. Unexpected providers must
retain visible permission failures.

The original ten-file v9 corpus is **classification provenance only**. The
vendor derivation re-evaluates its type and role closures, removes the 67
reviewed Binder allow occurrences, and preserves every other byte outside
those statement spans. Replaying the host derivation has reproduced the
1,708,593-byte vendor CIL with SHA256
`b0f3f4f0ca4d9526f3c0a05e7d650a1032ff32b3f81a2677aa6e929d9446d0c2`,
retaining all 6,366 assertions in that corpus. The
[Binder correction](binder-policy-correction.md) and
[helper projection](helper-policy-projection.md) retain the earlier experiments.
Their successful copied-CIL comparison is not the result of the new native
source build.

Run the following host commands from the workspace root. Replace `NEW` with an
unused name; keep the variables for both blocks. Existing output directories
are refused. The recorded corpus and capture must already exist: this does
not start another source sync or extract a replacement firmware package.

```sh
factory_analysis=artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b
policy_bundle=artifacts/policy-inputs/nezha-factory-NEW
policy_candidate=artifacts/device-candidates/nezha-policy-NEW
mkdir -p artifacts/policy-inputs &&
python3 scripts/policy_inputs.py stage \
  --corpus-root artifacts/build-validation/nezha-dsp-policy-v9-1/files/inputs/combined \
  --factory-policy-receipt "$factory_analysis/erofs-contract-v1/policy-receipt.json" \
  --output "$policy_bundle" &&
python3 scripts/policy_inputs.py verify --bundle "$policy_bundle"
```

`--factory-capture-root` can instead name the directory containing
`policy-receipt.json` and its original `policy/` capture layout. The selected
receipt must match `research/factory-framework-contract.json`. Staging copies
the original corpus, all 13 selected factory context files, reviewed tools and
contracts, provenance and `Android.bp`; it does **not** stage a hand-edited
derived CIL. Four ODM context files are authentically empty and remain so.
The fresh private directory is published only after input rechecks and complete
readback. A changed input, mixed package, symlink or existing destination fails.

Generate a new device candidate with the existing kernel/vendor receipts and
the explicit helper and policy-bundle arguments:

```sh
python3 scripts/generate_device_tree.py generate \
  --variant user \
  --kernel-receipt artifacts/kernel-inputs/nezha-xiaomi-eu-candidate-v2/receipt.json \
  --vendor-receipt artifacts/vendor-inputs/nezha-factory-d2cf57fd-camera-v1/vendor-inputs.json \
  --firmware-layout "$factory_analysis/normalized-layout-v1/firmware-layout.json" \
  --vintf-contract "$factory_analysis/build-property-comparison-v2/analysis/vintf-properties.json" \
  --factory-boot-contract research/factory-boot-contract.json \
  --partition-metadata research/partition-metadata.json \
  --dsp-policy-contract research/dsp-policy-integration.json \
  --init-helper-capability-contract config/nezha-init-helper-capability.json \
  --policy-inputs-receipt "$policy_bundle/policy-inputs.json" \
  --fstab-source "$factory_analysis/boot-analysis/ramdisk-comparison-v2/text-members/vendor_boot-0001.txt" \
  --output "$policy_candidate" &&
python3 scripts/generate_device_tree.py validate \
  --output "$policy_candidate" --purpose configuration
```

Only the verified opt-in exports `vendor/xiaomi/nezha-policy` through
`PRODUCT_SOONG_NAMESPACES`. Candidate validation checks its saved admission and
rendered configuration; it does not rehash an independently installed bundle
or apply the helper patch to the Linux source. Install through the existing
preservation workflow, retaining previous candidates and input bundles. Check
the exact source revision and preimage/postimage in the helper contract; do not
reapply an already installed patch or overwrite other reviewed source changes.

Before transferring or building, run `make apple-status`, inspect live
`active_volume_users`, and check existing processes, disk, architecture,
case-sensitive filesystem and the [source lock](source-lock.md). Use the sole
existing volume owner and the [verified container workflow](apple-container.md).
Transfer only the required controls and private bundle; no signing key or
home-directory mount is needed. Place the verified bundle at
`/work/evolution/vendor/xiaomi/nezha-policy` without overwriting an existing
version. Recheck destination bytes from the owning VM, using the trusted
transferred workspace controls as the current directory:

```sh
python3 scripts/policy_inputs.py verify \
  --bundle /work/evolution/vendor/xiaomi/nezha-policy
```

The verifier needs the matching trusted scripts, template, contracts and public
factory record named by `policy_inputs.CONTROL_FILES`. The bundle's own
manifest cannot authorize different hashes. Record the transferred control
revision and receipt identities; an updated template or tool requires a fresh
bundle and candidate binding.

The Android graph runs `vendor_policy.py derive` inside a native genrule,
producing both the derived vendor CIL and its receipt. It uses a fresh child
of the sandbox output directory because sbox precreates declared output
parents. `nezha_factory_precompiled_sepolicy` then consumes, in order:

1. Current platform, system_ext and product CIL and their three mapping outputs.
2. Original factory `plat_pub_versioned.cil`, the genrule-derived vendor CIL,
   and unchanged factory ODM CIL.
3. Current `plat_sepolicy_genfs_202504.cil`, through the pinned upstream
   `device_first_srcs` filegroup pattern.

The old framework files under `corpus/` are not binary compilation inputs.
Context aggregation uses `java_genrule` to consume Android common variants.
The binary is non-installable, keeps neverallow checking enabled, and supplies
no permissive-domain allowance. The following native targets include the
combined policy, all selected context checks and structural policy tests.
After the preflight and guarded installation, set `nezha_user_out` to the
already selected **user** OUT directory; do not reuse userdebug outputs.

```sh
test -n "${nezha_user_out:-}" &&
cd /work/evolution &&
PATH="$PWD/prebuilts/build-tools/path/linux-x86:$PATH" \
GOTOOLCHAIN=local GOENV=off GOPROXY=off GOSUMDB=off \
GOCACHE=/work/cache/nezha-framework-go \
TARGET_PRODUCT=lineage_nezha TARGET_RELEASE=bp4a TARGET_BUILD_VARIANT=user \
OUT_DIR="$nezha_user_out" build/soong/soong_ui.bash --make-mode -j8 \
  precompiled_sepolicy sepolicy_neverallows sepolicy-analyze \
  nezha_factory_precompiled_sepolicy \
  nezha_factory_file_contexts_test \
  nezha_factory_property_contexts_test \
  nezha_factory_hwservice_contexts_test \
  nezha_factory_service_contexts_test \
  nezha_factory_vndservice_contexts_test \
  nezha_factory_seapp_contexts_checked \
  nezha_factory_platform_seapp_contexts_checked \
  nezha_factory_sepolicy_test \
  nezha_factory_dev_type_test
```

Record the final `BoardSepolicyM4Defs`, enforcing configuration, generated
framework inputs, derivation receipt, compiler commands, output hashes and
complete diagnostics. Run an additional unfiltered `sepolicy-analyze POLICY
permissive` on each produced policy binary, including userdebug if tested;
do not infer zero permissive domains from a filtered target. A passed build
requires successful requested actions, not an abbreviated log or a skip.
Run `python3 -m unittest discover -s tests -v` separately for workspace tooling.

File, hardware-service and service checks combine current framework contexts
with the exact vendor/ODM captures. Property checks likewise use all five
partitions. Framework seapp checks omit the vendor-only `-c` restriction;
factory seapp checks retain it. Structural `sepolicy_tests` and the explicit
`TestDevTypeViolations` check do not establish complete Treble labeling. That
requires real complete APK inventories; the API-202504 compatibility no-op or
fabricated empty inventories cannot stand in for it. Captured vendor
keystore2-key and TEE-service contexts remain outside these native checks.

The retained opaque images still contain their original policy. This workflow
does not adopt the derived policy into images, validate VINTF or OTA packaging,
sign a complete AVB chain, or verify camera, media, accessories or other
hardware. Normal Android stays enforcing. The separately tested TWRP recovery
exception is unchanged, and no phone mutation is authorized by this workflow.

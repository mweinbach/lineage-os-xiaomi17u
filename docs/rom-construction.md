# Explicit ROM construction prerequisites

The maintained construction consumer separates **input admission** from
**artifact validation** and **device testing**. Its first descriptor,
[`nezha-rom-construction.json`](../config/nezha-rom-construction.json), is
deliberately unbound. It does not enable a complete product or admit any
currently blocked framework-checks target. No readiness flags change.

Inspect the exact outstanding roles without opening private evidence:

```sh
python3 -B scripts/rom_construction.py plan --phase target-files
python3 -B scripts/rom_construction.py check --phase target-files
```

`plan` exits zero when inspection succeeds and reports `status: blocked`.
`check` exits **2**, because construction is not admitted. Neither command
dispatches a process or build. To rehash the three existing component/provider
records, add `--verify-available-evidence .`. That confirms their identities
only; it does not rerun the tests or qualify a later selected source/input set.
Missing or mismatched evidence fails rather than becoming a skipped check.

The generator recognizes an explicit `--rom-construction-contract` argument.
Selecting this descriptor fails before reading proprietary input bundles or
publishing a candidate, with the missing native roles in the error. Omitting
the argument preserves the prior generator behavior and candidate bytes.
Existing `target-files`, `super`, OTA, default-build and alias restrictions
remain unchanged. Do not invoke raw output paths or nodeps aliases to bypass
them. This is the implemented fail-closed schema/consumer slice; a
construction-enabled BoardConfig derivative is not implemented or installed.

The exact missing selected-input roles are:

- `source_and_private_input_closure`: actual adopted source composition,
  current generated inputs, selected image/metadata bytes and their guards.
- `policy_and_context_checks`: strict policy/context evidence or an explicit
  complete relevant-input equality binding for the selected construction set.
- `provider_elf_and_install_closure`: selected native dependencies, actual
  strict ELF checks and installation closure. The completed 26-check result is
  retained as a basis; it is not silently relabelled for a future product.
- `full_vintf_native_result`: the actual complete native command/input result.
- `necessary_vintf_coverage`: separate review of the required checks and actual
  coverage, not the full runner's outer success field.

The VINTF distinction is required by the pinned runner. Its successful
commands can retain an unlevelled matrix-definition skip; `--check-one` uses
StubRuntimeInfo, mainline classification can bypass kernel requirements,
StaticRuntimeInfo substitutes SIZE_MAX for policy-version support, and default
flags disable AVB-version checking. Absence of warnings does not establish
coverage. The consumer preserves these limitations and does not change the
runner's deliberately false `complete_input_compatibility_verified` field.
Binding a receipt requires a new reviewed contract and consumer revision;
caller-supplied pass fields or self-resealed JSON cannot activate version 1.

Phases name only ordinary `target-files-package`, `superimage` and
`otapackage` rules. Super additionally needs validated target-files/images;
OTA additionally needs the signed image set, separate APK/APEX/payload/ZIP
trust inputs, and qualified care-map/snapshot inputs. These are requirements,
not enabled commands. Metadata installation against actual images/policy,
full installed APK labeling, final compatibility, real super output/LP checks
and OTA checks belong to their construction or artifact-validation phases.
Signed final images, live physical fit and successful hardware operation are
not prerequisites to the first image compilation. They remain required before
their respective final artifact and authorized device admissions.

Reproducibility remains separate: the descriptor references the existing 0012
version-date contract but does not select it, invent an epoch/build number, or
modify the current 0005–0011 packaging composition. A later source successor
must bind actual manifest epoch/build metadata evidence and validate the
maintained interface through the ordinary product route. The 33 earlier
isolated Kati cases are not evidence of active adoption or reproducible images.

The implementation reuses the metadata tool's bounded, no-follow reader and
strict JSON parser. Offline tests cover resealed controls, input/scope changes,
coverage waivers, unsafe phase aliases, explicit selection, refusal before
private-input reads and accurate blocked exit codes. They do not provide a
native product, target-files, signed ROM or device result.

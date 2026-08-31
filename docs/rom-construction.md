# Explicit ROM construction prerequisites

Construction separates **source derivation**, **native input admission**,
**artifact validation** and **device testing**. The explicit maintained source
selector now reproduces the installed first target-files BoardConfig and guard.
It does not dispatch a build or admit a flashable ROM. The first inspection descriptor,
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
That version-1 interface retains its `target-files`, `super`, OTA, default-build
and alias restrictions. It is not the new source selector. Do not invoke raw
output paths or nodeps aliases to bypass either interface.

The separate source selector is
`--rom-construction-source-contract config/nezha-rom-construction-source-v1.json`,
implemented by [`rom_construction_source.py`](../scripts/rom_construction_source.py).
Use it with the complete existing user/4 KiB/matrix/policy-image-delivery recipe.
The generator first performs all ordinary base-input checks and requires the
exact complete base admission `13b69244…` (162,579 bytes). It then replaces only
the reviewed BoardConfig target block with an include and adds the exact
generated `rom-construction.mk`. Validation reconstructs the complete base
admission, so changing other source bytes, input identities, scope fields or
readiness flags—even with new file hashes—fails. Omitting the selector retains
the prior candidate bytes and restrictions. Existing input bundles and frozen
candidate/control copies are not rewritten.

The source derivative permits only the sole ordinary `target-files-package`
goal under the pinned product, user variant, 4 KiB checks, AVB, GMS selection
and 0012 metadata interface. Existing component targets remain available for
preflight; default ROM, super, OTA and packaging aliases remain blocked. The
native runner must separately verify current source and inputs, bind the actual
fixed metadata environment and `bp4a` invocation, run `nothing`, then build and
verify `recoveryimage`, `mi_extimage`, `vendorimage`, `odmimage` and the three
ordinary framework policy-digest modules before target-files. Source selection
does not assert that those component artifacts or a native Make parse already
passed. Final signing, partition fit, super/OTA and authorized device admission
remain later gates; they are not circular prerequisites to compilation.

The August 31 source installation has two immutable records. The original
three-operation constructor receipt `f70dab48…` installed 0012 and the source
derivative. Source inspection then found that `release_config.mk` clears or
poisons `TARGET_RELEASE` before `envsetup.mk` includes BoardConfig. The separate
one-file correction receipt `2bbfdefc…` preserves that history and changes only
the generated guard. Its current-source proof retains 478 files and twelve
project observations. The corrected guard is
`fe1e32cffe0d7b7ba20a9fd1d90f1cf8712f9fa6b7aa0e3ec1a90a6b7058c469`
(2,553 bytes); it checks the resulting `BP4A`, `REL`, `16` and `36` release flags
without reading the unavailable raw selector. The maintained generator produces
those exact installed bytes. The source-order regression was verified with
host GNU Make; it is not evidence of a native Kati or target-files build.

The unchanged inspection descriptor records these unbound roles. Later actual
source/component records do not automatically rewrite or activate that historical
version; current native dispatch must bind the applicable records separately:

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

Reproducibility remains separate. The original inspection descriptor does not
select 0012 or invent an epoch/build number. The recorded constructor source
successor installs the exact two 0012 leaves separately from the eight-operation
0005–0011 packaging transaction. Actual fixed input descriptors and the ordinary
product metadata route still require their own verification. BUILD_NUMBER stays
invocation-only; it is not included in its own source-descriptor preimage. Neither
the earlier 33 isolated Kati cases nor source installation proves reproducible
images.

The implementation reuses the metadata tool's bounded, no-follow reader and
strict JSON parser. Offline tests cover resealed controls, input/scope changes,
coverage waivers, unsafe phase aliases, explicit selection, refusal before
private-input reads and accurate blocked exit codes. They do not provide a
native product, target-files, signed ROM or device result.

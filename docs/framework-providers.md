# Nezha framework-side Qualcomm providers

The factory device compatibility matrix names two framework-side AIDL HALs:
`vendor.qti.hardware.sigma_miracast_aidl` and `vendor.qti.qccsyshal_aidl`.
The stock `system_ext` image supplies their actual binaries, init rules and
framework VINTF fragments. The earlier Evolution component graph did not select
either provider. These are declared stock integration expectations, **not an
observed `checkvintf` failure**: the pinned `libvintf` framework/device-matrix
comparison does not enforce the presence of these HAL entries.

The [reviewed input contract](../config/nezha-framework-providers.json) and
[staging tool](../scripts/framework_provider_inputs.py) select both providers
explicitly. Staging does not enable them in every device product, admit their
SELinux policy, prove binary compatibility, or make the ROM ready. A generated
device admission must bind this separate private bundle before inheriting it.

## Exact input boundary

All selected firmware files come from the already reviewed factory-named
`OS3.0.309.0.WPACNXM` package, SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
The original `system_ext_a.img` is 713,158,656 bytes, SHA256
`53dd447bf8453f07b9df24e91a9429c2a15b5589b31406747cc62f0fc79cab5e`.
Image hashes establish byte provenance, not publisher authenticity.

The private bundle contains 31 selected firmware files: two AArch64 PIE
executables, 24 AArch64 shared libraries, two original init rules, two original
framework VINTF fragments and `wfdconfigsink.xml`. Each has an exact size, SHA256,
capture-receipt binding and original runtime path. The selected binaries are:

| Provider | Original executable | Private library closure |
| --- | --- | --- |
| Sigma AIDL | `/system_ext/bin/sigma_miracasthalservice_aidl` | 21 selected libraries; 43 additional source SONAMEs |
| QCC AIDL | `/system_ext/bin/qccsyshal_aidl-service` | 3 selected libraries; 14 additional source SONAMEs |

There are 47 distinct source SONAMEs across the two closures. Three captured
factory display libraries are evidence only. Their existing, pinned source
modules supply `vendor.display.config@2.0`, `libdisplayconfig.system.qti` and
`vendor.qti.hardware.display.config-V5-ndk`. The bundle does not replace platform
libraries with stock copies. The complete Evolution source lock remains in
force; module-name availability alone is not symbol or ABI compatibility.

The guarded EROFS captures under ignored
`artifacts/framework-providers-20260829/` read explicitly inventoried regular
files without mounting images, following symlinks or executing firmware.
Captured inputs are preserved; staging creates a new directory and refuses to
replace any existing destination. Recaptures with different receipt identities
require a reviewed contract update rather than silently changing provenance.

## Native build integration

Staging generates private `vendor/xiaomi/nezha-framework-providers` content and
a separate `framework-providers.Android.bp`. Explicit device admission copies
only that verified generated Blueprint to
`device/xiaomi/nezha/framework-providers/Android.bp`. The proprietary bytes stay
in the vendor bundle. Filegroups expose only the verification producer's
generated payloads to that exact device package; they do not expose raw inputs.
The generated device namespace imports the private input namespace. Original
installation names remain unchanged through `stem`/`filename` and
`system_ext_specific` properties. The native definitions use:

- `cc_prebuilt_binary` and `cc_prebuilt_library_shared`, with arm64 inputs,
  explicit `DT_NEEDED` dependencies, `check_elf_files: true`,
  `allow_undefined_symbols: false`, and no stripping of the captured files.
- `init_rc` and `vintf_fragments` attached to each actual binary. No bare HAL
  declaration or generic ELF/VINTF `PRODUCT_COPY_FILES` entry is introduced.
- `prebuilt_etc` for the original `wfdconfigsink.xml`.
- `nezha_framework_provider_inputs_check`, required by every installed module.
  This native genrule verifies exact hashes and sizes for all 42 selected
  firmware/control inputs using a generated standalone Python tool, then emits
  31 payloads under `verified/system_ext/` plus its checked receipt. Every ELF,
  init, VINTF and configuration consumer reads a specifically tagged payload
  output. The direct data dependency remains even for image targets that do not
  traverse a non-installable `required` check module.

The original `libmiracastsystem.so` has one reviewed dependency correction in
that producer. All 31 staged proprietary files, including this library, remain
identical to the factory captures. The producer checks all 42 original inputs
before deriving any output. It then changes exactly the byte at file offset
17,588 from ASCII `2` to `4` in the selected `DT_NEEDED` string
`android.media.audio.common.types-V2-cpp.so`. The published library names V4;
its generated module therefore depends on the actual V4 source module. The
original and derived sizes both remain 119,560 bytes:

| File role | SHA256 |
| --- | --- |
| Preserved proprietary input | `45880ab976336616c2ff91753d176d3d10e175564005d51266359316ad965541` |
| Verified generated payload | `06ffed0abd8cd7258c44e672e7fde4377f39626dddbed59eef70f60426c08082` |

The [compatibility record](../research/framework-provider-audio-compatibility.json)
binds the evidence supporting this specific correction. The
[pure derivation helper](../scripts/framework_provider_derivations.py) checks
the original ELF's selected dynamic string, parsed metadata and protected
regions during staging and verification. The generated standalone build tool
repeats the exact original hash, string, offset, byte and complete output hash
guards. Its checked receipt binds original and effective output identities
separately. A premodified proprietary input, changed recipe, or incorrect
derived hash fails before publication. The ELF build-id is unchanged because
all other bytes are unchanged; use the derived SHA256 as its identity.

This is not a general AIDL version upgrade. The earlier native v13f bootstrap
failed because the factory library's direct V2 dependency and the current audio
foundation's V4 dependency reached the same module. Three isolated tests using
the pinned real Soong/AIDL implementation established that moving dependencies
under `shared` only moves the conflict to the shared variant. Suppressing that
check or changing only the Blueprint's dependency would leave the original ELF
inconsistent. The producer instead supplies the reviewed derivative to the
normal native ELF and AIDL checks.

The producer holds the verified bytes, prepares and reads back all outputs,
then publishes complete files exclusively and writes the success receipt last.
It accepts only the expected empty output directories precreated by Soong's
`sbox`; it refuses existing files, symlinks and unrelated entries. It removes
its published files on caught errors. This matters because the pinned `sbox`
can copy declared output files even after a command fails. An interrupted or
failed native action is never counted as successful, regardless of leftover
files. Original inputs are never hard-linked to output files or modified.

The dependency chain is `raw inputs → verified-output genrule → tagged
filegroups → native consumers`. The literal generated device Blueprint is a
verification input, not a dependency on the consumer modules; the chain has no
cycle. An actual generated Ninja graph still must confirm these producer and
consumer edges after source admission. The contract's `native_output_recipe`
rejects the earlier raw-input design.
The producer is visible only inside its own package, to the exact device
consumer package, and to the policy-input package that depends on its checked
receipt. The Python verifier is private to its package.

The [mDNS visibility patch](../patches/evolution/framework-provider-mdnssd-visibility.patch)
adds only `//device/xiaomi/nezha/framework-providers:__pkg__` to `libmdnssd`'s
existing visibility list. It changes no library code or build checks. Its
[descriptor](../patches/evolution/framework-provider-mdnssd-visibility.json)
pins `external/mdnsresponder` revision
`3e0189c4d3be5272398b1ea6ad2f223a973d0ea2` and exact preimage/postimage hashes.
The staging tool verifies the patch inputs but does not apply that patch or
claim that the guest has it installed.

This split respects the pinned Soong visibility rule: a package outside vendor
cannot expose itself to one specific vendor package. Making `libmdnssd` visible
to all vendor packages would exceed this integration's scope. The first private
candidates with the rejected vendor-package design remain historical local
artifacts; they must not be installed. The generator verifies the current
device Blueprint bytes and exports both admitted namespaces.

Prepare and verify a fresh private candidate from the preserved captures:

```sh
python3 scripts/framework_provider_inputs.py stage \
  --capture-root artifacts/framework-providers-20260829 \
  --output artifacts/framework-providers-20260829/bundle-reviewed

python3 scripts/framework_provider_inputs.py verify \
  --bundle artifacts/framework-providers-20260829/bundle-reviewed
```

Before guest installation, inspect live volume ownership and existing jobs.
Transfer only the generated private bundle and reviewed control files; verify
the destination again against the same contract. Never install it over another
agent's work or start another volume writer. Root orchestration must admit the
provider-specific enforcing policy and the required source patch separately,
then run the actual native targets. Do not relax a failing symbol, visibility,
context, property or permission check to admit these providers.

## Evidence and remaining runtime limits

The initial independent static audit checked 29 factory ELF objects, including
the three display-library references that will be rebuilt from source. A
bounded ELF reader and native LLVM 21 `llvm-objdump` agreed on `DT_NEEDED`,
dynamic symbols, strong/weak bindings and imported symbol versions. Every
import with a captured private exporter could reach one through its declared
dependency closure. The actual rebuilt source-provider exports were not part
of that comparison; native `check_elf_file` results must be recorded separately.

The ignored audit index is
`reports/framework-providers-20260829/elf-audit/findings-v1.json`, SHA256
`26bba1ab2bfd9be2c6940eba0743ff859ae2d944e1d07cff5e53c2a61aa80ad0`.
Its exact disassembly and symbol tables remain private. The source-module
inventory and selected source definitions are also under the ignored
`reports/framework-providers-20260829/` directory.

The later audio correction has a narrower, stronger evidence set than the
initial module inventory. Factory caller instructions match the factory V4
audio layouts, while the factory audio companion libraries already name V4.
Two actual compile-only probes using the pinned current compiler, generated
V4 headers and original target/LTO/CFI flags matched all 15 measured factory
size, offset and stride constraints. Static analysis of the actual current
audio foundation's CFI dispatch accepts the caller's two relevant type checks.
All 20 selected strong, unversioned audio imports have unique matching exports
in the four actual current audio DSOs. The one changed string byte has no
other reference among the original library's dynamic string references.

These results support the exact dependency correction. They do not establish
every private C++ ABI or semantic contract, dynamic linker resolution, service
startup, wireless-display behavior, or a booting ROM. No target code or firmware
was executed for the layout and static checks. The first layout run failed in
the audit harness after a successful discovery compile; that result is
preserved separately and is not counted as the successful fresh measurement.
The compatibility record remains a fixed admission checkpoint; subsequent
native build and device results must be recorded separately.

Sigma imports private graphics/audio C++ APIs, including SurfaceComposer and
AudioSystem methods, plus mDNS functions. QCC imports Binder/FMQ APIs. Matching
SONAMEs or even symbols does not prove object-layout, semantic or cross-DSO CFI
compatibility. Both AIDL implementations report version 1; the static hash
getter/initializer linkage identifies Sigma
`48d143f4e6c2872933966b8769d8111ab4c8e107` and QCC
`5b5de541decedff24c382e8a5ee5adcf0df62680`.

The factory Sigma service remains disabled and oneshot, requiring a client
start path. QCC's original RC includes a stop rule for
`hwservicemanager.ready=true` and creates its own data/socket paths. Neither
service is proven running merely by packaging its declaration. Its original
`interface aidl vendor.qti.qccsyshal_aidl` line also differs from the fully
qualified `IQccsyshal/default` instance expected for a lazy restart request;
the pinned init parser accepts that shorter spelling literally. This is a
runtime question, not a demonstrated syntax failure, and this input bundle does
not rewrite the original rule. Their actual service types, executable labels,
domains and data/socket policy need explicit source integration before image
adoption through the [provider policy contract](../config/nezha-framework-provider-policy.json).

Wireless-display source functionality also refers to a separate `wfdservice`
Binder server. QCC companion applications and their signing, permissions and
application domains are outside this native provider slice. The RTP debug code
contains an alternate vendor-library name, but the captured `libmmosal`
`GetContext()` returns zero, selecting the captured system-side
`libwfdcommonutils.so` under normal, non-interposed resolution. Its error paths
also have fallbacks. This does not justify broad vendor linker-namespace access.

The original vendor WFD configuration remains in the preserved vendor image.
The bundle adds only the matching stock `system_ext` sink configuration. Native
symbol validation, complete linker configuration, service registration,
VINTF/image packaging and physical feature behavior remain separate gates.
No phone action follows from this workflow.

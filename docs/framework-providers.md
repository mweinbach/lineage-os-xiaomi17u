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
in the vendor bundle; filegroups expose them only to that exact device package.
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
  This native genrule verifies exact hashes and sizes for all selected firmware,
  the contract and capture receipts using a generated standalone Python tool.

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

# Factory framework inputs and strict policy checks

The supplied China fastboot images now have **60 captured SELinux files and
469 captured framework XML files**, with hashes bound to the inspected logical
images. Two strict policy compilations completed on **2026-08-27**. The ten
factory inputs failed one neverallow assertion. Seven newly built Evolution
framework inputs combined with the three exact factory vendor/ODM inputs failed
21 assertion sites. Neither check produced a policy binary or contexts output.
These are concrete integration failures, not device tests or passing SELinux
compatibility results.

The [public contract](../research/factory-framework-contract.json) records
aggregate counts, changed paths and hashes, ordered compiler inputs, source
pins, receipts, diagnostic locations and limits. Full inventories and identical
file listings remain in the bound private receipts, alongside raw policy,
contexts, XML, precompiled binaries and logs. No phone operation, firmware
executable, image mount, source edit or Android OUT edit was part of these checks.

Here, “factory” identifies the separately supplied China fastboot TGZ, SHA256
`d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b`.
Its provenance remains **user-provided, unknown URL, unverified origin**.
Passing internal AVB checks and all eight filesystem checks provide usable
inspection inputs; they do not establish an independently authenticated Xiaomi
trust root or download origin. The [image validation](factory-firmware-validation.md)
and [intake](factory-firmware-intake.md) preserve those distinctions.

The comparison baseline is the supplied modified Xiaomi.eu ZIP, SHA256
`b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69`.
Its earlier [SELinux failures](selinux-contract.md) and
[VINTF inventory](vintf-contract.md) remain separate evidence. No receipt or
failed result from that package was replaced with a factory result.

| Logical image | Selected policy files | Policy bytes | Selected XML files | XML bytes |
| --- | ---: | ---: | ---: | ---: |
| vendor | 14 | 2,366,441 | 214 | 116,623 |
| ODM | 11 | 1,586,898 | 53 | 25,055 |
| system | 13 | 2,812,610 | 61 | 856,438 |
| system-ext | 11 | 713,686 | 98 | 99,936 |
| product | 11 | 81,907 | 37 | 99,763 |
| mi-ext | Not selected | — | 6 | 1,824 |
| system-DLKM | Not selected | — | 0 | 0 |
| vendor-DLKM | Not selected | — | 0 | 0 |
| Total | 60 | 7,561,542 | 469 | 1,199,639 |

The guarded EROFS tool verified each source image hash, held its identity stable
and rehashed every captured file. Its eight complete inventories contain
18,512 entries. No symlink was followed. Policy selection matches the earlier
60-path baseline, including every regular vendor/ODM SELinux file. The record
separately lists 15 system, 16 system-ext and seven product SELinux paths that
were not selected, including older mappings and the separate userdebug platform
CIL. Thus “60 files” is a precise selection, not a claim to include every policy
file present anywhere in the package.

Of those 60 files, **45 match Xiaomi.eu and 15 differ**. Both vendor policy and
genfs version files declare `202504`, followed by a newline. The factory ODM
precompiled policy is 1,571,392 bytes, SHA256
`5ce021d525fa536e0c5e9b2b2b5b8b105d1a94993514ca4d406b298dd137f9b1`.
Its inspected header declares binary policy format 30. That stored binary was
not loaded, installed or used as a compiler fallback.

All three factory framework metadata digests match fresh SHA256 calculations
over each partition's exact CIL followed by its `202504` mapping. However, none
of the three stored framework/ODM precompiled metadata pairs agrees. The JSON
retains every digest. This applies the pinned Evolution hash recipe; Xiaomi's
original recipe has not been authenticated. Genfs CIL is not part of this hash
recipe. The mismatch does not establish its cause or which policy the connected
phone loaded. No metadata was repaired.
[Pinned hash rules](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/Android.bp)

XML selection covers regular XML beneath `etc/vintf`, `etc/permissions`,
`etc/sysconfig` and `etc/default-permissions`, plus the legacy manifest/matrix
paths, across all eight images. Nested product and mi-ext paths are retained as
package evidence; their presence does not prove an overlay or permission is
active. APEX payloads were not opened in this capture.

The first XML comparison used the previously captured Xiaomi.eu set. Its
absence labels could not establish that a path was missing from an image.
A separate corrected comparison bound both complete inventories and captured
38 additional Xiaomi.eu XML files, preserving the original receipt and files.
The corrected universe contains **469 factory and 470 Xiaomi.eu XML paths**:

| Category | Identical | Changed | Factory-only path | Xiaomi.eu-only path |
| --- | ---: | ---: | ---: | ---: |
| VINTF | 209 | 0 | 0 | 0 |
| Permissions | 208 | 1 | 16 | 14 |
| Sysconfig | 27 | 4 | 2 | 4 |
| Default permissions | 2 | 0 | 0 | 1 |
| Total | 446 | 5 | 18 | 19 |

All 209 selected VINTF XML files are byte-identical between these packages.
The five changed XML paths are `split-permissions-google.xml`, `google.xml`,
`hiddenapi-package-whitelist.xml`, `miui_whitelist.xml` and `power-save-conf.xml`;
their complete paths and both hashes are in the contract. This comparison does
not validate XML syntax or schemas, merge effective VINTF inputs, check active
APEX manifests, grant permissions, or prove framework/HAL compatibility.

Both policy checks executed the actual Soong-built x86-64 `secilc` in the
existing ARM64/Rosetta guest. The matching `sepolicy-analyze` executable was
verified but not run because compilation produced no binary. Tool hashes and
clean pinned source states were checked before and after. The sandbox exposed
Android source, Android OUT and staged inputs read-only; only each fresh
validation directory and `/tmp` were writable. No new build or VM was launched
by either compiler check.

The compiler arguments retained **`-m -M true -G -c 30`**, with ten explicit
ordered inputs and new output paths. Neither `-N` nor `--disable-neverallow` was
used. No assertion, grant, mapping or vendor/ODM input was removed. The order is
platform CIL/mapping, system-ext CIL/mapping, product CIL/mapping, vendor public
versioned CIL, vendor CIL, ODM CIL, then platform genfs `202504` CIL.

| Strict experiment | Exact inputs | Result |
| --- | --- | --- |
| Factory | Ten captured files, 5,408,720 bytes | Exit 255; one assertion site and two displayed allow locations |
| Evolution + factory, userdebug | Seven generated framework files plus three captured vendor/ODM files, 5,498,245 bytes | Exit 255; 21 assertion sites and 27 displayed allow locations |

The factory failure is at vendor CIL line 9901: its service-finding restriction
conflicts with grants for `cameramind_app` and `miuibooster` at system-ext CIL
lines 4604 and 4702. This is a strict assertion result for the supplied files,
not evidence that the running phone is permissive or that either service fails.

The Evolution inputs came from the successful 2,656-action boot/DLKM/framework
policy build using `lineage_nezha`, release `bp4a`, variant `userdebug`. The
build receipt SHA256 is
`f920c2adba3dace5aa4b7dc067b195d5bfdd40539dee1acf07b46fa2063fbc99`.
The record binds all seven observed output hashes to that receipt. The four
system-ext/product CIL and mapping outputs each contain exactly one newline;
all four were supplied unchanged. Their presence in a successful framework
target does not establish that the required device policy has been integrated.

The combined check reached neverallow assertions without a missing-type
diagnostic. Its **27 displayed allow locations are not a count of all matching
rules**: two Binder diagnostics show only four of 35 and four of 32 matches.
The full bounded log is preserved. Neither check generated a binary, so neither
has a permissive-domain analysis result. Guard checks passed and all input,
source-output and tool hashes remained unchanged.

Read-only inspection of the exact `system/sepolicy` commit
`e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27` identifies which reported grants are
controlled by the build variant. Seven public source files, totaling 172,389
bytes, were copied from pinned Git objects and verified against their Git blob
IDs and SHA256 hashes. The upstream `userdebug_or_eng` macro emits its body for
those two variants and suppresses it for `user`. This source behavior is not a
successful user-policy compilation, and it does not authorize an `eng` build.
[Macro definition](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/public/te_macros#L607)

| Reported restriction group | Assertion sites | Source finding |
| --- | ---: | --- |
| llkd process tracing | 15 | The grant is inside `userdebug_or_eng` at `llkd.te:22–33` |
| Codec2 TCP access to su | 1 | `hal_codec2.te:10` expands service-registration macros whose TCP grant is inside `userdebug_or_eng` |
| init_dev_config property writes | 2 | The grants at `init_dev_config.te:9–10` and `set_prop` macro are not variant-guarded |
| Isolated compute service lookup | 1 | The grant at `isolated_compute_app.te:17` is not variant-guarded |
| Binder permissions involving non-domain types | 2 | The assertions at `domain.te:2223–2224` are not variant-guarded |

Thus **16 reported assertion sites involve debug-only grants; five sites in
three restriction groups do not have that guard**. In particular,
`init_dev_config.te` wraps only its type declarations in
`until_board_api(202604)`, not the property grants below them. Changing the
build variant alone cannot be credited with resolving those remaining groups.
[llkd source](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/private/llkd.te),
[Codec2 source](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/private/hal_codec2.te),
[Property grants](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/private/init_dev_config.te),
[Isolated compute grant](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/private/isolated_compute_app.te),
[Binder assertions](https://github.com/Evolution-X/system_sepolicy/blob/e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27/private/domain.te#L2223)

A `user` experiment would require its own generated seven-file framework set
and the same three exact factory inputs, with all assertions retained. This
record contains no such result. The existing userdebug receipts must remain
available. The property, service and Binder findings identify source integration
work; deleting captured policy or disabling checks would not validate it.

The private factory artifact base is
`artifacts/firmware-analysis/d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b/`.
The contract records full paths, sizes and SHA256 values for these receipts:

| Receipt | SHA256 |
| --- | --- |
| `erofs-contract-v1/policy-receipt.json` | `e9b44133f73254493736496d1fb50b7402b96f3c3b395bbd042b0b35b35fedb3` |
| `erofs-contract-v1/xml-comparison-v2.json` | `6df160536e3c7df61445770a579854c2b8431ffa6fd501609394863b0c32b9fa` |
| `selinux-soong-check-v1/receipt.json` | `47f78e6dca9b424133339e4a5f62b67b2d40d843be41f6c36c5ce2ca148504ca` |
| `selinux-evolution-check-v1/receipt.json` | `f03d74c6380c9dcba51b29247c06673f693a81d826bed95d3957decd7fbcef29` |

After a strict combined policy compiles, its permissive domains and the exact
captured file, property, service and app contexts still need explicit checks.
Complete VINTF validation must include the framework/device matrices, kernel
requirements and active APEX inputs. A full image build and later separately
authorized device tests remain necessary to verify policy loading, enforcement,
boot and native service behavior.

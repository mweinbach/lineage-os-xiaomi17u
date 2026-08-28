# Initial TWRP graph dependency audit

The first strict Nezha graph attempt completed 132 Soong bootstrap steps, then
stopped on seven missing defaults used by 21 modules. All seven defaults are
defined in five AOSP projects explicitly removed by the TWRP minimal manifest.
This is a source selection problem before an Android recovery image has been
built. The [machine-readable audit](../research/twrp-graph-dependencies.json)
binds the failure log, exact provider revisions, source-file hashes and
individual consumers. The separate missing `splash.xml` message is not part
of this provider analysis.

The existing Evolution checkout was used to locate definitions and estimate
project scale. Every definition below was then fetched independently from its
verified AOSP `android-16.0.0_r1` commit. No Evolution `bka` source was copied
into TWRP, and this review did not sync, modify or build either source tree.

| Missing defaults | Correct r1 provider | Pinned commit |
| --- | --- | --- |
| `bpf_cc_defaults` | [system/bpf](https://android.googlesource.com/platform/system/bpf/+/4447acd742bf443f9088c300bd69f96ede8eaeb1/Android.bp) | `4447acd742bf443f9088c300bd69f96ede8eaeb1` |
| `tradefed_defaults`, `tradefed_errorprone_defaults`, `rdroidtest.defaults` | [platform_testing](https://android.googlesource.com/platform/platform_testing/+/7b48625b052b94b1ef24573ef5e8ffa5e2ea9783/) | `7b48625b052b94b1ef24573ef5e8ffa5e2ea9783` |
| `gfxstream_defaults` | [hardware/google/gfxstream](https://android.googlesource.com/platform/hardware/google/gfxstream/+/fc0dca02291e1d5ba1d2dad1d0b58b4f2ef255d0/Android.bp) | `fc0dca02291e1d5ba1d2dad1d0b58b4f2ef255d0` |
| `avf_build_flags_rust` | [packages/modules/Virtualization](https://android.googlesource.com/platform/packages/modules/Virtualization/+/c984fc337c11ca5edc03ccf02037b2455dd8fcaf/build/Android.bp) | `c984fc337c11ca5edc03ccf02037b2455dd8fcaf` |
| `neuralnetworks_utils_defaults` | [packages/modules/NeuralNetworks](https://android.googlesource.com/platform/packages/modules/NeuralNetworks/+/6cd97dca5e3ce0bd539d84d78f777a3576e673e3/common/types/Android.bp) | `6cd97dca5e3ce0bd539d84d78f777a3576e673e3` |

These pins are fallbacks, not instructions to restore every project. The
initial target excludes networking and data decryption. Its failing consumers
include emulator, advertising and test infrastructure, but also the non-test
`netbpfload`, secretkeeper and NN utility modules. Supported source selection
can exclude unrelated source roots; it must still report any missing dependency
used by a retained module. The build audit separately verifies
`PRODUCT_SOURCE_ROOT_DIRS` behavior. A successful retry, not this static
classification, establishes whether the retained graph is complete.

If a retained module needs one of these providers, restore its real r1 sources
and semantics. There are useful differences between the fallback scopes:

- `system/bpf/Android.bp` defines compiler warnings and clang-tidy policy,
  including errors. The default itself has no module dependencies. The small
  project is the simplest complete fallback if BPF is actually needed.
- [The Tradefed defaults file](https://android.googlesource.com/platform/platform_testing/+/7b48625b052b94b1ef24573ef5e8ffa5e2ea9783/libraries/tradefed-error-prone/Android.bp)
  contains two Java quality configurations. `tradefed_defaults` inherits the
  Error Prone configuration and adds compiler flags. The retained
  `tools/tradefederation/core` project does not supply those definitions.
- `avf_build_flags_rust` maps eleven AVF release flags to Rust configuration
  values; it has no Rust library dependencies. Its containing file also defines
  aconfig/Java modules and a `dtc` rule, so a repair must retain the adjacent
  inputs and applicable metadata rather than copying an isolated declaration.
- NN utilities inherit [project-root compiler defaults and license metadata](https://android.googlesource.com/platform/packages/modules/NeuralNetworks/+/6cd97dca5e3ce0bd539d84d78f777a3576e673e3/Android.bp).
  The `common/types` file also defines libraries that require other defaults.
  Selecting only that directory is not a demonstrated graph closure.
- Gfxstream defaults carry real graphics/header dependencies, including
  gfxstream, X11, AEMU, Magma and Vulkan headers, plus `libnativewindow` for the
  Android variant. Restoring the root declaration alone is insufficient.
- [The rdroidtest default](https://android.googlesource.com/platform/platform_testing/+/7b48625b052b94b1ef24573ef5e8ffa5e2ea9783/libraries/rdroidtest/Android.bp)
  selects a custom Rust test harness with library and proc-macro dependencies.
  Its associated sources require `liblibtest_mimic`, `liblinkme`, logging,
  `libpaste`, `libproc_macro2`, `libquote` and `libsyn` providers. It cannot be
  replaced by an empty default.

For scale only, the existing reference checkouts contain the following tracked
file sizes and Blueprint counts. These are **not r1 sizes or download estimates**;
the exact reference revisions are recorded, and r1 Git trees were not present
locally for a like-for-like measurement.

| Reference project | Tracked file size | Android.bp files |
| --- | --- | ---: |
| system/bpf | 131 KiB | 4 |
| hardware/google/gfxstream | 59.0 MiB | 62 |
| packages/modules/NeuralNetworks | 360.3 MiB | 26 |
| packages/modules/Virtualization | 1.10 GiB | 152 |
| platform_testing | 175.0 MiB | 262 |

Loading all five complete source roots would expose much more graph surface
than these seven definitions. No speculative full AOSP restoration, empty
default stubs, missing-dependency bypass or check suppression is recommended.
Use the smallest real provider scope needed by the retained recovery graph,
then require the strict graph and subsequent build to pass. This audit alone
does not prove a successful graph, recovery image, boot or device feature.

The third graph attempt later reported 19 errors after
`packages/modules/Connectivity/tests/common` was excluded: its shared defaults
are used by retained Connectivity, CTS and telephony tests. The missing
`libnetworkstackutilsjni_deps` that prompted that cut belongs to
[NetworkStack's unit-test defaults](https://android.googlesource.com/platform/packages/modules/NetworkStack/+/f9da1fc7154ea007aa835f88e8070c6ac46d54e9/tests/unit/Android.bp).
Restore the actual provider and common scope instead of extending the cuts to
all consumers. This follow-up does not change the initial 21-error record.

The r1 default requires `libnativehelper_compat_libc++`, `libapfjniv6` and
`libapfjninext`; the newer Evolution definition is different and was not copied.
The two JNI modules live in NetworkStack's `tests/unit/jni` and require APF
interpreter/disassembler/buffer libraries plus `libpcap`. All three missing
projects have independently verified `android-16.0.0_r1` pins:

| Supplementary provider | Pinned commit |
| --- | --- |
| [NetworkStack](https://android.googlesource.com/platform/packages/modules/NetworkStack/+/f9da1fc7154ea007aa835f88e8070c6ac46d54e9/) | `f9da1fc7154ea007aa835f88e8070c6ac46d54e9` |
| [APF](https://android.googlesource.com/platform/hardware/google/apf/+/40d36d317d9367641e685e88e46343f25b192fc4/) | `40d36d317d9367641e685e88e46343f25b192fc4` |
| [libpcap](https://android.googlesource.com/platform/external/libpcap/+/2e9a50d7694425ead7595bf98d3a9c0ab790e4f9/) | `2e9a50d7694425ead7595bf98d3a9c0ab790e4f9` |

APF's root, `v6` and `next` Blueprint files provide the required native libraries;
libpcap's root provides its host/vendor library. Nativehelper and logging are
already in the frozen base. These additions address the immediate JNI provider
chain, not a verified complete graph or runtime networking feature. The record
binds the exact source files and graph-three log separately from the original
failure, while the 391-project base remains unchanged.

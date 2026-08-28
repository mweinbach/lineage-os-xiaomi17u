# Android 16: which host tools can actually be swapped to ARM64?

Follow-up investigation, 28 August 2026 UTC. This refines the
[cluster feasibility report](android16-arm64-cluster-report.md): **absence of
an ARM64 package in AOSP does not mean that we must build every tool ourselves.**
Several replacements are available and now have direct execution evidence.

**Rust can run natively without rebuilding rustc. Java compilation tools and
standalone LLVM utilities are also good substitution candidates.** The
remaining work is selecting a complete compatible tool/library set in Soong,
preserving Android compiler changes, and testing real build actions. These
results lower the cost of trying a mostly native build; they do not establish
a completed native Android host port.

All execution probes below ran in new directories in the existing ARM64 Linux
VM. The active Android checkout, installed toolchains and system packages were
not changed. No full Android build, remote action, signing operation or phone
access occurred. [Commands, checksums and results](../research/arm64-cluster/tool-swap-probes.json)

## Practical ranking

| Candidate | How easy is the swap? | What the experiment established | What remains |
| --- | --- | --- | --- |
| Go 1.24.1 | **Easy** | Earlier matching ARM64 Go bootstrap passed | Package its matching installed stdlib archives; no compiler port required |
| Ninja, Kati, Python, Toybox | **Easy** | Android16 already supplies native versions; earlier execution probes passed | Keep their sibling libraries/stdlib and correct selected paths |
| JDK21 for javac, Turbine, D8 and R8 | **Easy for selected actions; moderate for all Java tools** | Native Ubuntu Java produced identical fixture outputs to the translated stock JVM | Pin/package the JDK, update paths, and keep JNI-dependent actions coherent |
| Official Rust 1.88.0 ARM64 | **Easy to run; moderate Soong integration** | Both GNU and musl compilers ran, accepted the tested Soong flags, and built/loaded native proc macros | Matching host libraries, path/variant changes, explicit unstable-feature configuration and Android compiler patch parity |
| `llvm-ar`, `llvm-objcopy`, `llvm-readobj` | **Easy to trial** | Native tools matched stock results on the tested inputs | Replay the actual Android flags/formats, including bitcode where relevant |
| Native Clang21 / LLD | **Moderate** | A community native package compiled both ARM64 Android and x86 host objects, and linked ThinLTO | Source provenance, MLGO policy, complete tool inputs and real-action tests |
| Bindgen + libclang | **Moderate; not tested here** | Source and native distro libraries exist | Replace executable and loaded library together; preserve compatible versions, libc and generated output |
| One global toolchain-directory/JAVA_HOME replacement | **Not a safe shortcut** | Actual JNI and Rust metadata failures demonstrate why | Separate execution binaries from target data and in-process dependencies |

## Rust: a real external-package option, with specific limits

The official Rust **1.88.0** release contains both
`aarch64-unknown-linux-gnu` and `aarch64-unknown-linux-musl` compilers, host
stdlibs and other components. Its upstream commit is
`6b00bc3880198600130e1cf62b8f8a93494488cc`, the same upstream commit reported
by Android's pinned compiler. Both report LLVM **20.1.5**. This is much closer
than swapping to an arbitrary current Rust release.
[Official release manifest](https://static.rust-lang.org/dist/channel-rust-1.88.0.toml)

The exact compiler identities differ:

```text
Android:  rustc 1.88.0-dev (6b00bc388 2025-06-23)
          Android Rust Toolchain version 13951379-linux-x86
Official: rustc 1.88.0 (6b00bc388 2025-06-23)
```

The GNU-native compiler compiled and ran a host program, compiled a native
proc-macro library, and used that library to compile another program which
printed `macro=42`. The common Soong flag set also compiled successfully with
`RUSTC_BOOTSTRAP=1`, including `-Z stack-protector=strong`, `dylib-lto`,
`link-native-libraries=no` and forced unwind tables. Without that environment
setting, the stable compiler rejected `-Z`, as expected. This is an explicitly
unstable compiler configuration, not ordinary supported stable-Rust usage.
[Soong flags](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/rust/config/global.go),
[RUSTC_BOOTSTRAP behavior](https://doc.rust-lang.org/unstable-book/compiler-environment-variables/RUSTC_BOOTSTRAP.html)

The musl-native compiler needed its dynamic loader and `libgcc_s.so.1`; Ubuntu
does not provide that musl environment by default. I used the existing native
AOSP musl1.2.5 loader and privately extracted a small official Alpine ARM64
musl libgcc package. Its APK signature was independently verified with
Alpine's published key, and its package/payload hashes are recorded. Nothing
was installed in `/lib` or `/usr`. The compiler then ran, compiled a static
native test program, and accepted the tested Soong flags.
[Official musl Rust recipe](https://github.com/rust-lang/rust/blob/1.88.0/src/ci/docker/host-x86_64/dist-arm-linux-musl/Dockerfile),
[Alpine package](https://pkgs.alpinelinux.org/package/v3.22/main/aarch64/libgcc)

A first musl proc-macro probe accidentally acquired a dependency on Ubuntu's
`libc.so.6` through the default C linker. Although that tiny test loaded, it
was not a valid demonstration of a consistent musl toolchain. I corrected the
private probe to use an explicitly musl-targeting native Clang and musl
libraries, rebuilt the macro, inspected its ELF dependencies, and successfully
loaded it with native musl rustc. The corrected library needs
`libgcc_s.so.1` and `libc_musl.so`, **not `libc.so.6`**. This is useful evidence
for the smaller musl integration path, not validation of every proc macro.

There are four concrete integration tasks:

1. **Do not reuse Android's compiled Rust libraries with the official compiler.**
   The attempted mix failed with `E0514`, even though the upstream commit
   matches: Rust metadata includes the compiler version string, and `-dev`
   differs from stable. Use matching host std/proc_macro libraries and rebuild
   dependent crates. The official host packages include both the `.rlib` and
   `.so` forms that Soong's prebuilt hook expects. These tests do not validate
   parity with Android's host-stdlib patches; if those are required, rebuild
   a coherent host library set rather than replacing only `libstd` beneath
   an existing `proc_macro` library. For example, Android's packaged Linux
   `Instant` implementation uses `CLOCK_BOOTTIME`; matching metadata and
   successful library loading do not establish the same time behavior.
   [Metadata encoding](https://github.com/rust-lang/rust/blob/1.88.0/compiler/rustc_metadata/src/rmeta/encoder.rs#L2411)
   and [Android's patched time implementation](https://android.googlesource.com/platform/prebuilts/rust/+/06a4f29f8512c6b77bdce81dd036a3e39954803b/linux-x86/1.88.0/lib/rustlib/src/rust/library/std/src/sys/pal/unix/time.rs).
2. **Keep Android's patched device-library sources.** Soong already rebuilds
   device std/core/alloc from bundled sources using `--sysroot=/dev/null` and
   explicit libraries. The source path containing `linux-x86` is not itself
   a binary-architecture problem. An upstream Android target std archive is
   not an equivalent replacement for the patched platform library sources.
   [Source selection](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/rust/toolchain_library.go),
   [Rust rule](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/rust/builder.go)
3. **Add ARM64 host-library/prebuilt selection.** The current hook implements
   x86 host variants, while native ARM64 Soong expects musl. Simply placing
   `rustc` at a new path does not create its std/proc_macro dependency graph.
   Put the unstable-feature setting in the relevant Rust action or a narrow
   wrapper: Ninja's environment allowlist does not include `RUSTC_BOOTSTRAP`.
   Do not enable unrestricted environment propagation.
   [Host prebuilt hook](https://android.googlesource.com/platform/prebuilts/rust/+/06a4f29f8512c6b77bdce81dd036a3e39954803b/soong/rustprebuilts.go),
   [Ninja environment](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/ui/build/ninja.go)
4. **Preserve Android's compiler hardening changes before production use.**
   The builder at `083779c7ebba8f829d4c38fe4f1ef6fd0d797e56` applies 11 patches.
   Several are library/build changes, but `rustc-0072` adds PAC/BTI attributes
   to compiler-generated synthetic functions. Official1.88 lacks this LLVM
   code-generator patch. Rebuilding std does not supply it. Its relevance
   depends on the selected architecture features; do not disable branch
   protection to sidestep it. A patched native compiler, or another compiler
   with the equivalent fix and a validated migration, is needed before
   claiming parity for affected builds.
   [Pinned build manifest](https://android.googlesource.com/platform/prebuilts/rust/+/06a4f29f8512c6b77bdce81dd036a3e39954803b/linux-x86/1.88.0/manifest_13951379.xml),
   [PAC/BTI patch](https://android.googlesource.com/toolchain/android_rust/+/083779c7ebba8f829d4c38fe4f1ef6fd0d797e56/patches/development/rustc-0072-Add-PAC-BTI-attributes-to-synthetic-functions.patch),
   [Soong branch-protection flags](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/rust/config/arm64_device.go)

The matching official **musl** compiler is the more natural first candidate
for native Soong's existing host model. A GNU compiler is easy to run, but
its proc macros and loaded libraries need a GNU environment too. Keeping
different libc environments in separate processes is valid; mixing them
inside one process requires much more care.

One additional recorded limit: the existing **x86 musl** Rust launcher failed
under this Rosetta VM with `AT_BASE not found in aux vector`. The ordinary
x86 GNU Android rustc executed successfully. Translation compatibility must
therefore be checked per package, not inferred from the name `rustc`.

## Java: several useful swaps already passed

The stock x86 JVM is Android_PDK **21.0.4+-12414455**; the installed native
Ubuntu JVM is **21.0.12+8-1-24.04-Ubuntu**. These are different vendor/patch
builds, but all 22 bounded comparison commands succeeded:

| Actual tested action | Native versus stock result |
| --- | --- |
| javac `--release 8`,17,21 | Identical class-file bytes for a fixture using generics, lambdas/streams and try-with-resources |
| Actual built Turbine JAR | Identical header-JAR bytes |
| Actual built D8 wrapper JAR | Identical `classes.dex` bytes |
| Actual built R8 wrapper JAR | Identical `classes.dex` bytes |

The jars were existing Evolution X build outputs, and all original input
hashes remained unchanged. This was not a newly built stock platform graph.
It validates these tools on the fixture, not every Java action or input.

The important counterexample is **Conscrypt JNI used by signapk**. Calling
`Conscrypt.checkAvailability()` with the existing library succeeded under the
translated JVM and failed under the native JVM with `UnsatisfiedLinkError`:
it could not load the AMD64 shared library on AArch64. No keys, certificates or
signing operation were involved. Keep that JVM/JNI pair translated initially,
or rebuild the JNI library and its dependencies for the native JVM's libc.
[signapk dependencies](https://android.googlesource.com/platform/build/+/b815dded1eafbf06191a6ae306956bb6ed6fb415/tools/signapk/Android.bp),
[invocation and library path](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/java/app_builder.go)

For integration, package a pinned JDK **inside the source execution root** and
select its relative path. Direct `/usr/lib/jvm` invocation was fine for the
probe, but Soong's Java source-path construction rejects absolute paths and
REAPI needs complete declared inputs. Some BP tools such as `javap` also have
independent x86-only definitions. `JAVA_HOME` alone does not update those.
[Java path selection](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/java/config/config.go),
[path validation](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/android/paths.go),
[JDK BP definitions](https://android.googlesource.com/platform/prebuilts/jdk/jdk21/+/ef5bcc92586b839ae3dbacc154127092fa4002ec/Android.bp)

## LLVM: an immediately usable experimental package exists

The community `lzhiyong/termux-ndk` r29 archive supplies native AArch64 Clang,
LLD and LLVM utilities, despite retaining a `prebuilt/linux-x86_64` directory
name. Its reported version is LLVM21.0.0 based on `r563880c`. The downloaded
archive SHA256 is
`02e10e4ddfe8deaeb0bd0cf29d04c981ed5bc8a5d6b560ebb9e7661f472d684b`.
[Release](https://github.com/lzhiyong/termux-ndk/releases/tag/android-ndk)

Of 32 commands, 31 succeeded and one deliberately tested missing MLGO:

- Native Clang compiled Android ARM64 objects, ThinLTO bitcode and x86 host
  objects. It also used the original AOSP resource headers successfully.
- Native LLD linked stock-generated ThinLTO bitcode. A native-generated x86
  executable subsequently ran under Rosetta.
- Native ar, objcopy and readobj matched stock results on the samples. Simple
  compiler output matched after removing `.comment`; the `.text` bytes matched
  without modification. Whole original object files were **not** identical.
- The stock MLGO register-allocation advisor option failed with the native
  linker because this package lacks the model support.

Soong already offers **`THINLTO_USE_MLGO=false`**, which removes the inspected
MLGO linker options while retaining ThinLTO. This can make a native experiment
much easier, but changes optimization choices and potentially size/performance;
it is not stock-setting equivalence. Alternatively keep MLGO-dependent links
on the existing translated stock linker while testing native compilation.
The source switch was inspected, not applied to the active build.
[LTO options](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/cc/lto.go),
[ML inliner options](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/cc/compiler.go)

**This package is not yet a production compiler recommendation.** Its vendor
string is hardcoded, its release tag resolves to an older 2023 commit, and
the inspected 2026 recipe postdates publication of the asset. The checksum
pins tested bytes; it does not establish an attested, reproducible match to
Android's complete LLVM patch set. Audit/rebuild from pinned sources before
trusting production outputs. The package also lacks non-runtime `libclang.so`
or `libclang.a`, so it does not solve bindgen's loaded-library dependency.
[Inspected recipe](https://github.com/lzhiyong/termux-ndk/blob/a9898a978cd28951bbbdae989b408cd7dbc11293/patches/build_stage2.sh)

Official upstream LLVM21.1.8 and apt.llvm.org ARM64 packages are another option,
particularly for standalone utilities and native glibc `libclang`. They are
not Android's patched21.0.0 compiler. Bindgen itself can be built from source
as a native tool, but Soong separately pins its Clang to `r563880`, selects
`CLANG_PATH`, `LIBCLANG_PATH` and `RUSTFMT`, and its generated host-target
metadata also needs attention. A native glibc bindgen/libclang pair is a
bounded alternative to a complete musl LLVM port; that pair was not tested
here.
[Official LLVM release](https://github.com/llvm/llvm-project/releases/tag/llvmorg-21.1.8),
[official ARM64 package index](https://apt.llvm.org/noble/dists/llvm-toolchain-noble-21/main/binary-arm64/Packages.gz),
[bindgen rule](https://android.googlesource.com/platform/build/soong/+/f389fa2a2a768a93bc99957e2288f3fbee032bff/rust/bindgen.go)

## What this changes about the recommendation

The earlier assumption that a maintained native path would start by building
all missing compilers was too broad. **Try the available native packages first.**
The smallest useful integration is selective native Java compilation plus
standalone native LLVM actions; official musl Rust is now a concrete candidate
for the next Soong host-library experiment.

Retain the full x86 process/library pair for unconverted JNI, bindgen and
other difficult tools. Do not globally replace `linux-x86` directories, copy
NDK target runtimes over AOSP platform runtimes, mix Rust metadata versions,
or remove compiler hardening to get a green build.

The next acceptance gate is **one real Soong action with each replacement**,
followed by a small native Rust module with matching host libraries and
source-built Android std. That work has not been performed. A complete native
host/image remains an integration project, but the entry point is now much
smaller and more concrete than the first report's compiler-build estimates
suggested.

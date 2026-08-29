# DEX imports as runtime shared libraries

The [reviewed Soong patch](../patches/evolution/dex-import-uses-library.patch)
adds the missing runtime dependency provider to `dex_import`. It preserves the
actual DEX build path, installed filename and partition, and carries ordered,
nested required dependencies into an app's class-loader context. The patch is
now installed in the pinned Linux guest source. On **August 29, 2026 at
22:57:13 UTC**, its native test binary passed all five added fixture tests and
eleven subtests, with **zero failures or skips**. This verifies synthetic Soong
graph behavior; it does not establish a current Camera JAR rebuild, APK
integration, or physical Camera/Leica support.

The patch is limited to `java/java.go`, its test registration in
`java/Android.bp`, and a new `java/dex_import_test.go`. Its base is
`build/soong` revision `cbcbea9e65503ca15b363a0b06dda88fdbcb0154`, already bound
by the [resolved platform manifest](../research/source-snapshots/evolution-bka-20260827.xml).
The [sanitized record](../research/dex-import-uses-library.json) binds the source
exports, before/after hashes, patch, and the historical August 27 host results.
That record remains unchanged because the camera input contract pins it. The
separate [native fixture record](../research/dex-import-native-fixtures.json)
binds the August 29 compilation, execution, sandbox and retained failed attempt.

## August 29 native fixture checkpoint

The existing `bka` / `bp4a` source and user output were reused. The normal
`soong/bootstrap.ninja` dependency target built
`host/linux-x86/bin/go/soong-java/test/test` using the pinned Go **1.24.1
linux/amd64** toolchain. The first build completed nine actions with exit zero,
including compilation of the patched Java package and generated test main,
then linking the test binary. Its harness subsequently failed because it
expected Ninja's idle message on stdout; this pinned Ninja wrote it to stderr.
That attempt remains a failed harness result, with no fixture execution.

The v2 harness changed only that stream handling. It requires the exact idle
message across the separately retained streams, rejects scheduled work and
extra diagnostics, and verifies the existing binary through the unchanged
normal dependency target. It then ran exactly `TestDexImportUsesLibrary*`
with `-test.count=1`, **without short mode**, and checked all 16 run/pass events.
The full Java suite was not run and its `test.passed` stamp remained absent.
This targeted host component does not invoke Kati or waive a product failure.

Compilation kept Android source read-only and the existing output writable.
Fixture execution kept both source and output read-only, with only new results
and temporary files writable within `/work`. Both phases recorded zero capability masks,
namespace identifiers, UID/GID maps and mount evidence. Source/tool hashes and
the bootstrap graph remained unchanged. The test binary is 40,984,727 bytes,
SHA256 `637cb8a350be37a91f890ef3d5cad41d217700a03d768d39835b84179f17549b`.

| Native evidence | SHA256 |
| --- | --- |
| Failed v1 harness receipt, after successful compilation | `1a37d9dae32ddc974d5d6e1436ec679868b1a78e9f5596b1c788ebb645c163b5` |
| Successful v2 dependency/freshness receipt | `0831bd3f0398301918937e208c2e6c0ee8cc46b2b249d09aed4a9086df320d23` |
| Successful v2 fixture execution receipt | `a618a397fee3fb0fc723f72f5bebdd96bf886613ccfd6f1b6739ce66038a7fe6` |

Raw evidence remains under ignored `artifacts/build-validation/nezha-dex-fixtures-*`.
The fixtures inspect generated strict manifest-check and dexpreopt rules; they
do not execute those rules, process proprietary JARs/APKs, or run dex2oat.
Actual installed library names, package membership, ODEX/VDEX and Camera APK
checks remain separate from this result.

## Names and dependency behavior

The module name must equal the runtime name from the installed library XML.
Soong resolves a namespace-qualified reference such as
`//vendor/example:runtime.parent` to `runtime.parent`; `stem` may independently
retain an original JAR filename. The provider returns the actual install path,
including a system-ext or product partition, rather than constructing a system
path from the module name. The JAR remains a DEX input: this change adds no
`.class` header or compilation provider.

The only added Blueprint property is `uses_libs`, for the JAR's **required**
runtime dependencies in their declared order. The patch uses the existing
uses-library dependency tags and context construction, preserving subtrees
rather than flattening transitive libraries into the app's manifest list.
Missing required modules, class-only imports, non-Java modules, SDK stubs without
an implementation, and dependency cycles fail the graph fixtures. The patch
does not suppress those failures or disable dexpreopt. Its ordinary platform
build behavior is tested; it retains the upstream helper's separate unbundled
build behavior, which this experiment does not validate.
[Pinned dependency handling](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/java/app.go)

An app may declare the exact-name DEX import in its existing
`optional_uses_libs`. The patch does **not** expose `provides_uses_lib`, JAR-level
`optional_uses_libs`, `enforce_uses_libs` or `exclude_uses_libs`. This restriction
has a concrete reason: the pinned context encoder filters optional libraries
by runtime name against `product_packages.txt`. A prefixed module name with a
different advertised runtime alias can pass a name-only manifest check yet
disappear from the encoded context. The experiment reproduces that omission;
an alias API would need additional product-package mapping work.
[Pinned optional-library filter](https://github.com/Evolution-X/build_soong/blob/cbcbea9e65503ca15b363a0b06dda88fdbcb0154/scripts/construct_context.py)

The patch does not generate or validate library-registration XML. It also does
not establish that every declared dependency is installed. Product selection,
exact XML names and paths, required dependencies and the generated package list
must be checked together in the separate [Camera runtime input bundle](camera-runtime-inputs.md).
The earlier prefixed Camera module names are not silently renamed by this patch. The tested
consumer is Soong's `android_app_import`; Make-defined app consumers and DEX
config export to Make are outside this patch's verified scope.

## Historical August 27 host verification and its limits

Seven existing source exports were rehashed against their recorded archives.
No source sync, clone, guest source edit or Android output edit was needed.
Only the intended three Soong source files differ in the isolated host fixture;
other exported project files remain unchanged. The patch applies with
`git apply --check --whitespace=error` to pristine files from the pinned archive,
the resulting three hashes match the tested files, reverse checking succeeds,
and both Go files are `gofmt` clean.

The actual Java fixture suite ran with local Go 1.26.2, `GOOS=darwin`,
`GOARCH=amd64` through Rosetta, and `CGO_ENABLED=0`. The Go driver itself is
Darwin ARM64. `GOPROXY=off`, `GOSUMDB=off`, `GOTOOLCHAIN=local` and `GOENV=off`
prevent dependency or toolchain downloads; the Go workspace uses the pinned
local exports. This is a host fixture test, not the guest's pinned Linux Go
toolchain or execution of generated Android build rules.

| Named test and subtest results | Unpatched baseline | Patched repeat |
| --- | ---: | ---: |
| Pass | 853 | 869 |
| Fail | 35 | 35 |
| Skip | 28 | 28 |

All existing named outcomes are identical. The 35 failing names also have the
same diagnostic sets after removing lifecycle timing, repeated lines and error
enumeration counters. The 16 added passing events cover the new fixture tests
and their subtests. The full suite **does not pass**:
both commands exit 1, with a separate package failure event. Twenty-nine named
failures encounter macOS SDK 27 outside the pinned supported-version list;
six have existing Lineage resource expected-output mismatches. Neither the
supported SDK list nor those expected outputs were changed to make the result
appear green. The earlier baseline, intermediate attempts and two completed
patched runs are preserved.

The fixtures verify actual generated providers and rules: default/stem/system-ext
paths, a namespace-qualified optional dependency, ordered required children and
a nested leaf, no invented class-file provider, an enabled dexpreopt rule and
an APK manifest-check command without the relaxation flag. They reject all
four unsupported properties and the dependency errors above. These fixtures
do not contain or execute proprietary JARs or an APK.

A separate experiment feeds the fixture's emitted JSON into the **unchanged
pinned** `construct_context.py`. It checks the complete host and stored-device
context strings, including the nested required subtree and the original
installed filename. It also verifies optional filtering with only the exact
parent name present and demonstrates the incorrect alias-name case producing
an empty context. The required children are not removed by optional filtering;
their installation still needs product validation.

The same experiment runs the unchanged pinned `manifest_check.py` against a
synthetic XML manifest. Exact direct optional names pass. Reordering them,
substituting a prefixed name, omitting a direct name, or promoting a nested
required library into the direct list each fails with exit 255. No relaxation
flag or missing-library exception is supplied. These eight expected outcomes
pass; they do not execute dex2oat or establish the real Camera APK's build or
runtime behavior.

Private receipts, all under `reports/dex-import-clc-20260827/`:

| Receipt | SHA256 |
| --- | --- |
| `patched-java-verification.json` | `b15572c850e2c1865b9968f3f9b18218266e6d116195aeea1099f2a65949fcaf` |
| `context-roundtrip/receipt.json` | `ff9985c4e7ef0afd049a4322d74c204b47e0e4080c6e6c685289492056d24210` |
| `patch-apply-verification.json` | `1954364b35a885d46b6bf4fe6793059b3d4b6671f1fc421687bd89aed14f5b66` |

The ordinary offline workspace checks need none of those private files:

```sh
python3 -m unittest discover -s tests -p 'test_dex_import_patch.py' -v
```

## Integration still to perform

The patch's guest installation, native test compilation and added fixture run
have now passed. The separately admitted exact-name Camera runtime bundle still
needs its current native JAR/JNI/XML rebuild and inspection of installed paths,
product package membership, generated class-loader contexts and ODEX/VDEX.
Earlier component builds and host fixtures do not substitute for that result.

The [Camera APK prerequisites](camera-apk-integration.md) remain separate:
signing identity, signature-only permissions, the privileged-app DEX packaging
contract and the eventual strict APK validation rule are not solved by this
provider. No APK is rewritten, signed, imported or installed here. The patch
changes no manifest checker, signature check, permission policy, dexpreopt
setting, SELinux rule or native ELF check. Camera and Leica feature claims
still require corresponding device tests after explicit authorization.

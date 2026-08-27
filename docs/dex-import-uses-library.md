# DEX imports as runtime shared libraries

The [proposed Soong patch](../patches/evolution/dex-import-uses-library.patch)
adds the missing runtime dependency provider to `dex_import`. It preserves the
actual DEX build path, installed filename and partition, and carries ordered,
nested required dependencies into an app's class-loader context. It has passed
isolated graph tests and strict checker experiments. **This work has not applied
the patch to the Linux guest, imported the Camera APK or changed the phone.**
This is the snapshot at `2026-08-27 21:29 UTC`; later guest integration needs a
separate build receipt.

The patch is limited to `java/java.go`, its test registration in
`java/Android.bp`, and a new `java/dex_import_test.go`. Its base is
`build/soong` revision `cbcbea9e65503ca15b363a0b06dda88fdbcb0154`, already bound
by the [resolved platform manifest](../research/source-snapshots/evolution-bka-20260827.xml).
The [sanitized record](../research/dex-import-uses-library.json) binds the source
exports, before/after hashes, patch, test results and private receipts.

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
must be checked together when making the next vendor bundle. The current
prefixed Camera module names are not silently renamed by this patch. The tested
consumer is Soong's `android_app_import`; Make-defined app consumers and DEX
config export to Make are outside this patch's verified scope.

## Verification and its limits

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

The next step is review and an idle-guest application to the exact pinned
source, followed by a real Soong rebuild. A new, separately admitted vendor
selection must use exact runtime names, bind its XML and JAR inputs, and verify
the actual product package list and class-loader contexts. The current Camera
dependency bundle and earlier source receipts remain historical inputs.

The [Camera APK prerequisites](camera-apk-integration.md) remain separate:
signing identity, signature-only permissions, the privileged-app DEX packaging
contract and the eventual strict APK validation rule are not solved by this
provider. No APK is rewritten, signed, imported or installed here. The patch
changes no manifest checker, signature check, permission policy, dexpreopt
setting, SELinux rule or native ELF check. Camera and Leica feature claims
still require corresponding device tests after explicit authorization.

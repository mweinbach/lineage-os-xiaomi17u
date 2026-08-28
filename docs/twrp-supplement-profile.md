# Additional native recovery test gates

The pinned SystemUI source contains a required production animation library and
a Robolectric test in the same Blueprint file. The original Robolectric project
also supplies runner libraries used by retained modules, alongside its own
integration tests. Removing those complete files or replacing their providers
would remove more than the native recovery profile needs to omit.

Patches 0015 and 0016 change only three `android_robolectric_test` constructors:

| Project and file | Module | Property change |
| --- | --- | --- |
| `frameworks/libs/systemui/animationlib/Android.bp` | `animationlib_robo_tests` | Replace its existing literal `enabled: true`. |
| `external/robolectric/integration_tests/ctesque/Android.bp` | `CtesqueRoboTests` | Add an enabled selector where no enabled property existed. |
| `external/robolectric/integration_tests/nativegraphics/Android.bp` | `NativeGraphicsTests` | Add an enabled selector where no enabled property existed. |

All three use the existing typed Boolean
`nezha_twrp.native_recovery_only`. A true value selects `false`; a false value or
missing variable selects `unset`. The SystemUI replacement has an additional
source proof: its exact pinned constructor uses the DeviceSupported Android
factory, has no inherited defaults or enabled overrides, and Android is enabled
by default. Its unset branch therefore preserves the previous effective true
value. This is specific to that module and those source pins, not a general
equivalence between `unset` and `true`. Incorrectly typed conditions are errors,
and the existing ForcedDisabled behavior remains in force. The two insertions
preserve the original absence of an enabled property when the profile is inactive.

The production `animationlib` module remains unchanged, as do
`NativeGraphicsTestsAssetsLib`, `NativeGraphicsPseudoApp`, all other definitions,
licenses, defaults, dependencies and source lists. The pinned Soong dependency
dispatcher skips the normal dependency
mutators of a disabled module; it does not skip Blueprint parsing or all other
validation. Neither patch changes the original Robolectric runtime-helper gate,
its compiler build-property producer, or any security or missing-dependency check.

SystemUI remains pinned to `9aacbcb77aa9353e75bc7c4ebc51d20b8b241b62` and
Robolectric to `559c38b2cb0fbd87f2118bdcb8bea6f536164d70`. They are supplementary
owners, separate from the unchanged 391-project Repo snapshot. The queue binds
each original and resulting file to its Git blob ID, SHA-256 and length; the
[supplementary patch contract](twrp-supplement-patching.md) controls application.

The previous fourteen patch entries, payloads and metadata are unchanged. In
particular, the initial nineteen-module and three-helper audit records retain
their historical counts and source exclusions. The six exclusions recorded for
Graph 14 are not a statement of the current device source selection. Companion
source admission and any restoration of original Robolectric plugin or Clearcut
providers are separate changes in the source configuration and device target.

Offline tests validate the exact constructor/property changes, hashes, preserved
history and rejected mutations. Sealed candidate receipts also record temporary
Git application checks and the pinned-source semantics review. These are source
checks, not an evaluated Android graph, compiled recovery or device test. This
profile deliberately omits the three JVM tests and does not claim full Android
test coverage or authorize a recovery image to boot or flash.

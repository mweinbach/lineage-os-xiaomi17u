# Aperture extension metadata cache correction, 2026-09-08

**Later device evidence:** V10 is installed. Ordinary Xiaomi Photo and all ten
warm Aperture effect cases pass; the high-resolution telephoto, Xiaomi RAW/Ultra
RAW and video failures remain open. See the [v10 runtime record](camera-v10-install-validation-20260908.md).

**All ten Aperture effect captures saved and decoded Ultra HDR photos on v9,
but switching rear effects can close the activity.** A logged None-to-Bokeh
switch selected a 1440×1080 preview, which the extension rejected. The bundled
CameraX 1.7.0-alpha03 caches extension metadata by camera ID alone. The first
effect queried can therefore supply the supported sizes for later effects on
the same camera.

The recorded Bokeh platform query offers 1280×960, 1280×720 and 1564×720 preview
sizes. During the failed switch, CameraX selected 1440×1080, then reported
`Repeating request surface size 1440x1080 not supported!`, graph configuration
error 4, and a critical error in CameraActivity. The activity finished; this
was not a fatal app or camera-provider process crash. Reopening the same
process retains its cache. A cold process launch permits a capture using the
selected effect's correct sizes.

[Upstream CameraX source](https://android.googlesource.com/platform/frameworks/support/+/ff1e2437ab0985eb3d490e56ae4d5ac2c5306356/camera/camera-camera2-pipe/src/main/java/androidx/camera/camera2/pipe/compat/Camera2MetadataCache.kt)
already keys this cache by both camera ID and effect. The observed upstream
head is `ff1e2437ab0985eb3d490e56ae4d5ac2c5306356`; Google's published Maven
metadata still selected 1.7.0-alpha03 when checked. The guest's existing AAR
was downloaded independently from Google and matched SHA256
`9d3f3a679f06e3423fd51da1477a9a121e57235a90c5c096d8c3703d7303fe63`.

[Patch 0033](../patches/evolution/0033-camerax-extension-metadata-cache.patch)
backports the upstream extension cache key correction. It preserves the
existing permission-sensitive uncached path and synchronization. The separate
upstream change to cache CameraExtensionCharacteristics is outside this
backport. No preview sizes or effect availability are invented.

The [input contract](../config/nezha-camerax-extension-cache.json) pins the
[source template](../templates/camerax-extension-cache/Camera2MetadataCache.kt),
patch, original AAR, original classes JAR, Kotlin compiler, SDK stubs and
compile dependency JAR. [The materializer](../scripts/camerax_extension_cache.py)
compiles that source, checks every public method descriptor, and replaces its
three generated class files in the AAR. All 854 other classes-JAR members and
12 other outer AAR members remain byte-identical, including the original full
Kotlin module metadata, resources and ProGuard rules. Archive member sets are
preserved. The generated AAR is an ignored public AndroidX derivative, not a
modification to Xiaomi Camera's proprietary APK.

The materialized AAR has SHA256
`09ef711c3a543e43d1ce392492b6b3a5516af1a944891374926e287a7968ce12`.
Its receipt is under `artifacts/camerax-inputs/nezha-extension-cache-20260908-v1/`.
A direct JVM harness loads the real library classes with Android host stubs:
for two camera IDs and five effects, the original library returns metadata
from the wrong effect in 16 synchronous/suspend lookups. The corrected classes
pass 24 assertions with zero cross-mode aliases. An unseeded effect enters the
uncached path instead of returning another effect's metadata. This verifies
cache behavior, not an Android camera session. Eight offline materializer tests
pass, as do all 939 current tests and the full 4,881-test suite (190.625 seconds
plus shell checks).

Private runtime evidence and retained public source inputs are under
`reports/camera-completion-20260907/v9-validation/extension-transition-diagnosis/`
and `transitions/`. The combined source is staged as `nezha.0c10ad024d3033691a2825cc`, with 659
verified inventory rows. The three rebuilt classes are byte-identical in
Aperture's Soong input to R8. Its Android app build passed all 63 actions,
including signing and dex preoptimization, with 659 unchanged source records.
The optimized APK was inspected after R8. Its active synchronous lookup is
inlined into `Camera2CameraMetadata.awaitExtensionMetadata(int)` and both reads
and populates `extensionCache[cameraId][extensionMode]`. R8 removes the unused
suspend method; both source methods passed the separate JVM harness. The
retained DEX and mapping receipt is `v10-aperture-run/dex-cache-verification.json`
under the camera-completion report directory. The full target-files build passed with all 659 source rows unchanged.
Its archive contains the exact inspected Aperture APK. The
[v10 package record](camera-v10-package-20260908.md) tracks final delivery
verification; an installed effect-switch test remains pending. The
phone remains on v9, `nezha.393aae12fba9ebe8627cdc38`, slot A, Enforcing. Final
cleanup restores rear camera, effect None, RAW off, Ultra HDR on and USB
stay-awake off, with all three camera/test apps stopped.

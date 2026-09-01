# Additional GMS optional-library declarations

The read-only native audit of 95 selected, enforced GMS consumers completes
with **91 passes and four manifest mismatches**. The customization bundle's
missing optional `wear-sdk` remains covered by the separate
[0018 preparation](gms-customization-optional-library.md). The
[0019 patch](../patches/evolution/0019-gms-prebuilt-optional-libraries.patch)
corrects only the other three Make declarations. The original failed audit is
retained; this preparation does not turn it into a successful build.

| Module | Declaration correction | Retained signing and placement |
| --- | --- | --- |
| `CrossDeviceAccessServicePrimary` | Remove stale `org.apache.http.legacy`; retain `androidx.window.extensions`, then `androidx.window.sidecar` | `platform`, nonprivileged system-ext app |
| `PersistentBackgroundServices` | Add optional `com.google.input.gia.giaservicemanager` | PRESIGNED, privileged system-ext app |
| `SafetyHubPrebuilt` | Prepend optional `wear-sdk` before the existing HTTP, window-extensions and window-sidecar entries | PRESIGNED, privileged product app; `EmergencyInfo` override unchanged |

All three APKs declare no required libraries. SafetyHub's exact optional order
is `wear-sdk org.apache.http.legacy androidx.window.extensions
androidx.window.sidecar`. The HTTP removal is specific to CrossDevice; removing
it from SafetyHub or appending Wear at the end would still fail the strict
checker. The patch changes no APK bytes, required-library settings, signing,
privilege, package placement, overrides, dexpreopt settings or enforcement
settings. It adds no provider, registration file or global exception.

The [source contract](../patches/evolution/gms-prebuilt-optional-libraries.json)
pins `vendor/gms` at `89c3940a77298c204c55a21efded92ddafb59fe9`, the same
reviewed `bka` source base as 0018. The fresh September 1 native capture verifies
HEAD, named remote `evo`, clean status, and unchanged hashes, modes and stat
identities for all four affected Makefiles and APKs. The three new source
changes retain mode `0644`:

| Makefile module | Original bytes | Patched bytes | Patched SHA-256 |
| --- | ---: | ---: | --- |
| CrossDevice | 1,046 | 1,023 | `a5e6b9aa8ebe94a4863f325a54ad6e105774b9f09cab323aa6387a8131c79a94` |
| Persistent | 966 | 1,038 | `f9df8965324973489f04a13a54c2e7b340d83d37f54787130320ac591307e2a0` |
| SafetyHub | 1,174 | 1,183 | `cc93b54e9c4331ac16eeaa660a412d6aa7e4b97fb837436ac7f17a2cd85bb863` |

The contract records the exact original APK hashes and strict diagnostic tags.
Those tags come from the actual native checker against the guarded APKs, not
from inferred package names. The audit removes only the ordinary status-output
argument to keep the source and build output read-only; it retains enforcement,
the actual native `aapt2`, dependency configurations and bootclasspath inputs.
Each mismatch exits 255. Seven selected declarations were omitted from this
audit's enforced-consumer scope. The 95 checks therefore do not establish full
GMS coverage, ordinary build stamps, per-APK upstream LFS reconciliation,
signature validation or target-files completion.

Two isolated host copies apply 0018 followed by 0019 and reproduce all four
expected Makefiles. Zero-fuzz forward and reverse checks preserve every mode,
reject duplicate 0019 application, and restore all originals. Eight admission
cases reject changes to the three preimages or modes, the project revision,
or the patch. The committed 0018 patch, record and guide remain byte-identical.

Eight host fixtures execute the unchanged pinned manifest checker against
synthetic XML derived from the actual diagnostic library lists. All three
corrected declarations pass with empty status files. The original three
declarations fail, as do a SafetyHub list with Wear appended and a SafetyHub
list with HTTP incorrectly removed. These are host semantic checks; they do
not process the proprietary APKs, regenerate the native graph or establish
actual dexpreopt contexts.

The Make rule still sends the full declared optional list to the checker and
separately filters optional dexpreopt dependencies by product membership.
The captured product list includes HTTP and both window libraries; it has no
exact Wear or GIA service-library entry. CrossDevice loses only its stale
explicit HTTP declaration. The existing automatic SDK-28 HTTP compatibility
handling stays in place. That compatibility special case also explains why
the original command has two window-library configuration inputs and no
explicit HTTP configuration input; it does not mean HTTP is unavailable.
Adding an optional declaration does not authorize fabricating a provider or
waiving checks. Actual module contexts, provider availability, installed JARs
and library registration remain separate native validation. Early product
filtering can miss indirectly installed libraries.

The next admission is one separately reviewed four-file source transaction
combining 0018 and 0019, with new source and build-identity bindings. The prior
537-file/thirteen-project source and `8643` identity remain the historical
baseline until that transaction succeeds. Then regenerate the ordinary
`bka` / `bp4a` user graph and require fresh successful execution of all four
real strict status actions before module/dexpreopt checks and the resumed
package build. A corrected read-only probe is useful evidence, but is not an
ordinary status producer or source-adoption result.

Normal Android enforcement, the 4 KiB baseline, working76 recovery, strict
APK checks, VINTF, AVB and rollback constraints remain unchanged. Signed-image
admission, functional behavior, ROM boot and OTA validation are outside this
patch preparation.

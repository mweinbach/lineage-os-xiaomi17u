The exact v9 policy comparison now fails at **two assertion sites instead of
four** when a private, derived vendor CIL replaces the original vendor CIL.
Both compiler invocations still exit **255** and produce **no policy binary**.
This is a prototype correction, not an adopted device change: the experiment
did not modify the current vendor image, vendor bundle, ODM image, active
source, build output, or phone.

The [v9 DSP build](dsp-policy-build.md) supplies seven actual framework CIL
files. Three captured factory vendor/ODM CIL files complete the ten-file
assembly. The baseline uses those ten originals; the corrected case changes
only input index 7, `vendor_sepolicy.cil`. Both use the same compiler, mappings,
input order and strict flags: `-m -M true -G -c 30`, without `-N`. Each has a
fresh, separate output directory. One authorized checker invocation ran the
two compiler commands; neither case was retried.

| Observed result | Original vendor CIL | Derived vendor CIL |
| --- | ---: | ---: |
| Compiler exit status | 255 | 255 |
| Neverallow assertion sites reported | 4 | 2 |
| Combined policy binary produced | No | No |
| Combined policy permissive analysis | Not run | Not run |

The original [Binder audit](selinux-user-integration.md) identified 67 allow
occurrences, representing 65 distinct normalized statements. Each involves
one process domain and one of five service-object labels that belong to
`object_r`, not `domain` or role `r`. The correction replaces only those
statement spans with spaces, retaining every line delimiter and every other
byte. Original and derived files both contain 1,708,593 bytes; 5,523 byte
values change within 5,823 selected span bytes. Duplicate occurrences are
handled separately, not silently deduplicated.

The classification was repeated against the actual v9 inputs. Both parsers
agree on every top-level statement in all ten files. The two Binder assertions
are found by normalized identity and resolved type sets, not historical line
numbers. The v9 closures still contain 596 process-domain types and the same
596 role-`r` types. The 35 target-object and 32 source-object occurrences
disappear from the derived assembly. Its Binder allow count falls from 3,300
to 3,233; no permission is added and no provider is guessed or retargeted.

All **6,366 assertions** remain: 5,976 `neverallow` statements and 390
`neverallowx` statements, including all 615 vendor neverallows. All 32 related
FD rule occurrences, representing 31 distinct statements, remain unchanged.
So do valid process Binder grants, service lookup and registration grants,
type/role declarations and compatibility mappings. Preserving an FD grant is
not proof that the grant is necessary. No service object is promoted into a
process domain. The original Xiaomi macro source has not been recovered, and
the display service's runtime provider remains unresolved.

The corrected compiler log reports only the existing `init_dev_config`
property setters for `media_variant_prop` and `apexd_select_prop`. Their
versioned vendor assertions and original platform grants remain visible and
unchanged. The compiler prints only its first four examples for each larger
Binder failure group in the baseline; the complete 67-occurrence count comes
from the separately bound static audit, not those abbreviated examples.

The sandbox observer executes immediately before each compiler. It records
the root filesystem, source, all build outputs, inputs, tools and provenance
as read-only; only the active experiment's results and temporary directory are
writable. All four observed namespace identities differ from the parent, and
the observed capability sets are zero. Its namespace UID/GID 65534 maps to
global UID/GID 0. The raw nsjail warnings about that mapping are preserved; this
is not a claim of unprivileged host execution or a wholly self-contained
runtime.

The read-only collector rehashes all 76 recorded input bindings and verifies
77 observer bindings twice, including the result receipt. Seven raw outputs
are copied and hashed on the host: the receipt, both complete stdout/stderr
pairs, and both sandbox observations. The original CIL, derived CIL, transfer
receipts and diagnostics remain private. Hashes, aggregate results and exact
receipt paths are in [the public record](../research/binder-policy-correction.json).
The comparison receipt SHA256 is
`257ad9f0c0a1903b9e339897253bc42684041db997bead3c2d81760410a1d514`;
its readback receipt SHA256 is
`f8308dc4a85ee71ba4095971697cb274f46950996ab6ef611e5738c815a59f7c`.

The source package remains a user-provided, factory-named China TGZ with
unauthenticated origin. This experiment neither authenticates an OEM trust
root nor changes a signed image. This comparison did not produce a combined
binary. The later [helper projection](helper-policy-projection.md) adds the
exact two-SET platform restriction and passes strict compilation and an
unfiltered permissive-domain check. Reviewed adoption into the source and
vendor integration, plus separate device tests, are still required. No boot or native
feature compatibility is established by either prototype.

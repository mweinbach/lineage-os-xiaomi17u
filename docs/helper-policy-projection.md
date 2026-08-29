**Historical checkpoint — August 28, 2026.** The strict copied-CIL comparison
below predates source integration. The later native user build passed through
patched source/M4, vendor derivation and strict combined compilation; see the
[current policy integration](policy-source-integration.md) and its
[result record](../research/policy-source-integration.json). That source-build
pass does not establish complete context/Treble validation, image adoption or
hardware support. The original prototype evidence remains unchanged below.

The private helper-policy prototype now **compiles with every assertion
retained and has zero permissive domains** under the unfiltered analyzer.
Its baseline still fails at two assertion sites. This is a successful strict
comparison of derived CIL files, not an Android source build or an adopted
image. The current v9 source combined with the unchanged factory vendor
policy still has its separately recorded four failures.

The experiment starts from the [Binder correction](binder-policy-correction.md),
which removed 67 vendor allow occurrences involving service objects rather
than process domains. Both cases here use that same derived vendor file.
Only platform input index 0 changes: two complete `init_dev_config` SET
statements are replaced with spaces. They target `apexd_select_prop` and
`media_variant_prop`; no new permission is added.

One authorized checker invocation ran on August 28, 2026, from 02:50:13.788425
to 02:51:01.513784 UTC. It ran two strict compiler commands and, after the
corrected case produced a binary, one unfiltered permissive analysis. Neither
compiler case was retried.

| Observed result | Binder-corrected v9 baseline | Baseline plus helper projection |
| --- | ---: | ---: |
| Compiler exit status | 255 | 0 |
| Neverallow assertion sites reported | 2 | 0 |
| Combined policy binary | Absent | 1,515,046 bytes |
| Unfiltered permissive analyzer | Not run | Exit 0, empty stdout |
| Strict compile and zero-permissive result | Failed | Passed |

The binary SHA256 is
`a827e265ee5bd3112eb657b36cf0e20db37328d948b629f97d631d68d8104bf8`.
The generated `file_contexts` output is empty; this does not validate the
separately supplied context files. Compiler and analyzer stderr are not empty:
each retains 315 bytes of nsjail warnings about the namespace user mapping to
global root. Those warnings were not filtered or counted as policy failures.
The baseline's full 1,347-byte diagnostic output is retained separately.

Both commands use all ten inputs, in the same order, with the same pinned
compiler and `-m -M true -G -c 30` flags, without `-N`. The baseline contains
seven actual [v9 framework outputs](dsp-policy-build.md), the derived vendor
CIL, and two unchanged factory vendor/ODM inputs. The corrected case replaces
only the platform CIL with its private projection. It does not substitute a
precompiled stock policy. Each case has a fresh output directory. The expected
two-to-zero diagnostic count is not used as the success condition: success
requires exit zero, a new nonempty binary and an unfiltered analyzer returning
zero with no reported permissive domains.

Original and projected platform CIL both contain 3,012,604 bytes. Exactly 125
byte values change within 133 selected span bytes; all other bytes, line
delimiters and offsets remain unchanged. The earlier derivation used two
parsers and an independent byte prediction. Across the original v9 corpus,
the Binder correction and this helper projection, all **6,366 assertions**
remain identical: 5,976 `neverallow` and 390 `neverallowx` occurrences. Type,
role, alias, attribute and compatibility-mapping sets are unchanged. The
modeled attribute closure finds two effective helper SET grants before the
projection and none afterward.

This matches the two-grant effect of the
[optional source patch](init-helper-capability.md), including preservation of
property-file reads and socket permissions. Existing `init` and `vendor_init`
permissions, including the observed vendor media setter, remain unchanged.
The optional source patch's undefined and `true` branches retain the upstream
grants; `false` removes only those two SET grants. The source patch and its
definition have not been installed, and admission still needs a duplicate
definition guard. This compiler run did not execute Android M4, regenerate
policy from the patch, or prove a provider cannot require the removed access.

The observer recorded separate mount, network, PID and user namespaces before
each of the three commands. Root, source, all build outputs, original evidence,
inputs, tools and provenance were read-only. Only the active case's results
and private temporary directory were writable; the produced policy was also
read-only during analysis. Observed capabilities were zero. Namespace UID/GID
65534 mapped to global UID/GID 0, so this is not a claim of unprivileged host
execution. The pinned runtime bundle still depends on system libraries and is
not hermetic.

The separate admission transfer copied and verified 13 files totaling
3,275,909 bytes; it did not run the checker. The checker then reverified all
77 prior Binder bindings and recorded 129 input/output/tool bindings of its
own. The separate read-only collector rehashed those 129 bindings and checked
130 observer bindings twice, including the result receipt. All 12 raw outputs,
totaling 1,609,831 bytes, were copied and independently rehashed on the host.
That count includes the policy binary and comparison receipt; it excludes
the collector's own readback receipt. The collector did not write guest files
or invoke a compiler.

The complete comparison receipt is bound in
[the public record](../research/helper-policy-projection.json), with SHA256
`32a49f11866bd44b391ba2931a4b7ec22f79a24af000fdb150ce1d11c3e4350e`.
The readback receipt SHA256 is
`d840adba3d1e76562697b517e3865a7829592aea97aa1fd45170ecfe23f86c90`.
Raw CIL, policy binaries and logs remain private.

The factory-named China TGZ remains user-provided, with an unknown source URL
and unauthenticated origin. Internal AVB validation does not authenticate an
OEM trust root. The vendor CIL in this experiment is explicitly modified;
the original vendor image, bundle and ODM image are unchanged. Historical
builds and failures have not been reclassified as passing results.

Source integration still needs the actual Android M4 path, explicit capability
admission, complete generated-policy checks, context and Treble-labeling
validation, and review of the existing vendor media path. APEX selection,
hardware codecs and native camera behavior require separate device tests.
No complete ROM, signed image, boot, native-feature or TWRP result follows from
this policy pass. No phone access or modification occurred.

# Preserve factory property labels

The full Evolution policy introduces seven more-specific property prefixes
that override the retained factory labels. The captured policy2 inputs show
that these relabels change access: the camera entries lose existing camera
readers and a HAL writer, the USB entry loses existing vendor readers/writers,
and the Dolby entries broaden reads while changing writers. The first boot
baseline should retain the factory labels for these regions, without adding
permissions to compensate for the relabels.

The [source patch](../patches/evolution/0017-preserve-factory-property-contexts.patch)
adds `target_nezha_preserve_factory_property_labels`. Selecting literal `true`
suppresses only seven existing rows in Evolution's
`common/private/property_contexts`:

| Suppressed Evolution prefix | Retained factory type |
| --- | --- |
| `vendor.camera.aux.packageexcludelist` | `vendor_camera_prop` |
| `vendor.camera.aux.packagelist` | `vendor_camera_prop` |
| `vendor.camera.skip_unconfigure.packagelist` | `vendor_camera_prop` |
| `ro.vendor.audio.dolby.dax.support` | `vendor_audio_prop` |
| `ro.vendor.audio.dolby.dax.version` | `vendor_audio_prop` |
| `ro.vendor.audio.dolby.surround.enable` | `vendor_audio_prop` |
| `vendor.usb.uvc.payload_transfer_size` | `vendor_usb_prop` |

These are untyped prefix rows, so the scope includes longer property names
that start with each prefix. A diagnostic of all five captured property-context
inputs found no exact or deeper-prefix exceptions inside these seven regions.
That evidence describes the preimage and intended omission; the final generated
context corpus still requires verification.

All other Evolution context rows remain unchanged, including
`ro.vendor.dolby.dax.version` and `ro.usb.uvc.disable_video_encode_flag`.
The [contract](../patches/evolution/factory-property-contexts.json) binds the
source project at `37c13c9b74344c17eddd6067541e9fcba116a34e`, original and guarded
file hashes, all seven row bytes, exact factory fallbacks and the captured
five-context input set. The original file is 2,870 bytes; its guarded postimage
is 3,423 bytes. Both retain mode `100644`. Selected source-fragment output removes
540 bytes and has exactly 25 semantic rows instead of 32. With the eight owned
rows retained, the required full system_ext output is 33 rows instead of 40;
that new native output has not yet been verified by this source fixture.

An absent capability or explicit `false` keeps the original context text.
Two isolated patch applications reproduce the exact guarded file. Host GNU M4
fixtures pass 48 valid cases and 22 expected failures, covering all three build
variants, normal/recovery selectors, and both plain and `-s` output. Invalid
explicit values fail before emitting any context rows. Plain default output is
byte-identical to the original. Under `-s`, the context row bytes, comments and
order are identical after excluding synchronization directives for comparison;
the raw evidence retains the truthful, changed `#line` markers. No markers are
rewritten or presented as identical.

The host fixture processes this source fragment. It does not replay the full
native command or its generated newline inputs, run Android's M4 tool, or
validate the final merged property-info trie. The twelve
[offline tests](../tests/test_factory_property_contexts_patch.py) use public
source/metadata and Python's standard library; they execute no M4, private-input,
guest or phone operations.

Activation requires paired device/source and private-bundle admission, with
exactly one generated `true` definition and missing, duplicate, conflicting,
injected or overridden definitions rejected. The ordinary context producer and
independent Evolution reference must receive the same value. Their outputs
must preserve the other 25 base and eight owned rows and pass complete
five-context prefix analysis, native property-info/context checks and applicable
Treble checks. Strict combined policy compilation and unfiltered normal-policy
permissive analysis remain separate gates.

This patch changes no declarations, permissions, assertions, factory files or
property values. [Patch 0016](camera-property-vendor-init-write.md) remains an
independent requirement: suppressing contexts does not remove its conflicting
declaration-generated write permission. Do not copy factory system property
defaults; Camera Java fallback behavior requires its own evidence. Final label
selection, effective access, image adoption and actual camera, USB and audio
behavior remain unverified by this source change.

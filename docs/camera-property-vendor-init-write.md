# Camera property write capability

The full Evolution policy build reaches a real factory-policy assertion failure:
the shared `system_vendor_config_prop(vendor_persist_camera_prop)` invocation
grants `vendor_init` permission to set that property. The unchanged factory
`plat_pub_versioned.cil` forbids all non-core domains from setting its mapped
type, which includes `vendor_init`. The original failed result is preserved.

The [source patch](../patches/evolution/0016-gate-camera-property-vendor-init-write.patch)
adds an explicit capability for this one invocation. With
`target_vendor_persist_camera_prop_vendor_init_writes=false`, it removes only
the emitted `vendor_init` → `vendor_persist_camera_prop` `property_service:set`
permission. The existing public type declaration, two socket permissions,
property read permission and complete Evolution `neverallow` remain. The
factory assertion and original proprietary input are unchanged. NFC, USB and
xtra-daemon declarations are untouched; the shared macro is not redefined.

The [contract](../patches/evolution/camera-property-vendor-init-write.json)
pins `device/lineage/sepolicy` at
`37c13c9b74344c17eddd6067541e9fcba116a34e` on `bka`. Only
`common/public/property.te` changes, retaining mode `100644`:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| Original | 267 | `e0448d64ba284410fb5281ee3390d53aee0b3730cf6ab0f44926009d5b50d6f7` |
| Guarded | 925 | `f61da3a36e2cbea8c74284270da46dc0ba8459483eea740e5aa2818440f9e3c4` |

An absent capability or explicit `true` retains the original behavior; the host
M4 output is byte-identical in both cases. Other explicit values stop M4 with
an error before emitting property statements. M4 value validation cannot detect
an earlier value overwritten by a repeated `-D` option. Activation therefore
requires the paired device/source and private-bundle admission: exactly one
generated `false` definition, with missing, duplicate, conflicting, injected or
overridden definitions rejected. Definitions must not be sorted or deduplicated
to make them pass. The normal source and independent comparison producers must
use that same explicit value; no default profile selects it.

Two isolated host copies reproduce the patch exactly with zero fuzz. A separate
host GNU M4 1.4.6 fixture uses the complete pinned platform macro file and checks
24 valid cases: original, absent, `true` and `false` for all three build variants
in normal and recovery mode. The disabled branch retains all four property
types and all four assertions; only one of twelve allow statements is removed.
Every other ordered statement is unchanged. Eleven invalid values fail with
exit 1 and no emitted policy statements. These are host M4 results, not Android
M4 or full-policy compilation. The twelve
[offline tests](../tests/test_camera_property_vendor_init_write.py) use only
public files and Python's standard library; they do not execute M4 or access
private artifacts, the guest or a phone.

The existing Evolution/factory duplicate-type checks must still require one
declaration in each exact source, the `object_r` role and singleton `202504`
mapping. The patch neither drops the exported type nor reclassifies its
attributes or `vendor_init`. Native validation must verify the effective set
permission is absent and the original reads, sockets and both assertions
remain, then pass strict combined compilation, context and Treble checks and
unfiltered normal-policy permissive analysis. The reviewed source composition,
actual Android build and image adoption remain separate work.

Camera property labels, initialization, assignments and readers require their
own review against the final merged contexts. This source correction does not
transfer write access to another domain, prove camera behavior, or establish a
bootable ROM.

# Actual host VINTF validation

On **2026-08-27 at 19:30:27 UTC**, the built Evolution `checkvintf` passed
the supplied vendor/ODM manifest load and merge, including the **observed active
vendor APEX fragments**, and parsed the device compatibility matrix. This is a
static device-side check, not full Evolution framework compatibility, APEX
activation on Evolution, or a working DRM, Wi-Fi or camera test.

The earlier [VINTF contract](vintf-contract.md) records the captured XML and its
initial inspection limits. The new
[validation record](../research/vintf-validation.json) records actual invocations,
input and output hashes, timestamps, source pins, and remaining checks.

| Actual check | Result | What it establishes |
| --- | --- | --- |
| Built tool `--dump-file-list` | Exit 0 at 19:14:46 UTC | The host binary executes and lists its built-in partition paths; that list omits APEX inputs |
| Vendor/ODM loose partition XML | Exit 0 at 19:14:46 UTC | Selected device manifest/fragments load and merge; the device matrix parses; active APEX content was absent |
| Supplied stock framework XML | Exit 70 at 19:14:46 UTC | Framework XML loads, but retained matrices reference five HIDL definitions absent from this host binary's compiled interface metadata |
| Vendor/ODM plus observed active vendor APEX XML | Exit 0 at 19:30:27 UTC | The same device-side check also reads the unchanged active list and both CAS/Widevine fragments |

The validator is the binary built by the real `libbase checkvintf` module build,
SHA-256 `672c43b9208a2bb24d192d9fcbe12644712996c7e79a0d38ac2f36d6d65b40b0`.
Its `system/libvintf` source is pinned at
`69c456ea4aa2f503a2904cfbc11f279a3b2efb09`, within the verified
[platform snapshot](../research/source-snapshots/evolution-bka-20260827.xml).
In that implementation, the vendor branch of `--check-one` only loads the
device manifest and device matrix. It does not compare them with framework
requirements or validate the declared services' implementations.
[Pinned CLI implementation](https://android.googlesource.com/platform/system/libvintf/+/69c456ea4aa2f503a2904cfbc11f279a3b2efb09/check_vintf.cpp)

All **209 partition XML files** remain staged unchanged: vendor 141, ODM 37,
system 19, system-ext 9 and product 3, totaling 790,394 bytes. The original
staging directory also contains the 220,352-byte captured `kernel.config`.
All **210 files**, totaling 1,010,746 bytes, were rehashed before and after the
APEX-inclusive check. `--check-one` does not consume that kernel configuration.
The first new preflight stopped before staging or running the validator because
its expected file list omitted this already present configuration; that failure
log is preserved, and the corrected preflight verified every existing file.

With the observed `canoe` vendor SKU and `nezha` hardware SKU, logs show 138
unique vendor XML files and all 37 ODM fragments fetched. The unselected vendor
files are `manifest_alor.xml` and the two nested `manifest/qspa/` fragments.
Those files remain present in their original directories; they were neither
deleted nor flattened to change the outcome. The latest run additionally
fetched the APEX list and two APEX VINTF fragments: 177 XML manifest/matrix files
plus one active-info list in total.

The unchanged `/apex/apex-info-list.xml` has **39 entries**, of which exactly
three active entries belong to `VENDOR` and none to `ODM`. A separate, already
completed read-only phone capture established that all three package files
(6,348,800 bytes) and both mounted VINTF fragments match the supplied firmware.
The [APEX dependency inspection](apex-dependencies.md) records the complete
payload inventories, hashes and separate runtime gaps.

| Active module name | VINTF content included |
| --- | --- |
| `com.android.hardware.cas` | `/etc/vintf/android.hardware.cas-service.xml`, 373 bytes |
| `com.google.android.widevine` | `/etc/vintf/com.google.android.widevine.xml`, 349 bytes |
| `com.xiaomi.wifi` | No VINTF directory: the complete matching payload contains only `apex_manifest.pb` and `etc/wifi_compat.json` as regular files |

The Widevine mount uses its actual module name, without the package filename's
`.nonupdatable` suffix. The validator explicitly fetched both fragments and
reported `NAME_NOT_FOUND` for Wi-Fi's absent VINTF directory, consistent with
that complete payload inventory. The full active-info list was not filtered,
rewritten or replaced with an empty list. Host libvintf defaults APEX readiness
to true and selects active entries by their partition and module name; no
`apex.all.ready` property override was supplied.
[Pinned APEX loader](https://android.googlesource.com/platform/system/libvintf/+/69c456ea4aa2f503a2904cfbc11f279a3b2efb09/Apex.cpp)

Three attempted mounted `apex_manifest.pb` reads had previously returned
permission-denied text despite ADB transport success. Those bytes are retained
as diagnostics, not metadata, and were not staged. This validation performed no
phone reads or retries. The existing package and VINTF comparisons do not
authenticate Xiaomi's signing origin or establish Evolution activation.

Only the observed info list and two exact VINTF XML files were streamed into the
new guest directory
`/work/validation/nezha-vintf-partition-xml-20260827/apex-inputs-v1`, totaling
13,940 bytes. All three files and the validator were rehashed afterward.
The source checkout, original partition inputs and concurrently used build
output were not modified by the validator. It used the same `nsjail` arguments
as the earlier checks: root/source/inputs mounted read-only, `/tmp` writable,
writable proc, and the preset's cgroup namespace setting unchanged. Its warning
about UID/GID zero in the outer namespace remains in the log; no unprivileged
outer-user claim is made.

The actual validator arguments, inside that recorded sandbox invocation, were:

```sh
/work/out/nezha-framework-20260827T1835Z/host/linux-x86/bin/checkvintf \
  --check-one \
  --dirmap /vendor:/work/validation/nezha-vintf-partition-xml-20260827/inputs/vendor \
  --dirmap /odm:/work/validation/nezha-vintf-partition-xml-20260827/inputs/odm \
  --dirmap /apex:/work/validation/nezha-vintf-partition-xml-20260827/apex-inputs-v1 \
  --property ro.boot.product.vendor.sku=canoe \
  --property ro.boot.product.hardware.sku=nezha \
  --property ro.vendor.api_level=202504 \
  --property ro.product.first_api_level=36
```

The ignored one-off script `reports/run-vintf-apex-check.py` records the guarded
streaming, file verification and complete sandbox command. Its first-use output
paths must be new; it does not overwrite receipts. The result is preserved as
`reports/vintf-apex-check-v2.json`, SHA-256
`d11f8d0e0f5c8934b47741b1dd48481c5d438c4bee860eaacb64bffd0f4faece`, and the
matching guest receipt is under `checks-v2-apex/receipt.json`. The new staging
receipt has SHA-256
`2395b2a815a75c814527b4acae71f59104026c5d3c33efd046ed499a883407d7`.
Earlier results remain in `reports/vintf-partition-checks-v1.json`, SHA-256
`05263842f25f35752d8681d8e9954c11f6f0a0618250699fbaab946e4cb485c5`.

The stock framework failure has **11 references to five unique definitions**
across FCM levels 5–8: automotive audio-control 1.0 and 2.0, VR 1.0, and two
Dolby DMS 2.0 interface names. The JSON retains every name and matrix path.
No old matrix was removed and no check was suppressed. This reports a mismatch
between retained stock framework matrices and the interface metadata compiled
into the host validator; it is not a full Nezha runtime incompatibility result
or a comparison with generated Evolution framework matrices.

Full compatibility still needs the assembled Evolution system, system-ext,
product and relevant framework APEX inputs, followed by a separately recorded
`--check-compat` using the exact Android16 kernel release and captured config.
`--check-one` returns before kernel argument handling. Even the host tool's
default compatibility mode does not authenticate image AVB signatures, and its
static runtime provider does not measure the running kernel's SELinux policy
capability. These are separate checks, not reasons to weaken them.
[Pinned default flags](https://android.googlesource.com/platform/system/libvintf/+/69c456ea4aa2f503a2904cfbc11f279a3b2efb09/include/vintf/CheckFlags.h)

The input remains an unauthenticated, modified Xiaomi.eu package with retained
AVB failures, as documented in the [boot contract](boot-contract.md). This host
result does not change its provenance, authorize flashing, prove module ABI or
signature acceptance, or establish any native feature on Evolution.

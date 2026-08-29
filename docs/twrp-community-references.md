The two user-supplied repositories provide useful leads, but neither supplies a
fully pinned Android platform manifest and recovery source base that reproduces
its claimed Nezha build. This review adds reference metadata only. No community
image, source patch, device payload, access setting or build waiver was adopted.
The [stock contract](../research/twrp-stock-contract.json) for the user-provided
China `OS3.0.309.0.WPACNXM_16.0` package remains authoritative for image geometry;
it is not a new physical-phone test.

The [public reference record](../research/twrp-community-references.json) records
the GitHub MCP observation at `2026-08-28T17:36:10.812Z`, full commit/tree IDs,
source links and hashes of the ignored review receipts.

| Reference | Useful evidence | Limits |
| --- | --- | --- |
| [EkinStrop / JohnTheFarm3r, `7ad14e49`](https://github.com/EkinStrop/twrp_device_xiaomi_nezha/tree/7ad14e492e3ca25a63dfdb39b2fa50e0074a0910) | Declares a kernel-free v4 recovery, LZ4 ramdisk and 104857600-byte partition, agreeing with stock. | The maintainer reports testing on LineageOS; Xiaomi.eu build 308 success is attributed to users. Neither verifies our China stock 309 build. |
| [antocorvo3000, `4a35185d`](https://github.com/antocorvo3000/twrp-xiaomi-17-series/tree/4a35185d43782b4dd460a7f456d674c0976c0859) | Reports Nezha boot/touch/ADB and supplies touch, USB and firmware-path leads. | The checked-in Nezha tree still identifies `xiaomi_sm8750` / `sun` / `sm8750_thales`, moves recovery into `vendor_boot`, and names Popsicle donor inputs. Decryption is unconfirmed, and returned release metadata contains no Nezha asset. These inconsistencies do not disprove an unpublished working binary. |

The Anto DTB metadata is 4511274 bytes versus 4496880 in our stock vendor_boot.
Matching kernel length alone does not establish byte identity or compatibility.
Neither donor geometry nor community binaries replace the stock boot, vendor_boot
or DTBO inputs. Both trees' brightness values differ from the stock panel maximum
16383 and stock recovery initial value 200; their values and pixel formats need
separate hardware validation.

Both USB files contain the same controller sequence, and stock independently
corroborates `a600000.dwc3`, the `a600000.ssusb` mode-path fallback and UDC path.
That supports a later, isolated transport change, not successful enumeration or
whole-file adoption. The stock touch drivers `synaptics_tcm2.ko` and
`xiaomi_touch.ko` have a declared 13-module dependency closure. Community
`hbtp_vm` blacklisting remains an input-device lead, not a validated touch fix.
Use exact stock signed modules, dependency order and firmware if that work is
later authorized. Anto's logd init file matches our pinned upstream source, but
neither reference proves nonroot access to recovery logs or fixes the collector's
process-identity checks.

Both references request `ro.adb.secure=0`; Ekin additionally configures TCP port
5555 and an `eng` build. Both include writable persistent-mount startup actions.
Ekin skips missing-dependency and ABI checks and enables duplicate-rule, ELF-copy
and plugin exceptions; Anto also permits missing dependencies. Those choices
are not imported. Authenticated USB ADB, SELinux enforcement, signature/ELF/image
checks and stock rollback constraints remain required. Ekin's permissive kernel
argument may not enter a kernel-free recovery, while generic vbmeta flags 3 do
not prove the flags on a generated recovery footer. Neither test keys, future
2099 security-patch values nor a release label establish OEM trust.

Nine Ekin patches were checked against recovery
`b70f8e998b302381ecefc6e7f46df1614bd61afc` and vold
`4c83041ec61f9b482085685f1e6aed5a62f103aa` in ignored host fixtures. Only
`0002-recovery-report-super-partition-size` applies unchanged and reverses to
identical bytes and modes; it remains unadmitted. The GCM/empty-credential patch
addresses patterns still present in our vold, but needs rebasing and
cryptographic test vectors before any future FBE adoption. Its existing final
hunk fails on our baseline. The battery patch targets an older Make compilation
path, and WLAN patches require separate adaptation. None is a current strict
graph fix. Independent failures do not assess the complete historical patch
chain.

Preserve antocorvo3000 and EkinStrop/JohnTheFarm3r credit in any later adaptation.
Ekin's README declares Apache 2.0, although its captured tree has no LICENSE file.
Public availability or a repository license declaration does not establish
proprietary-payload provenance or redistribution permission. This record contains
only factual metadata and links: no raw community sources, binaries, keys or
stock dumps. Its standard-library tests require only tracked public records,
not ignored reports, network access or a phone.

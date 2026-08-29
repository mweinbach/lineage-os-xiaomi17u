# TWRP for Nezha

**TWRP is the selected default recovery for Evolution X on the Xiaomi 17 Ultra.**
The current baseline is `working76`, a device-tested adaptation of the supplied
`fix22ZJ-touchfix18` recovery. It is not a newly compiled TWRP runtime, an
Evolution X ROM, or proof of ROM installation and OTA compatibility.

The [working-defaults record](../research/twrp-working-defaults.json) binds the
image, two text changes, signature checks and device observations. The
[recovery plan](recovery-plan.md) covers the remaining integration gates;
[bring-up history](twrp-bringup-history.md) retains the earlier source builds,
failed temporary boots and original review without changing their evidence.

## Tested baseline

Both images are 104,857,600 bytes (100 MiB), with a kernel-free Android boot
header v4. Preserve the original input as well as the installed derivative.

| Image | SHA-256 |
| --- | --- |
| Supplied `provided75` / `fix22ZJ-touchfix18` | `56029c8109e3ff1bcbb69ef38e8ae36355713340482d9f77405cdf6009bcd323` |
| Tested `working76` derivative | `a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e` |

The 2026-08-29 test used the selected `nezha` / `2512BPNDAG` phone with the
recorded `OS3.0.309.0.WPACNXM` China firmware inputs. Its physical sales region
is not established by the model name alone. The separately authorized flash
wrote only `recovery_a`; its readback matched working76 and the slot stayed `a`.

| Verified on that boot | Evidence and boundary |
| --- | --- |
| Recovery startup | `3.7.1_16-Xiaomi_17_Ultra`, running recovery service and `sys.boot_completed=1` |
| Display and touch | User confirmed that the fresh boot showed the UI and felt fast; no timed latency benchmark |
| USB diagnostics | Root ADB, UID 0, and private recovery/kernel log captures; host authentication is not established |
| Startup defaults | Global `Permissive` and all three vibration values zero, with no post-boot setting commands |

See [private recovery diagnostics](recovery-logs.md) for bounded collection and
its trust limits. Root USB access is not evidence of authenticated ADB or a
secure recovery environment.

## The two configuration changes

The [reviewed patch](../recovery/twrp-working/README.md) changes only:

- `system/etc/init/hw/init.rc`: the existing early-init action writes `0` to
  `/sys/fs/selinux/enforce`, making this recovery permissive without disabling
  SELinux in the kernel.
- `twres/ui.xml`: ordinary theme defaults set `tw_action_vibrate`,
  `tw_button_vibrate` and `tw_keyboard_vibrate` to `0`. Saved TWRP settings may
  override these defaults; the fix does not force settings on every page.

All other 4,208 CPIO members retain their payloads and metadata, including
executables, libraries, drivers, firmware and the policy file. The header is
unchanged except for the compressed ramdisk size. This preserves the tested
runtime; it does not establish source provenance or patch coverage of the
supplied binaries.

The original [installation record](../research/twrp-installed-recovery.json)
preserves the initial 5–10 second touch delay, partial improvement from global
permissive mode, and the much faster response after vibration was disabled.
The fresh working76 confirmation is recorded separately. The restarting
vibrator/touch services were not stopped, and no input driver was changed;
the precise cause of the delay is not proven.

## Rebuild and verify locally

The [working profile](../config/twrp-working.json) and
[host-side helper](../scripts/twrp_working.py) admit the exact baseline, patch,
archive identities and installed working76 image hash. Equivalent-looking
content is not enough. A future image needs an explicit reviewed profile
change and its own device test.

The plan performs no subprocess or device operation:

```sh
python3 scripts/twrp_working.py plan
```

The older full-source experiment remains available through
`make twrp-source-plan`. Its [archived workflow](twrp-bringup-history.md#local-workflow)
uses separate Linux source/output paths and does not produce the current
prebuilt adaptation by default.

To rebuild, supply the exact private baseline, the approved signing key and
explicit native tool paths. Use a fresh output directory under an ignored
artifact tree; existing directories are never reused or overwritten.

```sh
python3 scripts/twrp_working.py build \
  --baseline-image "${TWRP_BASELINE_IMAGE:?set the exact provided75 image path}" \
  --key "${TWRP_SIGNING_KEY:?set the approved private key path}" \
  --mkbootimg "${TWRP_MKBOOTIMG:?set the reviewed mkbootimg path}" \
  --avbtool "${TWRP_AVBTOOL:?set the reviewed avbtool path}" \
  --lz4 "${TWRP_LZ4:?set the reviewed lz4 path}" \
  --openssl "${TWRP_OPENSSL:?set the reviewed OpenSSL path}" \
  --output-dir "${TWRP_OUTPUT_DIR:?set a new ignored artifact directory}"

python3 scripts/twrp_working.py verify \
  --image "${TWRP_IMAGE:?set the exact working76 image path}" \
  --avbtool "${TWRP_AVBTOOL:?set the reviewed avbtool path}" \
  --public-key "${TWRP_PUBLIC_KEY:?set the PEM public key path}" \
  --openssl "${TWRP_OPENSSL:?set the reviewed OpenSSL path}"
```

Build emits `recovery.img`, `build-report.json`, `verification-report.json` and
`SHA256SUMS`, with private intermediate files, in a `0700` directory using
`0600` files. The independent verify command prints a JSON report; it does not
create a receipt file. Its public-key input is PEM, not an AVB binary key blob
or a private key. Keep images, key material, native outputs and raw reports
private and ignored. None of these commands flashes or boots a phone.

## Stage the Evolution X recovery input

The separate [input-staging helper](../scripts/recovery_inputs.py) verifies the
exact working76 image before creating a private bundle. The selected Evolution
source tree must already contain the [reviewed prebuilt-recovery build change](../patches/evolution/prebuilt-recovery.json);
staging refuses an unprepared tree. It does not apply a source patch, build a
ROM or flash a device.

On a fresh source checkout, first generate the current authored device tree
with its [documented private inputs](../device/xiaomi/nezha/README.md). The
recovery include is part of that generator's template set. Apply the reviewed
patch only to a clean `build/make` at its recorded commit:

```sh
(
  set -eu
  test "$(git -C "${EVOLUTION_SOURCE_TREE:?}/build/make" rev-parse HEAD)" = \
    a438ca40c6ed779042f806142b1165ba1360a7b2
  nezha_build_status="$(git -C "${EVOLUTION_SOURCE_TREE:?}/build/make" status --porcelain)"
  test -z "$nezha_build_status"
  git -C "${EVOLUTION_SOURCE_TREE:?}/build/make" apply --check \
    "${NEZHA_WORKSPACE:?set the bring-up workspace path}/patches/evolution/0005-verified-prebuilt-recovery.patch"
  git -C "${EVOLUTION_SOURCE_TREE:?}/build/make" apply \
    "${NEZHA_WORKSPACE:?}/patches/evolution/0005-verified-prebuilt-recovery.patch"
)
```

This is a preparation step, not something to repeat before every build. An
already prepared tree is checked by `recovery_inputs.py verify`; an unexpected
patch or different source revision must be reviewed, not reset to make the
command pass. The staging helper also checks the exact patched file hash and
pinned releasetools bytes, so merely applying a similarly named patch is not
enough.

```sh
python3 scripts/recovery_inputs.py plan
python3 scripts/recovery_inputs.py stage \
  --source-tree "${EVOLUTION_SOURCE_TREE:?set the verified Evolution source path}" \
  --image "${TWRP_IMAGE:?set the exact working76 image path}" \
  --output-dir "${RECOVERY_INPUT_BUNDLE:?set a new vendor/xiaomi/nezha-recovery path}" \
  --avbtool "${TWRP_AVBTOOL:?set the reviewed avbtool path}" \
  --public-key "${TWRP_PUBLIC_KEY:?set the PEM public key path}" \
  --openssl "${TWRP_OPENSSL:?set the reviewed OpenSSL path}"
python3 scripts/recovery_inputs.py verify \
  --source-tree "${EVOLUTION_SOURCE_TREE:?set the verified Evolution source path}" \
  --bundle "${RECOVERY_INPUT_BUNDLE:?set the existing private recovery bundle path}" \
  --avbtool "${TWRP_AVBTOOL:?set the reviewed avbtool path}" \
  --public-key "${TWRP_PUBLIC_KEY:?set the PEM public key path}" \
  --openssl "${TWRP_OPENSSL:?set the reviewed OpenSSL path}"
```

The bundle path must end in `vendor/xiaomi/nezha-recovery`. Stage creates it
exclusively with `0700` directory permissions and `0600` files: `recovery.img`,
`recovery-public.pem`, `receipt.json` and `recovery-inputs.mk`. The schema-2
bundle binds the public PEM bytes to the native verification result. The
device include selects that public key for the recovery chain, with
`SHA256_RSA4096`, rollback index `1` and location `1`; it must not retain the
generic engineering test key for this image. The private signing key never
enters the source tree or VM.

Staging never overwrites or deletes an older bundle. Preserve any schema-1
bundle outside the selected source path, then stage a fresh schema-2 bundle;
do not edit the receipt or makefile to pretend the older bundle is current.
The approved core copy preserves the image bytes and AVB footer. This admits
a recovery input, not a complete ROM,
super image or OTA: compatibility with newly built Evolution X boot-chain
companions still needs separate validation.

The pinned target-files tooling also requires a separately validated
`recovery-two-step.img`. The selected prebuilt rule does not supply that image
or a generated `RECOVERY` filesystem. Full target-files and OTA packaging stay
blocked until that workflow and the complete signed boot chain are validated.

After host/source checks and bundle verification, the explicit Android build
target is `recoveryimage`. In the verified Apple Container/Rosetta environment,
run this inside the sole VM that owns the source volume:

```sh
(
  set -eu
  cd "${EVOLUTION_SOURCE_TREE:?}"
  env PATH="$PWD/prebuilts/build-tools/path/linux-x86:$PATH" \
    OUT_DIR="${NEZHA_OUT_DIR:?set the reviewed relative output directory}" \
    TARGET_PRODUCT=lineage_nezha TARGET_RELEASE=bp4a TARGET_BUILD_VARIANT=user \
    GOTOOLCHAIN=local GOENV=off GOPROXY=off GOSUMDB=off \
    build/soong/soong_ui.bash --make-mode -j8 recoveryimage
)
```

Use the existing reviewed user output for an incremental build, or a new
separate output directory for a fresh graph. Do not mix user and userdebug
outputs. Verify the resulting `target/product/nezha/recovery.img` with the
public-key command above before treating it as a valid artifact. A bare `m`
and full-ROM aliases remain refused; choosing recovery does not waive the
other product admission checks.

At the **2026-08-29 validation checkpoint**, two fresh Mac rebuilds produced
working76 byte for byte. Linux staging and public-key verification passed,
then the actual `lineage_nezha-bp4a-user` recovery target produced the same
image twice. The first run took 641.289 seconds while regenerating the Android
build graph; the repeat took 25.430 seconds and performed the checked copy
again. The existing companion image outputs were unchanged, and native AVB
verification of the final output passed. The [integration record](../research/workspace-integration.json)
binds the code, source audit, bundle, logs and image hashes. No phone operation
or full ROM build was part of this check.

## Safety and remaining work

The tested derivative uses a local development-key AVB signature with
`SHA256_RSA4096`, flags `0`, recovery rollback index `1` and location `1`.
Signature and descriptor verification passed; OEM trust is not established.
The supplied input's unsigned AVB footer and mismatched hash were disclosed
before its separate installation. Do not silently bypass verification,
change rollback roles, or treat local signing as authorization to relock.

Permissive recovery is an explicit bring-up choice. Its unchanged policy also
contains eight permissive domains. Normal Android must remain enforcing;
these are recovery-only changes, and an Android round trip after installation
has not been tested. Enforcement restoration remains a separate milestone.

No device action follows from choosing a default or building/staging an image.
Reboot, flash, unlock/relock, wipe and slot changes require an explicit user
request and fresh selection of the authorized physical device. Do not copy
another phone's partition layout or use the earlier `fastboot boot` experiments
as installation instructions for this kernel-free recovery.

Data decryption, backup/restore coverage, another persistence reboot, an Android
round trip, Evolution X installation, target-files/OTA behavior and slot/snapshot
handling remain unverified. Magisk has not been installed. TWRP cannot protect
against bootloader corruption or missing required boot-chain components.

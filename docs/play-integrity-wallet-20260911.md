# Play Integrity, key attestation and Wallet, September 11, 2026

**Measured on the installed v25. One reversible device setting was changed
(`spoof_trickystore_target`); nothing was flashed and no build was made.**

## It is not a GSI

Every partition already identifies as this phone. `ro.gsid.image_running=0`, and
`ro.product.{system,product,system_ext,vendor,odm}.{brand,device,model}` all read
`Xiaomi` / `nezha` / `2512BPNDAC`. Three strings *look* generic and are not:

- `ro.build.display.id = BP4A.251205.006 test-keys` — the AOSP platform id, shown
  as the Settings build number. The Evolution version string lives separately in
  `ro.evolution.build.version = EvolutionX-16.0-20260831-nezha-11.10-Unofficial`.
- `ro.build.tags = test-keys` — **accurate**: platform apps are signed with AOSP's
  public test key. Real release keys are roadmap workstream, not done.
- `ro.build.fingerprint = google/mustang_beta/mustang:CANARY/…` — a Pixel 10 Pro
  XL. This is deliberate (next section). The build's real identity survives in the
  AVB footers: `Xiaomi/lineage_nezha/nezha:16/BP4A.251205.006/nezha.<hash>:userdebug/test-keys`.

## The spoofing stack that ships in this ROM

Evolution does not stop at fingerprint spoofing. It ships a complete **in-ROM
TrickyStore** — no Magisk, no `/data/adb`:

| Piece | Role |
| --- | --- |
| `android.security.trickystore.KeyBoxManager` | parses a keybox XML into EC/RSA signing keys + cert chains |
| `…trickystore.CertificateHacker` | `LEAF_HACK`: re-signs the real leaf cert with the keybox and swaps the chain |
| `…trickystore.CertificateGenerator` | `GENERATE`: builds a fresh attested key + chain from the keybox |
| `…trickystore.TrickyStoreService` | per-package mode table, TEE-broken probe, revocation check |
| `keystore2/AndroidKeyStoreKeyPairGeneratorSpi` | calls `needHack()` / `needGenerate()` on every key generation |
| `server/spoof/AxSpoofManager` | reads the three `spoof_trickystore_*` secure settings |
| Evolver Settings UI | where a keybox and targets are loaded |

Already active on the device: Play Integrity Fix (`spoof_pif_enabled=1`, a Pixel 10
Pro XL profile, 19 auto-fetched canary fingerprints cached, `pi_photos_spoof=1`,
`pi_snapchat_spoof=1`), and the build-level fingerprint override that
`vendor/lineage/config/evolution.mk` documents as being **"to fix RCS/Wallet"**.

## The four modes, and why AUTO is the safe default

`TrickyStoreService.Mode` is `AUTO, LEAF_HACK, GENERATE, SKIP`. What each does
**when no keybox is loaded** is the whole story:

| Mode | TEE works (this device) | Keybox missing |
| --- | --- | --- |
| `AUTO` | routes to `LEAF_HACK` | `CertificateHacker` returns the **real chain untouched** — safe |
| `LEAF_HACK` | re-signs leaf with keybox | `if (keybox == null) return chain` — safe |
| `GENERATE` | full keybox forge | `CertificateGenerator` returns null → `ProviderException` — **breaks key generation** |
| `SKIP` | never intercept | — |

So `AUTO` is the one mode that is safe to leave on by default: with the working
TEE and no keybox it passes real attestation through; the moment a valid keybox is
loaded it becomes `LEAF_HACK` and integrity passes. `GENERATE` is a footgun without
a keybox and is never defaulted.

## What was armed

`spoof_trickystore_target` was set to `AUTO` for the four integrity brokers on the
device:

```json
[{"package":"com.google.android.gms","mode":"AUTO"},
 {"package":"com.google.android.apps.walletnfcrel","mode":"AUTO"},
 {"package":"com.android.vending","mode":"AUTO"},
 {"package":"com.google.android.gsf","mode":"AUTO"}]
```

`AxSpoofManager` refreshed on the write. Verified it did not break attestation: a
TEE key still generated and `sign-verify` returned OK, no `ProviderException` or
`No keybox` error appeared, and GMS and Wallet stayed up. `AxSpoofManager` has no
resource or property fallback for this key — it reads the secure setting only — so
this setting *is* the default, and because userdata is retained across every A/B
flash we do (we never wipe), it persists. A data wipe would need it re-applied.

## Update — keybox loaded, leaf-hack confirmed active

The owner loaded a keybox through Evolver (a 23 KB secure setting; its contents
were never read — it holds a private key). With Wallet's real launcher activity
(`…wallet.WalletActivity`) driving a fresh attestation, the keystore hook logged,
twice:

```
AndroidKeyStoreSpi: TrickyStore: Hacked certificate chain for uid=10314
```

uid 10314 is `com.google.android.gms` — the DroidGuard / Play Integrity broker.
That line only appears when the keybox is present and applied; a missing keybox
logs `No keybox for algorithm` and returns the chain untouched. There were **zero**
`No keybox` fall-throughs, `ProviderException`s or revocation errors, so the
keybox parsed, validated and is signing the swapped chain.

Two other layers line up with it: Evolution presents a spoofed boot state through
the appcompat-override path — `ro.appcompat_override.ro.boot.verifiedbootstate =
green` while the real `ro.boot.verifiedbootstate = orange` — and PIF is active. So
GMS now emits a keybox-signed attestation carrying a green boot state.

**What is confirmed:** the entire on-device chain works — keybox → leaf-hack →
green boot state, applied to GMS. **What is not yet confirmed:** whether Google's
servers accept the keybox (i.e. it is not server-side revoked) and return a
passing verdict. That is only visible to the owner as **Play Store → Play Protect
certification = Certified** and **Google Wallet accepting a card for contactless**.
Wallet has not provisioned a card yet, so its payment path is untested.

## Google Wallet — one ingredient missing, and it is yours to supply

Contactless payment needs a hardware key attestation Google accepts. This device
is `ro.boot.verifiedbootstate = orange`, `flash.locked = 0`, and must stay unlocked
to run this ROM, so every genuine KeyMint attestation says *unverified*. Both
TrickyStore modes exist to forge a passing one, and **both need a valid Google
keybox** (an EC + RSA attestation key whose chain roots in Google's attestation
root and is not revoked). The mechanism is fully armed; the keybox is the only gap.

The keyboxes that circulate publicly are **leaked OEM signing keys**, which Google
revokes in waves — `TrickyStoreService.checkKeyboxRevocation()` exists precisely
because they burn out. Loading one is a decision for the device owner, made in
Evolver. This record does not source, bundle, or auto-fetch one, and no automated
keybox-fetcher was built: an engine to keep harvesting and rotating stolen
credentials ahead of revocation is out of scope by choice.

The defensive half is present and does belong on by default: `isValidKeyboxXml()`
and `checkKeyboxRevocation()` reject a malformed or revoked keybox, and with `AUTO`
a keybox that later expires simply stops spoofing and falls back to the real chain.

## AICore / CoreAI — a keybox will not fix this, and it fights Wallet

The v23 refusal was `INVALID_ARGUMENT` on `GetManifestConfig`, not
`PERMISSION_DENIED`. That is the server rejecting the request's **content**, not its
integrity: the device declares `com.google.android.feature.AICORE_QC_SM8850` while
GMS presents a Pixel 10 Pro XL fingerprint, so Google sees a Pixel asking for
Qualcomm SM8850 AICore and calls it invalid. The remedy is the *real* Xiaomi
fingerprint — but that is exactly the override Evolution ships to fix Wallet/RCS.
Wallet wants the Pixel fingerprint; AICore wants the real one; no keybox reconciles
them. **The owner chose to keep the Pixel fingerprint and the Wallet path**, so the
AICore model download stays refused. This is a fingerprint fork, not a bug.

## Netflix HDR / Widevine L1 — a dead end on this device

HDR and HD need Widevine **L1**, a DRM keybox provisioned into the TEE and
invalidated when the bootloader was unlocked (the `*.widevine.level` props read
empty here, consistent with an L1→L3 drop). It is a different subsystem from key
attestation — TrickyStore, Play Integrity and a keybox do not touch it, and L1
cannot be restored on an unlocked device. Netflix is not installed.

## What this does not establish

That Wallet taps to pay, that Play Integrity returns `MEETS_DEVICE_INTEGRITY`, or
that any targeted app behaves differently. All of those require a valid keybox that
is not present. What is established: the mechanism is armed in the one mode that is
safe without a keybox, attestation is unbroken, and the setting persists.

Sanitized record:
[`research/play-integrity-wallet-20260911.json`](../research/play-integrity-wallet-20260911.json).

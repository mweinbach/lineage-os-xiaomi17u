# V23 installation and validation, September 11, 2026

Installed on slot A. `nezha.2fa2ea3549a2fc869a4c79df`, source revision 25,
userdebug, eight images written and reverified, boot to
`sys.boot_completed` in **25.6 s**, SELinux **Enforcing**, root ADB, no fatal
crash, userdata retained (2 accounts, 23 third-party packages).

V23 is v22 plus one thing: the AICore feature declaration from this phone's own
global firmware. Everything else — Now Playing, Leica Essential, the recorder
fix, the camcorder profiles, CameraOpt, the dim level — is carried unchanged and
was re-observed after the boot.

## What the declaration did

Before, this build declared 24 `com.google.android.feature.*` entries and not
one AICore feature, and Play answered *"Your device isn't compatible with this
version."* After:

```
$ pm list features | grep -i aicore
feature:com.google.android.feature.AICORE_QC
feature:com.google.android.feature.AICORE_QC_SM8850
```

Play's button changed to **Update**, and it delivered the real thing: 336 MB,
`versionCode=513248`,
`versionName=0.thirdpartyexperimental.qc.ffdf_aicore_20260820.00_RC09.974378940`,
four splits, replacing the 21 KB OEM stub the fragment ships. It runs.

Its native payload is the Qualcomm one, and it carries the skeleton for this
exact NPU alongside the others:

```
libQnnHtpV73Skel.so  libQnnHtpV75Skel.so  libQnnHtpV79Skel.so
libQnnHtpV81Skel.so  libQnnHtpV85Skel.so      <- V81 is this SoC
libQnnHtp.so  libQnnSystem.so  libLiteRt.so  libLiteRtDispatch_Qualcomm.so
```

So the build-side finding from
[the availability record](gemini-nano-20260911.md) held: the gate was a missing
system-feature declaration, not the silicon, and Google does build AICore for
this chip.

## Where it stops

No model. The app's data directory holds 44 KB and its MDD file-group list is
empty, because no file group is ever registered. Every attempt ends at the same
server call:

```
I ProtectedDownloadGrpcBindableService: Starting GetManifestConfig request
I ProtectedDownloadProcessorImpl: generating new key set for a new client persistent state
I servicemanager: Caller(pid=1191,uid=1017,sid=u:r:keystore:s0) Found
    android.hardware.security.keymint.IRemotelyProvisionedComponent/default
I ProtectedDownloadProcessorImpl: downloading manifest with public key hash ...
E ProtectedDownloadGrpcBindableService: Failed to handle GetManifestConfig
E ProtectedDownloadGrpcBindableService: mer: INVALID_ARGUMENT: Request contains an invalid argument.
W gvo: lop: Failed to fetch manifest config from source for com.google.android.aicore:...
```

The weights travel over Google's *protected* download route, which is gated on
device attestation, and the keymint call immediately before the request is that
gate being consulted. This phone reports:

```
ro.boot.verifiedbootstate = orange
ro.boot.flash.locked      = 0
ro.boot.vbmeta.device_state = unlocked
```

It has to stay unlocked to run this build, so that gate cannot be satisfied here.

Two things were tried and did not change the answer. The user accepted AICore's
**Developer Preview** consent on the phone (`pref_user_opted_in_for_preview` is
true). And three Phenotype flags were flipped for one run —
`AicModels__protected_download_v2_enabled=false`,
`AicModels__protected_download_v1_enabled=true`,
`AicCommon__allow_dev_preview_access=true` — producing an identical failure;
all three were restored.

## What this does not prove

That any Gemini Nano feature runs. There is no model on the device, so nothing
downstream of the runtime has been exercised. Whether a locked bootloader would
change the server's answer is untested, and untestable on this phone.

Sanitized record:
[`research/v23-install-validation-20260911.json`](../research/v23-install-validation-20260911.json).
The AICore source change is described in
[AICore from the global firmware](aicore-global-20260911.md).

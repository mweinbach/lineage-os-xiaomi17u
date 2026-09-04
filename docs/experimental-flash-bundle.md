# Private experimental image bundle

`scripts/experimental_flash_bundle.py` packages already reviewed image bytes for
an eventual authorized first boot. **Successful assembly is not flash readiness
or authorization.** It does not discover or contact a phone, run subprocesses,
access keys, regenerate images, or change workspace readiness records.

The input is a reviewed delivery plan and its SHA256 supplied independently.
The assembler accepts the `nezha` / `canoe` / SM8850, `bka` / `bp4a`, 4 KiB,
enforcing-Android route only. All device preflight fields must remain present
and pending. This tool cannot admit a device or a write sequence.

The current route has eight payloads: `boot.img`, `dtbo.img`, `init_boot.img`,
`recovery.img`, `vbmeta.img`, `vbmeta_system.img`, `vendor_boot.img`, and the
previously validated sparse `super.img`. Supply the local Super path explicitly
after its separate transfer. No actual image identities are hardcoded, so a
corrected image set requires a new reviewed plan and independently pinned hash.
Do not assemble an obsolete candidate merely because its hashes still match.

**Super is shared and unslotted, with logical A populated and logical B empty.**
Writing it removes the existing logical fallback, including B. Leaving B's
physical boot images unchanged does not preserve a bootable stock B system.
The seven physical images are A candidates for this route. `countrycode` and
`pvmfw` remain existing-firmware requirements; their images are reference-only
and are never copied into the bundle. An inactive-slot-preserving installation
requires a different reviewed route and cannot substitute this Super image.

Create the parent `artifacts/flash/nezha` directory beforehand. Use absolute paths
without symbolic links or traversal components and select a new child directory:

```text
python3 scripts/experimental_flash_bundle.py assemble \
  --plan /absolute/path/to/reviewed-delivery-plan.json \
  --expected-plan-sha256 <independently-reviewed-plan-sha256> \
  --super /absolute/path/to/transferred-super.img \
  --output /Users/mweinbach/Projects/lineage-os-xiaomi17u/artifacts/flash/nezha/new-candidate
```

The assembler opens regular, singly linked inputs, rejects reused source inodes,
copies them exclusively, hashes the source bytes and rereads every copy. Held
descriptors detect changes to earlier inputs or outputs during a later large
copy. It writes `README.md`, `SHA256SUMS`, and a portable `manifest.json` with
relative payload paths. The manifest preserves pending device gates and records
prior AVB and LP evidence as **not reverified**. Original source images and the
reviewed plan are left unchanged. No stock-return artifacts or public key are
copied; they remain separately reviewed inputs to eventual device admission.

The command prints the manifest SHA256. Retain that digest independently of the
bundle. After transferring the directory, verify it with the maintained tool:

```text
python3 scripts/experimental_flash_bundle.py verify \
  --bundle /absolute/path/to/received-candidate \
  --expected-manifest-sha256 <independently-retained-manifest-sha256>
```

Verification rehashes all eight images and rejects missing, extra, aliased or
changed files, altered supporting text, unsafe paths, and readiness promotion.
It works outside the workspace because payload paths are relative. An ordinary
`SHA256SUMS` check alone does not authenticate a substituted manifest.

Existing output directories are never reused. A copy failure preserves partial
files and writes `INCOMPLETE.json` when storage permits; it does not publish a
success manifest.
Interrupted or incomplete output is unusable and cannot pass verification. Keep
it for investigation and choose a different fresh output for a later attempt.

These checks establish byte identities only. Device variant, current slots,
partition capacity, snapshot state, AVB key acceptance and rollback counters,
off-device backups, recovery/stock-return procedures and data/encryption handling
still require separate admission. The bundle is neither an OTA nor a TWRP
installer. It supplies no phone commands, automatic formatting, slot activation,
reboot, relock, or verification/rollback bypass.

Offline tests use tiny inert files, not Android images:

```text
python3 -m unittest tests.test_experimental_flash_bundle -v
python3 -m unittest discover -s tests -v
```

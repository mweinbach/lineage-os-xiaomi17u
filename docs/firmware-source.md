# Official firmware source and acquisition status

Verified on **2026-08-27**: the exact China build
`OS3.0.309.0.WPACNXM` for `nezha` is available from Xiaomi's HTTPS CDN.
**A complete official package has not been downloaded or accepted by the intake
tool.** Transfers were stopped at explicit time limits after measuring rates
that would require days. No download remains running in the background.

## Why this build

The [connected phone baseline](device-baseline.md), also recorded in
[`research/device-baseline.json`](../research/device-baseline.json), reports
`nezha`, hardware country `CN`, and system/vendor incremental
`OS3.0.309.0.WPACNXM`. The installation is **xiaomi.eu**, not pristine Xiaomi
firmware. Its global-looking product/model strings must not select a global
package for this China hardware.

The private camera APK and other observations collected from that installation
are a **xiaomi.eu application snapshot**. They remain distinct from official
China firmware and must not be relabeled as official stock extraction. Matching
the reported incremental establishes a research baseline, not proof that the
modified installation and official package have identical binaries.

## Primary artifact URLs

The following URLs were checked directly with HTTPS certificate verification,
without following redirects. All returned `HTTP/1.1 200 OK` to HEAD and advertised
`Accept-Ranges: bytes`. The download links were discovered through the
[EzBox index](https://mirom.ezbox.idv.tw/en/phone/nezha/); that third-party page was
used for URL discovery, not as a firmware mirror or authenticity authority.

| Package | Primary source | Exact HEAD Content-Length |
| --- | --- | --- |
| China fastboot, Android 16 | [Xiaomi bigota fastboot package](https://bigota.d.miui.com/OS3.0.309.0.WPACNXM/nezha_images_OS3.0.309.0.WPACNXM_20260714.0000.00_16.0_cn_1081d3072b.tgz) | 12,778,943,953 bytes |
| Same fastboot filename on a second official CDN | [Xiaomi hugeota fastboot package](https://hugeota.d.miui.com/OS3.0.309.0.WPACNXM/nezha_images_OS3.0.309.0.WPACNXM_20260714.0000.00_16.0_cn_1081d3072b.tgz) | 12,778,943,953 bytes |
| China full recovery/OTA, Android 16 | [Xiaomi bigota full recovery package](https://bigota.d.miui.com/OS3.0.309.0.WPACNXM/nezha-ota_full-OS3.0.309.0.WPACNXM-user-16.0-e50c8b894f.zip) | 10,169,043,993 bytes |

Both fastboot hosts returned ETag
`"61E4AC0B8B51720F3A9DD58C82EB93F0-400"` and Last-Modified
`Wed, 05 Aug 2026 09:52:52 GMT`. The recovery package returned ETag
`"F6CB37A860A00FF7789239486D87BF0B-400"` and Last-Modified
`Thu, 23 Jul 2026 13:50:47 GMT`.

These ETags identify the served objects for conditional requests; they are not
claimed to be MD5 or SHA256 checksums. No vendor-published SHA256 was obtained.
Package names, HTTP metadata, and transfer checks do not validate firmware
signatures, archive contents, restore safety, or Evolution X compatibility.

## Bounded transfer results

The host had **808.81 GiB free** before the first attempt, enough for either
package and the separate intake copy. Disk was not the limiting factor.

| Attempt | Time bound | Bytes retained | Measured rate | Approximate full download at that rate |
| --- | --- | --- | --- | --- |
| bigota fastboot, initial resumable transfer | 40 seconds | 1,257,096 | 31,423 bytes/s | 113 hours |
| bigota recovery, first 32 MiB range probe | 20 seconds | 726,064 | 36,293 bytes/s | 78 hours |
| hugeota fastboot, first 32 MiB range probe | 20 seconds | 743,443 | 37,171 bytes/s | 95.5 hours |

The two range probes returned `206 Partial Content`, the requested byte range,
the exact full object size above, and the expected ETag. They were still
incomplete when their time limits expired. All three curl processes exited
with code `28` at their configured limits. The rate estimates greatly exceed the
15-minute acquisition bound, so no full transfer was continued.

The original resumable partial is stored only at:

```text
artifacts/downloads/nezha_images_OS3.0.309.0.WPACNXM_20260714.0000.00_16.0_cn_1081d3072b.tgz.part
```

Its size is **1,257,096 bytes**. Its SHA256 is
`e5d5cca2d082ba3c817bb8afc382c8158c499b4b976f72b774367e3fff814f2d`.
**This hash describes only the incomplete partial file, not the official
firmware package.** Its initial bytes match the gzip header, which is not an
archive validation.

Adjacent `.download.json`, `.attempts.jsonl`, and `.partial.json` files record
the URL, response identity, exact byte count, checksum, and stop reason. The two
small probes and their response records are under
`artifacts/downloads/probes/`. These paths are ignored by Git. No complete file
with the `.tgz` basename was created, no partial was passed to
`scripts/firmware.py`, and nothing was extracted or executed.

## Resume and acceptance requirements

When a suitable network path is available, keep the partial as evidence and
resume only after a fresh HEAD confirms the same HTTPS URL, Content-Length, and
ETag. If the remote object differs, do not append bytes to this file. Start a
separate explicitly identified download and preserve the old partial.

Use a bounded foreground transfer with curl's `--continue-at -`, `--fail`,
`--proto '=https'`, and an `If-Match` header containing the recorded ETag. Keep
the `.part` suffix until the transfer has completed successfully and the file
has exactly **12,778,943,953 bytes**. Recheck disk space and measure the new
rate before committing to a long transfer. Do not silently splice the separate
range probes into the original download or switch to a third-party mirror.

After a complete download, compute the full SHA256 and validate any independently
published vendor checksum or package signature that becomes available. Only
then give the complete file its original basename and preserve it with the
[firmware intake tool](firmware-intake.md):

```sh
python3 scripts/firmware.py \
  'artifacts/downloads/nezha_images_OS3.0.309.0.WPACNXM_20260714.0000.00_16.0_cn_1081d3072b.tgz' \
  --device nezha \
  --build OS3.0.309.0.WPACNXM \
  --region CN \
  --source-url 'https://bigota.d.miui.com/OS3.0.309.0.WPACNXM/nezha_images_OS3.0.309.0.WPACNXM_20260714.0000.00_16.0_cn_1081d3072b.tgz'
```

That command is for a future **complete** file; it has not been run against this
partial. Intake records and verifies a separate local copy but does not by itself
authenticate the firmware. Offline extraction remains a separate reviewed task.
No package acquisition authorizes a reboot, flash, unlock, relock, or wipe.

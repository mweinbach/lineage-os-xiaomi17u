# Fastboot archive extraction

`scripts/firmware_tar.py` extracts regular `.img` files from a separately
verified TAR/GZIP intake. It never runs a firmware installer or extracts its
programs. The ZIP workflow remains in `scripts/firmware_images.py`.

First preserve a complete, readable package with the
[intake tool](firmware-intake.md), recording the actual source and full SHA256.
A filename or expected download length does not establish archive integrity
or publisher authenticity. Then use a new ignored output directory:

```sh
python3 scripts/firmware_tar.py \
  --intake artifacts/firmware/PACKAGE_SHA256 \
  --expected-sha256 PACKAGE_SHA256 \
  --output artifacts/firmware-analysis/PACKAGE_SHA256/archive-images
```

Replace both checksum placeholders with the verified 64-character digest. The
tool accepts `images/*.img` or one archive root above `images/`, including
numbered Android sparse fragments. It does not concatenate sparse fragments.
Links, special files, GNU sparse TAR members, ambiguous image roots, duplicate
paths and case aliases are rejected. An archive may contain inert installers,
but their contents are not written out or executed.

The package hash is checked before extraction. The entire gzip stream is read
through its CRC32 and length trailer, including bytes buffered past the TAR end
marker. TAR header checksums, decompression bounds, extended-header bounds and
available disk space are checked. Each selected image is hashed during the
copy and again on readback. Only a successful run publishes a new output
directory; existing outputs and the immutable intake remain unchanged.

The receipt preserves package provenance and every extracted image hash.
These checks establish local integrity, not Xiaomi key ownership, AVB validity,
partition fit or ROM compatibility. Inspect AVB, boot headers and logical
partition metadata separately before admitting an image to a build. See
[firmware analysis](firmware-analysis.md) for the existing sparse/LP workflow.

Offline synthetic tests cover successful extraction and malformed, truncated,
corrupt, ambiguous and concurrently changed inputs. Run `make test` before
using a changed extractor on firmware.

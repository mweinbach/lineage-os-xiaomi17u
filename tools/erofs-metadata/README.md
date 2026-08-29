# Read-only EROFS metadata inventory

`nezha_erofs_metadata` produces a complete JSONL inventory directly from an
EROFS image. It never mounts or extracts the filesystem, runs firmware, follows
on-image symlinks, or writes the image. This is evidence for a separately
reviewed five-file SELinux image derivation; running it does not adopt that
derivation or establish policy, AVB, OTA, or hardware compatibility.

The C source targets the exact `liberofs` ABI at
`external/erofs-utils` commit
`2c190a73fceb29f00da0558e44bb88ce19ec5bf4` (`1.8.3`). Keep that revision pinned.
The source snapshots reviewed for this implementation are recorded under the
ignored `reports/oem-policy-integration-20260829/source-erofs*` and
`source-policyextras` directories, with their capture receipts.
The native build and execution receipts are separate from offline Python tests.

## Native build and invocation

Copy this directory into the existing pinned Android checkout without replacing
unrelated source. Its `Android.bp` defines the Linux host target
`nezha_erofs_metadata`, using the pinned `erofs-utils_export_defaults` so the
library and consumer agree on conditional structure layouts. It links the
existing `liberofs` and BoringSSL `libcrypto` plus their host dependencies.
Build only from the sole authorized existing source-volume owner, after the
usual disk, process, source-pin and filesystem checks. The exporter is not a
reason to create another VM, sync sources, or alter readiness gates.

The preferred guarded runner opens the image read-only with no symlink
traversal, retains the descriptor and its identity, then passes that descriptor
to:

```text
nezha_erofs_metadata --image-fd FD
```

The exporter duplicates the descriptor with close-on-exec; it never closes the
caller's original descriptor or changes its file offset. The runner must bind
the executable hash, input image hash, source controls, exit status and complete
stdout/stderr, and verify the original pathname again after execution.

Direct invocation is also available:

```text
nezha_erofs_metadata --image /absolute/private/path/image.img
nezha_erofs_metadata --version
```

The path form checks every component with `openat` and `O_NOFOLLOW`, rejects
`.`/`..` and noncanonical separators, opens only a regular file read-only, and
reopens the path for an identity comparison afterward. No mount, block device,
write mode, extraction option or output filename is accepted. Redirect stdout
only through the enclosing guarded capture workflow.

## Admission and completeness

The initial supported slice deliberately covers only the reviewed 4 KiB,
single-device EROFS format:

- Compatibility flags are confined to `0x07`, with a present, valid superblock
  checksum required. Incompatible flags are confined to `0x01`.
- Extra devices, packed inodes, long xattr prefixes, superblock extensions,
  nonzero directory-block hints and unknown reserved fields are rejected.
  The 1,024-byte image preamble must be zero. The raw volume name and UUID are
  reported without interpreting them as terminated strings.
- The underlying file and filesystem must contain at least 16 KiB because the
  pinned Android library initially reads its 16 KiB maximum block size. Images
  are limited to 64 GiB, individual files to 16 GiB, decoded regular-file bytes
  across all paths to 128 GiB, and namespace entries to 100,000.
- Paths are limited to 4,096 bytes and 128 levels, with 64 MiB of total path
  storage. Directories are bounded to 16 MiB. Per-inode xattrs are bounded to
  1,024 names and 1 MiB of name/value bytes, and 64 MiB across all paths.

The superblock checksum uses the pinned fsck recipe: zero the checksum field
and run `erofs_crc32c(~0, block + 1024, 3072)`. The complete regular image file,
including any bytes after the EROFS filesystem, is SHA256-hashed before and after
the traversal. Descriptor device/inode, type/mode, owner, link count, length,
mtime and ctime must remain stable. Atime is excluded because reads may update
it. All filesystem reads are bounded to the declared EROFS extent, excluding
an AVB tail. Custom read-only library operations return a complete read or a
negative error, preventing `liberofs` from silently padding a short read with
zeroes. Unexpected write or cursor operations fail.

Raw inode fields are checked before library decoding. Raw directory blocks are
parsed with explicit entry/name bounds, byte ordering and duplicate checks;
`.` and `..` must identify the correct directories. Every reachable path is
reported, including `/`. Directory aliases and cycles fail. The count of
distinct reachable NIDs must match the superblock inode count; every
non-directory NID must have exactly its recorded number of links. Directory
link counts are checked against their immediate subdirectories, with the
compact-format overflow representation handled explicitly.

Xattrs are decoded directly from both inline and shared on-image entries, then
cross-checked against `erofs_listxattr` and `erofs_getxattr`. Namespaces
`user`, POSIX ACL, `trusted` and `security` are supported; undefined/Lustre and
long-prefix encodings fail instead of being silently omitted. All-zero inline
padding is accepted. Duplicate names fail. Raw value bytes are retained,
including zero-length values, trailing NUL bytes, SELinux labels, and the full
capability wire format. No label lookup, capability-mask reconstruction or
overlay-xattr rewrite occurs. The raw name-filter bits are checked with the
pinned XXH32 algorithm: a filter must never hide any present attribute. A zero
filter and additional clear bits remain valid.

Regular-file content is streamed through the pinned decoder and SHA256. Only
legacy 4 KiB physical clusters using LZ4 or the plain-block encoding are admitted;
compact headers must not enable unadvertised algorithms or packing features.
Logical index lookback is checked independently and limited to 2,048 clusters
and steps before invoking the recursive library mapper. Each map consumes the
same immutable index pages that passed those checks, with at most 16 cached
pages. Compact physical-block addition must not wrap. The exact resulting map
is range-checked before decoding into a 4 KiB input buffer and a maximum 8 MiB
decoded extent. This does not rely on the library's writer configuration to
bound its reader. At most 10,000,000 mappings may be processed per export.

The initial superblock decode likewise consumes the same captured 16 KiB that
passed raw admission. This keeps unsupported features from being introduced
between validation and decoding; full-file hashes and identity checks still
guard the completed inventory against other concurrent modifications. Symlink
target bytes are recorded without following or normalizing them. Device inodes
are reported without creating devices. Unknown inode types or data layouts,
decode errors, resource violations, malformed metadata and identity changes
prevent the completion record.

## JSONL contract

All strings containing on-image bytes use lowercase hexadecimal so arbitrary
POSIX names do not depend on UTF-8 or the host's case sensitivity. Each line is
one JSON object; output ends with exactly one successful summary. Partial output
is not a valid manifest, even if individual entries parse.

The header has `record="header"`, `schema_version=1`,
`tool="nezha_erofs_metadata"`, `image_size_bytes`, `image_sha256`,
`superblock_checksum_verified=true`, and this exact `superblock` field set:

```text
block_size, root_nid, inode_count, primary_blocks, total_blocks,
meta_blkaddr, xattr_blkaddr, feature_compat, feature_incompat,
build_time_sec, build_time_nsec, uuid_hex, volume_name_hex,
extra_devices, packed_nid, xattr_prefix_count,
available_compression_algorithms
```

Each entry has `record="entry"`, `path_hex`, `nid`, `type`, `mode`, `uid`,
`gid`, `nlink`, `size_bytes`, `mtime_sec`, `mtime_nsec`, `rdev`, and `xattrs`.
`mode` includes the file-type bits. Types are `regular`, `directory`, `symlink`,
`char`, `block`, `fifo`, or `socket`. `rdev` is the Linux-decoded device number
for character/block devices and JSON `null` otherwise. The xattr array is
sorted by raw name bytes, with objects containing exactly `name_hex` and
`value_hex`. Only regular files have `content_sha256`; only symlinks have
`symlink_target_hex`. The root path is `2f`.

The final line has `record="summary"`, `entry_count`, the matching final
`image_sha256`, and `complete=true`. Require process exit zero and retain all
diagnostics before accepting a manifest. The offline comparator binds exact
manifest and image identities, normalizes hardlink groups by their paths rather
than physical NIDs, and checks the separately reviewed replacement contract.
Changed EROFS layout or NIDs are not evidence of changed file semantics; missing
paths, changed raw xattrs or changed link groups must not be ignored.

The Python layer only validates already captured manifests. It does not launch
the native exporter or write images:

```text
python3 scripts/erofs_metadata.py validate --manifest native.jsonl --expected-image-sha256 HASH --expected-manifest-sha256 HASH
python3 scripts/erofs_metadata.py compare --before before.jsonl --after after.jsonl --contract replacements.json
```

The replacement contract uses `schema_version=1`,
`operation="erofs-policy-data-replacements"`, and `partition="vendor"` or
`"odm"`. Its `before` and `after` each bind `image_sha256`, `image_size_bytes`
and `manifest_sha256`. Each replacement binds its image-relative absolute path
such as `/etc/selinux/vendor_sepolicy.cil` and both before/after `sha256` and
`size_bytes`. The accepted set is exactly one vendor path or exactly four ODM
paths; raw metadata changes are not part of these content replacements.

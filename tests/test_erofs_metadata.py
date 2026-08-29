"""Offline semantic-evidence tests; no image, native process, VM, or phone is used."""

import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from scripts import erofs_metadata as metadata


def checksum(value):
    return hashlib.sha256(value).hexdigest()


def attr(name, value):
    return {"name_hex": name.hex(), "value_hex": value.hex()}


def inode(path, nid, kind="regular", data=b"preserved", *, nlink=1):
    row = {
        "record": "entry", "path_hex": path.hex(), "nid": nid, "type": kind,
        "mode": metadata.TYPE_MODES[kind] | (0o755 if kind == "directory" else 0o644),
        "uid": 0, "gid": 0, "nlink": nlink, "size_bytes": len(data),
        "mtime_sec": 1230768000, "mtime_nsec": 123456789, "rdev": None,
        "xattrs": [attr(b"security.selinux", b"u:object_r:vendor_file:s0\0")],
    }
    if kind == "regular":
        row["content_sha256"] = checksum(data)
    elif kind == "symlink":
        row["symlink_target_hex"] = data.hex()
    elif kind == "directory":
        row["size_bytes"] = 64
        row["nlink"] = 2
    else:
        row["size_bytes"] = 0
        if kind in {"char", "block"}:
            row["rdev"] = 259
    return row


def fixture(partition="vendor", image_hash="a" * 64):
    entries = [inode(b"/", 1, "directory"), inode(b"/etc", 2, "directory"),
               inode(b"/etc/selinux", 3, "directory")]
    for offset, path in enumerate(sorted(metadata.REPLACEMENT_PATHS[partition]), 4):
        entries.append(inode(path.encode(), offset, data=b"old policy"))
    next_nid = len(entries) + 1
    entries += [inode(b"/unchanged", next_nid),
                inode(b"/link", next_nid + 1, "symlink", b"../../external/target"),
                inode(b"/hard-a", next_nid + 2, nlink=2),
                inode(b"/hard-b", next_nid + 2, nlink=2),
                inode(b"/raw-\xff", next_nid + 3, data=b"")]
    header = {
        "record": "header", "schema_version": 1, "tool": metadata.TOOL_NAME,
        "image_size_bytes": 65536, "image_sha256": image_hash,
        "superblock_checksum_verified": True,
        "superblock": {
            "block_size": 4096, "root_nid": 1, "inode_count": len(entries) - 1,
            "primary_blocks": 4, "total_blocks": 4, "meta_blkaddr": 0,
            "xattr_blkaddr": 0, "feature_compat": 7, "feature_incompat": 1,
            "build_time_sec": 1230768000, "build_time_nsec": 0,
            "uuid_hex": "0123456789abcdef" * 2, "volume_name_hex": "00" * 16,
            "extra_devices": 0, "packed_nid": 0, "xattr_prefix_count": 0,
            "available_compression_algorithms": 1,
        },
    }
    rows = [header, *entries, {"record": "summary", "entry_count": len(entries),
                             "image_sha256": image_hash, "complete": True}]
    recount(rows)
    return rows


def by_path(rows, path):
    return next(row for row in rows if row.get("path_hex") == path.hex())


def recount(rows):
    entries = [row for row in rows if row.get("record") == "entry"]
    rows[0]["superblock"]["inode_count"] = len({row["nid"] for row in entries})
    rows[-1]["entry_count"] = len(entries)
    directories = {bytes.fromhex(row["path_hex"]): row for row in entries if row["type"] == "directory"}
    for row in directories.values():
        row["nlink"] = 2
    for path in directories:
        if path != b"/":
            parent = path.rsplit(b"/", 1)[0] or b"/"
            if parent in directories:
                directories[parent]["nlink"] += 1


class ErofsMetadataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.before_path = self.root / "before.jsonl"
        self.after_path = self.root / "after.jsonl"
        self.contract_path = self.root / "replacement.json"

    def write(self, rows, path=None):
        path = path or self.before_path
        raw = b"".join((json.dumps(row, separators=(",", ":")) + "\n").encode() for row in rows)
        path.write_bytes(raw)
        return checksum(raw)

    def read(self, rows):
        self.write(rows)
        return metadata.read_manifest(self.before_path)

    def pair(self, partition="vendor"):
        before = fixture(partition)
        after = copy.deepcopy(before)
        after[0]["image_sha256"] = after[-1]["image_sha256"] = "b" * 64
        after[0]["superblock"]["root_nid"] += 100
        after[0]["superblock"]["primary_blocks"] += 1
        after[0]["superblock"]["total_blocks"] += 1
        for row in after[1:-1]:
            row["nid"] += 100
        for path in metadata.REPLACEMENT_PATHS[partition]:
            row = by_path(after, path.encode())
            row["size_bytes"] = len(b"reviewed new policy")
            row["content_sha256"] = checksum(b"reviewed new policy")
        return before, after

    def save_pair(self, before, after, partition="vendor"):
        hashes = [self.write(before), self.write(after, self.after_path)]
        contract = {
            "schema_version": 1, "operation": "erofs-policy-data-replacements", "partition": partition,
            "before": {"image_sha256": before[0]["image_sha256"], "image_size_bytes": before[0]["image_size_bytes"],
                       "manifest_sha256": hashes[0]},
            "after": {"image_sha256": after[0]["image_sha256"], "image_size_bytes": after[0]["image_size_bytes"],
                      "manifest_sha256": hashes[1]},
            "replacements": [],
        }
        for path in sorted(metadata.REPLACEMENT_PATHS[partition]):
            row = {"path": path}
            for name, rows in (("before", before), ("after", after)):
                member = by_path(rows, path.encode())
                row[name] = {"sha256": member["content_sha256"], "size_bytes": member["size_bytes"]}
            contract["replacements"].append(row)
        self.contract_path.write_text(json.dumps(contract))
        return contract

    def compare(self):
        return metadata.compare(self.before_path, self.after_path, self.contract_path)

    def test_full_export_preserves_binary_paths_xattrs_and_hardlink_equivalence(self):
        rows = fixture()
        selected = by_path(rows, b"/unchanged")
        selected["uid"], selected["gid"], selected["mode"] = 1000, 2000, stat.S_IFREG | 0o4750
        selected["xattrs"] = [attr(b"security.capability", b"\x00\x00\x00\x02\x80\x00\x00\x00"),
                              attr(b"security.selinux", b"u:object_r:vendor_file:s0\0"),
                              attr(b"user.empty", b"")]
        manifest = self.read(rows)
        self.assertIn(b"/raw-\xff", manifest.entries)
        self.assertEqual(manifest.hardlinks, ((b"/hard-a", b"/hard-b"),))
        self.assertEqual(manifest.entries[b"/unchanged"], selected)
        report = metadata.manifest_report(manifest)
        self.assertTrue(report["structural_validation_passed"])
        self.assertTrue(all(value is False for value in report["boundaries"].values()))

    def test_exact_vendor_replacement_allows_new_nids_and_physical_layout(self):
        before, after = self.pair()
        self.save_pair(before, after)
        report = self.compare()
        self.assertTrue(report["comparison_passed"])
        self.assertEqual(len(report["replacements"]), 1)
        self.assertEqual(report["hardlink_group_count"], 1)
        self.assertTrue(report["replacements"][0]["content_changed"])

    def test_exact_odm_four_file_set_is_required(self):
        before, after = self.pair("odm")
        contract = self.save_pair(before, after, "odm")
        self.assertEqual(len(self.compare()["replacements"]), 4)
        contract["replacements"].pop()
        self.contract_path.write_text(json.dumps(contract))
        with self.assertRaisesRegex(metadata.MetadataError, "incomplete"):
            self.compare()

    def test_names_that_differ_by_case_are_preserved_as_distinct_paths(self):
        rows = fixture()
        rows[-1:-1] = [inode(b"/Upper", 40), inode(b"/upper", 41)]
        recount(rows)
        manifest = self.read(rows)
        self.assertIn(b"/Upper", manifest.entries)
        self.assertIn(b"/upper", manifest.entries)

    def test_no_content_or_metadata_exception_outside_declared_policy_path(self):
        mutations = {
            "owner": lambda row: row.update(uid=2000),
            "mode": lambda row: row.update(mode=stat.S_IFREG | 0o4755),
            "nanoseconds": lambda row: row.update(mtime_nsec=2),
            "xattr_removed": lambda row: row.update(xattrs=[]),
            "xattr_trailing_nul": lambda row: row["xattrs"][0].update(value_hex=b"u:object_r:vendor_file:s0".hex()),
            "content": lambda row: row.update(content_sha256=checksum(b"unexpected")),
            "size": lambda row: row.update(size_bytes=10),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                before, after = self.pair()
                mutate(by_path(after, b"/unchanged"))
                self.save_pair(before, after)
                with self.assertRaisesRegex(metadata.MetadataError, "unapproved"):
                    self.compare()

    def test_policy_replacement_cannot_change_its_metadata(self):
        before, after = self.pair()
        by_path(after, b"/etc/selinux/vendor_sepolicy.cil")["xattrs"] = []
        self.save_pair(before, after)
        with self.assertRaisesRegex(metadata.MetadataError, "unapproved"):
            self.compare()

    def test_root_and_ancestor_metadata_are_not_implicit_replacement_exceptions(self):
        for path in [b"/", b"/etc", b"/etc/selinux"]:
            with self.subTest(path=path):
                before, after = self.pair()
                by_path(after, path)["gid"] = 20
                self.save_pair(before, after)
                with self.assertRaisesRegex(metadata.MetadataError, "unapproved"):
                    self.compare()

    def test_symlink_target_change_is_rejected_without_following_target(self):
        before, after = self.pair()
        by_path(after, b"/link")["symlink_target_hex"] = b"../../external/other!".hex()
        self.save_pair(before, after)
        with self.assertRaises(metadata.MetadataError):
            self.compare()

    def test_added_and_removed_paths_are_rejected(self):
        for add in (True, False):
            with self.subTest(add=add):
                before, after = self.pair()
                if add:
                    after.insert(-1, inode(b"/extra", 200))
                else:
                    after.remove(by_path(after, b"/unchanged"))
                recount(after)
                self.save_pair(before, after)
                with self.assertRaisesRegex(metadata.MetadataError, "paths were added or removed"):
                    self.compare()

    def test_dereferencing_hardlinks_is_rejected_even_with_identical_content(self):
        before, after = self.pair()
        by_path(after, b"/hard-a")["nlink"] = 1
        by_path(after, b"/hard-b").update(nlink=1, nid=201)
        recount(after)
        self.save_pair(before, after)
        with self.assertRaisesRegex(metadata.MetadataError, "hardlink equivalence"):
            self.compare()

    def test_contradictory_hardlink_metadata_and_counts_are_rejected(self):
        for name, change in [("metadata", {"gid": 3}), ("count", {"nlink": 3})]:
            with self.subTest(name=name):
                rows = fixture()
                by_path(rows, b"/hard-a").update(change)
                with self.assertRaisesRegex(metadata.MetadataError, "hardlink|contradictory"):
                    self.read(rows)

    def test_directory_inode_alias_is_rejected(self):
        rows = fixture()
        by_path(rows, b"/etc")["nid"] = 1
        recount(rows)
        with self.assertRaisesRegex(metadata.MetadataError, "directory inode alias"):
            self.read(rows)

    def test_directory_links_must_match_children_and_directory_data_cannot_be_empty(self):
        for value in [1, 2, 4, 4294967295]:
            with self.subTest(value=value):
                rows = fixture()
                by_path(rows, b"/etc")["nlink"] = value
                with self.assertRaises(metadata.MetadataError):
                    self.read(rows)
        rows = fixture()
        by_path(rows, b"/etc")["size_bytes"] = 0
        with self.assertRaisesRegex(metadata.MetadataError, "directory size"):
            self.read(rows)

    def test_compact_directory_link_overflow_sentinel_is_scoped_to_uint16_overflow(self):
        # Boundary values from the pinned on-disk compact/extended representations.
        cases = [(2, 0, True), (1, 0, False), (65535, 65533, True),
                 (1, 65533, False), (1, 65534, True), (65536, 65534, True),
                 (65535, 65534, False)]
        for links, children, expected in cases:
            with self.subTest(links=links, children=children):
                self.assertIs(metadata._directory_links_match(links, children), expected)

    def test_superblock_uuid_timestamp_features_and_volume_are_preserved(self):
        fields = {"uuid_hex": "ff" * 16, "volume_name_hex": "01" * 16,
                  "build_time_sec": 100, "build_time_nsec": 1,
                  "feature_compat": 3, "feature_incompat": 0,
                  "available_compression_algorithms": 0}
        for field, value in fields.items():
            with self.subTest(field=field):
                before, after = self.pair()
                after[0]["superblock"][field] = value
                self.save_pair(before, after)
                with self.assertRaisesRegex(metadata.MetadataError, "superblock semantic field changed"):
                    self.compare()

    def test_unsupported_features_and_bad_extents_are_not_accepted(self):
        changes = [{"block_size": 16384}, {"feature_compat": 0}, {"feature_compat": 15},
                   {"feature_incompat": 2}, {"extra_devices": 1}, {"packed_nid": 1},
                   {"xattr_prefix_count": 1}, {"primary_blocks": 17, "total_blocks": 17},
                   {"meta_blkaddr": 4}, {"total_blocks": 3}, {"build_time_nsec": 10**9},
                   {"root_nid": 65536}, {"primary_blocks": 3, "total_blocks": 3},
                   {"build_time_sec": 2**63}]
        for change in changes:
            with self.subTest(change=change):
                rows = fixture()
                rows[0]["superblock"].update(change)
                with self.assertRaises(metadata.MetadataError):
                    self.read(rows)

    def test_bad_native_header_and_non_integer_metadata_are_rejected(self):
        rows = fixture()
        for field, value in [("schema_version", True), ("superblock_checksum_verified", False),
                             ("tool", "other"), ("image_sha256", "a" * 63)]:
            with self.subTest(field=field):
                changed = copy.deepcopy(rows)
                changed[0][field] = value
                with self.assertRaises(metadata.MetadataError):
                    self.read(changed)
        for field, value in [("uid", True), ("gid", -1), ("mode", 0o644), ("nlink", 0),
                             ("mtime_nsec", 1.5), ("type", []), ("nid", 2**64)]:
            with self.subTest(field=field):
                changed = copy.deepcopy(rows)
                by_path(changed, b"/unchanged")[field] = value
                with self.assertRaises(metadata.MetadataError):
                    self.read(changed)

    def test_ambiguous_raw_paths_and_missing_parent_are_rejected(self):
        for path in [b"relative", b"//double", b"/etc/../outside", b"/etc/./same", b"/trailing/",
                     b"/nul\0name", b"/" + b"a" * 256, b"/a" * 129, b"/missing/file"]:
            with self.subTest(path=path):
                rows = fixture()
                by_path(rows, b"/unchanged")["path_hex"] = path.hex()
                with self.assertRaises(metadata.MetadataError):
                    self.read(rows)

    def test_duplicate_paths_and_missing_root_are_rejected(self):
        rows = fixture()
        rows.insert(-1, copy.deepcopy(by_path(rows, b"/unchanged")))
        recount(rows)
        with self.assertRaisesRegex(metadata.MetadataError, "duplicate path"):
            self.read(rows)
        rows = fixture()
        rows.remove(by_path(rows, b"/"))
        recount(rows)
        with self.assertRaisesRegex(metadata.MetadataError, "root directory"):
            self.read(rows)

    def test_missing_null_duplicate_unsorted_or_noncanonical_xattrs_are_rejected(self):
        values = [None, {"security.selinux": "invented"},
                  [attr(b"security.selinux", b"a"), attr(b"security.selinux", b"b")],
                  [attr(b"user.z", b""), attr(b"security.selinux", b"a")],
                  [{"name_hex": "FF", "value_hex": ""}],
                  [attr(b"nul\0name", b"x")], [attr(b"user.large", b"x" * 65536)]]
        for value in values:
            with self.subTest(value=str(value)[:60]):
                rows = fixture()
                by_path(rows, b"/unchanged")["xattrs"] = value
                with self.assertRaises(metadata.MetadataError):
                    self.read(rows)
        rows = fixture()
        del by_path(rows, b"/unchanged")["xattrs"]
        with self.assertRaisesRegex(metadata.MetadataError, "unexpected inode fields"):
            self.read(rows)

    def test_complete_summary_is_required_and_must_bind_same_image(self):
        for mutation in [lambda rows: rows.pop(), lambda rows: rows[-1].update(complete=False),
                         lambda rows: rows[-1].update(entry_count=1),
                         lambda rows: rows[-1].update(image_sha256="b" * 64),
                         lambda rows: rows.append(copy.deepcopy(rows[-1]))]:
            rows = fixture()
            mutation(rows)
            with self.assertRaises(metadata.MetadataError):
                self.read(rows)

    def test_truncation_blank_records_duplicate_json_keys_and_nan_fail(self):
        self.write(fixture())
        valid = self.before_path.read_bytes()
        invalid = [valid[:-1], valid + b"\n", valid.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1', 1),
                   valid.replace(b'"uid":0', b'"uid":NaN', 1)]
        for raw in invalid:
            with self.subTest(raw=raw[:70]):
                self.before_path.write_bytes(raw)
                with self.assertRaises(metadata.MetadataError):
                    metadata.read_manifest(self.before_path)

    def test_non_utf8_json_and_excessive_integer_literals_fail_cleanly(self):
        self.write(fixture())
        valid = self.before_path.read_bytes()
        invalid = [valid.decode().encode("utf-16-be"),
                   valid.replace(b'"uid":0', b'"uid":' + b"9" * 5000, 1),
                   valid.replace(b'"tool":"', b'"tool":"\xff', 1)]
        for raw in invalid:
            with self.subTest(prefix=raw[:30]):
                self.before_path.write_bytes(raw)
                with self.assertRaises(metadata.MetadataError):
                    metadata.read_manifest(self.before_path)

    def test_expected_manifest_and_image_hashes_bind_evidence(self):
        digest = self.write(fixture())
        metadata.read_manifest(self.before_path, expected_image_sha256="a" * 64, expected_manifest_sha256=digest)
        for options in [{"expected_image_sha256": "b" * 64}, {"expected_manifest_sha256": "f" * 64}]:
            with self.subTest(options=options), self.assertRaises(metadata.MetadataError):
                metadata.read_manifest(self.before_path, **options)

    def test_contract_cannot_expand_the_replacement_set_or_omit_identity(self):
        mutations = [lambda value: value["replacements"][0].update(path="/unchanged"),
                     lambda value: value["before"].pop("manifest_sha256"),
                     lambda value: value.update(partition=[]),
                     lambda value: value["after"].update(image_size_bytes=65537),
                     lambda value: value["after"].update(manifest_sha256="f" * 64),
                     lambda value: value["replacements"][0]["after"].update(sha256="e" * 64)]
        for mutate in mutations:
            before, after = self.pair()
            contract = self.save_pair(before, after)
            mutate(contract)
            self.contract_path.write_text(json.dumps(contract))
            with self.assertRaises(metadata.MetadataError):
                self.compare()

    def test_special_inode_fields_are_checked_without_touching_devices(self):
        rows = fixture()
        rows.insert(-1, inode(b"/char-node", 50, "char"))
        recount(rows)
        self.read(rows)
        by_path(rows, b"/char-node")["rdev"] = None
        with self.assertRaises(metadata.MetadataError):
            self.read(rows)
        by_path(rows, b"/char-node")["rdev"] = 2**32
        with self.assertRaises(metadata.MetadataError):
            self.read(rows)
        rows = fixture()
        by_path(rows, b"/unchanged")["rdev"] = 1
        with self.assertRaises(metadata.MetadataError):
            self.read(rows)

    def test_empty_content_and_symlink_lengths_are_verified(self):
        rows = fixture()
        by_path(rows, b"/raw-\xff")["content_sha256"] = "e" * 64
        with self.assertRaisesRegex(metadata.MetadataError, "empty file"):
            self.read(rows)
        rows = fixture()
        by_path(rows, b"/link")["size_bytes"] += 1
        with self.assertRaisesRegex(metadata.MetadataError, "symlink target and size"):
            self.read(rows)

    def test_manifest_files_and_ancestors_must_not_be_symlinks(self):
        self.write(fixture())
        alias = self.root / "alias.jsonl"
        alias.symlink_to(self.before_path)
        with self.assertRaises((OSError, metadata.MetadataError)):
            metadata.read_manifest(alias)
        ancestor = self.root / "alias-dir"
        ancestor.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(metadata.MetadataError, "real directories"):
            metadata.read_manifest(ancestor / self.before_path.name)

    def test_evidence_changed_during_read_is_rejected(self):
        self.write(fixture())
        original = metadata._json
        changed = False

        def mutate(raw):
            nonlocal changed
            if not changed:
                changed = True
                with self.before_path.open("ab") as stream:
                    stream.write(b" ")
            return original(raw)

        with mock.patch.object(metadata, "_json", side_effect=mutate), self.assertRaises(metadata.MetadataError):
            metadata.read_manifest(self.before_path)

    def test_manifest_record_and_entry_bounds_are_enforced(self):
        self.write(fixture())
        for name, value in [("MAX_MANIFEST_BYTES", 50), ("MAX_RECORD_BYTES", 50), ("MAX_ENTRIES", 2)]:
            with self.subTest(name=name), mock.patch.object(metadata, name, value), self.assertRaises(metadata.MetadataError):
                metadata.read_manifest(self.before_path)

    def test_cli_is_read_only_and_reports_the_evidence_boundary(self):
        digest = self.write(fixture())
        original = self.before_path.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = metadata.main(["validate", "--manifest", str(self.before_path),
                                    "--expected-image-sha256", "a" * 64,
                                    "--expected-manifest-sha256", digest])
        self.assertEqual(result, 0)
        self.assertEqual(self.before_path.read_bytes(), original)
        report = json.loads(output.getvalue())
        self.assertFalse(report["boundaries"]["image_data_rehashed_by_this_command"])
        self.assertFalse(report["boundaries"]["exporter_binary_authenticated"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(metadata.main(["validate", "--manifest", str(self.before_path),
                                            "--expected-image-sha256", "b" * 64]), 1)


if __name__ == "__main__":
    unittest.main()

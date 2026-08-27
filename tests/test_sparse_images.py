"""Synthetic offline sparse-image tests; no firmware, phone, or network needed."""

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "sparse_images", Path(__file__).resolve().parents[1] / "scripts" / "sparse_images.py"
)
sparse = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sparse)


def fixture(chunks, *, block_size=16, total_blocks=None, **header_overrides):
    """Build tiny format fixtures, including intentionally malformed headers."""
    header = {
        "magic": sparse.MAGIC, "major": 1, "minor": 0,
        "header_size": sparse.HEADER.size, "chunk_header_size": sparse.CHUNK_HEADER.size,
        "block_size": block_size,
        "blocks": sum(blocks for _, blocks, _ in chunks) if total_blocks is None else total_blocks,
        "count": len(chunks), "checksum": 0,
    }
    header.update(header_overrides)
    body = bytearray(sparse.HEADER.pack(*header.values()))
    body.extend(b"E" * max(0, header["header_size"] - sparse.HEADER.size))
    for kind, blocks, data in chunks:
        body.extend(sparse.CHUNK_HEADER.pack(kind, 0, blocks, header["chunk_header_size"] + len(data)))
        body.extend(b"X" * max(0, header["chunk_header_size"] - sparse.CHUNK_HEADER.size))
        body.extend(data)
    return bytes(body)


class SparseImageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.destination = self.root / "reconstructed"
        self.parent_sha256 = "a1" * 32
        self.first = self.write(0, fixture([
            (sparse.RAW, 1, b"A" * 16),
            (sparse.DONT_CARE, 3, b""),
        ]))
        self.second = self.write(1, fixture([
            (sparse.DONT_CARE, 2, b""),
            (sparse.FILL, 1, b"1234"),
            (sparse.DONT_CARE, 1, b""),
        ]))
        self.paths = [self.first, self.second]
        self.expected = b"A" * 16 + bytes(16) + b"1234" * 4 + bytes(16)

    def write(self, index, contents):
        path = self.root / f"super.img.{index}"
        path.write_bytes(contents)
        return path

    def inspect(self, paths=None, **options):
        return sparse.inspect_images(self.paths if paths is None else paths,
                                     **{"expected_pieces": 2, **options})

    def reconstruct(self, paths=None, **options):
        return sparse.reconstruct_images(
            self.paths if paths is None else paths,
            **{"expected_pieces": 2, "output_dir": self.destination,
               "parent_sha256": self.parent_sha256, **options},
        )

    def assert_no_outputs(self):
        self.assertFalse(os.path.lexists(self.destination))
        self.assertEqual(list(self.root.glob(".*.stage-*")), [])
        self.assertEqual(list(self.root.glob(".*.sparse.lock")), [])

    def test_inspection_hashes_every_byte_without_writing(self):
        before = sorted(self.root.iterdir())
        report = self.inspect()
        self.assertEqual(report["expanded_size_bytes"], 64)
        self.assertEqual(report["written_bytes"], 32)
        self.assertEqual(report["unwritten_zero_bytes"], 32)
        self.assertEqual(report["write_range_count"], 2)
        self.assertEqual(report["piece_count"], 2)
        for record, path in zip(report["inputs"], self.paths):
            self.assertEqual(record["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(record["size_bytes"], path.stat().st_size)
            self.assertEqual(record["identity"]["inode"], path.stat().st_ino)
        self.assertEqual(report["inputs"][1]["chunk_counts"], {"raw": 0, "fill": 1, "dont_care": 2})
        self.assertEqual(sorted(self.root.iterdir()), before)

    def test_reconstruction_overlays_instead_of_concatenating(self):
        originals = [(path.read_bytes(), sparse._signature(path.stat())) for path in self.paths]
        result = self.reconstruct(list(reversed(self.paths)))
        image = self.destination / "super.raw.img"
        self.assertEqual(image.read_bytes(), self.expected)
        receipt = json.loads((self.destination / "receipt.json").read_text())
        self.assertEqual(receipt, result["receipt"])
        self.assertEqual(receipt["output"]["sha256"], hashlib.sha256(self.expected).hexdigest())
        self.assertEqual(receipt["parent_package_sha256"], self.parent_sha256)
        self.assertIn("caller-provided", receipt["parent_linkage"])
        self.assertIs(receipt["origin_verified"], False)
        self.assertEqual(receipt["output"]["size_bytes"], 64)
        self.assertEqual(len(receipt["tool_sha256"]), 64)
        self.assertEqual(set(path.name for path in self.destination.iterdir()), {"super.raw.img", "receipt.json"})
        for path, (content, signature) in zip(self.paths, originals):
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual(sparse._signature(path.stat()), signature)

    def test_numeric_order_places_ten_after_nine(self):
        paths = []
        for index in range(15):
            chunks = []
            if index:
                chunks.append((sparse.DONT_CARE, index, b""))
            chunks.append((sparse.RAW, 1, bytes([index]) * 16))
            if index < 14:
                chunks.append((sparse.DONT_CARE, 14 - index, b""))
            paths.append(self.write(index, fixture(chunks)))
        report = self.inspect(sorted(paths), expected_pieces=15)
        self.assertEqual([item["name"] for item in report["inputs"]], [path.name for path in paths])
        self.reconstruct(sorted(paths), expected_pieces=15)
        self.assertEqual((self.destination / "super.raw.img").read_bytes(),
                         b"".join(bytes([index]) * 16 for index in range(15)))

    def test_zero_fill_and_initial_holes_are_preserved(self):
        self.first.write_bytes(fixture([
            (sparse.DONT_CARE, 1, b""), (sparse.FILL, 1, bytes(4)),
            (sparse.RAW, 1, b"Z" * 16), (sparse.DONT_CARE, 1, b""),
        ]))
        self.reconstruct([self.first], expected_pieces=1)
        self.assertEqual((self.destination / "super.raw.img").read_bytes(),
                         bytes(32) + b"Z" * 16 + bytes(16))

    def test_all_dont_care_is_a_zeroed_new_image(self):
        self.first.write_bytes(fixture([(sparse.DONT_CARE, 4, b"")]))
        self.reconstruct([self.first], expected_pieces=1)
        self.assertEqual((self.destination / "super.raw.img").read_bytes(), bytes(64))

    def test_header_extensions_are_consumed_and_hashed(self):
        self.first.write_bytes(fixture([(sparse.RAW, 1, b"A" * 16)], header_size=32, chunk_header_size=16))
        report = self.inspect([self.first], expected_pieces=1)
        self.assertEqual(report["inputs"][0]["sha256"], hashlib.sha256(self.first.read_bytes()).hexdigest())
        self.reconstruct([self.first], expected_pieces=1)
        self.assertEqual((self.destination / "super.raw.img").read_bytes(), b"A" * 16)

    def test_buffers_remain_bounded_for_large_raw_and_fill_chunks(self):
        self.first.write_bytes(fixture([(sparse.RAW, 10, b"a" * 160), (sparse.FILL, 11, b"wxyz")]))
        original_read = sparse._parse
        maximum_read = []

        class Reader:
            def __init__(self, wrapped):
                self.wrapped = wrapped

            def read(self, size=-1):
                maximum_read.append(size)
                return self.wrapped.read(size)

            def __getattr__(self, name):
                return getattr(self.wrapped, name)

        def tracked(entry, *args, **kwargs):
            path, stream, signature = entry
            return original_read((path, Reader(stream), signature), *args, **kwargs)

        with mock.patch.object(sparse, "BUFFER_SIZE", 32), mock.patch.object(sparse, "_parse", side_effect=tracked):
            self.reconstruct([self.first], expected_pieces=1)
        self.assertLessEqual(max(maximum_read), 32)
        self.assertGreaterEqual(min(maximum_read), 0)
        self.assertEqual((self.destination / "super.raw.img").read_bytes(), b"a" * 160 + b"wxyz" * 44)

    def test_raw_and_fill_overlaps_are_rejected_including_identical_bytes(self):
        for kind, data in ((sparse.RAW, b"A" * 16), (sparse.FILL, b"AAAA")):
            self.second.write_bytes(fixture([(kind, 1, data), (sparse.DONT_CARE, 3, b"")]))
            with self.subTest(kind=kind), self.assertRaisesRegex(sparse.SparseError, "overlap"):
                self.reconstruct()
            self.assert_no_outputs()

    def test_middle_overlap_is_not_missed(self):
        self.first.write_bytes(fixture([(sparse.RAW, 3, b"A" * 48), (sparse.DONT_CARE, 1, b"")]))
        with self.assertRaisesRegex(sparse.SparseError, "overlap"):
            self.inspect()

    def test_different_geometry_rejected_even_if_byte_length_matches(self):
        for block_size, blocks in ((16, 5), (32, 2)):
            self.second.write_bytes(fixture([(sparse.DONT_CARE, blocks, b"")], block_size=block_size))
            with self.subTest(block_size=block_size), self.assertRaisesRegex(sparse.SparseError, "different output geometry"):
                self.reconstruct()
            self.assert_no_outputs()

    def test_bad_magic_versions_header_sizes_geometry_counts_fail(self):
        for options in (
            {"magic": 0}, {"major": 0}, {"major": 2}, {"minor": 1},
            {"header_size": 27}, {"chunk_header_size": 11}, {"block_size": 0},
            {"block_size": 15}, {"blocks": 0}, {"count": 0}, {"count": 100_001},
        ):
            self.first.write_bytes(fixture([(sparse.RAW, 1, b"A" * 16)], **options))
            with self.subTest(options=options), self.assertRaises(sparse.SparseError):
                self.inspect([self.first], expected_pieces=1)

    def test_nonzero_header_checksum_fails_closed(self):
        self.first.write_bytes(fixture([(sparse.RAW, 1, b"A" * 16)], checksum=123))
        with self.assertRaisesRegex(sparse.SparseError, "checksum is unsupported"):
            self.reconstruct([self.first], expected_pieces=1)
        self.assert_no_outputs()

    def test_crc_chunk_fails_closed_even_with_a_zero_checksum(self):
        self.first.write_bytes(fixture([(sparse.RAW, 1, b"A" * 16), (sparse.CRC32, 0, bytes(4))]))
        with self.assertRaisesRegex(sparse.SparseError, "CRC32 sparse chunks are unsupported"):
            self.reconstruct([self.first], expected_pieces=1)
        self.assert_no_outputs()

    def test_unknown_chunk_and_nonzero_reserved_field_fail(self):
        self.first.write_bytes(fixture([(0xFFFF, 1, b"A" * 16)]))
        with self.assertRaisesRegex(sparse.SparseError, "unknown sparse chunk"):
            self.inspect([self.first], expected_pieces=1)
        raw = bytearray(fixture([(sparse.RAW, 1, b"A" * 16)]))
        struct.pack_into("<H", raw, sparse.HEADER.size + 2, 1)
        self.first.write_bytes(raw)
        with self.assertRaisesRegex(sparse.SparseError, "reserved"):
            self.inspect([self.first], expected_pieces=1)

    def test_wrong_payload_length_for_each_chunk_type_fails(self):
        for kind, payload in ((sparse.RAW, bytes(15)), (sparse.RAW, bytes(17)),
                              (sparse.FILL, bytes(3)), (sparse.FILL, bytes(5)),
                              (sparse.DONT_CARE, bytes(1))):
            self.first.write_bytes(fixture([(kind, 1, payload)]))
            with self.subTest(kind=kind, size=len(payload)), self.assertRaisesRegex(sparse.SparseError, "total size"):
                self.inspect([self.first], expected_pieces=1)

    def test_chunk_total_size_smaller_than_header_fails(self):
        data = bytearray(fixture([(sparse.RAW, 1, bytes(16))]))
        struct.pack_into("<I", data, sparse.HEADER.size + 8, 1)
        self.first.write_bytes(data)
        with self.assertRaisesRegex(sparse.SparseError, "total size"):
            self.inspect([self.first], expected_pieces=1)

    def test_chunk_range_overflow_underflow_and_zero_length_fail(self):
        for chunks, blocks in (([(sparse.DONT_CARE, 2, b"")], 1),
                               ([(sparse.DONT_CARE, 1, b"")], 2),
                               ([(sparse.DONT_CARE, 0, b"")], 1)):
            self.first.write_bytes(fixture(chunks, total_blocks=blocks))
            with self.subTest(chunks=chunks, blocks=blocks), self.assertRaises(sparse.SparseError):
                self.inspect([self.first], expected_pieces=1)

    def test_every_truncated_prefix_is_rejected(self):
        complete = fixture([(sparse.RAW, 2, bytes(32)), (sparse.FILL, 2, b"abcd")])
        for length in range(len(complete)):
            self.first.write_bytes(complete[:length])
            with self.subTest(length=length), self.assertRaises(sparse.SparseError):
                self.inspect([self.first], expected_pieces=1)

    def test_trailing_data_and_underdeclared_chunk_count_fail(self):
        for data in (fixture([(sparse.RAW, 1, bytes(16))]) + b"trailing",
                     fixture([(sparse.RAW, 1, bytes(16)), (sparse.FILL, 1, bytes(4))], count=1)):
            self.first.write_bytes(data)
            with self.assertRaises(sparse.SparseError):
                self.reconstruct([self.first], expected_pieces=1)
            self.assert_no_outputs()

    def test_chunk_budget_is_for_the_whole_input_set(self):
        with mock.patch.object(sparse, "MAX_CHUNKS", 4):
            with self.assertRaisesRegex(sparse.SparseError, "chunk count"):
                self.inspect()

    def test_maximum_expanded_size_applies_before_payload_reads(self):
        self.first.write_bytes(fixture([(sparse.DONT_CARE, 1_000_000, b"")]))
        with self.assertRaisesRegex(sparse.SparseError, "size limit"):
            self.reconstruct([self.first], expected_pieces=1, max_output_bytes=64)
        self.assert_no_outputs()
        for maximum in (0, -1, True, 1.5):
            with self.subTest(maximum=maximum), self.assertRaisesRegex(sparse.SparseError, "positive integer"):
                self.inspect(max_output_bytes=maximum)

    def test_missing_trailing_piece_requires_explicit_inventory_count(self):
        with self.assertRaisesRegex(sparse.SparseError, "expected 2 pieces"):
            self.inspect([self.first])
        for count in (0, -1, True, sparse.MAX_PIECES + 1):
            with self.subTest(count=count), self.assertRaises(sparse.SparseError):
                self.inspect(expected_pieces=count)

    def test_gaps_duplicate_indexes_and_nonzero_first_index_fail(self):
        third = self.write(2, self.second.read_bytes())
        for paths in ([self.first, third], [self.first, self.first], [self.second, third]):
            with self.subTest(paths=paths), self.assertRaisesRegex(sparse.SparseError, "no gaps or duplicates"):
                self.inspect(paths)

    def test_malformed_or_mixed_piece_names_fail(self):
        for name in ("super.img.01", "super.img.-1", "super.img", "super.0", "vendor.img.1", "super.img.1\n"):
            path = self.root / name
            path.write_bytes(self.second.read_bytes())
            with self.subTest(name=name), self.assertRaises(sparse.SparseError):
                self.inspect([self.first, path])

    def test_mixed_parent_directories_fail(self):
        folder = self.root / "elsewhere"
        folder.mkdir()
        alternate = folder / self.second.name
        alternate.write_bytes(self.second.read_bytes())
        with self.assertRaisesRegex(sparse.SparseError, "same image basename and directory"):
            self.inspect([self.first, alternate])

    def test_input_symlink_directory_and_fifo_fail_without_blocking(self):
        self.second.unlink()
        self.second.symlink_to(self.first)
        with self.assertRaisesRegex(sparse.SparseError, "not a regular file"):
            self.inspect()
        self.second.unlink()
        self.second.mkdir()
        with self.assertRaisesRegex(sparse.SparseError, "not a regular file"):
            self.inspect()
        self.second.rmdir()
        os.mkfifo(self.second)
        with self.assertRaisesRegex(sparse.SparseError, "not a regular file"):
            self.inspect()

    def test_symlink_in_input_ancestor_fails(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(sparse.SparseError, "symlink"):
            self.inspect([alias / self.first.name, alias / self.second.name])

    def test_input_hardlink_alias_is_rejected(self):
        self.second.unlink()
        os.link(self.first, self.second)
        with self.assertRaisesRegex(sparse.SparseError, "same input inode"):
            self.inspect()

    def test_source_path_swap_between_lstat_and_open_is_rejected(self):
        original = sparse.os.open
        def replace_before_open(path, flags, *args, **kwargs):
            if path == self.first:
                content = self.first.read_bytes()
                self.first.unlink()
                self.first.write_bytes(content)
            return original(path, flags, *args, **kwargs)
        with mock.patch.object(sparse.os, "open", side_effect=replace_before_open):
            with self.assertRaisesRegex(sparse.SparseError, "changed while opening"):
                self.inspect()

    def test_source_change_between_passes_cleans_staging(self):
        original = sparse.shutil.disk_usage
        def change_input(path):
            self.first.write_bytes(self.first.read_bytes() + b"changed")
            return original(path)
        with mock.patch.object(sparse.shutil, "disk_usage", side_effect=change_input):
            with self.assertRaisesRegex(sparse.SparseError, "input changed"):
                self.reconstruct()
        self.assert_no_outputs()

    def test_replacing_input_path_after_output_hash_is_rejected(self):
        original = sparse._hash_output
        def replace_input(stream):
            result = original(stream)
            copy = self.root / "replacement"
            copy.write_bytes(self.first.read_bytes())
            copy.replace(self.first)
            return result
        with mock.patch.object(sparse, "_hash_output", side_effect=replace_input):
            with self.assertRaisesRegex(sparse.SparseError, "input changed"):
                self.reconstruct()
        self.assert_no_outputs()

    def test_changed_previously_read_input_is_detected_before_inspection_returns(self):
        original = sparse._parse
        def change_previous(entry, *args, **kwargs):
            result = original(entry, *args, **kwargs)
            if entry[0] == self.second:
                self.first.write_bytes(b"changed")
            return result
        with mock.patch.object(sparse, "_parse", side_effect=change_previous):
            with self.assertRaisesRegex(sparse.SparseError, "input changed"):
                self.inspect()

    def test_existing_output_directory_file_and_dangling_symlink_are_never_overwritten(self):
        self.destination.mkdir()
        with self.assertRaisesRegex(sparse.SparseError, "already exists"):
            self.reconstruct()
        self.assertEqual(list(self.destination.iterdir()), [])
        self.destination.rmdir()
        self.destination.write_bytes(b"existing evidence")
        with self.assertRaisesRegex(sparse.SparseError, "already exists"):
            self.reconstruct()
        self.assertEqual(self.destination.read_bytes(), b"existing evidence")
        self.destination.unlink()
        self.destination.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(sparse.SparseError, "already exists"):
            self.reconstruct()
        self.assertTrue(self.destination.is_symlink())

    def test_output_ancestor_symlink_and_absent_parent_are_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(sparse.SparseError, "symlink"):
            self.reconstruct(output_dir=alias / "new")
        with self.assertRaises(FileNotFoundError):
            self.reconstruct(output_dir=self.root / "missing" / "new")
        self.assertFalse((self.root / "new").exists())
        self.assertFalse((self.root / "missing").exists())

    def test_existing_lock_is_not_removed_or_modified(self):
        lock = self.root / ".reconstructed.sparse.lock"
        lock.write_text("existing")
        with self.assertRaises(FileExistsError):
            self.reconstruct()
        self.assertEqual(lock.read_text(), "existing")
        self.assertFalse(self.destination.exists())

    def test_destination_appearing_during_reconstruction_is_preserved(self):
        original = sparse._hash_output
        def create_destination(stream):
            checksum = original(stream)
            self.destination.mkdir()
            (self.destination / "evidence").write_bytes(b"preserve")
            return checksum
        with mock.patch.object(sparse, "_hash_output", side_effect=create_destination):
            with self.assertRaisesRegex(sparse.SparseError, "appeared during"):
                self.reconstruct()
        self.assertEqual((self.destination / "evidence").read_bytes(), b"preserve")
        self.assertEqual(list(self.root.glob(".*.stage-*")), [])
        self.assertEqual(list(self.root.glob(".*.sparse.lock")), [])

    def test_insufficient_disk_space_refuses_before_creating_output(self):
        with mock.patch.object(sparse.shutil, "disk_usage", return_value=mock.Mock(free=64)):
            with self.assertRaisesRegex(sparse.SparseError, "insufficient free disk"):
                self.reconstruct()
        self.assert_no_outputs()

    def test_output_write_failure_removes_partial_staging(self):
        original = sparse._inspect
        def fail_write(entries, maximum, output=None):
            if output is not None:
                output.write(b"partial")
                raise OSError("simulated disk failure")
            return original(entries, maximum)
        with mock.patch.object(sparse, "_inspect", side_effect=fail_write):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                self.reconstruct()
        self.assert_no_outputs()

    def test_staged_output_change_during_hashing_is_rejected(self):
        original = sparse._hash_output
        def corrupt(stream):
            result = original(stream)
            stream.truncate(1)
            return result
        with mock.patch.object(sparse, "_hash_output", side_effect=corrupt):
            with self.assertRaisesRegex(sparse.SparseError, "staged output changed"):
                self.reconstruct()
        self.assert_no_outputs()

    def test_invalid_parent_hash_is_rejected_and_uppercase_is_normalized(self):
        for checksum in ("", "x" * 64, "a" * 63, None):
            with self.subTest(checksum=checksum), self.assertRaisesRegex(sparse.SparseError, "parent SHA256"):
                self.reconstruct(parent_sha256=checksum)
            self.assert_no_outputs()
        result = self.reconstruct(parent_sha256=self.parent_sha256.upper())
        self.assertEqual(result["receipt"]["parent_package_sha256"], self.parent_sha256)

    def test_cli_inspect_and_reconstruct_emit_json(self):
        for operation in ("inspect", "reconstruct"):
            args = [operation, "--expected-pieces", "2", *map(str, reversed(self.paths))]
            if operation == "reconstruct":
                args += ["--output-dir", str(self.destination), "--parent-sha256", self.parent_sha256]
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = sparse.main(args)
            self.assertEqual(status, 0)
            report = json.loads(stdout.getvalue())
            self.assertEqual(report.get("receipt", report)["piece_count"], 2)

    def test_cli_errors_are_nonzero_without_success_json(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = sparse.main(["inspect", "--expected-pieces", "2", str(self.first)])
        self.assertEqual(status, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("expected 2 pieces", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

"""Offline EROFS workflow tests; every dump.erofs subprocess is mocked."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import erofs_inventory as erofs


def metadata(path, nid, kind="regular", size=0):
    category = "regular file" if kind == "regular" else "directory"
    return (f"Path : {path}\nSize: {size}  On-disk size: {size}  {category}\n"
            f"NID: {nid}   Links: 1   Layout: 2   Compression ratio: 100.00%\n"
            "Inode size: 32   Xattr size: 16\nUid: 0   Gid: 2000  Access: 0644/rw-r--r--\n"
            "Timestamp: 2009-01-01 00:00:00.000000000\n")


def listing(path, nid, parent, entries):
    rows = [(nid, 2, "."), (parent, 2, ".."), *entries]
    return (metadata(path, nid, "directory", 64) + "\n       NID TYPE  FILENAME\n"
            + "".join(f"{child:10d} {kind:4d}  {name}\n" for child, kind, name in rows))


class FakeProcess:
    """Real small pipes exercise the bounded reader without running a process."""
    def __init__(self, stdout=b"", stderr=b"", status=0, hold=False):
        self.returncode = None
        self.status = status
        self.killed = False
        self.writers = []
        self.stdout = self.pipe(stdout, hold)
        self.stderr = self.pipe(stderr, hold)

    def pipe(self, data, hold):
        reader, writer = os.pipe()
        if data:
            os.write(writer, data)
        if hold:
            self.writers.append(writer)
        else:
            os.close(writer)
        return os.fdopen(reader, "rb")

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = self.status
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9
        for writer in self.writers:
            os.close(writer)
        self.writers.clear()


class ErofsInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "artifacts").mkdir()
        (self.root / "evidence").mkdir()
        self.image = self.root / "evidence" / "source.img"
        self.image.write_bytes(b"synthetic EROFS image; subprocesses are mocked")
        self.sha = hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.tool = self.root / "installed" / "dump.erofs"
        self.tool.parent.mkdir()
        self.tool.write_bytes(b"trusted installed tool fixture, never executed")
        self.tool.chmod(0o755)
        self.scan_dir = self.root / "artifacts" / "scan"
        self.capture_dir = self.root / "artifacts" / "capture"
        self.listings = {
            1: listing("/", 1, 1, [(2, 2, "etc"), (3, 1, "Foo"), (4, 1, "foo"),
                                     (5, 7, "link"), (6, 5, "pipe"), (7, 1, "empty")]),
            2: listing("/etc", 2, 1, [(8, 1, "file.txt"), (9, 7, "escape")]),
        }
        self.file_data = {3: b"UPPER", 4: b"lower", 7: b"", 8: b"configuration"}
        self.file_paths = {3: "/Foo", 4: "/foo", 7: "/empty", 8: "/etc/file.txt"}
        self.commands = []
        self.processes = []
        self.overrides = {}
        self.enterContext(mock.patch.object(erofs, "WORKSPACE_ROOT", self.root))
        self.enterContext(mock.patch.object(erofs, "DEFAULT_TOOL", self.tool))
        self.popen = self.enterContext(mock.patch.object(erofs.subprocess, "Popen", side_effect=self.spawn))

    def spawn(self, command, **options):
        self.commands.append(command)
        self.assertEqual(command[0], str(self.tool.resolve()))
        self.assertNotIn("shell", options)
        self.assertEqual(options["stdin"], subprocess.DEVNULL)
        self.assertEqual(options["stdout"], subprocess.PIPE)
        self.assertEqual(options["stderr"], subprocess.PIPE)
        self.assertEqual(options["env"], {"LC_ALL": "C", "LANG": "C", "TZ": "UTC", "PATH": "/usr/bin:/bin"})
        arguments = command[1:]
        if arguments == ["--version"]:
            self.assertEqual(options["pass_fds"], ())
            key, payload = "version", erofs.TOOL_VERSION + "\n"
        else:
            self.assertEqual(len(options["pass_fds"]), 1)
            descriptor = options["pass_fds"][0]
            self.assertEqual(arguments[-1], f"/dev/fd/{descriptor}")
            self.assertEqual(os.fstat(descriptor).st_ino, self.image.stat().st_ino)
            self.assertNotIn(str(self.image), command)
            arguments = arguments[:-1]
            nid = int(next((arg[6:] for arg in arguments if arg.startswith("--nid=")), "1"))
            if "--ls" in arguments:
                key, payload = ("ls", nid), self.listings[nid]
            elif "--cat" in arguments:
                key, payload = ("cat", nid), self.file_data[nid]
            else:
                self.assertEqual(arguments, [f"--nid={nid}"])
                key = ("info", nid)
                payload = metadata(self.file_paths[nid], nid, size=len(self.file_data[nid]))
        payload = self.overrides.get(key, payload)
        if callable(payload):
            payload = payload()
        process = payload if isinstance(payload, FakeProcess) else FakeProcess(
            stdout=payload.encode() if isinstance(payload, str) else payload
        )
        self.processes.append(process)
        return process

    def scan(self, **options):
        return erofs.scan_image(self.image, **{"expected_sha256": self.sha, "output_dir": self.scan_dir, **options})

    def capture(self, **options):
        return erofs.capture_files(self.image, **{
            "expected_sha256": self.sha, "output_dir": self.capture_dir,
            "inventory_dir": self.scan_dir, "paths": ["/etc/file.txt"], **options,
        })

    def assert_no_partial(self, destination):
        self.assertFalse(os.path.lexists(destination))
        self.assertEqual(list(destination.parent.glob(f".{destination.name}.stage-*")), [])
        self.assertFalse((destination.parent / ("." + destination.name + ".erofs.lock")).exists())

    def rewrite_inventory(self, change):
        path = self.scan_dir / "inventory.json"
        inventory = json.loads(path.read_bytes())
        change(inventory)
        raw = json.dumps(inventory).encode()
        path.write_bytes(raw)
        receipt_path = self.scan_dir / "receipt.json"
        receipt = json.loads(receipt_path.read_bytes())
        receipt["inventory"]["sha256"] = hashlib.sha256(raw).hexdigest()
        receipt["inventory"]["size_bytes"] = len(raw)
        receipt["entry_count"] = len(inventory["entries"])
        receipt_path.write_text(json.dumps(receipt))

    def test_scan_preserves_image_and_records_tree_tool_and_inventory_hash(self):
        before = erofs._signature(self.image.stat())
        receipt = self.scan()
        inventory_bytes = (self.scan_dir / "inventory.json").read_bytes()
        inventory = json.loads(inventory_bytes)
        self.assertEqual(len(inventory["entries"]), 9)
        self.assertEqual(receipt["entry_count"], 9)
        self.assertEqual(receipt["image"]["sha256"], self.sha)
        self.assertEqual(receipt["tool"]["path"], str(self.tool))
        self.assertEqual(receipt["tool"]["version"], erofs.TOOL_VERSION)
        self.assertEqual(receipt["tool"]["sha256"], hashlib.sha256(self.tool.read_bytes()).hexdigest())
        self.assertEqual(receipt["inventory"]["sha256"], hashlib.sha256(inventory_bytes).hexdigest())
        self.assertEqual(json.loads((self.scan_dir / "receipt.json").read_bytes()), receipt)
        self.assertEqual(erofs._signature(self.image.stat()), before)
        self.assertFalse(receipt["symlinks_followed"])
        self.assertFalse(receipt["image_mounted"])
        self.assertFalse(receipt["origin_verified"])
        self.assertEqual(len(self.commands), 3)  # version, root, /etc; no links/files visited
        self.assertEqual({p.name for p in self.scan_dir.iterdir()}, {"inventory.json", "receipt.json"})

    def test_capture_flat_files_with_case_distinctions_empty_file_and_readback(self):
        self.scan()
        before = erofs._signature(self.image.stat())
        selected = ["/Foo", "/foo", "/etc/file.txt", "/empty"]
        receipt = self.capture(paths=selected)
        for index, (record, path, content) in enumerate(zip(receipt["files"], selected,
                                                          (b"UPPER", b"lower", b"configuration", b"")), 1):
            self.assertEqual(record["path"], path)
            self.assertEqual(record["output_path"], f"files/{index:04d}")
            copied = self.capture_dir / record["output_path"]
            self.assertEqual(copied.read_bytes(), content)
            self.assertEqual(record["sha256"], hashlib.sha256(content).hexdigest())
            self.assertTrue(record["readback_verified"])
            self.assertEqual(copied.stat().st_mode & 0o777, 0o600)
            self.assertFalse(copied.is_symlink())
        self.assertEqual(receipt["image"]["sha256"], self.sha)
        self.assertEqual(receipt["inventory_receipt_sha256"],
                         hashlib.sha256((self.scan_dir / "receipt.json").read_bytes()).hexdigest())
        self.assertEqual(erofs._signature(self.image.stat()), before)
        self.assertFalse(receipt["firmware_executed"])
        self.assertFalse(receipt["symlinks_followed"])

    def test_only_numeric_inode_arguments_are_used_for_selected_names(self):
        name = "$(touch pwned);file"
        self.listings[2] = listing("/etc", 2, 1, [(8, 1, name)])
        self.file_paths[8] = "/etc/" + name
        self.scan()
        receipt = self.capture(paths=[self.file_paths[8]])
        self.assertEqual(receipt["files"][0]["path"], self.file_paths[8])
        self.assertFalse(any(name in argument for command in self.commands for argument in command))
        self.assertFalse((self.root / "pwned").exists())

    def test_wrong_image_hash_does_not_execute_tool(self):
        with self.assertRaisesRegex(erofs.InventoryError, "SHA256 mismatch"):
            self.scan(expected_sha256="0" * 64)
        self.popen.assert_not_called()
        self.assert_no_partial(self.scan_dir)

    def test_source_symlink_nonregular_and_ancestor_symlink_are_rejected(self):
        link = self.root / "evidence" / "alias.img"
        link.symlink_to(self.image)
        for image in (link, self.image.parent):
            with self.subTest(image=image), self.assertRaises(ValueError):
                erofs.scan_image(image, expected_sha256=self.sha, output_dir=self.scan_dir)
        ancestor = self.root / "alias"
        ancestor.symlink_to(self.image.parent, target_is_directory=True)
        with self.assertRaisesRegex(erofs.InventoryError, "symlinks"):
            erofs.scan_image(ancestor / self.image.name, expected_sha256=self.sha, output_dir=self.scan_dir)
        fifo = self.root / "evidence" / "pipe.img"
        os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            erofs.scan_image(fifo, expected_sha256=self.sha, output_dir=self.scan_dir)
        self.popen.assert_not_called()

    def test_installed_tool_symlink_is_resolved_and_real_binary_is_recorded(self):
        alias = self.tool.parent / "dump-link"
        alias.symlink_to(self.tool)
        with mock.patch.object(erofs, "DEFAULT_TOOL", alias):
            receipt = self.scan()
        self.assertEqual(receipt["tool"]["requested_path"], str(alias))
        self.assertEqual(receipt["tool"]["path"], str(self.tool))

    def test_nonexecutable_tool_or_wrong_version_refuses(self):
        self.tool.chmod(0o600)
        with self.assertRaisesRegex(erofs.InventoryError, "not executable"):
            self.scan()
        self.popen.assert_not_called()
        self.tool.chmod(0o755)
        self.overrides["version"] = "dump.erofs (erofs-utils) 1.8.0\n"
        with self.assertRaisesRegex(erofs.InventoryError, "unsupported"):
            self.scan()
        self.assertEqual(len(self.commands), 1)
        self.assert_no_partial(self.scan_dir)

    def test_output_requires_private_new_directory_and_real_ancestors(self):
        with self.assertRaisesRegex(erofs.InventoryError, "private directories"):
            self.scan(output_dir=self.root / "public")
        self.scan_dir.mkdir()
        with self.assertRaisesRegex(erofs.InventoryError, "already exists"):
            self.scan()
        self.scan_dir.rmdir()
        self.scan_dir.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(erofs.InventoryError, "already exists"):
            self.scan()
        self.scan_dir.unlink()
        alias = self.root / "artifacts" / "alias"
        alias.symlink_to(self.root / "evidence", target_is_directory=True)
        with self.assertRaises(ValueError):
            self.scan(output_dir=alias / "new")
        self.assertFalse((self.root / "evidence" / "new").exists())

    def test_entry_depth_and_listing_size_bounds_fail_closed(self):
        for options in ({"max_entries": 2}, {"max_depth": 0}, {"max_depth": 1}):
            with self.subTest(options=options), self.assertRaisesRegex(erofs.InventoryError, "limit"):
                self.scan(**options)
            self.assert_no_partial(self.scan_dir)
        process = FakeProcess(stdout=b"x" * 33)
        with mock.patch.object(erofs.subprocess, "Popen", return_value=process):
            with self.assertRaisesRegex(erofs.InventoryError, "size bound"):
                erofs._run({"path": self.tool}, ["--ls"], io.BytesIO(), limit=32, timeout=1)
        self.assertTrue(process.killed)

    def test_directory_inode_loops_and_type_inconsistencies_are_rejected(self):
        for entry in ((1, 2, "loop"), (2, 2, "repeat"), (3, 7, "wrong-type")):
            original = self.listings[1]
            self.listings[1] = original + f"{entry[0]:10d} {entry[1]:4d}  {entry[2]}\n"
            with self.subTest(entry=entry), self.assertRaisesRegex(erofs.InventoryError, "loop|alias|inconsistent"):
                self.scan()
            self.assert_no_partial(self.scan_dir)
            self.listings[1] = original

    def test_directory_parent_and_requested_path_must_match(self):
        original = self.listings[2]
        bad = (listing("/etc", 2, 999, [(8, 1, "file.txt")]),
               original.replace("Path : /etc", "Path : /other"),
               original.replace("NID: 2", "NID: 999"))
        for text in bad:
            self.listings[2] = text
            with self.assertRaises(erofs.InventoryError):
                self.scan()
            self.assert_no_partial(self.scan_dir)

    def test_malformed_listing_unsafe_names_and_duplicate_components_fail(self):
        original = self.listings[1]
        bad_rows = ("garbage", "         8    0  unknown", "         8    8  unknown",
                    "         8    1  ../escape", "         8    1  sub/file", "         8    1  back\\slash",
                    "         8    1   leading", "         8    1  trailing ", "         8    1  tab\tname",
                    "         8    1  Foo", "         8    1  " + "a" * 256)
        for row in bad_rows:
            with self.subTest(row=row[:40]), self.assertRaises(erofs.InventoryError):
                erofs.parse_listing(original + row + "\n", path="/")
        for text in ("", original.replace("NID TYPE  FILENAME", "unexpected"),
                     original.replace("         1    2  ..\n", ""),
                     original.replace("Timestamp:", "Unexpected:"), original + "\n"):
            with self.assertRaises(erofs.InventoryError):
                erofs.parse_listing(text, path="/")

    def test_special_files_and_symlinks_cannot_be_captured_or_traversed(self):
        self.scan()
        count = len(self.commands)
        for path in ("/", "/etc", "/link", "/pipe", "/etc/escape", "/link/child", "/missing"):
            with self.subTest(path=path), self.assertRaisesRegex(erofs.InventoryError, "regular files"):
                self.capture(paths=[path])
            self.assert_no_partial(self.capture_dir)
        self.assertTrue(all(command[1:] == ["--version"] for command in self.commands[count:]))

    def test_empty_duplicate_and_unsafe_capture_paths_fail_before_subprocess(self):
        for paths in ([], ["/foo", "/foo"], ["foo"], ["/etc/../foo"], ["//foo"], ["/etc/"], ["/bad\nname"]):
            with self.subTest(paths=paths), self.assertRaises(erofs.InventoryError):
                self.capture(paths=paths)
        self.popen.assert_not_called()

    def test_inventory_hash_and_parent_image_are_verified(self):
        self.scan()
        inventory_path = self.scan_dir / "inventory.json"
        saved = inventory_path.read_bytes()
        inventory_path.write_bytes(saved + b" ")
        with self.assertRaisesRegex(erofs.InventoryError, "SHA256 mismatch"):
            self.capture()
        inventory_path.write_bytes(saved)
        self.image.write_bytes(b"different image")
        self.sha = hashlib.sha256(self.image.read_bytes()).hexdigest()
        with self.assertRaisesRegex(erofs.InventoryError, "different parent image"):
            self.capture()
        self.assert_no_partial(self.capture_dir)

    def test_inventory_symlinks_bad_schema_and_missing_directory_parent_fail(self):
        self.scan()
        inventory_path = self.scan_dir / "inventory.json"
        original = inventory_path.read_bytes()
        inventory_path.unlink()
        inventory_path.symlink_to(self.image)
        with self.assertRaises(ValueError):
            self.capture()
        inventory_path.unlink()
        inventory_path.write_bytes(original)
        for change in (
            lambda data: data.update(schema_version=True),
            lambda data: data["entries"].append(dict(data["entries"][0])),
            lambda data: data["entries"].append({"path": "/orphan/file", "nid": 50, "type": "regular"}),
            lambda data: data["entries"].append({"path": "/bad", "nid": True, "type": "regular"}),
        ):
            self.rewrite_inventory(change)
            with self.assertRaises(erofs.InventoryError):
                self.capture()
            inventory_path.write_bytes(original)
        self.assert_no_partial(self.capture_dir)

    def test_capture_verifies_inode_type_path_number_and_exact_metadata_shape(self):
        self.scan()
        for value in (metadata("/elsewhere", 8, size=13), metadata("/etc/file.txt", 50, size=13),
                      metadata("/etc/file.txt", 8, "directory", 13),
                      metadata("/etc/file.txt", 8, size=13) + "extra\n"):
            self.overrides[("info", 8)] = value
            with self.assertRaisesRegex(erofs.InventoryError, "does not match"):
                self.capture()
            self.assert_no_partial(self.capture_dir)
        self.assertFalse(any("--cat" in command for command in self.commands))

    def test_capture_file_and_batch_byte_limits_precede_cat(self):
        self.scan()
        for options in ({"max_file_bytes": 5}, {"max_total_bytes": 10},
                        {"paths": ["/Foo", "/foo"], "max_total_bytes": 9}):
            with self.subTest(options=options), self.assertRaisesRegex(erofs.InventoryError, "byte limit"):
                self.capture(**options)
            self.assert_no_partial(self.capture_dir)
        self.assertFalse(any("--cat" in command for command in self.commands))

    def test_capture_rejects_truncated_and_oversized_tool_streams(self):
        self.scan()
        for content, reason in ((b"short", "length differs"), (b"too much content for inode", "size bound")):
            self.overrides[("cat", 8)] = content
            with self.subTest(content=content), self.assertRaisesRegex(erofs.InventoryError, reason):
                self.capture()
            self.assert_no_partial(self.capture_dir)

    def test_capture_readback_corruption_is_detected(self):
        self.scan()
        open_regular = erofs._open_regular
        def corrupt_before_readback(path):
            if path.name == "0001":
                path.write_bytes(b"corrupted")
            return open_regular(path)
        with mock.patch.object(erofs, "_open_regular", side_effect=corrupt_before_readback):
            with self.assertRaisesRegex(erofs.InventoryError, "SHA256 mismatch"):
                self.capture()
        self.assert_no_partial(self.capture_dir)

    def test_inventory_write_readback_corruption_is_detected(self):
        open_regular = erofs._open_regular
        def corrupt_before_readback(path):
            if path.name == "inventory.json":
                path.write_bytes(b'{"changed": true}')
            return open_regular(path)
        with mock.patch.object(erofs, "_open_regular", side_effect=corrupt_before_readback):
            with self.assertRaisesRegex(erofs.InventoryError, "SHA256 mismatch"):
                self.scan()
        self.assert_no_partial(self.scan_dir)

    def test_image_changes_and_tool_changes_during_batch_are_rejected(self):
        def modify_image():
            self.image.write_bytes(b"externally changed image")
            return self.listings[1]
        self.overrides[("ls", 1)] = modify_image
        with self.assertRaisesRegex(erofs.InventoryError, "input changed"):
            self.scan()
        self.assertEqual(self.image.read_bytes(), b"externally changed image")
        self.assert_no_partial(self.scan_dir)
        self.sha = hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.overrides.clear()
        def modify_tool():
            self.tool.write_bytes(b"externally changed tool")
            return erofs.TOOL_VERSION
        self.overrides["version"] = modify_tool
        with self.assertRaisesRegex(erofs.InventoryError, "input changed"):
            self.scan()
        self.assert_no_partial(self.scan_dir)

    def test_image_is_hashed_once_per_scan_or_capture_batch(self):
        original = erofs._checked_file
        with mock.patch.object(erofs, "_checked_file", wraps=original) as checked:
            self.scan()
        self.assertEqual(sum(Path(call.args[0]) == self.image for call in checked.call_args_list), 1)
        with mock.patch.object(erofs, "_checked_file", wraps=original) as checked:
            self.capture(paths=["/Foo", "/foo", "/etc/file.txt"])
        self.assertEqual(sum(Path(call.args[0]) == self.image for call in checked.call_args_list), 1)

    def test_tool_diagnostics_nonzero_exit_and_invalid_utf8_fail_without_output(self):
        for process in (FakeProcess(stderr=b"warning"), FakeProcess(status=2), FakeProcess(stdout=b"\xff")):
            self.overrides[("ls", 1)] = process
            with self.assertRaises((erofs.InventoryError, UnicodeError)):
                self.scan()
            self.assert_no_partial(self.scan_dir)

    def test_process_timeout_and_stderr_bound_kill_and_reap(self):
        process = FakeProcess(hold=True)
        with mock.patch.object(erofs.subprocess, "Popen", return_value=process):
            with self.assertRaisesRegex(erofs.InventoryError, "timed out"):
                erofs._run({"path": self.tool}, ["--version"], io.BytesIO(), limit=10, timeout=0.01)
        self.assertTrue(process.killed)
        self.assertEqual(process.poll(), -9)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(process.stderr.closed)
        process = FakeProcess(stderr=b"x" * 65)
        with mock.patch.object(erofs, "BUFFER_SIZE", 64), \
                mock.patch.object(erofs.subprocess, "Popen", return_value=process):
            with self.assertRaisesRegex(erofs.InventoryError, "stderr exceeds"):
                erofs._run({"path": self.tool}, ["--version"], io.BytesIO(), limit=10, timeout=1)
        self.assertTrue(process.killed)

    def test_overall_batch_timeout_refuses_additional_commands(self):
        original = erofs._run
        def advance_after_version(*args, **options):
            result = original(*args, **options)
            self.enterContext(mock.patch.object(erofs.time, "monotonic", return_value=10**12))
            return result
        with mock.patch.object(erofs, "_run", side_effect=advance_after_version):
            with self.assertRaisesRegex(erofs.InventoryError, "batch timed out"):
                self.scan()
        self.assertEqual(len(self.commands), 1)
        self.assert_no_partial(self.scan_dir)

    def test_existing_lock_and_exclusive_publication_race_preserve_other_evidence(self):
        lock = self.scan_dir.parent / ".scan.erofs.lock"
        lock.write_text("existing")
        with self.assertRaises(FileExistsError):
            self.scan()
        self.assertEqual(lock.read_text(), "existing")
        lock.unlink()
        publish = erofs.publish_new_directory
        identity = []
        def race(staging, destination):
            destination.mkdir()
            identity.append(destination.stat().st_ino)
            publish(staging, destination)
        with mock.patch.object(erofs, "publish_new_directory", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.scan()
        self.assertEqual(self.scan_dir.stat().st_ino, identity[0])
        self.assertEqual(list(self.scan_dir.iterdir()), [])
        self.assertEqual(list(self.scan_dir.parent.glob(".scan.stage-*")), [])
        self.assertFalse(lock.exists())

    def test_disk_and_write_failures_clean_all_partial_output(self):
        with mock.patch.object(erofs.shutil, "disk_usage", return_value=mock.Mock(free=0)):
            with self.assertRaisesRegex(erofs.InventoryError, "insufficient free disk"):
                self.scan()
        self.assert_no_partial(self.scan_dir)
        with mock.patch.object(erofs.os, "fsync", side_effect=OSError("simulated disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                self.scan()
        self.assert_no_partial(self.scan_dir)

    def test_invalid_limits_are_rejected(self):
        for options in ({"max_entries": 0}, {"max_entries": True}, {"max_depth": -1},
                        {"timeout": 0}, {"timeout": 61}, {"batch_timeout": 3601}):
            with self.subTest(options=options), self.assertRaises(erofs.InventoryError):
                self.scan(**options)
        for options in ({"max_file_bytes": 0}, {"max_total_bytes": True}):
            with self.subTest(options=options), self.assertRaises(erofs.InventoryError):
                self.capture(**options)
        self.popen.assert_not_called()

    def test_cli_scan_capture_and_error_return_json_only_on_success(self):
        for operation, destination in (("scan", self.scan_dir), ("capture", self.capture_dir)):
            arguments = [operation, "--image", str(self.image), "--expected-sha256", self.sha,
                         "--output", str(destination)]
            if operation == "capture":
                arguments += ["--inventory", str(self.scan_dir), "--path", "/etc/file.txt"]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(erofs.main(arguments), 0)
            self.assertEqual(json.loads(output.getvalue())["receipt"]["operation"], "erofs-" + operation)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = erofs.main(["scan", "--image", str(self.image), "--expected-sha256", "0" * 64,
                                 "--output", str(self.root / "artifacts" / "bad")])
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("SHA256 mismatch", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

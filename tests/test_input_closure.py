"""Offline checks for the input-closure manifest: synthetic roots plus the real tree."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import input_closure as closure


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


class SyntheticRoot:
    """A minimal workspace with a lock, patches, authored files and one private receipt."""

    def __init__(self, root):
        self.root = Path(root)
        self.write("Makefile", "test:\n\ttrue\n")
        snapshot = "<manifest/>\n"
        self.write("research/source-snapshots/lock.xml", snapshot)
        self.write_json("config/evolution-source-lock.json", {
            "schema_version": 1,
            "manifest": {"reference": "evolution-manifest", "url": "https://example.invalid/m.git", "commit": "a" * 40},
            "repo": {"url": "https://example.invalid/repo", "commit": "b" * 40},
            "snapshot": {"path": "research/source-snapshots/lock.xml", "sha256": sha256(snapshot.encode()),
                         "bytes": len(snapshot), "project_count": 1},
        })
        self.write_json("config/sources.json", {"references": [
            {"name": "zeta", "url": "https://example.invalid/z.git", "commit": "c" * 40, "path": "upstream/z"},
            {"name": "alpha", "url": "https://example.invalid/a.git", "commit": "d" * 40, "path": "upstream/a"},
        ]})
        self.write_json("config/apple-container.json", {"image": "builder:v1", "volume": "work", "cpus": 4})
        self.write_json("containers/apple/base-image.json", {"registry": "docker.io/library/ubuntu",
                                                            "index_digest": "sha256:" + "e" * 64})
        patch_a = "--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y\n"
        self.write("patches/evolution/0001-a.patch", patch_a)
        self.write_json("patches/evolution/a.json", {"schema_version": 1, "patch": {
            "path": "patches/evolution/0001-a.patch", "sha256": sha256(patch_a.encode()), "size_bytes": len(patch_a)}})
        patch_b = "--- a\n+++ b\n@@ -1 +1 @@\n-p\n+q\n"
        self.write("patches/evolution/0002-b.patch", patch_b)
        self.write_json("patches/evolution/b.json", {"schema_version": 1, "patch": "0002-b.patch",
                                                     "patch_sha256": sha256(patch_b.encode())})
        self.write_json("patches/evolution/c.json", {"schema_version": 1, "purpose": "no patch declared"})
        self.write("device/xiaomi/nezha/BoardConfig.mk", "TARGET_ARCH := arm64\n")
        self.write("scripts/tool.py", "print('hi')\n")
        self.write("scripts/__pycache__/tool.cpython-313.pyc", "binary")
        self.write_json("artifacts/kernel-inputs/v1/receipt.json", {
            "schema_version": 1, "operation": "prepare", "file_count": 2, "total_bytes": 10,
            "files": [{"path": "kernel/Image", "sha256": "f" * 64}, {"path": "dtb/vendor.dtb", "sha256": "0" * 64}],
        })

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def write_json(self, relative, value):
        return self.write(relative, json.dumps(value, indent=1) + "\n")


class InputClosureSyntheticTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.workspace = SyntheticRoot(self.root)
        self.receipt = "artifacts/kernel-inputs/v1/receipt.json"

    def test_manifest_is_deterministic_and_never_copies_private_lists(self):
        first = closure.generate(self.root, [self.receipt])
        second = closure.generate(self.root, [self.receipt])
        self.assertEqual(first, second)
        body = {key: value for key, value in first.items() if key != "closure_sha256"}
        self.assertEqual(first["closure_sha256"], sha256(closure.canonical(body)))
        paths = [row["path"] for row in first["authored"]["files"]]
        self.assertEqual(paths, sorted(paths))
        self.assertIn("device/xiaomi/nezha/BoardConfig.mk", paths)
        self.assertIn("patches/evolution/a.json", paths)
        self.assertNotIn("scripts/__pycache__/tool.cpython-313.pyc", paths)
        self.assertNotIn("research/source-snapshots/lock.xml", paths)
        receipt = first["private_receipts"][0]
        self.assertEqual(receipt["path"], self.receipt)
        self.assertEqual(receipt["declared"], {"schema_version": 1, "operation": "prepare",
                                               "file_count": 2, "total_bytes": 10})
        self.assertEqual(receipt["inventory_rows"], 2)
        self.assertNotIn("files", receipt)
        self.assertNotIn("kernel/Image", json.dumps(first))
        self.assertEqual([item["name"] for item in first["upstream"]["references"]], ["alpha", "zeta"])
        self.assertTrue(first["upstream"]["source_lock"]["snapshot"]["verified"])
        self.assertEqual(first["environment"]["builder"], {"image": "builder:v1", "volume": "work"})
        self.assertFalse(first["scope"]["reproducibility_proven"])

    def test_both_contract_styles_bind_and_unbound_contracts_are_listed(self):
        manifest = closure.generate(self.root)
        patches = manifest["patches"]
        by_path = {row["path"]: row for row in patches["patch_files"]}
        self.assertEqual(by_path["patches/evolution/0001-a.patch"]["contracts"], ["patches/evolution/a.json"])
        self.assertEqual(by_path["patches/evolution/0002-b.patch"]["contracts"], ["patches/evolution/b.json"])
        self.assertEqual(patches["contracts_checked"], {"patches/evolution/a.json": "patches/evolution/0001-a.patch",
                                                        "patches/evolution/b.json": "patches/evolution/0002-b.patch"})
        self.assertEqual(patches["unbound_contracts"], ["patches/evolution/c.json"])

    def test_contract_hash_mismatch_and_missing_patch_fail(self):
        self.workspace.write("patches/evolution/0001-a.patch", "changed\n")
        with self.assertRaisesRegex(closure.InputClosureError, "different hash"):
            closure.generate(self.root)
        os.remove(self.root / "patches/evolution/0001-a.patch")
        with self.assertRaisesRegex(closure.InputClosureError, "not present"):
            closure.generate(self.root)

    def test_snapshot_drift_fails_instead_of_recording_the_lock(self):
        self.workspace.write("research/source-snapshots/lock.xml", "<manifest><project/></manifest>\n")
        with self.assertRaisesRegex(closure.InputClosureError, "snapshot bytes"):
            closure.generate(self.root)

    def test_symlinks_under_authored_roots_are_refused(self):
        os.symlink(self.root / "Makefile", self.root / "scripts/link.py")
        with self.assertRaisesRegex(closure.InputClosureError, "symlink"):
            closure.generate(self.root)

    def test_ignored_artifact_suffixes_are_listed_not_hashed(self):
        self.workspace.write("device/xiaomi/nezha/stray.img", "not an input")
        self.workspace.write("device/xiaomi/nezha/stray.tar.gz", "not an input")
        manifest = closure.generate(self.root)
        self.assertEqual(manifest["authored"]["excluded_ignored_files"],
                         ["device/xiaomi/nezha/stray.img", "device/xiaomi/nezha/stray.tar.gz"])
        self.assertNotIn("device/xiaomi/nezha/stray.img", [row["path"] for row in manifest["authored"]["files"]])

    def test_private_receipt_outside_workspace_or_duplicated_is_refused(self):
        outside = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        self.addCleanup(os.remove, outside.name)
        outside.write("{}")
        outside.close()
        with self.assertRaisesRegex(closure.InputClosureError, "outside the workspace"):
            closure.generate(self.root, [outside.name])
        with self.assertRaisesRegex(closure.InputClosureError, "listed twice"):
            closure.generate(self.root, [self.receipt, str(self.root / self.receipt)])

    def test_verify_reports_exact_changes_and_rejects_edited_manifests(self):
        output = self.root / "closure.json"
        code = closure.main(["generate", "--root", str(self.root), "--output", str(output),
                             "--private-receipt", self.receipt])
        self.assertEqual(code, 0)
        self.assertEqual(closure.main(["generate", "--root", str(self.root), "--output", str(output)]), 2)
        self.assertEqual(closure.main(["verify", "--root", str(self.root), "--manifest", str(output)]), 0)
        self.workspace.write("device/xiaomi/nezha/BoardConfig.mk", "TARGET_ARCH := arm64\nBOARD_X := y\n")
        self.workspace.write("scripts/new_tool.py", "pass\n")
        report = closure.verify(output, self.root)
        self.assertFalse(report["matches"])
        self.assertEqual(report["authored"]["changed"], ["device/xiaomi/nezha/BoardConfig.mk"])
        self.assertEqual(report["authored"]["added"], ["scripts/new_tool.py"])
        self.assertEqual(report["patches"], {"added": [], "removed": [], "changed": []})
        self.assertEqual(closure.main(["verify", "--root", str(self.root), "--manifest", str(output)]), 1)
        recorded = json.loads(output.read_text())
        recorded["authored"]["files"] = []
        output.write_text(json.dumps(recorded))
        with self.assertRaisesRegex(closure.InputClosureError, "edited after generation"):
            closure.verify(output, self.root)

    def test_generate_runs_no_processes(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("process dispatched")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("process dispatched")):
            closure.generate(self.root, [self.receipt])


class InputClosureWorkspaceTests(unittest.TestCase):
    """The real tree must close: every declared patch pin matches its file."""

    def test_real_workspace_closes_and_binds_every_declared_patch_contract(self):
        manifest = closure.generate(closure.ROOT)
        again = closure.generate(closure.ROOT)
        self.assertEqual(manifest["closure_sha256"], again["closure_sha256"])
        patches = manifest["patches"]
        self.assertGreaterEqual(len(patches["patch_files"]), 28 + 10)
        self.assertGreaterEqual(len(patches["contracts_checked"]), 20)
        self.assertTrue(manifest["upstream"]["source_lock"]["snapshot"]["verified"])
        self.assertEqual(manifest["upstream"]["source_lock"]["snapshot"]["project_count"], 1179)
        self.assertIn("device/xiaomi/nezha/BoardConfig.mk", [row["path"] for row in manifest["authored"]["files"]])
        self.assertEqual(manifest["authored"]["excluded_ignored_files"], [])
        self.assertEqual(manifest["environment"]["builder"]["image"], "evolution-nezha-builder:ubuntu24.04-v1")


if __name__ == "__main__":
    unittest.main()

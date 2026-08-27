"""Basic invariants for the bring-up workspace."""

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceTests(unittest.TestCase):
    def test_private_and_large_artifacts_are_ignored(self):
        paths = [
            "artifacts/stock.img", "evidence/device/identity.json",
            "reports/host.json", "sources/evolution/.repo/manifest.xml",
            "upstream/manifest/README.mkdn", ".tools/repo", "signing.pk8",
        ]
        result = subprocess.run(
            ["git", "check-ignore", "--stdin"], input="\n".join(paths) + "\n",
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertEqual(set(result.stdout.splitlines()), set(paths))

    def test_no_unverified_device_manifest_is_active(self):
        self.assertFalse((ROOT / "manifests" / "local_manifest.xml").exists())


if __name__ == "__main__":
    unittest.main()

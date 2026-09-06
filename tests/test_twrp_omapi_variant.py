"""Offline contract for the single OMAPI interface availability addition.

This checks the complete source delta. It does not execute AIDL/Soong or claim
Java/Rust recovery variants, successful native compilation, or runtime OMAPI.
"""

import hashlib
import json
from pathlib import Path
import unittest

from support import assert_frozen_owner_revision
from test_twrp_patches import hunks, SOURCE_SNAPSHOT_SHA256

ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0019-enable-omapi-interface-recovery"
PROJECT = "frameworks/base"
REVISION = "99b01a65cc4c104933788b3143285ab6bae65827"
REPOSITORY = "https://android.googlesource.com/platform/frameworks/base"
OLD_EIGHTEEN = "d4a05ca07f9102d4bf17d6a59517e7af9406a907eecd1088fd21f25ec3a7d373"
OLD_METADATA = "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22"
ENTRY_SHA256 = "dd46626667915bbb5b8395855b71841e41d912077bea00e21879e2e34268001d"
PATCH_SHA256 = "9ae3d4fffa910239f5ef8f2d5bc5581b6708372b91afa8b2155cff2c5401cdfa"
FILE = {
    "path": "omapi/aidl/Android.bp", "mode": "100644",
    "before_sha256": "5a65dfe1296c13061632d4d4daa26a087c21389751a47068e1ee057788effdd4",
    "after_sha256": "1ed6c797897e61f509e6681c0b34b17cadfdcc394fa81693b53499a36190d4f9",
    "before_git_blob": "3916bf3df73d73d3e3d4bb90a349a26b85610bc4",
    "after_git_blob": "8f3c54e5b56528f8d70bc8b709bc5157ee117fe5",
    "before_size_bytes": 1271, "after_size_bytes": 1301,
}
ADDITION = "    recovery_available: true,\n"
ANCHOR = 'aidl_interface {\n    name: "android.se.omapi",\n'
HEADER = (f"diff --git a/{FILE['path']} b/{FILE['path']}\n"
          f"index {FILE['before_git_blob']}..{FILE['after_git_blob']} 100644\n"
          f"--- a/{FILE['path']}\n+++ b/{FILE['path']}\n@@ -1,45 +1,46 @@\n")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def validate_patch(raw):
    """Constrain one whole-file hunk using the existing unified-diff reader."""
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Expected complete LF-terminated patch bytes")
    text = raw.decode("utf-8")
    parsed = list(hunks(text))
    if not text.startswith(HEADER) or len(parsed) != 1 or parsed[0][:4] != (1, 45, 1, 46):
        raise ValueError("Unreviewed path, full Git blobs, mode, or hunk coordinates")
    body = parsed[0][4]
    if len(body) != 46 or any(line[:1] not in (" ", "+") for line in body):
        raise ValueError("No removals, extra records, or malformed hunk bodies are allowed")
    if [line[1:] for line in body if line.startswith("+")] != [ADDITION]:
        raise ValueError("Only the single recovery_available true addition is allowed")
    before = "".join(line[1:] for line in body if line.startswith(" "))
    after = "".join(line[1:] for line in body)
    if (before.count(ANCHOR) != 1 or body[20] != "+" + ADDITION
            or after != before.replace(ANCHOR, ANCHOR + ADDITION, 1)):
        raise ValueError("The property must follow the exact interface name")
    for stage, data in [("before", before.encode()), ("after", after.encode())]:
        if digest(data) != FILE[stage + "_sha256"] or len(data) != FILE[stage + "_size_bytes"]:
            raise ValueError("The complete original or resulting Blueprint source changed")
    return before, after


class OmapiVariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        cls.rows = cls.series["patches"]
        cls.row = cls.rows[18]
        cls.path = ROOT / "patches/twrp" / (PATCH_ID + ".patch")
        cls.patch = cls.path.read_bytes()

    def test_historical_prefix_and_metadata_survive_future_appends(self):
        self.assertGreaterEqual(len(self.rows), 19)
        self.assertEqual(canonical(self.rows[:18]), OLD_EIGHTEEN)
        self.assertEqual(canonical({k: v for k, v in self.series.items() if k != "patches"}), OLD_METADATA)

    def test_old_payloads_and_exact_new_record(self):
        self.assertEqual(self.row["id"], PATCH_ID)
        self.assertEqual(canonical(self.row), ENTRY_SHA256)
        for row in self.rows[:19]:
            with self.subTest(patch=row["id"]):
                path = ROOT / row["patch"]
                self.assertFalse(path.is_symlink())
                self.assertEqual(digest(path.read_bytes()), row["patch_sha256"])

    def test_frozen_owner_revision(self):
        assert_frozen_owner_revision(self, self.row, PROJECT, REVISION, REPOSITORY,
                                     SOURCE_SNAPSHOT_SHA256)

    def test_fresh_file_full_identities_and_thirty_byte_delta(self):
        self.assertEqual(len(self.row["files"]), 1)
        self.assertEqual({k: self.row["files"][0][k] for k in FILE}, FILE)
        self.assertEqual(FILE["after_size_bytes"] - FILE["before_size_bytes"], len(ADDITION.encode()))
        self.assertNotIn((PROJECT, FILE["path"]), {(r["project"], f["path"])
                         for r in self.rows[:18] for f in r["files"]})

    def test_exact_payload_reconstructs_both_complete_files_and_git_blobs(self):
        self.assertEqual(len(self.patch), 1576)
        self.assertEqual(digest(self.patch), PATCH_SHA256)
        self.assertEqual(self.row["patch_sha256"], PATCH_SHA256)
        before, after = validate_patch(self.patch)
        for stage, text in [("before", before), ("after", after)]:
            raw = text.encode()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.assertEqual(blob, FILE[stage + "_git_blob"])

    def test_license_api_backends_and_original_fields_unchanged(self):
        before, after = validate_patch(self.patch)
        self.assertEqual(after.replace(ADDITION, "", 1), before)
        module = self.row["files"][0]["recovery_available_modules"][0]
        self.assertEqual((module["type"], module["name"]), ("aidl_interface", "android.se.omapi"))
        for stage, text in [("before", before), ("after", after)]:
            # This complete file ends after the module; metadata excludes final LFs.
            fragment = text[text.index(ANCHOR):].rstrip("\n")
            self.assertEqual(digest(fragment.encode()), module[stage + "_module_sha256"])
        for field in ('default_applicable_licenses: ["Android-Apache-2.0"]', 'vendor_available: true',
                      'srcs: ["android/se/omapi/*.aidl"]', 'stability: "vintf"',
                      'sdk_version: "module_current"', 'min_sdk_version: "35"',
                      '"com.android.nfcservices"', 'rust: {\n            enabled: true,',
                      'version: "1"', 'imports: []'):
            self.assertIn(field, before)
            self.assertIn(field, after)

    def test_target_omapi_and_crypto_still_disabled(self):
        board = (ROOT / "recovery/twrp/device/xiaomi/nezha/BoardConfig.mk").read_text()
        disable = "$(call soong_config_set_bool, twrpGlobalVars, include_se_omapi, false)"
        self.assertEqual(board.count(disable), 1)
        self.assertLess(board.index("include vendor/twrp/config/BoardConfigSoong.mk"), board.index(disable))
        for flag in ["TW_INCLUDE_CRYPTO", "TW_INCLUDE_CRYPTO_FBE", "TW_INCLUDE_LIBRESETPROP"]:
            self.assertIn(flag + " := false\n", board)

    def test_unreviewed_mutations_rejected_without_payload_checksum_gate(self):
        raw = self.patch
        changes = {
            "path": (b"--- a/omapi/aidl/Android.bp", b"--- a/other.bp"),
            "mode": (b" 100644\n", b" 100755\n"),
            "short_blob": (FILE["before_git_blob"].encode(), FILE["before_git_blob"][:12].encode()),
            "constructor": (b" aidl_interface {", b" cc_library {"),
            "name": (b'name: "android.se.omapi"', b'name: "other"'),
            "false": (b"+    recovery_available: true,", b"+    recovery_available: false,"),
            "duplicate": (("+" + ADDITION).encode(), ("+" + ADDITION + "+" + ADDITION).encode()),
            "moved": (("+" + ADDITION + "     vendor_available: true,\n").encode(),
                      ("     vendor_available: true,\n+" + ADDITION).encode()),
            "removal": (b"     vendor_available: true,", b"-    vendor_available: true,"),
            "api_version": (b'version: "1"', b'version: "2"'),
            "license": (b'"Android-Apache-2.0"', b'"unreviewed-license"'),
            "rust_backend": (b"             enabled: true,", b"             enabled: false,"),
            "hunk_count": (b"-1,45", b"-1,44"),
            "trailer": (raw, raw + b"GIT binary patch\n"),
        }
        for name, (old, new) in changes.items():
            with self.subTest(mutation=name):
                self.assertIn(old, raw)
                changed = raw.replace(old, new, 1)
                self.assertNotEqual(changed, raw)
                with self.assertRaises(ValueError):
                    validate_patch(changed)


if __name__ == "__main__":
    unittest.main()

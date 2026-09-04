"""Offline source-transform tests; no proprietary inputs or device required."""

import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from scripts import familyspace_privapp_permissions as family
from scripts import twrp_patch_state


ROOT = Path(__file__).resolve().parents[1]
PATCH = "patches/evolution/0024-familyspace-product-privapp-permissions.patch"
CONTRACT = "patches/evolution/familyspace-product-privapp-permissions.json"
FIXTURE = b'''<?xml version="1.0" encoding="utf-8"?>
<!-- Preserve spacing, comments, and this distinct supervision package. -->
<permissions>
    <privapp-permissions package="com.google.android.gms.supervision">
        <permission name="android.permission.MANAGE_USERS" />
    </privapp-permissions>
</permissions>
'''


class FamilySpacePrivappPermissionsTests(unittest.TestCase):
    def setUp(self):
        for target in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(target, side_effect=AssertionError("offline: " + target)))

    def test_exact_package_and_only_two_permissions_added(self):
        after = family._insert_block(FIXTURE)
        root = ET.fromstring(after)
        blocks = root.findall("privapp-permissions")
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[1].attrib, {"package": "com.google.android.apps.pixel.familyspace"})
        self.assertEqual([(node.tag, node.attrib) for node in blocks[1]], [
            ("permission", {"name": "android.permission.GET_ACCOUNTS_PRIVILEGED"}),
            ("permission", {"name": "android.permission.WRITE_SECURE_SETTINGS"}),
        ])
        self.assertTrue(all(not list(node) for node in blocks[1]))

    def test_every_existing_byte_and_distinct_supervision_block_preserved(self):
        after = family._insert_block(FIXTURE)
        self.assertEqual(after[:-len(family.END) - len(family.BLOCK)], FIXTURE[:-len(family.END)])
        self.assertEqual(after[-len(family.END):], family.END)
        self.assertEqual(after.replace(family.BLOCK, b"", 1), FIXTURE)
        self.assertEqual(after.count(b'package="com.google.android.gms.supervision"'), 1)
        self.assertEqual(len(after) - len(FIXTURE), 248)

    def test_existing_empty_target_is_rejected(self):
        existing = FIXTURE.replace(b"</permissions>",
            b'<privapp-permissions package="com.google.android.apps.pixel.familyspace"/>\n</permissions>')
        with self.assertRaisesRegex(ValueError, "already present"):
            family._insert_block(existing)

    def test_duplicate_application_and_duplicate_target_blocks_rejected(self):
        after = family._insert_block(FIXTURE)
        for source in (after, after.replace(family.BLOCK, family.BLOCK * 2)):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "already present"):
                family._insert_block(source)

    def test_duplicate_unrelated_package_is_rejected(self):
        duplicate = FIXTURE.replace(b"</permissions>",
            b'<privapp-permissions package="com.google.android.gms.supervision"/>\n</permissions>')
        with self.assertRaisesRegex(ValueError, "duplicate package"):
            family._insert_block(duplicate)

    def test_nested_target_and_wrong_xml_structure_rejected(self):
        mutations = (
            FIXTURE.replace(b'<permission name="android.permission.MANAGE_USERS" />',
                            b'<privapp-permissions package="nested"/>'),
            FIXTURE.replace(b"<permissions>", b'<permissions package="root">'),
            FIXTURE.replace(b"privapp-permissions", b"permissions-for-app"),
            FIXTURE.replace(b'package="com.google.android.gms.supervision"', b'package=""'),
            b"<permissions>\n</permissions>\n</permissions>\n",
        )
        for source in mutations:
            with self.subTest(source=source), self.assertRaises(ValueError):
                family._insert_block(source)

    def test_incomplete_normalized_or_non_utf8_source_rejected(self):
        mutations = (
            FIXTURE[:-1], FIXTURE + b"\n", FIXTURE.replace(b"\n", b"\r\n"),
            FIXTURE.replace(b"Preserve", b"\xff"), FIXTURE.replace(b"Preserve", b"\0"),
            FIXTURE.decode(), bytearray(FIXTURE),
        )
        for source in mutations:
            with self.subTest(source=source), self.assertRaises(ValueError):
                family._insert_block(source)

    def test_dtd_and_entity_declarations_rejected(self):
        for declaration in (b'<!DOCTYPE permissions []>\n', b'<!ENTITY injected "value">\n'):
            source = FIXTURE.replace(b"<permissions>", declaration + b"<permissions>")
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                family._insert_block(source)

    def test_public_entrypoints_reject_unpinned_valid_xml(self):
        for source in (FIXTURE, family._insert_block(FIXTURE), FIXTURE + b"\n"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "preimage differs"):
                    family.derive(source)
                with self.assertRaisesRegex(ValueError, "postimage differs"):
                    family.reverse(source)

    def test_public_entrypoints_reject_non_bytes(self):
        for function in (family.derive, family.reverse):
            for source in (None, FIXTURE.decode(), bytearray(FIXTURE)):
                with self.subTest(function=function, source=source), self.assertRaises(ValueError):
                    function(source)

    def test_patch_contains_only_fixed_addition_and_no_removed_lines(self):
        patch = (ROOT / PATCH).read_bytes()
        header, hunk = patch.split(b"@@ -1041,4 +1041,9 @@\n")
        self.assertEqual(header, (
            f"diff --git a/{family.SOURCE_PATH} b/{family.SOURCE_PATH}\n"
            f'index {family.BEFORE["git_blob"]}..{family.AFTER["git_blob"]} 100644\n'
            f"--- a/{family.SOURCE_PATH}\n+++ b/{family.SOURCE_PATH}\n"
        ).encode())
        self.assertFalse(any(line.startswith(b"-") for line in hunk.splitlines()))
        self.assertEqual(b"".join(line[1:] for line in hunk.splitlines(keepends=True)
                                  if line.startswith(b"+")), family.BLOCK)
        self.assertNotIn(b"\r", patch)
        self.assertLess(len(patch), 1024)

    def test_contract_pins_full_source_pair_mode_and_patch(self):
        record = json.loads((ROOT / CONTRACT).read_bytes())
        patch = (ROOT / PATCH).read_bytes()
        self.assertEqual(record["patch"], PATCH)
        self.assertEqual((record["patch_sha256"], record["patch_size_bytes"]),
                         (hashlib.sha256(patch).hexdigest(), len(patch)))
        self.assertEqual(record["files"], [{
            "path": family.SOURCE_PATH, "mode": "100644", "line_endings": "LF",
            **{"before_" + key: value for key, value in family.BEFORE.items()},
            **{"after_" + key: value for key, value in family.AFTER.items()},
        }])
        twrp_patch_state.chain_patch_index(patch, family.SOURCE_PATH, record["files"][0], mode=0o644)
        self.assertEqual(record["package"], family.PACKAGE)
        self.assertEqual(record["permissions_added"], list(family.PERMISSIONS))

    def test_project_origin_and_revision_match_pinned_manifest(self):
        record = json.loads((ROOT / CONTRACT).read_bytes())
        snapshot = record["source_snapshot"]
        raw = (ROOT / snapshot["path"]).read_bytes()
        self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw)),
                         (snapshot["sha256"], snapshot["size_bytes"]))
        manifest = ET.fromstring(raw)
        projects = [p for p in manifest.findall("project") if p.get("path") == "vendor/gms"]
        self.assertEqual(len(projects), 1)
        project = projects[0]
        self.assertEqual((record["base_commit"], project.get("revision")),
                         ("89c3940a77298c204c55a21efded92ddafb59fe9",) * 2)
        self.assertEqual((record["branch"], project.get("upstream")), ("bka", "refs/heads/bka"))
        remotes = [r for r in manifest.findall("remote") if r.get("name") == project.get("remote")]
        self.assertEqual(len(remotes), 1)
        self.assertEqual(remotes[0].get("fetch").rstrip("/") + "/" + project.get("name"), record["origin"])

    def test_preparation_does_not_claim_installation_build_or_boot(self):
        record = json.loads((ROOT / CONTRACT).read_bytes())
        self.assertEqual(record["status"], "tested_source_patch_not_installed")
        self.assertTrue(all(value is False for value in record["preparation_limits"].values()))
        self.assertEqual(record["retained_module_settings"], {
            "LOCAL_MODULE": "FamilySpacePrebuilt-v484",
            "LOCAL_SRC_FILES": "FamilySpacePrebuilt-v484.apk",
            "LOCAL_CERTIFICATE": "PRESIGNED",
            "LOCAL_PRODUCT_MODULE": "true", "LOCAL_PRIVILEGED_MODULE": "true",
        })
        self.assertEqual(record["observed_apk"]["archive_member"],
                         "PRODUCT/priv-app/FamilySpacePrebuilt-v484/FamilySpacePrebuilt-v484.apk")
        self.assertEqual(record["scope"]["changed_packages"], [family.PACKAGE])
        self.assertEqual(record["scope"]["other_package_to_preserve"], "com.google.android.gms.supervision")
        self.assertEqual(record["scope"]["permissions_removed"], [])
        for key in ("enforcement_changed", "apk_bytes_changed", "signing_changed",
                    "placement_changed", "selinux_changed", "recovery_changed", "page_size_changed"):
            self.assertIs(record["scope"][key], False)


if __name__ == "__main__":
    unittest.main()

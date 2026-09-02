"""Current checksum install-mode tests using the existing inert metadata fixture.

The real host and self-contained native install functions perform their mode
checks and atomic publication. Only current-policy receipt selection/reporting
is isolated; source and image verification uses the existing fixture verifier.
These tests do not execute Android tools or claim a packaged ROM.
"""

from pathlib import Path
import unittest
from unittest import mock

from scripts import target_files_metadata as legacy
from scripts import target_files_metadata_checksum as checksum
from tests import test_target_files_metadata as fixtures


class ChecksumInstallModeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TargetFilesMetadataTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.fixture.stage()
        controls = {name: (checksum.ROOT / name).read_bytes() for name in checksum.CONTROL_TOOLS}
        payload = checksum.runtime_tool_payloads(controls)["tools/target_files_metadata.py"]
        self.native = {"__name__": "isolated_checksum_mode_test",
                       "__file__": str(self.fixture.root / "tools/target_files_metadata.py")}
        with mock.patch("os.open", side_effect=AssertionError("external native-runtime code read forbidden")):
            exec(compile(payload, self.native["__file__"], "exec"), self.native)
        self.assertTrue(self.native["NATIVE"])
        self.assertIs(checksum._impl["_install_impl"], checksum._install_namespace["install"])
        self.assertIs(self.native["_impl"]["_install_impl"], self.native["_install_namespace"]["install"])
        self.installers = {"host": checksum._install_namespace["install"],
                           "native": self.native["_install_namespace"]["install"]}
        self.serial = 0

    def target(self, misc):
        original = self.fixture.target_files()
        self.serial += 1
        target = self.fixture.root / ("mode-target-" + str(self.serial))
        original.rename(target)
        (target / "META/misc_info.txt").write_text(misc)
        return target

    def invoke(self, install, target):
        def select(bundle, expected_receipt):
            self.assertEqual(Path(bundle), self.fixture.bundle)
            self.assertEqual(expected_receipt, self.fixture.digest())
            return checksum.SOURCE_CONTRACT

        def verify(bundle, *, source_contract, **options):
            self.assertEqual(source_contract, checksum.SOURCE_CONTRACT)
            self.assertEqual(options["source_tree"], self.fixture.source)
            self.assertEqual(options["vendor_image"], target / "IMAGES/vendor.img")
            self.assertEqual(options["odm_image"], target / "IMAGES/odm.img")
            return legacy.verify_bundle(bundle, **options)

        def report(receipt, expected_receipt, reader):
            reader.recheck()
            return {"schema_version": 1, "operation": "inert-checksum-mode-test",
                    "bundle_receipt_sha256": expected_receipt, "images": receipt["images"],
                    "files": receipt["files"], "scope": receipt["scope"]}

        with mock.patch.dict(install.__globals__, verify_bundle=verify,
                             _selected_receipt_source_contract=select,
                             _delivery_installation_report=report):
            return install(self.fixture.bundle, target, expected_receipt=self.fixture.digest(),
                           source_tree=self.fixture.source)

    def assert_unpublished(self, target):
        for name in ("VENDOR", "ODM", "META/nezha_target_files_metadata.json"):
            self.assertFalse((target / name).exists(), name)

    def test_only_two_exact_get_defaults_change_in_current_host_and_native_source(self):
        before = checksum._old._v2._install_source
        expected = before
        for key in ("building_vendor_image", "building_odm_image"):
            old = 'fields.get("' + key + '")'
            self.assertEqual(before.count(old), 1)
            expected = expected.replace(old, 'fields.get("' + key + '", "")')
        self.assertEqual(checksum._install_source, expected)
        self.assertEqual(self.native["_install_source"], expected)
        self.assertEqual(checksum._old._v2._install_source, before)
        self.assertEqual(self.native["_old"]._v2._install_source, before)
        self.assertEqual(checksum.identity(self.native["_CHECKSUM_PREDECESSOR_PAYLOAD"]),
                         checksum.PREDECESSOR_RUNTIME_ID)

    def test_missing_duplicate_or_already_changed_source_boundary_is_refused(self):
        source = checksum._old._v2._install_source
        for key in ("building_vendor_image", "building_odm_image"):
            old = 'fields.get("' + key + '")'
            for changed in (source.replace(old, "None"), source + "\n# " + old,
                            source.replace(old, 'fields.get("' + key + '", "")')):
                with self.subTest(key=key, changed=changed[-80:]):
                    with self.assertRaisesRegex(checksum.TargetFilesMetadataError, "source boundary"):
                        checksum._current_install_source(changed)

    def test_explicit_empty_or_omitted_prebuilt_flags_install_without_changing_images(self):
        for runtime, install in self.installers.items():
            for present in ((), ("vendor",), ("odm",), ("vendor", "odm")):
                with self.subTest(runtime=runtime, present=present):
                    misc = "ab_update=true\nvintf_enforce=true\n" + "".join(
                        "building_" + name + "_image=\n" for name in present)
                    target = self.target(misc)
                    self.invoke(install, target)
                    self.assertTrue((target / "META/nezha_target_files_metadata.json").is_file())
                    for partition, image in self.fixture.images.items():
                        self.assertEqual((target / "IMAGES" / (partition + ".img")).read_bytes(),
                                         image.read_bytes())
                    for partition, files in self.fixture.payloads.items():
                        for path, raw in files.items():
                            self.assertEqual((target / (partition.upper() + path)).read_bytes(), raw)

    def test_explicit_nonempty_build_flags_remain_rejected(self):
        for runtime, install in self.installers.items():
            target = self.target("")
            for partition in ("vendor", "odm"):
                for value in ("true", "false", "0", "1", "TRUE", " ", "\t", "false ", "broken=value"):
                    with self.subTest(runtime=runtime, partition=partition, value=value):
                        (target / "META/misc_info.txt").write_text(
                            "ab_update=true\nvintf_enforce=true\nbuilding_" + partition + "_image=" + value + "\n")
                        with self.assertRaisesRegex(ValueError, "native target-files mode differs"):
                            self.invoke(install, target)
                        self.assert_unpublished(target)

    def test_omitted_build_flags_do_not_relax_ab_vintf_or_duplicate_key_checks(self):
        original = "ab_update=true\nvintf_enforce=true\n"
        for runtime, install in self.installers.items():
            target = self.target("")
            for key in ("ab_update", "vintf_enforce"):
                for value in (None, "", "false", "TRUE", "true "):
                    with self.subTest(runtime=runtime, key=key, value=value):
                        replacement = "" if value is None else key + "=" + value + "\n"
                        (target / "META/misc_info.txt").write_text(original.replace(key + "=true\n", replacement))
                        with self.assertRaisesRegex(ValueError, "native target-files mode differs"):
                            self.invoke(install, target)
                        self.assert_unpublished(target)
            for extra, error in (("allow_non_ab=true\n", "native target-files mode differs"),
                                 ("ab_update=true\n", "duplicate misc_info field"),
                                 ("vintf_enforce=false\n", "duplicate misc_info field")):
                (target / "META/misc_info.txt").write_text(original + extra)
                with self.subTest(runtime=runtime, extra=extra), self.assertRaisesRegex(ValueError, error):
                    self.invoke(install, target)
                self.assert_unpublished(target)

    def test_omitted_build_flags_still_verify_source_and_both_images_before_publication(self):
        for runtime, install in self.installers.items():
            target = self.target("ab_update=true\nvintf_enforce=true\n")
            for path in (self.fixture.source / legacy.CORE,
                         target / "IMAGES/vendor.img", target / "IMAGES/odm.img"):
                with self.subTest(runtime=runtime, path=path):
                    original = path.read_bytes()
                    path.write_bytes(original + b"unreviewed\n")
                    with self.assertRaisesRegex(legacy.TargetFilesMetadataError, "identity"):
                        self.invoke(install, target)
                    self.assert_unpublished(target)
                    path.write_bytes(original)
            self.invoke(install, target)
            self.assertTrue((target / "META/nezha_target_files_metadata.json").is_file())


if __name__ == "__main__":
    unittest.main()

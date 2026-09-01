"""Offline record joins using inert bytes, never Android images or native tools."""

import copy
import io
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import unittest
from unittest import mock

from scripts import final_apk_projection as m


class FinalApkProjectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native execution forbidden")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network forbidden")))
        self.tool = {"path": "/not-opened/dump.erofs", "requested_path": "/not-opened/bin/dump.erofs",
                     "version": m.erofs.TOOL_VERSION, **m.metadata.identity(b"inert tool identity")}
        self.inventories, self.scans, self.captures = {}, {}, {}
        self.request = {"schema_version": 1, "operation": m.OPERATION, "context": dict(m.CONTEXT),
                        "package_binding": None, "graph": {"selected_platform_install_paths": [],
                        "source_records": [self.write("graph/query.json", b'{"inert": "graph bytes only"}\n')]},
                        "partitions": {}}
        platform = {"system": "/app/Platform/Platform.apk",
                    "system_ext": "/priv-app/Extra/Nested/base.apk",
                    "product": "/app/Product/Product.apk"}
        for partition in m.PARTITIONS:
            paths = [platform[partition]] if partition in platform else []
            if partition in m.FACTORY_APPS:
                paths = [*m.FACTORY_APPS[partition], *m.FACTORY_OVERLAYS[partition]]
            self.partition(partition, {path: ("inert APK fixture " + partition + path).encode() for path in paths})
        # Real EROFS scans contain ordinary filenames not valid as Make words.
        self.inventories["system"]["entries"] += [
            {"path": "/bin", "nid": 1001, "type": "directory"},
            {"path": "/bin/[", "nid": 1002, "type": "regular"},
        ]
        self.scans["system"]["entry_count"] += 2
        self.request["graph"]["selected_platform_install_paths"] = [
            "/" + partition + path for partition, path in platform.items()]
        self.seal()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"path": name, **m.metadata.identity(data)}

    def partition(self, partition, payloads, *, image_root="/"):
        """Generate the *original* scan/capture receipt shape, including 0644."""
        image = {"path": "/not-opened/" + partition + ".img",
                 **m.metadata.identity(("inert image identity " + partition).encode())}
        directories = {"/", image_root}
        for name in payloads:
            directories.update(parent.as_posix() for parent in PurePosixPath(name).parents)
        entries = [{"path": path, "nid": index, "type": "directory"}
                   for index, path in enumerate(sorted(directories), 1)]
        next_nid = len(entries) + 1
        entries += [{"path": path, "nid": next_nid + index, "type": "regular"}
                    for index, path in enumerate(sorted(payloads))]
        self.inventories[partition] = {"schema_version": 1, "image": copy.deepcopy(image), "entries": entries}
        self.scans[partition] = {
            "schema_version": 1, "operation": "erofs-scan", "image": copy.deepcopy(image),
            "tool": copy.deepcopy(self.tool), "created_at_utc": "2000-01-01T00:00:00+00:00",
            "inventory": {}, "entry_count": len(entries), "symlinks_followed": False,
            "image_mounted": False, "origin_verified": False,
        }
        by_path = {row["path"]: row for row in entries}
        files = []
        for index, (path, data) in enumerate(sorted(payloads.items()), 1):
            output = f"files/{index:04d}"
            self.write(f"{partition}/capture-1/{output}", data)
            files.append({**by_path[path], **m.metadata.identity(data), "uid": 0, "gid": 0,
                          "mode": "0644", "output_path": output, "readback_verified": True})
        self.captures[partition] = []
        if files:
            self.captures[partition].append({
                "schema_version": 1, "operation": "erofs-capture", "image": copy.deepcopy(image),
                "tool": copy.deepcopy(self.tool), "created_at_utc": "2000-01-01T00:00:00+00:00",
                "inventory_sha256": "", "inventory_receipt_sha256": "", "files": files,
                "total_bytes": sum(row["size_bytes"] for row in files), "image_mounted": False,
                "symlinks_followed": False, "firmware_executed": False, "origin_verified": False,
            })
        exclusions = []
        for path in payloads:
            if not path.endswith(".apk"):
                continue
            if image_root != "/" and not path.startswith(image_root + "/"):
                # Deliberately invalid fixture; the production mapper must
                # refuse this APK rather than omit it or guess another root.
                continue
            runtime = "/" + partition + (path if image_root == "/" else path[len(image_root):])
            if not m.included(partition, runtime):
                exclusions.append({"image_path": path, "reason": m.exclusion_reason(partition, runtime)})
        self.request["partitions"][partition] = {
            "image": {key: image[key] for key in ("sha256", "size_bytes")}, "image_root": image_root,
            "inventory": {}, "scan_receipt": {}, "captures": [], "exclusions": exclusions,
        }

    def seal(self):
        """Rehash mutated fixtures; semantic negative tests must survive resealing."""
        for partition, choice in self.request["partitions"].items():
            choice["inventory"] = self.write(f"{partition}/scan/inventory.json",
                                              m.metadata.encoded(self.inventories[partition]))
            self.scans[partition]["inventory"] = {
                "name": "inventory.json", **{key: choice["inventory"][key] for key in ("sha256", "size_bytes")}}
            choice["scan_receipt"] = self.write(f"{partition}/scan/receipt.json",
                                                m.metadata.encoded(self.scans[partition]))
            refs = []
            for index, capture in enumerate(self.captures[partition], 1):
                capture["inventory_sha256"] = choice["inventory"]["sha256"]
                capture["inventory_receipt_sha256"] = choice["scan_receipt"]["sha256"]
                refs.append(self.write(f"{partition}/capture-{index}/receipt.json", m.metadata.encoded(capture)))
            choice["captures"] = refs
        return self.save_request()

    def save_request(self):
        self.request_ref = self.write("request.json", m.metadata.encoded(self.request))
        return self.request_ref

    def result(self, *, seal=True):
        if seal:
            self.seal()
        return m.project("request.json", expected_sha256=self.request_ref["sha256"], input_root=self.root)

    def refused(self, match, *, seal=True):
        with self.assertRaisesRegex((m.ProjectionError, m.metadata.TargetFilesMetadataError,
                                     m.erofs.InventoryError, OSError), match):
            self.result(seal=seal)

    def change_document(self, ref, mutate):
        data = json.loads((self.root / ref["path"]).read_bytes())
        mutate(data)
        updated = self.write(ref["path"], m.metadata.encoded(data))
        ref.update(updated)
        self.save_request()

    def payload_path(self, partition="system", index=0):
        return self.root / partition / "capture-1" / self.captures[partition][0]["files"][index]["output_path"]

    def test_valid_join_accounts_for_all_eight_images_and_factory_nineteen(self):
        result = self.result()
        self.assertEqual(set(m.PARTITIONS), set(result["partitions"]))
        self.assertEqual(22, result["apk_count"])
        self.assertEqual(3, len(result["planned_native_lists"]["platform"]))
        self.assertEqual(10, len(result["planned_native_lists"]["vendor"]))
        self.assertEqual(9, sum(row["exclusion_reason"] is not None for row in result["apks"]))
        for flag in m.FALSE_SCOPE:
            self.assertIs(result["scope"][flag], False, flag)
        self.assertIsNone(result["package_binding"])
        self.assertIsNone(result["package_name_collisions"])
        self.assertEqual("supplied-record-and-payload-join-only", result["status"])
        for partition in ("mi_ext", "system_dlkm", "vendor_dlkm"):
            self.assertEqual(1, result["partitions"][partition]["inventory_entries"])
            self.assertEqual(0, result["partitions"][partition]["apk_entries"])
        self.assertEqual(sum(row["payload"]["size_bytes"] for row in result["apks"]),
                         result["payload_bytes_rehashed"])

    def test_repeat_is_identical_and_reads_do_not_write_or_execute(self):
        before = {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.root.rglob("*") if p.is_file()}
        first, second = self.result(seal=False), self.result(seal=False)
        after = {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(m.metadata.encoded(first), m.metadata.encoded(second))
        self.assertEqual(before, after)

    def test_no_logical_partition_can_be_omitted(self):
        for partition in m.PARTITIONS:
            with self.subTest(partition=partition):
                choice = self.request["partitions"].pop(partition)
                self.save_request()
                self.refused("eight logical partition", seal=False)
                self.request["partitions"][partition] = choice

    def test_additional_partition_is_not_silently_admitted(self):
        self.request["partitions"]["vendor_extra"] = {}
        self.save_request()
        self.refused("eight logical partition", seal=False)

    def test_extra_three_partition_apks_are_captured_and_explicitly_excluded(self):
        for partition in ("mi_ext", "system_dlkm", "vendor_dlkm"):
            self.partition(partition, {"/app/Outside/Outside.apk": b"inert outside APK"})
        result = self.result()
        rows = [row for row in result["apks"] if row["partition"] not in m.NATIVE_PARTITIONS]
        self.assertEqual(3, len(rows))
        for row in rows:
            self.assertFalse(row["selected_native_scope"])
            self.assertEqual("outside-native-partition-scope", row["exclusion_reason"])
            self.assertIsNone(row["planned_native_path"])
            self.assertEqual(b"inert outside APK", (self.root / row["payload"]["path"]).read_bytes())
        self.assertEqual(13, sum(map(len, result["planned_native_lists"].values())))

    def test_extra_partition_apk_without_exclusion_is_refused(self):
        self.partition("mi_ext", {"/app/Outside/Outside.apk": b"inert"})
        self.request["partitions"]["mi_ext"]["exclusions"] = []
        self.refused("out-of-scope APK")

    def test_extra_partition_apk_without_capture_is_refused(self):
        self.partition("vendor_dlkm", {"/Outside.apk": b"inert"})
        self.captures["vendor_dlkm"] = []
        self.refused("captured regular payload")

    def test_framework_and_other_apks_are_accounted_not_native_selected(self):
        self.partition("system", {"/app/Platform/Platform.apk": b"inert app",
                                  "/framework/framework-res.apk": b"inert framework",
                                  "/etc/security/fsverity/Certificate.apk": b"inert certificate"})
        rows = [row for row in self.result()["apks"] if row["partition"] == "system"]
        self.assertEqual({"framework-path-outside-app-scope", "other-path-outside-app-scope", None},
                         {row["exclusion_reason"] for row in rows})
        self.assertEqual(1, sum(row["selected_native_scope"] for row in rows))

    def test_empty_one_platform_partition_requires_real_inventory_structure(self):
        self.partition("system_ext", {})
        self.request["graph"]["selected_platform_install_paths"].remove("/system_ext/priv-app/Extra/Nested/base.apk")
        self.assertEqual(0, self.result()["partitions"]["system_ext"]["apk_entries"])

    def test_empty_graph_cannot_create_an_empty_success(self):
        self.request["graph"]["selected_platform_install_paths"] = []
        self.refused("nonempty platform graph")

    def test_apex_contents_remain_an_explicit_missing_gate(self):
        entries = self.inventories["system"]["entries"]
        entries += [{"path": "/apex", "nid": 1100, "type": "directory"},
                    {"path": "/apex/inert.apex", "nid": 1101, "type": "regular"}]
        self.scans["system"]["entry_count"] = len(entries)
        result = self.result()
        self.assertIn("apex-contained-apk-accounting", result["missing_admission_roles"])
        self.assertFalse(result["scope"]["complete_installed_apk_inventory_verified"])
        self.assertFalse(result["scope"]["apex_contained_apks_verified"])

    def test_make_nested_app_path_keeps_original_basename(self):
        row = next(row for row in self.result()["apks"] if row["partition"] == "system_ext")
        self.assertEqual("base.apk", PurePosixPath(row["planned_native_path"]).name)
        self.assertEqual("0001", PurePosixPath(row["payload"]["path"]).name)
        self.assertEqual("/nezha-final-apk-projection/system_ext/priv-app/Extra/Nested/base.apk",
                         row["planned_native_path"])

    def test_duplicate_basenames_and_equal_bytes_are_never_deduplicated(self):
        self.partition("product", {"/app/One/base.apk": b"same inert bytes",
                                   "/priv-app/Two/base.apk": b"same inert bytes"})
        selected = self.request["graph"]["selected_platform_install_paths"]
        selected.remove("/product/app/Product/Product.apk")
        selected += ["/product/app/One/base.apk", "/product/priv-app/Two/base.apk"]
        result = self.result()
        self.assertEqual(["/product/app/One/base.apk", "/product/priv-app/Two/base.apk",
                          "/system_ext/priv-app/Extra/Nested/base.apk"], result["basename_collisions"]["base.apk"])
        self.assertEqual(4, len(result["planned_native_lists"]["platform"]))
        self.assertIsNone(result["package_name_collisions"])

    def test_explicit_system_root_maps_once(self):
        self.partition("system", {"/system/app/Platform/Platform.apk": b"inert app"}, image_root="/system")
        row = next(row for row in self.result()["apks"] if row["partition"] == "system")
        self.assertEqual("/system/app/Platform/Platform.apk", row["runtime_install_path"])
        self.assertEqual("/system/app/Platform/Platform.apk", row["image_path"])

    def test_apk_outside_explicit_system_root_is_not_dropped(self):
        self.partition("system", {"/system/app/Platform/Platform.apk": b"inert",
                                  "/Outside.apk": b"inert outside"}, image_root="/system")
        self.refused("outside the explicitly selected")

    def test_wrong_system_root_does_not_silently_strip_prefix(self):
        self.partition("system", {"/system/app/Platform/Platform.apk": b"inert"})
        self.refused("platform paths and complete supplied image APK scope differ")

    def test_non_system_partition_cannot_claim_system_root(self):
        self.request["partitions"]["product"]["image_root"] = "/system"
        self.refused("image-root mapping")

    def test_missing_selected_root_is_refused(self):
        self.request["partitions"]["system"]["image_root"] = "/system"
        self.refused("selected image root is absent")

    def test_graph_missing_or_extra_paths_fail_set_equality(self):
        original = self.request["graph"]["selected_platform_install_paths"][:]
        for value in (original[:-1], original + ["/product/app/Missing/Missing.apk"]):
            with self.subTest(value=value):
                self.request["graph"]["selected_platform_install_paths"] = value
                self.refused("platform paths and complete supplied image APK scope differ")

    def test_duplicate_graph_paths_refused(self):
        self.request["graph"]["selected_platform_install_paths"].append("/system/app/Platform/Platform.apk")
        self.refused("duplicate graph-selected")

    def test_graph_cannot_admit_vendor_or_outside_app_roots(self):
        for path in ("/vendor/app/Unknown.apk", "/system/framework/Unknown.apk", "/mi_ext/app/Unknown.apk"):
            with self.subTest(path=path):
                self.request["graph"]["selected_platform_install_paths"] = [path]
                self.refused("outside the platform")

    def test_unsafe_graph_words_are_refused(self):
        for path in ("/system/app/../x.apk", "/system//app/x.apk", "/system/app/a b.apk",
                     "/system/app/a\nb.apk", "system/app/a.apk", "/system/app/a*.apk"):
            with self.subTest(path=path):
                self.request["graph"]["selected_platform_install_paths"] = [path]
                self.refused("path|relative|selector")

    def test_graph_records_required_and_unknown_graph_claim_refused(self):
        self.request["graph"]["source_records"] = []
        self.refused("raw graph/source records")
        self.request["graph"]["graph_authenticated"] = True
        self.refused("graph selection fields differ")

    def test_changed_raw_graph_evidence_is_refused(self):
        (self.root / "graph/query.json").write_bytes(b"unreviewed graph mutation")
        self.refused("input identity differs")

    def test_package_binding_cannot_manufacture_admission(self):
        self.request["package_binding"] = {"operation": "package2", "success": True}
        self.refused("actual package admission is not implemented")

    def test_wrong_context_or_boolean_numbers_are_refused(self):
        for field, value in (("page_size_bytes", 16384), ("page_size_bytes", True),
                             ("branch", "newer"), ("variant", "userdebug")):
            with self.subTest(field=field, value=value):
                self.request["context"] = {**m.CONTEXT, field: value}
                self.refused("only the Nezha")

    def test_unknown_top_level_readiness_claim_is_refused(self):
        self.request["complete_rom_ready"] = True
        self.refused("request fields differ")

    def test_changed_inventory_bytes_are_refused(self):
        (self.root / "system/scan/inventory.json").write_bytes(b"{}")
        self.refused("input identity differs", seal=False)

    def test_inventory_scan_capture_and_selected_image_must_agree(self):
        for role in ("inventory", "scan", "capture", "choice"):
            with self.subTest(role=role):
                target = {"inventory": self.inventories["system"], "scan": self.scans["system"],
                          "capture": self.captures["system"][0], "choice": self.request["partitions"]["system"]}[role]
                old = target["image"]["sha256"]
                target["image"]["sha256"] = "f" * 64
                self.refused("image identity differs|capture image")
                target["image"]["sha256"] = old

    def test_recorded_image_and_tool_paths_are_not_opened(self):
        self.assertFalse(Path("/not-opened/system.img").exists())
        result = self.result()
        self.assertFalse(result["scope"]["image_bytes_rehashed"])
        self.assertFalse(result["scope"]["native_tool_authenticated"])

    def test_scan_inventory_hash_and_size_must_bind_exact_bytes(self):
        choice = self.request["partitions"]["system"]
        for field, value in (("sha256", "f" * 64), ("size_bytes", 1)):
            with self.subTest(field=field):
                self.seal()
                self.change_document(choice["scan_receipt"], lambda doc: doc["inventory"].update({field: value}))
                self.refused("exact full inventory", seal=False)

    def test_scan_count_cannot_overstate_or_understate_inventory(self):
        self.scans["system"]["entry_count"] -= 1
        self.refused("inventory count differs")

    def test_missing_root_or_ancestor_and_duplicate_paths_refused(self):
        original = copy.deepcopy(self.inventories["system"]["entries"])
        for removed, match in (("/", "root directory missing"), ("/app/Platform", "directory ancestry")):
            with self.subTest(removed=removed):
                self.inventories["system"]["entries"] = [row for row in original if row["path"] != removed]
                self.scans["system"]["entry_count"] = len(self.inventories["system"]["entries"])
                self.refused(match)
        self.inventories["system"]["entries"] = original + [copy.deepcopy(original[-1])]
        self.scans["system"]["entry_count"] = len(original) + 1
        self.refused("duplicate path")

    def test_directory_inode_alias_is_refused(self):
        directories = [row for row in self.inventories["system"]["entries"] if row["type"] == "directory"]
        directories[1]["nid"] = directories[0]["nid"]
        self.refused("directory inode alias")

    def test_inconsistent_inode_type_is_refused(self):
        entries = self.inventories["system"]["entries"]
        regular = next(row for row in entries if row["type"] == "regular")
        regular["nid"] = next(row["nid"] for row in entries if row["type"] == "directory")
        self.refused("inconsistent inventory inode type")

    def test_non_apk_bracket_filename_is_accepted_without_make_filter(self):
        result = self.result()
        self.assertEqual(len(self.inventories["system"]["entries"]), result["partitions"]["system"]["inventory_entries"])

    def test_uppercase_apk_extension_is_refused_not_ignored(self):
        self.partition("system", {"/app/Platform/Platform.apk": b"inert", "/overlay/Unknown.APK": b"inert"})
        self.refused("noncanonical APK suffix")

    def test_nonregular_apk_is_refused_even_when_excluded(self):
        path = m.FACTORY_OVERLAYS["vendor"][0]
        entry = next(row for row in self.inventories["vendor"]["entries"] if row["path"] == path)
        entry["type"] = "symlink"
        self.refused("inventoried regular inode")

    def test_factory_missing_added_or_same_count_renamed_apk_refused(self):
        original = {path: b"inert" for path in (*m.FACTORY_APPS["odm"], *m.FACTORY_OVERLAYS["odm"])}
        for mutation in ("missing", "additional", "renamed"):
            with self.subTest(mutation=mutation):
                payloads = dict(original)
                if mutation != "additional":
                    del payloads[m.FACTORY_APPS["odm"][0]]
                if mutation != "missing":
                    payloads["/app/Unknown/Unknown.apk"] = b"inert"
                self.partition("odm", payloads)
                self.refused("retained factory APK paths changed")

    def test_factory_inode_numbers_may_change_with_explicit_final_derivation(self):
        for entry in self.inventories["vendor"]["entries"]:
            entry["nid"] += 12345
        for row in self.captures["vendor"][0]["files"]:
            row["nid"] += 12345
        self.assertEqual(16, self.result()["partitions"]["vendor"]["apk_entries"])

    def test_missing_overlay_exclusion_is_refused(self):
        self.request["partitions"]["vendor"]["exclusions"].pop()
        self.refused("exact explicit exclusion")

    def test_wrong_overlay_exclusion_reason_is_refused(self):
        self.request["partitions"]["vendor"]["exclusions"][0]["reason"] = "opaque-vendor-exemption"
        self.refused("exact explicit exclusion")

    def test_excluding_in_scope_apk_is_refused(self):
        self.request["partitions"]["system"]["exclusions"] = [
            {"image_path": "/app/Platform/Platform.apk", "reason": "overlay-path-outside-app-scope"}]
        self.refused("in-scope APK cannot be excluded")

    def test_duplicate_or_unused_exclusion_is_refused(self):
        exclusions = self.request["partitions"]["vendor"]["exclusions"]
        exclusions.append(copy.deepcopy(exclusions[0]))
        self.refused("duplicate or nonexistent APK exclusion")
        exclusions[-1]["image_path"] = "/overlay/Missing.apk"
        self.refused("duplicate or nonexistent APK exclusion")

    def test_missing_vendor_and_excluded_overlay_payloads_are_refused(self):
        for partition in ("vendor", "odm"):
            with self.subTest(partition=partition):
                captures = self.captures[partition]
                self.captures[partition] = []
                self.refused("captured regular payload")
                self.captures[partition] = captures

    def test_capture_inventory_scan_hashes_cannot_be_resealed_to_another_record(self):
        for field in ("inventory_sha256", "inventory_receipt_sha256"):
            with self.subTest(field=field):
                self.seal()
                ref = self.request["partitions"]["system"]["captures"][0]
                self.change_document(ref, lambda doc: doc.update({field: "e" * 64}))
                self.refused("capture image, scan, inventory or producer", seal=False)

    def test_mixed_scan_producer_identity_is_refused(self):
        self.scans["vendor_dlkm"]["tool"]["sha256"] = "f" * 64
        self.refused("mixed EROFS producer")

    def test_capture_tool_identity_must_match_its_scan(self):
        self.captures["system"][0]["tool"]["sha256"] = "f" * 64
        self.refused("capture image, scan, inventory or producer")

    def test_unsupported_tool_version_is_refused(self):
        self.scans["system"]["tool"]["version"] = "unreviewed newer version"
        self.refused("unsupported EROFS receipt producer")

    def test_receipt_operation_schema_and_scope_cannot_claim_native_success(self):
        target = self.captures["system"][0]
        for key, value, match in (("schema_version", True, "wrong capture operation"),
                                  ("operation", "erofs-scan", "wrong capture operation"),
                                  ("origin_verified", True, "capture scope differs"),
                                  ("image_mounted", 0, "capture scope differs"),
                                  ("firmware_executed", True, "capture scope differs")):
            with self.subTest(key=key):
                original = target[key]
                target[key] = value
                self.refused(match)
                target[key] = original

    def test_utc_timestamp_is_required_without_claiming_freshness(self):
        for value in ("2026-09-01T12:00:00", "2026-09-01T12:00:00-04:00", "not-a-time"):
            with self.subTest(value=value):
                self.scans["system"]["created_at_utc"] = value
                self.refused("timestamp")

    def test_capture_inode_metadata_must_match_inventory(self):
        self.captures["system"][0]["files"][0]["nid"] += 10000
        self.refused("inventoried regular inode")

    def test_capture_uses_permission_mode_not_full_stat_mode(self):
        row = self.captures["system"][0]["files"][0]
        self.assertEqual("0644", row["mode"])
        self.result()
        for mode in ("100644", "0648", "644", 420):
            with self.subTest(mode=mode):
                row["mode"] = mode
                self.refused("capture permission mode")

    def test_boolean_uid_size_and_count_are_refused(self):
        row = self.captures["system"][0]["files"][0]
        for key in ("uid", "gid", "size_bytes", "nid"):
            with self.subTest(key=key):
                value = row[key]
                row[key] = True
                self.refused("invalid|size|identity")
                row[key] = value
        self.scans["system"]["entry_count"] = True
        self.refused("invalid entry count")

    def test_capture_readback_and_exact_numeric_sequence_are_required(self):
        row = self.captures["system"][0]["files"][0]
        for key, value in (("readback_verified", 1), ("readback_verified", False),
                           ("output_path", "files/0000"), ("output_path", "files/Platform.apk"),
                           ("output_path", "../payload.apk")):
            with self.subTest(key=key, value=value):
                original = row[key]
                row[key] = value
                self.refused("exact original output/readback")
                row[key] = original

    def test_total_bytes_includes_all_captured_records(self):
        self.captures["system"][0]["total_bytes"] += 1
        self.refused("capture total_bytes differs")

    def test_empty_apk_is_refused(self):
        self.partition("system", {"/app/Platform/Platform.apk": b""})
        self.refused("empty input identity")

    def test_zero_length_ancillary_capture_is_allowed_and_rehashed(self):
        self.partition("mi_ext", {"/etc/selinux/ancillary_contexts": b""})
        result = self.result()
        self.assertEqual(1, result["partitions"]["mi_ext"]["captured_files_rehashed"])
        self.assertEqual(0, result["partitions"]["mi_ext"]["apk_entries"])

    def test_non_apk_capture_rows_are_not_an_unhashed_escape(self):
        self.partition("system", {"/app/Platform/Platform.apk": b"inert APK", "/etc/context": b"inert context"})
        result = self.result()
        self.assertEqual(2, result["partitions"]["system"]["captured_files_rehashed"])
        self.assertGreater(result["payload_bytes_rehashed"], sum(row["payload"]["size_bytes"] for row in result["apks"]))
        self.payload_path(index=1).write_bytes(b"modified context")
        self.refused("input identity differs", seal=False)

    def test_duplicate_image_path_across_capture_batches_is_refused(self):
        self.captures["system"].append(copy.deepcopy(self.captures["system"][0]))
        self.refused("duplicate captured image path")

    def test_changed_apk_payload_is_refused_even_when_same_size(self):
        path = self.payload_path()
        path.write_bytes(b"x" * path.stat().st_size)
        self.refused("input identity differs", seal=False)

    def test_records_must_retain_original_adjacent_scan_filenames(self):
        choice = self.request["partitions"]["system"]
        choice["scan_receipt"]["path"] = "elsewhere/receipt.json"
        self.save_request()
        self.refused("original adjacent EROFS scan files", seal=False)

    def test_capture_must_retain_original_receipt_filename(self):
        self.request["partitions"]["system"]["captures"][0]["path"] = "system/capture-1/renamed.json"
        self.save_request()
        self.refused("original receipt.json", seal=False)

    def test_unsafe_relative_references_are_refused(self):
        row = self.request["graph"]["source_records"][0]
        for path in ("../query.json", "/tmp/query.json", "graph//query.json", "graph/a b.json", "graph/./query.json"):
            with self.subTest(path=path):
                row["path"] = path
                self.refused("relative|selector|path")

    def test_same_input_path_cannot_fill_two_roles(self):
        self.request["graph"]["source_records"] *= 2
        self.refused("input path reused")

    def test_symlink_payload_is_refused(self):
        path = self.payload_path()
        destination = path.with_name("original")
        path.rename(destination)
        path.symlink_to(destination)
        self.refused("regular single-link", seal=False)

    def test_symlink_parent_is_refused(self):
        path = self.root / "system/capture-1/files"
        destination = path.with_name("original-files")
        path.rename(destination)
        path.symlink_to(destination, target_is_directory=True)
        self.refused("directory|symlink", seal=False)

    def test_hardlink_payload_is_refused(self):
        path = self.payload_path()
        os.link(path, path.with_name("hardlink"))
        self.refused("regular single-link", seal=False)

    def test_fifo_payload_is_refused_without_opening_or_blocking(self):
        path = self.payload_path()
        path.unlink()
        os.mkfifo(path)
        self.refused("regular single-link", seal=False)

    def test_input_root_symlink_is_refused(self):
        link = self.root / "link-to-root"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(m.metadata.TargetFilesMetadataError, "directory|symlink"):
            m.project("request.json", expected_sha256=self.request_ref["sha256"], input_root=link)

    def test_final_recheck_detects_post_read_payload_mutation(self):
        original = m.metadata.Reader.recheck

        def mutate_then_recheck(reader):
            path = self.payload_path()
            path.write_bytes(b"z" * path.stat().st_size)
            return original(reader)

        with mock.patch.object(m.metadata.Reader, "recheck", mutate_then_recheck):
            self.refused("input identity differs|input changed", seal=False)

    def test_final_recheck_detects_replacement_with_identical_bytes(self):
        original = m.metadata.Reader.recheck

        def replace_then_recheck(reader):
            path = self.payload_path()
            content = path.read_bytes()
            path.rename(path.with_name("previous-inode"))
            path.write_bytes(content)
            return original(reader)

        with mock.patch.object(m.metadata.Reader, "recheck", replace_then_recheck):
            self.refused("input changed between reads", seal=False)

    def test_metadata_and_payload_aggregate_caps_are_enforced(self):
        with mock.patch.object(m, "MAX_METADATA_TOTAL", 1):
            self.refused("aggregate metadata limit", seal=False)
        with mock.patch.object(m, "MAX_PAYLOAD_TOTAL", 1):
            self.refused("aggregate payload limit", seal=False)

    def test_capture_and_apk_count_bounds_are_enforced(self):
        with mock.patch.object(m, "MAX_CAPTURES", 0):
            self.refused("invalid capture list", seal=False)
        with mock.patch.object(m, "MAX_APKS", 3):
            self.refused("APK inventory bound", seal=False)

    def test_external_request_hash_is_mandatory_and_exact(self):
        for digest in (None, "f" * 64, "F" * 64, "short"):
            with self.subTest(digest=digest):
                with self.assertRaisesRegex(m.ProjectionError, "SHA256"):
                    m.project("request.json", expected_sha256=digest, input_root=self.root)

    def test_duplicate_json_keys_cannot_be_hidden_by_rehashing(self):
        raw = b'{"schema_version":1,"schema_version":1}'
        self.request_ref = self.write("request.json", raw)
        self.refused("invalid JSON object", seal=False)

    def test_json_nan_is_not_accepted_as_evidence(self):
        self.request_ref = self.write("request.json", b'{"value":NaN}')
        self.refused("invalid JSON object", seal=False)

    def test_cli_outputs_only_unbound_json(self):
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            code = m.main(["--request", "request.json", "--expected-sha256", self.request_ref["sha256"],
                           "--input-root", str(self.root)])
        self.assertEqual(0, code)
        result = json.loads(stdout.getvalue())
        self.assertFalse(result["scope"]["package2_admitted"])
        self.assertFalse(result["scope"]["native_execution_ready"])
        self.assertFalse(result["scope"]["complete_rom_ready"])

    def test_cli_refusal_has_no_partial_success_output(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            with self.assertRaises(SystemExit) as raised:
                m.main(["--request", "request.json", "--expected-sha256", "f" * 64,
                        "--input-root", str(self.root)])
        self.assertEqual(1, raised.exception.code)
        self.assertEqual("", stdout.getvalue())
        self.assertIn("APK projection refused", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

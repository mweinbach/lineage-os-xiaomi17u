"""Pin the four-method CameraOpt port: patch 0040, its templates, stubs, contract and planner."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/nezha-cameraopt-service.json"
SERVICE_DIR = ROOT / "device/xiaomi/nezha/cameraopt-service"
SERVICE = SERVICE_DIR / "src/com/android/server/cameraopt/NezhaCameraOptService.java"
PLANNER = SERVICE_DIR / "process-policy/src/com/android/server/am/NezhaCameraReclaimPlanner.java"
POLICY = SERVICE_DIR / "process-policy/src/com/android/server/am/NezhaCameraReclaimPolicy.java"
STUB = SERVICE_DIR / "compile-stubs/com/miui/cameraopt/configs/JsonDisptcher.java"
PORTED = ("boostCameraByThreshold", "reclaimMemoryForCamera", "notifyCameraPerformanceTime",
          "updateCloudData")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ContractPinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text())

    def test_fragment_patches_and_templates_match_their_pins(self):
        c = self.contract
        rows = [(c["fragment"], c["fragment_sha256"]), (c["patch"], c["patch_sha256"]),
                (c["reclaim_patch"]["patch"], c["reclaim_patch"]["patch_sha256"])]
        rows += [(path, row["sha256"]) for path, row in c["authored_templates"].items()]
        rows += [("device/xiaomi/nezha/cameraopt-service/compile-stubs/" + rel, row["sha256"])
                 for rel, row in c["compile_stubs"].items()]
        rows += [("device/xiaomi/nezha/cameraopt-service/src/" + rel, row["sha256"])
                 for rel, row in c["service_sources"].items()]
        for path, expected in rows:
            with self.subTest(path=path):
                self.assertEqual(sha256(ROOT / path), expected)
        self.assertEqual(len(c["reclaim_patch"]["patch"]), len(c["patch"]) - len("0031-cameraopt-process-state-compat")
                         + len("0040-nezha-cameraopt-reclaim-policy"))
        self.assertEqual((ROOT / c["reclaim_patch"]["patch"]).stat().st_size,
                         c["reclaim_patch"]["patch_size_bytes"])

    def test_reclaim_patch_installs_exactly_the_authored_templates(self):
        c = self.contract
        sections = (ROOT / c["reclaim_patch"]["patch"]).read_text().split("diff --git ")[1:]
        self.assertEqual(len(sections), 3)
        added = {}
        for section in sections:
            lines = section.splitlines(keepends=True)
            header = lines[0].split()
            destination = header[1][2:]
            body = "".join(line[1:] for line in lines
                           if line.startswith("+") and not line.startswith("+++"))
            added[destination] = (body, "new file mode 100644\n" in lines)
        files = c["reclaim_patch"]["files"]
        self.assertEqual(set(added), set(files))
        for destination, (body, new_file) in added.items():
            row = files[destination]
            with self.subTest(destination=destination):
                if row["before_sha256"] is None:
                    self.assertTrue(new_file)
                    template = SERVICE_DIR / "process-policy/src" / Path(destination).relative_to(
                        "services/core/java")
                    self.assertEqual(body.encode(), template.read_bytes())
                    self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), row["after_sha256"])
                    self.assertEqual(len(body.encode()), row["after_bytes"])
                else:
                    self.assertFalse(new_file)
                    self.assertEqual(destination, "services/proguard.flags")
                    self.assertIn("-keep class com.android.server.am.NezhaCameraReclaimPolicy {", body)
                    self.assertIn("-keep class com.android.server.am.NezhaCameraReclaimPlanner {", body)
                    # The pre-image is the post-image of patch 0031.
                    self.assertEqual(row["before_sha256"],
                                     c["files"]["services/proguard.flags"]["after_sha256"])
                    self.assertEqual(row["after_bytes"],
                                     c["files"]["services/proguard.flags"]["after_bytes"]
                                     + len(body.encode()))

    def test_contract_names_the_four_methods_as_ported_and_keeps_the_rest_explicit(self):
        c = self.contract
        for method in PORTED:
            self.assertIn(method, c["implemented_request_surfaces"])
            self.assertIn(method, c["ported_app_reachable_methods"])
        self.assertEqual(c["unported_app_reachable_methods"], [])
        self.assertEqual(c["contract_id"], "nezha-cameraopt-service-v2")
        self.assertEqual(sorted(c["reclaim_helper_classes"]),
                         ["Lcom/android/server/am/NezhaCameraReclaimPlanner;",
                          "Lcom/android/server/am/NezhaCameraReclaimPolicy;"])
        for name in ("Lcom/miui/cameraopt/configs/JsonDisptcher;",
                     "Lcom/miui/cameraopt/configs/JsonDisptcher$DataCallback;",
                     "Lcom/miui/cameraopt/utils/FileUtils;"):
            self.assertIn(name, c["factory_required_classes"])
        self.assertFalse(c["runtime_stubs_permitted"])
        self.assertTrue(any("SERVICE_B_ADJ" in row for row in c["reclaim_policy_deviations"]))


class SourceShapeTests(unittest.TestCase):
    def test_service_implements_the_four_methods_and_no_longer_throws_for_them(self):
        text = SERVICE.read_text()
        for method in PORTED:
            with self.subTest(method=method):
                self.assertNotIn(f'unsupported("{method}")', text)
                self.assertIn(f'count(mCalls, "{method}")', text)
        # The zero boost level and the enabled perf watcher stay explicit unported paths.
        self.assertIn('unsupported("boostCameraByThreshold:zero")', text)
        self.assertIn('unsupported("notifyCameraPerformanceTime:watcher")', text)
        self.assertEqual(text.count("throw unsupported("), 21)  # 18 methods + 3 partial paths
        self.assertIn("JsonDisptcher.getInstance()", text)
        self.assertIn('registerDataCallback(RECLAIM_SECTION, mReclaimConfiguration)', text)
        self.assertIn("mReclaimPolicy.onCaptureReclaim(caller.uid, caller.pid, modeId, first, second)", text)
        self.assertIn("mReclaimPolicy.onModeLevel(caller.uid, caller.pid, threshold)", text)
        self.assertIn("MAX_CLOUD_CHARS = 256 * 1024", text)
        self.assertIn('CLOUD_PROPERTY_PREFIX = "persist.vendor.camera.cloud"', text)
        # The factory memory-reserve and cloud-sync classes are described, never called.
        self.assertNotIn("CameraMemReserveWatcher.getInstance", text)
        self.assertNotIn("CameraCloundSync.getInstance", text)
        self.assertNotIn("import com.miui.cameraopt.configs.CameraCloundSync", text)

    def test_stub_declares_only_the_dispatcher_surface_the_service_uses(self):
        text = STUB.read_text()
        self.assertIn("public interface DataCallback", text)
        self.assertIn("void onDataCallback(JSONObject section);", text)
        self.assertIn("void dumpConfigs();", text)
        for signature in ("public static JsonDisptcher getInstance()", "public void loadJson()",
                          "public void registerDataCallback(String key, DataCallback callback)",
                          "public boolean updateCloudData(double version, JSONObject data)"):
            self.assertIn(signature, text)
        bodies = re.findall(r"\{\s*\n\s*throw new UnsupportedOperationException", text)
        self.assertEqual(len(bodies), 6)
        self.assertNotIn("static {", text)

    def test_planner_and_policy_state_their_floor_and_bounds(self):
        planner = PLANNER.read_text()
        self.assertIn("public static final int ADJ_FLOOR = ProcessList.SERVICE_B_ADJ;", planner)
        self.assertIn("public static final int MAX_KILLS_PER_BATCH = 8;", planner)
        self.assertIn("public static final long DEFAULT_CAPTURE_INTERVAL_MS = 60000;", planner)
        for scene in ("miuicam_capture_event", "miuicam_video_switch_event", "live_motion_scene_event",
                      "200M_scene_event", "video_4k_dolby_event"):
            self.assertIn(f'"{scene}"', planner)
        self.assertNotIn("import android.", planner)
        policy = POLICY.read_text()
        self.assertIn("ApplicationExitInfo.SUBREASON_MEMORY_PRESSURE", policy)
        self.assertIn('CGROUP_RECLAIM = "/sys/fs/cgroup/memory.reclaim"', policy)
        self.assertIn("CachedAppOptimizer.CompactProfile.FULL", policy)
        self.assertNotIn("controller.isInterestingToUser()", policy)  # takes the WM lock
        self.assertIn("Debug.MEMINFO_AVAILABLE", policy)
        self.assertNotIn("/dev/memcg", policy)

    def test_generator_lists_every_new_template(self):
        sys.path.insert(0, str(ROOT))
        from scripts import generate_device_tree as generator
        for name in ("cameraopt-service/compile-stubs/com/miui/cameraopt/configs/JsonDisptcher.java",
                     "cameraopt-service/process-policy/src/com/android/server/am/NezhaCameraReclaimPlanner.java",
                     "cameraopt-service/process-policy/src/com/android/server/am/NezhaCameraReclaimPolicy.java"):
            self.assertEqual(generator.TEMPLATE_FILES.count(name), 1, name)
        listed = {name for name in generator.TEMPLATE_FILES if name.startswith("cameraopt-service/")}
        on_disk = {p.relative_to(SERVICE_DIR.parent).as_posix() for p in SERVICE_DIR.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts}
        self.assertEqual(listed, on_disk)

    def test_readme_describes_the_port_and_its_deviations(self):
        text = (SERVICE_DIR / "README.md").read_text()
        for phrase in ("patch 0040", "memory.reclaim", "service-B adjustment band",
                       "at most eight processes", "18 Binder methods remain explicitly unported"):
            self.assertIn(phrase, text)


class ArtifactVerifierTests(unittest.TestCase):
    def test_verifier_requires_the_reclaim_helpers_in_services_jar(self):
        spec = importlib.util.spec_from_file_location("verify", SERVICE_DIR / "verify_artifacts.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = (SERVICE_DIR / "verify_artifacts.py").read_text()
        self.assertIn('contract.get("reclaim_helper_classes", [])', source)
        self.assertIn("selected reclaim helper", source)
        self.assertTrue(hasattr(module, "validate"))


class PlannerHarnessTests(unittest.TestCase):
    def test_planner_harness_passes_on_the_host_jvm(self):
        sys.path.insert(0, str(ROOT))
        from scripts import test_nezha_cameraopt_reclaim as harness
        if harness.find_javac() is None:
            self.skipTest("javac unavailable")
        result = harness.run()
        self.assertGreaterEqual(result["checks"], 70)
        self.assertEqual(result["gap_kb"], 300000)


if __name__ == "__main__":
    unittest.main()


class ArtifactVerifierBehaviorTests(unittest.TestCase):
    """The ownership check must refuse a services.jar without the reclaim helpers."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / "tests"))
        import test_cameraopt_service as fixture
        import tempfile
        self.fixture = fixture
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        d = Path(self.temp.name)
        self.original, self.runtime, self.adapter, self.services = (d / n for n in ("o.jar", "r.jar", "a.jar", "s.jar"))
        factory = ["Lcom/miui/cameraopt/ICameraOptManager;", "Lcom/miui/cameraopt/verify/Verifier;",
                   "Lcom/miui/cameraopt/configs/JsonDisptcher;"]
        adapter = ["Lcom/android/server/cameraopt/NezhaCameraOptService;"]
        self.helpers = ["Lcom/android/server/am/NezhaCameraReclaimPolicy;", "Lcom/android/server/am/NezhaCameraReclaimPlanner;"]
        fixture.jar(self.original, factory); fixture.jar(self.runtime, factory); fixture.jar(self.adapter, adapter)
        self.classpath = ["/system/framework/services.jar", "/system_ext/framework/miui-cameraopt.jar",
                          "/system_ext/framework/nezha-cameraopt-service.jar"]
        self.contract = {"factory_jar_sha256": hashlib.sha256(self.original.read_bytes()).hexdigest(),
                         "factory_required_classes": factory, "adapter_required_classes": adapter,
                         "process_helper_class": "Lcom/android/server/am/NezhaCameraProcessPolicy;",
                         "reclaim_helper_classes": self.helpers, "runtime_classpath_order": self.classpath}

    def test_missing_reclaim_helper_is_rejected_and_complete_services_jar_passes(self):
        A = self.fixture.ARTIFACTS
        self.fixture.jar(self.services, ["Lcom/android/server/am/NezhaCameraProcessPolicy;", self.helpers[0]])
        with self.assertRaisesRegex(A.ValidationError, "reclaim helper"):
            A.validate(self.contract, self.original, self.runtime, self.adapter, self.services, self.classpath)
        self.fixture.jar(self.services, ["Lcom/android/server/am/NezhaCameraProcessPolicy;", *self.helpers])
        result = A.validate(self.contract, self.original, self.runtime, self.adapter, self.services, self.classpath)
        self.assertEqual(result["status"], "artifact_ownership_verified")

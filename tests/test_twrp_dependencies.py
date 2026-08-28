"""Offline supplementary-source tests; no real Git, network, VM or phone calls."""

import contextlib
import copy
import errno
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import twrp_dependencies as dependencies
from scripts import twrp_workspace


BASE_SHA = "a" * 40
BASE_MANIFEST = ('<manifest><remote name="aosp" fetch="https://android.googlesource.com"/>'
                 '<default remote="aosp"/><project path="build/make" name="platform/build" revision="'
                 + BASE_SHA + '"/></manifest>')


class Fixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.control = self.root / "control"
        (self.control / "config").mkdir(parents=True)
        self.source = self.root / "source"
        self.source.mkdir()
        self.paths = {"source_dir": self.source, "out_dir": self.root / "out", "report_dir": self.root / "reports"}
        self.paths["report_dir"].mkdir()
        (self.paths["report_dir"] / twrp_workspace.SNAPSHOT).write_text(BASE_MANIFEST)
        self.base = twrp_workspace.load_config()
        self.base.update({key: str(value) for key, value in self.paths.items()})
        self.base["expected_project_count"] = 1
        self.base["project_selection"]["expanded_project_count"] = 2
        (self.control / "config/twrp.json").write_text(json.dumps(self.base))
        self.config = dependencies.load_config()
        self.config["projects"] = [next(project for project in self.config["projects"] if project["path"] == "system/bpf")]
        self.config["base"].update(source_dir=str(self.source), project_count=1,
                                   frozen_manifest_sha256=hashlib.sha256(BASE_MANIFEST.encode()).hexdigest())
        self.save_config()
        self.project = self.config["projects"][0]
        self.target = self.source / self.project["path"]
        self.frozen = twrp_workspace.parse_manifest(BASE_MANIFEST, resolved=True)

    def save_config(self):
        (self.control / dependencies.CONFIG).write_text(json.dumps(self.config))

    @contextlib.contextmanager
    def base_mocks(self):
        with patch.object(twrp_workspace, "verify_control"), \
             patch.object(twrp_workspace, "load_snapshot", return_value=self.frozen), \
             patch.object(twrp_workspace, "manifest_text", return_value=BASE_MANIFEST):
            yield

    def make_project(self):
        (self.target / ".git").mkdir(parents=True)

    def git(self, target, *args):
        return {("rev-parse", "--show-toplevel"): str(target),
                ("rev-parse", "--absolute-git-dir"): str(target / ".git"),
                ("rev-parse", "HEAD"): self.project["commit"],
                ("remote", "get-url", "origin"): self.project["url"],
                ("ls-files", "-v", "-z"): "H Android.bp\0H include/bpf.h\0",
                ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching"): "",
                ("rev-parse", "--verify", "FETCH_HEAD^{commit}"): self.project["commit"]}[args]


class ConfigurationTests(Fixture):
    def test_first_four_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:4]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "9eee51c8c2b77a938dad6044243cd8c6c18ecae909c5142b2059adfc4354e0bf")

    def test_first_seven_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:7]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "dfada91f5e31bf4df2de6d68dbbec59e22092c4bc78e8564aa36be4a720ad8cd")

    def test_first_eleven_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:11]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "fd8e7aff3ae58eb0703c7202567b4fccf87f29b9f0e1962dff3f999dddfad36d")

    def test_first_fifteen_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:15]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "b066a566e8af26b51541e1581bd90830a6c0a32390c0bf69ac96cac76e340a36")

    def test_first_forty_three_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:43]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "39d0f62d644fadebbb55f2a10e3d7ce41e35ee5b7e16c7f351ef8d688da265c3")

    def test_first_fifty_two_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:52]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "ab7ada6a928230f9899773b960dad1f4383edc55981540cb1d22dfc48e203197")

    def test_first_fifty_six_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:56]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "860009dff426d1c259256d1da2cfc2e3bb04125e55b50442089461157a3cec46")

    def test_first_sixty_three_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:63]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "87c86b59ca78b8aedc137d3f0cc632eb10a55a5477341305386c538817ea71af")

    def test_first_sixty_eight_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:68]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "66a247bf90591518ef4a401005fee79897f4ca783e423e7a34b4def5ba668558")

    def test_first_seventy_three_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:73]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "b66a26acd8b784dae18e99df575862e314d13ac8fe2220045a8ba461383e247b")

    def test_first_eighty_one_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:81]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "ac29d47f3b4645dd4083ea85f06bfa1ee7ad00fe2b84115dd20476c3df3f5dfb")

    def test_initial_java_supplements_and_original_391_project_snapshot_are_pinned(self):
        config = dependencies.load_config()
        self.assertEqual(config["base"]["project_count"], 391)
        self.assertEqual(config["projects"][:21], [{
            "path": "system/bpf", "url": "https://android.googlesource.com/platform/system/bpf",
            "commit": "4447acd742bf443f9088c300bd69f96ede8eaeb1", "tag": "android-16.0.0_r1",
            "reason": "Official AOSP provider of bpf_cc_defaults required by the selected Connectivity BPF headers. This addition supplements, and does not rewrite, the frozen 391-project Repo baseline."
        }, {
            "path": "packages/modules/NetworkStack",
            "url": "https://android.googlesource.com/platform/packages/modules/NetworkStack",
            "commit": "f9da1fc7154ea007aa835f88e8070c6ac46d54e9", "tag": "android-16.0.0_r1",
            "reason": config["projects"][1]["reason"]
        }, {
            "path": "hardware/google/apf", "url": "https://android.googlesource.com/platform/hardware/google/apf",
            "commit": "40d36d317d9367641e685e88e46343f25b192fc4", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP APF libraries required by NetworkStack JNI test defaults."
        }, {
            "path": "external/libpcap", "url": "https://android.googlesource.com/platform/external/libpcap",
            "commit": "2e9a50d7694425ead7595bf98d3a9c0ab790e4f9", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libpcap provider required by NetworkStack JNI test defaults."
        }, {
            "path": "platform_testing", "url": "https://android.googlesource.com/platform/platform_testing",
            "commit": "7b48625b052b94b1ef24573ef5e8ffa5e2ea9783", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP Tradefed defaults required by retained shared test infrastructure."
        }, {
            "path": "frameworks/libs/native_bridge_support",
            "url": "https://android.googlesource.com/platform/frameworks/libs/native_bridge_support",
            "commit": "b527289974e3883460370012325ab3736d59268a", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP native_bridge_proxy_libc_defaults required by the retained binary translation libc proxy."
        }, {
            "path": "external/skia", "url": "https://android.googlesource.com/platform/external/skia",
            "commit": "bcb0f77c44783b1800ba37641ba7ecab04f05e07", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP skia_deps and skia_renderengine_deps required by retained HWUI and RenderEngine framework code."
        }, {
            "path": "external/harfbuzz_ng", "url": "https://android.googlesource.com/platform/external/harfbuzz_ng",
            "commit": "e489c416b6f8d2a9a2e0e85b781d1e4a0c431401", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libharfbuzz_subset provider required by Skia font subsetting."
        }, {
            "path": "external/webp", "url": "https://android.googlesource.com/platform/external/webp",
            "commit": "7698c1d3a5cbecdf336510eeb3366d1de752454a", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libwebp-decode and libwebp-encode providers required by Skia image codecs."
        }, {
            "path": "external/rust/crabbyavif", "url": "https://android.googlesource.com/platform/external/rust/crabbyavif",
            "commit": "9f3e32a2ffc45466eaed69ad522080cbf67f827b", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libcrabbyavif_ffi provider required by Skia AVIF support."
        }, {
            "path": "external/libjpeg-turbo", "url": "https://android.googlesource.com/platform/external/libjpeg-turbo",
            "commit": "6cedbd6ff13946bef76a015693d02723b0d3226e", "tag": "android-16.0.0_r1",
            "reason": "Real current AOSP libjpeg provider required by Skia image codecs; profile metadata and legacy VNDK prebuilts are not substitutes."
        }, {
            "path": "hardware/st/nfc", "url": "https://android.googlesource.com/platform/hardware/st/nfc",
            "commit": "ffc570734ef14c1d153b0dcc13ce63a733d6540a", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP nfc_service_fuzzer provider required by the SELinux service-fuzzer binding validator. Generic ST source for validation only; not the selected phone NFC HAL."
        }, {
            "path": "system/connectivity/wificond", "url": "https://android.googlesource.com/platform/system/connectivity/wificond",
            "commit": "65a446e53318aa491314d4a858c383676a4499cf", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP wificond_service_fuzzer provider required by the SELinux service-fuzzer binding validator."
        }, {
            "path": "packages/modules/Virtualization", "url": "https://android.googlesource.com/platform/packages/modules/Virtualization",
            "commit": "c984fc337c11ca5edc03ccf02037b2455dd8fcaf", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP virtualizationmanager_fuzzer provider required by the SELinux service-fuzzer binding validator."
        }, {
            "path": "frameworks/opt/net/wifi", "url": "https://android.googlesource.com/platform/frameworks/opt/net/wifi",
            "commit": "1cab31f96d1f903e190708c1ce665520a4a89d10", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libwifi-system-iface and libwifi-system-iface-test providers required by the wificond service fuzzer source."
        }, {
            "path": "external/junit", "url": "https://android.googlesource.com/platform/external/junit",
            "commit": "56c85a91bba5313da30e5ca94b95b37a2613d641", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP junit and junit-host providers required by retained Java build modules."
        }, {
            "path": "external/doclava", "url": "https://android.googlesource.com/platform/external/doclava",
            "commit": "07b2d9cd367915b6d90c448a2371ab31b58deb5d", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP Doclava documentation tool and defaults required by retained Java build modules."
        }, {
            "path": "external/jsilver", "url": "https://android.googlesource.com/platform/external/jsilver",
            "commit": "020d5f12b76c4b4a21c8edb761b6318e486141b0", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP jsilver template provider required by the Doclava host tool."
        }, {
            "path": "external/hamcrest", "url": "https://android.googlesource.com/platform/external/hamcrest",
            "commit": "a4975acbd7161fbc95f11c1a8f68db544fe5936d", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP hamcrest provider required by JUnit."
        }, {
            "path": "external/antlr", "url": "https://android.googlesource.com/platform/external/antlr",
            "commit": "16467b971bd3e2009fad32dd79016f2c7e421deb", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP antlr-runtime provider required by Doclava defaults."
        }, {
            "path": "external/tagsoup", "url": "https://android.googlesource.com/platform/external/tagsoup",
            "commit": "e55b6311e644c0df77cdb0fded945e53c5890bc8", "tag": "android-16.0.0_r1",
            "reason": "Real AOSP tagsoup provider required by Doclava defaults."}])
        self.assertIn("libnetworkstackutilsjni_deps", config["projects"][1]["reason"])
        self.assertIn("tests/unit/Android.bp", config["projects"][1]["reason"])
        snapshot = dependencies.ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml"
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), config["base"]["frozen_manifest_sha256"])

    def test_graph_nine_cloud_and_native_providers_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/aws-sdk-java-v2", "5b6d2ca932250b95bb8fd65c6430e9425972ef1d"),
            ("external/aws-crt-java", "d6de37e00133e24434ad586120131e35c6d23064"),
            ("external/aws-eventstream-java", "4d25ba34e39ebb08772897d606ca054a61b6db82"),
            ("external/slf4j", "ef7a1a29d4e3942861760eb58b989f069a0f3200"),
            ("external/jackson-core", "a1462bea974256c3b2d4ae0c61d906592d21e7ef"),
            ("external/google-cloud-java", "5ba13afc6ce627cb4c71ad1ff1ff62f625022ad2"),
            ("external/sdk-platform-java", "daf609d6e2f51440e9161eb2cdfc8a3cafacf565"),
            ("external/google-auth-library-java", "65648776fb0f5e9582c12f6a432712a707fa6324"),
            ("external/opencensus-java", "f5311957763aa0d5af59a7da58791a7d3d6a153d"),
            ("external/threetenbp", "b6b56fd22e89d7362d1cf396d66d16975060cc26"),
            ("external/auto", "df40c3e9b3fc2bb8e37199c7f40ae177fde109b9"),
            ("external/escapevelocity", "c1615b26efb0acd888b6661506503c0c539dd2ae"),
            ("external/javapoet", "1b3553d5df7a74703fe646aa212c4b2d7f9adea9"),
            ("external/google-java-format", "10816b529e1d7005ca788e7b4c5efd1c72957e26"),
            ("system/media", "f01e84b958fb6a887dc0e74e4b5ebd159f03860a"),
            ("external/abseil-cpp", "3c03adaaf6c28f5c5c47c753e860b9ac16957b35"),
            ("external/aac", "46faeaba7093d2ce88645a1da20e379fb5bcc20f"),
            ("external/flatbuffers", "ba0a3a76154937b0f3c0126062a486e1644ab9e4"),
            ("external/tinyalsa", "a72ec6d8c6bbeb7ca0293e51e33573640904e99b"),
            ("external/tinyalsa_new", "86c164eaf9e10240dca32a2c8f0c26a7f88ad97f"),
            ("external/speex", "6c44585f68f6f7f71c51ff1d56d9a5d0409d2d29"),
            ("external/google-benchmark", "68f58239bba93c71a39e4cd872bcbf5f69d971ec"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[21:43]], expected)
        for project in projects[21:43]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].strip())

    def test_next_java_foundation_providers_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/testng", "8779cc45e4579acbc3a4ad19e8e99c79e96f793c"),
            ("external/junit-params", "6c63c83301825c8b94560b1ff8f8381c2deedc52"),
            ("external/snakeyaml", "d60b842e114fc22db76c6d84f9aa7950e5e4c2ea"),
            ("external/guice", "f37a7d76021c22a64143224a14517c3f53b8b137"),
            ("external/jspecify", "35b27b915ed9f1a58b71b29ada4d5ce0b41458ef"),
            ("external/mockito", "770ab8835bf0830a64aa833275c513281c47325c"),
            ("external/dexmaker", "73e46f3a1e0771fd9cd76e1b50f98b764df565dc"),
            ("external/objenesis", "ae9bf081469e4beaa2ea02549c417a13baf0c3c8"),
            ("tools/dexter", "4ce3b1286e402f28c53e0729925e1cde691fe968"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[43:52]], expected)
        for project in projects[43:52]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].strip())

    def test_graph_ten_java_tool_providers_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/apache-commons-math", "54b2db9e0e10bf0f5f34e97234201980f9757335"),
            ("prebuilts/r8", "318c3c8b381636efd5d7b00d085b07eeb5515949"),
            ("external/google-smali", "112192259df4c8cfe9491affe3728f98024a630c"),
            ("external/okio", "bef9e8ef12ad63247afe846957492f4ddb0f2b42"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[52:56]], expected)
        for project in projects[52:56]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].strip())

    def test_graph_eleven_compatibility_and_native_providers_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/apache-commons-bcel", "716e385615070dffa9e4201497808536bc692641"),
            ("external/jemalloc_new", "84644256fd89cd940d97c3ee264c6f1ec6daddf1"),
            ("system/testing/gtest_extras", "42ca057d3e9e46671647ca334f4e79552f546d2b"),
            ("external/libopus", "0e4b55f930cdf2b853dbdee1f5273f3c1c27f81f"),
            ("external/bcc", "d3fb98e35da3af11c4678b6e911d926ac0ad1fff"),
            ("external/vixl", "e685e67c8f41596dad341b086a649e9f4a7d6062"),
            ("external/image_io", "ed236bb2d9a3a65a78ea4abca94a2c7c5dbec1b8"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[56:63]], expected)
        for project in projects[56:63]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].strip())

    def test_dagger_and_shared_java_providers_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/dagger2", "eb622db751720f39a1ad974096dd371c75e34482"),
            ("external/jakarta.inject", "6deaa544ee90038fbc099429f3ee47c04c2cce04"),
            ("external/ksp", "88db449f6444fd8a8a45e51a1e1a36ab88d820b0"),
            ("external/TestParameterInjector", "3ece4c78c4ff10f1e0e8c78f7390561846f08fd0"),
            ("external/cbor-java", "2abec0b574627877ddc8a2dff7315ca2fe489e56"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[63:68]], expected)
        for project in projects[63:68]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].strip())

    def test_graph_twelve_java_and_windows_host_providers_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/javaparser", "f0340d8e30c177f9125cc02e7b512609509b136e"),
            ("external/javassist", "f1fbf3c2ab775ce834e0af96b7a85bdc7a0eac65"),
            ("prebuilts/cmdline-tools", "b5b2dcb54a4387a9eeae5f3fcd8ca9d5420f79ce"),
            ("external/googleapis", "99bff8ebcdde5aa21f01049c8c39900beef372e4"),
            ("prebuilts/gcc/linux-x86/host/x86_64-w64-mingw32-4.8", "517043524e83921c5b0be8ff2ad92a40376971a9"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[68:73]], expected)
        for project in projects[68:73]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].strip())

    def test_graph_thirteen_patch_audio_and_archive_providers_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/libdivsufsort", "f9226d8ff66736207cd7664bcca61b3760045691"),
            ("external/sonivox", "0dd66fcbc6f7456fd43d6bef4d2f670dfdc7b6d7"),
            ("external/apache-commons-compress", "4b700cfd7c3063cd0b00dac8d930dba78eedee0e"),
            ("external/xz-java", "e16429ac5ad2d18b7c9e5dbcd673005c5257e7a9"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[73:77]], expected)
        for project in projects[73:77]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].strip())

    def test_reviewed_native_projections_are_pinned_and_labelled(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/jsmn", "75c0d7b4f48725ffa51f1f5ee7b1af0034e2f280"),
            ("external/libogg", "44061a68e8a9b41bd2cfc32a0a2bf2a5caea2478"),
            ("external/vulkan-headers", "7e80b474147eb0c6a9464c2e867ae6ba277a3102"),
            ("external/OpenCSD", "98045c29085b5e10460f0c920d919597fbc91eeb"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[77:81]], expected)
        for project in projects[77:81]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 13 error:"))
                self.assertIn("Android.bp", project["reason"])

    def test_graph_fifteen_arm_headers_and_gsm_projection_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/arm-trusted-firmware", "54fd6939e177f8ff529b10183254802c76df6d08"),
            ("external/libgsm", "8ec969cea971fe25ff2d3933a5a9f8504f8e86c9"),
        ]
        self.assertEqual(len(projects), 83)
        self.assertEqual([(project["path"], project["commit"]) for project in projects[81:]], expected)
        for project in projects[81:]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
        self.assertIn("arm_dt_bindings_headers", projects[81]["reason"])
        self.assertIn("graph 15 error", projects[81]["reason"])
        self.assertTrue(projects[82]["reason"].startswith("Source audit projection, not a graph 15 error:"))
        self.assertIn("libcodec2_soft_gsmdec", projects[82]["reason"])

    def test_supplementary_projects_are_outside_the_frozen_repo_project_paths(self):
        config = dependencies.load_config()
        snapshot = dependencies.ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml"
        frozen = twrp_workspace.parse_manifest(snapshot.read_text(), resolved=True)
        self.assertEqual(len(frozen), 391)
        for project in config["projects"]:
            with self.subTest(path=project["path"]):
                self.assertFalse(any(twrp_workspace.overlap(Path(project["path"]), Path(path)) for path in frozen))

    def test_optional_configuration_preserves_older_control_bundles(self):
        (self.control / dependencies.CONFIG).unlink()
        with patch.object(twrp_workspace, "run", side_effect=AssertionError("No process")):
            self.assertIsNone(dependencies.load_config(self.control))
            self.assertIsNone(dependencies.descriptor(self.control))
            self.assertIsNone(dependencies.verify(self.control, self.source))

    def test_plan_is_default_and_never_runs_commands_probes_or_writes(self):
        with patch.object(twrp_workspace, "run", side_effect=AssertionError("No process")), \
             patch.object(twrp_workspace, "require_host", side_effect=AssertionError("No probe")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("No write")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(dependencies.main(["--control-root", str(self.control)]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["action"], "plan")
        self.assertFalse(report["executes_commands"])
        self.assertFalse(report["writes_files"])

    def test_descriptor_binds_exact_configuration_bytes(self):
        before = dependencies.descriptor(self.control)
        self.config["projects"][0]["reason"] += " Additional review."
        self.save_config()
        after = dependencies.descriptor(self.control)
        self.assertNotEqual(before["configuration_sha256"], after["configuration_sha256"])
        self.assertEqual(after["projects"], self.config["projects"])

    def test_bad_paths_origins_tags_and_pins_are_rejected(self):
        original = copy.deepcopy(self.config)
        for key, value in (("path", "../outside"), ("path", ".repo/manifests"),
                           ("url", "https://user:secret@example.com/repo"),
                           ("url", "file:///private/source"), ("tag", "--upload-pack=evil"),
                           ("tag", "../ref"), ("commit", "main")):
            self.config = copy.deepcopy(original)
            self.config["projects"][0][key] = value
            self.save_config()
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                dependencies.load_config(self.control)

    def test_duplicate_or_overlapping_projects_are_rejected(self):
        for path in ("system/bpf", "system/bpf/nested", "system"):
            self.config["projects"] = [self.project, dict(self.project, path=path)]
            self.save_config()
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "overlap"):
                dependencies.load_config(self.control)

    def test_symlinked_config_is_not_treated_as_optional(self):
        path = self.control / dependencies.CONFIG
        path.unlink()
        path.symlink_to(self.root / "missing.json")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            dependencies.load_config(self.control)


class BaseTests(Fixture):
    def test_base_context_requires_original_snapshot_and_retains_optional_paths(self):
        with self.base_mocks():
            context = dependencies.base_context(self.control, self.source, paths=self.paths)
        self.assertEqual(context["frozen"], self.frozen)
        self.assertEqual(context["paths"], self.paths)

    def test_wrong_source_path_is_rejected_before_git_or_snapshot_reads(self):
        with patch.object(twrp_workspace, "verify_control") as control, self.assertRaisesRegex(ValueError, "explicitly selected"):
            dependencies.base_context(self.control, self.root / "other")
        control.assert_not_called()

    def test_changed_frozen_snapshot_is_never_accepted(self):
        (self.paths["report_dir"] / twrp_workspace.SNAPSHOT).write_text(BASE_MANIFEST + "\n")
        with self.base_mocks(), self.assertRaisesRegex(ValueError, "immutable base"):
            dependencies.base_context(self.control, self.source)

    def test_changed_base_manifest_pin_is_rejected(self):
        self.config["base"]["manifest_commit"] = "f" * 40
        self.save_config()
        with self.base_mocks(), self.assertRaisesRegex(ValueError, "pinned base"):
            dependencies.base_context(self.control, self.source)

    def test_supplementary_sources_cannot_overlap_base_projects(self):
        for path in ("build/make", "build/make/nested", "build"):
            self.config["projects"][0]["path"] = path
            self.save_config()
            with self.subTest(path=path), self.base_mocks(), self.assertRaisesRegex(ValueError, "overlaps"):
                dependencies.base_context(self.control, self.source)

    def test_existing_unrelated_parent_checkout_is_rejected(self):
        (self.source / "system" / ".git").mkdir(parents=True)
        with self.base_mocks(), self.assertRaisesRegex(ValueError, "unrelated checkout"):
            dependencies.base_context(self.control, self.source)


class ProjectTests(Fixture):
    def setUp(self):
        super().setUp()
        self.make_project()

    def test_exact_standalone_project_is_accepted_without_mutation(self):
        with patch.object(dependencies, "git_value", side_effect=self.git):
            report = dependencies.verify_project(self.project, self.target)
        self.assertTrue(report["clean"])
        self.assertTrue(report["mode_changes_checked"])
        self.assertTrue(report["ignored_files_checked"])
        self.assertEqual(report["actual_head"], self.project["commit"])
        self.assertEqual(report["git_dir"], str(self.target / ".git"))

    def test_changed_head_origin_root_metadata_and_dirty_files_are_rejected(self):
        mutations = {("rev-parse", "HEAD"): "b" * 40,
                     ("remote", "get-url", "origin"): "https://example.com/wrong",
                     ("rev-parse", "--show-toplevel"): str(self.source),
                     ("rev-parse", "--absolute-git-dir"): str(self.source / ".repo/other.git"),
                     ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching"): " M Android.bp\0"}
        for changed, value in mutations.items():
            def fake(target, *args):
                return value if args == changed else self.git(target, *args)
            with self.subTest(changed=changed), patch.object(dependencies, "git_value", side_effect=fake), self.assertRaises(ValueError):
                dependencies.verify_project(self.project, self.target)

    def test_ignored_files_and_mode_changes_are_not_clean_exceptions(self):
        for status in ("!! ignored/Android.bp\0", " M executable\0", "?? new-source\0"):
            def fake(target, *args):
                return status if args[0] == "status" else self.git(target, *args)
            with self.subTest(status=status), patch.object(dependencies, "git_value", side_effect=fake), self.assertRaisesRegex(ValueError, "local, ignored or mode"):
                dependencies.verify_project(self.project, self.target)

    def test_git_worktree_or_symlink_metadata_is_rejected(self):
        metadata = self.target / ".git"
        metadata.rmdir()
        metadata.write_text("gitdir: /outside")
        with self.assertRaisesRegex(ValueError, "non-standalone"):
            dependencies.verify_project(self.project, self.target)
        metadata.unlink()
        outside = self.root / "outside-git"
        outside.mkdir()
        metadata.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "non-standalone"):
            dependencies.verify_project(self.project, self.target)

    def test_git_process_forces_executable_mode_checks(self):
        with patch.object(twrp_workspace, "run", return_value=SimpleNamespace(stdout="")) as run:
            dependencies.git_value(self.target, "status")
        self.assertEqual(run.call_args.args[0], ["git", "-c", "core.fileMode=true",
                         "-c", "core.fsmonitor=false", "-c", "core.ignoreStat=false", "-C", self.target, "status"])

    def test_assume_unchanged_cannot_hide_modified_tracked_bytes(self):
        def hidden(target, *args):
            if args == ("ls-files", "-v", "-z"):
                return "h Android.bp\0H include/bpf.h\0"
            return self.git(target, *args)
        (self.target / "Android.bp").write_text("modified bytes hidden from ordinary git status")
        with patch.object(dependencies, "git_value", side_effect=hidden), self.assertRaisesRegex(ValueError, "hidden or unexpected"):
            dependencies.verify_project(self.project, self.target)
        self.assertEqual((self.target / "Android.bp").read_text(), "modified bytes hidden from ordinary git status")

    def test_skip_worktree_cannot_hide_modified_tracked_bytes(self):
        for flag in ("S", "s"):
            def hidden(target, *args):
                if args == ("ls-files", "-v", "-z"):
                    return f"{flag} Android.bp\0H include/bpf.h\0"
                return self.git(target, *args)
            with self.subTest(flag=flag), patch.object(dependencies, "git_value", side_effect=hidden), \
                 self.assertRaisesRegex(ValueError, "hidden or unexpected"):
                dependencies.verify_project(self.project, self.target)

    def test_empty_malformed_or_unmerged_index_records_are_rejected(self):
        for flags in ("", "H Android.bp", "H \0", "M conflict\0", "H Android.bp\0\0"):
            def fake(target, *args):
                return flags if args == ("ls-files", "-v", "-z") else self.git(target, *args)
            with self.subTest(flags=flags), patch.object(dependencies, "git_value", side_effect=fake), \
                 self.assertRaisesRegex(ValueError, "hidden or unexpected"):
                dependencies.verify_project(self.project, self.target)

    def test_verify_report_does_not_claim_it_validated_base_patch_contents(self):
        with self.base_mocks(), patch.object(dependencies, "git_value", side_effect=self.git):
            report = dependencies.verify(self.control, self.source)
        self.assertTrue(report["verified"])
        self.assertFalse(report["base_worktrees_checked"])
        self.assertEqual(report["base"]["frozen_manifest_sha256"], self.config["base"]["frozen_manifest_sha256"])

    def test_additive_sources_keep_bpf_and_base_snapshot_unchanged(self):
        original_bpf = copy.deepcopy(self.config["projects"][0])
        self.config["projects"] = dependencies.load_config()["projects"]
        self.save_config()
        projects = {self.source / project["path"]: project for project in self.config["projects"]}
        for project in self.config["projects"][1:]:
            (self.source / project["path"] / ".git").mkdir(parents=True)
        snapshot = (self.paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes()
        def all_projects(target, *args):
            if args == ("rev-parse", "HEAD"):
                return projects[target]["commit"]
            if args == ("remote", "get-url", "origin"):
                return projects[target]["url"]
            return self.git(target, *args)
        with self.base_mocks(), patch.object(dependencies, "git_value", side_effect=all_projects):
            report = dependencies.verify(self.control, self.source)
        self.assertEqual(self.config["projects"][0], original_bpf)
        self.assertEqual([project["path"] for project in report["projects"]],
                         [project["path"] for project in self.config["projects"]])
        self.assertEqual([project["actual_head"] for project in report["projects"]],
                         [project["commit"] for project in self.config["projects"]])
        self.assertEqual((self.paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes(), snapshot)

    def test_valid_bpf_does_not_hide_any_wrong_supplementary_commit(self):
        self.config["projects"] = dependencies.load_config()["projects"]
        self.save_config()
        projects = {self.source / project["path"]: project for project in self.config["projects"]}
        for project in self.config["projects"][1:]:
            (self.source / project["path"] / ".git").mkdir(parents=True)
        for changed in self.config["projects"][1:]:
            def wrong_project(target, *args):
                if args == ("rev-parse", "HEAD"):
                    return "f" * 40 if target == self.source / changed["path"] else projects[target]["commit"]
                if args == ("remote", "get-url", "origin"):
                    return projects[target]["url"]
                return self.git(target, *args)
            with self.subTest(path=changed["path"]), self.base_mocks(), \
                 patch.object(dependencies, "git_value", side_effect=wrong_project), \
                 self.assertRaisesRegex(ValueError, changed["path"]):
                dependencies.verify(self.control, self.source)


class FetchTests(Fixture):
    def test_existing_verified_clone_is_not_downloaded_or_changed(self):
        self.make_project()
        with patch.object(dependencies, "git_value", side_effect=self.git), patch.object(twrp_workspace, "run") as run:
            report = dependencies.fetch_project(self.project, self.source)
        self.assertTrue(report["clean"])
        run.assert_not_called()

    def test_existing_empty_or_unrelated_directory_is_preserved(self):
        self.target.mkdir(parents=True)
        with patch.object(twrp_workspace, "run") as run, self.assertRaisesRegex(ValueError, "non-standalone"):
            dependencies.fetch_project(self.project, self.source)
        run.assert_not_called()
        self.assertEqual(list(self.target.iterdir()), [])

    def test_fetch_uses_exact_tag_depth_and_verifies_before_exclusive_publish(self):
        calls = []
        def fake_run(args, **kwargs):
            calls.append(args)
            if args[:2] == ["git", "init"]:
                (Path(args[2]) / ".git").mkdir(parents=True)
            return SimpleNamespace(stdout="")
        def publish(staging, target):
            self.assertFalse(target.exists())
            staging.rename(target)
        with patch.object(twrp_workspace, "run", side_effect=fake_run), \
             patch.object(dependencies, "git_value", side_effect=self.git), \
             patch.object(dependencies, "publish_exclusive", side_effect=publish) as publish_mock:
            report = dependencies.fetch_project(self.project, self.source)
        self.assertTrue(report["clean"])
        self.assertEqual(len(calls), 4)
        self.assertEqual(calls[2][3:], ["fetch", "--depth=1", "--no-tags", "origin", "refs/tags/android-16.0.0_r1"])
        self.assertEqual(calls[3][3:], ["checkout", "--detach", self.project["commit"]])
        publish_mock.assert_called_once()
        self.assertEqual(sorted(path.name for path in self.target.parent.iterdir()), ["bpf"])

    def test_moved_upstream_tag_is_never_published(self):
        def fake_run(args, **kwargs):
            if args[:2] == ["git", "init"]:
                Path(args[2]).mkdir()
            return SimpleNamespace(stdout="")
        with patch.object(twrp_workspace, "run", side_effect=fake_run), \
             patch.object(dependencies, "git_value", return_value="f" * 40), \
             patch.object(dependencies, "publish_exclusive") as publish, self.assertRaisesRegex(ValueError, "upstream tag differs"):
            dependencies.fetch_project(self.project, self.source)
        publish.assert_not_called()
        self.assertFalse(self.target.exists())

    def test_host_failure_prevents_base_reads_or_downloads(self):
        with patch.object(twrp_workspace, "require_host", side_effect=ValueError("host blocked")), \
             patch.object(dependencies, "base_context") as base, patch.object(dependencies, "fetch_project") as fetch, \
             self.assertRaisesRegex(ValueError, "host blocked"):
            dependencies.fetch(self.control, self.source, "native")
        base.assert_not_called()
        fetch.assert_not_called()

    def test_base_head_or_origin_failures_prevent_source_additions(self):
        report = {"projects": [{"path": "build/make", "errors": ["HEAD differs"], "clean": True}], "all_present": True}
        with self.base_mocks(), patch.object(twrp_workspace, "require_host", return_value={}), \
             patch.object(twrp_workspace, "project_report", return_value=report), \
             patch.object(dependencies, "fetch_project") as fetch, self.assertRaisesRegex(ValueError, "Base project"):
            dependencies.fetch(self.control, self.source, "native")
        fetch.assert_not_called()

    def test_preexisting_base_patch_status_is_recorded_not_silently_marked_clean(self):
        base = {"projects": [{"path": "build/make", "errors": ["Local changes preserved"],
                               "clean": False, "local_changes": " M reviewed.mk"}], "all_present": True}
        self.make_project()
        snapshot = (self.paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes()
        with self.base_mocks(), patch.object(twrp_workspace, "require_host", return_value={"supported_build_host": True}), \
             patch.object(twrp_workspace, "project_report", return_value=base), \
             patch.object(dependencies, "git_value", side_effect=self.git):
            report = dependencies.fetch(self.control, self.source, "native")
        self.assertEqual(report["base_dirty_projects"], [{"path": "build/make", "local_changes": " M reviewed.mk"}])
        self.assertTrue(report["base_worktrees_checked"])
        self.assertEqual((self.paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes(), snapshot)
        self.assertEqual(len(list(self.paths["report_dir"].glob("dependencies-fetch-*.json"))), 1)


class PublicationAndLockTests(Fixture):
    def test_publish_uses_linux_noreplace_rename(self):
        rename = Mock(return_value=0)
        with patch.object(dependencies.ctypes, "CDLL", return_value=SimpleNamespace(renameat2=rename)):
            dependencies.publish_exclusive(self.root / "staging", self.target)
        self.assertEqual(rename.call_args.args, (-100, bytes(self.root / "staging"), -100, bytes(self.target), 1))

    def test_publish_collision_is_not_retried_as_an_overwrite(self):
        rename = Mock(return_value=-1)
        with patch.object(dependencies.ctypes, "CDLL", return_value=SimpleNamespace(renameat2=rename)), \
             patch.object(dependencies.ctypes, "get_errno", return_value=errno.EEXIST), self.assertRaises(FileExistsError):
            dependencies.publish_exclusive(self.root / "staging", self.target)
        self.assertEqual(rename.call_count, 1)

    def test_missing_atomic_noreplace_support_fails_closed(self):
        with patch.object(dependencies.ctypes, "CDLL", return_value=SimpleNamespace()), self.assertRaisesRegex(ValueError, "renameat2"):
            dependencies.publish_exclusive(self.root / "staging", self.target)

    def test_active_or_stale_build_lock_prevents_fetch_before_mutations(self):
        lock = self.paths["report_dir"] / "build-operation.lock"
        lock.write_text("existing build")
        with patch.object(twrp_workspace, "require_host", return_value={}), \
             patch.object(dependencies, "base_context") as base, self.assertRaisesRegex(ValueError, "owns the lock"):
            dependencies.fetch(self.control, self.source, "native")
        base.assert_not_called()
        self.assertEqual(lock.read_text(), "existing build")

    def test_only_owned_lock_is_released(self):
        lock = self.paths["report_dir"] / "build-operation.lock"
        with dependencies.operation_lock(self.paths):
            self.assertTrue(lock.is_file())
        self.assertFalse(lock.exists())
        with dependencies.operation_lock(self.paths):
            lock.write_text("replacement")
        self.assertEqual(lock.read_text(), "replacement")


if __name__ == "__main__":
    unittest.main()

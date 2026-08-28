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

    def test_first_eighty_three_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:83]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "5dca287ccb9c418f6180e4e0677866d162b9ea00fed806a38d2237364b8c374d")

    def test_first_eighty_five_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:85]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "806456bb8d612d278751cbb8535b22c1a1799a19df2b303791216e2295ec2d37")

    def test_first_eighty_seven_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:87]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "5651d857ea80ec14d72399ee6f4e81cdaed2fa7a2db66fd343118290c8e5bf74")

    def test_first_108_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:108]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "d7e1114d3e27da568c2ea9691a7daefecfb5f6b27ef1686dd734213811f68094")

    def test_first_127_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:127]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "9506dc42bd91a45929657bc4350fb21926530ac74a82969a3a701675e9841583")

    def test_first_136_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:136]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "59f36d6c49d093927ea29a065e07f3ddd02b67baa147d8c00b5c39aab1269422")

    def test_first_140_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:140]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "5d10833601cb9dced9c9a00a28e1d66ffd17a65b64439a3ed769f552d8dfc4b5")

    def test_first_144_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:144]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "a5bdfd0dfc60d81b244e2fd7108324b8c95ee2ac587256fa490917801b4567ff")

    def test_first_147_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:147]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "351fe5eea9d963cf0919b5fd49e5619e1109937ff7735942aa532d568118053e")

    def test_first_154_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:154]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "9d7829a4abb1a007ce3bfebeb2680bda3a21676d7333c277a0f64b146a2c0fb0")

    def test_first_163_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:163]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "c24c21b076d4187244fc5c2d7386fc21ec1cf2d31a571f66c32870d31babc6bf")

    def test_first_176_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:176]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "8cbd0097005d05d90f041c32f9052db47fb5a2d9745be3a086cfbce7d9a858b9")

    def test_first_185_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:185]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "4bcb97a095b2d547280b772f53e1e73996aabf2846cd73f34210c6a664ddd2c0")

    def test_first_195_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:195]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "e470fa7807f5bb327cbc7795caf4e03bac5ce6ad5233d5fc7c129f3dede96a12")

    def test_first_196_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:196]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "c41ad2b8d551dd8d841b71231a5b20c5f4c01dfdc0be4590f9e01ad22221611b")

    def test_first_197_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:197]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "47dfb57da3384758dd1917e6345b7bc434c689fdd98605a1e57702e093f5f26c")

    def test_first_199_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:199]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "765dbe53ef58422a6e24d4910c466b8dd448030ce1a1389555db932d19b76652")

    def test_first_200_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:200]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "ae49a52b7e32d4338010e164fb2341a263f9d4d0f562a6e5d3163335d1fff1ca")

    def test_first_201_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:201]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "75d3f2f09dccc42d2b97639265929b2b6226f27d9f6e155ad0f6c409604c4aba")

    def test_first_202_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:202]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "7ba053d5a12e4202d42704c21d294a79123e5394212a93fa4e22a0f7ef95dd1a")

    def test_first_208_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:208]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "1a9cc7442df570d0702acb6a606d3c52110c3fde57796641ce49daa71e07f5fd")

    def test_first_210_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:210]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "622eb20771b1f177e52d34ff7a9f48e1dcf266a774193364c34e22b401f0a4ce")

    def test_first_213_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:213]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "cf5861733fd9cdcbd128df209bd622c06d9339c5fa2d6c718fab5880e4f2a1df")

    def test_first_224_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:224]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "c4f0d87449bf255ec5fad2a4fd52f9cccd94cf3a725c3fd4f0e5b8f758366a00")

    def test_first_225_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:225]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "39517a2a7b22d56b7c7bda093ef0ae149e7198d07834ad69b488125625252c42")

    def test_first_229_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:229]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "475b0b4a1daa8dbb96290432b613821c768267bf4d80f61aa06c5c2d27987b12")

    def test_first_236_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:236]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "f8212ed54b180abdfc3c6fe398212e9c62d9b264fc2ca40f606a973557f6c408")

    def test_first_239_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:239]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "846f25983f934dbf409e7f3b0e933d93cdfed3acac8ca0678e14a12d055a37dc")

    def test_first_245_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:245]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "3636b49022d3596f865ead2fd1b9e0c0b177abca317f3b3312854ab6f0091376")

    def test_first_246_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:246]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "f62d0744f3bbfda4b7224e45617de4d392fa74a64f69819a3ab92fe9eb1315f7")

    def test_first_247_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:247]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "968909aac626762c59dbfd098ceb8523f2950d793a68c3dd9d56155f40a43c5a")

    def test_first_249_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:249]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "6a9e406de2eaf5792e5351c32d44e3d364d57e7e31d03ca49d19be67fe9d824a")

    def test_first_250_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:250]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "49fa56ab1d4b72881b4b39a546586be7f3ae696b18322156d8017c993c301b32")

    def test_first_251_supplementary_entries_remain_exact(self):
        original = dependencies.load_config()["projects"][:251]
        encoded = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         "054e70e2557607a6971041be2dee6aa41d53b826cdd497bbf2412edd5b9e6a7b")

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
        self.assertEqual([(project["path"], project["commit"]) for project in projects[81:83]], expected)
        for project in projects[81:83]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
        self.assertIn("arm_dt_bindings_headers", projects[81]["reason"])
        self.assertIn("graph 15 error", projects[81]["reason"])
        self.assertTrue(projects[82]["reason"].startswith("Source audit projection, not a graph 15 error:"))
        self.assertIn("libcodec2_soft_gsmdec", projects[82]["reason"])

    def test_graph_sixteen_connected_apps_sdk_provider_is_pinned(self):
        projects = dependencies.load_config()["projects"]
        self.assertEqual(projects[83], {
            "path": "external/connectedappssdk",
            "url": "https://android.googlesource.com/platform/external/connectedappssdk",
            "commit": "21f658c783c6390c266210e2a7f72282dce74dea",
            "tag": "android-16.0.0_r1",
            "reason": "Real AOSP ConnectedAppsSDK_Annotations provider required by CTS RemoteFrameworkClasses_Processor_Src in the graph 16 error."
        })

    def test_hwtrust_projection_is_pinned_with_required_build_scope(self):
        projects = dependencies.load_config()["projects"]
        self.assertEqual(projects[84], {
            "path": "tools/security",
            "url": "https://android.googlesource.com/platform/tools/security",
            "commit": "8d8a8332751c3b20a87f38dd7cb4039eeea489b5",
            "tag": "android-16.0.0_r1",
            "reason": "Source audit projection, not a graph 15 or 16 error: real AOSP libhwtrust_cxx provider required by retained libkeymint_remote_prov_support. Requires selecting only tools/security/remote_provisioning/hwtrust/ build definitions while retaining the full pristine source project."
        })

    def test_graph_seventeen_flashrom_and_pci_providers_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/flashrom", "0d8ada436607417fbbc39a3271c6f9093189f4ca"),
            ("external/pciutils", "a7121b40f52a45c391cda8fb48430a833522a430"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[85:87]], expected)
        for project in projects[85:87]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
        self.assertIn("libvboot_util and libvboot_host", projects[85]["reason"])
        self.assertIn("does not select or execute the Flashrom CLI", projects[85]["reason"])
        self.assertIn("libpci", projects[86]["reason"])

    def test_graph_eighteen_initial_providers_and_projections_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/parameter-framework", "eede61bcaf52412ab329b8571872b127764e1776"),
            ("external/python/pyfakefs", "0448befc5e794113ba4533f8d62ce8c3c2feccbe"),
            ("external/fonttools", "e1fe3e4ad2793916b15cccdc4a7da52a7e1dd0e9"),
            ("external/libexif", "e6271597ffa3cfd4a67e984e1c2a99c3d4cbcdfd"),
            ("external/dynamic_depth", "d8b4372b2d0c552e650741eed784aec9b1f9e88d"),
            ("external/libvpx", "718dd469f67964d8f5fd4c8ebf09513bbfa50146"),
            ("external/flac", "600f14f40d737144c998e2ec7a483122d3776fbc"),
            ("external/libaom", "f919cc204179ff88eff36fd60226540c0c7a79bb"),
            ("external/libopenapv", "c62125fdb4d6b0b7de71fda6b918b37184591a2d"),
            ("external/tremolo", "bda690e46497e1f65c5077173b9c548e6e0cd5a1"),
            ("frameworks/wilhelm", "529601b3e1df4cbbf6065bc66a4c30246ffdbe1b"),
            ("test/vts-testcase/vndk", "ab0f26db5d6a14928538904e3f335a265ba9defd"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[87:99]], expected)
        for project in projects[87:99]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
        for project in projects[90:98]:
            with self.subTest(projection=project["path"]):
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 18 error:"))
        for project in projects[87:90] + projects[98:99]:
            with self.subTest(observed=project["path"]):
                self.assertIn("graph 18 errors", project["reason"])
                self.assertFalse(project["reason"].startswith("Source audit projection"))

    def test_graph_eighteen_complete_asuite_host_sources_are_pinned(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("tools/asuite", "dcf45295b954eedb9850194166835fdeaa84ad01"),
            ("external/jimfs", "49a5260d7a9e5ad68cb04bb0bf7de1c044ca929f"),
            ("external/python/google-api-python-client", "732370cc0aa5c65d01fde5b95c20270e25c84962"),
            ("external/python/httplib2", "e025a5ec7cd2edd804c2d394a2c7841ab522db57"),
            ("external/python/uritemplates", "44fcd14ebb8f3d1793bf1008ac0b881173864ddb"),
            ("external/python/oauth2client", "6598410cf1b485e24db4a4519ed58eefa6628018"),
            ("external/python/rsa", "e5a899dcdc7d9a4dd590bf501bccc20db9cb03d0"),
            ("external/python/pyasn1", "0071cbf57b52336b8261f3903612a2d4d81669af"),
            ("external/python/pyasn1-modules", "323b68127336bb8b8a47ad804487eda722c50489"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[99:108]], expected)
        for project in projects[99:108]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 18", project["reason"])
                self.assertFalse(project["reason"].startswith("Source audit projection"))
        self.assertIn("complete ASuite build definitions", projects[99]["reason"])
        for module in ("asuite_cc_client", "atest_tradefed.sh", "adevice_fingerprint"):
            self.assertIn(module, projects[99]["reason"])

    def test_graph_eighteen_proto_and_ml_source_batch_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("frameworks/proto_logging", "29d96a39adaffda3ad1b08ae17b6befbe2a625fa"),
            ("external/libtextclassifier", "e1ac719a8a882b1c01f85b4443d0c2961b9f839d"),
            ("external/tensorflow", "b02be12795f49019bc2312316e6bffece143ed21"),
            ("external/lua", "1ac810dae2874ee161b9e1ae4e0d0ad3f64c08e9"),
            ("external/libutf", "61e1860912dd2c19dfe4ff59b6f8ce9e69a4339d"),
            ("external/marisa-trie", "226c01d88c9944271f0b8d8f5969c6b49d61143d"),
            ("external/FP16", "8c6e6497ecf7aee9220ee39dbacbc57f4437717d"),
            ("external/eigen", "15bdc8bcfba097ad88c1e4a4afd0d6260c1abc15"),
            ("external/fft2d", "fa0ad63f8b666836f56a823de546390a6e4ff4b6"),
            ("external/ruy", "57ee36e9ad21509a1089323c0b9559cbb91701fe"),
            ("external/gemmlowp", "3b727b1baa7172cbfc22e9f52371a301b9cac79c"),
            ("external/downloader", "53a45f0c0d914c6a2d5c31fa077ef0e47b0aa9f9"),
            ("external/neon_2_sse", "80a68eefdccd99baeea4880baa1b4c25f2618725"),
            ("packages/modules/NeuralNetworks", "6cd97dca5e3ce0bd539d84d78f777a3576e673e3"),
            ("external/XNNPACK", "58b652403b0e6edc9b323f4aa3444c561bff7a78"),
            ("external/pthreadpool", "0eebb03dacd53a73fb77bb9accca6a32673e178e"),
            ("external/FXdiv", "6e77b01effdc0ef3b002d6a3400f0d5caf9c0174"),
            ("external/cpuinfo", "2dcdba348d94895452dce0c8da27ea6dcbbc507e"),
            ("external/libprotobuf-mutator", "1257b81718eeb7970057853201a6820a336bc5f5"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[108:127]], expected)
        for project in projects[108:127]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].strip())
        self.assertIn("graph18 Bluetooth proto", projects[108]["reason"])
        self.assertIn("zero upstream Blueprint modules", projects[120]["reason"])
        self.assertIn("without selecting runtime packages for recovery", projects[121]["reason"])
        self.assertIn("preserve all upstream mutator properties", projects[126]["reason"])

    def test_graph_nineteen_host_provider_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/openscreen", "3f982cf4871df8771c9d4abe6e9a6f8d829b2736"),
            ("external/python/parse_type", "05a141a9980f2357419aa004bcffac985baa0b56"),
            ("external/ply", "137b3d2f79f24c330e1a34782ed49e1516eb65e1"),
            ("external/jline", "17e6dd618a45cad3178698c9d02d31ca30254bb2"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[127:131]], expected)
        for project in projects[127:131]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 19 errors", project["reason"])
                self.assertFalse(project["reason"].startswith("Source audit projection"))

    def test_reviewed_graph_nineteen_native_projection_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/sonic", "ecc59065227009230b8f52701948de495ec22a58"),
            ("external/libavc", "82092580f1dafe88defd88f873016b585bbd9e52"),
            ("external/libhevc", "c83a76b084498d55f252f48b2e3786804cdf24b7"),
            ("external/libmpeg2", "a97c2a1f0a796dc32bed80d3353c69c5fc07c750"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[131:135]], expected)
        for project in projects[131:135]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 19 error:"))

    def test_graph_nineteen_platform_properties_source_pin(self):
        projects = dependencies.load_config()["projects"]
        self.assertEqual(projects[135], {
            "path": "system/libsysprop",
            "url": "https://android.googlesource.com/platform/system/libsysprop",
            "commit": "0abfc7ad91e9914459b11e65a572de9f8a546365",
            "tag": "android-16.0.0_r1",
            "reason": "Real AOSP PlatformProperties sysprop sources generating libplatformproperties_rust for libhypervisor_props in the graph 19 error. Existing generators and API/type checks remain unchanged."
        })

    def test_graph_twenty_webrtc_source_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/webrtc", "57ee4f162c0f4b3ab68faf26596437033f0fa2ba"),
            ("external/libsrtp2", "3a2bd469a7219556aa17ea771c4887ad94160f7c"),
            ("external/pffft", "efa0bc5d226e063f65b21afd35390cce22e8e09d"),
            ("external/rnnoise", "1295d6828459cc82c3c29cc5d7d297215250a74b"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[136:140]], expected)
        for project in projects[136:140]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 20", project["reason"])
                self.assertFalse(project["reason"].startswith("Source audit projection"))
        self.assertIn("webrtc_audio_processing", projects[136]["reason"])
        self.assertIn("libaudiopreprocessing", projects[136]["reason"])
        self.assertIn("preserving the original SRTP fuzzer", projects[137]["reason"])

    def test_graph_twenty_python_provider_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/python/absl-py", "7b59b5e5824651c2c65bf35dcd950a091cf286a5", "absl-py"),
            ("external/scapy", "f377b770d982debb11f5e988d0f65b9e7c5ecd81", "scapy"),
            ("tools/test/mobly_extensions", "9b4d9968df2deea5164340bad0c46f724aa5a4f0", "mobly_device_flags"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[140:143]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[140:143], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 20", project["reason"])
                self.assertIn(module, project["reason"])
                self.assertFalse(project["reason"].startswith("Source audit projection"))

    def test_graph_twenty_minigbm_source_pin(self):
        projects = dependencies.load_config()["projects"]
        self.assertEqual(projects[143], {
            "path": "external/minigbm",
            "url": "https://android.googlesource.com/platform/external/minigbm",
            "commit": "10d2dbeec1d248e7a040ecab225a075caa34b2bf",
            "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libgbm_sys bindings and libgbm provider required by libgbm_rust in the graph 20 error. Upstream build properties remain unchanged."
        })

    def test_graph_twenty_one_watchdog_source_pin(self):
        projects = dependencies.load_config()["projects"]
        self.assertEqual(projects[144], {
            "path": "external/python/watchdog",
            "url": "https://android.googlesource.com/platform/external/python/watchdog",
            "commit": "228887b8167a3cd9f43e04b305f7f9af32ced0d5",
            "tag": "android-16.0.0_r1",
            "reason": "Real AOSP watchdog provider required by edit_monitor_lib in the graph 21 error."
        })

    def test_graph_twenty_one_native_provider_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/curl", "80fe7404cfd198a477ffe3d5865c630e33e94adf", "libcurl"),
            ("external/libldac", "ba0389d2de9727375b779fb5890747a8d7dfe3a0", "libldacBT_abr and libldacBT_enc"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[145:147]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[145:147], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 21", project["reason"])
                self.assertIn(module, project["reason"])
                self.assertFalse(project["reason"].startswith("Source audit projection"))
        self.assertIn("preserves the upstream fuzzer", projects[146]["reason"])

    def test_reviewed_graph_twenty_two_projection_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/libwebm", "https://android.googlesource.com/platform/external/libwebm",
             "103e46e4cd4b6efcf6001f23fa8665fb110abf8d", "libwebm_mkvparser"),
            ("trusty/user/base", "https://android.googlesource.com/trusty/lib",
             "388e1c4f148264da6f97c54806c099b609c04e48", "libtrustystorageinterface"),
            ("external/pdfium", "https://android.googlesource.com/platform/external/pdfium",
             "61aafefc3df2bda22588c7764d1177018f0af4e4", "libpdfium_static"),
            ("prebuilts/bundletool", "https://android.googlesource.com/platform/prebuilts/bundletool",
             "4d55b55cd444c97bc021d35316010f57f62d7844", "bundletool"),
            ("external/libxaac", "https://android.googlesource.com/platform/external/libxaac",
             "30de3a01def68d7f856f5e3795f7f806c93ed2f5", "libxaacdec"),
        ]
        self.assertEqual([(project["path"], project["url"], project["commit"]) for project in projects[147:152]],
                         [(path, url, commit) for path, url, commit, _ in expected])
        for project, (_, _, _, module) in zip(projects[147:152], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn(module, project["reason"])
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 22 error:"))
        self.assertIn("upstream lib/pmu/include symlink", projects[148]["reason"])
        self.assertIn("absent trusty/kernel/lib/pmu/include", projects[148]["reason"])
        self.assertIn("no kernel source is added", projects[148]["reason"])
        for caveat in ("base/allocator/partition_allocator/*.cc", "skia_shared/*.cpp",
                       "match no files", "dib/cfx_dibextractor.cpp", "fx_ge_linux.cpp",
                       "No files or build properties are changed"):
            self.assertIn(caveat, projects[149]["reason"])

    def test_graph_twenty_two_java_provider_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/libphonenumber", "467b37350ac0c881864fac79358ecaa1265bcc54", "libphonenumber-platform"),
            ("external/caliper", "dab7f1ed7741aaa71102341533da32d312563359", "caliper-api-target"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[152:154]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[152:154], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 22 error", project["reason"])
                self.assertIn(module, project["reason"])
                self.assertFalse(project["reason"].startswith("Source audit projection"))
        self.assertIn("libphonenumber-nogeocoder", projects[152]["reason"])

    def test_reviewed_graph_twenty_two_additional_projection_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("frameworks/minikin", "1e1d5d137d487df875d7db69b5ff24e7d0291612", "libminikin"),
            ("external/accessibility-test-framework", "35527c4073b7219b33e4cb52290b1a577a68810c", "aatf"),
            ("external/jsoup", "1c57858b5fc8a56e1c284dc60c59a68e7300ae2b", "jsoup"),
            ("external/ksoap2", "405109123a9513ed7ec91529d62f4f2e040c01ee", "ksoap2"),
            ("external/nanohttpd", "4711b67f075d8ed195ca46785b125dbea03982c3", "libnanohttpd"),
            ("frameworks/libs/service_entitlement", "9bdaed61465be24bccdc928bc4d042c8b512fb1d", "service-entitlement"),
            ("external/nist-sip", "1db572a42315b95f37311478b7701b607fd9810a", "nist-sip"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[154:161]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[154:161], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn(module, project["reason"])
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 22 error:"))

    def test_graph_twenty_two_chre_restoration_dependency_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/pigweed", "6b21bb2df225f4559fcfe495a73d20ba11d87d60", "Pigweed pw_*"),
            ("external/emboss", "c003e8aff9ab3dce46d1ba22c9002541e45c5178",
             "emboss_compiler, embossc_script and emboss_runtime_headers"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[161:163]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[161:163], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn(module, project["reason"])
                self.assertTrue(project["reason"].startswith(
                    "Dependency of the full CHRE source restoration for the graph 22 chre_flags error:"))

    def test_reviewed_graph_twenty_three_renderscript_projection_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("frameworks/rs", "0b7a6a27c1a995a9b5969582599248888799b167", "libRSDriver"),
            ("frameworks/compile/libbcc", "5b81b8df3c0e34c5e88ce4d913178e852ce2f072", "libbcinfo"),
            ("frameworks/compile/slang", "90ad5a5e7c9a8b8e36bc4f82421e7f51745a6059", "llvm-rs-cc"),
            ("external/cblas", "9a08d559988d01c83eae1d7f0ed8bf1a99c756a1", "libblasV8"),
            ("prebuilts/ndk", "e0e58e67cd11713799cdf6b50ba5843d62881660", "cpufeatures"),
            ("external/xmp_toolkit", "4581aa1b0230c0aa1683e2564afc4687f3a22b48", "xmp_toolkit"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[163:169]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[163:169], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn(module, project["reason"])
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 23 error:"))

    def test_reviewed_graph_twenty_three_telephony_projection_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("packages/services/Telephony", "3066368aaebabf12ee002da3a6ceb46169a79071", "ecc-protos-lite"),
            ("packages/apps/PhoneCommon", "8167c931b193b19a14de2ebe94b5081e34772732", "com.android.phone.common-lib"),
            ("external/s2-geometry-library-java", "221a93fa99a93436336816289d06bc487e3ee294", "s2-geometry-library-java"),
            ("packages/modules/GeoTZ", "15cb260974f84795cf6f415296d79cc26e97f010", "s2storage_ro, s2storage_rw and s2storage_tools"),
            ("external/geojson-jackson", "8a46ab3fb500c34471b26fd77c85b0fff3c9a752", "geojson-jackson"),
            ("external/jackson-annotations", "0f61d1a12af53066055fcde3f094dd385041481e", "jackson-annotations"),
            ("external/jackson-databind", "94510fd06c9dc10c1deb211d30b1cb153a764fb7", "jackson-databind"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[169:176]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[169:176], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn(module, project["reason"])
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 23 error:"))

    def test_graph_twenty_three_provider_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("tools/trebuchet", "ce9f55a2ba161e0363727fe85178c67c4b5341ca", "trebuchet-core"),
            ("external/easymock", "06a9728c3609f856e87db38a6602196cec3ab727", "easymock"),
            ("external/cpu_features", "3aed778c722edb68321d66a5e1cd7b35ae2c891c", "libcpu_features"),
            ("external/google-breakpad", "9712c20fc9bbfbac4935993a2ca0b3958c5adad2", "breakpad_client"),
            ("external/deqp", "230a1897a8c33452735a02a17c63f3c9c6bcb2b1", "CtsDeqpRunnerTests"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[176:181]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[176:181], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 23", project["reason"])
                self.assertIn(module, project["reason"])
                self.assertFalse(project["reason"].startswith("Source audit projection"))

    def test_graph_twenty_three_deqp_dependency_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/deqp-deps/SPIRV-Headers", "aa7b8a45763915dc5ad8f9537232e84e3796a33a", "SPIR-V headers"),
            ("external/deqp-deps/SPIRV-Tools", "7935793a768d7f6c6b0671cc61fda3286841da0e", "deqp_spirv-tools"),
            ("external/deqp-deps/glslang", "0733c837682fd25e3363b598947126ff1838908c", "glslang libraries"),
            ("external/deqp-deps/amber", "166c03c471039f3efc935a68d89b52521870ffd9", "deqp_amber"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[181:185]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[181:185], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn(module, project["reason"])
                self.assertTrue(project["reason"].startswith(
                    "Dependency of the dEQP restoration for the graph 23 CtsDeqpRunnerTests error:"))
        for caveat in ("deqp_glslang_ResourceLimits_headers", "glslang/Public/ResourceLimits.h",
                       "a header file, as an include directory", "original property is retained"):
            self.assertIn(caveat, projects[183]["reason"])

    def test_reviewed_graph_twenty_four_crosvm_projection_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/crosvm", "8a4abfbaea5567de24e49cc43874c820098987d0", "libfuse_rust"),
            ("external/virtio-media", "fef1c2fb80d79b5c526e0c7e40b6bb8838f17786", "libvirtio_media"),
            ("external/wayland", "91dc38d8c70bd5fc6eaca346c52f5eef1c02a1fb", "libwayland_client_static"),
            ("external/wayland-protocols", "91460fd294110884e6fa5d96ac7ce9c8c67f6339", "libwayland_extension_client_protocols"),
            ("external/libepoxy", "220661d543ca0cd3cd73b0e87868064ad4d1e834", "libepoxy"),
            ("external/virglrenderer", "34d8dbfc7ba18adf8d012a469c26fe00cd0f796e", "libvirglrenderer"),
            ("hardware/google/gfxstream", "fc0dca02291e1d5ba1d2dad1d0b58b4f2ef255d0", "libgfxstream_backend"),
            ("external/rust/crates/v4l2r", "6397d7473aa4dda5edc7ec4f9e58c7d0962f08e7", "libv4l2r_ffi_static"),
            ("external/mesa3d", "1ab807486dbc8cd2a1bb6c10d2ebebc5e545faca", "mesa_gfxstream_connection_manager"),
            ("external/swiftshader", "a4305fb793e7a96b3e1baf248b9717f68eedd238", "libLLVM16_swiftshader"),
        ]
        self.assertEqual([(project["path"], project["commit"]) for project in projects[185:195]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[185:195], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn(module, project["reason"])
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 24 error:"))
        for seed in ("libfuse_rust", "libdisk", "libcrosvm_control_static", "retained AVF"):
            self.assertIn(seed, projects[185]["reason"])
        self.assertIn("plugin registration and validation are preserved", projects[191]["reason"])
        self.assertIn("LLVM and vendor properties remain unchanged", projects[193]["reason"])
        self.assertIn("features and vendor declarations are preserved", projects[194]["reason"])

    def test_graph_twenty_four_car_team_metadata_source_pin(self):
        projects = dependencies.load_config()["projects"]
        self.assertEqual(projects[195], {
            "path": "packages/services/Car",
            "url": "https://android.googlesource.com/platform/packages/services/Car",
            "commit": "61256ae811853028effed5c2c7227aebc347dc5e",
            "tag": "android-16.0.0_r1",
            "reason": "Real AOSP team metadata for the graph 24 trendy_team_aaos_power_triage error and retained VTS ownership. The full Car project is pinned, but build selection is limited to packages/services/Car/teams/Android.bp and its nine team definitions; no Car runtime, flag or proto libraries are selected."
        })

    def test_graph_twenty_five_fdlibm_source_pin(self):
        projects = dependencies.load_config()["projects"]
        self.assertEqual(projects[196], {
            "path": "external/fdlibm",
            "url": "https://android.googlesource.com/platform/external/fdlibm",
            "commit": "2e70335919bce0de03d619c57d4b7a98f848fd52",
            "tag": "android-16.0.0_r1",
            "reason": "Real AOSP libfdlibm provider required by libopenjdk and libopenjdkd in the graph 25 errors."
        })

    def test_graph_twenty_six_nfc_and_printing_library_source_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/libcups", "19c37bb83c28ae3325b7a38b72d601fa0a28dde0", ("libcups",)),
            ("packages/modules/Nfc", "bdd94b3be31253e756355e6e22f2fe8983da6b1e",
             ("libnfc-nci", "libnfc_nci_jni")),
        ]
        self.assertGreaterEqual(len(projects), 199)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[197:199]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, modules) in zip(projects[197:199], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 26 errors", project["reason"])
                self.assertIn("retained CTS security cases", project["reason"])
                for module in modules:
                    self.assertIn(module, project["reason"])
        for fact in ("CVE-2019-2180", "CVE-2019-2228", "legacy_by_exception_only"):
            self.assertIn(fact, projects[197]["reason"])

    def test_graph_twenty_seven_exoplayer_source_pin(self):
        projects = dependencies.load_config()["projects"]
        self.assertGreaterEqual(len(projects), 200)
        self.assertEqual(projects[199], {
            "path": "external/exoplayer",
            "url": "https://android.googlesource.com/platform/external/exoplayer",
            "commit": "562c956cd875e623d041e0819f39125f903722c5",
            "tag": "android-16.0.0_r1",
            "reason": "Real AOSP exoplayer-media_apex provider required by framework-media.impl in the graph 27 errors. Original source modules and API settings are preserved; this source pin does not establish recovery media support."
        })

    def test_reviewed_exoplayer_jarjar_tool_projection_source_pin(self):
        projects = dependencies.load_config()["projects"]
        self.assertGreaterEqual(len(projects), 201)
        self.assertEqual(projects[200], {
            "path": "external/jarjar",
            "url": "https://android.googlesource.com/platform/external/jarjar",
            "commit": "96b8d0a67118121374f3ed1962e876e533e8908b",
            "tag": "android-16.0.0_r1",
            "reason": "Source audit projection, not a graph 27 error: real AOSP jarjar host Java library supplies jarjar.jar for the original Soong relocation rule used by ExoPlayer jarjar_rules. Original tool, bundled Maven and Ant imports, and tests are preserved."
        })

    def test_reviewed_framework_docs_switcher_tool_projection_source_pin(self):
        projects = dependencies.load_config()["projects"]
        self.assertGreaterEqual(len(projects), 202)
        self.assertEqual(projects[201], {
            "path": "tools/doc_generation",
            "url": "https://android.googlesource.com/platform/tools/doc_generation",
            "commit": "8fb605eb38e53e74c1408ea01d4b7dd6be8ce467",
            "tag": "android-16.0.0_r1",
            "reason": "Source audit projection, not a graph 27 error: real AOSP switcher4 host Python tool required by the retained ds-docs-switched generator in frameworks/base/api/ApiDocs.bp. Original documentation consumers and tool definitions remain selected."
        })

    def test_graph_twenty_eight_python_and_java_provider_source_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/mpdecimal", "ed7ca08a5e74aab5f0c5a15cbc08f2364dbe69a3",
             "libmpdec", ("py3-c-modules",)),
            ("external/moshi", "57cf8f201e673c82d1640738c5928ed758a4ff75",
             "moshi", ("androidx.benchmark_benchmark-common",)),
            ("external/mockftpserver", "59892565b6b7f8e60db9299b4bb7ace4a16dff7a",
             "mockftpserver", ("core-tests",)),
            ("external/javasqlite", "0bdef7b65a85435705cf37408cb3e438d2c2f64e",
             "sqlite-jdbc", ("core-tests",)),
            ("external/mockwebserver", "a94bb9bc1f426fc1ae3e892ff08f0efeb763a809",
             "mockwebserver", ("core-tests", "core-ojtests", "core-ojtests-public")),
            ("external/nist-pkits", "ee62ccc6b7665d12a4328db024f449f7ca5320fb",
             "nist-pkix-tests", ("core-tests",)),
        ]
        self.assertGreaterEqual(len(projects), 208)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[202:208]],
                         [(path, commit) for path, commit, _, _ in expected])
        for project, (_, _, module, consumers) in zip(projects[202:208], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 28 errors", project["reason"])
                self.assertIn(module, project["reason"])
                self.assertNotIn("projection", project["reason"].lower())
                for consumer in consumers:
                    self.assertIn(consumer, project["reason"])
        self.assertIn("retained Android", projects[202]["reason"])
        self.assertIn("generated header and visibility rules are preserved", projects[202]["reason"])
        self.assertIn("license metadata are preserved", projects[205]["reason"])

    def test_graph_twenty_nine_bluetooth_java_provider_source_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("frameworks/opt/vcard", "09192f417d6f105cee940f566c0daa0db5fddb20",
             "com.android.vcard"),
            ("hardware/ril", "6bd627062458024e2cd1c13cf3d0b6c71cdfa495",
             "sap-api-java-static"),
        ]
        self.assertGreaterEqual(len(projects), 210)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[208:210]],
                         [(path, commit) for path, commit, _ in expected])
        for project, (_, _, module) in zip(projects[208:210], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 29 errors", project["reason"])
                self.assertIn("BluetoothLib", project["reason"])
                self.assertIn(module, project["reason"])
                self.assertNotIn("projection", project["reason"].lower())
        self.assertIn("SDK settings and test descriptors are preserved", projects[208]["reason"])
        self.assertIn("Java, native and protocol definitions are preserved", projects[209]["reason"])

    def test_graph_thirty_confirmation_ui_and_compose_provider_source_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/lottie", "649ad7a4c743cd110b6cdda764f832b088f1d953",
             "lottie_compose", ("SpaLib",)),
            ("external/cn-cbor", "250a8956c5106b42b96f66c660141693d0ed35ea",
             "libcn-cbor", ("VtsHalConfirmationUITargetTest", "VtsHalConfirmationUIV1_0TargetTest")),
        ]
        self.assertGreaterEqual(len(projects), 212)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[210:212]],
                         [(path, commit) for path, commit, _, _ in expected])
        for project, (_, _, module, consumers) in zip(projects[210:212], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertIn("graph 30 errors", project["reason"])
                self.assertIn(module, project["reason"])
                self.assertNotIn("projection", project["reason"].lower())
                for consumer in consumers:
                    self.assertIn(consumer, project["reason"])
        self.assertIn("dependencies and SDK settings are preserved", projects[210]["reason"])
        self.assertIn("retained Confirmation UI security tests are preserved", projects[211]["reason"])

    def test_reviewed_framework_extensions_projection_source_pin(self):
        projects = dependencies.load_config()["projects"]
        self.assertGreaterEqual(len(projects), 213)
        self.assertEqual(projects[212], {
            "path": "frameworks/ex",
            "url": "https://android.googlesource.com/platform/frameworks/ex",
            "commit": "06933c05c643430497ea48c713db04c0feb70d2e",
            "tag": "android-16.0.0_r1",
            "reason": "Source audit projection, not a graph 30 error: real AOSP android-common, android-ex-camera2 and androidx.camera.extensions.stub providers required by retained framework and CTS consumers, including CtsPermissionTestCases. Original library, test and SDK definitions are preserved."
        })

    def test_graph_thirty_one_framework_source_batch_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("packages/modules/CellBroadcastService", "1249b4c132181f66cbc5a36168570f12390b4b2d"),
            ("packages/apps/CellBroadcastReceiver", "b97c8a4ffa3946d7206808bf4810746678b44a5c"),
            ("packages/apps/Settings", "0fb38ed81e9b49d5da4be8f50d9d69865c1192e8"),
            ("packages/apps/Launcher3", "2f5b9b869d86620fdb899bc2df53d523dc9dc6ea"),
            ("packages/apps/Traceur", "781a9de78af68f825dc0031457c5fc12ff58cf39"),
            ("frameworks/opt/setupwizard", "8346eb25a87c195812e9255757ae8d3b47173da9"),
            ("external/setupdesign", "07da2d12899c8a083060b9bdd77473fa93564567"),
            ("external/setupcompat", "5e79860031bf30df936ebc08db2996874eb0ff9e"),
            ("external/zxing", "32fbdf1955cc1fad33e6a791284d316dc3834d1b"),
            ("external/subsampling-scale-image-view", "7c166c441cfc7d2de61396e7ebc0e574c5c6c585"),
            ("external/google-fonts/dancing-script", "56d6ed7d67ef97d12eae22d95aea33aab2270e1d"),
        ]
        self.assertGreaterEqual(len(projects), 224)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[213:224]], expected)
        for project in projects[213:224]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")

    def test_graph_thirty_one_source_reasons_and_scope_limits(self):
        projects = dependencies.load_config()["projects"]
        actual_consumers = {
            "external/setupdesign": ("setupdesign", "SettingsLibAvatarPicker"),
            "external/setupcompat": ("setupcompat", "android_onboarding.contracts.provisioning"),
        }
        for project in projects[213:224]:
            with self.subTest(path=project["path"]):
                reason = project["reason"]
                if project["path"] in actual_consumers:
                    self.assertIn("graph 31 errors", reason)
                    self.assertNotIn("projection", reason.lower())
                    for name in actual_consumers[project["path"]]:
                        self.assertIn(name, reason)
                else:
                    self.assertTrue(reason.startswith("Source audit projection, not a graph 31 error:"))
        for text in ("statslog-cellbroadcast-java-gen", "telephony-common"):
            self.assertIn(text, projects[213]["reason"])
        for text in ("apex/permissions/Android.bp", "no receiver app or APEX definition"):
            self.assertIn(text, projects[214]["reason"])
        for text in ("aconfig_settings_flags_lib", "root Blueprint", "Settings-core", "Settings app"):
            self.assertIn(text, projects[215]["reason"])
        for text in ("com_android_launcher3_flags_lib", "launcher-aosp-tapl", "WindowManager-Shell"):
            self.assertIn(text, projects[216]["reason"])
        for text in ("TraceurCommon", "Traceur-res", "Traceur app", "without adding product packages"):
            self.assertIn(text, projects[217]["reason"])
        for text in ("setup-wizard-lib", "SimAppDialog", "gingerbread compatibility library"):
            self.assertIn(text, projects[218]["reason"])
        self.assertIn("zxing-core-1.7 prebuilt, its version metadata", projects[221]["reason"])
        for text in ("SilkFX android_test", "test dependency", "no TWRP runtime feature"):
            self.assertIn(text, projects[222]["reason"])
        for text in ("GoogleFontDancingScript", "CorePerfTests", "Java test data",
                     "does not establish a TWRP font installation requirement", "BSD/MIT/OFL",
                     "special licensing notice", "no license waiver", "distribution rights"):
            self.assertIn(text, projects[223]["reason"])

    def test_graph_thirty_one_glide_prebuilt_source_pin_and_packaging_caveat(self):
        projects = dependencies.load_config()["projects"]
        self.assertGreaterEqual(len(projects), 225)
        project = projects[224]
        self.assertEqual({key: project[key] for key in ("path", "url", "commit", "tag")}, {
            "path": "prebuilts/maven_repo/bumptech",
            "url": "https://android.googlesource.com/platform/prebuilts/maven_repo/bumptech",
            "commit": "5fa5ea996556070a62957f197876d124f3a1e1b7",
            "tag": "android-16.0.0_r1",
        })
        self.assertNotIn("external/glide", {p["path"] for p in projects[213:225]})
        reason = project["reason"]
        self.assertIn("graph 31 errors", reason)
        self.assertNotIn("projection", reason.lower())
        for name in ("glide-prebuilt", "glide-gifdecoder-prebuilt", "glide-disklrucache-prebuilt",
                     "glide-annotation-and-compiler-prebuilt", "glide-ktx-prebuilt",
                     "glide-integration-webpdecoder-prebuilt", "glide-compose-prebuilt",
                     "glide-annotation-processor", "car-telephony-common-source-no-overlayable",
                     "car-telephony-common-source", "car-telephony-common-aar", "PhotopickerLib"):
            self.assertIn(name, reason)
        for caveat in ("original WebP import", "webpdecoder-2.6.4.16.0-sources.jar",
                       "Java sources and no compiled classes",
                       "does not establish WebP or application runtime support"):
            self.assertIn(caveat, reason)

    def test_reviewed_systemui_robolectric_mime_and_turbine_source_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("frameworks/libs/systemui", "9aacbcb77aa9353e75bc7c4ebc51d20b8b241b62"),
            ("external/robolectric", "559c38b2cb0fbd87f2118bdcb8bea6f536164d70"),
            ("external/mime-support", "c347c3d8fa4992e655674e6c9f2baa6e18e44ead"),
            ("external/turbine", "babc164379486626467efc50db0833d683c39fd5"),
        ]
        self.assertGreaterEqual(len(projects), 229)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[225:229]], expected)
        for project in projects[225:229]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")

    def test_shared_graph_provider_reasons_preserve_runtime_and_tool_boundaries(self):
        projects = dependencies.load_config()["projects"]
        systemui = projects[225]["reason"]
        self.assertIn("graph 31 errors", systemui)
        self.assertIn("SystemUI-shared-utils", systemui)
        self.assertIn("//frameworks/libs/systemui:view_capture", systemui)
        self.assertNotIn("projection", systemui.lower())
        for project in projects[226:229]:
            with self.subTest(path=project["path"]):
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 31 error:"))
        for text in ("Robolectric_all-target", "platform-parametric-runner-lib", "strict graph trial",
                     "does not establish compiled or runtime support"):
            self.assertIn(text, projects[226]["reason"])
        for text in ("debian.mime.types.minimized", "debian.mime.types.minimized-alt",
                     "frameworks/base/mime", "license metadata and generator definitions are preserved"):
            self.assertIn(text, projects[227]["reason"])
        for text in ("turbine java_library_host", "Kotlin and KAPT", "Always_use_prebuilt_sdks=false",
                     "framework/turbine.jar", "KatiInstalls", "no prebuilt substitution or flag change",
                     "does not claim a built JAR"):
            self.assertIn(text, projects[228]["reason"])
        self.assertNotIn("java_binary_host", projects[228]["reason"])

    def test_graph_thirty_two_source_provider_batch_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/glide", "2078ac4e2023465dd8f4473554ec65583b9267a6"),
            ("external/volley", "c34e6c11e6d8f47807f31fe1dbb655ab5ab4534b"),
            ("external/wycheproof", "bf75d8ae31587a5c81fe70533ea831728b3fdf0e"),
            ("packages/providers/ContactsProvider", "164078c92d23d173f0f0c986e298dd236d66279b"),
            ("packages/apps/TvSettings", "139dd3c1a8f626a57271baf4926180f8d1f3bade"),
            ("test/mlts/benchmark", "4617f7e28793f979153f3b088a79ba796e0268b3"),
            ("test/mlts/models", "cbb1ae5cfde49ed06ccf4afaa2fae1054364d4f3"),
        ]
        self.assertGreaterEqual(len(projects), 236)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[229:236]], expected)
        for project in projects[229:236]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")

    def test_graph_thirty_two_reasons_preserve_actual_and_transitive_boundaries(self):
        projects = dependencies.load_config()["projects"]
        actual_consumers = {
            "external/glide": ("glide source android_library", "CtsLeanbackJankApp"),
            "external/wycheproof": ("wycheproof", "wycheproof-keystore",
                                    "CtsLibcoreWycheproofBCTestCases",
                                    "CtsLibcoreWycheproofConscryptTestCases",
                                    "CtsKeystoreWycheproofTestCases"),
            "packages/providers/ContactsProvider": ("ContactsProviderTestUtils",
                                                     "E2eeContactKeysProviderTests",
                                                     "contactsprovider_flags_java_lib",
                                                     "CtsContactsProviderTestCases"),
            "packages/apps/TvSettings": ("TvSettingsAPI", "CtsSettingsAPITestCases"),
            "test/mlts/benchmark": ("NeuralNetworksApiBenchmark_Lib", "libnnbenchmark_jni",
                                    "VtsHalNeuralnetworksV1_2BenchmarkTestCases",
                                    "VtsHalNeuralnetworksV1_3BenchmarkTestCases"),
            "test/mlts/models": ("test_mlts_models_assets",
                                 "VtsHalNeuralnetworksV1_2BenchmarkTestCases",
                                 "VtsHalNeuralnetworksV1_3BenchmarkTestCases"),
        }
        for project in projects[229:236]:
            with self.subTest(path=project["path"]):
                reason = project["reason"]
                if project["path"] in actual_consumers:
                    self.assertIn("graph 32 errors", reason)
                    self.assertNotIn("projection", reason.lower())
                    for name in actual_consumers[project["path"]]:
                        self.assertIn(name, reason)
                else:
                    self.assertEqual(project["path"], "external/volley")
                    self.assertTrue(reason.startswith("Source audit projection, not a graph 32 error:"))
                    for text in ("volley", "original glide source library", "SDK 28",
                                 "optional org.apache.http.legacy dependency"):
                        self.assertIn(text, reason)
        self.assertIn("separate from the preserved graph 31 Glide prebuilt providers", projects[229]["reason"])
        self.assertNotIn("external/glide", {p["path"] for p in projects[:229]})
        self.assertIn("prebuilts/maven_repo/bumptech", {p["path"] for p in projects[:229]})
        for text in ("Original tests, test vectors", "optional empty keystore-cts/android/**/*.java"):
            self.assertIn(text, projects[231]["reason"])
        self.assertIn("without a new source scope or test gate", projects[232]["reason"])
        for text in ("SettingsAPI/Android.bp", "TwoPanelSettingsLib/Android.bp", "TvSliceLib",
                     "no TV app or root Blueprint is admitted"):
            self.assertIn(text, projects[233]["reason"])
        self.assertIn("does not establish performance or neural-network hardware support", projects[234]["reason"])
        for text in ("asset licenses and attribution metadata", "no asset redistribution rights determination",
                     "on-device neural-network support is implied"):
            self.assertIn(text, projects[235]["reason"])

    def test_reviewed_cts_plot_replica_and_tv_projection_source_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/androidplot", "e67b5c11b0a39d07706faa2f5faf820db3848005"),
            ("external/replicaisland", "f32cc0546b83dd918c94c37850109d311ebabcaf"),
            ("frameworks/opt/tv/tvsystem", "ddc4040688dca1b980b8744a012d6cf6a62f792c"),
        ]
        self.assertGreaterEqual(len(projects), 239)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[236:239]], expected)
        for project in projects[236:239]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")

    def test_cts_projection_reasons_preserve_upstream_api_tracking_choice(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("androidplot java_library", "CtsVerifierLibT"),
            ("com.replica.replicaisland android_test_helper_app", "CtsOpenGlPerfTestCases"),
            ("com.android.libraries.tv.tvsystem java_sdk_library",
             "CtsSharedLibsApiSignatureTestCases_cts-shared-libs-all-current.api"),
        ]
        for project, (provider, consumer) in zip(projects[236:239], expected):
            with self.subTest(path=project["path"]):
                reason = project["reason"]
                self.assertTrue(reason.startswith("Source audit projection, not a graph 33 error:"))
                self.assertNotIn("graph 33 errors", reason)
                self.assertIn(provider, reason)
                self.assertIn(consumer, reason)
        for text in ("complete original Blueprint", "AndroidPlotDemos", "compiler settings"):
            self.assertIn(text, projects[236]["reason"])
        for text in ("instrumentation_for and data", "preserved as test inputs",
                     "does not add a recovery product package or establish graphics performance"):
            self.assertIn(text, projects[237]["reason"])
        for text in (".public.api.txt", ".system.api.txt", "original unsafe_ignore_missing_latest_api:true",
                     "suppresses released API tracking", "current API checks remain",
                     "no new waiver is added", "No recovery product package or TV functionality is implied"):
            self.assertIn(text, projects[238]["reason"])

    def test_reviewed_camera_and_microdroid_projection_source_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/jetpack-camera-app", "https://android.googlesource.com/platform/external/jetpack-camera-app",
             "bff117dd925374b0023b6ca6e5a237fb5944e581"),
            ("external/accompanist", "https://android.googlesource.com/platform/external/accompanist",
             "f083e7c9735aa7806e6fa902923aa021881aee78"),
            ("kernel/prebuilts/6.6/arm64", "https://android.googlesource.com/kernel/prebuilts/6.6/arm64",
             "810308806a7a4677f8e4a0d37daa707a0832bbea"),
            ("kernel/prebuilts/6.6/x86_64", "https://android.googlesource.com/kernel/prebuilts/6.6/x86-64",
             "88d6379eab0da6425d570d22531c210e40f5abd6"),
            ("kernel/prebuilts/6.12/arm64", "https://android.googlesource.com/kernel/prebuilts/6.12/arm64",
             "0af99653adede9524c7dbb36ba901d22e6266404"),
            ("kernel/prebuilts/6.12/x86_64", "https://android.googlesource.com/kernel/prebuilts/6.12/x86-64",
             "0cbffc1bfc41e1e6d399a23d1ffe45875213b67f"),
        ]
        self.assertGreaterEqual(len(projects), 245)
        self.assertEqual([(p["path"], p["url"], p["commit"]) for p in projects[239:245]], expected)
        for project in projects[239:245]:
            with self.subTest(path=project["path"]):
                self.assertEqual(project["tag"], "android-16.0.0_r1")

    def test_camera_and_microdroid_reasons_preserve_guest_and_runtime_boundaries(self):
        projects = dependencies.load_config()["projects"]
        for project in projects[239:245]:
            with self.subTest(path=project["path"]):
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 34 error:"))
                self.assertNotIn("graph 34 errors", project["reason"])
        for text in ("jetpack-camera-app android_app", "other_required_apps in cts/apps/CtsVerifier",
                     "inert legacy subdirs assignment", "No APK, installation or camera functionality is claimed"):
            self.assertIn(text, projects[239]["reason"])
        for text in ("accompanist-permissions android_library", "jetpack-camera-app-tests-helper",
                     "jetpack-camera-app_feature_permissions", "jetpack-camera-app_feature_settings",
                     "SDK/minSDK checks are preserved", "no camera permission behavior or runtime compatibility"):
            self.assertIn(text, projects[240]["reason"])
        versions = [("android15", "6.6", "arm64"), ("android15", "6.6", "x86_64"),
                    ("android16", "6.12", "arm64"), ("android16", "6.12", "x86_64")]
        for project, (android, version, arch) in zip(projects[241:245], versions):
            with self.subTest(path=project["path"]):
                reason = project["reason"]
                self.assertIn(f"microdroid_gki_modules-{android}-{version}-{arch}", reason)
                self.assertIn(f"microdroid_gki-{android}-{version}_initrd_gen_{arch}", reason)
                for text in ("Generic AVF guest inputs only", "not Nezha recovery kernel, DTB, firmware or kernel-module inputs",
                             "Payload integrity and checkout size remain unverified",
                             "no built artifact or runtime support is claimed"):
                    self.assertIn(text, reason)

    def test_reviewed_car_settings_flags_projection_source_pin_and_scope(self):
        projects = dependencies.load_config()["projects"]
        self.assertGreaterEqual(len(projects), 246)
        project = projects[245]
        self.assertEqual({key: project[key] for key in ("path", "url", "commit", "tag")}, {
            "path": "packages/apps/Car/Settings",
            "url": "https://android.googlesource.com/platform/packages/apps/Car/Settings",
            "commit": "64634c7bfc79be369f0cd251d6c61df995cdf8b1",
            "tag": "android-16.0.0_r1",
        })
        reason = project["reason"]
        self.assertTrue(reason.startswith("Source audit projection, not a graph 34 error:"))
        self.assertNotIn("graph 34 errors", reason)
        for text in ("com_android_car_settings_flags_lib", "CtsSettingsTestCases",
                     "whole original project is pinned", "selection admits only aconfig/Android.bp",
                     "com_android_car_settings_flags", "Java flag library",
                     "No Car Settings app, APK installation or new test gate is added"):
            self.assertIn(text, reason)

    def test_graph_thirty_five_oboe_source_pin_and_reason(self):
        projects = dependencies.load_config()["projects"]
        self.assertGreaterEqual(len(projects), 247)
        project = projects[246]
        self.assertEqual({key: project[key] for key in ("path", "url", "commit", "tag")}, {
            "path": "external/oboe",
            "url": "https://android.googlesource.com/platform/external/oboe",
            "commit": "dd93a0db2d7458fceea325612623b9996feba378",
            "tag": "android-16.0.0_r1",
        })
        reason = project["reason"]
        self.assertIn("graph 35 error", reason)
        self.assertNotIn("projection", reason.lower())
        for text in ("oboe cc_library_static", "libaudioloopback_jni", "oboe_headers",
                     "SDK settings", "Apache-2.0/GPL-2.0/MIT license metadata are preserved",
                     "does not establish a built APK or audio-loopback functionality"):
            self.assertIn(text, reason)

    def test_reviewed_native_cts_projection_source_pins_and_reasons(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/seccomp-tests", "e175d3ba7741fe01a89e54ad5989aeb3293b0e3f",
             "external_seccomp_tests cc_library_static", "libctsos_jni"),
            ("packages/services/DeviceAsWebcam", "86c6b7e9b7217310836f7b8f75d0c764c148b6e5",
             "camera-webcam-test genrule", "android-cts-verifier genrule"),
        ]
        self.assertGreaterEqual(len(projects), 249)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[247:249]],
                         [(path, commit) for path, commit, _, _ in expected])
        for project, (_, _, provider, consumer) in zip(projects[247:249], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 36 error:"))
                self.assertNotIn("graph 36 errors", project["reason"])
                self.assertIn(provider, project["reason"])
                self.assertIn(consumer, project["reason"])
        for text in ("whole original project and Android Blueprint", "mixed Apache/GPL/LGPL license kinds",
                     "RESTRICTED metadata", "ancillary Linux Makefile is not invoked by Android.bp",
                     "no standalone Make support or licensing clearance is claimed"):
            self.assertIn(text, projects[247]["reason"])
        for text in ("All four original Blueprints", "app, library and JNI definitions, remain intact",
                     "No product package, app installation, signing-key access or webcam functionality is implied"):
            self.assertIn(text, projects[248]["reason"])

    def test_graph_forty_libgif_source_pin_and_reason(self):
        projects = dependencies.load_config()["projects"]
        self.assertGreaterEqual(len(projects), 250)
        project = projects[249]
        self.assertEqual({key: project[key] for key in ("path", "url", "commit", "tag")}, {
            "path": "external/giflib",
            "url": "https://android.googlesource.com/platform/external/giflib",
            "commit": "ad011248e266cc1bad1489704cc214942231cf09",
            "tag": "android-16.0.0_r1",
        })
        reason = project["reason"]
        self.assertIn("graph 40 errors", reason)
        self.assertNotIn("projection", reason.lower())
        for text in ("libgif cc_library_static", "libhwui and hwui_unit_tests",
                     "Android target of android_graphics_jni", "whole original project and Blueprint",
                     "exported headers", "SDK settings", "MIT license metadata are preserved",
                     "does not establish compiled HWUI or GIF rendering functionality"):
            self.assertIn(text, reason)

    def test_graph_forty_one_ethtool_source_pin_and_reason(self):
        projects = dependencies.load_config()["projects"]
        self.assertGreaterEqual(len(projects), 251)
        project = projects[250]
        self.assertEqual({key: project[key] for key in ("path", "url", "commit", "tag")}, {
            "path": "external/ethtool",
            "url": "https://android.googlesource.com/platform/external/ethtool",
            "commit": "9d3d10f9bbb011b10c2f9bb4527ee8bc942d3914",
            "tag": "android-16.0.0_r1",
        })
        reason = project["reason"]
        self.assertIn("graph 41 error", reason)
        self.assertNotIn("projection", reason.lower())
        for text in ("ethtool cc_binary", "com.android.tethering",
                     "whole original project and Blueprint", "bundled libmnl sources",
                     "original GPL/LGPL license metadata", "min_sdk_version 30", "installable false",
                     "existing apex_available entries", "Original unmatched source globs remain unchanged",
                     "No separate libmnl checkout or app activation is added",
                     "no tethering or network functionality is claimed"):
            self.assertIn(text, reason)

    def test_reviewed_graph_forty_three_font_projection_pins_and_metadata(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/google-fonts/carrois-gothic-sc", "317d5aad96dac8c1c6ac70fe7f1f77aa0a0bc178", "CarroisGothicSC", "BSD/MIT/OFL"),
            ("external/google-fonts/coming-soon", "e72d9ee22b601fd4e4ae56adc3b74a3d455364e3", "ComingSoon", "Apache-2.0"),
            ("external/google-fonts/cutive-mono", "f9e9dbc9604e91245765ba59c405712f618ac9bd", "CutiveMono", "BSD/MIT/OFL"),
            ("external/roboto-flex-fonts", "e9deeba80f18a1348a113f8ce954f0e5248fabde", "RobotoFlex", "OFL"),
            ("external/google-fonts/source-sans-pro", "ea777a6c3d98a14c34605c56e1cf36251fd8040b", "SourceSansPro", "legacy_by_exception_only"),
        ]
        self.assertGreaterEqual(len(projects), 256)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[251:256]],
                         [(path, commit) for path, commit, _, _ in expected])
        for project, (_, _, module, license_note) in zip(projects[251:256], expected):
            with self.subTest(path=project["path"]):
                self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
                self.assertEqual(project["tag"], "android-16.0.0_r1")
                reason = project["reason"]
                self.assertTrue(reason.startswith("Source audit projection, not a graph 43 error:"))
                for text in (module + " filegroup", "generate_font_fallback", "whole original project",
                             "configuration", license_note, "No font rendering or redistribution rights are claimed"):
                    self.assertIn(text, reason)
        for index in (251, 253, 255):
            self.assertIn("special licensing notices are preserved", projects[index]["reason"])
        self.assertIn("all six font prebuilts", projects[255]["reason"])

    def test_reviewed_graph_forty_three_fhir_and_shflags_projection_pins(self):
        projects = dependencies.load_config()["projects"]
        expected = [
            ("external/fhir/spec/r4", "8feeb7dabdaf4b99434215b64a8295cf6fc0d0d0"),
            ("external/shflags", "ca94e59d5633e0da49cfa9a999b565ca630e1b3d"),
        ]
        self.assertGreaterEqual(len(projects), 258)
        self.assertEqual([(p["path"], p["commit"]) for p in projects[256:258]], expected)
        for project in projects[256:258]:
            self.assertEqual(project["url"], "https://android.googlesource.com/platform/" + project["path"])
            self.assertEqual(project["tag"], "android-16.0.0_r1")
            self.assertTrue(project["reason"].startswith("Source audit projection, not a graph 43 error:"))
            self.assertIn("whole original project", project["reason"])
        for text in ("resource-definitions and type-definitions filegroups", "generate-fhir-spec-r4-binarypb",
                     "generate-fhir-spec-r4-textproto", "original visibility", "LICENSE", "MODULE_LICENSE_CC0-1.0",
                     "no package or license module is synthesized", "No generated artifact or runtime functionality is claimed"):
            self.assertIn(text, projects[256]["reason"])
        for text in ("shflags sh_binary_host", "required dependency", "host brillo_update_payload",
                     "during the Make stage, not an observed Soong error", "Apache-2.0 license metadata",
                     "No installed recovery tool or payload-generation success is claimed"):
            self.assertIn(text, projects[257]["reason"])

    def test_reviewed_graph_forty_three_cuttlefish_projection_pin_and_caveats(self):
        projects = dependencies.load_config()["projects"]
        self.assertEqual(len(projects), 259)
        project = projects[258]
        self.assertEqual({key: project[key] for key in ("path", "url", "commit", "tag")}, {
            "path": "device/google/cuttlefish",
            "url": "https://android.googlesource.com/device/google/cuttlefish",
            "commit": "c6a8b05c38d88e8d19b83fd8d47f75c0686f2e69",
            "tag": "android-16.0.0_r1",
        })
        self.assertNotIn("/platform/", project["url"])
        reason = project["reason"]
        self.assertTrue(reason.startswith("Source audit projection, not a graph 43 error:"))
        for text in ("com.google.cf.apex.key", "com.google.cf.apex.certificate", "append_squashfs_overlay host tool",
                     "APEX and OpenWrt generators", "whole original project is pinned",
                     "only apex/keys/Android.bp and host/commands/append_squashfs_overlay/Android.bp",
                     "append_squashfs_overlay.test", "global Apache metadata", "Original CleanSpec behavior is preserved",
                     "clean_steps.mk was absent at admission and must be checked again before graph/Kati",
                     "No Cuttlefish device selection, key payload access or runtime support is implied"):
            self.assertIn(text, reason)

    def test_large_synthetic_source_sets_fit_existing_configuration_limits(self):
        for count in (122, 127):
            with self.subTest(count=count):
                self.config["projects"] = [dict(self.project,
                    path=f"external/synthetic-{index:03d}",
                    url=f"https://android.googlesource.com/platform/external/synthetic-{index:03d}")
                    for index in range(count)]
                self.save_config()
                with patch.object(twrp_workspace, "run", side_effect=AssertionError("No process")):
                    self.assertEqual(len(dependencies.load_config(self.control)["projects"]), count)
                self.assertLess((self.control / dependencies.CONFIG).stat().st_size, 1024 * 1024)

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

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import camerax_extension_cache as cache


def archive(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as output:
        for name, data in entries:
            output.writestr(name, data)
    return stream.getvalue()


class CameraXExtensionCacheTests(unittest.TestCase):
    def test_backport_preserves_resources_other_classes_and_kotlin_module(self):
        original_jar = archive([
            ("cache/Main.class", b"old-main"), ("cache/Main$Async.class", b"old-async"),
            ("cache/Factory.class", b"unchanged-factory"),
            ("META-INF/library.kotlin_module", b"original-module"),
        ])
        original = archive([("classes.jar", original_jar), ("AndroidManifest.xml", b"manifest"),
                            ("proguard.txt", b"rules"), ("res/values/strings.xml", b"resources")])
        compiled = archive([("cache/Main.class", b"fixed-main"),
                            ("cache/Main$Async.class", b"fixed-async"),
                            ("META-INF/library.kotlin_module", b"single-source-module")])
        output, receipt = cache.rebuild_aar(original, compiled,
                                           ["cache/Main.class", "cache/Main$Async.class"])
        _, before = cache.members(original)
        _, after = cache.members(output)
        self.assertEqual({k: v for k, v in before.items() if k != "classes.jar"},
                         {k: v for k, v in after.items() if k != "classes.jar"})
        _, classes = cache.members(after["classes.jar"])
        self.assertEqual(classes["cache/Main.class"], b"fixed-main")
        self.assertEqual(classes["cache/Main$Async.class"], b"fixed-async")
        self.assertEqual(classes["cache/Factory.class"], b"unchanged-factory")
        self.assertEqual(classes["META-INF/library.kotlin_module"], b"original-module")
        self.assertEqual(receipt["unchanged_class_jar_members"], 2)
        self.assertEqual(receipt["unchanged_outer_members"], 3)
        self.assertEqual(cache.rebuild_aar(original, compiled,
                                          ["cache/Main.class", "cache/Main$Async.class"])[0], output)

    def test_unexpected_compiler_class_is_rejected(self):
        original = archive([("classes.jar", archive([("cache/Main.class", b"old")]))])
        generated = archive([("cache/Main.class", b"new"), ("cache/Other.class", b"extra")])
        with self.assertRaisesRegex(ValueError, "unexpected class set"):
            cache.rebuild_aar(original, generated, ["cache/Main.class"])

    def test_missing_compiler_class_is_rejected(self):
        original = archive([("classes.jar", archive([("cache/Main.class", b"old")]))])
        with self.assertRaisesRegex(ValueError, "unexpected class set"):
            cache.rebuild_aar(original, archive([]), ["cache/Main.class"])

    def test_new_class_cannot_be_injected(self):
        original = archive([("classes.jar", archive([("cache/Other.class", b"old")]))])
        with self.assertRaisesRegex(ValueError, "absent from original"):
            cache.rebuild_aar(original, archive([("cache/Main.class", b"new")]), ["cache/Main.class"])

    def test_unsafe_member_is_rejected(self):
        for name in ("../escape", "/absolute", "windows\\path"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Unsafe ZIP member"):
                cache.members(archive([(name, b"data")]))

    def test_source_and_patch_pins_are_recomputed(self):
        contract = json.loads(cache.CONTRACT.read_text())
        for name in ("template", "patch"):
            self.assertEqual(cache.identity(cache.ROOT / contract[name]), contract[name + "_identity"])

    def test_changed_input_is_rejected_before_compilation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input"
            path.write_bytes(b"measured")
            expected = {"sha256": hashlib.sha256(b"measured").hexdigest(), "size_bytes": 8}
            cache.checked(path, expected)
            path.write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "Input identity differs"):
                cache.checked(path, expected)

    def test_abi_order_is_irrelevant_but_descriptors_are_not(self):
        one = "  public a();\n    descriptor: ()V"
        two = "  public b(int);\n    descriptor: (I)V"
        self.assertEqual(cache.public_signatures(one + "\n\n" + two),
                         cache.public_signatures(two + "\n\n" + one))
        self.assertNotEqual(cache.public_signatures(one),
                            cache.public_signatures(one.replace("()V", "()I")))


if __name__ == "__main__":
    unittest.main()

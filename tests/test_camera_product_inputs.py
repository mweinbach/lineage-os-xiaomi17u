import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scripts import camera_apk_inputs as base
from scripts import camera_product_inputs as product


class CameraProductTests(unittest.TestCase):
    def source(self):
        review = json.loads((base.ROOT/'research/factory-camera-apk.json').read_text())
        return {'provenance/review.json': base.encoded(review),
                'provenance/contract.json': b'original contract',
                base.PAYLOAD: b'synthetic original apk'}

    def test_narrow_privileged_policy(self):
        review = base.metadata(self.source()['provenance/review.json'])
        xml = product.permission_policy(review).decode()
        self.assertEqual(xml.count('<permission name='), 11)
        self.assertIn('android.permission.SYSTEM_CAMERA', xml)
        for name in review['permissions']['pure_platform_signature_requests']:
            self.assertNotIn(name, xml)
        self.assertNotIn('READ_PHONE_STATE', xml)
        self.assertNotIn('mediatek.permission', xml)

    def test_rejects_signature_and_unreviewed_grants(self):
        review = base.metadata(self.source()['provenance/review.json'])
        for permission in ['android.permission.INJECT_EVENTS', 'android.permission.UNKNOWN']:
            changed = copy.deepcopy(review)
            changed['permissions']['normalized_possibly_privileged_requests'][0] = permission
            with self.assertRaises(base.CameraApkError):
                product.permission_policy(changed)

    def test_original_bytes_and_strict_properties(self):
        source = self.source()
        rendered = product.render(source)
        self.assertEqual(rendered[base.PAYLOAD], source[base.PAYLOAD])
        bp = rendered['Android.bp'].decode()
        for name in ['presigned', 'preprocessed', 'enforce_uses_libs', 'privileged', 'product_specific']:
            self.assertIn(f'{name}: true', bp)
        self.assertIn('filename: "MiuiCamera.apk"', bp)
        self.assertIn('optional_uses_libs: ["miui-cameraopt", "androidx.window.extensions", "androidx.window.sidecar"]', bp)
        for forbidden in ['certificate:', 'relax', 'skip_preprocessed', 'dex_preopt:', 'overrides:']:
            self.assertNotIn(forbidden, bp)
        self.assertIn(product.MODULE, rendered['camera-product.mk'].decode())
        self.assertIn('sub_dir: "permissions"', bp)

    def test_producer_verifies_policy_and_apk_before_output(self):
        for tamper in [None, product.PERMISSION_FILE, base.PAYLOAD, 'camera-product.mk']:
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory() as temp:
                root=Path(temp).resolve(); source=root/'source'; source.mkdir()
                rendered = product.render(self.source())
                for name,raw in rendered.items():
                    path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
                if tamper:
                    (source/tamper).write_bytes(b'changed')
                args=[sys.executable,str(source/'tools/verify_camera_apk.py'),'--output-dir',str(root/'out')]
                args.extend(str(source/name) for name in rendered if name!='tools/verify_camera_apk.py')
                result=subprocess.run(args,capture_output=True,text=True)
                self.assertEqual(result.returncode,2 if tamper else 0,result.stderr)
                if tamper:
                    self.assertFalse((root/'out'/base.VERIFIED).exists())
                else:
                    self.assertEqual((root/'out'/base.VERIFIED).read_bytes(),self.source()[base.PAYLOAD])

if __name__ == '__main__':
    unittest.main()

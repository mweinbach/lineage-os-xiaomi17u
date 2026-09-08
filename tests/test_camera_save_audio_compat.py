"""Recompute source contracts and pin the factory ABI behind the new save paths."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def contract(name):
    return json.loads((ROOT / 'config' / name).read_text())


class CameraSaveAudioContracts(unittest.TestCase):
    def test_patch_and_authored_template_bytes(self):
        for name in ('nezha-compressed-dng.json', 'aperture-neutral-gainmap.json',
                     'nezha-audio-vendor-enums.json'):
            record = contract(name)
            patch = (ROOT / record['patch']).read_bytes()
            self.assertEqual(hashlib.sha256(patch).hexdigest(), record['patch_sha256'])
            for path, row in record.get('authored_templates', {}).items():
                data = (ROOT / path).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), row['sha256'])
                self.assertEqual(len(data), row['size_bytes'])

    def test_new_files_reconstruct_the_authored_helpers(self):
        for name in ('nezha-compressed-dng.json', 'aperture-neutral-gainmap.json'):
            record = contract(name)
            patch = (ROOT / record['patch']).read_text()
            for path, row in record['files'].items():
                if row['before_sha256'] is not None:
                    continue
                section = next(s for s in patch.split('diff --git ')[1:]
                               if s.splitlines()[0] == f'a/{path} b/{path}')
                lines = section.splitlines(keepends=True)
                hunks = [i for i, line in enumerate(lines) if line.startswith('@@ ')]
                self.assertEqual(len(hunks), 1)
                match = re.fullmatch(r'@@ -0,0 \+1,(\d+) @@\n', lines[hunks[0]])
                self.assertIsNotNone(match)
                body = lines[hunks[0] + 1:]
                self.assertTrue(all(line.startswith('+') for line in body))
                self.assertEqual(len(body), int(match.group(1)))
                data = ''.join(line[1:] for line in body).encode()
                template = ROOT / 'templates/camera-save-compat' / Path(path).name
                self.assertEqual(data, template.read_bytes())
                self.assertEqual(hashlib.sha256(data).hexdigest(), row['after_sha256'])
                self.assertEqual(len(data), row['after_bytes'])

    def test_aperture_preimage_chains_to_existing_admission_patch(self):
        old = json.loads((ROOT / 'patches/evolution/aperture-nezha-camera-admission.json').read_text())
        new = contract('aperture-neutral-gainmap.json')
        path = 'app/src/main/java/org/lineageos/aperture/viewmodels/CameraViewModel.kt'
        self.assertEqual(new['files'][path]['before_sha256'], old['files'][path]['after_sha256'])
        self.assertEqual(new['files'][path]['before_bytes'], old['files'][path]['after_bytes'])
        self.assertEqual(new['revision'], old['revision'])

    def test_selected_product_file_matches_audio_contract(self):
        row = contract('nezha-audio-vendor-enums.json')['product_file']
        data = (ROOT / row['path']).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), row['after_sha256'])
        self.assertEqual(len(data), row['after_bytes'])

    def test_measured_factory_dng_layout_pins(self):
        # These constants decide what memory layout the native writer accepts.
        # Their basis is the retained factory runtime and DNG implementation.
        record = contract('nezha-compressed-dng.json')
        self.assertEqual(record['factory_runtime']['sha256'],
                         'ef093978b8cc781a9002eb9d7fafca8c19076c78beaa83cc77a9704590700191')
        self.assertEqual(record['factory_dng_impl']['sha256'],
                         '33021e6c3adfc82d7eb62febf80eb29e4e2a47eb09416806fe016884c82c49f0')
        layout = record['factory_contract']
        self.assertEqual(layout['header_fields'], {'format': 0, 'width': 4, 'height': 8,
                         'compressed_size': 12, 'multi_thread': 16, 'grid_x': 20,
                         'grid_y': 24, 'tile_byte_counts': 28})
        self.assertEqual((layout['metadata_bytes'], layout['linear_raw_format'], layout['max_tiles'],
                          layout['bits_per_sample'], layout['samples_per_pixel'],
                          layout['compression'], layout['photometric_interpretation']),
                         (604, 15, 64, 16, 3, 7, 34892))
        self.assertEqual(layout['tile_grid'], [8, 8])

    def test_measured_audio_enum_pins(self):
        # Altering these values changes compatibility with the retained audio HAL.
        record = contract('nezha-audio-vendor-enums.json')
        self.assertEqual(record['vendor_values'], {'output_flag': {'aidl_index': 19,
                         'legacy_mask': 0x40000000}, 'usage': {'aidl': 19, 'legacy': 19}})
        self.assertEqual(record['factory_converter']['sha256'],
                         '5837d318589b7f38e217dec0cd666bb32e4e68a637cabde6eb6916a56365b965')

    def test_retained_neutral_capture_repair_pins(self):
        # A decoder-verified repair changes only the corresponding XMP/ISO capacity bytes.
        record = contract('aperture-neutral-gainmap.json')['measured_image_repair']
        self.assertEqual(record['original_sha256'],
                         '2e8b73590a54dec30494887263ebd28e86c1ee79d4829fbd8a5354926ba1720c')
        self.assertEqual(record['corrected_sha256'],
                         '129a92fbedf054c2eb92e0ffab9777409a01d4861976aa60e46141ba3970e7c4')
        self.assertEqual(record['changed_offsets'], [3178676, 3178794])
        self.assertEqual(record['original_values'], [48, 0])
        self.assertEqual(record['corrected_values'], [49, 1])
        self.assertEqual(record['size_bytes'], 3478116)


if __name__ == '__main__':
    unittest.main()

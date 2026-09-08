"""Recompute the supplemental native camera patch and its inherited preimages."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def apply_section(before, section):
    """Apply exact unified hunks without an external patch tool or private source."""
    source = before.splitlines(keepends=True)
    lines = section.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith('@@ ')]
    output, cursor = [], 0
    for index, start in enumerate(starts):
        match = re.fullmatch(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n', lines[start])
        if match is None:
            raise ValueError('Invalid hunk')
        old_line, old_count, new_line, new_count = map(int, match.groups())
        body = lines[start + 1:starts[index + 1] if index + 1 < len(starts) else None]
        old = [line[1:] for line in body if line.startswith((' ', '-'))]
        new = [line[1:] for line in body if line.startswith((' ', '+'))]
        position = old_line - 1
        if (len(old) != old_count or len(new) != new_count or position < cursor
                or source[position:position + old_count] != old):
            raise ValueError('Preimage or hunk count differs')
        output.extend(source[cursor:position])
        if len(output) != new_line - 1:
            raise ValueError('Output position differs')
        output.extend(new)
        cursor = position + old_count
    if not starts:
        raise ValueError('No hunks')
    output.extend(source[cursor:])
    return ''.join(output)


class CameraStreamSizingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT / 'config/nezha-camera-stream-sizing.json').read_text())
        self.parent = json.loads((ROOT / 'config/nezha-camera-session-inject.json').read_text())
        self.patch = (ROOT / self.contract['patch']).read_text()

    def test_patch_and_template_hashes_recomputed(self):
        self.assertEqual(hashlib.sha256(self.patch.encode()).hexdigest(),
                         self.contract['patch_sha256'])
        for path, row in self.contract['authored_templates'].items():
            raw = (ROOT / path).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
            self.assertEqual(len(raw), row['size_bytes'])

    def test_adapter_patch_reconstructs_the_selected_templates(self):
        for path in self.contract['authored_templates']:
            name = Path(path).name
            destination = 'services/camera/libcameraservice/utils/' + name
            section = next(s for s in self.patch.split('diff --git ')[1:]
                           if s.splitlines()[0] == f'a/{destination} b/{destination}')
            old = (ROOT / 'templates/camera-session-inject' / name).read_text()
            new = apply_section(old, section)
            self.assertEqual(new, (ROOT / path).read_text())
            record = self.contract['files'][destination]
            self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), record['before_sha256'])
            self.assertEqual(hashlib.sha256(new.encode()).hexdigest(), record['after_sha256'])
            self.assertEqual(len(new.encode()), record['after_bytes'])

    def test_preexisting_files_chain_to_the_reviewed_native_hook(self):
        for path, row in self.contract['files'].items():
            if path in self.parent['files']:
                self.assertEqual(row['before_sha256'], self.parent['files'][path]['after_sha256'])
                self.assertEqual(row['before_bytes'], self.parent['files'][path]['after_bytes'])
        self.assertEqual(self.contract['revision'], self.parent['revision'])
        self.assertEqual(self.contract['requires_patch'], self.parent['patch'])
        for field in ('factory_cameraimpl_sha256', 'factory_cameraserver_sha256'):
            self.assertEqual(self.contract[field], self.parent[field])

    def test_factory_function_addresses_pin_the_measured_sizing_decisions(self):
        # Changing these pins changes which factory implementation justifies the
        # private-size behavior; each full disassembly is retained privately.
        expected = {
            'android::Camera3Device::getJpegBufferSize': '1d13b52a5d8ba6101c6c54448654de7acffd2329cfdb142aae4ac35f9d0b9798',
            'android::camera3::SessionConfigurationUtils::roundBufferDimensionNearest': '3f5217d9c651359f74923c44f818eb01a9a907d2dd33150ba5d5a377fff63d7f',
            'CameraStub::isMockCamera': 'e7d91accec7fb741d9f59d052c4cb17e653045096bd94a3f752aea1ffabc0926',
            'CameraStub::getCustomBestSize': 'bce049171367db83a73442405342fcacc5bc03adfae58bf8ebd2bc1f0e6189d0',
            'CameraStub::raiseDimensionsforCustomImageQuality': 'ae6c82665689143b9b771e746534fb292b7bbe31dd5f7961387e45c8439cd4b9',
        }
        self.assertEqual({row['function']: row['sha256']
                          for row in self.contract['factory_functions']}, expected)


if __name__ == '__main__':
    unittest.main()

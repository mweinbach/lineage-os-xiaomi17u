"""Offline exact-matrix source admission; no private dumps or Android processes."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from scripts import framework_compatibility_matrix as matrix
from scripts import generate_device_tree as generator

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('matrix_candidate_fixtures', ROOT / 'tests/test_generate_device_tree.py')
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


class FrameworkMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.GenerateDeviceTreeTests.setUpClass()
        cls.public_raw = (ROOT / matrix.CONTRACT_PATH).read_bytes()
        cls.public = json.loads(cls.public_raw)

    def setUp(self):
        self.fixture = fixtures.GenerateDeviceTreeTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.output = self.root / 'artifacts/matrix'

    def write(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {'path': name, **matrix.identity(raw)}

    def inputs(self):
        inputs = self.fixture.factory_inputs()
        contract = copy.deepcopy(self.public)
        contract['factory_package']['sha256'] = '3' * 64
        contract['factory_partitions'] = {}
        contract['factory_xml_inputs'] = []
        contract['evidence_records'] = []
        contract['source_preconditions'] = []
        contract['required_source_revisions'] = {}
        for entry in contract['entries']:
            entry['manifest_inputs'] = [0]
            entry['matrix_inputs'] = [1]
        source = matrix.render(contract)
        for i, (kind, partition) in enumerate((('device_manifest', 'vendor'), ('framework_matrix', 'system'))):
            xml = source if i else source.replace(b'compatibility-matrix', b'manifest').replace(b'type="framework"', b'type="device"')
            name = 'artifacts/matrix-fixture/' + partition + '/files/0001'
            row = self.write(name, xml)
            member = {'output_path': 'files/0001', 'path': '/etc/vintf/fixture.xml', 'nid': 100 + i,
                      'type': 'regular', 'readback_verified': True, **matrix.identity(xml)}
            inventory = self.write('artifacts/matrix-fixture/' + partition + '/inventory.json', encoded({
                'entries': [{key: member[key] for key in ('nid', 'path', 'type')}]}))
            inventory_receipt = self.write('artifacts/matrix-fixture/' + partition + '/inventory-receipt.json', b'{}\n')
            image = {'path': 'artifacts/matrix-fixture/' + partition + '/image.img', 'sha256': str(i + 1) * 64, 'size_bytes': 4096}
            capture = self.write('artifacts/matrix-fixture/' + partition + '/receipt.json', encoded({
                'files': [member], 'image': image, 'inventory_sha256': inventory['sha256'],
                'inventory_receipt_sha256': inventory_receipt['sha256']}))
            contract['factory_partitions'][partition] = {'image': image, 'capture_receipt': capture,
                                                        'inventory': inventory, 'inventory_receipt': inventory_receipt}
            contract['factory_xml_inputs'].append({**row, 'kind': kind, 'partition': partition,
                'runtime_path': '/' + partition + '/etc/vintf/fixture.xml', 'image_path': member['path'],
                'capture_receipt': capture['path'], 'capture_output_path': member['output_path'], 'nid': member['nid']})
            contract['evidence_records'] += [capture, inventory, inventory_receipt]
        for row in (contract['source_lock'], contract['source_snapshot']):
            self.write(row['path'], (ROOT / row['path']).read_bytes())
        raw = encoded(contract)
        self.contract_path = self.root / matrix.CONTRACT_PATH
        self.write(matrix.CONTRACT_PATH, raw)
        self.enterContext(mock.patch.object(matrix, 'CONTRACT_SHA256', matrix.identity(raw)['sha256']))
        self.contract = contract
        return dict(inputs, framework_matrix_contract=self.contract_path)

    def reseal_contract(self, change):
        contract = json.loads(self.contract_path.read_bytes())
        change(contract)
        raw = encoded(contract)
        self.contract_path.write_bytes(raw)
        matrix.CONTRACT_SHA256 = matrix.identity(raw)['sha256']
        return contract

    def reseal_output(self, plan, name, raw):
        (self.output / name).write_bytes(raw)
        row = next(row for row in plan['files'] if row['path'] == name)
        row.update(matrix.identity(raw))
        (self.output / 'admission.json').write_bytes(encoded(plan))

    def test_public_contract_has_exact_original_input_closure(self):
        matrix.validate_contract(self.public, matrix.identity(self.public_raw))
        self.assertEqual(len(self.public['entries']), 155)
        self.assertEqual(len(self.public['factory_xml_inputs']), 119)
        self.assertEqual(len(self.public['source_preconditions']), 15)
        self.assertEqual(self.public['derivation']['source_device_matrix_unique_tuples'], 152)
        self.assertEqual(len(self.public['derivation']['product_entries_relocated_to_device_fcm']), 3)
        self.assertEqual({r['name'] for r in self.public['entries'] if r['name'].startswith('android.')}, {'android.se.omapi'})
        self.assertEqual(self.public['scope'], matrix.SCOPE)
        self.assertFalse(self.public['factory_package']['origin_verified'])

    def test_exact_projection_contains_no_regex_ranges_optional_or_platform_fields(self):
        raw = matrix.render(self.public)
        root = ET.fromstring(raw)
        tuples = {(h.findtext('name'), int(h.findtext('version')), i.findtext('name'), n.text)
                  for h in root.findall('hal') for i in h.findall('interface') for n in i.findall('instance')}
        self.assertEqual(tuples, {matrix.tuple_key(e) for e in self.public['entries']})
        self.assertEqual(root.attrib, {'version': '9.0', 'type': 'framework'})
        self.assertEqual(len(root.findall('hal')), 130)
        for token in (b'regex-instance', b'optional=', b'<kernel', b'<sepolicy', b'<avb'):
            self.assertNotIn(token, raw)
        self.assertTrue(all(h.findtext('version').isdigit() for h in root.findall('hal')))
        self.assertEqual(raw, matrix.render(copy.deepcopy(self.public)))

    def test_deterministic_generation_changes_board_and_adds_only_source_contract_and_locks(self):
        inputs = self.inputs()
        plain = dict(inputs)
        del plain['framework_matrix_contract']
        before = generator.generate(self.root / 'artifacts/before', **plain)
        plan = generator.generate(self.output, **inputs)
        repeat = generator.generate(self.root / 'artifacts/repeat', **inputs)
        self.assertEqual(plan, repeat)
        old = {r['path']: r for r in before['files']}
        new = {r['path']: r for r in plan['files']}
        self.assertEqual(new.keys() - old.keys(), {matrix.SOURCE_PATH, matrix.CONTRACT_PATH,
                          self.contract['source_lock']['path'], self.contract['source_snapshot']['path']})
        self.assertEqual([p for p in old if old[p] != new[p]], ['device/xiaomi/nezha/generated/BoardConfigCandidate.mk'])
        self.assertEqual(plan['admission'], before['admission'])
        self.assertEqual(generator.validate(self.output), plan)
        self.assertEqual(plan['framework_matrix']['scope'], matrix.SCOPE)
        for purpose in ('target-files', 'flash'):
            with self.assertRaisesRegex(generator.CandidateError, 'admission refused'):
                generator.validate(self.output, purpose=purpose)

    def test_unselected_path_remains_identical_and_does_not_open_matrix_inputs(self):
        inputs = self.fixture.factory_inputs()
        with mock.patch.object(generator, '_framework_matrix_contract', side_effect=AssertionError('implicit selection')):
            before = generator.generate(self.root / 'artifacts/before', **inputs)
            after = generator.generate(self.output, framework_matrix_contract=None, **inputs)
        self.assertEqual(before, after)
        self.assertNotIn('framework_matrix', after)

    def test_factory_profile_is_required_before_reading_contract(self):
        with self.assertRaisesRegex(generator.CandidateError, 'explicit factory profile'):
            generator.generate(self.output, framework_matrix_contract='missing.json', **self.fixture.generation_inputs())

    def test_changed_contract_is_not_accepted_by_its_own_receipt(self):
        inputs = self.inputs()
        self.contract_path.write_bytes(self.contract_path.read_bytes() + b'\n')
        with self.assertRaisesRegex(generator.CandidateError, 'changed framework matrix contract'):
            generator.generate(self.output, **inputs)
        self.assertFalse(self.output.exists())

    def test_wrong_factory_package_is_rejected(self):
        inputs = self.inputs()
        self.reseal_contract(lambda c: c['factory_package'].update(sha256='4' * 64))
        with self.assertRaisesRegex(generator.CandidateError, 'exact original factory'):
            generator.generate(self.output, **inputs)

    def test_duplicate_or_missing_entry_is_rejected(self):
        for mutate in (lambda c: c['entries'].pop(), lambda c: c['entries'].__setitem__(1, c['entries'][0])):
            contract = copy.deepcopy(self.public)
            mutate(contract)
            with self.assertRaisesRegex(ValueError, 'missing, duplicated or unsorted'):
                matrix.validate_contract(contract, matrix.identity(self.public_raw))

    def test_wildcards_ranges_and_noninteger_versions_are_rejected(self):
        for key, value in (('instance', '.*'), ('instance', 'default|other'), ('version', '1-20'),
                           ('version', True), ('name', 'vendor.*'), ('interface', 'IFoo.*')):
            contract = copy.deepcopy(self.public)
            contract['entries'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises((ValueError, TypeError)):
                matrix.validate_contract(contract, matrix.identity(self.public_raw))

    def test_wrong_evidence_direction_and_missing_reference_are_rejected(self):
        for role, indexes in (('manifest_inputs', []), ('matrix_inputs', [-1]),
                              ('manifest_inputs', self.public['entries'][0]['matrix_inputs'])):
            contract = copy.deepcopy(self.public)
            contract['entries'][0][role] = indexes
            with self.assertRaisesRegex(ValueError, 'exact original XML evidence'):
                matrix.validate_contract(contract, matrix.identity(self.public_raw))

    def test_generated_matrix_cannot_promote_native_or_hardware_claims(self):
        contract = copy.deepcopy(self.public)
        for key in ('native_matrix_built', 'full_vintf_compatibility_verified', 'hardware_tested', 'complete_rom_admitted'):
            changed = copy.deepcopy(contract)
            changed['scope'][key] = True
            with self.assertRaisesRegex(ValueError, 'promote native success'):
                matrix.validate_contract(changed, matrix.identity(self.public_raw))

    def test_original_xml_change_is_rejected(self):
        inputs = self.inputs()
        (self.root / self.contract['factory_xml_inputs'][0]['path']).write_bytes(b'<manifest/>')
        with self.assertRaisesRegex(generator.CandidateError, 'device manifest changed'):
            generator.generate(self.output, **inputs)
        self.assertFalse(self.output.exists())

    def test_original_xml_symlink_is_rejected(self):
        inputs = self.inputs()
        path = self.root / self.contract['factory_xml_inputs'][0]['path']
        original = path.read_bytes()
        other = path.with_name('other')
        other.write_bytes(original)
        path.unlink()
        path.symlink_to(other)
        with self.assertRaisesRegex(generator.CandidateError, 'symlink'):
            generator.generate(self.output, **inputs)

    def test_semantic_evidence_does_not_accept_different_exact_instance(self):
        root = ET.fromstring(b'<manifest type="device"><hal format="aidl"><name>vendor.test</name><version>1</version><interface><name>ITest</name><instance>wrong</instance></interface></hal></manifest>')
        row = {'name': 'vendor.test', 'version': 1, 'interface': 'ITest', 'instance': 'default'}
        self.assertFalse(matrix._aidl_supports(root, row, matrix=False))

    def test_omitted_aidl_version_is_explicitly_interpreted_as_one(self):
        root = ET.fromstring(b'<manifest type="device"><hal format="aidl"><name>vendor.test</name><fqname>ITest/default</fqname></hal></manifest>')
        row = {'name': 'vendor.test', 'version': 1, 'interface': 'ITest', 'instance': 'default'}
        self.assertTrue(matrix._aidl_supports(root, row, matrix=False))
        self.assertFalse(matrix._aidl_supports(root, dict(row, version=2), matrix=False))

    def test_original_matrix_range_does_not_broaden_authored_projection(self):
        root = ET.fromstring(b'<compatibility-matrix type="framework"><hal format="aidl"><name>vendor.test</name><version>1-3</version><interface><name>ITest</name><instance>default</instance></interface></hal></compatibility-matrix>')
        row = {'name': 'vendor.test', 'version': 2, 'interface': 'ITest', 'instance': 'default'}
        self.assertTrue(matrix._aidl_supports(root, row, matrix=True))
        self.assertFalse(matrix._aidl_supports(root, dict(row, version=4), matrix=True))
        raw = matrix.render({'entries': [row]})
        self.assertIn(b'<version>2</version>', raw)
        self.assertNotIn(b'1-3', raw)

    def test_regex_only_original_matrix_is_insufficient(self):
        root = ET.fromstring(b'<compatibility-matrix type="framework"><hal format="aidl"><name>vendor.test</name><version>1</version><interface><name>ITest</name><regex-instance>.*</regex-instance></interface></hal></compatibility-matrix>')
        self.assertFalse(matrix._aidl_supports(root, {'name':'vendor.test','version':1,'interface':'ITest','instance':'default'}, matrix=True))

    def test_xml_dtd_wrong_direction_and_bad_syntax_are_rejected(self):
        for raw in (b'<!DOCTYPE manifest><manifest type="device"/>', b'<manifest type="framework"/>', b'<manifest'):
            with self.assertRaises(ValueError):
                matrix._xml(raw, 'manifest', 'device')

    def test_capture_inode_link_is_rechecked(self):
        inputs = self.inputs()
        self.reseal_contract(lambda c: c['factory_xml_inputs'][0].update(nid=9999))
        with self.assertRaisesRegex(generator.CandidateError, 'capture member differs'):
            generator.generate(self.output, **inputs)

    def test_late_original_change_is_caught_before_publication(self):
        inputs = self.inputs()
        original_validate = generator.validate
        def change_after_validation(*args, **kwargs):
            result = original_validate(*args, **kwargs)
            path = self.root / self.contract['factory_xml_inputs'][0]['path']
            path.write_bytes(path.read_bytes() + b'\n')
            return result
        with mock.patch.object(generator, 'validate', side_effect=change_after_validation), self.assertRaisesRegex(generator.CandidateError, 'device manifest changed'):
            generator.generate(self.output, **inputs)
        self.assertFalse(self.output.exists())

    def test_resealed_generated_matrix_change_is_rejected(self):
        plan = generator.generate(self.output, **self.inputs())
        self.reseal_output(plan, matrix.SOURCE_PATH, (self.output / matrix.SOURCE_PATH).read_bytes().replace(b'<instance>default</instance>', b'<instance>fake</instance>', 1))
        with self.assertRaisesRegex(generator.CandidateError, 'generated framework matrix differs'):
            generator.validate(self.output)

    def test_resealed_admission_cannot_claim_native_success(self):
        plan = generator.generate(self.output, **self.inputs())
        plan['framework_matrix']['scope']['native_matrix_built'] = True
        (self.output / 'admission.json').write_bytes(encoded(plan))
        with self.assertRaisesRegex(generator.CandidateError, 'matrix admission differs'):
            generator.validate(self.output)

    def test_resealed_selector_or_product_matrix_override_is_rejected(self):
        plan = generator.generate(self.output, **self.inputs())
        name = 'device/xiaomi/nezha/generated/BoardConfigCandidate.mk'
        raw = (self.output / name).read_bytes()
        for change in (raw.replace(matrix.SOURCE_PATH.encode(), b'other.xml'), raw + b'\nDEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE := extra.xml\n'):
            self.reseal_output(plan, name, change)
            with self.assertRaisesRegex(generator.CandidateError, 'matrix generated board'):
                generator.validate(self.output)

    def test_duplicate_external_selector_is_rejected(self):
        for raw in (b'DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE += extra.xml\n',
                    b'DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE += extra.xml\n',
                    b'DEVICE_FRAMEWORK_COMPATIBILITY_\\\nMATRIX_FILE += extra.xml\n'):
            with self.assertRaisesRegex(generator.CandidateError, 'selectors require'):
                generator._framework_matrix_source_guards({}, {'device/xiaomi/nezha/device.mk': raw})

    def test_other_compatibility_xml_is_rejected_without_banning_provider_manifests(self):
        with self.assertRaisesRegex(generator.CandidateError, 'unreviewed extra'):
            generator._framework_matrix_source_guards({}, {'device/xiaomi/nezha/other.xml': b'<compatibility-matrix type="framework"/>'})
        generator._framework_matrix_source_guards({}, {'device/xiaomi/nezha/provider.xml': b'<manifest type="framework"/>'})

    def test_wiring_rejects_overrides_and_freezes_both_selectors(self):
        raw = '\n'.join(matrix.wiring_lines())
        self.assertIn('$(origin DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE)', raw)
        self.assertIn('$(origin DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE)', raw)
        self.assertIn('.KATI_READONLY := DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE', raw)
        self.assertEqual(raw.count(matrix.SELECTOR + ' := ' + matrix.SOURCE_PATH), 1)

    def test_cli_forwards_explicit_contract(self):
        with mock.patch.object(generator, 'generate', return_value={}) as generate, mock.patch('builtins.print'):
            self.assertEqual(generator.main(['generate','--kernel-receipt','kernel','--vendor-receipt','vendor',
                                             '--framework-matrix-contract','matrix.json','--output','out']), 0)
        self.assertEqual(generate.call_args.kwargs['framework_matrix_contract'], Path('matrix.json'))


if __name__ == '__main__':
    unittest.main()

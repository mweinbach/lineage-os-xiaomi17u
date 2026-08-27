"""Offline literal configuration comparison and provenance boundary tests."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import erofs_inventory
from scripts import kernel_config_audit as audit


def config(text, source='stock'):
    return audit.parse_kconfig(text.encode(), source)


class KconfigParserTests(unittest.TestCase):
    def test_explicit_types_unset_and_source_lines(self):
        result = config('# header\nCONFIG_Y=y\nCONFIG_M=m\n# CONFIG_N is not set\n'
                        'CONFIG_INT=-10\nCONFIG_HEX=0xAb\nCONFIG_TEXT="a \\\"quote\\\""\n')
        self.assertEqual(result['CONFIG_N']['value'], 'n')
        self.assertEqual(result['CONFIG_N']['line'], 4)
        self.assertEqual(result['CONFIG_N']['spelling'], 'explicit_unset')
        self.assertEqual(result['CONFIG_HEX']['value'], '0xAb')
        self.assertEqual(result['CONFIG_INT']['value'], '-10')
        self.assertNotIn('CONFIG_ABSENT', result)

    def test_duplicate_assignments_are_rejected_even_if_equal(self):
        for tail in ('CONFIG_A=y', 'CONFIG_A=n', '# CONFIG_A is not set'):
            with self.subTest(tail=tail), self.assertRaisesRegex(audit.ConfigAuditError, 'duplicate'):
                config('CONFIG_A=y\n' + tail)

    def test_unset_and_assignment_duplicate_is_rejected(self):
        with self.assertRaisesRegex(audit.ConfigAuditError, 'duplicate'):
            config('# CONFIG_A is not set\nCONFIG_A=n\n')

    def test_unsupported_syntax_is_not_evaluated_or_guessed(self):
        for text in ('CONFIG_A =y', 'CONFIG_A=', 'CONFIG_A=true', 'CONFIG_A=$(run)',
                     '# CONFIG_A= n', 'source "other"', 'CONFIG_A=y #inline',
                     'CONFIG_A="unterminated', 'CONFIG_A="bad\\n"', 'CONFIG_A=y\r\n', '\0'):
            with self.subTest(text=text), self.assertRaises(audit.ConfigAuditError):
                config(text)

    def test_quoted_shell_looking_text_is_only_data(self):
        result = config('CONFIG_TEXT="$(not executed) `still inert`"\n')
        self.assertEqual(result['CONFIG_TEXT']['value'], '"$(not executed) `still inert`"')

    def test_empty_and_symbol_size_limits(self):
        for data in (b'', b'# comments only\n'):
            with self.subTest(data=data), self.assertRaises(audit.ConfigAuditError):
                audit.parse_kconfig(data, 'fixture')
        with mock.patch.object(audit, 'MAX_SYMBOLS', 1), self.assertRaises(audit.ConfigAuditError):
            config('CONFIG_A=y\nCONFIG_B=n\n')
        with mock.patch.object(audit, 'MAX_INPUT_BYTES', 1), self.assertRaises(audit.ConfigAuditError):
            config('CONFIG_A=y\n')


class StarlarkParserTests(unittest.TestCase):
    def parse(self, text):
        return audit.parse_starlark_config(text.encode(), 'ddk', 'test_config')

    def test_named_literal_dictionary_and_nested_config_quotes(self):
        result = self.parse('test_config = {\n # comment\n "CONFIG_A": "m",\n "CONFIG_S": "\\\"\\\"",\n}')
        self.assertEqual(result['CONFIG_A']['value'], 'm')
        self.assertEqual(result['CONFIG_A']['line'], 3)
        self.assertEqual(result['CONFIG_S']['value'], '""')

    def test_single_quotes_are_literal(self):
        self.assertEqual(self.parse("test_config = {'CONFIG_A': 'y'}")['CONFIG_A']['value'], 'y')

    def test_equal_and_different_duplicate_keys_are_rejected(self):
        for value in ('y', 'n'):
            with self.subTest(value=value), self.assertRaisesRegex(audit.ConfigAuditError, 'duplicate'):
                self.parse('test_config = {"CONFIG_A": "y", "CONFIG_A": "' + value + '"}')

    def test_no_executable_or_nonliteral_starlark_is_accepted(self):
        texts = ['load("//evil", "x")\ntest_config={"CONFIG_A":"y"}',
                 'test_config = dict(CONFIG_A="y")',
                 'test_config = {"CONFIG_A": str(1)}',
                 'test_config = {"CONFIG_A": True}',
                 'test_config = {**other}',
                 'test_config = {x: "y" for x in names}',
                 'test_config = {"CONFIG_A": "y"} | other',
                 'wrong_name = {"CONFIG_A": "y"}',
                 'test_config = {"CONFIG_A": __import__("os").system("anything")}',
                 'test_config = {f"CONFIG_A": "y"}',
                 'test_config = {b"CONFIG_A": "y"}',
                 'test_config = {"CONFIG_" "A": "y"}',
                 'test_config = {u"CONFIG_A": "y"}',
                 'test_config = {"CONFIG_A": "y"}\npass']
        with mock.patch('os.system') as system:
            for text in texts:
                with self.subTest(text=text), self.assertRaises(audit.ConfigAuditError):
                    self.parse(text)
        system.assert_not_called()

    def test_unsupported_dictionary_values_fail(self):
        for value in ('', 'yes', 'true', 'm|y', '$(cmd)'):
            with self.subTest(value=value), self.assertRaises(audit.ConfigAuditError):
                self.parse('test_config = {"CONFIG_A": ' + json.dumps(value) + '}')


class ComparisonTests(unittest.TestCase):
    def test_absent_is_unknown_and_not_unset(self):
        stock = config('CONFIG_Y=y\n# CONFIG_N is not set\n')
        requests = config('CONFIG_Y=y\nCONFIG_N=n\nCONFIG_ABSENT=n\n', 'request')
        result = audit.compare_requests(stock, {'request': requests}, ['request'])
        self.assertEqual(result['counts'], {'equal': 2, 'different_literal': 0, 'not_observed_in_stock': 1})
        absent = next(r for r in result['rows'] if r['symbol'] == 'CONFIG_ABSENT')
        self.assertIsNone(absent['stock'])
        self.assertFalse(result['absence_means_unset'])
        self.assertFalse(result['kconfig_evaluated'])

    def test_layer_override_order_and_identical_overrides_are_preserved(self):
        sources = {'common': config('CONFIG_A=m\nCONFIG_B=y\n', 'common'),
                   'sibling': config('CONFIG_A=y\nCONFIG_B=y\n', 'sibling')}
        result = audit.compare_requests(config('CONFIG_A=m\nCONFIG_B=y\n'), sources, ['common', 'sibling'])
        self.assertEqual(len(result['source_layer_overrides']), 2)
        self.assertEqual([x['literal_value_changed'] for x in result['source_layer_overrides']], [True, False])
        self.assertEqual(result['rows'][0]['request']['source_id'], 'sibling')
        self.assertEqual(result['counts']['different_literal'], 1)

    def test_numeric_spelling_difference_is_not_claimed_as_effective_change(self):
        result = audit.compare_requests(config('CONFIG_N=16\n'), {'r': config('CONFIG_N=0x10\n', 'r')}, ['r'])
        self.assertEqual(result['counts']['different_literal'], 1)
        self.assertFalse(result['kconfig_evaluated'])

    def test_stock_unrequested_symbols_are_not_synthesized_into_requests(self):
        result = audit.compare_requests(config('CONFIG_A=y\nCONFIG_B=m\n'), {'r': config('CONFIG_A=y\n')}, ['r'])
        self.assertEqual(result['explicit_request_count'], 1)
        self.assertEqual(result['stock_symbols_not_requested_count'], 1)


class AssertionTests(unittest.TestCase):
    def setUp(self):
        self.stock = config('CONFIG_MODULE_SIG_ALL=y\n# CONFIG_CFI_PERMISSIVE is not set\n')
        self.specs = [{'symbol': 'CONFIG_MODULE_SIG_ALL', 'expected': 'y', 'reason': 'Preserve signing.'},
                      {'symbol': 'CONFIG_CFI_PERMISSIVE', 'expected': 'n', 'reason': 'Do not make CFI permissive.'}]

    def test_assertions_only_bind_observed_values_and_do_not_generate_config(self):
        result = audit.make_assertions(self.stock, self.specs)
        self.assertFalse(result['generated_defconfig'])
        self.assertFalse(result['kmi_compatibility_verified'])
        self.assertEqual(result['assertions'][0]['stock_source']['value'], 'y')

    def test_assertions_cannot_invent_or_change_stock_values(self):
        for specs in ([], self.specs + [self.specs[0]],
                      [{'symbol': 'CONFIG_MISSING', 'expected': 'n', 'reason': 'absent'}],
                      [{'symbol': 'CONFIG_MODULE_SIG_ALL', 'expected': 'n', 'reason': 'reduce signing'}]):
            with self.subTest(specs=specs), self.assertRaises(audit.ConfigAuditError):
                audit.make_assertions(self.stock, specs)

    def test_missing_or_reduced_candidate_signing_fails(self):
        assertions = audit.make_assertions(self.stock, self.specs)
        for text in ('CONFIG_OTHER=y\n', '# CONFIG_MODULE_SIG_ALL is not set\n# CONFIG_CFI_PERMISSIVE is not set\n'):
            with self.subTest(text=text):
                result = audit.check_candidate(config(text), assertions)
                self.assertFalse(result['selected_assertions_passed'])

    def test_matching_assertions_do_not_prove_full_configuration_or_build(self):
        result = audit.check_candidate(self.stock, audit.make_assertions(self.stock, self.specs))
        self.assertTrue(result['selected_assertions_passed'])
        self.assertFalse(result['kernel_buildability_verified'])
        self.assertFalse(result['kconfig_evaluated'])

    def test_empty_external_assertion_document_fails(self):
        with self.assertRaises(audit.ConfigAuditError):
            audit.check_candidate(self.stock, {'schema_version': 1, 'assertions': []})


class AuditWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        patch = mock.patch.object(erofs_inventory, 'WORKSPACE_ROOT', self.root)
        patch.start()
        self.addCleanup(patch.stop)
        self.inputs = self.root / 'inputs'
        self.inputs.mkdir()
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.package = 'a' * 64
        self.ack, self.micode = 'b' * 40, 'c' * 40
        self.stock = b'CONFIG_ARM64_4K_PAGES=y\nCONFIG_MODULE_SIG_ALL=y\n# CONFIG_UNUSED is not set\n'
        evidence = {'parent_package_sha256': self.package, 'inputs_unchanged': True, 'firmware_executed': False,
                    'artifacts': [{'path': 'kernel.config', 'kind': 'regular', 'size_bytes': len(self.stock),
                                   'sha256': hashlib.sha256(self.stock).hexdigest()}]}
        self.contents = {'stock_config': self.stock, 'stock_receipt': json.dumps(evidence).encode(),
                         'micode_ack_pointer': (self.ack + '\nexact-tag\n').encode(),
                         'ack_config': b'CONFIG_ARM64_4K_PAGES=y\nCONFIG_NOT_OBSERVED=n\n',
                         'ddk_config': b'ddk_config = {"CONFIG_MODULE_SIG_ALL": "n", "CONFIG_VENDOR_ONLY": "m"}\n'}
        sources = []
        definitions = [('stock_config', 'kconfig', 'observed_stock_config', 'stock-evidence'),
                       ('stock_receipt', 'stock_receipt', 'stock_receipt', 'stock-evidence'),
                       ('micode_ack_pointer', 'reference', 'source_reference', 'micode'),
                       ('ack_config', 'kconfig', 'ack_gki_requests', 'ack'),
                       ('ddk_config', 'starlark_config_dict', 'vendor_ddk_requests', 'micode')]
        for name, kind, role, repository in definitions:
            data = self.contents[name]
            (self.inputs / name).write_bytes(data)
            source = {'id': name, 'path': name, 'format': kind, 'role': role, 'repository': repository,
                      'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data)}
            if repository != 'stock-evidence':
                source['commit'] = self.ack if repository == 'ack' else self.micode
            if kind == 'starlark_config_dict':
                source['dictionary_name'] = 'ddk_config'
                source['git_blob_sha1'] = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            sources.append(source)
        self.recipe = {'schema_version': 1, 'device': {'codename': 'nezha', 'hardware_region': 'CN', 'architecture': 'arm64'},
                       'references': {'ack': {'commit': self.ack, 'tag': 'exact-tag'}, 'micode': {'commit': self.micode}},
                       'stock': {'package_sha256': self.package, 'origin_verified': False, 'input_avb_status': 'failed'},
                       'sources': sources,
                       'profiles': [{'id': 'ack', 'sources': ['ack_config'], 'scope': 'ACK requests only'},
                                    {'id': 'ddk', 'sources': ['ddk_config'], 'scope': 'Vendor DDK comparison only'}],
                       'assertions': [{'symbol': 'CONFIG_ARM64_4K_PAGES', 'expected': 'y', 'reason': 'Keep page size.'},
                                      {'symbol': 'CONFIG_MODULE_SIG_ALL', 'expected': 'y', 'reason': 'Keep signing.'}]}
        self.recipe_path = self.root / 'recipe.json'
        self.save_recipe()

    def save_recipe(self):
        self.recipe_path.write_text(json.dumps(self.recipe))

    def run_audit(self, **kwargs):
        return audit.audit(recipe_path=self.recipe_path, source_root=self.inputs,
                           output_dir=self.artifacts / 'result', **kwargs)

    def test_complete_audit_writes_only_private_json_and_keeps_roles_distinct(self):
        result = self.run_audit()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['profiles'][0]['counts']['not_observed_in_stock'], 1)
        self.assertEqual(result['profiles'][1]['assertion_conflicts'], ['CONFIG_MODULE_SIG_ALL'])
        self.assertEqual({p.name for p in (self.artifacts / 'result').iterdir()},
                         {'stock-symbols.json', 'assertions.json', 'literal-deltas.json', 'receipt.json'})
        for field in ('origin_verified', 'source_executed', 'firmware_executed', 'kconfig_evaluated',
                      'effective_config_generated', 'kernel_build_performed', 'module_dependencies_completed',
                      'kmi_compatibility_verified', 'signature_trust_verified', 'phone_accessed', 'vm_accessed'):
            self.assertIs(result[field], False)
        self.assertEqual(result['input_avb_status'], 'failed')
        for artifact in result['artifacts']:
            path = self.artifacts / 'result' / artifact['name']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact['sha256'])

    def test_existing_output_is_not_replaced(self):
        output = self.artifacts / 'result'
        output.mkdir()
        (output / 'keep').write_text('unchanged')
        with self.assertRaises(ValueError):
            self.run_audit()
        self.assertEqual((output / 'keep').read_text(), 'unchanged')

    def test_public_or_symlinked_output_is_rejected(self):
        with self.assertRaises(ValueError):
            audit.audit(recipe_path=self.recipe_path, source_root=self.inputs, output_dir=self.root / 'public')
        (self.artifacts / 'result').symlink_to(self.inputs, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_input_symlink_is_rejected(self):
        original = self.inputs / 'stock_config'
        renamed = self.inputs / 'real-stock'
        original.rename(renamed)
        original.symlink_to(renamed)
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_file_hash_and_size_are_required(self):
        (self.inputs / 'stock_config').write_bytes(self.stock.replace(b'=y', b'=n', 1))
        with self.assertRaises(ValueError):
            self.run_audit()
        (self.inputs / 'stock_config').write_bytes(self.stock)
        self.recipe['sources'][0]['size_bytes'] -= 1
        self.save_recipe()
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_git_blob_pin_is_checked_independently(self):
        self.recipe['sources'][-1]['git_blob_sha1'] = 'd' * 40
        self.save_recipe()
        with self.assertRaisesRegex(audit.ConfigAuditError, 'Git blob'):
            self.run_audit()

    def test_source_commit_metadata_cannot_disagree_with_reference(self):
        self.recipe['sources'][-1]['commit'] = 'd' * 40
        self.save_recipe()
        with self.assertRaisesRegex(audit.ConfigAuditError, 'reference commit'):
            self.run_audit()

    def test_original_stock_receipt_binding_is_enforced(self):
        evidence = json.loads(self.contents['stock_receipt'])
        evidence['parent_package_sha256'] = 'd' * 64
        data = json.dumps(evidence).encode()
        (self.inputs / 'stock_receipt').write_bytes(data)
        source = self.recipe['sources'][1]
        source.update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
        self.save_recipe()
        with self.assertRaisesRegex(audit.ConfigAuditError, 'parent package'):
            self.run_audit()

    def test_ack_pointer_is_not_treated_as_an_unchecked_label(self):
        data = ('d' * 40 + '\nexact-tag\n').encode()
        (self.inputs / 'micode_ack_pointer').write_bytes(data)
        self.recipe['sources'][2].update(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
        self.save_recipe()
        with self.assertRaisesRegex(audit.ConfigAuditError, 'ACK pointer'):
            self.run_audit()

    def test_ack_and_ddk_profiles_cannot_be_combined(self):
        self.recipe['profiles'][0]['sources'].append('ddk_config')
        self.save_recipe()
        with self.assertRaisesRegex(audit.ConfigAuditError, 'must not be merged'):
            self.run_audit()

    def test_recipe_cannot_upgrade_modified_package_trust(self):
        self.recipe['stock']['origin_verified'] = True
        self.save_recipe()
        with self.assertRaisesRegex(audit.ConfigAuditError, 'trust and AVB'):
            self.run_audit()

    def test_candidate_needs_hash_and_does_not_overwrite_source(self):
        path = self.root / 'candidate.config'
        data = b'CONFIG_ARM64_4K_PAGES=y\n# CONFIG_MODULE_SIG_ALL is not set\n'
        path.write_bytes(data)
        with self.assertRaises(audit.ConfigAuditError):
            self.run_audit(candidate_config=path)
        result = self.run_audit(candidate_config=path, expected_candidate_sha256=hashlib.sha256(data).hexdigest())
        self.assertFalse(result['candidate_check']['selected_assertions_passed'])
        self.assertEqual(path.read_bytes(), data)

    def test_duplicate_recipe_json_keys_are_rejected(self):
        self.recipe_path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(audit.ConfigAuditError, 'duplicate JSON'):
            self.run_audit()

    def test_source_path_traversal_is_rejected(self):
        self.recipe['sources'][0]['path'] = '../stock_config'
        self.save_recipe()
        with self.assertRaisesRegex(audit.ConfigAuditError, 'source path'):
            self.run_audit()

    def test_duplicate_sources_and_profiles_are_rejected(self):
        original = copy.deepcopy(self.recipe)
        for key in ('sources', 'profiles'):
            self.recipe = copy.deepcopy(original)
            self.recipe[key].append(copy.deepcopy(self.recipe[key][0]))
            self.save_recipe()
            with self.subTest(key=key), self.assertRaises(audit.ConfigAuditError):
                self.run_audit()


class PinnedRecipeTests(unittest.TestCase):
    def test_checked_recipe_pins_are_exact_and_never_define_nezha_build(self):
        recipe = audit._recipe(audit.DEFAULT_RECIPE.read_bytes())
        self.assertEqual(recipe['references']['ack']['commit'], 'f1bdb13583da85a47fcf1632a78ef52d6e6da651')
        self.assertEqual(recipe['references']['micode']['commit'], '45705be1220b4cfa8100516ad86711656c0b634e')
        self.assertEqual(len(recipe['sources']), 17)
        self.assertEqual(len(recipe['assertions']), 20)
        self.assertTrue(all('nezha' not in p['id'] for p in recipe['profiles']))
        self.assertFalse(recipe['output_policy']['generate_defconfig'])
        self.assertFalse(recipe['output_policy']['infer_absent_as_n'])

    def test_mandatory_signing_and_security_assertions_are_not_reductions(self):
        recipe = json.loads(audit.DEFAULT_RECIPE.read_text())
        expected = {a['symbol']: a['expected'] for a in recipe['assertions']}
        for key in ('MODULE_SIG', 'MODULE_SIG_ALL', 'MODULE_SIG_PROTECT', 'MODVERSIONS',
                    'TRIM_UNUSED_KSYMS', 'SECURITY_SELINUX', 'DM_VERITY', 'CFI_CLANG'):
            self.assertEqual(expected['CONFIG_' + key], 'y')
        self.assertEqual(expected['CONFIG_CFI_PERMISSIVE'], 'n')
        self.assertEqual(expected['CONFIG_ARM64_4K_PAGES'], 'y')
        self.assertNotIn('CONFIG_MODULE_SIG_FORCE', expected)


if __name__ == '__main__':
    unittest.main()

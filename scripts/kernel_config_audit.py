#!/usr/bin/env python3
"""Compare pinned literal kernel-config requests with captured Nezha IKCONFIG.

This tool never executes Starlark, Kconfig, Make, a compiler or a source script.
It does not resolve defaults/dependencies, construct an effective .config,
generate an installable defconfig or infer n for an absent symbol. Generated
assertions are a bounded check for later candidate configuration text, not a
kernel, module ABI or hardware validation.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

if __package__:
    from .erofs_inventory import (_checked_file, _destination, _real_parents,
                                  _staging, _unchanged, _write_json)
else:
    from erofs_inventory import (_checked_file, _destination, _real_parents,
                                 _staging, _unchanged, _write_json)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / 'kernel/xiaomi/nezha/config-audit/recipe.json'
MAX_INPUT_BYTES = 4 * 1024**2
MAX_SOURCES = 64
MAX_SYMBOLS = 32768
SYMBOL = re.compile(r'CONFIG_[A-Za-z0-9_]+')
IDENTIFIER = re.compile(r'[a-z][a-z0-9_]*')
DIGEST = re.compile(r'[0-9a-f]{64}')
VALUE = re.compile(r'(?:[ymn]|-?[0-9]+|0[xX][0-9a-fA-F]+|"(?:[^"\\\x00-\x1f]|\\["\\])*")')
STRING_LITERAL = re.compile(r'''(?:"(?:[^"\\\r\n]|\\["'\\])*"|'(?:[^'\\\r\n]|\\["'\\])*')''')
FORMATS = {'kconfig', 'starlark_config_dict', 'reference', 'stock_receipt'}
ROLES = {'observed_stock_config', 'ack_gki_requests', 'vendor_ddk_requests',
         'sibling_ddk_requests', 'source_reference', 'stock_receipt'}


class ConfigAuditError(ValueError):
    """An input is unsafe, unsupported, ambiguous or inconsistent with its pin."""


def require(condition, message):
    if not condition:
        raise ConfigAuditError(message)


def checksum(value):
    require(isinstance(value, str) and DIGEST.fullmatch(value), 'expected lowercase SHA256 required')
    return value


def relative_path(value):
    require(isinstance(value, str) and 0 < len(value) <= 4096,
            'a bounded relative source path is required')
    require(all(part not in ('', '.', '..') and re.fullmatch(r'[A-Za-z0-9_.+-]+', part)
                for part in value.split('/')), 'unsafe or noncanonical source path')
    return value


def config_value(value):
    require(isinstance(value, str) and len(value) <= 16384 and VALUE.fullmatch(value),
            'unsupported Kconfig literal value')
    return value


def _text(data):
    require(0 < len(data) <= MAX_INPUT_BYTES, 'configuration text size exceeds its bound')
    text = data.decode('utf-8', errors='strict')
    require('\0' not in text and '\r' not in text, 'NUL/CR configuration text is not supported')
    return text


def parse_kconfig(data, source_id):
    """Read assignments and explicit unset comments; preserve literal spelling."""
    result = {}
    for number, raw in enumerate(_text(data).splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if match := re.fullmatch(r'# (CONFIG_[A-Za-z0-9_]+) is not set', line):
            symbol, value, spelling = match[1], 'n', 'explicit_unset'
        elif match := re.fullmatch(r'(CONFIG_[A-Za-z0-9_]+)=(.+)', line):
            symbol, value, spelling = match[1], config_value(match[2]), 'assignment'
        elif line.startswith('#'):
            require(not line.startswith('# CONFIG_'), 'unsupported Kconfig unset/comment syntax')
            continue
        else:
            raise ConfigAuditError(f'unsupported Kconfig syntax at {source_id}:{number}')
        require(symbol not in result, f'duplicate Kconfig symbol: {symbol}')
        require(len(result) < MAX_SYMBOLS, 'configuration symbol limit exceeded')
        result[symbol] = {'value': value, 'source_id': source_id, 'line': number, 'spelling': spelling}
    require(result, 'configuration contains no literal assignments')
    return result


def parse_starlark_config(data, source_id, dictionary_name):
    """Accept one named dictionary assignment containing string constants only."""
    require(isinstance(dictionary_name, str) and IDENTIFIER.fullmatch(dictionary_name),
            'literal Starlark dictionary name is invalid')
    text = _text(data)
    try:
        tree = ast.parse(text, mode='exec')
    except (SyntaxError, RecursionError) as exc:
        raise ConfigAuditError('unsupported Starlark dictionary syntax') from exc
    require(len(tree.body) == 1 and isinstance(tree.body[0], ast.Assign),
            'Starlark input must contain only one literal dictionary assignment')
    assignment = tree.body[0]
    require(len(assignment.targets) == 1 and isinstance(assignment.targets[0], ast.Name)
            and assignment.targets[0].id == dictionary_name and isinstance(assignment.value, ast.Dict),
            'Starlark input must assign the expected name to a literal dictionary')
    dictionary = assignment.value
    require(0 < len(dictionary.keys) <= MAX_SYMBOLS, 'Starlark dictionary size exceeds its bound')
    result = {}
    for key, value in zip(dictionary.keys, dictionary.values):
        require(isinstance(key, ast.Constant) and type(key.value) is str and SYMBOL.fullmatch(key.value)
                and isinstance(value, ast.Constant) and type(value.value) is str,
                'Starlark keys and values must be literal configuration strings')
        require(STRING_LITERAL.fullmatch(ast.get_source_segment(text, key) or '')
                and STRING_LITERAL.fullmatch(ast.get_source_segment(text, value) or ''),
                'unsupported string syntax or implicit literal concatenation')
        require(key.value not in result, f'duplicate Starlark configuration symbol: {key.value}')
        result[key.value] = {'value': config_value(value.value), 'source_id': source_id,
                             'line': key.lineno, 'spelling': 'literal_dictionary_entry'}
    return result


def compare_requests(stock, sources, source_order):
    """Compose only explicitly named request dictionaries; never resolve Kconfig."""
    requested, overrides = {}, []
    for source_id in source_order:
        require(source_id in sources, 'comparison profile references an unavailable parsed source')
        for symbol, record in sources[source_id].items():
            if symbol in requested:
                overrides.append({'symbol': symbol, 'previous': requested[symbol], 'replacement': record,
                                  'literal_value_changed': requested[symbol]['value'] != record['value']})
            requested[symbol] = record
    rows, counts = [], {'equal': 0, 'different_literal': 0, 'not_observed_in_stock': 0}
    for symbol in sorted(requested):
        observation = stock.get(symbol)
        status = ('not_observed_in_stock' if observation is None else
                  'equal' if observation['value'] == requested[symbol]['value'] else 'different_literal')
        counts[status] += 1
        rows.append({'symbol': symbol, 'request': requested[symbol], 'stock': observation, 'comparison': status})
    return {'explicit_request_count': len(requested), 'counts': counts, 'rows': rows,
            'source_order': source_order, 'source_layer_overrides': overrides,
            'stock_symbols_not_requested_count': len(set(stock) - set(requested)),
            'absence_means_unset': False, 'kconfig_evaluated': False}


def make_assertions(stock, specifications):
    require(isinstance(specifications, list) and 0 < len(specifications) <= 128,
            'a bounded list of stock-preservation assertions is required')
    symbols, assertions = set(), []
    for specification in specifications:
        require(isinstance(specification, dict) and set(specification) == {'symbol', 'expected', 'reason'},
                'invalid assertion specification')
        symbol, expected = specification['symbol'], config_value(specification['expected'])
        require(isinstance(symbol, str) and SYMBOL.fullmatch(symbol) and symbol not in symbols,
                'invalid or duplicate assertion symbol')
        require(isinstance(specification['reason'], str) and 0 < len(specification['reason']) <= 512,
                'assertion needs a bounded reason')
        require(symbol in stock and stock[symbol]['value'] == expected,
                f'assertion is not an observed stock value: {symbol}')
        symbols.add(symbol)
        assertions.append({**specification, 'stock_source': stock[symbol]})
    return {'schema_version': 1, 'scope': 'selected observed stock values for later candidate text checks',
            'assertions': assertions, 'generated_defconfig': False, 'kernel_buildability_verified': False,
            'kmi_compatibility_verified': False, 'signature_trust_verified': False}


def check_candidate(candidate, assertions):
    require(isinstance(assertions, dict) and type(assertions.get('schema_version')) is int
            and assertions['schema_version'] == 1 and isinstance(assertions.get('assertions'), list)
            and 0 < len(assertions['assertions']) <= 128, 'invalid or empty assertion document')
    checks = []
    symbols = set()
    for assertion in assertions['assertions']:
        require(isinstance(assertion, dict) and isinstance(assertion.get('symbol'), str)
                and SYMBOL.fullmatch(assertion['symbol']) and assertion['symbol'] not in symbols,
                'invalid or duplicate candidate assertion')
        config_value(assertion.get('expected'))
        symbols.add(assertion['symbol'])
        observed = candidate.get(assertion['symbol'])
        checks.append({'symbol': assertion['symbol'], 'expected': assertion['expected'],
                       'observed': observed,
                       'matches': observed is not None and observed['value'] == assertion['expected']})
    return {'checked': True, 'selected_assertions_passed': all(c['matches'] for c in checks), 'checks': checks,
            'scope': 'literal values only; not proof of a complete or effective kernel configuration',
            'kconfig_evaluated': False, 'kernel_buildability_verified': False}


def _json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON object key')
            result[key] = value
        return result
    value = json.loads(data, object_pairs_hook=pairs)
    require(isinstance(value, dict), 'JSON input must be an object')
    return value


def _file(stack, path, expected=None, size=None):
    path = Path(os.path.abspath(path))
    _real_parents(path.parent)
    require(0 < path.lstat().st_size <= MAX_INPUT_BYTES, 'source file size exceeds its bound')
    record = stack.enter_context(_checked_file(path, checksum(expected) if expected is not None else None))
    require(size is None or record['size_bytes'] == size, 'source file length differs from the recipe')
    record['stream'].seek(0)
    data = record['stream'].read(MAX_INPUT_BYTES + 1)
    require(len(data) <= MAX_INPUT_BYTES and len(data) == record['size_bytes'], 'source changed size while read')
    _unchanged(record)
    return data, record


def _recipe(data):
    recipe = _json(data)
    require(type(recipe.get('schema_version')) is int and recipe['schema_version'] == 1,
            'unsupported config-audit recipe schema')
    require(recipe.get('device') == {'codename': 'nezha', 'hardware_region': 'CN', 'architecture': 'arm64'},
            'recipe is not the reviewed China Nezha ARM64 contract')
    sources = recipe.get('sources')
    require(isinstance(sources, list) and 0 < len(sources) <= MAX_SOURCES, 'invalid source list')
    names, paths = set(), set()
    for source in sources:
        require(isinstance(source, dict) and isinstance(source.get('id'), str)
                and IDENTIFIER.fullmatch(source['id']) and source['id'] not in names, 'invalid/duplicate source id')
        path = relative_path(source.get('path'))
        require(path not in paths and source.get('format') in FORMATS and source.get('role') in ROLES,
                'invalid/duplicate source path, format or role')
        require(type(source.get('size_bytes')) is int and 0 < source['size_bytes'] <= MAX_INPUT_BYTES,
                'invalid source byte length')
        checksum(source.get('sha256'))
        names.add(source['id'])
        paths.add(path)
    require({'stock_config', 'stock_receipt', 'micode_ack_pointer'} <= names, 'missing evidence binding sources')
    roles = {s['id']: s['role'] for s in sources}
    require(roles['stock_config'] == 'observed_stock_config' and roles['stock_receipt'] == 'stock_receipt',
            'invalid stock evidence roles')
    profiles = recipe.get('profiles')
    require(isinstance(profiles, list) and 0 < len(profiles) <= 16, 'invalid comparison profiles')
    profile_names = set()
    for profile in profiles:
        require(isinstance(profile, dict) and isinstance(profile.get('id'), str)
                and IDENTIFIER.fullmatch(profile['id']) and profile['id'] not in profile_names,
                'invalid/duplicate profile id')
        order = profile.get('sources')
        require(isinstance(order, list) and 0 < len(order) <= MAX_SOURCES
                and all(isinstance(x, str) and x in names for x in order) and len(set(order)) == len(order),
                'invalid comparison source order')
        selected_roles = {roles[x] for x in order}
        require(selected_roles <= {'ack_gki_requests', 'vendor_ddk_requests', 'sibling_ddk_requests'}
                and not ('ack_gki_requests' in selected_roles and len(selected_roles) > 1),
                'ACK base and vendor/sibling DDK requests must not be merged')
        require(isinstance(profile.get('scope'), str) and 0 < len(profile['scope']) <= 512,
                'profile scope must be explicit')
        profile_names.add(profile['id'])
    references = recipe.get('references')
    require(isinstance(references, dict), 'reference pins must be an object')
    for reference in ('ack', 'micode'):
        pin = references.get(reference)
        require(isinstance(pin, dict) and isinstance(pin.get('commit'), str)
                and re.fullmatch(r'[0-9a-f]{40}', pin['commit']),
                'exact reference commit pin required')
    require(isinstance(references['ack'].get('tag'), str) and references['ack']['tag'], 'exact ACK tag required')
    for source in sources:
        repository = source.get('repository')
        if repository in ('ack', 'micode'):
            require(source.get('commit') == references[repository]['commit'],
                    'source metadata disagrees with its reference commit')
        else:
            require(repository == 'stock-evidence' and source['role'] in ('observed_stock_config', 'stock_receipt'),
                    'unknown source repository or stock evidence role')
    require(isinstance(recipe.get('stock'), dict), 'stock provenance must be an object')
    checksum(recipe['stock'].get('package_sha256'))
    require(recipe['stock'].get('origin_verified') is False and recipe['stock'].get('input_avb_status') == 'failed',
            'this recipe must retain its modified-package trust and AVB limitations')
    return recipe


def audit(*, recipe_path, source_root, output_dir, candidate_config=None, expected_candidate_sha256=None):
    require((candidate_config is None) == (expected_candidate_sha256 is None),
            'candidate path and expected SHA256 must be supplied together')
    destination = _destination(output_dir)
    source_root = Path(os.path.abspath(source_root))
    _real_parents(source_root)
    with ExitStack() as stack:
        recipe_bytes, recipe_file = _file(stack, recipe_path)
        recipe = _recipe(recipe_bytes)
        files, data, parsed = {}, {}, {}
        for source in recipe['sources']:
            content, record = _file(stack, source_root / source['path'], source['sha256'], source['size_bytes'])
            if 'git_blob_sha1' in source:
                expected_blob = source['git_blob_sha1']
                require(isinstance(expected_blob, str) and re.fullmatch(r'[0-9a-f]{40}', expected_blob),
                        'invalid expected Git blob id')
                blob = hashlib.sha1(b'blob ' + str(len(content)).encode('ascii') + b'\0' + content).hexdigest()
                require(blob == expected_blob, 'source bytes disagree with their pinned Git blob')
            files[source['id']], data[source['id']] = record, content
            if source['format'] == 'kconfig':
                parsed[source['id']] = parse_kconfig(content, source['id'])
            elif source['format'] == 'starlark_config_dict':
                parsed[source['id']] = parse_starlark_config(content, source['id'], source.get('dictionary_name'))
        require('stock_config' in parsed, 'stock config was not parsed as literal Kconfig')
        evidence = _json(data['stock_receipt'])
        require(evidence.get('parent_package_sha256') == recipe['stock']['package_sha256']
                and evidence.get('inputs_unchanged') is True and evidence.get('firmware_executed') is False,
                'stock receipt does not preserve the reviewed parent package')
        artifacts = evidence.get('artifacts')
        require(isinstance(artifacts, list) and all(isinstance(a, dict) for a in artifacts),
                'invalid stock artifact list')
        matches = [a for a in artifacts if a.get('path') == 'kernel.config']
        require(len(matches) == 1 and matches[0].get('kind') == 'regular'
                and matches[0].get('sha256') == files['stock_config']['sha256']
                and matches[0].get('size_bytes') == files['stock_config']['size_bytes'],
                'stock config does not match its original boot receipt')
        pointer = data['micode_ack_pointer'].decode('ascii').splitlines()
        require(pointer == [recipe['references']['ack']['commit'], recipe['references']['ack']['tag']],
                'MiCode ACK pointer disagrees with the reviewed source pin')
        stock = parsed['stock_config']
        assertions = make_assertions(stock, recipe.get('assertions'))
        profiles = []
        for profile in recipe['profiles']:
            comparison = compare_requests(stock, parsed, profile['sources'])
            constraints = {a['symbol']: a['expected'] for a in assertions['assertions']}
            comparison['assertion_conflicts'] = [row for row in comparison['rows']
                                                if row['symbol'] in constraints
                                                and row['request']['value'] != constraints[row['symbol']]]
            profiles.append({'id': profile['id'], 'scope': profile['scope'], **comparison})
        candidate_result = {'checked': False, 'selected_assertions_passed': None}
        if candidate_config is not None:
            candidate_bytes, candidate_file = _file(stack, candidate_config, expected_candidate_sha256)
            files['candidate_config'] = candidate_file
            candidate_result = check_candidate(parse_kconfig(candidate_bytes, 'candidate_config'), assertions)
        result = {'schema_version': 1, 'operation': 'literal-kernel-config-audit',
                  'device': recipe['device'], 'references': recipe['references'], 'provenance': recipe['stock'],
                  'stock_symbol_count': len(stock), 'profiles': profiles, 'candidate_check': candidate_result,
                  'kconfig_evaluated': False, 'effective_config_generated': False,
                  'generated_defconfig': False, 'kernel_build_performed': False,
                  'module_dependencies_completed': False, 'kmi_compatibility_verified': False,
                  'signature_trust_verified': False, 'phone_accessed': False, 'vm_accessed': False}
        with _staging(destination, 32 * 1024**2) as staging:
            artifacts = []
            artifacts.append(_write_json(staging / 'stock-symbols.json', {'schema_version': 1, 'symbols': stock}))
            artifacts.append(_write_json(staging / 'assertions.json', assertions))
            artifacts.append(_write_json(staging / 'literal-deltas.json', result))
            for record in [recipe_file, *files.values()]:
                _unchanged(record)
            receipt = {'schema_version': 1, 'operation': 'literal-kernel-config-audit', 'status': 'complete',
                       'created_at_utc': datetime.now(timezone.utc).isoformat(),
                       'recipe_sha256': recipe_file['sha256'],
                       'inspector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       'sources': [{**source, 'readback_verified': True} for source in recipe['sources']],
                       'artifacts': artifacts, 'stock_symbol_count': len(stock),
                       'profiles': [{'id': p['id'], 'counts': p['counts'],
                                     'explicit_request_count': p['explicit_request_count'],
                                     'source_layer_override_count': len(p['source_layer_overrides']),
                                     'assertion_conflicts': [r['symbol'] for r in p['assertion_conflicts']]}
                                    for p in profiles],
                       'assertion_count': len(assertions['assertions']),
                       'candidate_check': candidate_result,
                       'candidate_sha256': files['candidate_config']['sha256'] if candidate_config is not None else None,
                       'input_files_unchanged': True, 'origin_verified': False, 'input_avb_status': 'failed',
                       'source_executed': False, 'firmware_executed': False, 'kconfig_evaluated': False,
                       'effective_config_generated': False, 'kernel_build_performed': False,
                       'module_dependencies_completed': False, 'kmi_compatibility_verified': False,
                       'signature_trust_verified': False, 'phone_accessed': False, 'vm_accessed': False}
            _write_json(staging / 'receipt.json', receipt)
            for record in [recipe_file, *files.values()]:
                _unchanged(record)
        return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', type=Path, default=DEFAULT_RECIPE)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate-config', type=Path)
    parser.add_argument('--expected-candidate-sha256')
    args = parser.parse_args(argv)
    try:
        receipt = audit(recipe_path=args.recipe, source_root=args.source_root, output_dir=args.output,
                        candidate_config=args.candidate_config, expected_candidate_sha256=args.expected_candidate_sha256)
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        print(f'Kernel config audit: {exc}', file=sys.stderr)
        return 1
    print(json.dumps({'output': str(args.output), 'stock_symbols': receipt['stock_symbol_count'],
                      'profiles': receipt['profiles'], 'candidate_check': receipt['candidate_check']}, indent=2))
    return 2 if receipt['candidate_check']['selected_assertions_passed'] is False else 0


if __name__ == '__main__':
    raise SystemExit(main())

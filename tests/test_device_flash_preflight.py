"""Offline tests: every device/process call is mocked."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest import mock

from scripts import device_flash_preflight as candidate


def result(stdout=b'', stderr=b'', status='ok', exit_code=0, truncated=()):
    return {'stdout': stdout, 'stderr': stderr, 'status': status, 'exit_code': exit_code,
            'truncated_streams': list(truncated), 'elapsed_seconds': 0.001}


class ParserTests(unittest.TestCase):
    def test_serial_requires_explicit_usb_identifier(self):
        for value in ('', 'emulator-5554', '192.0.2.1:5555', 'adb-x._adb-tls-connect._tcp', 'a;id', 'a b', None):
            with self.subTest(value=value):
                self.assertFalse(candidate.valid_serial(value))
        self.assertTrue(candidate.valid_serial('PRIVATE-USB-ID'))

    def test_mutating_and_unreviewed_commands_are_rejected(self):
        for cmd in [('adb', 'root'), ('reboot',), ('snapshotctl', 'dump'), ('snapshotctl', 'cancel'),
                    ('bootctl', 'mark-boot-successful'), ('bootctl', 'set-active-boot-slot', '1'),
                    ('dd', 'if=/dev/zero', 'of=/dev/block/by-name/super'),
                    ('dd', 'if=/dev/block/by-name/pvmfw_b', 'bs=4096', 'count=256')]:
            with self.subTest(cmd=cmd), self.assertRaises(candidate.CollectionError):
                candidate.validate_read(cmd, 'a')

    def test_only_fixed_bounded_dd_reads_have_no_output_file_or_pipeline(self):
        reads = candidate.read_allowlist('a')
        for cmd in reads:
            self.assertEqual(candidate.validate_read(cmd, 'a'), cmd)
            self.assertFalse(any(t.startswith('of=') or t in ('>', '|', ';', '&&') for t in cmd))
        raw = [x for x in reads if x[0] == 'dd']
        self.assertEqual(len(raw), 3)
        self.assertTrue(all(x[-2:] == ('bs=4096', 'count=256') for x in raw))

    def test_fastboot_supports_exact_key_in_stderr(self):
        parsed = candidate.parse_fastboot_value('partition-size:boot_a', b'',
            b'(bootloader) partition-size:boot_a: 0x6000000\nFinished. Total time: 0.001s\n', 0)
        self.assertEqual(candidate.parse_capacity(parsed['value']), 100663296)

    def test_failed_truncated_duplicate_empty_or_unrelated_getvar_stays_unknown(self):
        cases = [(b'', b'FAILED (remote: unknown variable)', 0, False),
                 (b'current-slot: a\n', b'', 1, False), (b'current-slot: a\n', b'', 0, True),
                 (b'current-slot: \n', b'', 0, False),
                 (b'current-slot: a\ncurrent-slot: b\n', b'', 0, False), (b'other: a\n', b'', 0, False)]
        for out, err, code, truncated in cases:
            with self.subTest(out=out, err=err):
                parsed = candidate.parse_fastboot_value('current-slot', out, err, code, truncated=truncated)
                self.assertEqual(parsed['status'], 'unknown')
                self.assertIsNone(parsed['value'])

    def test_no_invented_oem_or_rollback_getvars(self):
        for var in ('all', 'anti', 'rollback-index', 'rollback-index:1', 'partition-size:system_a'):
            with self.assertRaises(ValueError):
                candidate.parse_fastboot_value(var, b'', b'', 0)

    def test_capacity_does_not_guess_missing_ambiguous_or_overflow_values(self):
        for value in ('6000000h', '0', 'unknown', '-1', '0x', '0x10000000000000000', None):
            self.assertIsNone(candidate.parse_capacity(value))

    def test_false_bootctl_getter_is_observed_but_hal_error_is_unknown(self):
        self.assertEqual(candidate.interpret_bootctl(result(b'0\n', status='failed', exit_code=70), 'is-slot-bootable')['value'], '0')
        self.assertEqual(candidate.interpret_bootctl(result(b'', b'HAL unavailable', 'failed', 70))['status'], 'unknown')
        self.assertEqual(candidate.interpret_bootctl(result(b'unknown\n'), 'get-snapshot-merge-status')['status'], 'unknown')
        self.assertEqual(candidate.interpret_bootctl(result(b'0\n', status='failed', exit_code=70), 'get-number-slots')['status'], 'unknown')

    def test_firmware_comparison_distinguishes_authenticated_payload_from_padding(self):
        body = b'authenticated' + bytes(51)
        ref = {'image': {'size_bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()},
               'descriptor': {'image_size': 13, 'salt_hex': 'ab12',
                              'digest_hex': hashlib.sha256(bytes.fromhex('ab12') + body[:13]).hexdigest()}}
        same = candidate.compare_retained_firmware(body, ref)
        self.assertTrue(same['authenticated_region_matches'])
        self.assertTrue(same['full_file_matches'])
        padding = candidate.compare_retained_firmware(body[:-1] + b'X', ref)
        self.assertTrue(padding['authenticated_region_matches'])
        self.assertFalse(padding['full_file_matches'])
        changed = candidate.compare_retained_firmware(b'X' + body[1:], ref)
        self.assertFalse(changed['authenticated_region_matches'])
        for captured in (body[:-1], body + b'X'):
            self.assertEqual(candidate.compare_retained_firmware(captured, ref)['status'], 'unknown')
        self.assertFalse(same['complete_firmware_trust_or_bootloader_acceptance_proven'])


class CollectorTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(candidate, 'ROOT', self.root).start()
        self.serial = 'PRIVATE-USB-SERIAL'
        self.output = self.root / 'evidence' / 'collection'
        self.args = ['--collect', '--serial', self.serial, '--mode', 'adb-recovery',
                     '--target-slot', 'a', '--output', str(self.output)]
        self.props = dict.fromkeys(candidate.PROPERTIES, '')
        self.props.update({'ro.product.manufacturer': 'Xiaomi', 'ro.product.device': 'nezha',
                           'ro.kernel.qemu': '0', 'ro.board.platform': 'canoe', 'ro.bootmode': 'recovery',
                           'init.svc.recovery': 'running', 'ro.twrp.version': '3.7.1_16-Xiaomi_17_Ultra',
                           'sys.boot_completed': '1', 'ro.boot.slot_suffix': '_a'})
        self.adb_state = 'recovery'
        self.dt = {
            '/proc/device-tree/model': b'Qualcomm Technologies, Inc. Nezha based on SM8850\0',
            '/proc/device-tree/compatible': b'qcom,canoe-mtp\0qcom,canoe\0qcom,canoep-mtp\0qcom,canoep\0qcom,mtp\0',
        }
        self.uid = '0'
        self.mode = 'no'
        self.fwbody = b'C' * candidate.MAX_BLOCK_READ
        self.reference = {'image': {'size_bytes': len(self.fwbody), 'sha256': hashlib.sha256(self.fwbody).hexdigest()},
                          'descriptor': {'image_size': 32, 'salt_hex': 'ab12',
                              'digest_hex': hashlib.sha256(bytes.fromhex('ab12') + self.fwbody[:32]).hexdigest()}}
        self.contract = {'raw_descriptor_sources': {r: self.reference for r in candidate.RETAINED}}
        self.profile = {'image_budgets': {r: candidate.MAX_BLOCK_READ for r in candidate.PHYSICAL_ROLES + candidate.RETAINED}}
        mock.patch.object(candidate.avb_signing, 'load_contract', return_value=(self.contract, 'a'*64, self.profile, 'b'*64)).start()

    def fake(self, command, **kwargs):
        self.assertLessEqual(kwargs['timeout'], 60)
        self.assertGreater(kwargs['max_bytes'], 0)
        if command == ['adb', 'version']:
            return result(b'ADB test\n')
        if command == ['adb', 'devices', '-l']:
            return result(f'{self.serial}\t{self.adb_state} usb:fixture transport_id:7\n'.encode())
        if command[:1] == ['fastboot']:
            self.assertEqual(command[1:4], ['-s', self.serial, 'getvar'])
            var = command[4]
            values = {'is-userspace': self.mode, 'product': 'nezha', 'unlocked': 'yes',
                      'current-slot': 'a', 'slot-count': '2', 'snapshot-update-status': 'none', 'max-download-size': '0x10000000'}
            value = values.get(var, '0x100000' if var.startswith('partition-size:') else '7' if var.startswith('slot-retry-count:') else 'yes')
            return result(stderr=f'{var}: {value}\nFinished. Total time: 0.001s\n'.encode())
        self.assertEqual(command[:3], ['adb', '-t', '7'])
        if command[3:] == ['get-state']:
            return result((self.adb_state + '\n').encode())
        if command[3:] == ['features']:
            return result(b'shell_v2,cmd\n')
        self.assertEqual(command[3:5], ['shell', '-T'])
        cmd = shlex.split(command[5])
        if cmd[0] == 'getprop':
            return result((self.props[cmd[1]] + '\n').encode())
        if cmd[0] == 'cat' and cmd[1] in self.dt:
            return result(self.dt[cmd[1]])
        if cmd == ['pidof', 'recovery']:
            return result(b'123\n')
        if cmd == ['id', '-u']:
            return result((self.uid+'\n').encode())
        if cmd[:2] == ['readlink', '-f']:
            return result(('/dev/block/sda' + str(candidate.PARTITIONS.index(cmd[-1].rsplit('/', 1)[1]) + 1) + '\n').encode())
        if cmd[0] == 'stat':
            return result(('block special file:8:' + str(candidate.PARTITIONS.index(cmd[-1].rsplit('/', 1)[1]) + 1) + '\n').encode())
        if cmd[0] == 'blockdev':
            return result(b'15300820992\n' if cmd[-1].endswith('/super') else b'1048576\n')
        if cmd[0] == 'dd':
            return result(self.fwbody)
        if cmd[0] == 'bootctl':
            values = {'hal-info': 'AIDL fixture', 'get-number-slots': '2', 'get-current-slot': '0', 'get-active-boot-slot': '0', 'get-snapshot-merge-status': 'none'}
            value = ('_a' if cmd[-1] == '0' else '_b') if cmd[1] == 'get-suffix' else values.get(cmd[1], '1')
            return result((value + '\n').encode())
        return result(b'read-only fixture\n')

    def invoke(self, args=None, effect=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(candidate, 'bounded_run', side_effect=effect or self.fake) as runner:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = candidate.main(self.args if args is None else args)
        return code, stdout.getvalue(), stderr.getvalue(), runner

    def report(self):
        return json.loads((self.output/'manifest.json').read_text())

    def test_default_plan_never_runs_or_writes(self):
        code, out, _, runner = self.invoke([])
        self.assertEqual(code, 0)
        runner.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertIn('Plan only', out)

    def test_explicit_identity_mode_slot_output_required_for_collection(self):
        for args in (['--collect'], ['--collect', '--serial', self.serial], ['--collect', '--mode', 'adb-recovery']):
            with self.subTest(args=args), mock.patch.object(candidate, 'bounded_run') as runner:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    candidate.main(args)
                runner.assert_not_called()

    def test_mode_incompatible_raw_reads_rejected_before_any_process(self):
        for mode in ('adb-android', 'fastboot-bootloader'):
            args = [*self.args, '--mode', mode, '--include-firmware']
            with self.subTest(mode=mode), mock.patch.object(candidate, 'bounded_run') as runner:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    candidate.main(args)
                runner.assert_not_called()

    def test_wrong_identity_stops_before_partition_and_firmware_reads(self):
        self.props['ro.board.platform'] = 'different-board'
        code, _, _, runner = self.invoke([*self.args, '--include-firmware'])
        self.assertEqual(code, 2)
        self.assertFalse(any('dd ' in c.args[0][-1] or 'blockdev' in c.args[0][-1] for c in runner.call_args_list))

    def test_installed_recovery_donor_property_requires_exact_live_device_tree(self):
        self.props['ro.board.platform'] = 'xiaomi_sm8750'
        self.props['ro.bootmode'] = 'unknown'
        code, _, _, _ = self.invoke([*self.args, '--include-firmware'])
        self.assertEqual(code, 0)
        self.assertEqual(self.report()['recovery_device_tree'], {k: v.decode() for k, v in self.dt.items()})
        self.assertTrue(self.report()['firmware'])

    def test_canoe_property_cannot_replace_wrong_device_tree(self):
        self.dt['/proc/device-tree/model'] = b'Other phone\0'
        code, _, _, runner = self.invoke([*self.args, '--include-firmware'])
        self.assertEqual(code, 2)
        self.assertFalse(any('blockdev' in c.args[0][-1] or c.args[0][-1].startswith('dd ') for c in runner.call_args_list))

    def test_recovery_device_tree_requires_complete_nul_terminated_bytes(self):
        self.dt['/proc/device-tree/compatible'] = self.dt['/proc/device-tree/compatible'][:-1]
        code, _, _, _ = self.invoke()
        self.assertEqual(code, 2)

    def test_unknown_recovery_mode_requires_recovery_transport(self):
        self.props['ro.bootmode'] = 'unknown'
        self.adb_state = 'device'
        code, _, _, _ = self.invoke()
        self.assertEqual(code, 2)

    def test_android_unknown_mode_is_not_recovery_exception(self):
        self.props['ro.bootmode'] = 'unknown'
        self.props['init.svc.recovery'] = ''
        self.adb_state = 'device'
        code, _, _, _ = self.invoke([*self.args, '--mode', 'adb-android'])
        self.assertEqual(code, 2)

    def test_device_tree_change_before_raw_reads_stops_capture(self):
        count = 0
        def effect(command, **kwargs):
            nonlocal count
            if command[-1] == 'cat /proc/device-tree/model':
                count += 1
                if count > 1:
                    return result(b'Other phone\0')
            return self.fake(command, **kwargs)
        code, _, _, runner = self.invoke([*self.args, '--include-firmware'], effect)
        self.assertEqual(code, 2)
        self.assertFalse(any(c.args[0][-1].startswith('dd ') for c in runner.call_args_list))

    def test_recovery_stays_transport_pinned_private_and_never_ready(self):
        code, out, err, runner = self.invoke()
        self.assertEqual(code, 0, err)
        self.assertNotIn(self.serial, out+err)
        report = self.report()
        self.assertFalse(report['flash_ready'])
        self.assertFalse(report['device_preflight_admitted'])
        self.assertIsNone(report['secure_rollback_indices'])
        self.assertIsNone(report['bootloader_unlocked_confirmed'])
        self.assertEqual(len(report['capacities']), 19)
        for call in runner.call_args_list:
            cmd = call.args[0]
            if cmd not in (['adb', 'version'], ['adb', 'devices', '-l']):
                self.assertEqual(cmd[:3], ['adb', '-t', '7'])
            self.assertFalse(any(x in cmd for x in ('root', 'remount', 'reboot', 'flash', 'wipe')))
        self.assertFalse(any('bootctl' in c.args[0][-1] or 'dd ' in c.args[0][-1] for c in runner.call_args_list))
        for record in report['commands']:
            for stream in ('stdout', 'stderr'):
                saved = self.output/record[stream]['path']
                self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(),record[stream]['sha256'])

    def test_raw_firmware_and_super_capture_are_bounded_and_read_only(self):
        code, _, err, runner = self.invoke([*self.args, '--include-firmware', '--include-super-metadata'])
        self.assertEqual(code, 0, err)
        raw = [shlex.split(c.args[0][-1]) for c in runner.call_args_list if c.args[0][-1].startswith('dd ')]
        self.assertEqual(len(raw), 6)
        self.assertTrue(all(cmd[-2:] == ['bs=4096', 'count=256'] for cmd in raw))
        self.assertTrue(all(not any(t.startswith('of=') for t in cmd) for cmd in raw))
        self.assertTrue(self.report()['firmware']['countrycode_a']['authenticated_region_matches'])
        self.assertTrue(self.report()['super_metadata_capture']['host_lp_parse_pending'])

    def test_toybox_block_device_label_supports_same_raw_identity_checks(self):
        def effect(command, **kwargs):
            r = self.fake(command, **kwargs)
            if command[-1].startswith('stat '):
                r['stdout'] = r['stdout'].replace(b'block special file:', b'block device:')
            return r
        code, _, _, _ = self.invoke([*self.args, '--include-firmware'], effect)
        self.assertEqual(code, 0)
        self.assertTrue(self.report()['firmware'])

    def test_nonblock_device_label_never_allows_raw_reads(self):
        def effect(command, **kwargs):
            r = self.fake(command, **kwargs)
            if command[-1].startswith('stat '):
                r['stdout'] = r['stdout'].replace(b'block special file:', b'character device:')
            return r
        code, _, _, runner = self.invoke([*self.args, '--include-firmware'], effect)
        self.assertEqual(code, 2)
        self.assertFalse(any(c.args[0][-1].startswith('dd ') for c in runner.call_args_list))

    def test_raw_reads_refused_without_existing_root(self):
        self.uid = '2000'
        code, _, _, runner = self.invoke([*self.args, '--include-firmware'])
        self.assertEqual(code, 2)
        self.assertFalse(any(c.args[0][-1].startswith('dd ') for c in runner.call_args_list))

    def test_raw_short_read_is_not_admitted(self):
        def effect(command, **kwargs):
            if command[-1].startswith('dd '):
                return result(b'short')
            return self.fake(command, **kwargs)
        code, _, _, _ = self.invoke([*self.args, '--include-firmware'], effect)
        self.assertEqual(code, 2)
        self.assertFalse(self.report()['firmware'])

    def test_bootloader_mode_rejects_fastbootd_before_trust_or_capacity_queries(self):
        self.mode = 'yes'
        code, _, _, runner = self.invoke([*self.args, '--mode', 'fastboot-bootloader'])
        self.assertEqual(code, 2)
        self.assertEqual(len(runner.call_args_list), 1)
        self.assertEqual(runner.call_args.args[0][-1], 'is-userspace')

    def test_bootloader_reads_only_getvars_and_does_not_claim_board_or_rollback(self):
        code, _, err, runner = self.invoke([*self.args, '--mode', 'fastboot-bootloader'])
        self.assertEqual(code, 0, err)
        report = self.report()
        self.assertTrue(report['bootloader_unlocked_confirmed'])
        self.assertIsNone(report['board_identity'])
        self.assertIsNone(report['secure_rollback_indices'])
        self.assertFalse(report['snapshot_idle_verified'])
        self.assertFalse(report['flash_ready'])
        for call in runner.call_args_list:
            self.assertEqual(call.args[0][:4], ['fastboot','-s',self.serial,'getvar'])
            self.assertIn(call.args[0][4],candidate.FASTBOOT_VARS)

    def test_unknown_bootloader_lock_remains_unknown(self):
        def effect(command, **kwargs):
            if command[-1]=='unlocked':
                return result(b'', b'FAILED (remote: unknown variable)', 'failed', 1)
            return self.fake(command, **kwargs)
        code, _, _, _ = self.invoke([*self.args, '--mode', 'fastboot-bootloader'], effect)
        self.assertEqual(code,3)
        self.assertIsNone(self.report()['bootloader_unlocked_confirmed'])

    def test_changed_running_slot_invalidates_collection(self):
        counts = {}
        def effect(command, **kwargs):
            if command[-1]=='getprop ro.boot.slot_suffix':
                counts['slot']=counts.get('slot',0)+1
                if counts['slot']>1:return result(b'_b\n')
            return self.fake(command, **kwargs)
        code, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(code,2)

    def test_zero_exit_malformed_getvar_is_partial_not_complete(self):
        def effect(command, **kwargs):
            if command[-1] == 'unlocked':
                return result(b'unlocked: \n')
            return self.fake(command, **kwargs)
        code, _, _, _ = self.invoke([*self.args, '--mode', 'fastboot-bootloader'], effect)
        self.assertEqual(code, 3)
        self.assertIn('fastboot:unlocked', self.report()['unknowns'])

    def test_mode_changes_before_raw_capture_are_refused(self):
        counts = {}
        def effect(command, **kwargs):
            if command[-1] == 'getprop init.svc.recovery':
                counts['mode'] = counts.get('mode', 0) + 1
                if counts['mode'] > 1:
                    return result(b'stopped\n')
            return self.fake(command, **kwargs)
        code, _, _, runner = self.invoke([*self.args, '--include-firmware'], effect)
        self.assertEqual(code, 2)
        self.assertFalse(any(c.args[0][-1].startswith('dd ') for c in runner.call_args_list))

    def test_paired_raw_content_changes_are_refused(self):
        counts = {}
        def effect(command, **kwargs):
            if command[-1].startswith('dd '):
                counts[command[-1]] = counts.get(command[-1], 0) + 1
                if counts[command[-1]] > 1:
                    return result(b'X' + self.fwbody[1:])
            return self.fake(command, **kwargs)
        code, _, _, _ = self.invoke([*self.args, '--include-firmware'], effect)
        self.assertEqual(code, 2)
        self.assertFalse(self.report()['firmware'])

    def test_failed_first_raw_capture_does_not_trigger_repeat(self):
        for failure in (result(self.fwbody, b'I/O error', 'failed', 1),
                        result(self.fwbody, status='byte_limit', exit_code=None, truncated=('stdout',))):
            with self.subTest(status=failure['status']):
                self.output = self.root / 'evidence' / failure['status']
                args = [*self.args, '--output', str(self.output), '--include-firmware']
                def effect(command, **kwargs):
                    if command[-1].startswith('dd '):
                        return failure
                    return self.fake(command, **kwargs)
                code, _, _, runner = self.invoke(args, effect)
                self.assertEqual(code, 2)
                self.assertEqual(sum(c.args[0][-1].startswith('dd ') for c in runner.call_args_list), 1)

    def test_raw_node_change_stops_before_repeat(self):
        counts = {}
        def effect(command, **kwargs):
            if command[-1] == "stat -L -c %F:%t:%T /dev/block/by-name/countrycode_a":
                counts['type'] = counts.get('type', 0) + 1
                if counts['type'] > 1:
                    return result(b'block special file:8:2\n')
            return self.fake(command, **kwargs)
        code, _, _, runner = self.invoke([*self.args, '--include-firmware'], effect)
        self.assertEqual(code, 2)
        self.assertEqual(sum(c.args[0][-1].startswith('dd ') for c in runner.call_args_list), 1)

    def test_time_exhaustion_preserves_blocked_manifest_without_device_calls(self):
        with mock.patch.object(candidate.time, 'monotonic', side_effect=[0, 1000]):
            code, _, _, runner = self.invoke()
        self.assertEqual(code, 2)
        runner.assert_not_called()
        self.assertEqual(self.report()['status'], 'blocked-or-incomplete')

    def test_interrupted_capture_writes_incomplete_manifest(self):
        code, _, _, _ = self.invoke(effect=lambda *a, **k: result(status='interrupted', exit_code=None))
        self.assertEqual(code, 130)
        self.assertEqual(self.report()['status'], 'interrupted')
        self.assertFalse(self.report()['flash_ready'])

    def test_network_inventory_without_usb_marker_stops_before_device_reads(self):
        def effect(command, **kwargs):
            if command == ['adb', 'devices', '-l']:
                return result(f'{self.serial} recovery transport_id:7\n'.encode())
            return self.fake(command, **kwargs)
        code, _, _, runner = self.invoke([*self.args, '--include-firmware'], effect)
        self.assertEqual(code, 2)
        self.assertEqual(len(runner.call_args_list), 2)

    def test_nonlocal_adb_server_environment_refused_before_process(self):
        with mock.patch.dict(candidate.os.environ, {'ADB_SERVER_SOCKET': 'tcp:192.0.2.1:5037'}):
            with mock.patch.object(candidate, 'bounded_run') as runner:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    candidate.main(self.args)
                runner.assert_not_called()

    def test_dm_or_aliased_block_nodes_refused_before_raw_reads(self):
        def effect(command, **kwargs):
            if command[-1].startswith('readlink -f /dev/block/by-name/'):
                return result(b'/dev/block/dm-0\n')
            return self.fake(command, **kwargs)
        code, _, _, runner = self.invoke([*self.args, '--include-firmware'], effect)
        self.assertEqual(code, 2)
        self.assertFalse(any(c.args[0][-1].startswith('dd ') for c in runner.call_args_list))

    def test_valid_false_bootctl_getter_is_a_complete_observation(self):
        def effect(command, **kwargs):
            if command[-1] == 'bootctl is-slot-bootable 1':
                return result(b'0\n', status='failed', exit_code=70)
            return self.fake(command, **kwargs)
        code, _, err, _ = self.invoke([*self.args, '--include-boot-control'], effect)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.report()['bootctl']['is-slot-bootable 1']['value'], '0')
        self.assertFalse(self.report()['snapshot_idle_verified'])

    def test_recovery_process_disappearance_invalidates_final_recheck(self):
        count = 0
        def effect(command, **kwargs):
            nonlocal count
            if command[-1] == 'pidof recovery':
                count += 1
                if count > 1:
                    return result(b'', status='failed', exit_code=1)
            return self.fake(command, **kwargs)
        code, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(code, 2)

    def test_output_outside_evidence_or_existing_is_refused_without_device_calls(self):
        for path in (self.root/'outside',self.root/'evidence'):
            with self.subTest(path=path):
                code, _, _, runner = self.invoke([*self.args,'--output',str(path)])
                self.assertEqual(code,2)
                runner.assert_not_called()
        self.output.mkdir(parents=True)
        code, _, _, runner=self.invoke()
        self.assertEqual(code,2)
        runner.assert_not_called()

    def test_symlink_output_parent_is_refused_without_device_calls(self):
        elsewhere=self.root/'elsewhere';elsewhere.mkdir()
        (self.root/'evidence').symlink_to(elsewhere,target_is_directory=True)
        code, _, _, runner=self.invoke()
        self.assertEqual(code,2)
        runner.assert_not_called()


if __name__ == '__main__':
    unittest.main()

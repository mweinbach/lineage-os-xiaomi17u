#!/usr/bin/env python3
"""Stage an opt-in original Xiaomi Camera system-ext candidate; never install it."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
if __package__:
    from . import camera_apk_inputs as base
else:
    import camera_apk_inputs as base

NAMESPACE = 'vendor/xiaomi/nezha-camera'
MODULE = 'NezhaXiaomiCamera'
PERMISSION_MODULE = 'nezha_xiaomi_camera_privapp_permissions'
PERMISSION_FILE = 'permissions/privapp-permissions-nezha-camera.xml'
RECEIPT = 'camera-product-inputs.json'


def permission_policy(review):
    """Derive only reviewed platform privileged requests, including flag variants."""
    permissions = review['permissions']
    allows = permissions['normalized_possibly_privileged_requests']
    base.require(len(allows) == 11 and len(set(allows)) == 11,
                 'unexpected privileged permission profile')
    base.require(set(allows) <= set(permissions['factory_camera_block']['allow']),
                 'permission absent from factory Camera policy')
    base.require(not set(allows) & set(permissions['pure_platform_signature_requests']),
                 'cannot grant pure signature permissions through privileged policy')
    return ('<?xml version="1.0" encoding="utf-8"?>\n<permissions>\n'
            '    <privapp-permissions package="com.android.camera">\n' +
            ''.join(f'        <permission name="{name}" />\n' for name in sorted(allows)) +
            '    </privapp-permissions>\n</permissions>\n').encode()


def render(source):
    """Use the verified packet payload; regenerate its producer for the new graph."""
    files = {name: raw for name, raw in source.items()
             if name not in {'Android.bp', 'tools/verify_camera_apk.py'}}
    files[PERMISSION_FILE] = permission_policy(base.metadata(files['provenance/review.json']))
    files['camera-product.mk'] = (f'# Original factory APK; candidate requires native and device validation.\n'
        f'PRODUCT_SOONG_NAMESPACES += {NAMESPACE}\n'
        f'PRODUCT_PACKAGES += {MODULE} {PERMISSION_MODULE} androidx.window.extensions androidx.window.sidecar\n').encode()
    blueprint = base._blueprint([*files, 'Android.bp']).decode()
    blueprint = blueprint.replace('// Generated build-only input packet; no product or image admission.',
        '// Original factory Camera product candidate; preserve signature and strict library checks.')
    # System-ext keeps the platform-dependent app bundled in LoadedApk.
    # Preserve all other import properties and the original payload bytes.
    blueprint = blueprint.replace('    product_specific: true,', '    system_ext_specific: true,')
    blueprint = blueprint.replace(base.MODULE, MODULE)
    blueprint = blueprint.replace('nezha_factory_camera_', 'nezha_product_camera_')
    blueprint = blueprint.replace('    owner: "xiaomi",',
        f'    owner: "xiaomi",\n    filename: "MiuiCamera.apk",\n    required: ["{PERMISSION_MODULE}"],')
    blueprint += f'''\nprebuilt_etc {{
    name: "{PERMISSION_MODULE}",
    src: "{PERMISSION_FILE}",
    filename: "privapp-permissions-nezha-camera.xml",
    sub_dir: "permissions",
    system_ext_specific: true,
}}\n'''
    base.require('product_specific' not in blueprint, 'Camera integration must remain system-ext')
    files['Android.bp'] = blueprint.encode()
    files['tools/verify_camera_apk.py'] = base._native({n: base.identity(b) for n,b in sorted(files.items())})
    return files


def expected_packet(input_packet):
    verified = base.verify_bundle(input_packet)
    reader = base.Reader()
    source = {row['path'].removeprefix('source/'): reader.read(Path(input_packet)/row['path'], row, base.MAX_APK)
              for row in verified['files'] if row['path'].startswith('source/')}
    files = {'source/'+name: raw for name,raw in render(source).items()}
    receipt = {'schema_version': 1, 'purpose': 'factory-camera-system-ext-candidate',
        'partition': 'system_ext',
        'namespace': NAMESPACE, 'module': MODULE, 'original_packet': verified['receipt'],
        'include': NAMESPACE+'/camera-product.mk',
        'apk_transformed_or_signed': False, 'phone_accessed': False,
        'native_build_verified': False, 'runtime_verified': False,
        'files': [{'path': name, 'destination': NAMESPACE+'/'+name.removeprefix('source/'), **base.identity(raw)}
                  for name,raw in sorted(files.items())]}
    files[RECEIPT] = base.encoded(receipt)
    reader.recheck()
    return files, receipt


def verify(input_packet, bundle):
    files, receipt = expected_packet(input_packet)
    reader = base.Reader()
    base._inventory(base.directory(bundle), files, reader)
    reader.recheck()
    return receipt


def stage(input_packet, output):
    files, receipt = expected_packet(input_packet)
    output = Path(os.path.abspath(output))
    base.require(any(root in output.parents for root in (base.ROOT/'artifacts', base.ROOT/'evidence')),
                 'output must stay in ignored artifacts/ or evidence/')
    base.directory(output.parent)
    base.require(not os.path.lexists(output), 'output already exists')
    base.require(not output.is_relative_to(Path(input_packet).resolve()), 'output overlaps input packet')
    scratch = Path(tempfile.mkdtemp(prefix='.camera-product-', dir=output.parent))
    try:
        for name, raw in files.items():
            path = scratch/name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                os.chmod(path, 0o600)
                stream.write(raw)
        verify(input_packet, scratch)
        base.publish_new_directory(scratch, output)
        scratch = None
    finally:
        if scratch is not None:
            shutil.rmtree(scratch)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['stage', 'verify'])
    parser.add_argument('--input-packet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = stage(args.input_packet, args.output) if args.command == 'stage' else verify(args.input_packet, args.output)
        print(json.dumps(result, sort_keys=True, indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, str(error)+'\n')

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Generate reviewed pre-upgrade setup and verify substantive upstream test runs."""
import argparse
import base64
import hashlib
import io
import importlib.machinery
import json
import re
import shlex
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
prepare = importlib.machinery.SourceFileLoader('package_prepare', str(ROOT/'scripts/prepare-plasma-package.py')).load_module()


def reviewed_setup_files(root, record):
    if record.get('baseline_setup_payload') is None:
        return [record['baseline_setup_script']]
    assert record['baseline_setup_payload'] == 'reviewed-tests-tree', 'Unknown baseline payload format'
    names = sorted(name for name in record['packaging_sha256'] if name.startswith('tests/'))
    assert record['baseline_setup_script'] in names, 'Baseline script absent from reviewed tree'
    packaging = root / record['packaging_path']
    assert packaging.resolve().is_relative_to(root.resolve()), 'Packaging tree escapes root'
    for name in names:
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        path = packaging / relative
        assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(packaging.resolve()), 'Baseline file escapes reviewed tree'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['packaging_sha256'][name], 'Baseline tree inputs changed'
    return names


def verify_baseline_input_hashes(record, baseline):
    mode = record.get('baseline_setup_payload')
    assert mode in {None, 'reviewed-tests-tree'}, 'Unknown baseline payload format'
    names = ([record['baseline_setup_script']] if mode is None else
             sorted(name for name in record['packaging_sha256'] if name.startswith('tests/')))
    assert record['baseline_setup_script'] in names
    for name in names:
        assert baseline['inputs_sha256'][record['packaging_path'] + '/' + name] == record['packaging_sha256'][name], 'Baseline reviewed input mismatch'


def reviewed_tree_commands(root, record):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as archive:
        for name in reviewed_setup_files(root, record):
            payload = (root / record['packaging_path'] / name).read_bytes()
            entry = tarfile.TarInfo(name)
            entry.size = len(payload)
            entry.mode = 0o755 if name in record['required_executable_files'] else 0o644
            archive.addfile(entry, io.BytesIO(payload))
    payload = stream.getvalue()
    encoded = base64.b64encode(payload).decode()
    wrapped = '\n'.join(encoded[offset:offset+76] for offset in range(0, len(encoded), 76))
    return ['baseline_root=$(mktemp -d)',
            'trap \'rm -rf "$baseline_root"\' EXIT',
            'base64 --decode > "$baseline_root/payload.tar" <<\'SUPRALINUX_BASELINE_TREE_BASE64\'',
            wrapped, 'SUPRALINUX_BASELINE_TREE_BASE64',
            f"printf '%s  %s\\n' {shlex.quote(hashlib.sha256(payload).hexdigest())} \"$baseline_root/payload.tar\" | sha256sum --check --strict",
            'tar --extract --file="$baseline_root/payload.tar" --directory="$baseline_root" --no-same-owner',
            'bash "$baseline_root"/' + shlex.quote(record['baseline_setup_script'])]


def setup_commands(root, record):
    package, version = record['ubuntu_baseline_package'], record['version']
    assert re.fullmatch(r'[a-z0-9][a-z0-9+.-]+', package), 'Invalid Ubuntu baseline package'
    commands = ['set -eu', 'apt-get update',
                f'apt-get install -y --no-install-recommends {package}',
                f"dpkg-query -W -f='${{Version}}' {package} > /var/tmp/supralinux-ubuntu-package-version",
                f'dpkg --compare-versions {shlex.quote(version)} gt "$(cat /var/tmp/supralinux-ubuntu-package-version)"']
    script = record.get('baseline_setup_script')
    if script:
        relative = PurePosixPath(script)
        assert not relative.is_absolute() and '..' not in relative.parts, 'Unsafe baseline setup path'
        assert script.startswith('tests/'), 'Baseline setup must belong to the reviewed package tests'
        if record.get('baseline_setup_payload') is not None:
            return '\n'.join(commands + reviewed_tree_commands(root, record))
        payload = (root/record['packaging_path']/relative).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == record['packaging_sha256'][script], 'Setup inputs changed'
        encoded = base64.b64encode(payload).decode()
        wrapped = '\n'.join(encoded[offset:offset + 76] for offset in range(0, len(encoded), 76))
        commands.extend(["baseline_setup=$(mktemp)",
                         "trap 'rm -f \"$baseline_setup\"' EXIT",
                         "base64 --decode > \"$baseline_setup\" <<'SUPRALINUX_BASELINE_SETUP_BASE64'",
                         wrapped,
                         "SUPRALINUX_BASELINE_SETUP_BASE64",
                         f"printf '%s  %s\\n' {shlex.quote(hashlib.sha256(payload).hexdigest())} \"$baseline_setup\" | sha256sum --check --strict",
                         'bash "$baseline_setup"'])
    return '\n'.join(commands)


def upstream_test_result(record, log):
    expected = record.get('upstream_tests', [])
    assert len(set(expected)) == len(expected), 'Duplicate upstream test names'
    for name in expected:
        assert re.search(r'Test\s+#\d+:\s+' + re.escape(name) + r'\s+\.+\s+Passed\s+', log), f'Upstream test did not pass: {name}'
    executed = re.findall(r'Test\s+#\d+:\s+(\S+)\s+\.+\s+Passed\s+', log)
    if expected:
        assert len(executed) == len(re.findall(r'Test\s+#\d+:\s+\S+\s+\.+\s+', log)), 'Some executed upstream tests did not pass'
        assert len(executed) == len(set(executed)), 'Duplicate upstream test executions'
        assert set(expected) <= set(executed)
        # ECM may add integration tests (for example AppStream). Every executed
        # test must pass, and the summary must account for all recorded entries.
        assert re.search(r'100% tests passed, 0 tests failed out of ' + str(len(executed)) + r'\b', log), 'Upstream suite count/result mismatch'
    return {'state': 'PASS' if expected else 'not-applicable', 'expected_tests': expected,
            'executed_tests': executed, 'scope': 'CTest suite executed during the clean package build'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['setup', 'upstream-tests'])
    p.add_argument('node')
    p.add_argument('--build-log', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    record = prepare.load_campaign()['nodes'][a.node]
    if a.mode == 'setup':
        print(setup_commands(ROOT, record))
    else:
        assert a.build_log and a.output
        result = upstream_test_result(record, a.build_log.read_text())
        a.output.write_text(json.dumps(result, indent=2)+'\n')
        print(f"Upstream package tests: {result['state']}; required={len(result['expected_tests'])}; executed={len(result['executed_tests'])}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Generate reviewed pre-upgrade setup and verify substantive upstream test runs."""
import argparse
import base64
import hashlib
import json
import re
import shlex
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


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
        payload = (root/record['packaging_path']/relative).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == record['packaging_sha256'][script], 'Setup inputs changed'
        encoded = base64.b64encode(payload).decode()
        commands.extend(["baseline_setup=$(mktemp)",
                         "trap 'rm -f \"$baseline_setup\"' EXIT",
                         f"printf '%s' {shlex.quote(encoded)} | base64 --decode > \"$baseline_setup\"",
                         'bash "$baseline_setup"'])
    return '\n'.join(commands)


def upstream_test_result(record, log):
    expected = record.get('upstream_tests', [])
    assert len(set(expected)) == len(expected), 'Duplicate upstream test names'
    for name in expected:
        assert re.search(r'Test\s+#\d+:\s+' + re.escape(name) + r'\s+\.+\s+Passed\s+', log), f'Upstream test did not pass: {name}'
    if expected:
        assert re.search(r'100% tests passed, 0 tests failed out of ' + str(len(expected)) + r'\b', log), 'Upstream suite count/result mismatch'
    return {'state': 'PASS' if expected else 'not-applicable', 'expected_tests': expected,
            'scope': 'CTest suite executed during the clean package build'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['setup', 'upstream-tests'])
    p.add_argument('node')
    p.add_argument('--build-log', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    record = json.loads((ROOT/'manifests/kde-plasma-package-build.json').read_text())['nodes'][a.node]
    if a.mode == 'setup':
        print(setup_commands(ROOT, record))
    else:
        assert a.build_log and a.output
        result = upstream_test_result(record, a.build_log.read_text())
        a.output.write_text(json.dumps(result, indent=2)+'\n')
        print(f"Upstream package tests: {result['state']}; count={len(result['expected_tests'])}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Generate reviewed pre-upgrade setup and verify substantive upstream test runs."""
import argparse
import base64
import hashlib
import io
import importlib.machinery
import inspect
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


def configure_ubuntu_apt_https(root):
    """Change only official Ubuntu transport in a disposable testbed."""
    root = root.resolve()
    bundle = root/'etc/ssl/certs/ca-certificates.crt'
    assert bundle.is_file() and bundle.stat().st_size, 'Testbed Ubuntu CA trust store is missing'
    apt = root/'etc/apt'
    paths = [apt/'sources.list'] + sorted((apt/'sources.list.d').glob('*.list'))
    paths += sorted((apt/'sources.list.d').glob('*.sources'))
    changed = []
    for path in paths:
        if not path.is_file():
            continue
        assert path.resolve().is_relative_to(root), 'APT source file escapes the disposable testbed'
        before = path.read_bytes()
        after = re.sub(rb'http://(?:archive|security)\.ubuntu\.com/ubuntu(?=[/\s]|$)',
                       lambda match: match.group().replace(b'http:',b'https:',1), before)
        if after != before:
            path.write_bytes(after)
            changed.append(str(path.relative_to(root)))
    return changed


def setup_commands(root, record, https_transport=False):
    package, version = record['ubuntu_baseline_package'], record['version']
    assert re.fullmatch(r'[a-z0-9][a-z0-9+.-]+', package), 'Invalid Ubuntu baseline package'
    transport = []
    if https_transport:
        transport = ["python3 - <<'SUPRALINUX_UBUNTU_APT_HTTPS'", 'import re', 'from pathlib import Path',
                     inspect.getsource(configure_ubuntu_apt_https).rstrip(),
                     'changed = configure_ubuntu_apt_https(Path("/"))',
                     'print("Official Ubuntu APT HTTPS transport configured:", changed)',
                     'SUPRALINUX_UBUNTU_APT_HTTPS']
    commands = ['set -eu', *transport, 'apt-get update',
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


def meson_test_result(record, log):
    """Require each numbered Meson result and the complete successful summary."""
    expected = record.get('upstream_tests', [])
    project = record.get('upstream_test_project', '')
    assert expected and len(set(expected)) == len(expected), 'Reviewed Meson tests required'
    assert re.fullmatch(r'[A-Za-z0-9_.+-]+', project), 'Reviewed Meson project required'
    rows = re.findall(r'^[ \t]*(\d+)/(\d+)[ \t]+(\S+)[ \t]+(.+?)[ \t]+\d+(?:\.\d+)?s(?:[ \t].*)?$', log, re.MULTILINE)
    assert rows, 'Meson test executions missing'
    count = len(rows)
    assert sorted(int(row[0]) for row in rows) == list(range(1, count + 1)), 'Missing or duplicate Meson test indexes'
    assert all(int(row[1]) == count for row in rows), 'Meson suite count mismatch'
    assert all(row[3] == 'OK' for row in rows), 'Some executed Meson tests did not pass'
    assert all(row[2].startswith(project + ':') for row in rows), 'Unexpected Meson project'
    executed = [row[2].removeprefix(project + ':') for row in rows]
    assert len(executed) == len(set(executed)), 'Duplicate Meson test executions'
    assert set(expected) <= set(executed), 'Reviewed Meson tests missing'
    summaries = re.findall(r'^[ \t]*Ok:[ \t]*(\d+)[ \t]*$', log, re.MULTILINE | re.IGNORECASE)
    failures = re.findall(r'^[ \t]*Fail:[ \t]*(\d+)[ \t]*$', log, re.MULTILINE | re.IGNORECASE)
    assert summaries == [str(count)] and failures == ['0'], 'Meson summary count/result mismatch'
    other = re.findall(r'^[ \t]*(?:Skipped|Timeout|Expected Fail|Unexpected Pass):[ \t]*(\d+)[ \t]*$', log, re.MULTILINE | re.IGNORECASE)
    assert all(int(value) == 0 for value in other), 'Meson non-passing results present'
    return {'state': 'PASS', 'expected_tests': expected, 'executed_tests': executed,
            'scope': 'Meson suite executed during the clean package build'}


def upstream_test_result(record, log):
    backend = record.get('upstream_test_backend', 'ctest')
    assert backend in {'ctest', 'meson'}, 'Unknown upstream test backend'
    if backend == 'meson':
        return meson_test_result(record, log)
    expected = record.get('upstream_tests', [])
    expected_cases = record.get('upstream_test_cases', [])
    exclusions = record.get('upstream_test_exclusions', [])
    assert len(set(expected)) == len(expected), 'Duplicate upstream test names'
    assert len(set(expected_cases)) == len(expected_cases), 'Duplicate upstream test cases'
    for name in expected:
        assert re.search(r'Test\s+#\d+:\s+' + re.escape(name) + r'\s+\.+\s+Passed\s+', log), f'Upstream test did not pass: {name}'
    executed = re.findall(r'Test\s+#\d+:\s+(\S+)\s+\.+\s+Passed\s+', log)
    if expected:
        assert len(executed) == len(re.findall(r'Test\s+#\d+:\s+\S+\s+\.+\s+', log)), 'Some executed upstream tests did not pass'
        assert len(executed) == len(set(executed)), 'Duplicate upstream test executions'
        assert set(expected) <= set(executed)
        assert re.search(r'100% tests passed, 0 tests failed out of ' + str(len(executed)) + r'\b', log), 'Upstream suite count/result mismatch'
    for case in expected_cases:
        assert re.search(r'PASS\s+:\s+' + re.escape(case), log), f'Upstream test case did not pass: {case}'
    excluded_cases = []
    for exclusion in exclusions:
        assert set(exclusion) == {'test', 'reason', 'marker'}, 'Invalid upstream test exclusion contract'
        name = exclusion['test']
        assert name and exclusion['reason'] and exclusion['marker']
        assert exclusion['marker'] in log, f'Upstream exclusion marker missing: {name}'
        assert not re.search(r'(?:PASS|FAIL!|XFAIL|XPASS)\s+:\s+' + re.escape(name), log), f'Excluded upstream test case executed: {name}'
        excluded_cases.append(name)
    assert not (set(expected_cases) & set(excluded_cases)), 'Upstream test case both required and excluded'
    return {'state': 'PASS' if expected or expected_cases else 'not-applicable',
            'expected_tests': expected, 'executed_tests': executed,
            'expected_cases': expected_cases, 'excluded_cases': excluded_cases,
            'scope': 'CTest suite plus reviewed hermetic QtTest cases executed during the clean package build'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['setup', 'upstream-tests'])
    p.add_argument('node')
    p.add_argument('--build-log', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--https-transport', action='store_true')
    a = p.parse_args()
    record = prepare.load_campaign()['nodes'][a.node]
    if a.mode == 'setup':
        print(setup_commands(ROOT, record, https_transport=a.https_transport))
    else:
        assert a.build_log and a.output
        result = upstream_test_result(record, a.build_log.read_text())
        a.output.write_text(json.dumps(result, indent=2)+'\n')
        print(f"Upstream package tests: {result['state']}; required={len(result['expected_tests'])}; executed={len(result['executed_tests'])}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Certify large reviewed setup payloads through the real nested QEMU testbed."""
import argparse
import hashlib
import importlib.machinery
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
testing = importlib.machinery.SourceFileLoader('testing', str(ROOT / 'scripts/plasma-package-testing.py')).load_module()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    work = ROOT / '.work/autopkgtest-baseline-transport'
    evidence = ROOT / 'evidence/runner-contract/baseline-transport'
    assert not work.exists() and not evidence.exists(), 'Refusing to overwrite probe evidence'
    source = work / 'source'
    (source / 'debian/tests').mkdir(parents=True)
    evidence.mkdir(parents=True)
    marker = '/var/tmp/supralinux-baseline-transport'
    expected = 'complete-reviewed-baseline-setup'
    payload = ('#!/bin/sh\nset -eu\n# ' + 'large-reviewed-script-fixture ' * 1500 + '\n' +
               f"printf '%s' '{expected}' > {marker}\n").encode()
    setup = source / 'debian/tests/baseline-setup'
    setup.write_bytes(payload)
    # autopkgtest supports a tests-only tree as built-tree with no binary build.
    # A Debian/control file would instead select unbuilt-tree source extraction.
    (source / 'debian/tests/control').write_text('Tests: preserved-setup\nDepends: coreutils\nRestrictions: needs-root\n')
    test = source / 'debian/tests/preserved-setup'
    test.write_text(f'#!/bin/sh\nset -eu\ntest "$(cat {marker})" = "{expected}"\n'
                    "printf 'Large exact reviewed baseline arrived and executed before testing: PASS\\n'\n")
    test.chmod(0o755)
    record = {'ubuntu_baseline_package': 'base-files', 'version': '9999.0', 'packaging_path': 'source/debian',
              'baseline_setup_script': 'tests/baseline-setup',
              'packaging_sha256': {'tests/baseline-setup': hashlib.sha256(payload).hexdigest()}}
    commands = testing.setup_commands(work, record)
    assert len(payload) > 4096 and max(len(line.encode()) for line in commands.splitlines()) < 512
    for name, path in [('baseline-setup', setup), ('preserved-setup', test)]:
        shutil.copyfile(path, evidence / name)
    (evidence / 'setup-commands.txt').write_text(commands)
    (evidence / 'fixture.json').write_text(json.dumps(record, indent=2) + '\n')
    if args.prepare_only:
        print('Large baseline transport fixture prepared; authoritative KVM execution not started')
        return
    image = os.environ.get('AUTOPKGTEST_QEMU_IMAGE', '/var/lib/supralinux/autopkgtest/resolute-amd64.img')
    command = ['autopkgtest', str(source), '--no-built-binaries', '--setup-commands=' + commands,
               '--output-dir=' + str(evidence / 'autopkgtest'), '--', 'qemu',
               '--qemu-command=' + str(ROOT / 'scripts/qemu-kvm-required.sh'),
               '--qemu-architecture=x86_64', '--cpus=2', '--ram-size=2048', image]
    print('Certifying large reviewed baseline transport in nested KVM...', flush=True)
    with (evidence / 'pipeline.log').open('w') as log:
        execution = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    summary = evidence / 'autopkgtest/summary'
    passed = execution.returncode == 0 and summary.is_file() and re.fullmatch(r'preserved-setup\s+PASS', summary.read_text().strip()) is not None
    result = {'schema': 1, 'scope': 'large-reviewed-autopkgtest-baseline-transport',
              'state': 'PASS' if passed else 'INFRA_INVALID', 'exit_code': execution.returncode,
              'source_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
              'workflow_run_id': os.environ.get('GITHUB_RUN_ID'), 'package_execution_started': False,
              'consumes_package_attempt': False, 'canonical_package_state_effect': 'none',
              'system_test_backend': 'autopkgtest-qemu', 'system_test_acceleration': 'kvm-required',
              'setup_payload_bytes': len(payload), 'setup_max_line_bytes': max(len(line.encode()) for line in commands.splitlines()),
              'setup_payload_sha256': hashlib.sha256(payload).hexdigest(),
              'inputs_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [Path(__file__), ROOT / 'scripts/plasma-package-testing.py', ROOT / 'scripts/qemu-kvm-required.sh']},
              'files_sha256': {str(p.relative_to(evidence)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(evidence.rglob('*')) if p.is_file() and p.name != 'pipeline.log'}}
    (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'Large reviewed baseline transport: {result["state"]}; package Attempts consumed=0')
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Execute the current reviewed Ubuntu baseline without building a candidate."""
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
testing = importlib.machinery.SourceFileLoader(
    'testing', str(ROOT / 'scripts/plasma-package-testing.py')).load_module()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    campaign = testing.prepare.load_campaign()
    nodes = campaign['authorized_nodes']
    assert len(nodes) <= 1, 'Preflight requires an individually reviewed current node'
    if not nodes or not campaign['nodes'][nodes[0]].get('baseline_setup_script'):
        print('No current reviewed Ubuntu baseline requires execution')
        return
    node = nodes[0]
    record = campaign['nodes'][node]
    assert not campaign.get('dependency_hold'), 'Repair the known predecessor upgrade conflict first'
    assert record['state'] == 'build-pending' and record['packaging_review'] == 'PASS'
    work = ROOT / '.work/reviewed-ubuntu-baseline'
    evidence = ROOT / 'evidence/runner-contract/reviewed-ubuntu-baseline'
    assert not work.exists() and not evidence.exists(), 'Refusing to overwrite preflight evidence'
    source = work / 'source'
    (source / 'debian/tests').mkdir(parents=True)
    evidence.mkdir(parents=True)
    commands = testing.setup_commands(ROOT, record)
    (source / 'debian/tests/control').write_text(
        'Tests: reviewed-baseline\nDepends: coreutils, dpkg\nRestrictions: needs-root\n')
    test = source / 'debian/tests/reviewed-baseline'
    # The setup itself compiles and executes the reviewed real Ubuntu client.
    # This test also detects a missing setup or an unintended candidate install.
    test.write_text('#!/bin/sh\nset -eu\n'
                    'test -s /var/tmp/supralinux-ubuntu-package-version\n'
                    f'actual=$(dpkg-query -W -f=\'${{Version}}\' {record["ubuntu_baseline_package"]})\n'
                    'test "$actual" = "$(cat /var/tmp/supralinux-ubuntu-package-version)"\n'
                    "printf 'Reviewed Ubuntu baseline client completed before candidate installation: PASS\\n'\n")
    test.chmod(0o755)
    baseline = ROOT / record['packaging_path'] / record['baseline_setup_script']
    shutil.copyfile(baseline, evidence / 'baseline-setup')
    (evidence / 'setup-commands.txt').write_text(commands)
    frozen = {key: record[key] for key in ['source_package', 'version', 'ubuntu_baseline_package',
                                         'baseline_setup_script', 'packaging_path', 'packaging_sha256']}
    (evidence / 'reviewed-inputs.json').write_text(json.dumps(frozen, indent=2) + '\n')
    if args.prepare_only:
        print(f'{node}: reviewed Ubuntu baseline prepared; no candidate package execution')
        return
    image = os.environ.get('AUTOPKGTEST_QEMU_IMAGE', '/var/lib/supralinux/autopkgtest/resolute-amd64.img')
    command = ['autopkgtest', str(source), '--no-built-binaries', '--setup-commands=' + commands,
               '--output-dir=' + str(evidence / 'autopkgtest'), '--', 'qemu',
               '--qemu-command=' + str(ROOT / 'scripts/qemu-kvm-required.sh'),
               '--qemu-architecture=x86_64', '--cpus=2', '--ram-size=2048', image]
    print(f'Executing {node} reviewed Ubuntu baseline in nested KVM...', flush=True)
    with (evidence / 'pipeline.log').open('w') as log:
        execution = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    summary = evidence / 'autopkgtest/summary'
    passed = (execution.returncode == 0 and summary.is_file() and
              re.fullmatch(r'reviewed-baseline\s+PASS', summary.read_text().strip()) is not None)
    result = {'schema': 1, 'scope': 'reviewed-ubuntu-baseline-preflight', 'node': node,
              'state': 'PASS' if passed else 'INFRA_INVALID', 'exit_code': execution.returncode,
              'source_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
              'workflow_run_id': os.environ.get('GITHUB_RUN_ID'), 'package_execution_started': False,
              'consumes_package_attempt': False, 'canonical_package_state_effect': 'none',
              'system_test_backend': 'autopkgtest-qemu', 'system_test_acceleration': 'kvm-required',
              'candidate_installed': False,
              'inputs_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [Path(__file__), ROOT / 'scripts/plasma-package-testing.py',
                                         ROOT / 'scripts/qemu-kvm-required.sh', baseline]},
              'files_sha256': {str(p.relative_to(evidence)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(evidence.rglob('*')) if p.is_file() and p.name != 'pipeline.log'}}
    (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'{node} reviewed Ubuntu baseline: {result["state"]}; package Attempts consumed=0')
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()

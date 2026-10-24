#!/usr/bin/env python3
"""Freeze the current package execution inputs without copying unrelated history."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def freeze(campaign, node, manifest_path, manifest_sha256):
    assert campaign['role'] in {'reviewed-plasma-package-build', 'reviewed-package-revalidation'}
    assert campaign['state'] == 'execution-authorized' and campaign['package_execution_authorized'] is True
    assert campaign['authorized_nodes'] == [node]
    record = campaign['nodes'][node]
    assert record['state'] == 'build-pending' and record['packaging_review'] == 'PASS'
    contract = {key: copy.deepcopy(campaign[key]) for key in
                ['schema', 'role', 'state', 'package_execution_authorized', 'authorized_nodes', 'runner_class', 'execution_checkpoint']}
    contract['execution_mode'] = campaign.get('execution_mode', 'build')
    contract['nodes'] = {node: {key: copy.deepcopy(value) for key, value in record.items() if key != 'attempts'}}
    contract['next_package_attempt'] = len(record['attempts']) + 1
    contract['campaign_manifest'] = manifest_path
    contract['campaign_manifest_sha256'] = manifest_sha256
    return contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('contract_prepare', ROOT/'scripts/prepare-plasma-package.py')
    prepare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prepare)
    campaign, _ = prepare.contract(args.node)
    path = os.environ.get('SUPRALINUX_PACKAGE_CAMPAIGN', 'manifests/kde-plasma-package-build.json')
    payload = (ROOT/path).read_bytes()
    contract = freeze(campaign, args.node, path, hashlib.sha256(payload).hexdigest())
    assert not args.output.exists(), 'Refusing to overwrite frozen execution inputs'
    args.output.write_text(json.dumps(contract, indent=2)+'\n')
    print(f'{args.node}: current execution contract frozen; unrelated campaign history stays in its own evidence')


if __name__ == '__main__':
    main()

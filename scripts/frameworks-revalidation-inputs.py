#!/usr/bin/env python3
"""Resolve reviewed Frameworks repairs while keeping historical DAG evidence intact."""
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def effective_nodes(dag, historical=False):
    nodes = copy.deepcopy(dag['nodes'])
    if historical:
        return nodes
    campaign = json.loads((ROOT/'manifests/package-revalidation.json').read_text())
    completed = {node: record for node, record in campaign['nodes'].items() if record['state'] == 'PASS'}
    if completed:
        spec = importlib.util.spec_from_file_location('repair_validation', ROOT/'scripts/validate_package_revalidation.py')
        validation = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validation)
        validation.validate()
    for node, record in campaign['nodes'].items():
        original = nodes[node]
        assert record['source_package'] == original['source_package']
        assert record['upstream_sha256'] == original['source_sha256']
        assert record['supersedes']['version'] == original['package_version']
        if record['state'] != 'PASS':
            # A known repair is a hold on new consumers of the superseded binary.
            original['downstream_eligible'] = False
            continue
        assert record['downstream_eligible'] is True
        original.update({'state': 'PASS', 'package_version': record['version'],
                         'downstream_eligible': True, 'binary_packages': list(record['binary_packages']),
                         'revalidated_binaries': record['binaries'], 'revalidation': record['evidence']})
    return nodes


def check_requested(node, requested, effective):
    assert effective['state'] == 'PASS' and effective.get('downstream_eligible') is not False, f'{node}: predecessor repair is not complete'
    assert effective['package_version'] == requested['version'], f'{node}: superseded or unreviewed predecessor version'
    assert effective['source_package'] == requested['source_package']
    assert requested['binaries'] and all(binary['package'] in effective['binary_packages'] for binary in requested['binaries'])
    if effective.get('revalidation'):
        binaries = {(binary['package'], binary['architecture']): binary for binary in effective['revalidated_binaries']}
        for binary in requested['binaries']:
            admitted = binaries[(binary['package'], binary['architecture'])]
            assert admitted['sha256'] == binary['sha256'], f'{node}: revalidated binary digest mismatch'

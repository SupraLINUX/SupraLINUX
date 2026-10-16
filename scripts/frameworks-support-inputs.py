#!/usr/bin/env python3
"""Verify retained support inputs without modifying the historical Frameworks DAG."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = 'manifests/frameworks-support-inputs.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(root, relative):
    path = root / relative
    assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
    assert path.resolve().is_relative_to(root.resolve()) and not path.is_symlink()
    return path


def verified_nodes(root=ROOT, registry=None):
    registry = registry or json.loads((root / REGISTRY).read_text())
    assert registry['schema'] == 1 and registry['role'] == 'retained-frameworks-support-build-inputs'
    nodes = {}
    for node, record in registry['nodes'].items():
        assert record['state'] == 'PASS' and record['downstream_eligible'] is True
        assert record['purpose'] and record['depends_on']
        link = record['evidence']
        path = local(root, link['path'])
        assert digest(path) == link['sha256'], 'Support evidence digest mismatch'
        proof = json.loads(path.read_text())
        assert proof['node'] == node and proof['state'] == 'PASS'
        assert proof['scope'] == 'retained-support-predecessor-input'
        assert proof['claim'] == 'hosted-clean-package-preflight' and proof['authoritative'] is False
        assert proof['canonical_package_state_effect'] == 'none'
        assert proof['offline_restore_verified'] is True and proof['requires_github_for_restore'] is False
        historical = local(root, proof['historical_manifest_path'])
        assert digest(historical) == proof['historical_manifest_sha256'], 'Historical support inputs changed'
        original = json.loads(historical.read_text())['nodes'][node]
        assert original['state'] == 'PASS' and original['downstream_eligible'] is True
        assert set(record['depends_on']) == {'extra-cmake-modules', *original['predecessors']}
        assert original['source_package'] == proof['source_package']
        assert original['package_version'] == proof['version']
        assert original['materialization']['orig_tar_sha256'] == proof['upstream_sha256']
        old = original['pass_evidence']
        for old_key, new_key in [('workflow_run', 'workflow_run_id'), ('job_id', 'workflow_job_id'),
                                 ('commit', 'source_commit'), ('artifact_id', 'artifact_id'),
                                 ('artifact_sha256', 'artifact_sha256')]:
            assert old[old_key] == proof[new_key], 'Original support evidence identity mismatch'
        for name, sha in proof['files_sha256'].items():
            assert Path(name).name == name and name != 'verification.json'
            assert digest(local(path.parent, name)) == sha, 'Retained support file changed'
        raw = json.loads((path.parent / 'result.json').read_text())
        assert raw['state'] == 'PASS' and raw['stage'] == 'complete' and raw['exit_code'] == 0
        assert raw['claim'] == proof['claim'] and raw['authoritative'] is False
        assert raw['node'] == node and raw['package_version'] == proof['version']
        assert raw['downstream_eligible'] is True and raw['package_attempted'] is True
        for key in ['tests', 'lintian', 'apt_check', 'consumer_smoke', 'payload_contract']:
            assert raw[key] == old[key], 'Original support result differs from closed evidence'
        meta = json.loads((path.parent / 'artifact-meta.json').read_text())
        job = json.loads((path.parent / 'workflow-job.json').read_text())
        assert meta['id'] == proof['artifact_id'] and meta['digest'] == 'sha256:' + proof['artifact_sha256']
        assert meta['workflow_run']['id'] == job['run_id'] == proof['workflow_run_id']
        assert meta['workflow_run']['head_sha'] == job['head_sha'] == proof['source_commit']
        assert job['id'] == proof['workflow_job_id'] and job['status'] == 'completed' and job['conclusion'] == 'success'
        assert any(step['name'] == 'Build and validate support node' and step['conclusion'] == 'success'
                   for step in job['steps'])
        url = meta['archive_download_url']
        assert re.fullmatch(r'https://api\.github\.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/[0-9]+/zip', url)
        assert int(url.split('/')[-2]) == proof['artifact_id']
        inspection = proof['inspection']
        assert inspection['artifact_sha256'] == proof['artifact_sha256']
        assert inspection['source_package'] == proof['source_package'] and inspection['package_version'] == proof['version']
        assert all(inspection[k] is True for k in ['source_payload_verified', 'buildinfo_verified', 'changes_payload_complete'])
        assert inspection['missing_debug_packages'] == []
        binaries = inspection['binaries']
        assert len({(b['package'], b['architecture']) for b in binaries}) == len(binaries)
        assert {b['package'] for b in binaries if not b['package'].endswith('-dbgsym')} == set(original['expected_binary_packages'])
        for binary in binaries:
            assert binary['version'] == proof['version'] and binary['architecture'] in {'amd64', 'all'}
            assert binary['size'] > 0 and raw['files'][binary['file']] == binary['sha256']
            assert old['files'][binary['file']] == binary['sha256']
        assert proof['archive_files_sha256']['result.json'] == proof['files_sha256']['result.json']
        assert all(proof['archive_files_sha256'][name] == sha for name, sha in raw['files'].items())
        nodes[node] = {'state': 'PASS', 'downstream_eligible': True, 'source_package': proof['source_package'],
                       'package_version': proof['version'], 'source_sha256': proof['upstream_sha256'],
                       'binary_packages': original['expected_binary_packages'], 'depends_on': record['depends_on'],
                       'retained_binaries': binaries, 'retained_support': link, 'authoritative': False}
    return nodes


def verify_archive(archive, proof):
    names = archive.namelist()
    assert len(names) == len(set(names)) and set(names) == set(proof['archive_files_sha256'])
    for name, sha in proof['archive_files_sha256'].items():
        assert Path(name).name == name
        assert hashlib.sha256(archive.read(name)).hexdigest() == sha, 'Original support archive member changed'


if __name__ == '__main__':
    result = verified_nodes()
    print(f'Retained Frameworks support input evidence: PASS; nodes={len(result)}; historical scope preserved')

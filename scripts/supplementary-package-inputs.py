#!/usr/bin/env python3
"""Restore exact authoritative supplementary providers as reviewed build inputs."""
import hashlib
import importlib.util
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(root, relative):
    path = root / relative
    assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
    assert path.resolve().is_relative_to(root.resolve()) and not path.is_symlink()
    return path


def checked_contract(node, requested, root=ROOT, historical=False, consumer=None):
    providers = json.loads((root/'manifests/kde-plasma-supplementary-providers.json').read_text())['nodes']
    assert node in providers, 'Unknown supplementary predecessor'
    provider = providers[node]
    assert provider['qt_provider_effect'] == 'none'
    if consumer is not None:
        assert consumer != node and consumer in provider['affected_nodes'], 'Unreviewed supplementary consumer'
    link = requested['evidence']
    result_path = local(root, link['result_path'])
    assert digest(result_path) == link['result_sha256'], 'Supplementary result changed'
    result = json.loads(result_path.read_text())
    assert result['state'] == 'PASS' and result['authoritative'] is True
    assert result['exit_code'] == 0 and result['package_attempt_consumed'] is True
    assert result['node'] == node and result['version'] == requested['version']
    assert result['system_test_acceleration'] == 'kvm-required'
    assert all(result[key] == 'PASS' for key in ['sbuild_result', 'lintian_result', 'autopkgtest_result'])
    contract_path = local(root, link['contract_path'])
    assert digest(contract_path) == result['files_sha256']['build-contract.json'] == link['contract_sha256']
    frozen = json.loads(contract_path.read_text())['nodes'][node]
    assert frozen['source_scope'] == 'plasma-supplementary-provider'
    assert frozen['source_package'] == requested['source_package'] == node
    assert frozen['version'] == requested['version'] and frozen['packaging_review'] == 'PASS'
    assert requested['cmake_package'] == provider['cmake_requirement']['module']
    assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]+', requested['cmake_package'])
    assert requested['upstream_version'] == frozen['upstream_version']
    assert re.fullmatch(r'[0-9]+(?:\.[0-9]+)+', requested['upstream_version'])
    campaign = json.loads((root/'manifests/kde-plasma-package-build.json').read_text())
    canonical = campaign['nodes'][node]
    if not historical:
        assert canonical['state'] == 'PASS' and canonical.get('downstream_eligible') is not False
        assert canonical['source_scope'] == 'plasma-supplementary-provider'
        assert provider['state'] == 'package-PASS' and provider['candidate_provider']['package_gate'] == 'PASS'
        assert canonical['version'] == requested['version'] and canonical['source_package'] == requested['source_package']
        evidence = canonical['evidence']
        for field in ['result_path', 'result_sha256', 'contract_path', 'artifact_id', 'artifact_sha256']:
            assert link[field] == evidence[field], f'Supplementary evidence identity mismatch: {field}'
        assert link['archive_root'] == evidence['local_retention']['archive_root']
        assert all(evidence['local_retention'][key] for key in ['source_complete', 'changes_complete', 'buildinfo_verified', 'offline_restore_verified'])
    metadata_path = result_path.parent/'artifact-meta.json'
    metadata = json.loads(metadata_path.read_text())
    assert metadata['id'] == link['artifact_id']
    assert metadata['digest'] == 'sha256:'+link['artifact_sha256']
    assert metadata['workflow_run']['head_sha'] == result['source_commit']
    assert str(metadata['workflow_run']['id']) == result['workflow_run_id']
    assert link['payload_prefix'] == 'packages/'
    assert requested['binaries'] and len({b['package'] for b in requested['binaries']}) == len(requested['binaries'])
    for binary in requested['binaries']:
        assert frozen['binary_packages'][binary['package']] == binary['architecture']
        file = f"{binary['package']}_{requested['version'].split(':')[-1]}_{binary['architecture']}.deb"
        assert Path(file).name == file
        assert result['files_sha256'][link['payload_prefix']+file] == binary['sha256'], 'Supplementary binary digest changed'
    return result, metadata


def verify_binary(path, node, requested, binary):
    assert path.is_file() and not path.is_symlink() and digest(path) == binary['sha256']
    actual = [subprocess.check_output(['dpkg-deb', '-f', str(path), field], text=True).strip()
              for field in ['Package', 'Source', 'Version', 'Architecture']]
    # Debian omits Source when its name/version equal the binary identity.
    source = actual[1] or actual[0]
    assert source == requested['source_package']
    assert [actual[0], actual[2], actual[3]] == [binary['package'], requested['version'], binary['architecture']], (node, actual)


def materialize(record, output, archive_root=ROOT, token=None, consumer=None):
    selected = []
    for node, requested in record.get('supplementary_predecessors', {}).items():
        result, metadata = checked_contract(node, requested, consumer=consumer)
        link = requested['evidence']
        directory = output/node
        assert not directory.exists(), 'Refusing to overwrite supplementary predecessor inputs'
        directory.mkdir(parents=True)
        archive_path = local(archive_root, link['archive_root'])/'sha256'/f"{link['artifact_sha256']}.zip"
        if not archive_path.is_file():
            assert token, 'Supplementary archive unavailable; artifact transport requires a read token'
            url = metadata['archive_download_url']
            assert url == f"https://api.github.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/{link['artifact_id']}/zip"
            archive_path = directory/f"{link['artifact_sha256']}.zip"
            with archive_path.open('wb') as stream:
                subprocess.run([str(ROOT/'scripts/github-read-with-retry.sh'), '-H', f'Authorization: Bearer {token}',
                                '-H', 'Accept: application/vnd.github+json', url], stdout=stream, check=True)
        assert not archive_path.is_symlink() and digest(archive_path) == link['artifact_sha256'], 'Supplementary archive digest changed'
        spec = importlib.util.spec_from_file_location('supplementary_retention', ROOT/'scripts/retain-package-artifacts.py')
        retention = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(retention)
        inspection = retention.inspect(archive_path, {'node':node, 'package_version':requested['version'],
                                       'artifact_sha256':link['artifact_sha256'], 'payload_prefix':link['payload_prefix']}, requested['source_package'])
        assert all(inspection[key] for key in ['source_payload_verified', 'buildinfo_verified', 'changes_payload_complete'])
        assert not inspection['missing_debug_packages']
        with zipfile.ZipFile(archive_path) as archive:
            assert hashlib.sha256(archive.read('result.json')).hexdigest() == link['result_sha256']
            for name, expected in result['files_sha256'].items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
            for binary in requested['binaries']:
                file = f"{binary['package']}_{requested['version'].split(':')[-1]}_{binary['architecture']}.deb"
                target = directory/file
                target.write_bytes(archive.read(link['payload_prefix']+file))
                verify_binary(target, node, requested, binary)
                selected.append({'node':node, 'source_package':requested['source_package'], 'version':requested['version'],
                                 'path':str(target), **binary, 'supplementary_evidence':link,
                                 'artifact_sha256':link['artifact_sha256'], 'cmake_package':requested['cmake_package'],
                                 'upstream_version':requested['upstream_version']})
    return selected

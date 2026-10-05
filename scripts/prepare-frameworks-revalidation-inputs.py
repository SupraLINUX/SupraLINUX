#!/usr/bin/env python3
"""Restore exact PASS repair binaries from retained or Actions artifact archives."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/file)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


effective = module('effective_frameworks', 'frameworks-revalidation-inputs.py')
retention = module('repair_retention', 'retain-package-artifacts.py')
support = module('support_retention', 'frameworks-support-inputs.py')


def materialize(record, output, archive_root=ROOT, token=None):
    nodes = effective.effective_nodes(json.loads((ROOT/'manifests/kde-dag.json').read_text()))
    restored = []
    for node, requested in record['frameworks_predecessors'].items():
        current = nodes[node]
        effective.check_requested(node, requested, current)
        evidence_key = 'revalidation' if current.get('revalidation') else 'retained_support'
        if not current.get(evidence_key):
            continue
        link = current[evidence_key]
        proof_path = ROOT/link['path']
        assert hashlib.sha256(proof_path.read_bytes()).hexdigest() == link['sha256']
        proof = json.loads(proof_path.read_text())
        directory = output/node
        assert not directory.exists(), 'Refusing to overwrite repaired predecessor input evidence'
        directory.mkdir(parents=True)
        archive_path = archive_root/proof['archive_path']
        if not archive_path.is_file():
            assert token, 'Retained repair archive unavailable; artifact transport requires a read token'
            metadata = json.loads((proof_path.parent/'artifact-meta.json').read_text())
            url = metadata['archive_download_url']
            assert re.fullmatch(r'https://api\.github\.com/repos/SupraLINUX/SupraLINUX/actions/artifacts/[0-9]+/zip', url)
            assert int(url.split('/')[-2]) == proof['artifact_id']
            archive_path = directory/f"{proof['artifact_sha256']}.zip"
            with archive_path.open('wb') as stream:
                subprocess.run([str(ROOT/'scripts/github-read-with-retry.sh'), '-H', f'Authorization: Bearer {token}',
                                '-H', 'Accept: application/vnd.github+json', url], stdout=stream, check=True)
        prefix = proof.get('payload_prefix', 'packages/')
        inspection = retention.inspect(archive_path, {'node': node, 'package_version': current['package_version'],
                                        'artifact_sha256': proof['artifact_sha256'], 'payload_prefix': prefix}, current['source_package'])
        assert inspection['source_payload_verified'] and inspection['buildinfo_verified'] and inspection['changes_payload_complete']
        assert not inspection['missing_debug_packages']
        admitted_binaries = current.get('revalidated_binaries', current.get('retained_binaries'))
        binaries = {(binary['package'], binary['architecture']): binary for binary in admitted_binaries}
        with zipfile.ZipFile(archive_path) as archive:
            raw = json.loads(archive.read('result.json'))
            assert raw['state'] == 'PASS'
            if evidence_key == 'retained_support':
                support.verify_archive(archive, proof)
                assert raw['claim'] == 'hosted-clean-package-preflight' and raw['authoritative'] is False
            else:
                assert raw['source_commit'] == proof['source_commit']
                for name, digest in raw['files_sha256'].items():
                    assert hashlib.sha256(archive.read(name)).hexdigest() == digest
            for binary in requested['binaries']:
                admitted = binaries[(binary['package'], binary['architecture'])]
                assert admitted['version'] == current['package_version'] and admitted['sha256'] == binary['sha256']
                name = admitted['file']
                assert Path(name).name == name and name.endswith('.deb')
                data = archive.read(prefix+name)
                assert len(data) == admitted['size'] and hashlib.sha256(data).hexdigest() == binary['sha256']
                target = directory/name
                target.write_bytes(data)
                restored.append({'node': node, 'source_package': current['source_package'],
                                 'version': current['package_version'], 'path': str(target), **binary,
                                 evidence_key: link, 'artifact_sha256': proof['artifact_sha256']})
    return restored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive-root', type=Path, default=ROOT)
    args = parser.parse_args()
    prepare = module('repair_prepare', 'prepare-plasma-package.py')
    _, record = prepare.contract(args.node)
    restored = materialize(record, args.output, args.archive_root, os.environ.get('GITHUB_TOKEN'))
    print(json.dumps({'state': 'PASS', 'cache_only': True, 'selected': restored}, indent=2))


if __name__ == '__main__':
    main()

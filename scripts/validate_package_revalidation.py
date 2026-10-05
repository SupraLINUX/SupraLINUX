#!/usr/bin/env python3
"""Validate a scoped predecessor repair without rewriting historical campaigns."""
import hashlib
import importlib.machinery
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prepare = importlib.machinery.SourceFileLoader('prepare', str(ROOT/'scripts/prepare-plasma-package.py')).load_module()


def validate():
    previous = os.environ.get('SUPRALINUX_PACKAGE_CAMPAIGN')
    os.environ['SUPRALINUX_PACKAGE_CAMPAIGN'] = 'manifests/package-revalidation.json'
    try:
        campaign = prepare.load_campaign()
        assert campaign['role'] == 'reviewed-package-revalidation'
        assert campaign['execution_mode'] in {'preflight', 'build', 'complete'}
        assert len(campaign['authorized_nodes']) <= 1
        assert campaign['package_execution_authorized'] is bool(campaign['authorized_nodes'])
        for incident in campaign.get('infrastructure_incidents', []):
            raw = (ROOT/incident['path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==incident['sha256']
            proof=json.loads(raw)
            assert proof['state']=='INFRA_INVALID' and proof['package_attempt_consumed'] is False
            assert incident['cause'] and incident['repair']
            directory=(ROOT/incident['path']).parent
            for name,digest in proof['files_sha256'].items():
                assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest
            result=json.loads((ROOT/proof['result_path']).read_text())
            assert result['state']=='INFRA_INVALID' and result['package_attempt_consumed'] is False
            assert result['source_commit']==proof['source_commit']
        for node, record in campaign['nodes'].items():
            prepare.contract(node)
            assert record['review'] and all(record['review'].values())
            assert record['upstream_tests'] and len(set(record['upstream_tests'])) == len(record['upstream_tests'])
            assert record['baseline_preflight_required'] and record['symbols_baselines']
            packaging = ROOT/record['packaging_path']
            for file in record['required_executable_files'] + ['tests/retained-upgrade']:
                assert (packaging/file).stat().st_mode & 0o111
            version = subprocess.check_output(['dpkg-parsechangelog','-l',str(packaging/'changelog'),'-S','Version'],text=True).strip()
            assert version == record['version']
            for reference in record['symbols_baselines'].values():
                assert hashlib.sha256((ROOT/reference['path']).read_bytes()).hexdigest() == reference['sha256']
            for proof in campaign['certifications']:
                raw = (ROOT/proof['path']).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == proof['sha256']
                certification = json.loads(raw)
                assert certification['state'] == 'PASS' and certification['package_attempt_consumed'] is False
                assert certification['scope'] == 'reviewed-package-revalidation-preflight'
                assert certification['node'] == node
                assert certification['packaging_sha256']==record['packaging_sha256']
                for file, digest in certification['inputs_sha256'].items():
                    assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest() == digest
            if campaign['execution_mode'] == 'build':
                assert campaign['certifications'], 'Certify the new input route before the package Attempt'
            if node == 'kconfig':
                assert 'libexec/kf6/kconf_update' in (packaging/'libkf6config-bin.install').read_text()
                assert 'kconf_update' not in (packaging/'libkf6configcore6.install').read_text()
                assert f'Breaks: libkf6configcore6 (<< {version})' in (packaging/'control').read_text()
                assert f'Replaces: libkf6configcore6 (<< {version})' in (packaging/'control').read_text()
                assert len(record['binary_packages']) == len(record['retained_upgrade']['binaries']) == 9
    finally:
        if previous is None:
            os.environ.pop('SUPRALINUX_PACKAGE_CAMPAIGN', None)
        else:
            os.environ['SUPRALINUX_PACKAGE_CAMPAIGN'] = previous
    print('Scoped authoritative package revalidation contract: PASS')


if __name__ == '__main__':
    validate()

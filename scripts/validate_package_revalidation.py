#!/usr/bin/env python3
"""Validate a scoped predecessor repair without rewriting historical campaigns."""
import hashlib
import datetime
import importlib.machinery
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prepare = importlib.machinery.SourceFileLoader('prepare', str(ROOT/'scripts/prepare-plasma-package.py')).load_module()


def verify_preflight_transport(link, result, job, artifact, host, proof):
    """Preserve an original result while refusing admission after lost transport."""
    assert job['status'] == 'completed'
    cancelled = artifact.get('kind') == 'sealed-host-preflight-cancelled-result-export'
    infra_export = artifact.get('kind') == 'sealed-host-preflight-infra-result-export'
    failed = cancelled or infra_export or artifact.get('kind') == 'sealed-host-preflight-result-export'
    assert job['conclusion'] == ('cancelled' if cancelled else ('failure' if failed else ('success' if result['state'] == 'PASS' else 'failure')))
    if not failed:
        assert (host['exit_code'] == 0) is (result['state'] == 'PASS')
        return
    assert host['exit_code'] != 0 and result['package_attempt_consumed'] is False
    if infra_export:
        assert result['state'] == 'INFRA_INVALID'
        assert all(result[key] == 'not-run' for key in ['sbuild_result', 'lintian_result', 'autopkgtest_result'])
    else:
        assert result['state'] == 'PASS' and result['stage'] == 'reviewed-package-preflight-complete'
    assert proof['infrastructure_transport_result'] == 'FAIL'
    assert proof['original_runner_result_preserved'] is True and proof['current_input_admission'] is False
    assert link.get('applicable') is False and link.get('inapplicability_reason'), 'Recovered transport failure cannot admit current package execution'
    assert artifact['id'] is None
    steps = {step['name']: step for step in job['steps']}
    execution = steps['Run current reviewed package']
    if cancelled:
        assert execution['conclusion'] == 'cancelled'
        assert result['exit_code'] == 0
        timestamps = [datetime.datetime.fromisoformat(value) for value in
                      [execution['started_at'], execution['completed_at'], result['finished_at'], host['finished_at']]]
        assert all(value.tzinfo is not None for value in timestamps)
        assert timestamps == sorted(timestamps), 'Recovered original PASS must finish after cancellation and before host cleanup'
    else:
        assert execution['conclusion'] == ('failure' if infra_export else 'success')
    assert steps['Retain package sources, binaries and evidence']['conclusion'] != 'success'


def verified_evidence(link):
    path = ROOT/link['path']
    assert path.resolve().is_relative_to((ROOT/'manifests/evidence/package-revalidation').resolve())
    payload = path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == link['sha256']
    proof = json.loads(payload)
    directory = path.parent
    for name, digest in proof['files_sha256'].items():
        file = directory/name
        assert file.resolve().is_relative_to(directory.resolve())
        assert hashlib.sha256(file.read_bytes()).hexdigest() == digest
    result_path = ROOT/proof['result_path']
    assert result_path == directory/'result.json'
    assert hashlib.sha256(result_path.read_bytes()).hexdigest() == proof['result_sha256']
    result = json.loads(result_path.read_text())
    assert result['state'] == proof['state']
    assert result['node'] == proof['node'] and result['version'] == proof['version']
    assert result['source_commit'] == proof['source_commit']
    assert result['workflow_run_id'] == str(proof['workflow_run_id'])
    assert result['authoritative'] is True and result['system_test_acceleration'] == 'kvm-required'
    assert result['package_attempt_consumed'] is proof['package_attempt_consumed']
    job = json.loads((directory/'workflow-job.json').read_text())
    artifact = json.loads((directory/'artifact-meta.json').read_text())
    host = json.loads((directory/'host-result.json').read_text())
    verify_preflight_transport(link, result, job, artifact, host, proof)
    assert job['head_sha'] == artifact['workflow_run']['head_sha'] == proof['source_commit']
    assert job['id'] == proof['workflow_job_id'] and job['run_id'] == artifact['workflow_run']['id'] == proof['workflow_run_id']
    assert host['workflow_run_id'] == result['workflow_run_id']
    assert proof['host_evidence_manifest_sha256'] == proof['files_sha256']['host-evidence-sha256.txt']
    assert artifact['id'] == proof['artifact_id']
    assert artifact['digest'] == 'sha256:' + proof['artifact_sha256']
    if artifact.get('kind') == 'sealed-host-preflight-export':
        assert artifact['id'] is None and result['state'] == 'INFRA_INVALID'
        assert result['kind'] == 'sealed-host-preflight-interruption-observation'
        assert result['runner_result_present'] is result['package_attempt_consumed'] is False
        assert result['host_result_sha256'] == proof['files_sha256']['host-result.json']
        assert result['host_evidence_manifest_sha256'] == proof['host_evidence_manifest_sha256']
        assert not proof['inspection']['source_complete'] and not proof['inspection']['candidate_binaries_built']
        diagnosis = json.loads((directory/'infra-interruption.json').read_text())
        assert diagnosis['package_attempt_consumed'] is diagnosis['candidate_installed'] is False
    assert proof['offline_restore_verified'] is True and proof['requires_github_for_restore'] is False
    contract_path = ROOT/proof['contract_path']
    assert contract_path == directory/'build-contract.json'
    assert proof['files_sha256']['build-contract.json'] == result['files_sha256']['build-contract.json']
    frozen = json.loads(contract_path.read_text())
    assert frozen['nodes'][proof['node']]['version'] == proof['version']
    for name, digest in proof['files_sha256'].items():
        if name in result['files_sha256']:
            assert digest == result['files_sha256'][name]
    if result['state'] == 'PASS':
        baseline = json.loads((directory/'ubuntu-baseline-preflight/result.json').read_text())
        assert baseline['state'] == 'PASS' and baseline['exit_code'] == 0
        assert baseline['candidate_installed'] is baseline['consumes_package_attempt'] is baseline['package_execution_started'] is False
        assert baseline['node'] == proof['node'] and baseline['source_commit'] == proof['source_commit']
        assert baseline['workflow_run_id'] == result['workflow_run_id']
        assert json.loads((directory/'cache-probe/result.json').read_text())['state'] == 'PASS'
        assert json.loads((directory/'rootfs-admission.json').read_text())['frameworks_and_qt_sdk_preinstalled'] is False
        if frozen['nodes'][proof['node']].get('retained_upgrade'):
            assert json.loads((directory/'retained-upgrade-inputs.json').read_text())['eligible_as_build_predecessors'] is False
    return proof, result, frozen, directory


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
            proof, result, _, _ = verified_evidence(incident)
            assert proof['state']=='INFRA_INVALID' and proof['package_attempt_consumed'] is False
            assert incident['cause'] and incident['repair']
            assert result['state']=='INFRA_INVALID' and result['package_attempt_consumed'] is False
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
            for link in campaign['certifications']:
                certification, result, frozen, _ = verified_evidence(link)
                assert certification['state'] == 'PASS' and certification['package_attempt_consumed'] is False
                assert certification['scope'] == 'reviewed-package-revalidation-preflight'
                assert certification['node'] == node
                assert certification['packaging_sha256']==record['packaging_sha256']
                assert frozen['execution_mode'] == 'preflight' and result['stage'] == 'reviewed-package-preflight-complete'
                assert all(result[key] == 'not-run' for key in ['sbuild_result', 'lintian_result', 'autopkgtest_result'])
                if campaign['execution_mode'] != 'complete':
                    for file, digest in certification['inputs_sha256'].items():
                        assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest() == digest
            if campaign['execution_mode'] == 'build':
                assert campaign['certifications'], 'Certify the new input route before the package Attempt'
            for number, attempt in enumerate(record['attempts'], 1):
                proof, result, frozen, directory = verified_evidence(attempt)
                assert attempt['attempt'] == number and attempt['state'] == proof['state']
                assert proof['scope'] == 'authoritative-package-revalidation' and proof['package_attempt_consumed'] is True
                assert proof['node'] == node and frozen['execution_mode'] == 'build'
                if proof['state'] == 'PASS':
                    assert record['state'] == 'PASS' and record['evidence'] == {key: attempt[key] for key in ['path', 'sha256']}
                    assert proof['version'] == record['version']
                    built = frozen['nodes'][node]
                    for key in ['packaging_sha256', 'symbols_baselines', 'frameworks_predecessors', 'retained_upgrade', 'upstream_sha256', 'signature_sha256']:
                        assert built[key] == record[key]
                    assert all(result[key] == 'PASS' for key in ['sbuild_result', 'lintian_result', 'autopkgtest_result'])
                    inspection = proof['inspection']
                    assert inspection['source_payload_verified'] and inspection['buildinfo_verified'] and inspection['changes_payload_complete']
                    assert not inspection['missing_debug_packages']
                    binaries = [binary for binary in inspection['binaries'] if not binary['package'].endswith('-dbgsym')]
                    assert binaries == record['binaries']
                    assert {binary['package']: binary['architecture'] for binary in binaries} == record['binary_packages']
                    assert all(binary['version'] == record['version'] and len(binary['sha256']) == 64 for binary in binaries)
                    upstream = json.loads((directory/'upstream-tests.json').read_text())
                    assert upstream['state'] == 'PASS' and upstream['expected_tests'] == record['upstream_tests']
                    assert (directory/'autopkgtest/summary').read_text().split() == ['ubuntu-abi-client', 'PASS', 'consumer', 'PASS']
                    assert (directory/'retained-upgrade/summary').read_text().split() == ['retained-upgrade', 'PASS']
            if record['state'] == 'PASS':
                assert record['attempts'] and record['attempts'][-1]['state'] == 'PASS'
                assert record['downstream_eligible'] is True
                assert campaign['state'] == 'PASS' and campaign['execution_mode'] == 'complete'
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

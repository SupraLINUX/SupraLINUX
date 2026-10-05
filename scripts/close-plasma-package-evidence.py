#!/usr/bin/env python3
"""Admit a package PASS only after identity, tests, host seal and offline retention."""
import argparse
import hashlib
import importlib.machinery
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('node')
    p.add_argument('--zip', type=Path, required=True)
    p.add_argument('--artifact-meta', type=Path)
    p.add_argument('--host-export', action='store_true', help='export the complete sealed guest after an Actions transport interruption')
    p.add_argument('--workflow-job-meta',type=Path,help='original GitHub job metadata retrieved through the connector')
    p.add_argument('--host-dir', type=Path, required=True)
    p.add_argument('--job-id', type=int, required=True)
    p.add_argument('--recover-hidden-files', action='store_true',
                   help='retain hidden files omitted by Actions from the independently sealed host copy')
    a = p.parse_args()
    campaign_path = ROOT/'manifests/kde-plasma-package-build.json'
    campaign = json.loads(campaign_path.read_text())
    record = campaign['nodes'][a.node]
    assert campaign['authorized_nodes'] == [a.node] and record['state'] == 'build-pending'
    source_commit = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'], text=True).strip()
    host = json.loads((a.host_dir/'host-result.json').read_text())
    check = subprocess.run(['sha256sum','--check','--quiet','evidence-sha256.txt'], cwd=a.host_dir, capture_output=True, text=True)
    assert check.returncode == 0, check.stderr
    job_bytes = host_bytes = None
    if a.host_export:
        assert host['exit_code'] != 0 and a.workflow_job_meta and not a.artifact_meta
        assert not a.zip.exists(), 'Refusing to replace an export'
        job_bytes = a.workflow_job_meta.read_bytes()
        job = json.loads(job_bytes)
        assert job['id'] == a.job_id and str(job['run_id']) == host['workflow_run_id']
        assert job['head_sha'] == source_commit and job['status'] == 'completed'
        steps = {step['name']:step for step in job['steps']}
        assert steps['Run current reviewed package']['conclusion'] == 'success'
        assert steps['Retain package sources, binaries and evidence']['conclusion'] != 'success'
        payload_dir = a.host_dir/'guest-files/workspace/evidence/authoritative-plasma-package'
        original = json.loads((payload_dir/'result.json').read_text())
        assert original['state'] == 'PASS' and original['exit_code'] == 0
        assert original['source_commit'] == source_commit and original['workflow_run_id'] == host['workflow_run_id']
        for name,digest in original['files_sha256'].items():
            path = payload_dir/name
            assert path.resolve().is_relative_to(payload_dir.resolve()) and sha(path) == digest,name
        a.zip.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(a.zip,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(payload_dir.rglob('*')):
                if path.is_file():archive.write(path,str(path.relative_to(payload_dir)))
        artifact_sha = sha(a.zip)
        meta = {'id':None,'digest':'sha256:'+artifact_sha,'kind':'sealed-host-package-export',
                'workflow_run':{'id':job['run_id'],'head_sha':source_commit}}
        host_bytes = (a.host_dir/'host-result.json').read_bytes()
    else:
        assert host['exit_code'] == 0 and a.artifact_meta
        meta = json.loads(a.artifact_meta.read_text())
        artifact_sha = meta['digest'].removeprefix('sha256:')
        assert sha(a.zip) == artifact_sha
    with zipfile.ZipFile(a.zip) as archive:
        result_bytes = archive.read('result.json')
        result = json.loads(result_bytes)
        assert result['state'] == 'PASS' and result['source_commit'] == source_commit
        assert result['node'] == a.node and result['version'] == record['version']
        assert result['workflow_run_id'] == host['workflow_run_id']
        assert meta['workflow_run']['head_sha'] == source_commit
        assert meta['workflow_run']['id'] == int(result['workflow_run_id'])
        assert result['authoritative'] is True and result['package_attempt_consumed'] is True
        assert all(result[k] == 'PASS' for k in ['sbuild_result','lintian_result','autopkgtest_result'])
        exporter = importlib.machinery.SourceFileLoader('exporter', str(ROOT/'scripts/plasma-evidence-export.py')).load_module()
        recovered = exporter.verify_export(archive, result, a.host_dir if a.recover_hidden_files else None)
        upstream_bytes = None
        if record.get('upstream_tests'):
            upstream_bytes = archive.read('upstream-tests.json')
            upstream = json.loads(upstream_bytes)
            assert upstream['state'] == 'PASS' and upstream['expected_tests'] == record['upstream_tests']
        contract_bytes = archive.read('build-contract.json')
        frozen = json.loads(contract_bytes)
        if 'campaign_manifest_sha256' in frozen:
            assert frozen['campaign_manifest'] == 'manifests/kde-plasma-package-build.json'
            assert frozen['campaign_manifest_sha256'] == hashlib.sha256(subprocess.check_output(['git','show',f'{source_commit}:manifests/kde-plasma-package-build.json'])).hexdigest()
            assert frozen['next_package_attempt'] == len(record['attempts'])+1
        built = frozen['nodes'][a.node]
        assert built['packaging_sha256'] == record['packaging_sha256'] and built['upstream_sha256'] == record['upstream_sha256']
        assert built.get('frameworks_predecessors', {}) == record.get('frameworks_predecessors', {})
        assert built['signature_sha256'] == record['signature_sha256']
        baseline_bytes = None
        if record.get('baseline_preflight_required'):
            baseline_bytes = archive.read('ubuntu-baseline-preflight/result.json')
            baseline = json.loads(baseline_bytes)
            assert baseline['state'] == 'PASS' and baseline['exit_code'] == 0
            assert baseline['node'] == a.node and baseline['source_commit'] == source_commit
            assert baseline['workflow_run_id'] == result['workflow_run_id']
            assert baseline['system_test_acceleration'] == 'kvm-required' and baseline['candidate_installed'] is False
            assert baseline['consumes_package_attempt'] is baseline['package_execution_started'] is False
            script = record['packaging_path'] + '/' + record['baseline_setup_script']
            assert baseline['inputs_sha256'][script] == record['packaging_sha256'][record['baseline_setup_script']]
            for name, digest in baseline['files_sha256'].items():
                assert result['files_sha256']['ubuntu-baseline-preflight/' + name] == digest
        tests = []
        for line in (ROOT/record['packaging_path']/'tests/control').read_text().splitlines():
            if line.startswith('Tests:'):
                tests.extend(line.split(':',1)[1].replace(',',' ').split())
        assert tests
        summary_bytes = archive.read('autopkgtest/summary')
        summary = summary_bytes.decode()
        assert all(re.search(r'^'+re.escape(test)+r'\s+PASS\s*$', summary, re.M) for test in tests), summary
        if record.get('frameworks_predecessors'):
            probe_bytes = archive.read('cache-probe/result.json')
            probe = json.loads(probe_bytes)
            assert probe['state'] == 'PASS' and probe['consumes_package_attempt'] is False
            assert 'Frameworks retained build input probe: PASS' in archive.read('pipeline.log').decode()
        else:
            probe_bytes = None
        rootfs_bytes = None
        if record.get('sbuild_rootfs_policy',{}).get('kind') == 'immutable-bare-milestone':
            rootfs_bytes = archive.read('rootfs-admission.json')
            rootfs = json.loads(rootfs_bytes)
            assert rootfs['state'] == 'PASS' and rootfs['base_sha256'] == record['sbuild_rootfs_policy']['sha256']
            assert rootfs['frameworks_and_qt_sdk_preinstalled'] is False and rootfs['package_attempt_consumed'] is False
            assert rootfs['requires_sbuild_apt_update_and_distupgrade'] is True
            assert rootfs['suites'] == record['sbuild_rootfs_policy']['suites']
    number = len(record['attempts']) + 1
    relative = Path(f'manifests/evidence/plasma/{a.node}-attempt{number}')
    historical = ROOT/relative
    assert not historical.exists(), 'Refusing to rewrite closed evidence'
    plan_path = ROOT/f'manifests/evidence/plasma/{a.node}-artifact-plan.json'
    plan = {'schema':1, 'items':[{'node':a.node, 'package_version':record['version'], 'artifact_id':meta['id'],
                                'workflow_run_id':int(result['workflow_run_id']), 'artifact_sha256':artifact_sha,
                                'payload_prefix':'packages/'}]}
    with tempfile.TemporaryDirectory(dir=ROOT/'.work', prefix='package-retention-') as temp:
        temp = Path(temp)
        tmp_plan = temp/'plan.json'
        write(tmp_plan, plan)
        cache = temp/'cache'
        cache.mkdir()
        shutil.copyfile(a.zip, cache/f"{meta['id']}.zip")
        archive_root = ROOT/f".artifacts/plasma-{record['upstream_version']}/{a.node}-attempt{number}"
        retention = importlib.machinery.SourceFileLoader('retention',str(ROOT/'scripts/retain-package-artifacts.py')).load_module()
        index = retention.retain(tmp_plan, campaign_path, cache, archive_root)
        assert index['result'] == 'PASS' and index['source_complete_artifact_count'] == 1
        assert all(item['changes_payload_complete'] and item['buildinfo_verified'] for item in index['items'])
        restored = temp/'empty-cache'
        retention.retain(tmp_plan, campaign_path, restored, archive_root, restore_cache=True)
        assert sha(restored/f"{meta['id']}.zip") == artifact_sha
    historical.mkdir(parents=True)
    (historical/'result.json').write_bytes(result_bytes)
    (historical/'build-contract.json').write_bytes(contract_bytes)
    (historical/'summary').write_bytes(summary_bytes)
    if probe_bytes is not None:
        (historical/'cache-probe-result.json').write_bytes(probe_bytes)
    if upstream_bytes is not None:
        (historical/'upstream-tests.json').write_bytes(upstream_bytes)
    if rootfs_bytes is not None:
        (historical/'rootfs-admission.json').write_bytes(rootfs_bytes)
    if baseline_bytes is not None:
        (historical/'ubuntu-baseline-preflight.json').write_bytes(baseline_bytes)
    if job_bytes is not None:
        (historical/'workflow-job.json').write_bytes(job_bytes)
        (historical/'host-result.json').write_bytes(host_bytes)
    recovery = None
    if recovered:
        supplement = archive_root/'sealed-host-hidden-files.zip'
        assert not supplement.exists(), 'Refusing to replace retained recovery bytes'
        with zipfile.ZipFile(supplement, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(recovered.items()):
                archive.writestr(name, data)
        with tempfile.TemporaryDirectory(dir=ROOT/'.work', prefix='evidence-offline-restore-') as temp:
            restored = Path(temp)/supplement.name
            shutil.copyfile(supplement, restored)
            assert sha(restored) == sha(supplement)
            with zipfile.ZipFile(restored) as archive:
                assert set(archive.namelist()) == set(recovered)
                assert all(hashlib.sha256(archive.read(name)).hexdigest() == result['files_sha256'][name] for name in recovered)
        proof = {'kind':'sealed-host-hidden-file-export-recovery', 'actions_artifact_id':meta['id'],
                 'actions_artifact_sha256':artifact_sha, 'host_evidence_manifest_sha256':sha(a.host_dir/'evidence-sha256.txt'),
                 'files_sha256':{name:result['files_sha256'][name] for name in sorted(recovered)},
                 'supplement_path':str(supplement.relative_to(ROOT)), 'supplement_sha256':sha(supplement),
                 'offline_restore_verified':True, 'original_actions_archive_unchanged':True}
        write(historical/'export-recovery.json', proof)
        recovery = {'proof_path':str(relative/'export-recovery.json'), 'proof_sha256':sha(historical/'export-recovery.json')}
    write(plan_path, plan)
    binaries = index['items'][0]['binaries']
    evidence = {'workflow_run_id':int(result['workflow_run_id']), 'workflow_job_id':a.job_id,
                'source_commit':source_commit, 'artifact_id':meta['id'], 'artifact_sha256':artifact_sha,
                'result_path':str(relative/'result.json'), 'result_sha256':sha(historical/'result.json'),
                'contract_path':str(relative/'build-contract.json'), 'host_evidence_dir':str(a.host_dir),
                'host_evidence_manifest_sha256':sha(a.host_dir/'evidence-sha256.txt'),
                'local_retention':{'archive_root':str(archive_root.relative_to(ROOT)),
                                   'archive_index_sha256':sha(archive_root/'index.json'),
                                   'plan_path':str(plan_path.relative_to(ROOT)), 'plan_sha256':sha(plan_path),
                                   'source_complete':True, 'changes_complete':True, 'buildinfo_verified':True,
                                   'artifact_zip_sha256_verified':True, 'offline_restore_verified':True,
                                   'requires_github_for_restore':False, 'off_host_backup_verified':False,
                                   'unique_binary_package_count':len({(b['package'], b['version'], b['architecture']) for b in binaries}),
                                   'binary_payload_file_count':len(binaries), 'payload_prefix':'packages/'}}
    if probe_bytes is not None:
        evidence['cache_probe_result_path'] = str(relative/'cache-probe-result.json')
        evidence['cache_probe_result_sha256'] = sha(historical/'cache-probe-result.json')
    if upstream_bytes is not None:
        evidence['upstream_tests_path'] = str(relative/'upstream-tests.json')
        evidence['upstream_tests_sha256'] = sha(historical/'upstream-tests.json')
    if recovery is not None:
        evidence['hidden_file_export_recovery'] = recovery
    if rootfs_bytes is not None:
        evidence['rootfs_admission_path'] = str(relative/'rootfs-admission.json')
        evidence['rootfs_admission_sha256'] = sha(historical/'rootfs-admission.json')
    if baseline_bytes is not None:
        evidence['baseline_preflight_path'] = str(relative/'ubuntu-baseline-preflight.json')
        evidence['baseline_preflight_sha256'] = sha(historical/'ubuntu-baseline-preflight.json')
    if a.host_export:
        evidence.update(artifact_origin='sealed-host-package-export',actions_export_complete=False,
                        workflow_job_path=str(relative/'workflow-job.json'),workflow_job_sha256=sha(historical/'workflow-job.json'),
                        host_result_path=str(relative/'host-result.json'),host_result_sha256=sha(historical/'host-result.json'))
    record.update(state='PASS', evidence=evidence)
    record['attempts'].append({'attempt':number, 'state':'PASS', 'sbuild_result':'PASS', 'lintian_result':'PASS',
                              'autopkgtest_result':'PASS', 'package_attempt_consumed':True,
                              **{k:v for k,v in evidence.items() if k not in ['contract_path','local_retention','cache_probe_result_path','cache_probe_result_sha256','upstream_tests_path','upstream_tests_sha256']}})
    campaign.update(state='partial-PASS', authorized_nodes=[], package_execution_authorized=False)
    campaign['retained_attempt_archives'].append({'node':a.node,'attempt':number,
                                                'archive_root':evidence['local_retention']['archive_root'],
                                                'archive_index_sha256':evidence['local_retention']['archive_index_sha256']})
    write(campaign_path, campaign)
    path = ROOT/'manifests/kde-plasma.json'
    planning = json.loads(path.read_text())
    planning['planning'].update(status='level0-package-build-complete', next_gate='plasma-level0-remaining-packaging-preparation',
                                package_execution_authorized=False, authorized_package_nodes=[])
    write(path, planning)
    path = ROOT/'manifests/kde-plasma-level0.json'
    level = json.loads(path.read_text())
    level.update(state='package-build-partial-PASS',next_gate=planning['planning']['next_gate'],
                 package_execution_authorized=False,authorized_package_nodes=[])
    level['scheduling'].update(package_execution_locked=True,scope='Remaining nodes require individual packaging review and explicit admission')
    level['nodes'][a.node].update(state='PASS', package_execution_authorized=False)
    write(path, level)
    print(f"{a.node} package evidence closure: PASS; Attempt {number}; offline artifact restoration verified")

if __name__ == '__main__':
    main()

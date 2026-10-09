#!/usr/bin/env python3
"""Retain an original scoped revalidation or preflight with verified identities."""
import argparse
import hashlib
import importlib.machinery
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
retention = importlib.machinery.SourceFileLoader('retention', str(ROOT/'scripts/retain-package-artifacts.py')).load_module()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path, payload):
    path.write_text(json.dumps(payload,indent=2)+'\n')


def interrupted_preflight(payload, baseline, host, job, head, node, version):
    """Describe a sealed interruption, explicitly without an original runner result."""
    assert not (payload/'result.json').exists(), 'Use the original runner result when available'
    assert host['exit_code'] != 0 and job['status'] == 'completed' and job['conclusion'] == 'failure'
    assert job['head_sha'] == head and str(job['run_id']) == host['workflow_run_id']
    frozen = json.loads((payload/'build-contract.json').read_text())
    assert frozen['authorized_nodes'] == [node] and frozen['nodes'][node]['version'] == version
    diagnosis = json.loads((payload/'infra-interruption.json').read_text())
    assert diagnosis['package_attempt_consumed'] is diagnosis['candidate_installed'] is False
    assert not (payload/'sbuild.log').exists() and not list((payload/'packages').rglob('*'))
    assert baseline.is_dir() and not (baseline/'result.json').exists()
    assert not (baseline/'autopkgtest/summary').read_text().strip()
    assert 'Executing '+node+' reviewed Ubuntu baseline' in (payload/'pipeline.log').read_text()
    assert 'Run current reviewed package' in {step['name'] for step in job['steps']}
    files = {}
    for source, prefix in [(payload, ''), (baseline, 'ubuntu-baseline-preflight/')]:
        for path in sorted(source.rglob('*')):
            if path.is_file():
                assert not path.is_symlink()
                files[prefix+str(path.relative_to(source))] = path
    observation = {'schema': 1, 'kind': 'sealed-host-preflight-interruption-observation',
                   'runner_result_present': False, 'node': node, 'version': version,
                   'state': 'INFRA_INVALID', 'stage': 'reviewed-ubuntu-baseline-preflight',
                   'source_commit': head, 'workflow_run_id': host['workflow_run_id'],
                   'authoritative': True, 'system_test_acceleration': 'kvm-required',
                   'package_attempt_consumed': False, 'sbuild_result': 'not-run',
                   'lintian_result': 'not-run', 'autopkgtest_result': 'not-run',
                   'files_sha256': {name: sha(path) for name, path in files.items()}}
    return observation, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node')
    parser.add_argument('--campaign', choices=['manifests/package-revalidation.json', 'manifests/kde-plasma-package-build.json'],
                        default='manifests/package-revalidation.json')
    parser.add_argument('--zip',type=Path,required=True)
    parser.add_argument('--artifact-meta',type=Path)
    parser.add_argument('--host-export', action='store_true', help='retain a sealed interrupted preflight without an original runner result')
    parser.add_argument('--job-json',type=Path,required=True)
    parser.add_argument('--host-dir',type=Path,required=True)
    args = parser.parse_args()
    manifest = ROOT/args.campaign
    campaign = json.loads(manifest.read_text())
    plasma_inputs = campaign['role'] == 'reviewed-plasma-package-build'
    assert campaign['role'] in {'reviewed-plasma-package-build', 'reviewed-package-revalidation'}
    record = campaign['nodes'][args.node]
    assert campaign['authorized_nodes'] == [args.node] and record['state'] == 'build-pending'
    job = json.loads(args.job_json.read_text())
    subprocess.run(['sha256sum','--check','--quiet','evidence-sha256.txt'],cwd=args.host_dir,check=True)
    host = json.loads((args.host_dir/'host-result.json').read_text())
    head = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    if args.host_export:
        assert plasma_inputs and not args.artifact_meta and not args.zip.exists()
        base = args.host_dir/'guest-files/workspace/evidence'
        payload = base/'authoritative-plasma-package'
        original_present = (payload/'result.json').is_file()
        if original_present:
            raw = json.loads((payload/'result.json').read_text())
            assert raw['state'] == 'PASS' and raw['package_attempt_consumed'] is False
            assert raw['stage'] == 'reviewed-package-preflight-complete' and host['exit_code'] != 0
            assert job['status'] == 'completed' and job['conclusion'] == 'failure'
            steps = {step['name']: step for step in job['steps']}
            assert steps['Run current reviewed package']['conclusion'] == 'success'
            assert steps['Retain package sources, binaries and evidence']['conclusion'] != 'success'
            files = {str(path.relative_to(payload)): path for path in sorted(payload.rglob('*')) if path.is_file()}
            assert all(not path.is_symlink() for path in files.values())
            assert all(name in files and sha(files[name]) == digest for name, digest in raw['files_sha256'].items())
        else:
            raw, files = interrupted_preflight(payload,
                                              base/'runner-contract/reviewed-ubuntu-baseline', host, job, head, args.node, record['version'])
            raw['host_result_sha256'] = sha(args.host_dir/'host-result.json')
            raw['host_evidence_manifest_sha256'] = sha(args.host_dir/'evidence-sha256.txt')
        args.zip.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.zip, 'w', compression=zipfile.ZIP_DEFLATED, strict_timestamps=False) as archive:
            for name, path in files.items():
                archive.write(path, name)
            if not original_present:
                archive.writestr('result.json', json.dumps(raw, indent=2)+'\n')
        digest = sha(args.zip)
        meta = {'id': None, 'kind': 'sealed-host-preflight-result-export' if original_present else 'sealed-host-preflight-export', 'digest': 'sha256:'+digest,
                'workflow_run': {'id': job['run_id'], 'head_sha': head}}
    else:
        assert args.artifact_meta
        meta = json.loads(args.artifact_meta.read_text())
        digest = sha(args.zip)
        assert digest == meta['digest'].removeprefix('sha256:')
    with zipfile.ZipFile(args.zip) as archive:
        raw = json.loads(archive.read('result.json'))
        assert raw['source_commit'] == head == job['head_sha'] == meta['workflow_run']['head_sha']
        expected_artifact = ('authoritative-plasma-package-' if plasma_inputs else 'authoritative-package-revalidation-') + head
        if not args.host_export:
            assert meta['name'] == expected_artifact
        assert raw['workflow_run_id'] == str(job['run_id']) == host['workflow_run_id']
        transport_failure = meta.get('kind') == 'sealed-host-preflight-result-export'
        assert job['status'] == 'completed' and job['conclusion'] == ('failure' if transport_failure else ('success' if raw['state']=='PASS' else 'failure'))
        assert raw['node'] == args.node and raw['version'] == record['version']
        assert raw['authoritative'] and raw['system_test_acceleration'] == 'kvm-required'
        assert (host['exit_code'] != 0 and raw['state'] == 'PASS') if transport_failure else ((host['exit_code']==0) == (raw['state']=='PASS'))
        for name, expected in raw['files_sha256'].items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
        frozen = json.loads(archive.read('build-contract.json'))
        if 'campaign_manifest_sha256' in frozen:
            assert frozen['campaign_manifest'] == args.campaign
            assert frozen['campaign_manifest_sha256'] == hashlib.sha256(subprocess.check_output(['git','show',f'{head}:{args.campaign}'])).hexdigest()
            assert frozen['next_package_attempt'] == len(record['attempts'])+1
        built = frozen['nodes'][args.node]
        for key in ['packaging_sha256','symbols_baselines','frameworks_predecessors','supplementary_predecessors','retained_upgrade','upstream_sha256','signature_sha256']:
            assert built.get(key, {}) == record.get(key, {}), f'Changed reviewed input: {key}'
        assert frozen['execution_mode'] == campaign['execution_mode']
        preflight = raw['package_attempt_consumed'] is False
        if plasma_inputs:
            assert preflight, 'Use the existing Plasma closure for actual package Attempts'
        if frozen['execution_mode'] == 'preflight':
            assert preflight
        elif preflight:
            assert raw['state'] == 'INFRA_INVALID', 'Only infrastructure failure can end build mode before a package Attempt'
        sources = [name for name in archive.namelist() if name.startswith('packages/') and name.endswith('.dsc')]
        if sources:
            assert len(sources) == 1
            source = retention.fields(archive.read(sources[0]).decode())
            assert source['Source'] == record['source_package'] and source['Version'] == record['version']
            for line in source['Checksums-Sha256'].splitlines():
                if not line.strip():continue
                expected,size,name = line.split()
                data = archive.read('packages/'+name)
                assert hashlib.sha256(data).hexdigest() == expected and len(data) == int(size)
            orig = f"packages/{record['source_package']}_{record['upstream_version']}.orig.tar.xz"
            assert hashlib.sha256(archive.read(orig)).hexdigest() == record['upstream_sha256']
            assert hashlib.sha256(archive.read('upstream.tar.xz.sig')).hexdigest() == record['signature_sha256']
        else:
            assert preflight and raw['state']=='INFRA_INVALID', 'A package PASS requires the verified source closure'
        if raw['state'] == 'PASS':
            baseline = json.loads(archive.read('ubuntu-baseline-preflight/result.json'))
            assert baseline['state'] == 'PASS' and baseline['candidate_installed'] is False
            assert baseline['source_commit'] == head and baseline['workflow_run_id'] == raw['workflow_run_id']
            if record.get('baseline_setup_script'):
                baseline_testing = importlib.machinery.SourceFileLoader('baseline_testing', str(ROOT/'scripts/plasma-package-testing.py')).load_module()
                baseline_testing.verify_baseline_input_hashes(record, baseline)
            assert json.loads(archive.read('cache-probe/result.json'))['state'] == 'PASS'
            assert json.loads(archive.read('rootfs-admission.json'))['frameworks_and_qt_sdk_preinstalled'] is False
            if built.get('retained_upgrade'):
                assert json.loads(archive.read('retained-upgrade-inputs.json'))['eligible_as_build_predecessors'] is False
        if preflight:
            assert raw['state'] in {'PASS','INFRA_INVALID'}
            if raw['state']=='PASS':assert raw['stage']=='reviewed-package-preflight-complete'
            assert raw['sbuild_result'] == raw['lintian_result'] == raw['autopkgtest_result'] == 'not-run'
            certificates = campaign.get('package_input_certifications', []) if plasma_inputs else campaign['certifications']
            incidents = campaign.get('package_input_incidents', []) if plasma_inputs else campaign.get('infrastructure_incidents', [])
            number = len(certificates)+len(incidents)+1
            label = f'{args.node}-preflight{number}'
            inspection = {'source_complete':bool(sources),'candidate_binaries_built':False}
        else:
            number = len(record['attempts'])+1
            label = f'{args.node}-attempt{number}'
            changes=[name for name in archive.namelist() if name.startswith('packages/') and name.endswith('.changes')]
            if changes:
                inspection = retention.inspect(args.zip,{'node':args.node,'package_version':record['version'],
                                               'artifact_sha256':digest,'payload_prefix':'packages/'},record['source_package'])
            else:
                assert raw['state']!='PASS', 'A PASS requires the complete binary closure'
                inspection={'source_payload_verified':bool(sources),'buildinfo_verified':False,
                            'changes_payload_complete':False,'binaries':[]}
            for binary in inspection['binaries']:
                data=archive.read('packages/'+binary['file'])
                binary.update({'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)})
            if raw['state']=='PASS':
                assert {b['package']:b['architecture'] for b in inspection['binaries'] if not b['package'].endswith('-dbgsym')} == record['binary_packages']
                assert inspection['source_payload_verified'] and inspection['changes_payload_complete'] and not inspection['missing_debug_packages']
                assert all(raw[k]=='PASS' for k in ['sbuild_result','lintian_result','autopkgtest_result'])
                upstream = json.loads(archive.read('upstream-tests.json'))
                assert upstream['state']=='PASS' and upstream['expected_tests']==record['upstream_tests']
                assert archive.read('autopkgtest/summary').decode().split()==['ubuntu-abi-client','PASS','consumer','PASS']
                assert archive.read('retained-upgrade/summary').decode().split()==['retained-upgrade','PASS']
        directory = ROOT/'manifests/evidence/package-revalidation'/label
        assert not directory.exists(), 'Closed evidence is immutable'
        directory.mkdir(parents=True)
        for name in ['result.json','build-contract.json','signature.log','ubuntu-baseline-preflight/result.json',
                     'cache-probe/result.json','rootfs-admission.json','retained-upgrade-inputs.json',
                     'upstream-tests.json','autopkgtest/summary','retained-upgrade/summary','infra-interruption.json',
                     'cache-probe/installed-predecessor-contract.json', 'build-predecessor-verifier-tests.log']:
            if name in archive.namelist():
                path=directory/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(archive.read(name))
        # Replay the whole hash closure from an empty extraction, including hidden files.
        with tempfile.TemporaryDirectory(prefix='supralinux-revalidation-restore-') as temporary:
            for name in archive.namelist():
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
            archive.extractall(temporary)
            assert all(sha(Path(temporary)/name)==expected for name,expected in raw['files_sha256'].items())
    write(directory/'artifact-meta.json', meta)
    for path,name in [(args.job_json,'workflow-job.json'),
                      (args.host_dir/'host-result.json','host-result.json'),(args.host_dir/'evidence-sha256.txt','host-evidence-sha256.txt')]:
        shutil.copyfile(path,directory/name)
    if (args.host_dir/'live-memory-adjustment.json').is_file():
        shutil.copyfile(args.host_dir/'live-memory-adjustment.json',directory/'live-memory-adjustment.json')
    if (args.host_dir/'qemu-cpu-policy.json').is_file():
        shutil.copyfile(args.host_dir/'qemu-cpu-policy.json',directory/'qemu-cpu-policy.json')
    stored = ROOT/'.artifacts/package-revalidation'/label/'sha256'/f'{digest}.zip'
    assert not stored.exists()
    stored.parent.mkdir(parents=True)
    shutil.copyfile(args.zip,stored)
    preflight_scope = 'reviewed-package-input-preflight' if plasma_inputs else 'reviewed-package-revalidation-preflight'
    proof = {'schema':1,'scope':preflight_scope if preflight else 'authoritative-package-revalidation',
             'node':args.node,'version':record['version'],'state':raw['state'],'source_commit':head,
             'workflow_run_id':job['run_id'],'workflow_job_id':job['id'],'artifact_id':meta['id'],
             'artifact_sha256':digest,'host_evidence_dir':str(args.host_dir),
             'host_evidence_manifest_sha256':sha(args.host_dir/'evidence-sha256.txt'),
             'package_attempt_consumed':raw['package_attempt_consumed'],
             'result_path':str((directory/'result.json').relative_to(ROOT)), 'result_sha256':sha(directory/'result.json'),
             'contract_path':str((directory/'build-contract.json').relative_to(ROOT)),
             'archive_path':str(stored.relative_to(ROOT)),'inspection':inspection,
             'offline_restore_verified':True,'requires_github_for_restore':False,
             'files_sha256':{str(p.relative_to(directory)):sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}}
    if transport_failure:
        proof['infrastructure_transport_result'] = 'FAIL'
        proof['original_runner_result_preserved'] = True
        proof['current_input_admission'] = False
    if preflight:
        inputs=['scripts/run-authoritative-plasma-package.sh','scripts/prepare-plasma-package.py',
                'scripts/plasma-package-testing.py','scripts/probe-reviewed-ubuntu-baseline.py',
                'scripts/admit-frameworks-cache.py','scripts/prepare-milestone-sbuild-rootfs.py',
                'scripts/prepare-retained-package-inputs.py','scripts/run-kvm-jit-gate-core.sh',
                'scripts/configure-kvm-guest-network.py','scripts/check-kvm-network.py',
                'scripts/check-kvm-host.sh','scripts/test-kvm-network.py',
                'scripts/github-read-with-retry.sh',
                'scripts/qemu-kvm-required.sh', 'scripts/verify-reviewed-build-predecessors.py',
                'scripts/test-reviewed-package-contract.py']
        if plasma_inputs:
            inputs += ['scripts/frameworks-revalidation-inputs.py', 'scripts/prepare-frameworks-revalidation-inputs.py',
                       'scripts/probe-frameworks-build-inputs.sh']
            source_registry = ROOT/'manifests/frameworks-source-identities.json'
            if source_registry.is_file():
                source_nodes = json.loads(source_registry.read_text())['nodes']
                selected_legacy = set(record['frameworks_predecessors']) & set(source_nodes)
                if selected_legacy:
                    inputs += ['manifests/frameworks-source-identities.json']
                    inputs += [source_nodes[node]['manifest_path'] for node in sorted(selected_legacy)]
            support_registry = ROOT/'manifests/frameworks-support-inputs.json'
            if support_registry.is_file():
                support_nodes = json.loads(support_registry.read_text())['nodes']
                selected_support = set(record['frameworks_predecessors']) & set(support_nodes)
                if selected_support:
                    inputs += ['scripts/frameworks-support-inputs.py', 'manifests/frameworks-support-inputs.json']
                    inputs += [support_nodes[node]['evidence']['path'] for node in sorted(selected_support)]
        if 'campaign_manifest_sha256' in frozen:
            inputs += ['scripts/freeze-reviewed-package-contract.py']
        if record.get('supplementary_predecessors'):
            inputs += ['scripts/supplementary-package-inputs.py']
        proof['inputs_sha256']={name:hashlib.sha256(subprocess.check_output(['git','show',f'{head}:{name}'])).hexdigest() for name in inputs}
        proof['packaging_sha256']=record['packaging_sha256']
        proof['frameworks_predecessors']=record['frameworks_predecessors']
        if record.get('supplementary_predecessors'):
            proof['supplementary_predecessors']=record['supplementary_predecessors']
    write(directory/'verification.json',proof)
    link={'path':str((directory/'verification.json').relative_to(ROOT)),'sha256':sha(directory/'verification.json')}
    if preflight:
        if raw['state']=='PASS':
            key = 'package_input_certifications' if plasma_inputs else 'certifications'
            campaign.setdefault(key, []).append(link)
            if transport_failure:
                link.update(applicable=False, inapplicability_reason='Original preflight PASS preserved after Actions/host network transport failure; changed host network policy requires fresh certification')
            else:
                campaign['execution_mode']='build'
            if plasma_inputs and record.get('source_scope') == 'plasma-supplementary-provider':
                path = ROOT/'manifests/kde-plasma-supplementary-providers.json'
                providers = json.loads(path.read_text())
                providers['nodes'][args.node]['next_gate'] = 'authoritative-supplementary-package-build'
                write(path, providers)
        else:
            key = 'package_input_incidents' if plasma_inputs else 'infrastructure_incidents'
            campaign.setdefault(key, []).append(link)
    else:
        record['attempts'].append({'attempt':number,'state':raw['state'],**link})
        if raw['state']=='PASS':
            record['state']='PASS'
            record['downstream_eligible']=True
            record['evidence']=link
            record['binaries']=[b for b in inspection['binaries'] if not b['package'].endswith('-dbgsym')]
            campaign['authorized_nodes']=[]
            campaign['package_execution_authorized']=False
            campaign['execution_mode']='complete'
            campaign['state']='PASS'
    write(manifest,campaign)
    origin = 'sealed host observation' if args.host_export else 'original runner result'
    print(f'{label}: {origin} {raw["state"]} retained, offline restoration verified; package Attempt={not preflight}')


if __name__=='__main__':
    main()

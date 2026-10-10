#!/usr/bin/env python3
"""Reject stale, forged or misidentified supplementary predecessor inputs."""
import copy
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('supplementary', ROOT/'scripts/supplementary-package-inputs.py')
inputs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inputs)


def reviewed_request():
    directory = Path('manifests/evidence/plasma/plasma-wayland-protocols-attempt1')
    record = json.loads((ROOT/directory/'build-contract.json').read_text())['nodes']['plasma-wayland-protocols']
    result = json.loads((ROOT/directory/'result.json').read_text())
    metadata = json.loads((ROOT/directory/'artifact-meta.json').read_text())
    evidence = {'result_path':str(directory/'result.json'), 'result_sha256':inputs.digest(ROOT/directory/'result.json'),
                'contract_path':str(directory/'build-contract.json'), 'artifact_id':metadata['id'],
                'artifact_sha256':metadata['digest'].removeprefix('sha256:'),
                'local_retention':{'archive_root':'.artifacts/plasma-1.22.0/plasma-wayland-protocols-attempt1'}}
    binary = 'plasma-wayland-protocols_1.22.0-0supralinux1_all.deb'
    return {'source_package':record['source_package'], 'version':record['version'],
            'upstream_version':record['upstream_version'], 'cmake_package':'PlasmaWaylandProtocols',
            'binaries':[{'package':'plasma-wayland-protocols', 'architecture':'all',
                         'sha256':result['files_sha256']['packages/'+binary]}],
            'evidence':{**{key:evidence[key] for key in ['result_path','result_sha256','contract_path','artifact_id','artifact_sha256']},
                        'contract_sha256':inputs.digest(ROOT/evidence['contract_path']),
                        'archive_root':evidence['local_retention']['archive_root'], 'payload_prefix':'packages/'}}


class SupplementaryAdmission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.request = reviewed_request()
        files = ['manifests/kde-plasma-package-build.json', 'manifests/kde-plasma-supplementary-providers.json',
                 self.request['evidence']['result_path'], self.request['evidence']['contract_path'],
                 str(Path(self.request['evidence']['result_path']).parent/'artifact-meta.json')]
        for relative in files:
            target = self.root/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, target)
        # The fixture comes from immutable Attempt 1 evidence, independently
        # of a later live provider repair or version transition.
        path = self.root/'manifests/kde-plasma-package-build.json'
        campaign = json.loads(path.read_text())
        frozen = json.loads((self.root/self.request['evidence']['contract_path']).read_text())['nodes']['plasma-wayland-protocols']
        frozen.update(state='PASS', evidence={**self.request['evidence'], 'local_retention':{
            'archive_root':self.request['evidence']['archive_root'], 'source_complete':True,
            'changes_complete':True,'buildinfo_verified':True,'offline_restore_verified':True}})
        campaign['nodes']['plasma-wayland-protocols'] = frozen
        path.write_text(json.dumps(campaign))
        path = self.root/'manifests/kde-plasma-supplementary-providers.json'
        providers = json.loads(path.read_text())
        provider = providers['nodes']['plasma-wayland-protocols']
        provider.update(state='package-PASS', qt_provider_effect='none', affected_nodes=['kwayland','libkscreen'])
        provider['candidate_provider']['package_gate'] = 'PASS'
        provider['cmake_requirement']['module'] = 'PlasmaWaylandProtocols'
        path.write_text(json.dumps(providers))

    def check(self, historical=False, consumer='kwayland'):
        return inputs.checked_contract('plasma-wayland-protocols', self.request, self.root, historical, consumer)

    def change_canonical(self, key, value):
        path = self.root/'manifests/kde-plasma-package-build.json'
        data = json.loads(path.read_text())
        data['nodes']['plasma-wayland-protocols'][key] = value
        path.write_text(json.dumps(data))

    def test_exact_closed_authoritative_provider_is_eligible(self):
        result, _ = self.check()
        self.assertEqual(result['state'], 'PASS')
        self.assertEqual(self.check(consumer='libkscreen')[0]['version'], self.request['version'])

    def test_old_closure_stays_historical_but_cannot_feed_a_changed_active_provider(self):
        self.change_canonical('version', '1.23.0-0supralinux1')
        with self.assertRaises(AssertionError): self.check()
        self.assertEqual(self.check(historical=True)[0]['version'], '1.22.0-0supralinux1')

    def test_nonpass_or_ineligible_or_wrong_authority_is_rejected(self):
        for key, value in [('state','build-pending'), ('downstream_eligible',False), ('source_scope','plasma-level0')]:
            with self.subTest(key=key):
                path = self.root/'manifests/kde-plasma-package-build.json'
                original = path.read_bytes()
                self.change_canonical(key,value)
                with self.assertRaises(AssertionError): self.check()
                path.write_bytes(original)

    def test_changed_source_version_config_architecture_or_binary_digest_is_rejected(self):
        original = copy.deepcopy(self.request)
        for key,value in [('source_package','unrelated'),('version','1.20.0-2'),
                          ('upstream_version','1.20.0'),('cmake_package','Unrelated')]:
            self.request = copy.deepcopy(original);self.request[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.check()
        for key,value in [('architecture','amd64'),('sha256','0'*64)]:
            self.request = copy.deepcopy(original);self.request['binaries'][0][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.check()

    def test_replayed_artifact_or_contract_digest_or_escaping_path_is_rejected(self):
        original = copy.deepcopy(self.request)
        for key,value in [('artifact_id',1),('artifact_sha256','0'*64),('contract_sha256','0'*64),
                          ('result_path','../outside'),('payload_prefix','other/')]:
            self.request = copy.deepcopy(original);self.request['evidence'][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): self.check()

    def test_unreviewed_consumer_or_self_dependency_is_rejected(self):
        for node in ['unrelated','plasma-wayland-protocols']:
            with self.subTest(node=node), self.assertRaises(AssertionError): self.check(consumer=node)

    def test_proof_symlink_is_rejected(self):
        path = self.root/self.request['evidence']['result_path']
        original = path.with_suffix('.original')
        path.rename(original);path.symlink_to(original)
        with self.assertRaises(AssertionError): self.check()


class DebianIdentity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.request = {'source_package':'example', 'version':'1.0-1'}
        self.binary = {'package':'example', 'architecture':'all'}

    def build(self, **changes):
        control = {'Package':'example','Version':'1.0-1','Architecture':'all',
                   'Maintainer':'Test <test@example.invalid>','Description':'Input identity fixture'}
        control.update(changes)
        directory = self.root/'package/DEBIAN';directory.mkdir(parents=True,exist_ok=True)
        (directory/'control').write_text(''.join(f'{key}: {value}\n' for key,value in control.items()))
        self.deb = self.root/'input.deb'
        subprocess.run(['dpkg-deb','--root-owner-group','--build',str(directory.parent),str(self.deb)],check=True,stdout=subprocess.DEVNULL)
        self.binary['sha256'] = inputs.digest(self.deb)

    def test_debian_implicit_source_identity_is_supported(self):
        self.build();inputs.verify_binary(self.deb,'example',self.request,self.binary)

    def test_same_digest_claim_cannot_hide_wrong_debian_identity(self):
        for changes in [{'Package':'unrelated'},{'Source':'unrelated'},{'Version':'1.0-2'},{'Architecture':'amd64'}]:
            self.build(**changes)
            with self.subTest(changes=changes), self.assertRaises(AssertionError):
                inputs.verify_binary(self.deb,'example',self.request,self.binary)

    def test_corrupted_binary_is_rejected(self):
        self.build();self.deb.write_bytes(self.deb.read_bytes()+b'changed')
        with self.assertRaises(AssertionError): inputs.verify_binary(self.deb,'example',self.request,self.binary)


if __name__ == '__main__': unittest.main()

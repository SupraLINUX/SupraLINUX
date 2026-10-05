#!/usr/bin/env python3
"""Regression guards for historical support evidence and exact downstream inputs."""
import hashlib
import importlib.machinery
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
support = importlib.machinery.SourceFileLoader('support_test', str(ROOT/'scripts/frameworks-support-inputs.py')).load_module()
effective = importlib.machinery.SourceFileLoader('support_effective_test', str(ROOT/'scripts/frameworks-revalidation-inputs.py')).load_module()


class SupportInputs(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.registry = json.loads((ROOT/support.REGISTRY).read_text())
        self.link = self.registry['nodes']['kdoctools']['evidence']
        self.proof_path = self.root/self.link['path']
        shutil.copytree((ROOT/self.link['path']).parent, self.proof_path.parent)
        self.proof = json.loads(self.proof_path.read_text())
        history = self.proof['historical_manifest_path']
        (self.root/history).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/history, self.root/history)

    def reseal(self, file=None):
        if file:
            self.proof['files_sha256'][file] = support.digest(self.proof_path.parent/file)
        self.proof_path.write_text(json.dumps(self.proof))
        self.link['sha256'] = support.digest(self.proof_path)

    def validate(self):
        return support.verified_nodes(self.root, self.registry)

    def test_original_scope_and_binary_identities_preserved(self):
        node = self.validate()['kdoctools']
        self.assertFalse(node['authoritative'])
        self.assertEqual(len(node['retained_binaries']), 6)
        self.assertEqual(node['package_version'], '6.30.0-0supralinux1')
        before = (ROOT/'manifests/kde-dag.json').read_bytes()
        historical = effective.effective_nodes(json.loads(before), historical=True)
        self.assertNotIn('kdoctools', historical)
        self.assertEqual((ROOT/'manifests/kde-dag.json').read_bytes(), before)

    def test_changed_evidence_rejected(self):
        (self.proof_path.parent/'result.json').write_text('{}')
        with self.assertRaisesRegex(AssertionError, 'file changed'):
            self.validate()

    def test_hosted_result_cannot_be_promoted_by_resealing(self):
        self.proof['authoritative'] = True
        self.reseal()
        with self.assertRaises(AssertionError):
            self.validate()

    def test_wrong_original_job_rejected_after_resealing(self):
        file = self.proof_path.parent/'workflow-job.json'
        job = json.loads(file.read_text())
        job['head_sha'] = '0'*40
        file.write_text(json.dumps(job))
        self.reseal('workflow-job.json')
        with self.assertRaises(AssertionError):
            self.validate()

    def test_wrong_source_or_version_rejected(self):
        for key, value in [('source_package', 'unreviewed-source'), ('version', '6.30.0-0supralinux2')]:
            with self.subTest(key=key):
                original = self.proof[key]
                self.proof[key] = value
                self.reseal()
                with self.assertRaises(AssertionError):
                    self.validate()
                self.proof[key] = original
                self.reseal()

    def test_reviewed_digest_cannot_be_changed(self):
        node = self.validate()['kdoctools']
        binary = next(b for b in node['retained_binaries'] if b['package'] == 'libkf6doctools-dev')
        requested = {'source_package': node['source_package'], 'version': node['package_version'],
                     'binaries': [{key: binary[key] for key in ['package', 'architecture', 'sha256']}]}
        effective.check_requested('kdoctools', requested, node)
        requested['binaries'][0]['sha256'] = '0'*64
        with self.assertRaisesRegex(AssertionError, 'digest mismatch'):
            effective.check_requested('kdoctools', requested, node)

    def test_archived_logs_cannot_change(self):
        proof = {'archive_files_sha256': {'pipeline.log': hashlib.sha256(b'original log').hexdigest()}}
        for data in [b'original log', b'changed log']:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as archive:
                archive.writestr('pipeline.log', data)
            with zipfile.ZipFile(buffer) as archive:
                if data == b'original log':
                    support.verify_archive(archive, proof)
                else:
                    with self.assertRaisesRegex(AssertionError, 'member changed'):
                        support.verify_archive(archive, proof)


if __name__ == '__main__':
    unittest.main()

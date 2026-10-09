#!/usr/bin/env python3
"""Check that execution contracts preserve active inputs and reject stale scope."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from plasma_lifecycle import verify_package_hold

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('freeze_contract', ROOT/'scripts/freeze-reviewed-package-contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)
input_spec = importlib.util.spec_from_file_location('build_predecessors', ROOT/'scripts/verify-reviewed-build-predecessors.py')
predecessors = importlib.util.module_from_spec(input_spec)
input_spec.loader.exec_module(predecessors)


class ExecutionContract(unittest.TestCase):
    def setUp(self):
        self.campaign = {'schema': 1, 'role': 'reviewed-plasma-package-build', 'state': 'execution-authorized',
                         'package_execution_authorized': True, 'authorized_nodes': ['active'],
                         'runner_class': 'disposable-kvm', 'execution_checkpoint': 'reviewed-cache',
                         'nodes': {'active': {'state': 'build-pending', 'packaging_review': 'PASS',
                                             'version': '1.0-2', 'upstream_sha256': '1'*64,
                                             'packaging_sha256': {'control': '2'*64},
                                             'frameworks_predecessors': {'dependency': {'version': '1.0-3'}},
                                             'attempts': [{'state': 'FAIL'}]}}}

    def freeze(self, node='active'):
        return contract.freeze(self.campaign, node, 'manifests/campaign.json', '3'*64)

    def test_unrelated_history_does_not_expand_or_change_execution_inputs(self):
        before = self.freeze()
        self.campaign['nodes']['closed'] = {'state': 'PASS', 'attempts': [{'large': 'history'*10000}]}
        after = self.freeze()
        self.assertEqual(before, after)
        self.assertEqual(after['nodes']['active']['version'], '1.0-2')
        self.assertEqual(after['nodes']['active']['packaging_sha256'], {'control': '2'*64})
        self.assertEqual(after['nodes']['active']['frameworks_predecessors'], {'dependency': {'version': '1.0-3'}})
        self.assertEqual(after['next_package_attempt'], 2)

    def test_stale_or_unreviewed_scope_rejected(self):
        original = copy.deepcopy(self.campaign)
        for key, value in [('authorized_nodes', ['different']), ('package_execution_authorized', False), ('state', 'PASS')]:
            with self.subTest(key=key):
                self.campaign = copy.deepcopy(original)
                self.campaign[key] = value
                with self.assertRaises(AssertionError):
                    self.freeze()
        self.campaign = original
        self.campaign['nodes']['active']['packaging_review'] = 'pending'
        with self.assertRaises(AssertionError):
            self.freeze()


class ActualBuildPredecessors(unittest.TestCase):
    def setUp(self):
        self.control = 'Source: example\nBuild-Depends: sdk (= 4:6.30-1), cmake\n\nPackage: example\nArchitecture: any\n'
        self.record = {'source_package': 'example', 'version': '1.0-2',
                       'packaging_sha256': {'control': hashlib.sha256(self.control.encode()).hexdigest()},
                       'frameworks_predecessors': {'sdk-node': {'version': '4:6.30-1', 'binaries': [
                           {'package': 'sdk', 'architecture': 'amd64'},
                           {'package': 'runtime', 'architecture': 'amd64'},
                           {'package': 'unused-tool', 'architecture': 'all'}]}}}
        self.info = ('Source: example\nVersion: 1.0-2\nBuild-Architecture: amd64\n'
                     'Installed-Build-Depends:\n sdk (= 4:6.30-1),\n runtime (= 4:6.30-1),\n cmake (= 4.2-1)\n')

    def verify(self):
        return predecessors.verify(self.record, self.control, self.info)

    def test_unused_available_package_is_not_an_installed_build_dependency(self):
        result = self.verify()
        self.assertEqual(result['required_direct_predecessors'], ['sdk'])
        self.assertEqual(result['available_predecessors_not_installed'], ['unused-tool'])
        self.assertEqual(len(result['installed_predecessors']), 2)

    def test_supplementary_input_is_required_at_its_exact_reviewed_version(self):
        self.control = self.control.replace(', cmake', ', protocols (= 1.22.0-1), cmake')
        self.record['packaging_sha256']['control'] = hashlib.sha256(self.control.encode()).hexdigest()
        self.record['supplementary_predecessors'] = {'protocol-provider':{'version':'1.22.0-1',
            'binaries':[{'package':'protocols','architecture':'all'}]}}
        self.info += ' , protocols (= 1.22.0-1)\n'
        self.assertEqual(self.verify()['required_direct_predecessors'], ['protocols','sdk'])
        self.info = self.info.replace('protocols (= 1.22.0-1)', 'protocols (= 1.20.0-2)')
        with self.assertRaisesRegex(AssertionError, 'installed'): self.verify()

    def test_wrong_installed_version_is_rejected_for_direct_or_transitive_inputs(self):
        original = self.info
        for name in ['sdk', 'runtime']:
            self.info = original.replace(name+' (= 4:6.30-1)', name+' (= 4:6.24-1)')
            with self.subTest(name=name), self.assertRaisesRegex(AssertionError, 'installed'):
                self.verify()

    def test_missing_direct_sdk_is_rejected(self):
        self.info = self.info.replace(' sdk (= 4:6.30-1),\n', '')
        with self.assertRaisesRegex(AssertionError, 'direct predecessor absent'):
            self.verify()

    def test_architecture_qualified_relations_and_epochs_are_preserved(self):
        self.info = self.info.replace('sdk (=', 'sdk:amd64 (=')
        self.assertEqual(self.verify()['state'], 'PASS')
        self.info = self.info.replace('sdk:amd64', 'sdk:arm64')
        with self.assertRaisesRegex(AssertionError, 'architecture'):
            self.verify()

    def test_changed_source_control_or_build_identity_is_rejected(self):
        self.control += '\n'
        with self.assertRaisesRegex(AssertionError, 'control changed'):
            self.verify()
        self.control = self.control[:-1]
        self.info = self.info.replace('Version: 1.0-2', 'Version: 1.0-1')
        with self.assertRaisesRegex(AssertionError, 'build version'):
            self.verify()

    def test_duplicate_installed_identity_is_rejected(self):
        self.info += ' , sdk (= 4:6.30-1)\n'
        with self.assertRaisesRegex(AssertionError, 'Duplicate installed'):
            self.verify()


class CompatibilityHold(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / 'manifests/evidence/plasma/held-attempt1'
        self.directory.mkdir(parents=True)
        result = {'state': 'FAIL', 'node': 'held', 'version': '1.0-1', 'source_commit': 'a'*40}
        self.result = self.directory / 'result.json'
        self.result.write_text(json.dumps(result))
        digest = hashlib.sha256(self.result.read_bytes()).hexdigest()
        self.record = {'state': 'compatibility-review-required', 'version': '1.0-1',
                       'upstream_sha256': 'b'*64, 'packaging_sha256': {'symbols': 'c'*64},
                       'attempts': [{'state': 'FAIL', 'package_attempt_consumed': True,
                                     'result_path': str(self.result.relative_to(self.root)),
                                     'result_sha256': digest, 'source_commit': 'a'*40}]}
        self.review = self.directory / 'review.json'
        self.proof = {'kind': 'package-compatibility-hold', 'state': 'HOLD', 'node': 'held',
                      'version': '1.0-1', 'source_commit': 'a'*40, 'upstream_sha256': 'b'*64,
                      'packaging_sha256': {'symbols': 'c'*64}, 'original_result_sha256': digest,
                      'reason': 'Observed incompatible SDK change', 'downstream_eligible': False,
                      'files_sha256': {'result.json': digest}}
        self.record['compatibility_hold'] = {'reason': self.proof['reason'], 'reentry_gate': 'compatibility-review',
                                             'result_path': str(self.result.relative_to(self.root)),
                                             'review_path': str(self.review.relative_to(self.root))}
        self.save_review()

    def save_review(self):
        self.review.write_text(json.dumps(self.proof))
        self.record['compatibility_hold']['review_sha256'] = hashlib.sha256(self.review.read_bytes()).hexdigest()

    def verify(self, scope=None):
        return verify_package_hold(self.root, 'held', self.record, scope or [])

    def test_hold_preserves_failure_without_blocking_an_independent_package(self):
        self.assertEqual(self.verify(['independent'])['state'], 'HOLD')

    def test_hold_cannot_become_an_executable_scope(self):
        with self.assertRaisesRegex(AssertionError, 'cannot execute'):
            self.verify(['held'])

    def test_changed_review_bytes_are_rejected(self):
        self.review.write_text(self.review.read_text() + ' ')
        with self.assertRaises(AssertionError):
            self.verify()

    def test_review_cannot_substitute_another_source_or_package(self):
        for field, value in [('source_commit', 'd'*40), ('version', '2.0-1'),
                             ('upstream_sha256', 'e'*64), ('packaging_sha256', {'symbols': 'f'*64}),
                             ('downstream_eligible', True)]:
            with self.subTest(field=field):
                original = self.proof[field]
                self.proof[field] = value
                self.save_review()
                with self.assertRaises(AssertionError):
                    self.verify()
                self.proof[field] = original
                self.save_review()

    def test_original_failure_and_file_bytes_must_remain_intact(self):
        self.result.write_text('{}')
        with self.assertRaises(AssertionError):
            self.verify()

    def test_evidence_paths_cannot_escape_the_review(self):
        for name in ['../result.json', str(self.result)]:
            with self.subTest(name=name):
                self.proof['files_sha256'] = {name: self.record['attempts'][0]['result_sha256']}
                self.save_review()
                with self.assertRaises(AssertionError):
                    self.verify()

    def test_pass_cannot_be_used_as_an_original_failed_attempt(self):
        self.record['attempts'][0]['state'] = 'PASS'
        with self.assertRaises(AssertionError):
            self.verify()


if __name__ == '__main__':
    unittest.main()

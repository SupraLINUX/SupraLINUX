#!/usr/bin/env python3
"""Check that execution contracts preserve active inputs and reject stale scope."""
import copy
import hashlib
import importlib.util
import unittest
from pathlib import Path

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


if __name__ == '__main__':
    unittest.main()

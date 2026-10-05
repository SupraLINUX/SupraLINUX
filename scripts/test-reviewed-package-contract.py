#!/usr/bin/env python3
"""Check that execution contracts preserve active inputs and reject stale scope."""
import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('freeze_contract', ROOT/'scripts/freeze-reviewed-package-contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


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


if __name__ == '__main__':
    unittest.main()

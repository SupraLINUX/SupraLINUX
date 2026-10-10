#!/usr/bin/env python3
"""Check historical recovery after cancellation without admitting package execution."""
import importlib.util
import copy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('execution_contract_controls', ROOT/'scripts/test-reviewed-package-contract.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class CancelledPreflightTransport(contract.PreflightTransport):
    def setUp(self):
        super().setUp()
        self.link['inapplicability_reason'] = 'Workflow deadline; original complete result recovered from sealed host'
        self.job['conclusion'] = 'cancelled'
        self.job['steps'][0].update(conclusion='cancelled', started_at='2000-01-01T20:46:18Z',
                                  completed_at='2000-01-01T22:45:18Z')
        self.artifact['kind'] = 'sealed-host-preflight-cancelled-result-export'
        self.result.update(exit_code=0, finished_at='2000-01-01T22:48:20+00:00')
        self.host['finished_at'] = '2000-01-01T22:50:03Z'

    def test_recovered_pass_requires_original_completion_before_cleanup(self):
        for mapping, key, value in [(self.result, 'exit_code', 143),
                                    (self.result, 'finished_at', '2000-01-01T22:44:00Z'),
                                    (self.result, 'finished_at', '2000-01-01T22:51:00Z'),
                                    (self.result, 'finished_at', '2000-01-01T22:48:20'),
                                    (self.job['steps'][0], 'conclusion', 'success')]:
            old = mapping[key]
            mapping[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(AssertionError):
                self.verify()
            mapping[key] = old

    def test_cancelled_export_cannot_be_relabelled_as_successful_transport(self):
        self.artifact['kind'] = 'sealed-host-preflight-result-export'
        with self.assertRaises(AssertionError):
            self.verify()


class InfrastructurePreflightTransport(unittest.TestCase):
    def setUp(self):
        self.control = contract.PreflightTransport()
        self.control.setUp()
        self.control.result.update(state='INFRA_INVALID', stage='reviewed-ubuntu-baseline-preflight',
                                   sbuild_result='not-run', lintian_result='not-run', autopkgtest_result='not-run')
        self.control.job['steps'][0]['conclusion'] = 'failure'
        self.control.artifact['kind'] = 'sealed-host-preflight-infra-result-export'

    def test_original_infrastructure_failure_is_preserved_without_admission(self):
        before = copy.deepcopy(self.control.result)
        self.control.verify()
        self.assertEqual(self.control.result, before)

    def test_infrastructure_export_cannot_claim_package_execution_or_pass(self):
        for key, value in [('state', 'PASS'), ('state', 'FAIL'), ('package_attempt_consumed', True),
                           ('sbuild_result', 'PASS'), ('lintian_result', 'PASS'), ('autopkgtest_result', 'PASS')]:
            old = self.control.result[key]
            self.control.result[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(AssertionError):
                self.control.verify()
            self.control.result[key] = old

    def test_failed_export_cannot_become_successful_or_cancelled_delivery(self):
        for mapping, key, value in [(self.control.job, 'conclusion', 'success'),
                                    (self.control.job, 'conclusion', 'cancelled'),
                                    (self.control.job, 'status', 'in_progress'),
                                    (self.control.host, 'exit_code', 0),
                                    (self.control.artifact, 'id', 123),
                                    (self.control.artifact, 'kind', 'sealed-host-preflight-result-export')]:
            old = mapping[key]
            mapping[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(AssertionError):
                self.control.verify()
            mapping[key] = old

    def test_execution_and_retention_failure_are_both_required(self):
        for step in self.control.job['steps']:
            old = step['conclusion']
            step['conclusion'] = 'success'
            with self.subTest(step=step['name']), self.assertRaises(AssertionError):
                self.control.verify()
            step['conclusion'] = old

    def test_recovered_infrastructure_result_never_admits_current_execution(self):
        for mapping, key, value in [(self.control.link, 'applicable', True),
                                    (self.control.proof, 'current_input_admission', True),
                                    (self.control.proof, 'original_runner_result_preserved', False),
                                    (self.control.proof, 'infrastructure_transport_result', 'PASS')]:
            old = mapping[key]
            mapping[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.control.verify()
            mapping[key] = old


if __name__ == '__main__':
    unittest.main()

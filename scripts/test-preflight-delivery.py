#!/usr/bin/env python3
"""Check historical recovery after cancellation without admitting package execution."""
import importlib.util
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


if __name__ == '__main__':
    unittest.main()

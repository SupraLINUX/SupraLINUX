#!/usr/bin/env python3
"""Reject ambiguous or completed executions when retaining an interrupted preflight."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preflight_closure', ROOT/'scripts/close-package-revalidation-evidence.py')
closure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(closure)


class Recovery(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.payload, self.baseline = root/'package', root/'baseline'
        (self.payload/'packages').mkdir(parents=True)
        (self.baseline/'autopkgtest').mkdir(parents=True)
        (self.baseline/'autopkgtest/summary').write_text('')
        (self.payload/'build-contract.json').write_text(json.dumps({'authorized_nodes': ['active'], 'nodes': {'active': {'version': '1-2'}}}))
        (self.payload/'infra-interruption.json').write_text(json.dumps({'package_attempt_consumed': False, 'candidate_installed': False}))
        (self.payload/'pipeline.log').write_text('Executing active reviewed Ubuntu baseline in nested KVM...')
        self.host = {'exit_code': 1, 'workflow_run_id': '123'}
        self.job = {'status': 'completed', 'conclusion': 'failure', 'head_sha': 'source', 'run_id': 123,
                    'steps': [{'name': 'Run current reviewed package'}]}

    def recover(self):
        return closure.interrupted_preflight(self.payload, self.baseline, self.host, self.job, 'source', 'active', '1-2')

    def test_partial_baseline_retained_as_observation_with_zero_attempts(self):
        hidden = self.baseline/'autopkgtest/.partial-log'
        hidden.write_text('retained bytes')
        observation, files = self.recover()
        self.assertFalse(observation['runner_result_present'])
        self.assertFalse(observation['package_attempt_consumed'])
        self.assertEqual(observation['state'], 'INFRA_INVALID')
        self.assertEqual(files['ubuntu-baseline-preflight/autopkgtest/.partial-log'], hidden)

    def test_existing_runner_result_rejected(self):
        (self.payload/'result.json').write_text('{}')
        with self.assertRaises(AssertionError):
            self.recover()

    def test_candidate_or_build_execution_rejected(self):
        for path in ['packages/candidate.dsc', 'sbuild.log']:
            with self.subTest(path=path):
                file = self.payload/path
                file.write_text('started')
                with self.assertRaises(AssertionError):
                    self.recover()
                file.unlink()

    def test_completed_baseline_rejected(self):
        (self.baseline/'autopkgtest/summary').write_text('consumer PASS\n')
        with self.assertRaises(AssertionError):
            self.recover()

    def test_wrong_source_or_run_rejected(self):
        for key, value in [('head_sha', 'different'), ('run_id', 124)]:
            with self.subTest(key=key):
                old = self.job[key]
                self.job[key] = value
                with self.assertRaises(AssertionError):
                    self.recover()
                self.job[key] = old


if __name__ == '__main__':
    unittest.main()

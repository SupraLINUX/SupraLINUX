#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
"""Reject stale package evidence and unsafe desktop composition plans."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('image_planner', Path(__file__).with_name('plan-desktop-image.py'))
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class ImagePlan(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.manifests = self.root / 'manifests'
        self.manifests.mkdir()
        self.profile = {'schema': 1, 'name': 'core-session', 'state': 'planning-only',
                        'scope': 'Preliminary desktop path, not final seed', 'roots': ['shell'],
                        'final_install_seed': False, 'image_build_authorized': False,
                        'additional_image_gates': ['actual boot and install'], 'final_release_gates': ['full compatibility']}
        self.dag = {'canonical_for_package_planning': True, 'nodes': {
            'sdk': {'level': 0, 'depends_on': []}, 'shell': {'level': 1, 'depends_on': ['sdk']}}}
        self.result = {'node': 'sdk', 'version': '1.0-2', 'source_commit': 'a' * 40,
                       'state': 'PASS', 'authoritative': True,
                       'sbuild_result': 'PASS', 'lintian_result': 'PASS', 'autopkgtest_result': 'PASS'}
        self.result_path = self.manifests / 'evidence/sdk/result.json'
        self.result_path.parent.mkdir(parents=True)
        self.record = {'state': 'PASS', 'source_package': 'sdk', 'version': '1.0-2', 'evidence': {
            'result_path': 'manifests/evidence/sdk/result.json', 'source_commit': 'a' * 40,
            'local_retention': {key: True for key in ['source_complete', 'changes_complete', 'buildinfo_verified', 'offline_restore_verified']}}}
        self.save_result()
        self.campaign = {'nodes': {'sdk': self.record}}
        (self.manifests / 'desktop-stack.json').write_text(json.dumps({
            'platform': {'authority': 'ubuntu', 'version': '26.04 LTS'},
            'desktop': {name: {'version': 'selected'} for name in ['plasma', 'frameworks', 'gear']}}))

    def tearDown(self):
        self.temporary.cleanup()

    def save_result(self):
        self.result_path.write_text(json.dumps(self.result))
        self.record['evidence']['result_sha256'] = hashlib.sha256(self.result_path.read_bytes()).hexdigest()

    def run_plan(self):
        (self.manifests / 'kde-plasma-dag.json').write_text(json.dumps(self.dag))
        (self.manifests / 'kde-plasma-package-build.json').write_text(json.dumps(self.campaign))
        return planner.plan(self.root, self.profile)

    def test_partial_desktop_is_ordered_and_never_authorizes_an_image(self):
        result = self.run_plan()
        self.assertEqual([row['node'] for row in result['components']], ['sdk', 'shell'])
        self.assertEqual(result['missing_package_gates'], ['shell'])
        self.assertEqual(result['counts']['recorded_package_PASS'], 1)
        self.assertFalse(result['image_build_authorized'])
        self.assertFalse(result['image_available'])
        self.assertFalse(result['remaining_upstream_components_excluded'])
        self.assertTrue(all(not row['local_image_payload_restored'] for row in result['components']))

    def test_cycle_and_unknown_roots_are_rejected(self):
        self.dag['nodes']['sdk']['depends_on'] = ['shell']
        with self.assertRaisesRegex(AssertionError, 'cycle'): self.run_plan()
        self.dag['nodes']['sdk']['depends_on'] = []
        self.profile['roots'] = ['unknown']
        with self.assertRaisesRegex(AssertionError, 'Unknown'): self.run_plan()

    def test_changed_bytes_or_identity_are_rejected_even_after_rehash(self):
        self.result_path.write_text('{}')
        with self.assertRaisesRegex(AssertionError, 'digest'): self.run_plan()
        for field, value in [('version', '1.0-1'), ('node', 'another'), ('source_commit', 'b' * 40),
                             ('authoritative', False), ('sbuild_result', 'FAIL'), ('autopkgtest_result', 'not-run')]:
            original = copy.deepcopy(self.result)
            self.result[field] = value
            self.save_result()
            with self.subTest(field=field), self.assertRaises(AssertionError): self.run_plan()
            self.result = original
        self.save_result()

    def test_missing_retention_hold_and_unsafe_path_are_rejected(self):
        self.record['evidence']['local_retention']['source_complete'] = False
        with self.assertRaisesRegex(AssertionError, 'retention'): self.run_plan()
        self.record['evidence']['local_retention']['source_complete'] = True
        self.record['compatibility_hold'] = {'reason': 'pending'}
        with self.assertRaisesRegex(AssertionError, 'hold'): self.run_plan()
        del self.record['compatibility_hold']
        self.record['evidence']['result_path'] = '../result.json'
        with self.assertRaisesRegex(AssertionError, 'Unsafe'): self.run_plan()

    def test_even_complete_package_plan_requires_independent_image_gates(self):
        self.profile['roots'] = ['sdk']
        result = self.run_plan()
        self.assertEqual(result['missing_package_gates'], [])
        self.assertFalse(result['image_build_authorized'])
        self.assertEqual(result['additional_image_gates'], ['actual boot and install'])

    def test_profile_cannot_convert_planning_into_seed_or_build_authorization(self):
        for field in ['final_install_seed', 'image_build_authorized']:
            self.profile[field] = True
            with self.subTest(field=field), self.assertRaises(AssertionError): self.run_plan()
            self.profile[field] = False
        before = self.run_plan()['profile_definition_sha256']
        self.profile['scope'] = 'Another explicitly preliminary analysis'
        self.assertNotEqual(self.run_plan()['profile_definition_sha256'], before)


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Fail-closed policy scope and coverage regression tests."""
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("policy_scope",
    ROOT / "scripts/plan-repository-policy.py")
planner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planner)


class HistoricalPolicyTests(unittest.TestCase):
    def test_active_only_delta_skips_closed_campaign_tests(self):
        paths = [
            "packages/plasma/kde-cli-tools/debian/tests/consumer",
            "scripts/hosted-ubuntu-guest-lane.sh",
            "manifests/desktop-stack.json",
        ]
        self.assertFalse(planner.historical_required(paths))

    def test_fail_closed_on_unknown_and_historical(self):
        for paths in [[], ["manifests/kde-tier3.json"],
                      ["manifests/evidence/round26/pass.json"],
                      ["scripts/validate_kde_tier3_kio_round25_remediation.py"],
                      [".github/workflows/repository-policy.yml"],
                      ["packages/frameworks/kio/debian/control"],
                      ["docs/project-instructions.md"],
                      ["scripts/hosted-ubuntu-guest-lane.sh", "scripts/unknown.py"]]:
            with self.subTest(paths=paths):
                self.assertTrue(planner.historical_required(paths))

    def test_full_on_non_pr_events_and_missing_evidence(self):
        self.assertTrue(planner.choose("push", "", "", "", "", "")[0])
        self.assertTrue(planner.choose("workflow_dispatch", "", "", "", "", "")[0])
        with mock.patch.object(planner, "git_delta", return_value=None):
            self.assertTrue(planner.choose("pull_request", "synchronize", "", "", "", "")[0])

    def test_exact_synchronize_delta_can_skip(self):
        with mock.patch.object(planner, "git_delta",
                               return_value=["scripts/hosted-ubuntu-guest-lane.sh"]):
            self.assertFalse(planner.choose("pull_request", "synchronize",
                                             "a" * 40, "b" * 40, "", "")[0])

    def test_every_historical_step_is_guarded_not_deleted(self):
        content = (ROOT / ".github/workflows/repository-policy.yml").read_text()
        before = content.index("- name: Validate KDE Frameworks Tier 1 manifest")
        after = content.index("- name: Verify runner and Ubuntu Qt candidate")
        historical = content[before:after]
        self.assertGreaterEqual(historical.count("- name: "), 80)
        self.assertEqual(historical.count("- name: "),
                         historical.count("if: steps.policy_scope.outputs.historical == 'true'"))
        self.assertIn("run: python3 scripts/validate_kde_tier3_kio_round26_remediation.py", historical)
        self.assertNotIn("if: steps.policy_scope.outputs.historical == 'true'",
                         content[after:])
        self.assertIn("run: python3 scripts/validate_plasma_package_build.py",
                      content[:before])


if __name__ == "__main__":
    unittest.main()

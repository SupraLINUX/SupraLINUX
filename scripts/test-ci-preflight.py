#!/usr/bin/env python3
"""Regression checks for syntax coverage, active routing and artifact identity."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class PreflightTests(unittest.TestCase):
    def test_syntax_checks_later_files_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "manifests").mkdir()
            (root / "scripts/a.sh").write_text("true\n")
            (root / "scripts/z.sh").write_text("if then\n")
            (root / "scripts/b.py").write_text("x = 1\\ny = 2\n")
            (root / "manifests/a.json").write_text('{"state":"PASS","state":"FAIL"}')
            errors, _ = module("check-source-syntax").check(root)
            self.assertEqual(len(errors), 3)

    def test_closed_work_and_documentation_do_not_reopen_campaigns(self):
        planner = module("plan-pr-ci")
        active = {"execution_authorized": True, "status": "level0-materialization-pending"}
        for paths in (["docs/plasma-level0.md"], ["manifests/kde-tier3-kio-round25-remediation.json"]):
            result = planner.plan(paths, active)
            self.assertFalse(result["run_plasma_lane"])
            self.assertFalse(result["run_qt_provider"])
        self.assertTrue(planner.plan(["scripts/validate_kde_plasma_level0.py"], active)["run_plasma_lane"])
        self.assertFalse(planner.plan(["manifests/kde-plasma.json"], {"execution_authorized": False})["run_plasma_lane"])
        self.assertTrue(planner.plan([], active, qt_changed=True)["run_qt_provider"])

    def test_milestone_rejects_other_or_unspecified_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "manifests").mkdir()
            script = root / "scripts/plan-frameworks-milestone.py"
            script.write_bytes((ROOT / "scripts/plan-frameworks-milestone.py").read_bytes())
            dag = {"frameworks_series": "6.30.0", "nodes": {f"node{i}": {
                "state": "PASS", "package_version": "6.30.0-1", "evidence": [{
                    "result": "PASS", "attempted_package_version": "6.30.0-1",
                    "workflow_run": i + 1, "artifact_id": i + 1, "artifact_sha256": "a" * 64,
                }],
            } for i in range(65)}}
            path = root / "manifests/kde-dag.json"
            for version, eligible, expected in (("6.30.0-1", True, 0), ("6.29.0-1", True, 1), (None, True, 1), ("6.30.0-1", False, 1)):
                evidence = dag["nodes"]["node0"]["evidence"][0]
                evidence["attempted_package_version"] = version
                evidence["downstream_eligible"] = eligible
                path.write_text(json.dumps(dag))
                result = subprocess.run(["python3", str(script)], capture_output=True)
                self.assertEqual(result.returncode, expected)

    def test_artifact_bytes_and_source_version_are_checked(self):
        inspector = module("retain-package-artifacts")
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "test.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("sample.changes", "Source: sample\nVersion: 1\n")
            item = {"node": "sample", "package_version": "2",
                    "artifact_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
            with self.assertRaisesRegex(ValueError, "does not identify"):
                inspector.inspect(archive, item, "sample")
            item["artifact_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                inspector.inspect(archive, item, "sample")

    def test_release_fingerprint_must_belong_to_valid_signature(self):
        materializer = module("run-kde-plasma-level0-materialization")
        expected = materializer.EXPECTED_FPR
        signature = f"[GNUPG:] VALIDSIG {'A' * 40} 2026-10-04 1 0 4 0 1 10 00 {expected}"
        self.assertTrue(materializer.valid_release_signature(signature))
        unrelated = signature.replace(expected, 'B' * 40) + f"\nExpected key: {expected}"
        self.assertFalse(materializer.valid_release_signature(unrelated))
        self.assertEqual(materializer.check_signing_key(), [expected])
        with self.assertRaisesRegex(ValueError, "expected primary fingerprint"):
            materializer.check_signing_key(ROOT / "packages/kde/karchive/debian/upstream/signing-key.asc")


if __name__ == "__main__":
    unittest.main()

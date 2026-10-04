#!/usr/bin/env python3
"""Regression checks for syntax coverage, active routing and artifact identity."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
import zipfile
import hashlib
import os
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

    def test_milestone_cache_returns_only_path_and_restores_without_token(self):
        builder = (ROOT / "scripts/build-frameworks-milestone-image.sh").read_text()
        function = builder.split("download_artifact() {", 1)[1].split("\n}\n", 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "archive/sha256"
            archive.mkdir(parents=True)
            cache = root / "cache"
            cache.mkdir()
            payload = b"retained bytes"
            digest = hashlib.sha256(payload).hexdigest()
            retained = archive / f"{digest}.zip"
            retained.write_bytes(payload)
            wrapper = root / "reuse.sh"
            wrapper.write_text("set -euo pipefail\n" + "download_artifact() {" + function +
                               "\n}\n" + 'download_artifact sample 123 "$EXPECTED"\n')
            environment = {**os.environ, "DOWNLOAD_DIR": str(cache),
                           "ARTIFACT_ARCHIVE": str(archive.parent), "TOKEN": "", "EXPECTED": digest}
            for _ in range(2):
                result = subprocess.run(["bash", str(wrapper)], env=environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, str(cache / "123.zip") + "\n")
            (cache / "123.zip").unlink()
            retained.write_bytes(b"tampered")
            result = subprocess.run(["bash", str(wrapper)], env=environment, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_candidate_versions_preserve_epoch_and_supersede_ubuntu(self):
        planner = module("assign-plasma-candidate-versions")
        self.assertEqual(planner.candidate_version("6.7.5", "4:6.6.4-0ubuntu1", ["4:6.6.4-0ubuntu1"]), "4:6.7.5-0supralinux1")
        candidate = planner.candidate_version("6.7.5", "6.7.5-0ubuntu1", ["6.7.5-0ubuntu1", "6.7.5-0ubuntu2"])
        self.assertTrue(planner.compare(candidate, "gt", "6.7.5-0ubuntu2"))
        with self.assertRaisesRegex(ValueError, "transition review"):
            planner.candidate_version("6.7.5", "4:6.8.0-0ubuntu1", ["4:6.8.0-0ubuntu1"])

    def test_lifecycle_rejects_evidence_tampering_and_lost_epoch(self):
        lifecycle = module("plasma_lifecycle")
        # Closed evidence is a fixture; future live phase changes must not break this test.
        result_payload = (ROOT / "manifests/evidence/kde-plasma-level0-materialization-result.json").read_bytes()
        version_payload = (ROOT / "manifests/evidence/kde-plasma-level0-candidate-versions.json").read_bytes()
        result = json.loads(result_payload)
        versions = {node["node"]: node for node in json.loads(version_payload)["nodes"]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "result.json").write_bytes(result_payload)
            (root / "versions.json").write_bytes(version_payload)
            boundary = {"execution_authorized": False, "materialization_authorized": False,
                        "package_execution_authorized": False, "consumes_package_attempt": False,
                        "canonical_package_state_effect": "none", "next_gate": "plasma-level0-packaging-preparation"}
            evidence = {"result_path": "result.json", "result_json_sha256": hashlib.sha256(result_payload).hexdigest(),
                        "artifact_digest": "sha256:" + "a" * 64, "workflow_head_sha": result["github"]["source_commit"],
                        "workflow_run_id": int(result["github"]["workflow_run_id"]), "inputs_sha256": result["inputs_sha256"]}
            materialization = {**boundary, "state": "PASS", "evidence": evidence,
                               "source_authority": {"required_primary_fingerprint": result["nodes"][0]["upstream"]["required_primary_fingerprint"]}}
            plasma = {"planning": {**boundary, "status": "level0-packaging-preparation-pending",
                                   "phase": "level0-packaging-preparation", "package_preparation_authorized": True}}
            level = {**boundary, "state": "candidate-versions-assigned", "selected_nodes": list(versions),
                     "version_policy": {"candidate_version_assignment": "PASS"},
                     "candidate_versions_evidence": {"path": "versions.json", "sha256": hashlib.sha256(version_payload).hexdigest()},
                     "nodes": {node["node"]: {"state": "packaging-preparation-pending", "package_execution_authorized": False,
                               "upstream_source_sha256": node["upstream"]["sha256"], "upstream_version": node["upstream"]["version"],
                               "packaging_reference": {"source_package": node["ubuntu_reference"]["source_package"]},
                               "candidate_package_version": versions[node["node"]]["candidate_package_version"]} for node in result["nodes"]}}
            self.assertEqual(lifecycle.validate(root, plasma, level, materialization), [])
            node = next(node for node in level["nodes"].values() if ":" in node["candidate_package_version"])
            version = node["candidate_package_version"]
            node["candidate_package_version"] = version.split(":", 1)[1]
            self.assertTrue(any("preserved Ubuntu epoch" in error for error in lifecycle.validate(root, plasma, level, materialization)))
            node["candidate_package_version"] = version
            evidence["result_json_sha256"] = "0" * 64
            self.assertTrue(any("retained result digest" in error for error in lifecycle.validate(root, plasma, level, materialization)))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Validate reviewed package scope, frozen inputs and any retained KVM closure."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare", ROOT / "scripts/prepare-plasma-package.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def validate():
    campaign = json.loads((ROOT / "manifests/kde-plasma-package-build.json").read_text())
    planning = json.loads((ROOT / "manifests/kde-plasma.json").read_text())["planning"]
    level = json.loads((ROOT / "manifests/kde-plasma-level0.json").read_text())
    assert campaign["role"] == "reviewed-plasma-package-build"
    scope = campaign["authorized_nodes"]
    assert scope == planning["authorized_package_nodes"] == level["authorized_package_nodes"]
    assert campaign["package_execution_authorized"] is bool(scope)
    assert campaign["runner_class"] == "supralinux-kvm-ubuntu-26.04-ephemeral"
    assert set(campaign["nodes"]) <= set(level["selected_nodes"])
    for incident in campaign.get("infrastructure_incidents", []):
        assert incident["state"] == "INFRA_INVALID"
        assert incident["consumes_package_attempt"] is False and incident["package_execution_started"] is False
        payload = (ROOT / incident["result_path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == incident["result_sha256"]
        assert json.loads(payload)["exit_code"] != 0
        assert incident["cause"] and incident["repair"]
    if campaign.get("execution_checkpoint", "none") != "none":
        assert campaign["execution_checkpoint"] == "frameworks-6.30-pass"
        checkpoints = json.loads((ROOT / "manifests/execution-checkpoints.json").read_text())
        assert checkpoints["checkpoints"][campaign["execution_checkpoint"]]["state"] == "PASS"
    material = json.loads((ROOT / "manifests/evidence/kde-plasma-level0-materialization-result.json").read_text())
    sources = {node["node"]: node for node in material["nodes"]}
    for name, record in campaign["nodes"].items():
        prepare.contract(name)
        assert record["upstream_sha256"] == sources[name]["upstream"]["sha256"]
        assert record["signature_sha256"] == sources[name]["upstream"]["signature_sha256"]
        assert record["packaging_reference_sha256"] == sources[name]["ubuntu_reference"]["debian_tree_tar_sha256"]
        assert record["packaging_reference_version"] == sources[name]["ubuntu_reference"]["source_version"]
        assert all(record["review"].values()), "Individual packaging review missing"
        for predecessor, inputs in record.get("frameworks_predecessors", {}).items():
            dag = json.loads((ROOT / "manifests/kde-dag.json").read_text())["nodes"][predecessor]
            assert dag["state"] == "PASS" and dag["package_version"] == inputs["version"]
            assert dag["source_package"] == inputs["source_package"]
            assert inputs["binaries"] and all(binary["package"] in dag["binary_packages"] for binary in inputs["binaries"])
        for attempt in record["attempts"]:
            payload = (ROOT / attempt["result_path"]).read_bytes()
            assert hashlib.sha256(payload).hexdigest() == attempt["result_sha256"], "Attempt evidence changed"
            result = json.loads(payload)
            if result.get("kind") == "host-recovered-interruption-observation":
                assert result["state"] == "INFRA_INVALID" and result["runner_result_present"] is False
                assert attempt["artifact_origin"] == "sealed-host-recovery" and attempt["artifact_id"] is None
                assert result["downstream_eligible"] is False and result["archive_sha256"] == attempt["artifact_sha256"]
                directory = (ROOT / attempt["result_path"]).parent
                host_bytes = (directory / "host-result.json").read_bytes()
                assert hashlib.sha256(host_bytes).hexdigest() == result["host_result_sha256"]
                assert json.loads(host_bytes)["exit_code"] != 0
                assert hashlib.sha256((directory / "build-contract.json").read_bytes()).hexdigest() == result["contract_sha256"]
            if attempt.get("verification_diagnosis_path"):
                diagnostic_bytes = (ROOT / attempt["verification_diagnosis_path"]).read_bytes()
                assert hashlib.sha256(diagnostic_bytes).hexdigest() == attempt["verification_diagnosis_sha256"]
                diagnostic = json.loads(diagnostic_bytes)
                assert diagnostic["kind"] == "verification-gate-false-negative"
                assert diagnostic["original_result_sha256"] == attempt["result_sha256"]
                assert attempt["state"] == "INFRA_INVALID" and result["state"] == attempt["original_state"] == "FAIL"
                assert result["stage"] == "upstream-package-tests" and result["sbuild_result"] == "PASS"
                assert diagnostic["upstream_tests"]["state"] == "PASS"
                assert diagnostic["upstream_tests"]["expected_tests"] == record["upstream_tests"]
            else:
                assert result["state"] == attempt["state"]
            assert result["node"] == name
            assert result["source_commit"] == attempt["source_commit"]
            assert result["workflow_run_id"] == str(attempt["workflow_run_id"])
            assert result["package_attempt_consumed"] is attempt["package_attempt_consumed"]
            assert all(result[key] == attempt[key] for key in ["sbuild_result", "lintian_result", "autopkgtest_result"])
            if attempt["state"] == "PASS":
                assert result["version"] == record["version"]
            else:
                assert attempt.get("cause"), "Unexplained attempt failure"
        executables = record["required_executable_files"]
        assert "rules" in executables and (ROOT / record["packaging_path"] / "tests/control").is_file()
        for script in executables:
            assert os.access(ROOT / record["packaging_path"] / script, os.X_OK), f"Non-executable packaging script: {script}"
        if record.get("baseline_setup_script"):
            assert record["baseline_setup_script"] in executables
            assert record["baseline_setup_script"].startswith("tests/")
        if record.get("upstream_tests"):
            assert len(set(record["upstream_tests"])) == len(record["upstream_tests"])
        if record.get('sbuild_rootfs_policy'):
            policy = record['sbuild_rootfs_policy']
            assert policy['kind'] == 'immutable-bare-milestone'
            assert campaign['execution_checkpoint'] == 'frameworks-6.30-pass'
            assert len(policy['sha256']) == 64 and all(c in '0123456789abcdef' for c in policy['sha256'])
            assert policy['suites'] == ['resolute','resolute-updates','resolute-security']
        if name in scope:
            assert record["state"] == "build-pending" and campaign["state"] == "execution-authorized"
        if record["state"] == "PASS":
            evidence = record["evidence"]
            payload = (ROOT / evidence["result_path"]).read_bytes()
            assert hashlib.sha256(payload).hexdigest() == evidence["result_sha256"]
            result = json.loads(payload)
            assert result["node"] == name and result["version"] == record["version"]
            assert result["state"] == "PASS" and result["authoritative"] is True
            assert result["source_commit"] == evidence["source_commit"]
            assert result["workflow_run_id"] == str(evidence["workflow_run_id"])
            assert all(result[key] == "PASS" for key in ["sbuild_result", "lintian_result", "autopkgtest_result"])
            assert result["system_test_acceleration"] == "kvm-required"
            built_contract = json.loads((ROOT / evidence["contract_path"]).read_text())
            assert hashlib.sha256((ROOT / evidence["contract_path"]).read_bytes()).hexdigest() == result["files_sha256"]["build-contract.json"]
            assert built_contract["nodes"][name]["packaging_sha256"] == record["packaging_sha256"]
            assert record["attempts"][-1]["state"] == "PASS" and result["package_attempt_consumed"] is True
            retention = evidence["local_retention"]
            if evidence.get('hidden_file_export_recovery'):
                recovery = evidence['hidden_file_export_recovery']
                proof_bytes = (ROOT/recovery['proof_path']).read_bytes()
                assert hashlib.sha256(proof_bytes).hexdigest() == recovery['proof_sha256']
                proof = json.loads(proof_bytes)
                assert proof['kind'] == 'sealed-host-hidden-file-export-recovery'
                assert proof['actions_artifact_id'] == evidence['artifact_id']
                assert proof['actions_artifact_sha256'] == evidence['artifact_sha256']
                assert proof['host_evidence_manifest_sha256'] == evidence['host_evidence_manifest_sha256']
                assert proof['offline_restore_verified'] is True and proof['original_actions_archive_unchanged'] is True
                assert proof['files_sha256'] and proof['supplement_path'].startswith(retention['archive_root']+'/')
                assert all(any(part.startswith('.') for part in Path(name).parts) and
                           result['files_sha256'][name] == digest for name,digest in proof['files_sha256'].items())
            assert all(retention[key] is True for key in ["source_complete", "changes_complete", "buildinfo_verified",
                                                         "artifact_zip_sha256_verified", "offline_restore_verified"])
            assert retention["requires_github_for_restore"] is False
            assert hashlib.sha256((ROOT / retention["plan_path"]).read_bytes()).hexdigest() == retention["plan_sha256"]
            if record.get("upstream_tests"):
                test_bytes = (ROOT / evidence["upstream_tests_path"]).read_bytes()
                assert hashlib.sha256(test_bytes).hexdigest() == evidence["upstream_tests_sha256"]
                assert evidence["upstream_tests_sha256"] == result["files_sha256"]["upstream-tests.json"]
                upstream = json.loads(test_bytes)
                assert upstream["state"] == "PASS" and upstream["expected_tests"] == record["upstream_tests"]
            if record.get("frameworks_predecessors"):
                assert "predecessor-inputs.json" in result["files_sha256"]
                assert "cache-probe/sbuild.log" in result["files_sha256"]
                assert "cache-probe/predecessor-buildinfo.txt" in result["files_sha256"]
                probe_bytes = (ROOT / evidence["cache_probe_result_path"]).read_bytes()
                assert hashlib.sha256(probe_bytes).hexdigest() == evidence["cache_probe_result_sha256"]
                assert evidence["cache_probe_result_sha256"] == result["files_sha256"]["cache-probe/result.json"]
                probe = json.loads(probe_bytes)
                assert probe["state"] == "PASS" and probe["consumes_package_attempt"] is False
            if record.get('sbuild_rootfs_policy'):
                rootfs_bytes = (ROOT/evidence['rootfs_admission_path']).read_bytes()
                assert hashlib.sha256(rootfs_bytes).hexdigest() == evidence['rootfs_admission_sha256']
                assert evidence['rootfs_admission_sha256'] == result['files_sha256']['rootfs-admission.json']
                rootfs = json.loads(rootfs_bytes)
                assert rootfs['state'] == 'PASS' and rootfs['base_sha256'] == record['sbuild_rootfs_policy']['sha256']
                assert rootfs['frameworks_and_qt_sdk_preinstalled'] is False and rootfs['package_attempt_consumed'] is False
                assert rootfs['requires_sbuild_apt_update_and_distupgrade'] is True
                assert rootfs['suites'] == record['sbuild_rootfs_policy']['suites']
    workflow = (ROOT / ".github/workflows/authoritative-plasma-package-build.yml").read_text()
    assert "github.event.pull_request.head.sha || github.sha" in workflow, "Workflow must bind the PR head"
    assert "ci:plasma-package-build" in workflow and "types: [labeled]" in workflow
    print(f"Reviewed Plasma package build: PASS; authorized={scope}; states=" +
          str({node: record["state"] for node, record in campaign["nodes"].items()}))


if __name__ == "__main__":
    validate()

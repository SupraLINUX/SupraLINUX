#!/usr/bin/env python3
"""Validate reviewed package scope, frozen inputs and any retained KVM closure."""
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
from plasma_lifecycle import verify_package_hold

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare", ROOT / "scripts/prepare-plasma-package.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
repair_spec = importlib.util.spec_from_file_location('effective_frameworks', ROOT/'scripts/frameworks-revalidation-inputs.py')
repairs = importlib.util.module_from_spec(repair_spec)
repair_spec.loader.exec_module(repairs)
proof_spec = importlib.util.spec_from_file_location('input_evidence', ROOT/'scripts/validate_package_revalidation.py')
input_evidence = importlib.util.module_from_spec(proof_spec)
proof_spec.loader.exec_module(input_evidence)
testing_spec = importlib.util.spec_from_file_location('baseline_testing', ROOT/'scripts/plasma-package-testing.py')
testing = importlib.util.module_from_spec(testing_spec)
testing_spec.loader.exec_module(testing)
supplementary_spec = importlib.util.spec_from_file_location('supplementary_inputs', ROOT/'scripts/supplementary-package-inputs.py')
supplementary = importlib.util.module_from_spec(supplementary_spec)
supplementary_spec.loader.exec_module(supplementary)


def validate():
    campaign = json.loads((ROOT / "manifests/kde-plasma-package-build.json").read_text())
    planning = json.loads((ROOT / "manifests/kde-plasma.json").read_text())["planning"]
    level = json.loads((ROOT / "manifests/kde-plasma-level0.json").read_text())
    providers = json.loads((ROOT/'manifests/kde-plasma-supplementary-providers.json').read_text())['nodes']
    assert campaign["role"] == "reviewed-plasma-package-build"
    scope = campaign["authorized_nodes"]
    level_scope = [name for name in scope if name in level['selected_nodes']]
    assert level_scope == planning["authorized_package_nodes"] == level["authorized_package_nodes"]
    assert len(scope) <= 1 and all(name in campaign['nodes'] for name in scope)
    assert campaign["package_execution_authorized"] is bool(scope)
    assert campaign["runner_class"] == "supralinux-kvm-ubuntu-26.04-ephemeral"
    assert set(campaign["nodes"]) <= set(level["selected_nodes"]) | set(providers)
    assert campaign.get('execution_mode', 'build') in {'preflight', 'build'}
    effective = repairs.effective_nodes(json.loads((ROOT/'manifests/kde-dag.json').read_text()))
    historical = repairs.effective_nodes(json.loads((ROOT/'manifests/kde-dag.json').read_text()), historical=True)
    input_certified = set()
    for link in campaign.get('package_input_certifications', []):
        proof, result, frozen, directory = input_evidence.verified_evidence(link)
        assert proof['scope'] == 'reviewed-package-input-preflight' and proof['state'] == 'PASS'
        assert proof['package_attempt_consumed'] is False and result['stage'] == 'reviewed-package-preflight-complete'
        assert frozen['execution_mode'] == 'preflight' and frozen['role'] == campaign['role']
        assert all(result[key] == 'not-run' for key in ['sbuild_result', 'lintian_result', 'autopkgtest_result'])
        probe = json.loads((directory/'cache-probe/result.json').read_text())
        assert probe['predecessors_installed_at_reviewed_versions'] is True
        expected = json.loads((directory/'cache-probe/installed-predecessor-contract.json').read_text())
        built = frozen['nodes'][proof['node']]
        wanted = {(binary['package'], predecessor['source_package'], predecessor['version'], binary['architecture'])
                  for key in ['frameworks_predecessors', 'supplementary_predecessors']
                  for predecessor in built.get(key, {}).values() for binary in predecessor['binaries']}
        assert {(item['package'], item['source_package'], item['version'], item['architecture']) for item in expected} == wanted
        if not link.get('applicable', True):
            assert link['inapplicability_reason']
        if link.get('applicable', True) and proof['node'] in scope:
            record = campaign['nodes'][proof['node']]
            assert proof['packaging_sha256'] == record['packaging_sha256']
            assert proof['frameworks_predecessors'] == record['frameworks_predecessors']
            assert proof.get('supplementary_predecessors', {}) == record.get('supplementary_predecessors', {})
            for file, digest in proof['inputs_sha256'].items():
                assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest() == digest
            input_certified.add(proof['node'])
    for incident in campaign.get('package_input_incidents', []):
        proof, result, _, _ = input_evidence.verified_evidence(incident)
        assert proof['state'] == result['state'] == 'INFRA_INVALID' and proof['package_attempt_consumed'] is False
        assert incident['cause'] and incident['repair']
    for certification in campaign.get("infrastructure_certifications", []):
        path = ROOT / certification["path"]
        payload = path.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == certification["sha256"]
        proof = json.loads(payload)
        assert proof["state"] == "PASS" and proof["scope"] in {
            "active-bound-monitor-read-outage-recovery", "large-reviewed-autopkgtest-baseline-transport",
            "reviewed-ubuntu-baseline-preflight"}
        assert proof["consumes_package_attempt"] is False and proof["package_execution_started"] is False
        assert proof["canonical_package_state_effect"] == "none"
        for name, digest in proof["files_sha256"].items():
            file = path.parent / name
            assert file.resolve().is_relative_to(path.parent.resolve())
            assert hashlib.sha256(file.read_bytes()).hexdigest() == digest
        assert proof["files_sha256"]["evidence-sha256.txt"] == proof["host_evidence_seal_sha256"]
        host = json.loads((path.parent / "host-result.json").read_text())
        job = json.loads((path.parent / "workflow-job.json").read_text())
        assert host["exit_code"] == 0 and job["conclusion"] == "success"
        assert str(job["run_id"]) == host["workflow_run_id"] == str(proof["workflow_run_id"])
        assert job["id"] == proof["workflow_job_id"] and job["head_sha"] == proof["source_commit"]
        if proof["scope"] == "active-bound-monitor-read-outage-recovery":
            assert proof["injected_monitor_read_failures"] > 0 and proof["observed_live_guest_after_read_failure"] is True
            assert json.loads((path.parent / "monitor-guest-process.json").read_text())["exited"] is False
        else:
            result = json.loads((path.parent / "result.json").read_text())
            assert result["state"] == "PASS" and result["exit_code"] == 0
            assert result["source_commit"] == proof["source_commit"] and result["workflow_run_id"] == str(proof["workflow_run_id"])
            assert result["inputs_sha256"] == proof["inputs_sha256"]
            assert result["package_execution_started"] is False and result["consumes_package_attempt"] is False
            assert result["system_test_acceleration"] == "kvm-required"
            assert result["files_sha256"]["autopkgtest/summary"] == proof["files_sha256"]["summary"]
            steps = {step["name"]: step for step in job["steps"]}
            if proof["scope"] == "large-reviewed-autopkgtest-baseline-transport":
                assert result["setup_payload_bytes"] > 4096 and result["setup_max_line_bytes"] < 512
                assert (path.parent / "summary").read_text().split() == ["preserved-setup", "PASS"]
                assert steps["Verify reviewed setup transport through autopkgtest QEMU"]["conclusion"] == "success"
            else:
                assert result["node"] == proof["node"] and result["candidate_installed"] is proof["candidate_installed"] is False
                assert (path.parent / "summary").read_text().split() == ["reviewed-baseline", "PASS"]
                assert steps["Execute current reviewed Ubuntu baseline before candidate build"]["conclusion"] == "success"
                reviewed = json.loads((path.parent / "reviewed-inputs.json").read_text())
                setup_path = reviewed["packaging_path"] + "/" + reviewed["baseline_setup_script"]
                assert proof["files_sha256"]["baseline-setup"] == result["inputs_sha256"][setup_path]
                assert reviewed["packaging_sha256"][reviewed["baseline_setup_script"]] == result["inputs_sha256"][setup_path]
        if certification["applicable"]:
            for name, digest in proof["inputs_sha256"].items():
                assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, "Recertify changed monitor inputs"
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
        if record['state'] == 'compatibility-review-required':
            verify_package_hold(ROOT, name, record, scope)
        else:
            assert 'compatibility_hold' not in record, 'Resolve a hold explicitly before changing package state'
        if record.get('source_scope') == 'plasma-supplementary-provider':
            assert name in providers and name not in level['selected_nodes']
            assert providers[name]['package_record'] == name
            assert providers[name]['package_execution_authorized'] is (name in scope)
            if name in scope and campaign['execution_mode'] == 'build':
                assert name in input_certified, 'Certify supplementary package inputs before its first Attempt'
        else:
            assert name in sources
            assert record["upstream_sha256"] == sources[name]["upstream"]["sha256"]
            assert record["signature_sha256"] == sources[name]["upstream"]["signature_sha256"]
            assert record["packaging_reference_sha256"] == sources[name]["ubuntu_reference"]["debian_tree_tar_sha256"]
            assert record["packaging_reference_version"] == sources[name]["ubuntu_reference"]["source_version"]
        assert all(record["review"].values()), "Individual packaging review missing"
        assert not (set(record.get('frameworks_predecessors', {})) & set(record.get('supplementary_predecessors', {})))
        for predecessor, requested in record.get('supplementary_predecessors', {}).items():
            supplementary.checked_contract(predecessor, requested, historical=record['state']=='PASS', consumer=name)
            if name in scope and campaign['execution_mode'] == 'build':
                assert name in input_certified, 'Certify supplementary artifact transport before the package Attempt'
        for predecessor, inputs in record.get("frameworks_predecessors", {}).items():
            original = historical.get(predecessor)
            canonical = original if original and record['state'] == 'PASS' and inputs['version'] == original['package_version'] else effective[predecessor]
            repairs.check_requested(predecessor, inputs, canonical)
            if name in scope and (canonical.get('revalidation') or canonical.get('retained_support')) and campaign.get('execution_mode', 'build') == 'build':
                assert name in input_certified, 'Certify repaired input transport before the investigated package Attempt'
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
                assert diagnostic["original_result_sha256"] == attempt["result_sha256"]
                assert attempt["state"] == "INFRA_INVALID" and result["state"] == attempt["original_state"] == "FAIL"
                if diagnostic["kind"] == "verification-gate-false-negative":
                    assert result["stage"] == "upstream-package-tests" and result["sbuild_result"] == "PASS"
                    assert diagnostic["upstream_tests"]["state"] == "PASS"
                    assert diagnostic["upstream_tests"]["expected_tests"] == record["upstream_tests"]
                elif diagnostic['kind'] == 'build-predecessor-verification-false-negative':
                    assert result['stage'] == 'artifact-capture' and result['sbuild_result'] == 'PASS'
                    assert result['lintian_result'] == result['autopkgtest_result'] == 'not-run'
                    assert diagnostic['candidate_outputs_retained'] is True
                    assert diagnostic['package_result'] == 'incomplete; requires remaining package tests'
                    directory = (ROOT/attempt['verification_diagnosis_path']).parent
                    for filename, digest in diagnostic['files_sha256'].items():
                        path = directory/filename
                        assert path.resolve().is_relative_to(directory.resolve())
                        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
                    assert result['files_sha256'][diagnostic['original_buildinfo_path']] == diagnostic['files_sha256']['package.buildinfo']
                    built = json.loads((directory/'build-contract.json').read_text())['nodes'][name]
                    assert built['packaging_sha256']['control'] == diagnostic['files_sha256']['source-control']
                    verifier_spec = importlib.util.spec_from_file_location('actual_build_inputs', ROOT/'scripts/verify-reviewed-build-predecessors.py')
                    verifier = importlib.util.module_from_spec(verifier_spec)
                    verifier_spec.loader.exec_module(verifier)
                    checked = verifier.verify(built, (directory/'source-control').read_text(), (directory/'package.buildinfo').read_text())
                    assert checked == json.loads((directory/'build-predecessors.json').read_text())
                    assert checked['available_predecessors_not_installed']
                elif diagnostic["kind"] == "autopkgtest-dbus-stderr-policy-false-negative":
                    assert result["stage"] == "autopkgtest-qemu" and result["exit_code"] == 4
                    assert result["sbuild_result"] == result["lintian_result"] == "PASS"
                    assert diagnostic["package_result"] == "incomplete; repaired harness revalidation required"
                    directory = (ROOT / attempt["verification_diagnosis_path"]).parent
                    for file_name, digest in diagnostic["files_sha256"].items():
                        path = directory / file_name
                        assert path.resolve().is_relative_to(directory.resolve())
                        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
                        assert result["files_sha256"][file_name] == digest
                    summary = (directory / "autopkgtest/summary").read_text().splitlines()
                    assert len(summary) == len(diagnostic["tests"])
                    for test in diagnostic["tests"]:
                        assert any(line.split()[:3] == [test, "FAIL", "stderr:"] for line in summary)
                        stdout = (directory / f"autopkgtest/{test}-stdout").read_text()
                        assert all(marker in stdout for marker in diagnostic["required_client_success_markers"])
                        stderr = (directory / f"autopkgtest/{test}-stderr").read_text().splitlines()
                        assert len(stderr) == 2 and all(line.startswith("dbus-daemon[") for line in stderr)
                        assert "Activating service name='" + diagnostic["dbus_service"] + "'" in stderr[0]
                        assert "Successfully activated service '" + diagnostic["dbus_service"] + "'" in stderr[1]
                else:
                    assert diagnostic["kind"] == "infrastructure-testbed-setup-transport-failure"
                    assert result["stage"] == "autopkgtest-qemu" and result["sbuild_result"] == result["lintian_result"] == "PASS"
                    assert diagnostic["state"] == "INFRA_INVALID" and diagnostic["downstream_eligible"] is False
                    directory = (ROOT / attempt["verification_diagnosis_path"]).parent
                    for file_name, digest in diagnostic["files_sha256"].items():
                        path = directory / file_name
                        assert path.resolve().is_relative_to(directory.resolve())
                        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
                    assert diagnostic["files_sha256"]["baseline-setup-original"] == diagnostic["original_setup_sha256"]
                    built = json.loads((directory / "build-contract.json").read_text())["nodes"][name]
                    assert built["packaging_sha256"][diagnostic["baseline_setup_script"]] == diagnostic["original_setup_sha256"]
                    assert diagnostic["original_setup_encoded_bytes"] > 4096
                    old = json.loads((directory / "serial-original.json").read_text())
                    repaired = json.loads((directory / "serial-repaired.json").read_text())
                    assert old["shell_status"] == "0" and old["baseline_marker_present"] is False and old["wire_max_line_bytes"] > 4096
                    assert repaired["shell_status"] == "0" and repaired["baseline_marker_present"] is True and repaired["wire_max_line_bytes"] < 1024
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
        if record.get('baseline_setup_payload') is not None:
            assert record.get('baseline_setup_script') and record['baseline_setup_payload'] == 'reviewed-tests-tree'
            testing.reviewed_setup_files(ROOT, record)
        if record.get("baseline_preflight_required"):
            assert record.get("baseline_setup_script"), "Required baseline preflight lacks a reviewed setup"
        if record.get("upstream_tests"):
            assert len(set(record["upstream_tests"])) == len(record["upstream_tests"])
        backend = record.get('upstream_test_backend', 'ctest')
        assert backend in {'ctest', 'meson'}, 'Unknown upstream test backend'
        if backend == 'meson':
            assert record.get('upstream_tests'), 'Reviewed Meson tests required'
            assert re.fullmatch(r'[A-Za-z0-9_.+-]+', record.get('upstream_test_project', '')), 'Reviewed Meson project required'
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
            assert built_contract['nodes'][name].get('frameworks_predecessors', {}) == record.get('frameworks_predecessors', {})
            assert built_contract['nodes'][name].get('supplementary_predecessors', {}) == record.get('supplementary_predecessors', {})
            assert record["attempts"][-1]["state"] == "PASS" and result["package_attempt_consumed"] is True
            if record.get("baseline_preflight_required"):
                baseline_bytes = (ROOT / evidence["baseline_preflight_path"]).read_bytes()
                assert hashlib.sha256(baseline_bytes).hexdigest() == evidence["baseline_preflight_sha256"]
                assert evidence["baseline_preflight_sha256"] == result["files_sha256"]["ubuntu-baseline-preflight/result.json"]
                baseline = json.loads(baseline_bytes)
                assert baseline["state"] == "PASS" and baseline["exit_code"] == 0 and baseline["node"] == name
                assert baseline["source_commit"] == result["source_commit"] and baseline["workflow_run_id"] == result["workflow_run_id"]
                assert baseline["candidate_installed"] is baseline["consumes_package_attempt"] is baseline["package_execution_started"] is False
                assert baseline["system_test_acceleration"] == "kvm-required"
                testing.verify_baseline_input_hashes(record, baseline)
                assert all(result["files_sha256"]["ubuntu-baseline-preflight/" + file] == digest
                           for file, digest in baseline["files_sha256"].items())
            retention = evidence["local_retention"]
            if 'campaign_manifest_sha256' in built_contract:
                assert evidence.get('workflow_job_path') and evidence.get('host_result_path')
            if evidence.get('workflow_job_path') and evidence.get('artifact_origin') != 'sealed-host-package-export':
                job_bytes = (ROOT/evidence['workflow_job_path']).read_bytes()
                host_bytes = (ROOT/evidence['host_result_path']).read_bytes()
                assert hashlib.sha256(job_bytes).hexdigest() == evidence['workflow_job_sha256']
                assert hashlib.sha256(host_bytes).hexdigest() == evidence['host_result_sha256']
                job, host = json.loads(job_bytes), json.loads(host_bytes)
                assert job['id'] == evidence['workflow_job_id'] and job['head_sha'] == evidence['source_commit']
                assert str(job['run_id']) == host['workflow_run_id'] == result['workflow_run_id']
                assert job['status'] == 'completed' and job['conclusion'] == 'success' and host['exit_code'] == 0
                steps = {step['name']: step for step in job['steps']}
                assert all(steps[step]['conclusion'] == 'success' for step in
                           ['Run current reviewed package', 'Retain package sources, binaries and evidence'])
                seal = (ROOT/evidence['host_result_path']).parent/'host-evidence-sha256.txt'
                assert hashlib.sha256(seal.read_bytes()).hexdigest() == evidence['host_evidence_manifest_sha256']
            if evidence.get('artifact_origin') == 'sealed-host-package-export':
                assert evidence['artifact_id'] is None and evidence['actions_export_complete'] is False
                job_bytes = (ROOT/evidence['workflow_job_path']).read_bytes()
                host_bytes = (ROOT/evidence['host_result_path']).read_bytes()
                assert hashlib.sha256(job_bytes).hexdigest() == evidence['workflow_job_sha256']
                assert hashlib.sha256(host_bytes).hexdigest() == evidence['host_result_sha256']
                job,host = json.loads(job_bytes),json.loads(host_bytes)
                assert job['id'] == evidence['workflow_job_id'] and job['head_sha'] == evidence['source_commit']
                assert str(job['run_id']) == host['workflow_run_id'] == result['workflow_run_id']
                assert host['exit_code'] != 0 and result['exit_code'] == 0 and job['status'] == 'completed'
                steps = {step['name']:step for step in job['steps']}
                assert steps['Run current reviewed package']['conclusion'] == 'success'
                assert steps['Retain package sources, binaries and evidence']['conclusion'] != 'success'
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

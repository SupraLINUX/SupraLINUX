"""Current Plasma lifecycle checks, independent of closed planning snapshots."""
import hashlib
import json
import re
import subprocess


def validate(root, plasma, level, materialization):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    planning = plasma["planning"]
    phase = planning.get("status")
    phases = {
        "level0-materialization-pending": ("level0-materialization", "materialization-pending", "plasma-level0-materialization-evidence", True),
        "level0-packaging-preparation-pending": ("level0-packaging-preparation", "candidate-versions-assigned", "plasma-level0-packaging-preparation", False),
        "level0-package-build-pending": ("level0-package-build", "package-build-authorized", "plasma-level0-authoritative-package-build", False),
        "level0-package-build-complete": ("level0-package-build", "package-build-partial-PASS", "plasma-level0-remaining-packaging-preparation", False),
    }
    require(phase in phases, "unsupported current Plasma lifecycle state")
    if phase not in phases:
        return errors
    expected_phase, expected_level, gate, authorized = phases[phase]
    require(planning.get("phase") == expected_phase, "Plasma phase/status coherence")
    require(level.get("state") == expected_level, "Level definition/current phase coherence")
    package_authorized = phase == "level0-package-build-pending"
    for document in (planning, level, materialization):
        require(document.get("execution_authorized") is authorized, "current lane execution authorization")
        require(document.get("materialization_authorized") is authorized, "current materialization authorization")
        require(document.get("package_execution_authorized") is (package_authorized and document is not materialization), "phase-specific package execution authorization")
        require(document.get("consumes_package_attempt") is False, "planning does not consume package Attempts")
        require(document.get("canonical_package_state_effect") == "none", "planning cannot change canonical package state")
    require(planning.get("next_gate") == gate and level.get("next_gate") == gate, "current next-gate coherence")
    require(materialization.get("state") == ("execution-authorized" if authorized else "PASS"), "materialization lifecycle state")
    selected = level["selected_nodes"]
    scope = planning.get("authorized_package_nodes", [])
    require(bool(scope) is package_authorized and len(scope) == len(set(scope)) and set(scope) <= set(selected), "exact authorized package scope")
    require(level.get("authorized_package_nodes", []) == scope, "Level/live package scope coherence")
    require(all(node.get("package_execution_authorized") is (name in scope) for name, node in level["nodes"].items()), "per-node package execution authorization")
    if authorized:
        require(all(node.get("state") == "materialization-pending" and node.get("candidate_package_version") is None
                    for node in level["nodes"].values()), "candidate versions remain deferred until evidence closure")
        require(level["version_policy"]["candidate_version_assignment"] == "deferred-until-reference-materialization", "pending version assignment")
        return errors
    evidence = materialization.get("evidence", {})
    path = root / evidence.get("result_path", "")
    require(path.is_file(), "retained materialization result missing")
    require(bool(re.fullmatch(r"[0-9a-f]{64}", evidence.get("artifact_digest", "").removeprefix("sha256:"))), "artifact digest")
    if not path.is_file():
        return errors
    require(hashlib.sha256(path.read_bytes()).hexdigest() == evidence.get("result_json_sha256"), "retained result digest")
    result = json.loads(path.read_text())
    require(result.get("package_execution_started") is False and result.get("consumes_package_attempt") is False,
            "materialization evidence cannot claim package execution")
    require(result.get("state") == "PASS" and result.get("counts") == {"PASS": len(selected), "INFRA_INVALID": 0, "REVIEW_REQUIRED": 0}, "materialization PASS scope")
    require(result.get("github", {}).get("source_commit") == evidence.get("workflow_head_sha"), "materialization commit binding")
    require(result.get("github", {}).get("workflow_run_id") == str(evidence.get("workflow_run_id")), "materialization run binding")
    require(result.get("inputs_sha256") == evidence.get("inputs_sha256"), "materialization input binding")
    by_node = {node["node"]: node for node in result["nodes"]}
    require(len(by_node) == len(result["nodes"]) and set(by_node) == set(selected), "exact retained node coverage")
    version_path = root / level.get("candidate_versions_evidence", {}).get("path", "")
    require(version_path.is_file(), "candidate version evidence missing")
    if not version_path.is_file():
        return errors
    version_payload = version_path.read_bytes()
    require(hashlib.sha256(version_payload).hexdigest() == level["candidate_versions_evidence"].get("sha256"), "candidate version evidence digest")
    versions = json.loads(version_payload)
    require(versions.get("state") == "PASS" and versions.get("package_execution_started") is False
            and versions.get("consumes_package_attempt") is False, "candidate version assignment scope")
    require(versions.get("materialization_result_sha256") == evidence.get("result_json_sha256"), "candidate versions source evidence binding")
    version_nodes = {node["node"]: node for node in versions["nodes"]}
    require(len(version_nodes) == len(versions["nodes"]) and set(version_nodes) == set(selected), "candidate version node coverage")
    for name in selected:
        if name not in by_node or name not in version_nodes:
            continue
        node, record, version_record = level["nodes"][name], by_node[name], version_nodes[name]
        upstream, reference = record["upstream"], record["ubuntu_reference"]
        require(record["state"] == "PASS" and upstream["signature_verification"] == "PASS", f"{name}: verified source")
        require(upstream.get("required_primary_fingerprint") == materialization["source_authority"]["required_primary_fingerprint"], f"{name}: source signing authority")
        require(upstream["sha256"] == node["upstream_source_sha256"] and upstream["version"] == node["upstream_version"], f"{name}: source identity")
        require(reference["source_package"] == node["packaging_reference"]["source_package"], f"{name}: reference identity")
        version = node.get("candidate_package_version", "")
        require(version == version_record["candidate_package_version"], f"{name}: candidate version evidence")
        expected_state = "package-build-pending" if name in scope else "packaging-preparation-pending"
        if phase == "level0-package-build-complete" and node.get("state") == "PASS":
            campaign_path = root / planning.get("package_build_manifest", "")
            require(campaign_path.is_file(), f"{name}: package build closure missing")
            if campaign_path.is_file():
                campaign = json.loads(campaign_path.read_text())
                require(campaign.get("nodes", {}).get(name, {}).get("state") == "PASS", f"{name}: package PASS scope")
            expected_state = "PASS"
        require(node.get("state") == expected_state, f"{name}: preparation state")
        ref_epoch = reference["source_version"].split(":", 1)[0] if ":" in reference["source_version"] else "0"
        epoch = version.split(":", 1)[0] if ":" in version else "0"
        require(epoch == ref_epoch, f"{name}: preserved Ubuntu epoch")
        for ref in reference["apt_source_versions"]:
            require(subprocess.run(["dpkg", "--compare-versions", version, "gt", ref]).returncode == 0, f"{name}: version must exceed captured Ubuntu {ref}")
    require(level["version_policy"]["candidate_version_assignment"] == "PASS", "candidate version assignment closure")
    require(planning.get("package_preparation_authorized") is True, "package preparation authorization")
    return errors

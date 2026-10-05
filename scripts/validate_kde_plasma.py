#!/usr/bin/env python3
import hashlib
import json
import re
import sys
from pathlib import Path
from plasma_lifecycle import validate as validate_lifecycle

ROOT = Path(__file__).resolve().parents[1]
errors = []

def req(condition, message):
    if not condition:
        errors.append(message)

plasma = json.loads((ROOT / "manifests/kde-plasma.json").read_text())
deps = json.loads((ROOT / "manifests/kde-plasma-dependencies.json").read_text())
dag = json.loads((ROOT / "manifests/kde-plasma-dag-candidate.json").read_text())
executable_dag = json.loads((ROOT / "manifests/kde-plasma-dag.json").read_text())
audit = json.loads((ROOT / "manifests/kde-plasma-provider-audit.json").read_text())
resolution = json.loads((ROOT / "manifests/kde-plasma-provider-resolution.json").read_text())
resolution_review = json.loads((ROOT / "manifests/kde-plasma-provider-resolution-review.json").read_text())
resolution_preflight = json.loads((ROOT / "manifests/kde-plasma-provider-resolution-preflight.json").read_text())
level0_preflight = json.loads((ROOT / "manifests/kde-plasma-level0-materialization-preflight.json").read_text())
level0_materialization = json.loads((ROOT / "manifests/kde-plasma-level0-materialization.json").read_text())
level0 = json.loads((ROOT / "manifests/kde-plasma-level0.json").read_text())
desktop = json.loads((ROOT / "manifests/desktop-stack.json").read_text())
cert = json.loads((ROOT / "manifests/authoritative-kvm-certification.json").read_text())
lane = (ROOT / ".github/workflows/kde-plasma-lane.yml").read_text()

release = plasma.get("release", {})
req(release.get("version") == "6.7.5", "Plasma canonical stable version")
req(release.get("status") == "stable", "Plasma release must be stable")
req(release.get("selection_policy") == "latest-official-stable-compatible", "Plasma selection policy")
req(release.get("rejected_noncanonical_release") == "6.8 beta", "Plasma 6.8 beta must remain noncanonical")
req(release.get("source_count") == 75, "Plasma 6.7.5 upstream source count")
req(release.get("signing_fingerprint") == "0AAC775BB6437A8D9AF7A3ACFE0784117FBCE11D", "Plasma release signing fingerprint")

requirements = plasma.get("requirements", {})
req(requirements.get("qt_minimum") == "6.10", "Plasma 6.7 Qt requirement")
req(requirements.get("frameworks_minimum") == "6.26", "Plasma 6.7 Frameworks requirement")
req(requirements.get("supralinux_qt_candidate") == "6.10.2+dfsg-7", "SupraLINUX Qt candidate")
req(requirements.get("supralinux_frameworks") == "6.30.0", "SupraLINUX Frameworks provider")

sources = plasma.get("sources", [])
ids = [node.get("id") for node in sources]
req(len(sources) == 75 and len(set(ids)) == 75, "Plasma source inventory must contain 75 unique nodes")
for node in sources:
    node_id = node.get("id", "")
    sha = node.get("source_sha256", "")
    req(node.get("version") == "6.7.5", f"{node_id}: source version")
    req(bool(re.fullmatch(r"[0-9a-f]{64}", sha)), f"{node_id}: source SHA-256")
    req(node.get("source_url") == f"https://download.kde.org/stable/plasma/6.7.5/{node_id}-6.7.5.tar.xz", f"{node_id}: source URL")

planning = plasma.get("planning", {})
errors.extend(validate_lifecycle(ROOT, plasma, level0, level0_materialization))
req(planning.get("consumes_package_attempt") is False, "Level 0 materialization must not consume package Attempt")
req(planning.get("canonical_package_state_effect") == "none", "Level 0 materialization canonical package state effect")
req(planning.get("lane_workflow") == ".github/workflows/kde-plasma-lane.yml", "Plasma lane workflow")
req(planning.get("dag_manifest") == "manifests/kde-plasma-dag.json", "Executable DAG manifest binding")
req(planning.get("level0_manifest") == "manifests/kde-plasma-level0.json", "Level 0 manifest binding")
req(planning.get("level0_materialization_preflight_manifest") == "manifests/kde-plasma-level0-materialization-preflight.json", "Level 0 preflight manifest binding")
req(planning.get("level0_materialization_manifest") == "manifests/kde-plasma-level0-materialization.json", "Level 0 materialization manifest binding")
req(planning.get("level0_materialization_preflight_evidence", {}).get("artifact_id") == 11286979140, "Level 0 preflight evidence binding")

disc = deps.get("discovery", {})
req(deps.get("state") == "discovery-evidence-promoted", "Plasma dependency discovery evidence promotion")
req(disc.get("result") == "PASS", "Plasma dependency discovery PASS")
req(disc.get("workflow_run_id") == 36951077374 and disc.get("artifact_id") == 11204675088, "Plasma discovery evidence binding")
req(disc.get("artifact_digest") == "sha256:9b6192b1145474cca5bd255d4cb517be2ea8ea4fcd87679f05dfa5aa039a39fd", "Plasma discovery artifact digest")
req(disc.get("dependencies_json_sha256") == "a6b2d066ced63231dd3de6adb6248dbbd7eba01cf0d776d49c6d2b091c0f82ef", "Plasma dependency snapshot hash")
req(disc.get("result_json_sha256") == "71aea7c5ba1481cd41915fd7d645aed6cb4ac8f2da8cce0e13e7440a8df03493", "Plasma discovery result hash")
req(disc.get("parser_revision") == 4 and disc.get("source_sha256_verified") == 75, "Plasma discovery revision/source verification")
req(disc.get("canonical_dag_effect") == "candidate-only-pending-provider-resolution", "Plasma dependency candidate evidence boundary")
req(set(deps.get("nodes", {})) == set(ids), "Plasma dependency manifest node set")

req(dag.get("state") == "candidate-review-required" and dag.get("candidate_only") is True, "Plasma DAG candidate state")
req(dag.get("package_execution_authorized") is False and dag.get("consumes_package_attempt") is False, "Plasma DAG package execution lock")
req(executable_dag.get("state") == "executable" and executable_dag.get("candidate_only") is False, "Plasma executable DAG state")
req(executable_dag.get("canonical_for_package_planning") is True, "Plasma executable DAG planning authority")
req(executable_dag.get("topology") == dag.get("topology") and executable_dag.get("nodes") == dag.get("nodes"), "Plasma DAG promotion must preserve topology")
req(executable_dag.get("promotion", {}).get("provider_resolution_review", {}).get("artifact_id") == 11261258576, "Plasma executable DAG review evidence")
req(executable_dag.get("package_execution_authorized") is False and executable_dag.get("consumes_package_attempt") is False, "Plasma executable DAG package execution lock")
req(executable_dag.get("next_gate") == "plasma-level0-definition", "Plasma executable DAG next gate")

req(audit.get("state") == "PASS", "Plasma provider audit PASS")
req(audit.get("execution_authorized") is False, "Closed provider audit execution authorization")
req(audit.get("package_execution_authorized") is False, "Plasma provider audit package execution lock")
req(audit.get("consumes_package_attempt") is False, "Plasma provider audit Attempt boundary")
req(audit.get("evidence", {}).get("artifact_id") == 11226253937, "Plasma provider audit evidence artifact")

req(resolution.get("state") == "PASS", "Plasma provider resolution PASS")
req(resolution.get("execution_authorized") is False, "Closed Plasma provider resolution authorization")
req(resolution.get("package_execution_authorized") is False, "Plasma provider resolution package execution lock")
req(resolution.get("consumes_package_attempt") is False, "Plasma provider resolution Attempt boundary")
req(resolution.get("input", {}).get("provider_audit_artifact_id") == 11226253937, "Provider resolution input artifact")
resolution_evidence = resolution.get("evidence", {})
req(resolution_evidence.get("workflow_run_id") == 37086119189, "Provider resolution workflow run")
req(resolution_evidence.get("job_id") == 111096931279, "Provider resolution job")
req(resolution_evidence.get("artifact_id") == 11260780398, "Provider resolution artifact")
req(resolution_evidence.get("artifact_digest") == "sha256:aeabbadbb4ea5d5388cfe0aee4eb62e8ca3b79de839414b77abd000724aa7785", "Provider resolution artifact digest")
req(resolution_evidence.get("files", {}).get("result.json") == "49e137d999886f447264aafe857c351c5aca84171069c986bcdf182876176a21", "Provider resolution result hash")
req(resolution.get("result_summary", {}).get("review_required") is True, "Provider resolution review requirement")
recovery = resolution.get("recovery", {})
req(recovery.get("state") == "PASS", "Provider resolution infrastructure recovery PASS")
req(recovery.get("mechanism") == "batched-apt-cache-showsrc-plus-policy", "Provider resolution recovered mechanism")
req(recovery.get("evidence", {}).get("artifact_id") == 11240638791, "Provider resolution recovery artifact")
req(recovery.get("prior_infrastructure_hold", {}).get("consecutive_infra_invalid") == 2, "Provider resolution repeated INFRA_INVALID history")
req(recovery.get("prior_infrastructure_hold", {}).get("package_attempts_consumed") == 0, "Provider resolution infrastructure incidents package Attempt boundary")

req(resolution_review.get("state") == "PASS", "Provider resolution review PASS")
req(resolution_review.get("execution_authorized") is False, "Closed provider resolution review authorization")
req(resolution_review.get("package_execution_authorized") is False, "Provider resolution review package execution lock")
req(resolution_review.get("consumes_package_attempt") is False, "Provider resolution review Attempt boundary")
req(resolution_review.get("canonical_package_state_effect") == "none", "Provider resolution review canonical package effect")
req(resolution_review.get("input", {}).get("artifact_id") == 11260780398, "Provider resolution review input artifact")
req(resolution_review.get("input", {}).get("files", {}).get("cmake-resolution.json") == "832a121efba8d13c054fdfecc0fbb0a359869629d505bc95dbe6d27a8069973f", "Provider resolution CMake evidence hash")
req(set(resolution_review.get("source_reference_decisions", {})) == {"plasma-bigscreen", "plasma-login-manager", "plasma-setup", "spectacle", "union"}, "Provider resolution source-reference review set")
req(len(resolution_review.get("missing_build_dep_decisions", {})) == 7, "Provider resolution special Build-Depends review count")
req(len(resolution_review.get("qml_provider_decisions", {})) == 12, "Provider resolution QML review count")
req(resolution_review.get("cmake_source_reference_policy", {}).get("expected_review_count") == 117, "Provider resolution CMake contextual review count")
req(len(resolution_review.get("legacy_compatibility", {}).get("references", [])) == 11, "Provider resolution legacy compatibility review count")
review_evidence = resolution_review.get("evidence", {})
req(review_evidence.get("workflow_run_id") == 37088387510, "Provider resolution review workflow run")
req(review_evidence.get("artifact_id") == 11261258576, "Provider resolution review artifact")
req(review_evidence.get("artifact_digest") == "sha256:7f6aa009fcd72086102f5e64a43bddf59a533c2972b2324f02ece6f1a5ce4aff", "Provider resolution review artifact digest")
req(review_evidence.get("review_json_sha256") == "838c60bbf5e16b72e3e8551b2fd0f77aeff7f82b0c11d269b1067df7146aebe7", "Provider resolution review snapshot hash")
req(review_evidence.get("result_json_sha256") == "1d68c3373990aaa6dfeb614cd1a62d196be00e0208d9ea0c4cc5e7371d114bad", "Provider resolution review result hash")
req(review_evidence.get("review_required") is False, "Provider resolution review closed result")
req(resolution_review.get("next_gate") == "plasma-dag-executable-promotion", "Provider resolution review next gate")
semantic_correction = resolution_review.get("post_review_findings", {}).get("semantic_source_identity_correction", {})
req(semantic_correction.get("status") == "applied-before-Level0-materialization", "Provider review source-identity correction")
req(semantic_correction.get("corrected_reference_source") == "plasma-discover", "Provider review discover source correction")
req(semantic_correction.get("dag_topology_effect") == "none", "Provider review correction DAG boundary")

# Live source findings supplement the immutable historical availability review.
supplementary = json.loads((ROOT / "manifests/kde-plasma-supplementary-providers.json").read_text())
req(supplementary.get("role") == "plasma-supplementary-providers", "Supplementary provider role")
for name, provider in supplementary["nodes"].items():
    req(provider["package_execution_authorized"] is False, f"{name}: unreviewed provider execution")
    req(provider["consumes_package_attempt"] is False, f"{name}: preparation Attempt boundary")
    req(provider["qt_provider_effect"] == "none", f"{name}: Ubuntu Qt boundary")
    req(set(provider["affected_nodes"]) <= set(executable_dag["nodes"]), f"{name}: unknown consumers")
    ubuntu = provider["ubuntu_provider"]
    req(hashlib.sha256((ROOT / ubuntu["policy_path"]).read_bytes()).hexdigest() == ubuntu["policy_sha256"],
        f"{name}: Ubuntu availability evidence changed")
    source_review = provider.get("source_review")
    if source_review:
        path = ROOT / source_review["path"]
        req(hashlib.sha256(path.read_bytes()).hexdigest() == source_review["sha256"], f"{name}: source review changed")
        proof = json.loads(path.read_text())
        candidate = provider["candidate_provider"]
        req(proof["state"] == source_review["state"] == "PASS" and proof["scope"] == source_review["scope"],
            f"{name}: source authentication scope")
        req(proof["consumes_package_attempt"] is proof["package_execution_started"] is False,
            f"{name}: source review Attempt boundary")
        req(proof["upstream_sha256"] == candidate["upstream_sha256"] and
            proof["signature_sha256"] == candidate["signature_sha256"], f"{name}: authenticated source inputs")
        req(proof["primary_fingerprint"] == candidate["signing_primary_fingerprint"] and
            proof["signature_verification"] == candidate["signature_verification"] == "PASS", f"{name}: signature authority")
        for filename, digest in proof["files_sha256"].items():
            file = path.parent / filename
            req(file.resolve().is_relative_to(path.parent.resolve()), f"{name}: unsafe source evidence path")
            req(hashlib.sha256(file.read_bytes()).hexdigest() == digest, f"{name}: source evidence changed: {filename}")
        status = (path.parent / "signature-status-arch-reference.log").read_text()
        req(f'[GNUPG:] VALIDSIG {proof["primary_fingerprint"]} ' in status and '[GNUPG:] GOODSIG ' in status and
            not any(failure in status for failure in ['EXPKEYSIG', 'REVKEYSIG', 'EXPSIG', 'BADSIG', 'ERRSIG']),
            f"{name}: current release signature result")
        schema = json.loads((path.parent / "schema-review.json").read_text())
        req(schema["state"] == "PASS" and not schema["incompatible"], f"{name}: installed XML structural review")
        req(hashlib.sha256((ROOT / proof["retention_path"]).read_bytes()).hexdigest() == proof["retention_sha256"],
            f"{name}: source retention evidence changed")
    review = provider.get("compatibility_review", {}).get("local_wire_review")
    if review:
        path = ROOT / review["path"]
        req(hashlib.sha256(path.read_bytes()).hexdigest() == review["sha256"], f"{name}: wire review changed")
        proof = json.loads(path.read_text())
        req(proof["state"] == review["state"] == "PASS", f"{name}: local wire fixture result")
        req(proof["scope"] == review["scope"] and "not authoritative" in proof["scope"],
            f"{name}: local review scope")
        for filename, digest in proof["files_sha256"].items():
            file = path.parent / filename
            req(file.resolve().is_relative_to(path.parent.resolve()), f"{name}: unsafe evidence path")
            req(hashlib.sha256(file.read_bytes()).hexdigest() == digest, f"{name}: wire evidence changed: {filename}")
        result = json.loads((path.parent / "result.json").read_text())
        req(result["state"] == "PASS" and result["versions"] == proof["negotiated_versions"] == [1, 7, 8, 20],
            f"{name}: negotiated wire versions")
        req(result["baseline_xml_sha256"] == proof["baseline_xml_sha256"] and
            result["candidate_xml_sha256"] == proof["candidate_xml_sha256"], f"{name}: wire XML inputs")
if supplementary.get("source_review_retention"):
    retained = supplementary["source_review_retention"]
    raw = (ROOT / retained["path"]).read_bytes()
    req(hashlib.sha256(raw).hexdigest() == retained["sha256"], "Supplementary source retention changed")
    index = json.loads(raw)
    req(index["state"] == "PASS" and index["requires_github_for_restore"] is False,
        "Supplementary source independent retention")
    if retained.get("offline_restoration"):
        restored = retained["offline_restoration"]
        raw_restore = (ROOT / restored["path"]).read_bytes()
        req(hashlib.sha256(raw_restore).hexdigest() == restored["sha256"], "Source restoration evidence changed")
        proof = json.loads(raw_restore)
        req(proof["state"] == "PASS" and proof["network_used"] is False and
            proof["requires_github_for_restore"] is False and proof["candidate_package_execution_started"] is False,
            "Offline source restoration scope")
        req(proof["archive_sha256"] == index["archive_sha256"] and
            proof["retention_index_sha256"] == retained["sha256"], "Source restoration archive binding")
        req(proof["restored_ubuntu_sources"] == [{key: item[key] for key in ("source_package", "version")}
                                                 for item in index["ubuntu_sources"]] and
            proof["ubuntu_source_packages_extracted"] == len(index["ubuntu_sources"]), "Restored source identities")

req(resolution_preflight.get("state") == "PASS", "Provider resolution preflight PASS")
req(resolution_preflight.get("execution_authorized") is False, "Closed provider resolution preflight authorization")
req(resolution_preflight.get("package_execution_authorized") is False, "Provider resolution preflight package execution lock")
req(resolution_preflight.get("consumes_package_attempt") is False, "Provider resolution preflight Attempt boundary")
req(resolution_preflight.get("mechanism") == "batched-apt-cache-showsrc-plus-policy", "Provider resolution preflight mechanism")
req(resolution_preflight.get("revision") == 2, "Provider resolution preflight revision")
req(resolution_preflight.get("evidence", {}).get("artifact_id") == 11240638791, "Provider resolution preflight evidence artifact")
req(resolution_preflight.get("evidence", {}).get("result_json_sha256") == "6bdc666ef3ab38b0657dd4e066f270cdda073ac1b3f9202941c92f613b834c46", "Provider resolution preflight result hash")
audit_input = audit.get("input", {})
req(audit_input.get("discovery_workflow_run_id") == 36951077374, "Provider audit discovery run")
req(audit_input.get("discovery_artifact_id") == 11204675088, "Provider audit discovery artifact")
req(audit_input.get("dependencies_json_sha256") == "a6b2d066ced63231dd3de6adb6248dbbd7eba01cf0d776d49c6d2b091c0f82ef", "Provider audit input hash")

for token in (
    "level0-materialization-pending",
    "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
    "run-id: 37086119189",
    "run-kde-plasma-provider-resolution-review.py",
    "run-kde-plasma-provider-audit.py",
    "run-kde-plasma-provider-resolution.py",
    "run-kde-plasma-provider-resolution-preflight.py",
):
    req(token in lane, f"Plasma lane contract: {token}")

req(level0_preflight.get("state") == "PASS", "Level 0 materialization preflight PASS")
req(level0_preflight.get("execution_authorized") is False, "Closed Level 0 preflight authorization")
req(level0_preflight.get("evidence", {}).get("artifact_id") == 11286979140, "Level 0 preflight artifact")
req(level0_preflight.get("evidence", {}).get("files", {}).get("result.json") == "cb8e6471aa1149e8335cde8d4d43c1d84916151187ecb11fda3b3d7f2cf9ed4f", "Level 0 preflight result hash")
req(level0_materialization.get("package_execution_authorized") is False, "Level 0 materialization package lock")

stack = desktop.get("desktop", {})
req(stack.get("plasma", {}).get("version") == "6.7.5", "desktop-stack Plasma version")
req(stack.get("frameworks", {}).get("version") == "6.30.0", "desktop-stack Frameworks version")
qt = desktop.get("qt", {})
req(qt.get("required_series") == "6.10", "desktop-stack Qt requirement")
req(qt.get("provider", {}).get("candidate_version") == "6.10.2+dfsg-7", "desktop-stack Qt provider candidate")
runner = desktop.get("ci", {}).get("authoritative_runner", {})
req(runner.get("status") == "certified", "authoritative runner certification precondition")
req(runner.get("desktop_release_relevant_authorized") is True, "release-relevant desktop must be unlocked")

req(cert.get("next_gate") == "certification-complete", "authoritative KVM certification complete")
release_state = cert.get("release_relevant_desktop", {})
req(release_state.get("status") == "unlocked", "release-relevant desktop certification state")
req(release_state.get("plasma_authorized") is True and release_state.get("kwin_authorized") is True and release_state.get("session_authorized") is True, "Plasma/KWin/session authorizations")
req(cert.get("stable_publication_authorized") is False, "Plasma planning must not authorize stable publication")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Plasma 6.7.5 planning validation: PASS")
print(f"Lane phase: {planning['status']}")
print(f"Next gate: {planning['next_gate']}; package execution: scoped by current lifecycle")

#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

def req(condition, message):
    if not condition:
        errors.append(message)

plasma = json.loads((ROOT / "manifests/kde-plasma.json").read_text())
deps = json.loads((ROOT / "manifests/kde-plasma-dependencies.json").read_text())
dag = json.loads((ROOT / "manifests/kde-plasma-dag-candidate.json").read_text())
audit = json.loads((ROOT / "manifests/kde-plasma-provider-audit.json").read_text())
resolution = json.loads((ROOT / "manifests/kde-plasma-provider-resolution.json").read_text())
resolution_preflight = json.loads((ROOT / "manifests/kde-plasma-provider-resolution-preflight.json").read_text())
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
req(planning.get("phase") == "provider-resolution", "Plasma planning phase")
req(planning.get("status") == "provider-resolution-pending", "Plasma provider resolution live status")
req(planning.get("execution_authorized") is True, "Plasma provider resolution authorization")
req(planning.get("package_execution_authorized") is False, "Provider resolution must not authorize package execution")
req(planning.get("consumes_package_attempt") is False, "Provider resolution must not consume package Attempt")
req(planning.get("canonical_package_state_effect") == "none", "Provider resolution canonical package state effect")
req(planning.get("runner_scope") == "github-hosted-ubuntu-26.04-non-authoritative-preflight", "Provider resolution runner scope")
req(planning.get("lane_workflow") == ".github/workflows/kde-plasma-lane.yml", "Plasma lane workflow")
req(planning.get("next_gate") == "plasma-provider-resolution-evidence", "Plasma provider resolution next gate")

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

req(audit.get("state") == "PASS", "Plasma provider audit PASS")
req(audit.get("execution_authorized") is False, "Closed provider audit execution authorization")
req(audit.get("package_execution_authorized") is False, "Plasma provider audit package execution lock")
req(audit.get("consumes_package_attempt") is False, "Plasma provider audit Attempt boundary")
req(audit.get("evidence", {}).get("artifact_id") == 11226253937, "Plasma provider audit evidence artifact")

req(resolution.get("state") == "execution-authorized", "Plasma provider resolution state")
req(resolution.get("execution_authorized") is True, "Plasma provider resolution authorization")
req(resolution.get("package_execution_authorized") is False, "Plasma provider resolution package execution lock")
req(resolution.get("consumes_package_attempt") is False, "Plasma provider resolution Attempt boundary")
req(resolution.get("input", {}).get("provider_audit_artifact_id") == 11226253937, "Provider resolution input artifact")
recovery = resolution.get("recovery", {})
req(recovery.get("state") == "PASS", "Provider resolution infrastructure recovery PASS")
req(recovery.get("mechanism") == "batched-apt-cache-showsrc-plus-policy", "Provider resolution recovered mechanism")
req(recovery.get("evidence", {}).get("artifact_id") == 11240638791, "Provider resolution recovery artifact")
req(recovery.get("prior_infrastructure_hold", {}).get("consecutive_infra_invalid") == 2, "Provider resolution repeated INFRA_INVALID history")
req(recovery.get("prior_infrastructure_hold", {}).get("package_attempts_consumed") == 0, "Provider resolution infrastructure incidents package Attempt boundary")

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
    "provider-resolution-pending",
    "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
    "run-id: 36951077374",
    "run-kde-plasma-provider-audit.py",
    "run-kde-plasma-provider-resolution.py",
    "run-kde-plasma-provider-resolution-preflight.py",
):
    req(token in lane, f"Plasma lane contract: {token}")

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
print("Lane phase: provider-audit-pending")
print("Package execution: locked")

#!/usr/bin/env python3
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
dag = json.loads((ROOT / "manifests/kde-plasma-dag.json").read_text())
level0 = json.loads((ROOT / "manifests/kde-plasma-level0.json").read_text())
preflight = json.loads((ROOT / "manifests/kde-plasma-level0-materialization-preflight.json").read_text())
materialization = json.loads((ROOT / "manifests/kde-plasma-level0-materialization.json").read_text())
review = json.loads((ROOT / "manifests/kde-plasma-provider-resolution-review.json").read_text())
lane = (ROOT / ".github/workflows/kde-plasma-lane.yml").read_text()

levels = dag.get("topology", {}).get("levels", [])
dag_level0 = next((x.get("nodes", []) for x in levels if x.get("level") == 0), [])
selected = level0.get("selected_nodes", [])
nodes = level0.get("nodes", {})
sources = {x.get("id"): x for x in plasma.get("sources", [])}

req(level0.get("role") == "plasma-level0-definition", "Level 0 role")
errors.extend(validate_lifecycle(ROOT, plasma, level0, materialization))
req(level0.get("package_execution_authorized") is False, "Level 0 package execution lock")
req(level0.get("consumes_package_attempt") is False, "Level 0 definition Attempt boundary")
req(level0.get("canonical_package_state_effect") == "none", "Level 0 definition package-state effect")
req(level0.get("selected_level") == 0, "Level 0 selected level")
req(level0.get("selected_node_count") == 34, "Level 0 node count")
req(selected == dag_level0, "Level 0 selection must exactly follow canonical DAG order")
req(set(nodes) == set(selected), "Level 0 node map coverage")
checkpoint = level0.get("execution_checkpoint", {})
req(checkpoint.get("checkpoint_id") == "frameworks-6.30-pass", "Level 0 Frameworks checkpoint binding")
req(checkpoint.get("state") == "PASS", "Level 0 Frameworks checkpoint state")
req(checkpoint.get("required_before_package_execution") is True, "Level 0 Frameworks checkpoint requirement")
req(checkpoint.get("cache_only") is True, "Level 0 Frameworks checkpoint cache-only role")
req(checkpoint.get("image_sha256") == "ec38f99e306d5a13333d6b247a9433b3526ec4a6d1a272631242c68df56c3e97", "Level 0 Frameworks checkpoint admitted image hash")
req(checkpoint.get("consumes_package_attempt") is False, "Level 0 Frameworks checkpoint Attempt boundary")
req(level0.get("version_policy", {}).get("preserve_epoch") is True, "Level 0 epoch preservation policy")

for node_id in selected:
    node = nodes.get(node_id, {})
    dag_node = dag.get("nodes", {}).get(node_id, {})
    upstream = sources.get(node_id, {})
    req(dag_node.get("level") == 0, f"{node_id}: DAG level")
    req(dag_node.get("depends_on") == [], f"{node_id}: internal predecessor set")
    req(node.get("internal_predecessors") == [], f"{node_id}: Level 0 predecessor set")
    req(node.get("upstream_version") == "6.7.5", f"{node_id}: upstream version")
    req(node.get("upstream_source_url") == upstream.get("source_url"), f"{node_id}: upstream source URL")
    req(node.get("upstream_source_sha256") == upstream.get("source_sha256"), f"{node_id}: upstream source SHA")
    req(bool(re.fullmatch(r"[0-9a-f]{64}", node.get("upstream_source_sha256", ""))), f"{node_id}: source SHA format")
    req(node.get("package_execution_authorized") is False, f"{node_id}: package execution lock")
    ref = node.get("packaging_reference", {})
    req(ref.get("provider_platform") == "ubuntu-resolute", f"{node_id}: reference provider platform")
    req(ref.get("reference_only") is True, f"{node_id}: Ubuntu reference-only role")
    req(ref.get("suites") == ["resolute", "resolute-updates", "resolute-security"], f"{node_id}: reference suites")
    if node_id == "discover":
        req(ref.get("source_package") == "plasma-discover", "discover: corrected Ubuntu source alias")
        req(ref.get("verified_reference", {}).get("version") == "6.6.6-0ubuntu0.1", "discover: verified Resolute Updates version")
    else:
        req(ref.get("source_package") == node_id, f"{node_id}: same-name Ubuntu source reference")

guard = level0.get("packaging_reference_policy", {})
req(guard.get("explicit_aliases") == {"discover": "plasma-discover"}, "Level 0 explicit source aliases")
false_positive = guard.get("historical_false_positive", {})
req(false_positive.get("rejected_reference_source") == "discover", "discover historical false source")
req(false_positive.get("rejected_reference_version") == "2.1.2-10.1build1", "discover historical false version")
req(false_positive.get("corrected_reference_source") == "plasma-discover", "discover corrected source")

finding = review.get("post_review_findings", {}).get("semantic_source_identity_correction", {})
req(finding.get("status") == "applied-before-Level0-materialization", "provider review semantic correction status")
req(finding.get("historical_evidence_immutable") is True, "historical provider evidence immutability")
req(finding.get("corrected_reference_source") == "plasma-discover", "provider review corrected source")
req(finding.get("dag_topology_effect") == "none", "provider correction DAG topology boundary")
req(finding.get("package_attempts_consumed") == 0, "provider correction Attempt boundary")

req(preflight.get("state") == "PASS", "Level 0 materialization preflight state")
req(preflight.get("execution_authorized") is False, "Closed Level 0 materialization preflight authorization")
req(preflight.get("materialization_authorized") is False, "Closed preflight materialization boundary")
req(preflight.get("package_execution_authorized") is False, "Preflight package execution lock")
req(preflight.get("consumes_package_attempt") is False, "Preflight Attempt boundary")
req(preflight.get("mechanism") == "apt-get-source-download-only-plus-dpkg-source-extract", "Preflight mechanism")
req(preflight.get("sample", {}).get("source_package") == "kf6-kconfig", "Preflight synthetic source")
req("kf6-kconfig" not in selected, "Preflight sample must not be a Level 0 package")
req(preflight.get("failure_classification") == "INFRA_INVALID", "Preflight failure classification")
req(preflight.get("next_gate_on_pass") == "plasma-level0-materialization", "Preflight PASS next gate")
req(preflight.get("evidence", {}).get("artifact_id") == 11286979140, "Preflight PASS artifact")
req(preflight.get("evidence", {}).get("files", {}).get("result.json") == "cb8e6471aa1149e8335cde8d4d43c1d84916151187ecb11fda3b3d7f2cf9ed4f", "Preflight PASS result hash")
req(materialization.get("input", {}).get("selected_node_count") == 34, "Level 0 materialization scope")
req(materialization.get("package_execution_authorized") is False, "Materialization package execution lock")

planning = plasma.get("planning", {})
req(planning.get("package_execution_authorized") is False, "Plasma live package execution lock")
req(planning.get("level0_manifest") == "manifests/kde-plasma-level0.json", "Plasma live Level 0 manifest")
req(planning.get("level0_materialization_preflight_manifest") == "manifests/kde-plasma-level0-materialization-preflight.json", "Plasma live preflight manifest")
req(planning.get("level0_materialization_manifest") == "manifests/kde-plasma-level0-materialization.json", "Plasma live materialization manifest")

for token in (
    "level0-materialization-pending",
    "run-kde-plasma-level0-materialization.py",
    "kde-plasma-level0-materialization-",
):
    req(token in lane, f"Plasma Level 0 lane contract: {token}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Plasma Level 0 definition validation: PASS")
print("nodes=34; package_execution_authorized=false")
print(f"Level 0: {level0['state']}; next_gate={planning['next_gate']}")
print("discover packaging reference: plasma-discover")

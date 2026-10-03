#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

def req(condition, message):
    if not condition:
        errors.append(message)

candidate = json.loads((ROOT / "manifests/kde-plasma-dag-candidate.json").read_text())
dag = json.loads((ROOT / "manifests/kde-plasma-dag.json").read_text())
review = json.loads((ROOT / "manifests/kde-plasma-provider-resolution-review.json").read_text())
plasma = json.loads((ROOT / "manifests/kde-plasma.json").read_text())

req(candidate.get("state") == "candidate-review-required", "historical candidate DAG state")
req(candidate.get("candidate_only") is True, "historical candidate DAG must remain candidate-only")

req(dag.get("state") == "executable", "canonical Plasma DAG state")
req(dag.get("candidate_only") is False, "canonical Plasma DAG must not be candidate-only")
req(dag.get("canonical_for_package_planning") is True, "canonical Plasma DAG planning authority")
req(dag.get("plasma_version") == "6.7.5", "canonical Plasma DAG version")
req(dag.get("package_execution_authorized") is False, "DAG promotion must not authorize package execution")
req(dag.get("consumes_package_attempt") is False, "DAG promotion must not consume package Attempt")
req(dag.get("canonical_package_state_effect") == "none", "DAG promotion package state effect")
req(dag.get("next_gate") == "plasma-level0-definition", "canonical Plasma DAG next gate")

promotion = dag.get("promotion", {})
req(promotion.get("candidate_manifest") == "manifests/kde-plasma-dag-candidate.json", "candidate manifest binding")
req(promotion.get("candidate_commit") == "bab176ffbdc83e62f08030506983f28e34335f86", "candidate commit binding")
req(promotion.get("candidate_blob_sha") == "dc53609dce00ba6ccee178ca00daffb7253cca39", "candidate blob binding")
rev = promotion.get("provider_resolution_review", {})
req(rev.get("result") == "PASS", "provider-resolution review promotion result")
req(rev.get("workflow_run_id") == 37088387510, "provider-resolution review run")
req(rev.get("artifact_id") == 11261258576, "provider-resolution review artifact")
req(rev.get("artifact_digest") == "sha256:7f6aa009fcd72086102f5e64a43bddf59a533c2972b2324f02ece6f1a5ce4aff", "provider-resolution review artifact digest")
req(rev.get("review_json_sha256") == "838c60bbf5e16b72e3e8551b2fd0f77aeff7f82b0c11d269b1067df7146aebe7", "provider-resolution review snapshot hash")
req(rev.get("result_json_sha256") == "1d68c3373990aaa6dfeb614cd1a62d196be00e0208d9ea0c4cc5e7371d114bad", "provider-resolution review result hash")
req(rev.get("review_definition_sha256") == "cf194c5818c88223e219ff56dcd537c0f0592038b5d101f1506621a7aa4354c4", "provider-resolution review definition hash")
req(rev.get("review_required") is False, "provider-resolution review must be closed")

req(review.get("state") == "PASS", "provider-resolution review canonical closure")
req(review.get("execution_authorized") is False, "closed provider-resolution review execution lock")
req(review.get("package_execution_authorized") is False, "closed provider-resolution review package lock")
req(review.get("evidence", {}).get("artifact_id") == 11261258576, "review manifest evidence binding")
req(review.get("evidence", {}).get("result_json_sha256") == "1d68c3373990aaa6dfeb614cd1a62d196be00e0208d9ea0c4cc5e7371d114bad", "review manifest result hash")
req(review.get("next_gate") == "plasma-dag-executable-promotion", "review historical next gate")

req(dag.get("source_discovery") == candidate.get("source_discovery"), "DAG promotion must preserve source-discovery evidence")
req(dag.get("topology") == candidate.get("topology"), "DAG promotion must preserve candidate topology")
req(dag.get("nodes") == candidate.get("nodes"), "DAG promotion must preserve candidate edges and levels")

top = dag.get("topology", {})
nodes = dag.get("nodes", {})
req(top.get("acyclic") is True, "canonical Plasma DAG must be acyclic")
req(top.get("level_count") == 6, "canonical Plasma DAG level count")
req(top.get("level_sizes") == [34, 11, 20, 1, 2, 7], "canonical Plasma DAG level sizes")
req(len(nodes) == 75, "canonical Plasma DAG node count")
req(sum(len(node.get("depends_on", [])) for node in nodes.values()) == 109, "canonical Plasma DAG edge count")
for name, node in nodes.items():
    for dep in node.get("depends_on", []):
        req(dep in nodes, f"{name}: missing dependency {dep}")
        if dep in nodes:
            req(nodes[dep].get("level", 999) < node.get("level", -1), f"{name}: dependency {dep} must be earlier")

planning = plasma.get("planning", {})
req(planning.get("phase") == "dag-executable", "Plasma live phase after DAG promotion")
req(planning.get("status") == "dag-executable-promoted", "Plasma live status after DAG promotion")
req(planning.get("dag_manifest") == "manifests/kde-plasma-dag.json", "Plasma live canonical DAG binding")
req(planning.get("package_execution_authorized") is False, "Plasma live package execution lock")
req(planning.get("next_gate") == "plasma-level0-definition", "Plasma live next gate")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Plasma executable DAG validation: PASS")
print("nodes=75 edges=109 levels=6 sizes=34,11,20,1,2,7")
print("package_execution_authorized=false")
print("next_gate=plasma-level0-definition")

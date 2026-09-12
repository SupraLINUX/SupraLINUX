#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1.json"
REFERENCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1-packaging-reference.json"

EXPECTED_SNAPSHOT = {
    "status": "PASS",
    "claim": "packaging-reference-snapshot-only",
    "authoritative": False,
    "workflow_run": 34701132721,
    "head_sha": "943a99f7465e311bbc72d63cbe6555a29aa4b5ab",
    "artifact_id": 10299579234,
    "artifact_sha256": "a2951c297f125ad81d1487075f0a0a6250114c4e875f3ba3870c3c18c09adaca",
    "snapshot_json_sha256": "601c668342c206af179e9c564bf87cac6a166f1070fe9af0b640cb57d2151597",
    "versions_tsv_sha256": "af6fd90121801eaf322442c43b793422494dfd5a109edccf484f5d24b463ea9b",
    "nodes": 29,
    "ubuntu_reference_upstream_versions": ["6.23.0", "6.24.0"],
    "debian_reference_upstream_versions": ["6.28.0", "6.28.1"],
    "framework_package_build_certification": "pending",
}

EXPECTED_BINARY_CONTRACT_SNAPSHOT = {
    "status": "pending",
    "claim": "binary-packaging-contract-reference-only",
    "authoritative": False,
    "framework_package_build_certification": "pending",
}

errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot load {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(data, dict):
        print(f"ERROR: {path.relative_to(ROOT)} must contain an object", file=sys.stderr)
        raise SystemExit(1)
    return data


source = load(SOURCE_MANIFEST)
reference = load(REFERENCE_MANIFEST)

source_nodes = source.get("nodes", [])
require(source.get("frameworks_series") == "6.30.0", "Packaging reference must follow Frameworks 6.30.0")
require(isinstance(source_nodes, list) and len(source_nodes) == 29, "Packaging reference requires the fixed 29-node Tier 1 set")
source_ids = {node.get("id") for node in source_nodes if isinstance(node, dict)}
require(len(source_ids) == 29 and None not in source_ids, "Tier 1 source node IDs are incomplete")

require(reference.get("schema") == 1, "Packaging-reference schema must be 1")
require(reference.get("authority") is False, "Packaging references must never be authoritative")
require(reference.get("role") == "packaging-reference-only", "Packaging-reference role changed unexpectedly")
require(reference.get("selected_kde") == "6.30.0", "Packaging reference must follow selected KDE 6.30.0")
require(reference.get("snapshot") == EXPECTED_SNAPSHOT, "Packaging-reference PASS evidence changed without review")
require(
    reference.get("binary_contract_snapshot") == EXPECTED_BINARY_CONTRACT_SNAPSHOT,
    "Binary-contract snapshot must remain pending until a real retained workflow PASS is recorded",
)

references = reference.get("references", {})
require(references.get("ubuntu", {}).get("distribution") == "ubuntu", "Ubuntu reference distribution missing")
require(references.get("ubuntu", {}).get("series") == "resolute", "Ubuntu packaging reference must be Resolute")
require(references.get("ubuntu", {}).get("components") == ["main", "universe"], "Ubuntu reference components changed unexpectedly")
require(references.get("debian", {}).get("distribution") == "debian", "Debian reference distribution missing")
require(references.get("debian", {}).get("series") == "sid", "Debian packaging reference must be sid")
require(references.get("debian", {}).get("components") == ["main"], "Debian reference components changed unexpectedly")

policy = reference.get("policy", {})
for key in (
    "kde_upstream_remains_authority",
    "reference_packaging_may_not_disable_upstream_defaults_without_documented_reason",
    "reference_versions_do_not_select_kde_version",
    "reference_binary_names_are_inputs_for_compatibility_review_not_automatic_decisions",
):
    require(policy.get(key) is True, f"Packaging reference policy must keep {key}=true")

nodes = reference.get("nodes", {})
require(isinstance(nodes, dict), "Packaging-reference nodes must be an object")
require(set(nodes) == source_ids, "Packaging-reference node set must exactly match Tier 1")
for node_id in sorted(source_ids):
    node = nodes.get(node_id, {})
    require(node == {"source_package": f"kf6-{node_id}"}, f"{node_id}: source package mapping must remain kf6-{node_id}")

for node in source_nodes:
    if not isinstance(node, dict):
        continue
    node_id = node.get("id", "<unknown>")
    require(node.get("packaging") == {"state": "pending"}, f"{node_id}: packaging state must remain pending during reference capture")
    require(node.get("state") == "pending", f"{node_id}: DAG state must remain pending during reference capture")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Frameworks Tier 1 packaging-reference policy: PASS")
print("Reference authorities: none; Ubuntu Resolute and Debian sid are technical inputs only")
print("Source packaging snapshot evidence: PASS, non-authoritative")
print("Binary-contract snapshot evidence: pending until real workflow PASS")
print("Framework packaging/DAG states: pending")

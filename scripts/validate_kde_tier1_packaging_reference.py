#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1.json"
REFERENCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1-packaging-reference.json"
SCOPE = ROOT / "scripts" / "kde-tier1-packaging-reference-needed.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-tier1-packaging-reference.yml"

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
    "status": "PASS",
    "claim": "binary-packaging-contract-reference-only",
    "authoritative": False,
    "workflow_run": 34704117024,
    "head_sha": "be7a53c34a7ac27065f848ea3abc14b867673bde",
    "artifact_id": 10301282501,
    "artifact_sha256": "9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97",
    "binary_query_plan_sha256": "b26c95d381db242c3c7a87228044a37bac8696e211358149a08bb5b55f411bb9",
    "binary_contracts_json_sha256": "e44507d0dd73db913a91bd4852c452f783618aab0bd6a3790e4c4f4c40707b7b",
    "binary_contracts_tsv_sha256": "ef29ecdf03a35616a7cd0155a54a0d93828ff2af9bd9a3dcba37c0dbdb8bb1ca",
    "ubuntu_binary_packages": 147,
    "debian_binary_packages": 151,
    "common_binary_packages": 147,
    "ubuntu_only_binary_packages": 0,
    "debian_only_binary_packages": 4,
    "debian_only_packages": [
        "libkirigamiforms6",
        "libkirigamiformsprivatecards6",
        "libkirigamiformsprivateflat6",
        "libkirigamiformsprivatetemplates6",
    ],
    "framework_package_build_certification": "pending",
}
FAIL_NODES = {"karchive", "kholidays", "ktexttemplate"}
PASS_NODES = {
    "attica": ("6.30.0-0supralinux2", 34706416753, 10301851297, "f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27"),
    "kcodecs": ("6.30.0-0supralinux4", 34716761551, 10305050385, "d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45"),
    "kdbusaddons": ("6.30.0-0supralinux3", 34713034164, 10304340428, "2bfb451724808b5318625eee3df25a6104c9b6da77482737ac54eea058a7e799"),
    "threadweaver": ("6.30.0-0supralinux3", 34713034164, 10303986419, "6395f11ed633fb034b0bf61a95639ce00005e3211994b04924abeb306deed2b8"),
}
errors: list[str] = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot load {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(value, dict):
        raise SystemExit(f"ERROR: {path.relative_to(ROOT)} must contain an object")
    return value

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""

source = load(SOURCE_MANIFEST)
reference = load(REFERENCE_MANIFEST)
scope = read(SCOPE)
workflow = read(WORKFLOW)

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
require(reference.get("binary_contract_snapshot") == EXPECTED_BINARY_CONTRACT_SNAPSHOT, "Binary-contract PASS evidence changed without review")

references = reference.get("references", {})
require(references.get("ubuntu", {}).get("distribution") == "ubuntu", "Ubuntu reference distribution missing")
require(references.get("ubuntu", {}).get("series") == "resolute", "Ubuntu reference must be Resolute")
require(references.get("ubuntu", {}).get("components") == ["main", "universe"], "Ubuntu reference components changed")
require(references.get("debian", {}).get("distribution") == "debian", "Debian reference distribution missing")
require(references.get("debian", {}).get("series") == "sid", "Debian reference must be sid")
require(references.get("debian", {}).get("components") == ["main"], "Debian reference components changed")

policy = reference.get("policy", {})
for key in (
    "kde_upstream_remains_authority",
    "reference_packaging_may_not_disable_upstream_defaults_without_documented_reason",
    "reference_versions_do_not_select_kde_version",
    "reference_binary_names_are_inputs_for_compatibility_review_not_automatic_decisions",
):
    require(policy.get(key) is True, f"Packaging reference policy must keep {key}=true")

nodes = reference.get("nodes", {})
require(set(nodes) == source_ids, "Packaging-reference node set must exactly match Tier 1")
for node_id in sorted(source_ids):
    require(nodes.get(node_id) == {"source_package": f"kf6-{node_id}"}, f"{node_id}: source package mapping changed")

for node in source_nodes:
    if not isinstance(node, dict):
        continue
    node_id = node.get("id")
    if node_id in PASS_NODES:
        version, run, artifact, digest = PASS_NODES[node_id]
        packaging = node.get("packaging", {})
        require(node.get("state") == "PASS", f"{node_id}: actual package PASS must remain intact")
        require(packaging.get("state") == "PASS", f"{node_id}: packaging PASS must remain intact")
        require(packaging.get("package_version") == version, f"{node_id}: validated revision mismatch")
        require(packaging.get("downstream_eligible") is True, f"{node_id}: PASS must remain downstream eligible")
        passes = [item for item in packaging.get("evidence", []) if isinstance(item, dict) and item.get("result") == "PASS"]
        require(len(passes) == 1, f"{node_id}: exactly one current PASS evidence item expected")
        if passes:
            require(passes[0].get("workflow_run") == run, f"{node_id}: PASS run mismatch")
            require(passes[0].get("artifact_id") == artifact, f"{node_id}: PASS artifact mismatch")
            require(passes[0].get("artifact_sha256") == digest, f"{node_id}: PASS digest mismatch")
    elif node_id in FAIL_NODES:
        require(node.get("state") == "FAIL", f"{node_id}: real package FAIL must remain visible")
        require(node.get("packaging", {}).get("state") == "FAIL", f"{node_id}: packaging FAIL must remain visible")
        require(node.get("packaging", {}).get("downstream_eligible") is False, f"{node_id}: FAIL cannot feed downstream")
    else:
        require(node.get("packaging") == {"state":"pending"}, f"{node_id}: unattempted packaging must remain pending")
        require(node.get("state") == "pending", f"{node_id}: unattempted node must remain pending")

require(sum(1 for node in source_nodes if node.get("state") == "PASS") == 4, "Reference validator expects 4 actual package PASS nodes")
require(sum(1 for node in source_nodes if node.get("state") == "pending") == 22, "Reference validator expects 22 pending nodes")
require(sum(1 for node in source_nodes if node.get("state") == "FAIL") == 3, "Reference validator expects 3 real FAIL nodes")

for token in (
    "manifests/kde-frameworks-tier1.json",
    "manifests/kde-frameworks-tier1-packaging-reference.json",
    "scripts/run-kde-tier1-packaging-reference-snapshot.sh",
    "scripts/kde-tier1-packaging-reference-needed.sh",
    ".github/workflows/kde-tier1-packaging-reference.yml",
):
    require(token in scope, f"Packaging-reference scope must track input {token}")
require("docs/" not in scope, "Packaging-reference snapshot must not rerun for documentation-only changes")
require("validate_kde_tier1_packaging_reference.py" not in scope, "Packaging-reference snapshot must not rerun for validator-only changes")
require('git diff --name-only "${BEFORE}" "${AFTER}" --' in scope, "Packaging-reference scope must compare exact event delta")

for token in (
    "fetch-depth: 0",
    "github.event.before",
    "github.event.after",
    "github.event.pull_request.base.sha",
    "github.event.pull_request.head.sha",
    "scripts/kde-tier1-packaging-reference-needed.sh",
    "steps.scope.outputs.run == 'true'",
    "steps.scope.outputs.run == 'false'",
):
    require(token in workflow, f"Packaging-reference workflow missing event-delta invariant: {token}")
require("paths:" not in workflow, "Packaging-reference workflow must not rely on PR-wide paths filtering")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Frameworks Tier 1 packaging-reference policy: PASS")
print("Reference snapshots remain non-authoritative technical inputs")
print("Actual package states: 4 PASS; 22 pending; 3 FAIL; 0 BLOCKED")

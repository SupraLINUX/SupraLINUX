#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

def req(condition, message):
    if not condition:
        errors.append(message)

materialization = json.loads((ROOT / "manifests/kde-plasma-level0-materialization.json").read_text())
preflight = json.loads((ROOT / "manifests/kde-plasma-level0-materialization-preflight.json").read_text())
level0 = json.loads((ROOT / "manifests/kde-plasma-level0.json").read_text())
plasma = json.loads((ROOT / "manifests/kde-plasma.json").read_text())
lane = (ROOT / ".github/workflows/kde-plasma-lane.yml").read_text()

req(preflight.get("state") == "PASS", "materialization preflight must be closed PASS")
req(preflight.get("execution_authorized") is False, "closed preflight execution lock")
req(preflight.get("evidence", {}).get("artifact_id") == 11286979140, "preflight artifact binding")
req(preflight.get("evidence", {}).get("files", {}).get("result.json") == "cb8e6471aa1149e8335cde8d4d43c1d84916151187ecb11fda3b3d7f2cf9ed4f", "preflight result hash")
req(preflight.get("evidence", {}).get("package_execution_started") is False, "preflight package execution boundary")

req(materialization.get("state") == "execution-authorized", "materialization execution state")
req(materialization.get("execution_authorized") is True, "materialization authorization")
req(materialization.get("materialization_authorized") is True, "materialization gate authorization")
req(materialization.get("package_execution_authorized") is False, "materialization package lock")
req(materialization.get("consumes_package_attempt") is False, "materialization Attempt boundary")
req(materialization.get("canonical_package_state_effect") == "none", "materialization package state effect")
req(materialization.get("input", {}).get("selected_node_count") == 34, "materialization node count")
req(materialization.get("input", {}).get("preflight_artifact_id") == 11286979140, "materialization preflight input")
req(materialization.get("source_authority", {}).get("required_primary_fingerprint") == "0AAC775BB6437A8D9AF7A3ACFE0784117FBCE11D", "KDE signing fingerprint")
req(materialization.get("ubuntu_packaging_reference", {}).get("explicit_source_aliases") == {"discover": "plasma-discover"}, "materialization source alias")
req(materialization.get("execution", {}).get("max_parallel_nodes") == 6, "materialization parallelism")
req(materialization.get("next_gate_on_pass") == "plasma-level0-candidate-version-assignment", "materialization PASS next gate")

req(level0.get("state") == "materialization-pending", "Level 0 live materialization state")
req(level0.get("materialization_authorized") is True, "Level 0 materialization authorization")
req(level0.get("package_execution_authorized") is False, "Level 0 package lock")
req(level0.get("materialization_manifest") == "manifests/kde-plasma-level0-materialization.json", "Level 0 materialization manifest")
req(level0.get("next_gate") == "plasma-level0-materialization-evidence", "Level 0 materialization evidence gate")
req(all(node.get("state") == "materialization-pending" for node in level0.get("nodes", {}).values()), "all Level 0 nodes materialization pending")
req(all(node.get("candidate_package_version") is None for node in level0.get("nodes", {}).values()), "candidate versions remain deferred")

planning = plasma.get("planning", {})
req(planning.get("phase") == "level0-materialization", "Plasma live phase")
req(planning.get("status") == "level0-materialization-pending", "Plasma live status")
req(planning.get("materialization_authorized") is True, "Plasma live materialization authorization")
req(planning.get("package_execution_authorized") is False, "Plasma live package lock")
req(planning.get("next_gate") == "plasma-level0-materialization-evidence", "Plasma live next gate")

for token in (
    "level0-materialization-pending",
    "run-kde-plasma-level0-materialization.py",
    "kde-plasma-level0-materialization-",
):
    req(token in lane, f"Plasma lane materialization contract: {token}")

for path in (
    ROOT / "scripts/run-kde-plasma-level0-materialization.py",
    ROOT / "manifests/kde-plasma-level0-materialization.json",
):
    req(path.is_file(), f"materialization implementation missing: {path.name}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Plasma Level 0 materialization definition: PASS")
print("nodes=34 max_parallel=6 package_execution_authorized=false")
print("next_gate=plasma-level0-materialization-evidence")

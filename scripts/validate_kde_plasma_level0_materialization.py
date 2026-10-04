#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from plasma_lifecycle import validate as validate_lifecycle

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

errors.extend(validate_lifecycle(ROOT, plasma, level0, materialization))
req(materialization.get("package_execution_authorized") is False, "materialization package lock")
req(materialization.get("consumes_package_attempt") is False, "materialization Attempt boundary")
req(materialization.get("canonical_package_state_effect") == "none", "materialization package state effect")
req(materialization.get("input", {}).get("selected_node_count") == 34, "materialization node count")
req(materialization.get("input", {}).get("preflight_artifact_id") == 11286979140, "materialization preflight input")
req(materialization.get("source_authority", {}).get("required_primary_fingerprint") == "0AAC775BB6437A8D9AF7A3ACFE0784117FBCE11D", "KDE signing fingerprint")
req(materialization.get("ubuntu_packaging_reference", {}).get("explicit_source_aliases") == {"discover": "plasma-discover"}, "materialization source alias")
req(materialization.get("execution", {}).get("max_parallel_nodes") == 6, "materialization parallelism")
req(materialization.get("next_gate_on_pass") == "plasma-level0-candidate-version-assignment", "materialization PASS next gate")

req(level0.get("package_execution_authorized") is False, "Level 0 package lock")
req(level0.get("materialization_manifest") == "manifests/kde-plasma-level0-materialization.json", "Level 0 materialization manifest")

planning = plasma.get("planning", {})
req(planning.get("package_execution_authorized") is False, "Plasma live package lock")

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

print(f"KDE Plasma Level 0 materialization validation: PASS; state={materialization['state']}")
print("nodes=34 max_parallel=6 package_execution_authorized=false")
print(f"next_gate={planning['next_gate']}")

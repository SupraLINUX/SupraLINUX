#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "manifests/kde-tier3-build-level0.json").read_text())
planner = ROOT / "scripts/plan-kde-tier3-build-level0.py"
runner = (ROOT / "scripts/run-kde-tier3-build-level0.sh").read_text()

out = subprocess.check_output([sys.executable, str(planner)], text=True)
payload = json.loads(out)
matrix = json.loads(payload["matrix"])
planned = [row["node"] for row in matrix["include"]]
expected = manifest["selected_nodes"]

if manifest.get("state") == "active-pending-ci" and manifest.get("execution_authorized") is True:
    if payload["run"] != "true":
        raise SystemExit("active Level0 campaign unexpectedly planned run=false")
    if planned != expected:
        raise SystemExit(f"active Level0 matrix must contain all selected nodes in canonical order: expected={expected} actual={planned}")

required_states = {
    "prepared-pending-build",
    "prepared-pending-revalidation",
    "remediation-pending-build",
}
for state in required_states:
    if state not in runner:
        raise SystemExit(f"runner missing runnable lifecycle state: {state}")

print("KDE Tier 3 Level 0 planner/runner scope: PASS")
print(f"planned_nodes={len(planned)}")

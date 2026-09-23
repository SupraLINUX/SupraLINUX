#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/"manifests/kde-tier3-build-level1.json").read_text())
planner=ROOT/"scripts/plan-kde-tier3-build-level1.py"
runner=(ROOT/"scripts/run-kde-tier3-build-level1.sh").read_text()

payload=json.loads(subprocess.check_output([sys.executable,str(planner)],text=True))
matrix=json.loads(payload["matrix"])
planned=[row["node"] for row in matrix["include"]]

if manifest.get("execution_authorized") is False:
    if payload["run"]!="false" or planned:
        raise SystemExit("inactive Level1 gate must schedule zero package jobs")
elif manifest.get("state")=="active-pending-ci":
    if payload["run"]!="true" or planned!=manifest["selected_nodes"]:
        raise SystemExit(f"active Level1 matrix mismatch: {planned}")

for token in (
    "manifests/kde-tier3-build-level1.json",
    ".work/kde-tier3-build-level1",
    "evidence/kde-tier3-build-level1",
    "buildinfo-proof-contracts.tsv",
    "consumer-runtime-check.log",
    "provider_closure_input_ids",
    "provider-closure.json",
    "runtime_validation_input_ids",
    "runtime-validation.json",
    "declared-runtime-input-proof",
):
    if token not in runner:
        raise SystemExit(f"Level1 runner missing contract token: {token}")

print("KDE Tier 3 Level 1 planner/runner scope: PASS")
print(f"planned_nodes={len(planned)}")

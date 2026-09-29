#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/"manifests/kde-tier3-build-level3.json").read_text())
p=json.loads(subprocess.check_output([sys.executable,str(ROOT/"scripts/plan-kde-tier3-build-level3.py")],text=True))
planned=[x["node"] for x in json.loads(p["matrix"])["include"]]
expected=["ktexteditor","purpose"]

if m.get("selected_nodes") != expected:
    raise SystemExit("Level3 selected-node set drift")
if m.get("execution_authorized") is False and (p["run"]!="false" or planned):
    raise SystemExit("inactive Level3 gate scheduled package jobs")
if m.get("state")=="active-pending-ci" and (p["run"]!="true" or planned!=expected):
    raise SystemExit("active Level3 matrix mismatch")

runner=(ROOT/"scripts/run-kde-tier3-build-level3.sh").read_text()
for token in ("manifests/kde-tier3-build-level3.json",".work/kde-tier3-build-level3","evidence/kde-tier3-build-level3","buildinfo-proof-contracts.tsv","provider_closure_input_ids","support-closure.json","SBUILD_ENABLE_NETWORK","STAGE=sbuild","PACKAGE_ATTEMPTED=true"):
    if token not in runner: raise SystemExit("Level3 runner missing "+token)
if runner.index("STAGE=sbuild") >= runner.index("PACKAGE_ATTEMPTED=true"):
    raise SystemExit("Level3 Package Attempt marker ordering drift")
for node,cfg in m["nodes"].items():
    if cfg.get("sbuild_enable_network") is not False: raise SystemExit(node+": network must remain disabled")

wf=(ROOT/".github/workflows/kde-tier3-build-level3.yml").read_text()
if "workflow_call:" not in wf or "\n  pull_request:" in wf:
    raise SystemExit("Level3 must be reusable through the single PR router")
print("KDE Tier 3 Level 3 planner/runner scope: PASS")
print(f"planned_nodes={len(planned)}")

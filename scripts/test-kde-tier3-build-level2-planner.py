#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]; m=json.loads((ROOT/"manifests/kde-tier3-build-level2.json").read_text())
p=json.loads(subprocess.check_output([sys.executable,str(ROOT/"scripts/plan-kde-tier3-build-level2.py")],text=True)); planned=[x["node"] for x in json.loads(p["matrix"])["include"]]
if m.get("execution_authorized") is False and (p["run"]!="false" or planned): raise SystemExit("inactive Level2 gate scheduled package jobs")
if m.get("state")=="active-pending-ci" and (p["run"]!="true" or planned!=m["selected_nodes"]): raise SystemExit("active Level2 matrix mismatch")
runner=(ROOT/"scripts/run-kde-tier3-build-level2.sh").read_text()
for token in ("manifests/kde-tier3-build-level2.json",".work/kde-tier3-build-level2","evidence/kde-tier3-build-level2","buildinfo-proof-contracts.tsv","provider_closure_input_ids","provider-closure.json","SBUILD_ENABLE_NETWORK"):
    if token not in runner: raise SystemExit("Level2 runner missing "+token)
for node,cfg in m["nodes"].items():
    if cfg.get("sbuild_enable_network") is not False: raise SystemExit(node+": network must remain disabled")
h=m["deferred_runtime_validation_handoff"]["knewstuff"]
if h["requires_level2_pass"]!=["kcmutils"] or h["effect"]!="runtime-validation-gate-only-no-auto-PASS": raise SystemExit("KNewStuff handoff drift")
print("KDE Tier 3 Level 2 planner/runner scope: PASS"); print(f"planned_nodes={len(planned)}")

#!/usr/bin/env python3
from pathlib import Path
import json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]; m=json.loads((ROOT/"manifests/kde-tier3-build-level2.json").read_text())
p=json.loads(subprocess.check_output([sys.executable,str(ROOT/"scripts/plan-kde-tier3-build-level2.py")],text=True)); planned=[x["node"] for x in json.loads(p["matrix"])["include"]]
if m.get("execution_authorized") is False and (p["run"]!="false" or planned): raise SystemExit("inactive Level2 gate scheduled package jobs")
if m.get("state")=="active-pending-ci" and (p["run"]!="true" or planned!=m["selected_nodes"]): raise SystemExit("active Level2 matrix mismatch")
runner_path=ROOT/"scripts/run-kde-tier3-build-level2.sh"
if not runner_path.is_file() or not os.access(runner_path,os.X_OK):
    raise SystemExit("Level2 runner must be executable")
runner=runner_path.read_text()
for token in ("manifests/kde-tier3-build-level2.json",".work/kde-tier3-build-level2","evidence/kde-tier3-build-level2","buildinfo-proof-contracts.tsv","provider_closure_input_ids","provider-closure.json","SBUILD_ENABLE_NETWORK"):
    if token not in runner: raise SystemExit("Level2 runner missing "+token)
for node,cfg in m["nodes"].items():
    if cfg.get("sbuild_enable_network") is not False: raise SystemExit(node+": network must remain disabled")
    if m.get("next_attempt")==3 and cfg.get("support_input_ids")!=["breeze-icons","kdoctools"]:
        raise SystemExit(node+": Attempt3 support closure mismatch")
if m.get("next_attempt")==3 and set(m.get("support_predecessors",{}))!={"breeze-icons","kdoctools"}:
    raise SystemExit("Attempt3 support predecessor registry mismatch")
h=m["deferred_runtime_validation_handoff"]["knewstuff"]
if h["requires_level2_pass"]!=["kcmutils"] or h["effect"]!="runtime-validation-gate-only-no-auto-PASS": raise SystemExit("KNewStuff handoff drift")
print("KDE Tier 3 Level 2 planner/runner scope: PASS"); print(f"planned_nodes={len(planned)}")

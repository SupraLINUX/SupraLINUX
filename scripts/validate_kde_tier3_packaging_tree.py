#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier3-package-contracts.json")
selected=c.get("selected_nodes",[])
capture=c.get("packaging_tree_capture",{})

req(c.get("state") in {"packaging-tree-pending","packaging-tree-pass","contracts-ready","materialized"},"Tier3 packaging-tree lifecycle")
req(c.get("reference_capture",{}).get("status")=="PASS","packaging tree requires reference capture PASS")
req(len(selected)==20,"Tier3 packaging-tree node count")
req(capture.get("claim")=="technical-packaging-tree-only" and capture.get("authoritative") is False,"packaging-tree non-authority")
req(capture.get("package_state_effect")=="none","packaging-tree package-state semantics")
req(capture.get("selected_sides")==["ubuntu","debian"],"packaging-tree selected sides")

for node in selected:
    refs=c["nodes"][node].get("technical_references",{})
    for side in ("ubuntu","debian"):
        rr=refs.get(side,{})
        req(rr.get("source_package")==f"kf6-{node}",f"{node}/{side}: source package")
        req(isinstance(rr.get("version"),str) and rr.get("version"),f"{node}/{side}: source version")
        for prefix in ("dsc","debian_tar","orig_tar"):
            req(isinstance(rr.get(prefix+"_file"),str) and rr.get(prefix+"_file"),f"{node}/{side}: {prefix} file")
            req(len(rr.get(prefix+"_sha256",""))==64,f"{node}/{side}: {prefix} hash")

if capture.get("status")=="pending-ci":
    req(c.get("state")=="packaging-tree-pending","pending packaging-tree state")
    req(capture.get("evidence") is None,"pending packaging-tree evidence")
    req(capture.get("execution_request",{}).get("status")=="requested","pending packaging-tree execution request")
else:
    req(capture.get("status")=="PASS","packaging-tree PASS status")
    ev=capture.get("evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_state_effect")=="none","packaging-tree PASS semantics")
    req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),"packaging-tree run/job")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"packaging-tree artifact")
    req(len(ev.get("index_sha256",""))==64 and ev.get("nodes")==20 and ev.get("sides")==40,"packaging-tree index evidence")
    trees=c.get("packaging_trees",{})
    req(set(trees)==set(selected),"promoted packaging-tree node set")
    for node,sides in trees.items():
        req(set(sides)=={"ubuntu","debian"},f"{node}: promoted packaging-tree sides")
        for side,r in sides.items():
            req(len(r.get("tree_sha256",""))==64,f"{node}/{side}: tree hash")
            req(len(r.get("control_summary_sha256",""))==64,f"{node}/{side}: control summary hash")
            req(len(r.get("packaging_files_sha256",""))==64,f"{node}/{side}: packaging files hash")
    req(capture.get("execution_request",{}).get("status")=="consumed","packaging-tree execution request consumed")

for path in (
 "scripts/capture_kde_tier3_packaging_trees.py",
 "scripts/kde-tier3-packaging-tree-needed.sh",
 "scripts/test-kde-tier3-packaging-tree-scope.sh",
 ".github/workflows/kde-tier3-packaging-tree.yml",
):
    req((ROOT/path).exists(),f"missing Tier3 packaging-tree component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 packaging-tree historical evidence: PASS")
print("status="+capture["status"])

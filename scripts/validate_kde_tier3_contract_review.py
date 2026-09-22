#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier3-package-contracts.json")
t=load("manifests/kde-frameworks-tier3.json")
r=c.get("contract_review",{})
selected=c.get("selected_nodes",[])

req(c.get("state") in {"packaging-tree-pass","contracts-ready","materialized"},"Tier3 contract review requires packaging-tree PASS")
req(c.get("packaging_tree_capture",{}).get("status")=="PASS","Tier3 contract review packaging-tree prerequisite")
req(len(selected)==20,"Tier3 contract review node count")
req(r.get("status") in {"pending-ci","PASS"},"Tier3 contract-review lifecycle")
req(r.get("claim")=="supralinux-package-contract-review","Tier3 contract-review claim")
req(r.get("authority")=="supralinux" and r.get("source_authority")=="kde-upstream","Tier3 review authority boundary")
req(r.get("package_state_effect")=="none","Tier3 review package-state semantics")
req(r.get("selected_nodes")==selected,"Tier3 review selected nodes")
req(r.get("materialization_authorized") is False,"Tier3 review must not authorize materialization while pending/review-only")
req(r.get("package_build_authorized") is False,"Tier3 review must not authorize builds")
req(t.get("discovery_policy",{}).get("phase") in {"package-contract-review","package-contract-review-pass","materialization"},"Tier3 canonical review phase")
req(t.get("support_components",{}).get("next_gate") in {"tier3-package-contract-review","tier3-materialization"},"Tier3 canonical review next gate")

if r.get("status")=="pending-ci":
    req(r.get("evidence") is None,"pending Tier3 review evidence")
    req(r.get("execution_request",{}).get("status")=="requested","pending Tier3 review execution request")
    for n in t.get("nodes",[]):
        req(n.get("state")=="pending",f"{n.get('id')}: review must not alter package state")
        req(n.get("planning",{}).get("readiness")=="package-contract-review-pending",f"{n.get('id')}: review-pending readiness")
        req(n.get("planning",{}).get("package_contract")=="review-pending",f"{n.get('id')}: review-pending contract")
else:
    ev=r.get("evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_state_effect")=="none","Tier3 review PASS evidence semantics")
    req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),"Tier3 review run/job")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"Tier3 review artifact")
    req(len(ev.get("review_sha256",""))==64 and ev.get("nodes")==20,"Tier3 review digest/node evidence")
    req(r.get("execution_request",{}).get("status")=="consumed","Tier3 review execution request consumed")

for path in (
 "scripts/review_kde_tier3_package_contracts.py",
 "scripts/kde-tier3-contract-review-needed.sh",
 "scripts/test-kde-tier3-contract-review-scope.sh",
 ".github/workflows/kde-tier3-contract-review.yml",
 "docs/kde-tier3-contract-review.md",
):
    req((ROOT/path).exists(),f"missing Tier3 contract-review component: {path}")

doc=(ROOT/"docs/kde-tier3-contract-review.md").read_text()
for token in ("KDE upstream","Ubuntu","Debian","package_state_effect=none","materialization"):
    req(token in doc,f"Tier3 contract-review docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 contract-review definition: PASS")
print("status="+r["status"])

#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

m=load("manifests/kde-tier3-support-package-contracts.json")
tier3=load("manifests/kde-frameworks-tier3.json")

req(m.get("state") in {"reference-capture-pass","contracts-ready","materialized"},"packaging-tree requires source-record capture PASS")
rc=m.get("reference_capture",{})
req(rc.get("status")=="PASS","packaging-tree requires reference capture PASS")
req(isinstance(rc.get("evidence",{}).get("artifact_id"),int),"reference capture artifact linkage")

capture=m.get("packaging_tree_capture",{})
req(capture.get("status") in {"pending-ci","PASS"},"support packaging-tree lifecycle")
req(capture.get("claim")=="technical-packaging-tree-only" and capture.get("authoritative") is False,"packaging-tree non-authority")
req(capture.get("package_state_effect")=="none","packaging-tree package-state semantics")
req(capture.get("selected_components")==["breeze-icons","kdoctools","kded"],"packaging-tree component set")
req(capture.get("selected_sides")==["ubuntu","debian"],"packaging-tree side set")

refs=m.get("technical_references",{})
for node in capture.get("selected_components",[]):
    r=refs.get(node,{})
    for side in capture.get("selected_sides",[]):
        rr=r.get(side,{})
        req(rr.get("source_package"),f"{node}/{side}: source package")
        req(rr.get("version"),f"{node}/{side}: source version")
        checks=rr.get("checksums_sha256",[])
        req(any(x.get("file","").endswith(".dsc") and len(x.get("sha256",""))==64 for x in checks),f"{node}/{side}: dsc pin")
        req(any(".debian.tar." in x.get("file","") and len(x.get("sha256",""))==64 for x in checks),f"{node}/{side}: Debian tar pin")
        req(any(".orig.tar." in x.get("file","") and not x.get("file","").endswith(".asc") and len(x.get("sha256",""))==64 for x in checks),f"{node}/{side}: orig tar pin")

if capture.get("status")=="pending-ci":
    req(capture.get("evidence") is None,"pending packaging-tree evidence")
else:
    ev=capture.get("evidence",{})
    req(ev.get("result")=="PASS" and ev.get("package_state_effect")=="none","packaging-tree PASS evidence")
    req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),"packaging-tree run/job evidence")
    req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,"packaging-tree artifact evidence")
    req(len(ev.get("index_sha256",""))==64,"packaging-tree index digest")
    trees=m.get("packaging_trees",{})
    req(set(trees)=={"breeze-icons","kdoctools","kded"},"promoted packaging-tree set")
    for node, sides in trees.items():
        req(set(sides)=={"ubuntu","debian"},f"{node}: promoted packaging-tree sides")
        for side,record in sides.items():
            req(len(record.get("tree_sha256",""))==64,f"{node}/{side}: tree SHA-256")
            req(record.get("source_version")==refs[node][side]["version"],f"{node}/{side}: source version linkage")
            req(record.get("source_package")==refs[node][side]["source_package"],f"{node}/{side}: source package linkage")

support=tier3.get("support_components",{})
req(support.get("package_contract_manifest")=="manifests/kde-tier3-support-package-contracts.json","canonical support contract manifest")
req(support.get("next_gate") in {"support-contract-tree-capture","support-contract-review"},"canonical packaging-tree next gate")

for path in (
 "scripts/run-kde-tier3-support-packaging-tree-capture.sh",
 "scripts/kde-tier3-support-packaging-tree-needed.sh",
 "scripts/test-kde-tier3-support-packaging-tree-scope.sh",
 ".github/workflows/kde-tier3-support-packaging-tree.yml",
):
    req((ROOT/path).exists(),f"missing support packaging-tree component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 support packaging-tree definition: PASS")
print("status="+capture["status"])

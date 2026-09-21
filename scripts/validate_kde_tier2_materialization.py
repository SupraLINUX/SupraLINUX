#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

contracts=load("manifests/kde-tier2-package-contracts.json")
tier2=load("manifests/kde-frameworks-tier2.json")
selected=contracts.get("selected_nodes",[])
mat=contracts.get("materialization",{})
state=contracts.get("state")
canonical={n["id"]:n for n in tier2["nodes"]}

req(mat.get("method")=="kde-authority-source-plus-pinned-debian-tree","materialization method")
req(mat.get("package_state_effect")=="none" and mat.get("package_attempted") is False,"materialization package-state semantics")
req(mat.get("maintainer_during_ci")=="SupraLINUX Build System <build@supralinux.invalid>","CI maintainer marker")
req(mat.get("publication_blocker")=="replace-ci-maintainer-with-approved-project-contact","publication blocker")

if state=="reference-capture-pending":
    req(mat.get("status")=="blocked-reference-capture","pending references must block materialization")
    req(set(mat.get("targets",[]))==set(selected),"blocked target set")
else:
    req(state in {"reference-capture-pass","materialized"},"materializable contract state")
    req(mat.get("status") in {"pending-ci","PASS"},"materialization status")
    req(set(mat.get("targets",[])) <= set(selected),"materialization targets selected")
    for node_id in selected:
        c=contracts["nodes"][node_id]
        refs=c.get("technical_references",{})
        req(refs.get("debian",{}).get("version")=="6.30.0-1",f"{node_id}: Debian 6.30 reference")
        req(len(refs.get("debian",{}).get("debian_tar_sha256",""))==64,f"{node_id}: pinned Debian tree digest")
    if mat.get("status")=="PASS":
        req(mat.get("result")=="PASS","materialization result")
        req(set(mat.get("evidence",{})) <= set(selected),"materialization evidence selected")

if "kpackage" in selected:
    kp=contracts["nodes"]["kpackage"]
    req(kp.get("build_depends_remove")==["libkf6doctools-dev"],"KPackage DocTools Build-Depends removal")
    req(kp.get("selected_profile",{}).get("CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools") is True,"KPackage DocTools CMake disable")

for node_id in selected:
    n=canonical[node_id]
    req(n.get("state")=="pending",f"{node_id}: materialization never promotes package state")
    req(n.get("planning",{}).get("readiness") in {"package-contract-ready","build-ready"},f"{node_id}: readiness")

for path in (
  "scripts/materialize_kde_tier2_package.py",
  "scripts/run-kde-tier2-package-materialization.sh",
  "scripts/kde-tier2-materialization-needed.sh",
  "scripts/plan-kde-tier2-materialization.py",
  ".github/workflows/kde-tier2-package-materialization.yml",
):
    req((ROOT/path).exists(),f"missing materialization component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 package-materialization definition: PASS")
print(f"state={state} status={mat.get('status')} nodes={selected}")

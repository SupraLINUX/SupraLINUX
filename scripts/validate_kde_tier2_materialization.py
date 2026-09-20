#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

contracts=load("manifests/kde-tier2-package-contracts.json")
tier2=load("manifests/kde-frameworks-tier2.json")
expected=contracts.get("selected_nodes",[])
req(contracts.get("state")=="reference-capture-pass","reference capture must be PASS before materialization")
mat=contracts.get("materialization",{})
req(mat.get("status") in {"pending-ci","PASS"},"materialization status")
req(mat.get("method")=="kde-authority-source-plus-pinned-debian-tree","materialization method")
req(mat.get("package_state_effect")=="none" and mat.get("package_attempted") is False,"materialization package-state semantics")
req(mat.get("maintainer_during_ci")=="SupraLINUX Build System <build@supralinux.invalid>","CI maintainer marker")
req(mat.get("publication_blocker")=="replace-ci-maintainer-with-approved-project-contact","publication blocker")

canonical={n["id"]:n for n in tier2["nodes"]}
for node_id in expected:
    n=canonical[node_id]
    c=contracts["nodes"][node_id]
    req(n.get("state")=="pending",f"{node_id}: materialization does not promote package state")
    req(n.get("planning",{}).get("readiness")=="package-contract-ready",f"{node_id}: readiness")
    req(n.get("planning",{}).get("package_contract")=="not-materialized",f"{node_id}: contract not promoted before materialization PASS")
    req(c.get("technical_references",{}).get("debian",{}).get("version")=="6.30.0-1",f"{node_id}: Debian 6.30 packaging reference")
    req(len(c.get("technical_references",{}).get("debian",{}).get("debian_tar_sha256",""))==64,f"{node_id}: pinned Debian tree digest")

for node_id in ("knotifications","kstatusnotifieritem","kunitconversion"):
    c=contracts["nodes"][node_id]
    req(c.get("python_runtime_package"),f"{node_id}: Python runtime package mapping")
    req(c.get("selected_profile",{}).get("BUILD_PYTHON_BINDINGS") is True,f"{node_id}: upstream Python binding profile")

for path in (
  "scripts/materialize_kde_tier2_package.py",
  "scripts/run-kde-tier2-package-materialization.sh",
  "scripts/kde-tier2-materialization-needed.sh",
  "scripts/test-kde-tier2-materialization-scope.sh",
  ".github/workflows/kde-tier2-package-materialization.yml",
):
    req((ROOT/path).exists(),f"missing materialization component: {path}")

doc=(ROOT/"docs/kde-tier2-package-materialization.md").read_text()
for token in ("KDE upstream","debian.tar.xz","BUILD_PYTHON_BINDINGS","build@supralinux.invalid","not a package PASS"):
    req(token in doc,f"materialization docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 package-materialization definition: PASS")
print(f"nodes={len(expected)} status={mat.get('status')} package-state-effect=none")

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
deps=load("manifests/kde-frameworks-tier2-dependencies.json")

expected=["kcrash","knotifications","kstatusnotifieritem","kunitconversion","syndication"]
req(contracts.get("schema")==1,"contract schema")
req(contracts.get("state") in {"reference-capture-pending","reference-capture-pass","materialized"},"contract state")
req(contracts.get("source_authority")=="kde-upstream" and contracts.get("packaging_authority")=="supralinux","authority split")
req(contracts.get("frameworks_series")=="6.30.0","Frameworks series")
req(contracts.get("selected_nodes")==expected,"selected contract node order")
req(contracts.get("compatibility_reference",{}).get("ubuntu",{}).get("role")=="technical-reference-only","Ubuntu reference role")
req(contracts.get("compatibility_reference",{}).get("debian",{}).get("role")=="technical-reference-only","Debian reference role")

canonical={n["id"]:n for n in tier2["nodes"]}
dep_nodes=deps["nodes"]
for node_id in expected:
    c=contracts["nodes"].get(node_id,{})
    n=canonical[node_id]
    req(n.get("state")=="pending","contract node must remain package-state pending")
    req(n.get("planning",{}).get("readiness")=="package-contract-ready",f"{node_id}: canonical readiness")
    req(n.get("planning",{}).get("package_contract")=="not-materialized",f"{node_id}: package contract not yet promoted")
    req(c.get("upstream_version")=="6.30.0",f"{node_id}: version")
    req(c.get("source_sha256")==n.get("source_sha256"),f"{node_id}: source SHA")
    req(c.get("source_package")==f"kf6-{node_id}",f"{node_id}: Ubuntu-compatible source package")
    req(c.get("package_version_candidate")=="6.30.0-0supralinux1",f"{node_id}: first candidate revision")
    req(c.get("cmake_target","").startswith("KF6::"),f"{node_id}: CMake target")
    req(c.get("soname","").endswith(".so.6"),f"{node_id}: SONAME")
    req(dep_nodes[node_id].get("provider_audit")=="PASS",f"{node_id}: provider audit PASS")
    req(c.get("compatibility_binary_packages"),f"{node_id}: compatibility binary package set")

for node_id,module,pkg in (
    ("knotifications","KNotifications","python3-kf6notifications"),
    ("kstatusnotifieritem","KStatusNotifierItem","python3-kf6statusnotifieritem"),
    ("kunitconversion","KUnitConversion","python3-kf6unitconversion"),
):
    c=contracts["nodes"][node_id]
    req(c.get("python_module")==module,f"{node_id}: upstream Python module")
    req(c.get("selected_profile",{}).get("BUILD_PYTHON_BINDINGS") is True,f"{node_id}: Python bindings selected")
    req(pkg in c.get("supralinux_additional_binary_packages",[]),f"{node_id}: Python binary split")

req(contracts["nodes"]["knotifications"]["selected_profile"].get("BUILD_QML_IF_PROVIDER_AVAILABLE") is True,"KNotifications QML capability preserved")

doc=(ROOT/"docs/kde-tier2-package-contracts.md").read_text()
for token in ("technical reference","python3-kf6notifications","python3-kf6statusnotifieritem","python3-kf6unitconversion","not a package PASS"):
    req(token in doc,f"contract docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 package-contract draft: PASS")
print("nodes=5; reference capture pending; package state unchanged")

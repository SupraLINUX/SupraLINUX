#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier3-support-build-level0.json")
a=load("manifests/kde-tier3-support-build-level0-attempts.json")
mat=load("manifests/kde-tier3-support-materialization.json")
deps=load("manifests/kde-frameworks-tier3-dependencies.json")
tier3=load("manifests/kde-frameworks-tier3.json")
tier1=load("manifests/kde-frameworks-tier1.json")
dag=load("manifests/kde-dag.json")

req(c.get("schema")==1 and c.get("authority")=="kde-upstream","support build level0 schema/authority")
req(c.get("role")=="support-binary-build-level0","support build level0 role")
req(c.get("frameworks_series")=="6.30.0","support build level0 series")
req(c.get("state") in {"pending-ci","PARTIAL","PASS"},"support build level0 lifecycle")
req(c.get("selected_nodes")==["breeze-icons","kdoctools"],"support build level0 selected nodes")
req(c.get("package_state_effect")=="real-package-build-on-PASS","support build package-state semantics")
blocked=c.get("blocked_nodes",{}).get("kded",{})
if c.get("state")=="PASS":
    req(blocked.get("state")=="READY" and blocked.get("previously_blocked_by")=="kdoctools","KDED must be READY after KDocTools PASS")
    req(blocked.get("unblocked_by",{}).get("artifact_id")==10682066198,"KDED unblock evidence")
    req(blocked.get("next_gate")=="support-build-level1","KDED next support gate")
else:
    req(blocked.get("state")=="BLOCKED" and blocked.get("blocked_by")=="kdoctools","KDED must be BLOCKED by KDocTools before level0 PASS")
req(c.get("materialization_manifest")=="manifests/kde-tier3-support-materialization.json","materialization manifest linkage")
req(mat.get("state")=="PASS" and all(n.get("state")=="materialized" for n in mat.get("nodes",{}).values()),"level0 requires materialization PASS")

ecm=c.get("shared_predecessors",{}).get("extra_cmake_modules",{})
canon_ecm=dag.get("nodes",{}).get("extra-cmake-modules",{})
req(canon_ecm.get("state")=="PASS","canonical ECM PASS")
req(ecm.get("version")==canon_ecm.get("package_version"),"ECM version pin")
req(any(e.get("result")=="PASS" and e.get("artifact_id")==ecm.get("artifact_id") and e.get("artifact_sha256")==ecm.get("artifact_sha256") for e in canon_ecm.get("evidence",[])),"ECM PASS artifact pin")

canon1={n["id"]:n for n in tier1.get("nodes",[])}
for pred in ("karchive","ki18n"):
    cfg=c.get("retained_predecessors",{}).get(pred,{})
    n=canon1.get(pred,{})
    req(n.get("state")=="PASS" and n.get("packaging",{}).get("downstream_eligible") is True,f"{pred}: canonical downstream PASS")
    req(cfg.get("version")==n.get("packaging",{}).get("package_version"),f"{pred}: version pin")
    req(any(e.get("result")=="PASS" and e.get("artifact_id")==cfg.get("artifact_id") and e.get("artifact_sha256")==cfg.get("artifact_sha256") for e in n.get("packaging",{}).get("evidence",[])),f"{pred}: PASS artifact pin")
    req(cfg.get("dev_package") in cfg.get("debs",{}),f"{pred}: dev package retained")

nodes=c.get("nodes",{})
req(set(nodes)=={"breeze-icons","kdoctools"},"level0 node set")
expected={
 "breeze-icons":{
   "version":"4:6.30.0-0supralinux1","runtime":"libkf6breezeicons6","dev":"libkf6breezeicons-dev",
   "soname":"libKF6BreezeIcons.so.6","cmake":"KF6BreezeIcons","target":"KF6::BreezeIcons",
   "preds":[],"artifact":10680459412,
 },
 "kdoctools":{
   "version":"6.30.0-0supralinux1","runtime":"libkf6doctools6","dev":"libkf6doctools-dev",
   "soname":"libKF6DocTools.so.6","cmake":"KF6DocTools","target":"KF6::DocTools",
   "preds":["karchive","ki18n"],"artifact":10680938435,
 },
}
support=deps.get("support_components",{})
for node,e in expected.items():
    n=nodes.get(node,{})
    req(n.get("state") in {"prepared-pending-build","remediation-pending-build","PASS"},f"{node}: level0 state")
    req(n.get("package_version")==e["version"],f"{node}: package version")
    req(n.get("runtime_package")==e["runtime"] and n.get("dev_package")==e["dev"],f"{node}: runtime/dev contract")
    req(n.get("soname")==e["soname"],f"{node}: SONAME")
    req(n.get("cmake_package")==e["cmake"] and n.get("cmake_target")==e["target"],f"{node}: CMake consumer contract")
    req(n.get("predecessors")==e["preds"],f"{node}: predecessor set")
    m=n.get("materialization",{})
    req(m.get("workflow_run")==35698463205 and m.get("artifact_id")==e["artifact"],f"{node}: materialization evidence")
    req(len(m.get("artifact_sha256",""))==64 and len(m.get("dsc_sha256",""))==64 and len(m.get("debian_tar_sha256",""))==64 and len(m.get("orig_tar_sha256",""))==64,f"{node}: materialization hashes")
    req(support.get(node,{}).get("readiness") in {"materialized","PASS"},f"{node}: canonical support readiness")
    if n.get("state")=="PASS":
        ev=n.get("pass_evidence",{})
        req(ev.get("result")=="PASS" and ev.get("package_attempted") is True,f"{node}: PASS evidence semantics")
        req(ev.get("downstream_eligible") is True,f"{node}: downstream eligibility")
        req(isinstance(ev.get("workflow_run"),int) and isinstance(ev.get("job_id"),int),f"{node}: run/job evidence")
        req(isinstance(ev.get("artifact_id"),int) and len(ev.get("artifact_sha256",""))==64,f"{node}: artifact evidence")

req(a.get("schema")==1 and a.get("batch")=="tier3-support-build-level0","level0 attempt ledger")
req(set(a.get("nodes",{}))=={"breeze-icons","kdoctools"},"level0 attempt ledger nodes")
if c.get("state")=="PASS":
    summary=c.get("evidence_summary",{})
    req(summary.get("result")=="PASS" and summary.get("workflow_run")==35700002095,"level0 PASS summary")
    req(summary.get("rootfs_sha256")=="e649388bcf5e02372714f59dde3579cf0c9c9f2e42a2f94bd4a358f9a8a8811e","level0 rootfs SHA")
    for node in ("breeze-icons","kdoctools"):
        attempts=a.get("nodes",{}).get(node,[])
        req(len(attempts)==1 and attempts[0].get("result")=="PASS",f"{node}: one recorded PASS attempt")
        req(attempts[0].get("workflow_run")==35700002095,f"{node}: attempt workflow evidence")
req(tier3.get("support_components",{}).get("next_gate") in {"support-build-level0","support-build-level1","tier3-provider-audit","tier3-package-contracts","tier3-build","tier3-package-contract-tree-capture","tier3-package-contract-review","tier3-materialization"},"canonical level0 gate")
req(c.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

for path in (
 "scripts/plan-kde-tier3-support-build-level0.py",
 "scripts/validate-kde-tier3-support-level0-retained-inputs.py",
 "scripts/run-kde-tier3-support-build-level0.sh",
 "scripts/kde-tier3-support-build-level0-needed.sh",
 "scripts/test-kde-tier3-support-build-level0-scope.sh",
 ".github/workflows/kde-tier3-support-build-level0.yml",
 "docs/kde-tier3-support-build-level0.md",
):
    req((ROOT/path).exists(),f"missing level0 component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 support build level 0 definition: PASS")
print("state="+c["state"])

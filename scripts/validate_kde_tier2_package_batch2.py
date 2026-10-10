#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier2-package-campaign-batch2.json")
a=load("manifests/kde-tier2-package-batch2-attempts.json")
plan=load("manifests/kde-tier2-campaign-plan.json")
contracts=load("manifests/kde-tier2-package-contracts.json")
tier2=load("manifests/kde-frameworks-tier2.json")
tier1=load("manifests/kde-frameworks-tier1.json")
dag=load("manifests/kde-dag.json")

expected=["kcrash","knotifications","kstatusnotifieritem","kunitconversion","syndication"]
req(c.get("schema")==1 and c.get("batch")=="tier2-batch-2","Batch2 identity")
req(c.get("selected_nodes")==expected,"Batch2 selected nodes")
req(c.get("scheduling",{}).get("fail_fast") is False,"Batch2 fail-fast policy")
req(c.get("semantics",{}).get("fail_requires")=="node-owned-root-cause","FAIL ownership")
req(c.get("semantics",{}).get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

canon={n["id"]:n for n in tier2["nodes"]}
pass_nodes={n for n in expected if c["nodes"][n].get("state")=="PASS"}
remat_nodes={n for n in expected if c["nodes"][n].get("state")=="rematerialization-pending"}
runnable={n for n in expected if c["nodes"][n].get("state") in {"prepared-pending-build","remediation-pending-build"}}
req(pass_nodes==set(expected),"Batch2 final PASS set")
req(remat_nodes|runnable|pass_nodes==set(expected),"Batch2 node state partition")
req(set(plan.get("retained_pass",[])) >= {"kauth","kcrash"},"generated plan retains KCrash")
req(runnable <= set(plan.get("build_queue",[])),"Batch2 runnable nodes must be present in the global build queue")
req(set(plan.get("build_queue",[])).isdisjoint(pass_nodes),"Batch2 retained PASS nodes must be absent from the global build queue")
req(set(plan.get("package_contract_ready",[])) >= remat_nodes,"rematerialization nodes remain contract-ready")

for node_id in expected:
    n=c["nodes"][node_id]; cn=canon[node_id]; contract=contracts["nodes"][node_id]
    req(n.get("source_sha256")==contract.get("source_sha256"),f"{node_id}: source SHA")
    req(n.get("package_version")==contract.get("package_version_candidate"),f"{node_id}: package version")
    if node_id in pass_nodes:
        req(cn.get("state")=="PASS" and cn.get("packaging",{}).get("state")=="PASS",f"{node_id}: canonical PASS")
        req(cn.get("planning",{}).get("readiness")=="retained-pass",f"{node_id}: retained-pass readiness")
        pe=n.get("pass_evidence",{})
        expected_pass={
            "kcrash":{"run":35535289692,"artifact":10613480229,"tests":"4/4 PASS"},
            "knotifications":{"run":35544063879,"artifact":10616445435,"tests":"1/1 PASS"},
            "kstatusnotifieritem":{"run":35544063879,"artifact":10616011544,"tests":"1/1 PASS"},
            "kunitconversion":{"run":35544063879,"artifact":10616255861,"tests":"3/3 PASS"},
            "syndication":{"run":35543268413,"artifact":10615910224,"tests":"4/4 PASS"},
        }[node_id]
        req(pe.get("workflow_run")==expected_pass["run"] and pe.get("artifact_id")==expected_pass["artifact"],f"{node_id}: PASS evidence identity")
        req(pe.get("tests")==expected_pass["tests"] and pe.get("lintian")=="PASS-errors" and pe.get("consumer_smoke")=="PASS" and pe.get("apt_check")=="PASS",f"{node_id}: PASS gates")
        if contract.get("python_module"):
            req(pe.get("python_import")=="PASS",f"{node_id}: Python import gate")
        if n.get("qml_package"):
            req(pe.get("qml_payload_smoke")=="PASS",f"{node_id}: QML payload gate")
        req(n.get("downstream_eligible") is True,f"{node_id}: downstream eligible")
    elif node_id in remat_nodes:
        req(cn.get("state")=="pending",f"{node_id}: remains pending")
        req(cn.get("planning",{}).get("readiness")=="package-contract-ready",f"{node_id}: contract-ready")
        req(cn.get("planning",{}).get("package_contract")=="not-materialized",f"{node_id}: stale materialization invalidated")
        req(n.get("materialization_status")=="superseded-rematerialization-required",f"{node_id}: stale materialization marker")
    else:
        req(cn.get("state")=="pending" and cn.get("planning",{}).get("readiness")=="build-ready",f"{node_id}: runnable build-ready")

req(a.get("schema")==1 and a.get("batch")=="tier2-batch-2","attempt ledger identity")
expected_attempt_counts={"kcrash":3,"knotifications":5,"kstatusnotifieritem":5,"kunitconversion":4,"syndication":4}
for node_id,count in expected_attempt_counts.items():
    req(len(a["real_attempts"][node_id])==count and a["real_attempts"][node_id][-1].get("result")=="PASS",f"{node_id}: final PASS attempt history")
req(any(x.get("result")=="FAIL" and x.get("stage")=="lintian-source-binary" for x in a["real_attempts"]["kstatusnotifieritem"]),"KStatusNotifierItem historical node-owned symbols FAIL retained")
for node_id in expected:
    req(isinstance(a.get("real_attempts",{}).get(node_id),list),f"{node_id}: attempt ledger")
    req(isinstance(a.get("blocked_events",{}).get(node_id),list),f"{node_id}: blocked ledger")

doc=(ROOT/"docs/kde-tier2-package-batch2.md").read_text()
for token in ("shared Resolute rootfs","package_attempted","fail-fast: false","KCrash","Syndication","stable"):
    req(token in doc,f"Batch2 docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 Batch 2 state: PASS")
print(f"retained-pass={sorted(pass_nodes)} rematerialization={sorted(remat_nodes)} runnable={sorted(runnable)}")

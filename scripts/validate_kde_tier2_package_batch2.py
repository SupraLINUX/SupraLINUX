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
req(c.get("lane")=="build-ready-independent","Batch2 lane")
req(c.get("authority")=="kde-upstream" and c.get("provider_platform")=="ubuntu-resolute","authority/provider split")
req(c.get("selected_nodes")==expected,"Batch2 selected nodes")
req(plan.get("build_queue")==expected,"Batch2 must equal generated build queue")
req(c.get("scheduling",{}).get("fail_fast") is False and c["scheduling"].get("independent_nodes") is True,"DAG matrix policy")
req(c.get("scheduling",{}).get("shared_resolute_rootfs") is True,"shared rootfs policy")
req(c.get("semantics",{}).get("package_attempt_begins")=="immediately-before-sbuild","attempt boundary")
req(c.get("semantics",{}).get("pre_sbuild_failure")=="INFRA","pre-sbuild classification")
req(c.get("semantics",{}).get("attempted_build_failure")=="FAIL","attempted failure classification")
req(c.get("semantics",{}).get("stable_promotion_requires_explicit_user_approval") is True,"stable promotion policy")

ecm=dag["nodes"]["extra-cmake-modules"]
ecm_pass=[x for x in ecm.get("evidence",[]) if x.get("result")=="PASS"][-1]
ce=c["shared_predecessors"]["extra_cmake_modules"]
req(ce.get("version")==ecm.get("package_version") and ce.get("workflow_run")==ecm_pass.get("run_id") and ce.get("artifact_id")==ecm_pass.get("artifact_id"),"ECM retained evidence identity")
req(ce.get("debs",{}).get("extra-cmake-modules")==ecm_pass.get("files",{}).get("deb_sha256"),"ECM .deb digest")

t1={n["id"]:n for n in tier1["nodes"]}; t2={n["id"]:n for n in tier2["nodes"]}
for node_id in expected:
    n=c["nodes"][node_id]; canon=t2[node_id]; contract=contracts["nodes"][node_id]
    req(canon.get("state")=="pending","Batch2 nodes must remain pending before real result promotion")
    req(canon.get("planning",{}).get("readiness")=="build-ready",f"{node_id}: build-ready")
    req(canon.get("planning",{}).get("package_contract")=="materialized",f"{node_id}: materialized contract")
    req(n.get("state") in {"prepared-pending-build","remediation-pending-build","PASS","FAIL"},f"{node_id}: campaign state")
    req(n.get("source_sha256")==contract.get("source_sha256"),f"{node_id}: source SHA")
    req(n.get("package_version")==contract.get("package_version_candidate"),f"{node_id}: package version")
    req(sorted(n.get("expected_binary_packages",[]))==sorted(contract.get("compatibility_binary_packages",[])+contract.get("supralinux_additional_binary_packages",[])),f"{node_id}: binary package set")
    me=contracts["materialization"]["evidence"][node_id]; cm=n["materialization"]
    for key in ("artifact_id","artifact_sha256","tree_sha256","debian_tree_sha256","dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
        req(cm.get(key)==me.get(key),f"{node_id}: materialization {key}")
    pred=n["predecessor"]; p=t1[pred["id"]]
    pe=[x for x in p.get("packaging",{}).get("evidence",[]) if x.get("result")=="PASS"][-1]
    req(p.get("state")=="PASS" and p.get("packaging",{}).get("downstream_eligible") is True,f"{node_id}: predecessor PASS")
    req(pred.get("version")==p["packaging"]["package_version"],f"{node_id}: predecessor version")
    req(pred.get("workflow_run")==pe.get("workflow_run") and pred.get("artifact_id")==pe.get("artifact_id"),f"{node_id}: predecessor artifact identity")
    req(pred.get("dev_package") in pred.get("debs",{}),f"{node_id}: predecessor dev package hash")

req(a.get("schema")==1 and a.get("batch")=="tier2-batch-2" and a.get("selected_nodes")==expected,"attempt ledger identity")
for node_id in expected:
    req(isinstance(a.get("real_attempts",{}).get(node_id),list),f"{node_id}: attempt ledger")
    req(isinstance(a.get("blocked_events",{}).get(node_id),list),f"{node_id}: blocked ledger")

for p in (
 "scripts/plan-kde-tier2-package-batch2.py","scripts/kde-tier2-package-batch2-needed.sh",
 "scripts/run-kde-tier2-package-batch2.sh","scripts/test-kde-tier2-package-batch2-scope.sh",
 ".github/workflows/kde-tier2-package-batch2.yml","docs/kde-tier2-package-batch2.md",
):
    req((ROOT/p).exists(),f"missing Batch2 component: {p}")

doc=(ROOT/"docs/kde-tier2-package-batch2.md").read_text()
for token in ("shared Resolute rootfs","package_attempted","fail-fast: false","KCrash","Syndication","stable"):
    req(token in doc,f"Batch2 docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 Batch 2 preparation: PASS")
print("5 build-ready independent nodes; real attempt begins immediately before sbuild")

#!/usr/bin/env python3
from pathlib import Path
import json,sys,re

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier2-package-campaign-batch3.json")
a=load("manifests/kde-tier2-package-batch3-attempts.json")
plan=load("manifests/kde-tier2-campaign-plan.json")
contracts=load("manifests/kde-tier2-package-contracts.json")
tier2=load("manifests/kde-frameworks-tier2.json")
tier1=load("manifests/kde-frameworks-tier1.json")

expected=["kcolorscheme","kcompletion","kcontacts","kpackage","kpty"]
expected_preds={
 "kcolorscheme":["kconfig","kguiaddons","ki18n"],
 "kcompletion":["kcodecs","kconfig","kwidgetsaddons"],
 "kcontacts":["ki18n","kconfig","kcodecs"],
 "kpackage":["karchive","ki18n","kcoreaddons"],
 "kpty":["kcoreaddons","ki18n"],
}
expected_package_closure={
 "kcolorscheme":["kcoreaddons"],
 "kcompletion":[],
 "kcontacts":[],
 "kpackage":[],
 "kpty":[],
}

req(c.get("schema")==1 and c.get("batch")=="tier2-batch-3","Batch3 identity")
req(c.get("selected_nodes")==expected,"Batch3 selected nodes/order")
req(c.get("scheduling",{}).get("fail_fast") is False,"Batch3 fail-fast policy")
req(c.get("semantics",{}).get("fail_requires")=="node-owned-root-cause","FAIL ownership")
req(c.get("semantics",{}).get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")
req("package-level transitive closure" in c.get("semantics",{}).get("package_dependency_closure",""),"package closure semantics")
req(contracts.get("materialization",{}).get("status")=="PASS","selective replacement materialization PASS")
req(contracts.get("materialization",{}).get("targets")==[],"no rematerialization targets remain")

canon={n["id"]:n for n in tier2["nodes"]}
t1={n["id"]:n for n in tier1["nodes"]}
contract_nodes=contracts.get("nodes",{})
mat_evidence=contracts.get("materialization",{}).get("evidence",{})
runnable={n for n in expected if c["nodes"][n].get("state") in {"prepared-pending-build","remediation-pending-build"}}
rematerialization={n for n in expected if c["nodes"][n].get("state")=="rematerialization-pending"}
pass_nodes={n for n in expected if c["nodes"][n].get("state")=="PASS"}
req(runnable=={"kcolorscheme","kcontacts","kpackage"},"Batch3 remediation runnable set")
req(rematerialization==set(),"Batch3 rematerialization queue must be empty")
req(pass_nodes=={"kcompletion","kpty"},"Batch3 retained PASS set")
req(runnable <= set(plan.get("build_queue",[])),"runnable Batch3 nodes are in generated build queue")
req(set(plan.get("build_queue",[])).isdisjoint(pass_nodes),"retained Batch3 PASS nodes absent from build queue")

used=set()
for node_id in expected:
    n=c["nodes"][node_id]; cn=canon[node_id]; pc=contract_nodes[node_id]
    preds=n.get("predecessors",[])
    closure=n.get("package_dependency_closure",[])
    req(preds==expected_preds[node_id],f"{node_id}: predecessor list")
    req(preds==cn.get("depends_on",[])[1:],f"{node_id}: campaign/canonical predecessor drift")
    req(closure==expected_package_closure[node_id],f"{node_id}: package dependency closure")
    req(set(preds).isdisjoint(closure),f"{node_id}: package closure must not duplicate KDE predecessors")
    req(n.get("source_sha256")==pc.get("source_sha256"),f"{node_id}: source SHA")
    req(n.get("package_version")==pc.get("package_version_candidate"),f"{node_id}: package version")
    req(n.get("expected_binary_packages")==pc.get("compatibility_binary_packages"),f"{node_id}: binary set")
    used.update(preds); used.update(closure)

    if node_id in pass_nodes:
        req(cn.get("state")=="PASS" and cn.get("planning",{}).get("readiness")=="retained-pass",f"{node_id}: canonical retained PASS")
        pe=n.get("pass_evidence",{})
        req(pe.get("workflow_run")==35620923130 and pe.get("run_attempt")==2,f"{node_id}: PASS run identity")
        req(pe.get("lintian")=="PASS-errors" and pe.get("consumer_smoke")=="PASS" and pe.get("apt_check")=="PASS",f"{node_id}: PASS gates")
        req(pe.get("predecessor_buildinfo_proof")=="PASS",f"{node_id}: predecessor buildinfo proof")
        req(n.get("downstream_eligible") is True,f"{node_id}: downstream eligible")
    else:
        req(cn.get("state")=="pending" and cn.get("planning",{}).get("readiness")=="build-ready",f"{node_id}: build-ready pending")
        req(cn.get("planning",{}).get("package_contract")=="materialized",f"{node_id}: materialized package contract")
        req(n.get("materialization_status") in {"retained-pass-corrected-evidence","replacement-pass"},f"{node_id}: runnable materialization status")

    m=n.get("materialization",{}); me=mat_evidence.get(node_id,{})
    req(m.get("artifact_id")==me.get("artifact_id"),f"{node_id}: materialization artifact identity")
    for key in ("artifact_sha256","tree_sha256","debian_tree_sha256","dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
        req(m.get(key)==me.get(key),f"{node_id}: materialization {key}")

req(c["nodes"]["kcolorscheme"]["package_dependency_closure"]==["kcoreaddons"],"KColorScheme package closure must include KCoreAddons")
req("kcoreaddons" not in c["nodes"]["kcolorscheme"]["predecessors"],"KCoreAddons must not become a KDE KColorScheme DAG edge")

pool=c.get("retained_predecessors",{})
req(set(pool)==used,"retained predecessor pool exactly covers Batch3 KDE plus package closure inputs")
for pred_id,cfg in pool.items():
    tn=t1.get(pred_id,{})
    req(tn.get("state")=="PASS",f"{pred_id}: Tier1 retained PASS")
    req(tn.get("packaging",{}).get("package_version")==cfg.get("version"),f"{pred_id}: retained version")
    req(cfg.get("dev_package") in cfg.get("debs",{}),f"{pred_id}: dev package in .deb contract")
    for pkg,digest in cfg.get("debs",{}).items():
        req(bool(pkg) and re.fullmatch(r"[0-9a-f]{64}",digest or ""),f"{pred_id}: {pkg} digest")

req(a.get("schema")==1 and a.get("batch")=="tier2-batch-3","attempt ledger identity")
req(len(a["real_attempts"]["kcompletion"])==1 and a["real_attempts"]["kcompletion"][-1].get("result")=="PASS","KCompletion PASS attempt")
req(len(a["real_attempts"]["kpty"])==1 and a["real_attempts"]["kpty"][-1].get("result")=="PASS","KPty PASS attempt")
req(len(a["real_attempts"]["kcontacts"])==1 and a["real_attempts"]["kcontacts"][-1].get("result")=="INFRA","KContacts integration attempt retained")
req(len(a["real_attempts"]["kpackage"])==1 and a["real_attempts"]["kpackage"][-1].get("result")=="INFRA","KPackage integration attempt retained")
req(len(a["real_attempts"]["kcolorscheme"])==1 and a["real_attempts"]["kcolorscheme"][-1].get("result")=="INFRA","KColorScheme package-closure incident retained")
req(a["real_attempts"]["kcolorscheme"][-1].get("stage")=="sbuild-install-deps","KColorScheme closure incident stage")
req(any(x.get("node")=="kcolorscheme" and x.get("package_attempted") is False for x in a.get("infrastructure_incidents",[])),"KColorScheme pre-sbuild hash incident retained")
for node_id in expected:
    req(isinstance(a.get("blocked_events",{}).get(node_id),list),f"{node_id}: blocked ledger")

doc=(ROOT/"docs/kde-tier2-package-batch3.md").read_text()
for token in ("multi-predecessor","shared retained input","package_attempted","package_dependency_closure","35623204812","stable"):
    req(token.casefold() in doc.casefold(),f"Batch3 docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 Batch 3 remediation preparation: PASS")
print("retained-pass=['kcompletion','kpty'] runnable=['kcolorscheme','kcontacts','kpackage'] package-closure={'kcolorscheme':['kcoreaddons']}")

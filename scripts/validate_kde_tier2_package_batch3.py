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
expected_pass_run={
 "kcolorscheme":35627389046,
 "kcompletion":35620923130,
 "kcontacts":35627389046,
 "kpackage":35631458583,
 "kpty":35620923130,
}

req(c.get("schema")==1 and c.get("batch")=="tier2-batch-3","Batch3 identity")
req(c.get("state")=="PASS","Batch3 final state")
req(c.get("canonical_snapshot")=="11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED","Batch3 canonical snapshot")
req(c.get("selected_nodes")==expected,"Batch3 selected nodes/order")
req(c.get("scheduling",{}).get("fail_fast") is False,"Batch3 fail-fast policy")
req(c.get("semantics",{}).get("fail_requires")=="node-owned-root-cause","FAIL ownership")
req(c.get("semantics",{}).get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")
req("package-level transitive closure" in c.get("semantics",{}).get("package_dependency_closure",""),"package closure semantics")

mat=contracts.get("materialization",{})
req(mat.get("status")=="PASS" and mat.get("result")=="PASS","materialization PASS")
req(mat.get("targets")==[],"materialization queue empty")
req(mat.get("workflow_run")==35629129797 and mat.get("commit")=="5fa15910b91e5693395d04ef7555af94dfa7fe13","KPackage rematerialization identity")

canon={n["id"]:n for n in tier2["nodes"]}
t1={n["id"]:n for n in tier1["nodes"]}
contract_nodes=contracts.get("nodes",{})
mat_evidence=mat.get("evidence",{})
runnable={n for n in expected if c["nodes"][n].get("state") in {"prepared-pending-build","remediation-pending-build"}}
rematerialization={n for n in expected if c["nodes"][n].get("state")=="rematerialization-pending"}
pass_nodes={n for n in expected if c["nodes"][n].get("state")=="PASS"}
req(runnable==set(),"Batch3 runnable queue empty")
req(rematerialization==set(),"Batch3 rematerialization queue empty")
req(pass_nodes==set(expected),"Batch3 five-node PASS closure")
req(plan.get("build_queue")==[],"generated build queue empty after Batch3 closure")
req(set(plan.get("package_contract_ready",[]))=={"kdeclarative","kfilemetadata","kservice"},"next package-contract-ready set")
req(set(expected) <= set(plan.get("retained_pass",[])),"all Batch3 nodes retained globally")

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

    req(cn.get("state")=="PASS" and cn.get("planning",{}).get("readiness")=="retained-pass",f"{node_id}: canonical retained PASS")
    pe=n.get("pass_evidence",{})
    req(pe.get("workflow_run")==expected_pass_run[node_id],f"{node_id}: PASS run identity")
    req(pe.get("lintian")=="PASS-errors" and pe.get("consumer_smoke")=="PASS" and pe.get("apt_check")=="PASS",f"{node_id}: PASS gates")
    req(pe.get("predecessor_buildinfo_proof")=="PASS",f"{node_id}: predecessor buildinfo proof")
    req(n.get("downstream_eligible") is True,f"{node_id}: downstream eligible")
    if node_id=="kcolorscheme":
        req(pe.get("package_dependency_closure_buildinfo_proof")=="PASS","KColorScheme closure buildinfo proof")
        req(pe.get("package_dependency_closure",{}).get("kcoreaddons")=="6.30.0-0supralinux4","KColorScheme KCoreAddons package closure")
    if node_id=="kcontacts":
        req(pe.get("qml_payload_smoke")=="PASS","KContacts QML payload smoke")
    if node_id=="kpackage":
        req(pe.get("tests")=="10/10 PASS","KPackage full upstream tests")
        req(pe.get("abi_soname")=="libKF6Package.so.6" and pe.get("abi_export_count")==86,"KPackage ABI evidence")
        req(pe.get("workflow_run")==35631458583 and pe.get("job_id")==106439193430,"KPackage final run/job")
        req(pe.get("artifact_id")==10653599787 and pe.get("artifact_sha256")=="8b55260a3b9f4653c3e5c6589034c1fa96daa5ca000e8669c2a39f8c64288faf","KPackage final artifact")
        req(pe.get("rootfs_sha256")=="af1bbbf06929caef42b87b39b26c2b12b7ffdc5c058e747a6fa8eb64be63b2a8","KPackage rootfs content digest")

    m=n.get("materialization",{}); me=mat_evidence.get(node_id,{})
    req(m.get("artifact_id")==me.get("artifact_id"),f"{node_id}: materialization artifact identity")
    for key in ("artifact_sha256","tree_sha256","debian_tree_sha256","dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
        req(m.get(key)==me.get(key),f"{node_id}: materialization {key}")

kp=contracts["nodes"]["kpackage"]
req(kp.get("rules_auto_test_command","").startswith("AS_VALIDATE_NONET=1 xvfb-run "),"KPackage offline AppStream test command")
tea=kp.get("test_environment_adaptation",{})
req(tea.get("observed_provider_version")=="1.1.2-1" and tea.get("setting")=="AS_VALIDATE_NONET=1","KPackage AppStream 1.1.2 offline contract")
req(tea.get("scope")=="dh_auto_test-only" and tea.get("kde_feature_effect")=="none","KPackage AppStream contract scope/neutrality")

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
req(len(a["real_attempts"]["kcolorscheme"])==2 and a["real_attempts"]["kcolorscheme"][-1].get("result")=="PASS","KColorScheme final PASS")
req(len(a["real_attempts"]["kcontacts"])==2 and a["real_attempts"]["kcontacts"][-1].get("result")=="PASS","KContacts final PASS")
req(len(a["real_attempts"]["kpackage"])==3 and a["real_attempts"]["kpackage"][-1].get("result")=="PASS","KPackage third-attempt PASS")
req(a["real_attempts"]["kpackage"][-1].get("tests")=="10/10 PASS","KPackage final upstream tests")
req(any(x.get("node")=="kcolorscheme" and x.get("package_attempted") is False for x in a.get("infrastructure_incidents",[])),"KColorScheme pre-sbuild hash incident retained")
for node_id in expected:
    req(isinstance(a.get("blocked_events",{}).get(node_id),list),f"{node_id}: blocked ledger")

closure=c.get("closure",{})
req(closure.get("result")=="PASS" and closure.get("workflow_run")==35631458583,"Batch3 closure evidence")
req(closure.get("canonical_snapshot")=="11 PASS / 4 pending / 0 current FAIL / 0 BLOCKED","Batch3 closure snapshot")

doc=(ROOT/"docs/kde-tier2-package-batch3.md").read_text()
for token in ("5/5 PASS","35631458583","10/10 tests","11 PASS / 4 pending","AS_VALIDATE_NONET","stable"):
    req(token.casefold() in doc.casefold(),f"Batch3 docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 Batch 3 closure: PASS")
print("retained-pass=['kcolorscheme','kcompletion','kcontacts','kpackage','kpty'] runnable=[]")

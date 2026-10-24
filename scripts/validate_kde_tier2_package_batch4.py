#!/usr/bin/env python3
from pathlib import Path
import json,re,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier2-package-campaign-batch4.json")
a=load("manifests/kde-tier2-package-batch4-attempts.json")
plan=load("manifests/kde-tier2-campaign-plan.json")
tier2=load("manifests/kde-frameworks-tier2.json")
contracts=load("manifests/kde-tier2-package-contracts.json")
tier1=load("manifests/kde-frameworks-tier1.json")

expected=["kdeclarative","kfilemetadata","kservice"]
expected_preds={
 "kdeclarative":["ki18n","kconfig","kguiaddons","kglobalaccel","kwidgetsaddons"],
 "kfilemetadata":["ki18n","kcoreaddons","kcodecs","karchive","kconfig"],
 "kservice":["kconfig","kcoreaddons","ki18n"],
}
expected_closure={"kdeclarative":["kcoreaddons"],"kfilemetadata":[],"kservice":[]}
RUNNABLE={"prepared-pending-build","remediation-pending-build"}

req(c.get("schema")==1 and c.get("batch")=="tier2-batch-4","Batch4 identity")
req(c.get("selected_nodes")==expected,"Batch4 selected nodes/order")
req(c.get("frameworks_series")=="6.30.0","Batch4 Frameworks series")
req(c.get("scheduling",{}).get("fail_fast") is False,"Batch4 fail-fast policy")
req(c.get("scheduling",{}).get("shared_resolute_rootfs") is True,"Batch4 shared rootfs")
req(c.get("scheduling",{}).get("shared_retained_input_bundle") is True,"Batch4 shared predecessor bundle")
req(c.get("semantics",{}).get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")
req(c.get("semantics",{}).get("fail_requires")=="node-owned-root-cause","FAIL ownership")
req(c.get("semantics",{}).get("package_attempt_begins")=="immediately-before-sbuild","attempt boundary")

canon={n["id"]:n for n in tier2["nodes"]}
t1={n["id"]:n for n in tier1["nodes"]}
runnable={n for n in expected if c["nodes"][n].get("state") in RUNNABLE}
pass_nodes={n for n in expected if c["nodes"][n].get("state")=="PASS"}
rematerialization={n for n in expected if c["nodes"][n].get("state")=="rematerialization-pending"}
req(runnable | pass_nodes | rematerialization == set(expected),"Batch4 node states cover selected set")
req(runnable.isdisjoint(pass_nodes) and runnable.isdisjoint(rematerialization) and pass_nodes.isdisjoint(rematerialization),"Batch4 state sets disjoint")
req(set(plan.get("build_queue",[])).intersection(expected)==runnable,"Batch4 scoped global build queue")
req(set(plan.get("package_contract_ready",[])).intersection(expected)==rematerialization,"Batch4 scoped package-contract/rematerialization queue")

used=set()
for node_id in expected:
    n=c["nodes"][node_id]; cn=canon[node_id]; pc=contracts["nodes"][node_id]
    req(n.get("predecessors")==expected_preds[node_id],f"{node_id}: predecessor list")
    req(n.get("package_dependency_closure",[])==expected_closure[node_id],f"{node_id}: package closure")
    req(set(n.get("predecessors",[])).isdisjoint(n.get("package_dependency_closure",[])),f"{node_id}: direct/closure overlap")
    req(n.get("source_sha256")==cn.get("source_sha256")==pc.get("source_sha256"),f"{node_id}: source SHA")
    req(n.get("package_version")==cn.get("package_identity",{}).get("package_version_candidate")==pc.get("package_version_candidate"),f"{node_id}: package version")
    req(n.get("expected_binary_packages")==pc.get("compatibility_binary_packages"),f"{node_id}: binary package contract")
    m=n.get("materialization",{})
    if n.get("state") in RUNNABLE or n.get("state")=="PASS":
        cm=cn.get("planning",{}).get("materialization_evidence",{})
        for key in ("workflow_run","artifact_id","artifact_sha256","tree_sha256","debian_tree_sha256","dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
            req(m.get(key)==cm.get(key),f"{node_id}: materialization {key}")
    if n.get("state") in RUNNABLE:
        req(cn.get("planning",{}).get("package_contract")=="materialized",f"{node_id}: runnable canonical materialized")
        req(cn.get("state")=="pending" and cn.get("planning",{}).get("readiness")=="build-ready",f"{node_id}: runnable canonical state")
        req(n.get("downstream_eligible") is False,f"{node_id}: runnable not downstream eligible")
    elif n.get("state")=="PASS":
        req(cn.get("planning",{}).get("package_contract")=="retained-pass",f"{node_id}: PASS canonical retained contract")
        req(cn.get("state")=="PASS" and cn.get("planning",{}).get("readiness")=="retained-pass",f"{node_id}: retained PASS canonical state")
        req(n.get("downstream_eligible") is True,f"{node_id}: PASS downstream eligible")
    else:
        req(cn.get("state")=="pending" and cn.get("planning",{}).get("readiness")=="package-contract-ready",f"{node_id}: rematerialization canonical readiness")
        req(cn.get("planning",{}).get("package_contract")=="not-materialized",f"{node_id}: rematerialization canonical contract state")
        history=cn.get("planning",{}).get("materialization_history",[])
        req(any(x and x.get("artifact_id")==m.get("artifact_id") for x in history),f"{node_id}: previous materialization retained historically")
        req(n.get("downstream_eligible") is False,f"{node_id}: rematerialization not downstream eligible")
    used.update(n.get("predecessors",[])); used.update(n.get("package_dependency_closure",[]))

kd=c["nodes"]["kdeclarative"]
req(kd.get("qml_packages")==[
 "qml6-module-org-kde-draganddrop",
 "qml6-module-org-kde-graphicaleffects",
 "qml6-module-org-kde-kquickcontrols",
 "qml6-module-org-kde-kquickcontrolsaddons",
],"KDeclarative four-QML payload contract")
req(kd.get("extra_abi_contracts")==[{"package":"libkquickcontrolsprivate0","soname":"libkquickcontrolsprivate.so.0"}],"KDeclarative private ABI contract")
req(kd.get("package_dependency_closure")==["kcoreaddons"],"KDeclarative KCoreAddons package closure")
req("libkquickcontrolsprivate0" in kd.get("expected_binary_packages",[]),"KDeclarative Ubuntu binary compatibility package")

ks=contracts["nodes"]["kservice"]
req(ks.get("build_depends_remove")==["libkf6doctools-dev"],"KService optional KDocTools Build-Depends removal")
req(ks.get("binary_depends_remove",{}).get("libkf6service-dev")==["libkf6doctools-dev"],"KService optional KDocTools dev Depends removal")
req(ks.get("symbols_adjustments")==[{"file":"libkf6service6.symbols","symbol":"_ZSt19piecewise_construct@Base","version":"6.30.0","tag":"optional=toolchain"}],"KService toolchain symbol remediation")

pool=c.get("retained_predecessors",{})
req(set(pool)==used,"retained predecessor pool exactly covers Batch4 direct plus package closure inputs")
for pred_id,cfg in pool.items():
    tn=t1.get(pred_id,{})
    req(tn.get("state")=="PASS",f"{pred_id}: Tier1 PASS")
    req(tn.get("packaging",{}).get("package_version")==cfg.get("version"),f"{pred_id}: retained version")
    req(cfg.get("dev_package") in cfg.get("debs",{}),f"{pred_id}: dev package retained")
    for pkg,digest in cfg.get("debs",{}).items():
        req(bool(pkg) and re.fullmatch(r"[0-9a-f]{64}",digest or ""),f"{pred_id}: {pkg} digest")

ecm=c.get("shared_predecessors",{}).get("extra_cmake_modules",{})
req(ecm.get("version")=="6.30.0-0supralinux3","ECM version")
req(ecm.get("debs",{}).get("extra-cmake-modules")=="ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f","ECM binary digest")

req(a.get("schema")==1 and a.get("batch")=="tier2-batch-4","attempt ledger identity")
for node_id in expected:
    req(isinstance(a.get("real_attempts",{}).get(node_id),list),f"{node_id}: real-attempt ledger")
    req(isinstance(a.get("blocked_events",{}).get(node_id),list),f"{node_id}: blocked ledger")
req(isinstance(a.get("infrastructure_incidents"),list),"Batch4 infrastructure ledger")

for path in (
 "scripts/plan-kde-tier2-package-batch4.py",
 "scripts/kde-tier2-package-batch4-needed.sh",
 "scripts/validate-kde-tier2-batch4-retained-inputs.py",
 "scripts/run-kde-tier2-package-batch4.sh",
 "scripts/test-kde-tier2-package-batch4-scope.sh",
 ".github/workflows/kde-tier2-package-batch4.yml",
):
    req((ROOT/path).exists(),f"missing Batch4 component: {path}")

doc=(ROOT/"docs/kde-tier2-package-batch4.md").read_text()
for token in ("KDeclarative","KFileMetaData","KService","KCoreAddons","libkquickcontrolsprivate0","stable"):
    req(token.casefold() in doc.casefold(),f"Batch4 docs missing {token}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 Batch 4 preparation: PASS")
print(f"runnable={sorted(runnable)} rematerialization={sorted(rematerialization)} retained-pass={sorted(pass_nodes)}")

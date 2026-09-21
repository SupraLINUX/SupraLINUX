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
req(c.get("schema")==1 and c.get("batch")=="tier2-batch-3","Batch3 identity")
req(c.get("selected_nodes")==expected,"Batch3 selected nodes/order")
req(c.get("scheduling",{}).get("fail_fast") is False,"Batch3 fail-fast policy")
req(c.get("scheduling",{}).get("shared_retained_input_bundle") is True,"shared retained input bundle")
req(c.get("semantics",{}).get("fail_requires")=="node-owned-root-cause","FAIL ownership")
req(c.get("semantics",{}).get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")
req(c.get("materialization_source",{}).get("workflow_run")==35608790364 and c.get("materialization_source",{}).get("status")=="PASS","materialization source")

canon={n["id"]:n for n in tier2["nodes"]}
t1={n["id"]:n for n in tier1["nodes"]}
contract_nodes=contracts.get("nodes",{})
mat_evidence=contracts.get("materialization",{}).get("evidence",{})
runnable={n for n in expected if c["nodes"][n].get("state") in {"prepared-pending-build","remediation-pending-build"}}
pass_nodes={n for n in expected if c["nodes"][n].get("state")=="PASS"}
req(runnable <= set(plan.get("build_queue",[])),"runnable Batch3 nodes are in generated build queue")
req(set(plan.get("build_queue",[])).isdisjoint(pass_nodes),"retained Batch3 PASS nodes absent from build queue")

used=set()
for node_id in expected:
    n=c["nodes"][node_id]; cn=canon[node_id]; pc=contract_nodes[node_id]
    req(cn.get("state") in {"pending","PASS"},f"{node_id}: canonical state vocabulary")
    if n.get("state")!="PASS":
        req(cn.get("state")=="pending",f"{node_id}: pre-PASS canonical state")
        req(cn.get("planning",{}).get("readiness")=="build-ready",f"{node_id}: build-ready")
        req(cn.get("planning",{}).get("package_contract")=="materialized",f"{node_id}: materialized package contract")
    req(n.get("source_sha256")==pc.get("source_sha256"),f"{node_id}: source SHA")
    req(n.get("package_version")==pc.get("package_version_candidate"),f"{node_id}: package version")
    req(n.get("expected_binary_packages")==pc.get("compatibility_binary_packages"),f"{node_id}: binary set")
    req(n.get("predecessors")==expected_preds[node_id],f"{node_id}: predecessor list")
    expected_from_canon=cn.get("depends_on",[])[1:]
    req(n.get("predecessors")==expected_from_canon,f"{node_id}: campaign/canonical predecessor drift")
    used.update(n.get("predecessors",[]))
    m=n.get("materialization",{}); me=mat_evidence.get(node_id,{})
    req(m.get("workflow_run")==35608790364 and m.get("artifact_id")==me.get("artifact_id"),f"{node_id}: materialization identity")
    for key in ("artifact_sha256","tree_sha256","debian_tree_sha256","dsc_sha256","debian_tar_sha256","orig_tar_sha256"):
        req(m.get(key)==me.get(key),f"{node_id}: materialization {key}")

pool=c.get("retained_predecessors",{})
req(set(pool)==used,"retained predecessor pool exactly covers Batch3")
for pred_id,cfg in pool.items():
    tn=t1.get(pred_id,{})
    req(tn.get("state")=="PASS",f"{pred_id}: Tier1 retained PASS")
    req(tn.get("packaging",{}).get("package_version")==cfg.get("version"),f"{pred_id}: retained version")
    pev=[x for x in tn.get("packaging",{}).get("evidence",[]) if x.get("result")=="PASS"]
    req(bool(pev),f"{pred_id}: retained PASS evidence")
    if pev:
        ev=pev[-1]
        req(ev.get("workflow_run")==cfg.get("workflow_run"),f"{pred_id}: workflow run")
        req(ev.get("artifact_id")==cfg.get("artifact_id"),f"{pred_id}: artifact id")
        req(ev.get("artifact_sha256")==cfg.get("artifact_sha256"),f"{pred_id}: artifact digest")
    req(cfg.get("dev_package") in cfg.get("debs",{}),f"{pred_id}: dev package in .deb contract")
    for pkg,digest in cfg.get("debs",{}).items():
        req(bool(pkg) and re.fullmatch(r"[0-9a-f]{64}",digest or ""),f"{pred_id}: {pkg} digest")

ecm=c.get("shared_predecessors",{}).get("extra_cmake_modules",{})
req(ecm.get("version")=="6.30.0-0supralinux3" and ecm.get("artifact_id")==10298635300,"ECM retained identity")
req(ecm.get("debs",{}).get("extra-cmake-modules")=="ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f","ECM retained .deb digest")

req(a.get("schema")==1 and a.get("batch")=="tier2-batch-3","attempt ledger identity")
for node_id in expected:
    req(isinstance(a.get("real_attempts",{}).get(node_id),list),f"{node_id}: attempt ledger")
    req(isinstance(a.get("blocked_events",{}).get(node_id),list),f"{node_id}: blocked ledger")
req(isinstance(a.get("infrastructure_incidents"),list),"infrastructure incident ledger")

for path in (
 "scripts/plan-kde-tier2-package-batch3.py",
 "scripts/kde-tier2-package-batch3-needed.sh",
 "scripts/validate-kde-tier2-batch3-retained-inputs.py",
 "scripts/run-kde-tier2-package-batch3.sh",
 "scripts/test-kde-tier2-package-batch3-scope.sh",
 ".github/workflows/kde-tier2-package-batch3.yml",
 "docs/kde-tier2-package-batch3.md",
):
    req((ROOT/path).exists(),f"missing Batch3 component: {path}")

doc=(ROOT/"docs/kde-tier2-package-batch3.md").read_text()
for token in ("multi-predecessor","shared retained input","package_attempted","fail-fast: false","35608790364","stable"):
    req(token in doc,f"Batch3 docs missing {token}")

policy=(ROOT/".github/workflows/repository-policy.yml").read_text()
req("scripts/test-kde-tier2-package-batch3-scope.sh" in policy,"Repository Policy Batch3 scope gate")
req("python3 scripts/validate_kde_tier2_package_batch3.py" in policy,"Repository Policy Batch3 validator")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 2 Batch 3 preparation: PASS")
print(f"runnable={sorted(runnable)} pass={sorted(pass_nodes)} predecessors={sorted(used)}")

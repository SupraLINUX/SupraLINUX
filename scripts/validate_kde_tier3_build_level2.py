#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
m=load("manifests/kde-tier3-build-level2.json"); a=load("manifests/kde-tier3-build-level2-attempts.json"); c=load("manifests/kde-tier3-build-campaign.json"); d=load("manifests/kde-dag.json"); l0=load("manifests/kde-tier3-build-level0.json"); l1=load("manifests/kde-tier3-build-level1.json"); mat=load("manifests/kde-tier3-materialization.json"); contracts=load("manifests/kde-tier3-package-contracts.json"); t=load("manifests/kde-frameworks-tier3.json")
T=["baloo","kcmutils","knotifyconfig","kparts"]
D={"baloo":["kio","kcoreaddons","kconfig","kdbusaddons","ki18n","kidletime","solid","kfilemetadata","kcrash"],"kcmutils":["kio","kconfigwidgets","kxmlgui","kitemviews","kcoreaddons","kguiaddons","ki18n","kwidgetsaddons","kirigami"],"knotifyconfig":["kio","kconfigwidgets","kxmlgui","kcompletion","kconfig","ki18n","knotifications","kwidgetsaddons"],"kparts":["kio","kjobwidgets","kxmlgui","kconfig","kcoreaddons","ki18n","kservice","kwidgetsaddons"]}
P={"baloo":{"BUILD_TESTING":"ON"},"kcmutils":{"BUILD_TESTING":"ON"},"knotifyconfig":{"BUILD_TESTING":"ON"},"kparts":{"BUILD_TESTING":"ON","KDE_INSTALL_APP_TEMPLATES":"ON"}}
req(m.get("schema")==1 and m.get("authority")=="kde-upstream" and m.get("provider_platform")=="ubuntu-resolute","Level2 schema/authority/provider")
req(m.get("role")=="tier3-binary-build-level2" and m.get("frameworks_series")=="6.30.0","Level2 role/series")
req(m.get("selected_nodes")==T and m.get("canonical_snapshot")=="13 PASS / 7 pending / 0 current FAIL / 0 BLOCKED","Level2 node set/snapshot")
if m.get("state")=="planned-pending-activation":
    req(m.get("execution_authorized") is False and m.get("next_gate")=="tier3-build-level2-planning-validation","planned Level2 authorization/gate")
else: req(m.get("state") in {"active-pending-ci","PASS","PARTIAL"},"Level2 lifecycle")
pre=m.get("planning_precondition",{}); req(pre.get("level1_attempt")==10 and pre.get("level1_workflow_run")==36425867815 and pre.get("level1_closure_commit")=="0e5e2602cba730612bcb9301a59f5b51c3fdd574" and pre.get("repository_policy_workflow_run")==36430910043 and pre.get("result")=="PASS","Level2 precondition")
req(l1.get("state")=="PASS" and l1.get("execution_authorized") is False and l1.get("current_attempt")==10,"Level1 closed precondition")
req(t.get("discovery_policy",{}).get("phase")=="build-level2-planning","canonical live phase")
tn={x["id"]:x for x in t.get("nodes",[])}; ks=tn["knewstuff"]; req(ks.get("state")=="pending" and ks.get("packaging",{}).get("state")=="runtime-validation-required","KNewStuff runtime pending")
h=m["deferred_runtime_validation_handoff"]["knewstuff"]; req(h.get("requires_level2_pass")==["kcmutils"] and h.get("effect")=="runtime-validation-gate-only-no-auto-PASS","KNewStuff handoff")
dn=d.get("nodes",{}); ret=m.get("retained_predecessors",{})
def rec(roots):
    seen=set()
    def visit(x):
        req(x in dn,x+": missing canonical DAG predecessor")
        if x not in dn: return
        for dep in dn[x].get("depends_on",[]):
            if dep!="extra-cmake-modules" and dep not in seen: seen.add(dep); visit(dep)
    for x in roots: visit(x)
    return seen
for x,cfg in ret.items():
    prov=cfg.get("provenance")
    if prov=="tier3-level1-pass":
        can=dn.get(x,{}); req(can.get("state")=="PASS" and can.get("downstream_eligible") is True,x+": Level1 PASS"); req(cfg.get("version")==can.get("package_version") and cfg.get("artifact_id")==can.get("artifact_id") and cfg.get("artifact_sha256")==can.get("artifact_sha256"),x+": Level1 pin")
    elif prov in {"canonical-dag-pass","canonical-dag-provider-closure"}:
        can=dn.get(x,{}); cp=c.get("retained_pass_artifacts",{}).get(x,{}); req(can.get("state")=="PASS" and can.get("downstream_eligible") is True,x+": DAG PASS"); req(cfg.get("version")==cp.get("version") and cfg.get("artifact_id")==cp.get("artifact_id") and cfg.get("artifact_sha256")==cp.get("artifact_sha256"),x+": retained pin")
    elif prov=="tier3-level0-pass":
        n=l0.get("nodes",{}).get(x,{}); ev=n.get("pass_evidence",{}); req(n.get("state")=="PASS" and ev.get("result")=="PASS" and ev.get("downstream_eligible") is True,x+": Level0 PASS"); req(cfg.get("version")==n.get("package_version") and cfg.get("artifact_id")==ev.get("artifact_id") and cfg.get("artifact_sha256")==ev.get("artifact_sha256"),x+": Level0 pin")
    else: req(False,x+": unknown predecessor provenance "+str(prov))
    req(cfg.get("dev_package") in cfg.get("expected_binary_packages",[]),x+": dev package identity")
for x in T:
    n=m["nodes"][x]; cp=c["nodes"][x]; mm=mat["nodes"][x]; cc=contracts["nodes"][x]
    req(cp.get("level")==2 and cp.get("state")=="planned",x+": campaign Level2")
    req(n.get("state") in {"prepared-pending-build","remediation-pending-build","PASS","FAIL"},x+": node state")
    req(n.get("source_package")==cp.get("source_package") and n.get("package_version")==cp.get("package_version") and n.get("expected_binary_packages")==cp.get("expected_binary_packages"),x+": package identity")
    req(n.get("materialization")==cp.get("materialization"),x+": materialization pin")
    req(mm.get("state")=="materialized" and mm.get("evidence",{}).get("result")=="PASS" and mm.get("evidence",{}).get("package_attempted") is False,x+": materialization PASS")
    req(cc.get("contract_state")=="contract-ready" and cc.get("selected_profile",{}).get("BUILD_TESTING") is True,x+": contract")
    req(n.get("direct_build_predecessors")==D[x],x+": direct Build-Depends")
    provider=sorted(rec(D[x])-set(D[x])); req(n.get("provider_closure_input_ids")==provider,x+": provider closure"); req(set(n.get("retained_input_ids",[]))==set(D[x])|set(provider),x+": retained closure")
    req(all(y in ret for y in n.get("retained_input_ids",[])),x+": retained pins")
    req(n.get("buildinfo_proof_packages")==[ret[y]["dev_package"] for y in D[x]],x+": buildinfo proof")
    req(not ({ret[y]["dev_package"] for y in provider}&set(n.get("buildinfo_proof_packages",[]))),x+": closure invented buildinfo edge")
    req(n.get("profile_assertions")==P[x],x+": profile"); req(n.get("qml_packages")==[y for y in cp.get("expected_binary_packages",[]) if y.startswith("qml6-module-")],x+": QML contract")
    req(n.get("python_module") is None and n.get("runtime_validation_input_ids")==[] and n.get("sbuild_enable_network") is False,x+": undeclared runtime/network")
    req(n.get("success_transition")=="PASS" and n.get("downstream_eligible_on_build_success") is True,x+": success transition")
req(a.get("schema")==1 and a.get("batch")=="tier3-build-level2" and a.get("selected_nodes")==T and set(a.get("nodes",{}))==set(T),"Level2 ledger")
if m.get("state")=="planned-pending-activation": req(a.get("campaign_history")==[] and all(a["nodes"][x]==[] for x in T),"planned ledger must be empty")
for p in ("scripts/plan-kde-tier3-build-level2.py","scripts/test-kde-tier3-build-level2-planner.py","scripts/run-kde-tier3-build-level2.sh",".github/workflows/kde-tier3-build-level2.yml","docs/kde-tier3-build-level2.md"): req((ROOT/p).exists(),"missing Level2 component: "+p)
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 build Level 2 definition: PASS"); print("state="+m["state"]); print("execution_authorized="+str(m["execution_authorized"]).lower())

#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

m=load("manifests/kde-tier3-build-level3.json")
a=load("manifests/kde-tier3-build-level3-attempts.json")
c=load("manifests/kde-tier3-build-campaign.json")
d=load("manifests/kde-dag.json")
l2=load("manifests/kde-tier3-build-level2.json")
mat=load("manifests/kde-tier3-materialization.json")
contracts=load("manifests/kde-tier3-package-contracts.json")
t=load("manifests/kde-frameworks-tier3.json")

T=["ktexteditor","purpose"]
D={
  "ktexteditor":["kio","kparts","karchive","kconfig","kguiaddons","ki18n","sonnet","syntax-highlighting","kcolorscheme","kauth"],
  "purpose":["kio","kcmutils","kcoreaddons","ki18n","kconfig","kirigami","knotifications","kservice","prison","kitemmodels"],
}
P={"ktexteditor":{"BUILD_TESTING":"ON"},"purpose":{"BUILD_TESTING":"ON"}}
SNAP="18 PASS / 2 pending / 0 current FAIL / 0 BLOCKED"

req(m.get("schema")==1 and m.get("authority")=="kde-upstream" and m.get("provider_platform")=="ubuntu-resolute","Level3 schema/authority/provider")
req(m.get("role")=="tier3-binary-build-level3" and m.get("frameworks_series")=="6.30.0","Level3 role/series")
req(m.get("selected_nodes")==T and m.get("canonical_snapshot")==SNAP,"Level3 node set/snapshot")
PV={"repository_policy_workflow_run":36606233220,"repository_policy_job_id":109535845900,"router_plan_job_id":109535845121,"commit":"87099ae7fa83a41edde584c60cea0d2880e22d4c"}
state=m.get("state")
if state=="planned-pending-activation":
    req(m.get("execution_authorized") is False and m.get("next_gate")=="tier3-build-level3-planning-validation","planned Level3 authorization/gate")
elif state=="active-pending-ci":
    req(m.get("execution_authorized") is True and m.get("current_attempt")==1 and m.get("next_attempt") is None and m.get("next_gate")=="tier3-build-level3-attempt1","active Level3 authorization/gate")
    pv=m.get("planning_validation",{})
    req(all(pv.get(k)==v for k,v in PV.items()) and pv.get("planner_runner_scope")=="PASS" and pv.get("level3_definition")=="PASS" and pv.get("historical_boundary")=="PASS" and pv.get("result")=="PASS","Level3 Attempt1 planning validation evidence")
    act=m.get("activation",{})
    req(act.get("status")=="ACTIVE" and act.get("attempt")==1 and act.get("planning_policy_workflow_run")==PV["repository_policy_workflow_run"] and act.get("planning_commit")==PV["commit"],"Level3 Attempt1 activation evidence")
else:
    req(state in {"PASS","PARTIAL"},"Level3 lifecycle")

pre=m.get("planning_precondition",{})
req(pre.get("level2_attempt")==5 and pre.get("level2_workflow_run")==36503684811,"Level3 Level2 precondition")
req(pre.get("knewstuff_runtime_workflow_run")==36595513031 and pre.get("knewstuff_runtime_job_id")==109499716109,"Level3 runtime closure precondition")
req(pre.get("repository_policy_workflow_run")==36601250554 and pre.get("repository_policy_job_id")==109518908048,"Level3 closure policy precondition")
req(pre.get("closure_commit")=="b3890f8b1399da43527a97136365c8d4339385f7" and pre.get("result")=="PASS" and pre.get("canonical_snapshot")==SNAP,"Level3 closure commit/snapshot")

req(l2.get("state")=="PASS" and l2.get("execution_authorized") is False and l2.get("current_attempt")==5,"Level2 closed precondition")
pol=t.get("discovery_policy",{})
req(pol.get("runtime_validation")=="PASS-closed","KNewStuff runtime closure retained")
live=t.get("build_level3",{})
req(t.get("build_level3_manifest")=="manifests/kde-tier3-build-level3.json","Tier3 Level3 manifest linkage")
req(live.get("selected_nodes")==T and live.get("canonical_snapshot")==SNAP,"Tier3 Level3 live node set/snapshot")
if state=="planned-pending-activation":
    req(pol.get("phase")=="build-level3-planning" and pol.get("package_builds")=="tier3-level3-planning-pending-validation","Tier3 Level3 planning live gate")
    req(live.get("status")=="planned-pending-activation" and live.get("execution_authorized") is False and live.get("next_gate")=="tier3-build-level3-planning-validation","Tier3 Level3 live planning state")
elif state=="active-pending-ci":
    req(pol.get("phase")=="build-level3" and pol.get("package_builds")=="tier3-level3-authorized","Tier3 Level3 active live gate")
    req(live.get("status")=="attempt1-active-pending-ci" and live.get("execution_authorized") is True and live.get("current_attempt")==1 and live.get("next_gate")=="tier3-build-level3-attempt1","Tier3 Level3 live Attempt1 state")
    lpv=live.get("planning_validation",{})
    req(all(lpv.get(k)==v for k,v in PV.items()) and lpv.get("result")=="PASS","Tier3 Level3 live planning evidence")

tn={x["id"]:x for x in t.get("nodes",[])}
for x in T:
    req(tn.get(x,{}).get("state")=="pending" and tn.get(x,{}).get("packaging",{}).get("state")=="pending",x+": target must remain pending before package evidence")

dn=d.get("nodes",{})
ret=m.get("retained_predecessors",{})
def pass_pin(x):
    can=dn.get(x,{})
    ev=[e for e in can.get("evidence",[]) if e.get("result")=="PASS" and e.get("artifact_id") and e.get("artifact_sha256")]
    last=ev[-1] if ev else {}
    return {"version":can.get("package_version"),"workflow_run":can.get("workflow_run",last.get("workflow_run")),"artifact_id":can.get("artifact_id",last.get("artifact_id")),"artifact_sha256":can.get("artifact_sha256",last.get("artifact_sha256")),"expected_binary_packages":can.get("binary_packages",[])}
def rec(roots):
    seen=set()
    def visit(x):
        req(x in dn,x+": missing canonical DAG predecessor")
        if x not in dn: return
        for dep in dn[x].get("depends_on",[]):
            if dep!="extra-cmake-modules" and dep not in seen:
                seen.add(dep); visit(dep)
    for x in roots: visit(x)
    return seen

for x,cfg in ret.items():
    can=dn.get(x,{})
    req(can.get("state")=="PASS" and can.get("downstream_eligible") is True,x+": retained predecessor must be canonical PASS")
    pin=pass_pin(x)
    for key in ("version","workflow_run","artifact_id","artifact_sha256","expected_binary_packages"): req(cfg.get(key)==pin.get(key),x+": retained canonical pin "+key)
    req(cfg.get("dev_package") in cfg.get("expected_binary_packages",[]),x+": dev package identity")

req(m.get("support_predecessors")=={k:l2.get("support_predecessors",{}).get(k) for k in ("breeze-icons","kdoctools")},"Level3 support closure pins")

for x in T:
    n=m["nodes"][x]; cp=c["nodes"][x]; mm=mat["nodes"][x]; cc=contracts["nodes"][x]
    req(cp.get("level")==3 and cp.get("state")=="planned",x+": campaign Level3")
    req(n.get("state") in {"prepared-pending-build","remediation-pending-build","PASS","FAIL","BLOCKED"},x+": node state")
    req(n.get("source_package")==cp.get("source_package") and n.get("package_version")==cp.get("package_version") and n.get("expected_binary_packages")==cp.get("expected_binary_packages"),x+": package identity")
    req(n.get("materialization")==cp.get("materialization"),x+": materialization pin")
    req(mm.get("state")=="materialized" and mm.get("evidence",{}).get("result")=="PASS" and mm.get("evidence",{}).get("package_attempted") is False,x+": materialization PASS")
    req(cc.get("contract_state")=="contract-ready" and cc.get("selected_profile",{}).get("BUILD_TESTING") is True,x+": package contract/profile")
    req(n.get("direct_build_predecessors")==D[x],x+": direct Build-Depends/profile inputs")
    provider=sorted(rec(D[x])-set(D[x]))
    req(n.get("provider_closure_input_ids")==provider,x+": provider closure")
    req(n.get("retained_input_ids")==D[x]+provider,x+": retained closure")
    req(all(y in ret for y in n.get("retained_input_ids",[])),x+": retained pins complete")
    req(n.get("buildinfo_proof_packages")==[ret[y]["dev_package"] for y in D[x]],x+": buildinfo proof")
    req(not ({ret[y]["dev_package"] for y in provider}&set(n.get("buildinfo_proof_packages",[]))),x+": closure invented buildinfo edge")
    req(n.get("profile_assertions")==P[x],x+": profile")
    req(n.get("qml_packages")==[y for y in cp.get("expected_binary_packages",[]) if y.startswith("qml6-module-")],x+": QML contract")
    req(n.get("python_module") is None and n.get("runtime_validation_input_ids")==[] and n.get("sbuild_enable_network") is False,x+": undeclared runtime/network")
    req(n.get("support_input_ids")==["breeze-icons","kdoctools"],x+": selected support closure")
    req(n.get("success_transition")=="PASS" and n.get("downstream_eligible_on_build_success") is True,x+": success transition")

req(a.get("schema")==1 and a.get("batch")=="tier3-build-level3" and a.get("selected_nodes")==T and set(a.get("nodes",{}))==set(T),"Level3 ledger")
if state in {"planned-pending-activation","active-pending-ci"}: req(a.get("campaign_history")==[] and all(a["nodes"][x]==[] for x in T),"pre-execution Level3 ledger must be empty")
for p in ("scripts/plan-kde-tier3-build-level3.py","scripts/test-kde-tier3-build-level3-planner.py","scripts/run-kde-tier3-build-level3.sh",".github/workflows/kde-tier3-build-level3.yml","docs/kde-tier3-build-level3.md"): req((ROOT/p).exists(),"missing Level3 component: "+p)

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 build Level 3 definition: PASS")
print("state="+m["state"])
print("execution_authorized="+str(m["execution_authorized"]).lower())
print("canonical="+SNAP)

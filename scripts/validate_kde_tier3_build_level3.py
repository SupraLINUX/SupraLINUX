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

# Attempt 3 source-remediation state is validated by the dedicated remediation lifecycle.
if t.get("level3_remediation",{}).get("status") in {"materialization-pending-ci","materialization-PASS-pending-attempt3-planning-validation"} and t.get("level3_remediation",{}).get("trigger",{}).get("attempt")==2:
    import subprocess
    raise SystemExit(subprocess.run([sys.executable,str(ROOT/"scripts/validate_kde_tier3_level3_remediation.py")]).returncode)

# Attempt 3 is a new live lifecycle over immutable Attempts 1/2.
if m.get("state")=="active-pending-ci" and m.get("current_attempt")==3:
    import subprocess
    for script in ("scripts/validate_kde_tier3_level3_attempt1_closure.py","scripts/validate_kde_tier3_level3_attempt2_closure.py"):
        rc=subprocess.run([sys.executable,str(ROOT/script)]).returncode
        if rc:
            raise SystemExit(rc)

    T3=["ktexteditor","purpose"]
    SNAP3="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED"
    PV3={
      "repository_policy_workflow_run":36644567893,
      "repository_policy_job_id":109664830010,
      "router_plan_job_id":109664829457,
      "commit":"691816b58bd631bc946cdfd617403971f3f6ef2e",
      "planner_runner_scope":"PASS",
      "level3_definition":"PASS",
      "historical_boundary":"PASS",
      "result":"PASS",
    }
    MAT3={
      "ktexteditor":{"workflow_run":36643423967,"job_id":109661057170,"artifact_id":11066929892,"artifact_sha256":"74afd833bcd1f35571e59a9983e5fa56bb8b774eff4210df9c4a5b6a93a321b5","version":"6.30.0-0supralinux3"},
      "purpose":{"workflow_run":36643423967,"job_id":109661057232,"artifact_id":11067860328,"artifact_sha256":"988a4d2f21d152a938e17b802026a9c950fd2a91351ab2fbee6ae1300720945f","version":"6.30.0-0supralinux3"},
    }

    req(m.get("schema")==1 and m.get("authority")=="kde-upstream" and m.get("provider_platform")=="ubuntu-resolute","Attempt3 Level3 schema/authority/provider")
    req(m.get("selected_nodes")==T3 and m.get("canonical_snapshot")==SNAP3,"Attempt3 Level3 node set/snapshot")
    req(m.get("execution_authorized") is True and m.get("next_attempt") is None and m.get("next_gate")=="tier3-build-level3-attempt3","Attempt3 Level3 authorization/gate")
    pv=m.get("attempt3_planning_validation",{})
    req(all(pv.get(k)==v for k,v in PV3.items()),"Attempt3 planning validation evidence")
    act=m.get("attempt3_activation",{})
    req(act.get("status")=="ACTIVE" and act.get("attempt")==3 and act.get("planning_policy_workflow_run")==PV3["repository_policy_workflow_run"] and act.get("planning_commit")==PV3["commit"] and act.get("next_gate")=="tier3-build-level3-attempt3","Attempt3 activation evidence")

    pol=t.get("discovery_policy",{})
    live=t.get("build_level3",{})
    req(pol.get("phase")=="build-level3" and pol.get("package_builds")=="tier3-level3-attempt3-authorized" and pol.get("remediation")=="level3-attempt3-active","Attempt3 canonical live gate")
    req(pol.get("runtime_validation")=="PASS-closed","Attempt3 retains KNewStuff runtime closure")
    req(live.get("status")=="attempt3-active-pending-ci" and live.get("execution_authorized") is True and live.get("current_attempt")==3 and live.get("next_attempt") is None and live.get("next_gate")=="tier3-build-level3-attempt3","Attempt3 canonical live state")
    req(all(live.get("attempt3_planning_validation",{}).get(k)==v for k,v in PV3.items()),"Attempt3 canonical planning evidence")
    req(live.get("attempt3_activation",{}).get("status")=="ACTIVE" and live.get("attempt3_activation",{}).get("attempt")==3 and live.get("attempt3_activation",{}).get("planning_commit")==PV3["commit"],"Attempt3 canonical activation evidence")
    rem=t.get("level3_remediation",{})
    req(rem.get("status")=="attempt3-active" and rem.get("materialization_authorized") is False and rem.get("package_execution_authorized") is True and rem.get("current_attempt")==3 and rem.get("next_attempt") is None and rem.get("next_gate")=="tier3-build-level3-attempt3","Attempt3 remediation live authority")

    tn={x["id"]:x for x in t.get("nodes",[])}
    for node in T3:
        cn=tn.get(node,{})
        pkg=cn.get("packaging",{})
        req(cn.get("state")=="FAIL" and pkg.get("state")=="FAIL" and pkg.get("package_version")=="6.30.0-0supralinux2" and pkg.get("downstream_eligible") is False,node+": Attempt2 canonical FAIL retained until Attempt3 result")

        n=m["nodes"][node]; exp=MAT3[node]
        req(n.get("state")=="remediation-pending-build" and n.get("package_version")==exp["version"],node+": Attempt3 runnable identity")
        req(n.get("materialization")=={k:exp[k] for k in ("workflow_run","job_id","artifact_id","artifact_sha256")},node+": Attempt3 materialization pin")
        req(n.get("support_input_ids")==["breeze-icons","kdoctools","kded"],node+": Attempt3 support closure")

        mm=mat.get("nodes",{}).get(node,{})
        req(mm.get("state")=="materialized" and mm.get("package_version")==exp["version"] and mm.get("evidence",{}).get("result")=="PASS" and mm.get("evidence",{}).get("package_attempted") is False,node+": Attempt3 source-only materialization PASS")
        cp=c.get("nodes",{}).get(node,{})
        req(cp.get("package_version")==exp["version"] and cp.get("materialization")==n.get("materialization"),node+": generated campaign Attempt3 pin")

    hist=a.get("campaign_history",[])
    req(len(hist)==2 and [x.get("attempt") for x in hist]==[1,2] and all(x.get("result")=="FAIL" for x in hist),"Attempt3 pre-execution campaign ledger retains Attempts 1/2 only")
    for node in T3:
        rows=a.get("nodes",{}).get(node,[])
        req(len(rows)==2 and [x.get("attempt") for x in rows]==[1,2] and all(x.get("result")=="FAIL" for x in rows),node+": Attempt3 pre-execution ledger retains Attempts 1/2 only")

    if errors:
        for e in errors: print("ERROR:",e,file=sys.stderr)
        raise SystemExit(1)
    print("KDE Tier 3 build Level 3 Attempt 3 definition: PASS")
    print("state=active-pending-ci")
    print("execution_authorized=true")
    print("canonical="+SNAP3)
    raise SystemExit(0)

# Closed Attempt 2: validate immutable history first, then only current live closure.
if m.get("state")=="FAIL" and m.get("current_attempt")==2:
    import subprocess
    for script in ("scripts/validate_kde_tier3_level3_attempt1_closure.py","scripts/validate_kde_tier3_level3_attempt2_closure.py"):
        rc=subprocess.run([sys.executable,str(ROOT/script)]).returncode
        if rc:
            raise SystemExit(rc)
    SNAP2="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED"
    req(m.get("execution_authorized") is False and m.get("next_attempt")==3 and m.get("next_gate")=="tier3-build-level3-attempt2-remediation-definition","Attempt2 closed Level3 authorization/gate")
    req(m.get("canonical_snapshot")==SNAP2,"Attempt2 closed Level3 snapshot")
    pol=t.get("discovery_policy",{})
    live=t.get("build_level3",{})
    req(pol.get("phase")=="build-level3-remediation-planning" and pol.get("package_builds")=="tier3-level3-attempt2-closed-FAIL" and pol.get("remediation")=="level3-attempt2-closed-failure","Attempt2 closed canonical gate")
    req(pol.get("runtime_validation")=="PASS-closed","Attempt2 closure retains KNewStuff runtime PASS")
    req(live.get("status")=="attempt2-closed-FAIL" and live.get("execution_authorized") is False and live.get("current_attempt")==2 and live.get("next_attempt")==3 and live.get("next_gate")=="tier3-build-level3-attempt2-remediation-definition","Attempt2 closed canonical Level3 state")
    rem=t.get("level3_remediation",{})
    req(rem.get("status")=="attempt2-closed-FAIL-pending-remediation-definition" and rem.get("materialization_authorized") is False and rem.get("package_execution_authorized") is False and rem.get("current_attempt")==2 and rem.get("next_attempt")==3,"Attempt2 remediation execution pause")
    req(mat.get("state")=="PASS" and mat.get("package_attempted") is False and mat.get("package_state_effect")=="none","Attempt2 source materialization remains closed source-only PASS")
    tn={x["id"]:x for x in t.get("nodes",[])}
    expected={
      "ktexteditor":("6.30.0-0supralinux2",109648411937,11066168089,"74fd2819b9110d7a8ce35ca2a2c8a89fb1a9b31548e32e05de2cb0e9426234e6"),
      "purpose":("6.30.0-0supralinux2",109648412196,11066102772,"adf13dd09a0ebd4b001f51c83cfe2b19360fa482b6c73c1a1ab579e7914e0a19"),
    }
    for node,(version,job,artifact,digest) in expected.items():
        n=m.get("nodes",{}).get(node,{})
        req(n.get("state")=="FAIL" and n.get("package_version")==version,node+": closed Attempt2 Level3 package state")
        fe=n.get("fail_evidence",{})
        req(fe.get("workflow_run")==36639418961 and fe.get("job_id")==job and fe.get("artifact_id")==artifact and fe.get("artifact_sha256")==digest and fe.get("package_attempted") is True,node+": Level3 current FAIL evidence")
        cn=tn.get(node,{})
        pkg=cn.get("packaging",{})
        req(cn.get("state")=="FAIL" and pkg.get("state")=="FAIL" and pkg.get("package_version")==version and pkg.get("downstream_eligible") is False,node+": canonical current FAIL")
        cfe=pkg.get("failure_evidence",{})
        req(cfe.get("workflow_run")==36639418961 and cfe.get("job_id")==job and cfe.get("artifact_id")==artifact and cfe.get("artifact_sha256")==digest and cfe.get("package_attempted") is True,node+": canonical current FAIL evidence")
    if errors:
        for e in errors: print("ERROR:",e,file=sys.stderr)
        raise SystemExit(1)
    print("KDE Tier 3 build Level 3 Attempt 2 closure: PASS")
    print("state=FAIL")
    print("execution_authorized=false")
    print("canonical="+SNAP2)
    raise SystemExit(0)

# Attempt 2 is a new live lifecycle over immutable Attempt 1 history.
# Validate it independently so closed Attempt 1 evidence never constrains future live state.
if m.get("state")=="active-pending-ci" and m.get("current_attempt")==2:
    import subprocess
    rc=subprocess.run([sys.executable,str(ROOT/"scripts/validate_kde_tier3_level3_attempt1_closure.py")]).returncode
    if rc:
        raise SystemExit(rc)

    T2=["ktexteditor","purpose"]
    SNAP2="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED"
    PV2={
      "repository_policy_workflow_run":36638763826,
      "repository_policy_job_id":109645765290,
      "router_plan_job_id":109645764969,
      "commit":"53189d094b89afecbd6e382fe8fd4054334c1a0e",
      "planner_runner_scope":"PASS",
      "level3_definition":"PASS",
      "historical_boundary":"PASS",
      "result":"PASS",
    }
    SUPPORT2={
      "breeze-icons":{
        "version":"4:6.30.0-0supralinux1","workflow_run":35700002095,
        "artifact_id":10682012012,"artifact_sha256":"daaa5abda5a8f824c6fa509142d7cd9132de213d782cb32e0561873f427aa577",
        "expected_binary_packages":["breeze-icon-theme","breeze-icon-theme-rcc","kf6-breeze-icon-theme","kf6-breeze-icon-theme-rcc","libkf6breezeicons-dev","libkf6breezeicons6"],
        "dev_package":"libkf6breezeicons-dev","provenance":"tier3-support-pass",
      },
      "kdoctools":{
        "version":"6.30.0-0supralinux1","workflow_run":35700002095,
        "artifact_id":10682066198,"artifact_sha256":"6daeb6beed63ba7b7e441dba4dfd356be3ad48a9f3ae75acddae0945c36a683d",
        "expected_binary_packages":["kdoctools6","libkf6doctools-dev","libkf6doctools-doc","libkf6doctools6"],
        "dev_package":"libkf6doctools-dev","provenance":"tier3-support-pass",
      },
      "kded":{
        "version":"6.30.0-0supralinux1","workflow_run":35721085911,
        "artifact_id":10691372157,"artifact_sha256":"ff8756cf6efb4746568fa032cfb17cdf5c6b47bc31f532130936536aecb7c5c9",
        "expected_binary_packages":["kded6","kded6-dev"],"dev_package":"kded6-dev","provenance":"tier3-support-level1-pass",
      },
    }
    MAT2={
      "ktexteditor":{"workflow_run":36637751833,"job_id":109643132222,"artifact_id":11064709291,"artifact_sha256":"606f9e22f162382f60b9499654248ebb8ac9e7970f47934b11457757a832becf","version":"6.30.0-0supralinux2"},
      "purpose":{"workflow_run":36614234522,"job_id":109563580375,"artifact_id":11054941469,"artifact_sha256":"b7fa3f20bacbc6b142f18596cc6cabd3a670a86f9246f39f7307be905dac16c7","version":"6.30.0-0supralinux2"},
    }

    req(m.get("schema")==1 and m.get("authority")=="kde-upstream" and m.get("provider_platform")=="ubuntu-resolute","Attempt2 Level3 schema/authority/provider")
    req(m.get("selected_nodes")==T2 and m.get("canonical_snapshot")==SNAP2,"Attempt2 Level3 node set/snapshot")
    req(m.get("execution_authorized") is True and m.get("next_attempt") is None and m.get("next_gate")=="tier3-build-level3-attempt2","Attempt2 Level3 authorization/gate")
    pv=m.get("attempt2_planning_validation",{})
    req(all(pv.get(k)==v for k,v in PV2.items()),"Attempt2 planning validation evidence")
    act=m.get("attempt2_activation",{})
    req(act.get("status")=="ACTIVE" and act.get("attempt")==2 and act.get("planning_policy_workflow_run")==PV2["repository_policy_workflow_run"] and act.get("planning_commit")==PV2["commit"] and act.get("next_gate")=="tier3-build-level3-attempt2","Attempt2 activation evidence")

    pol=t.get("discovery_policy",{})
    live=t.get("build_level3",{})
    req(pol.get("phase")=="build-level3" and pol.get("package_builds")=="tier3-level3-attempt2-authorized" and pol.get("remediation")=="level3-attempt2-active","Attempt2 canonical live gate")
    req(pol.get("runtime_validation")=="PASS-closed","Attempt2 retains KNewStuff runtime closure")
    req(live.get("status")=="attempt2-active-pending-ci" and live.get("execution_authorized") is True and live.get("current_attempt")==2 and live.get("next_attempt") is None and live.get("next_gate")=="tier3-build-level3-attempt2","Attempt2 canonical live state")
    lpv=live.get("attempt2_planning_validation",{})
    req(all(lpv.get(k)==v for k,v in PV2.items()),"Attempt2 canonical planning evidence")
    lact=live.get("attempt2_activation",{})
    req(lact.get("status")=="ACTIVE" and lact.get("attempt")==2 and lact.get("planning_commit")==PV2["commit"],"Attempt2 canonical activation evidence")
    rem=t.get("level3_remediation",{})
    req(rem.get("status")=="attempt2-active" and rem.get("materialization_authorized") is False and rem.get("package_execution_authorized") is True and rem.get("current_attempt")==2 and rem.get("next_attempt") is None,"Attempt2 remediation live authority")

    tn={x["id"]:x for x in t.get("nodes",[])}
    for node in T2:
        req(tn.get(node,{}).get("state")=="FAIL" and tn.get(node,{}).get("packaging",{}).get("state")=="FAIL" and tn.get(node,{}).get("packaging",{}).get("downstream_eligible") is False,node+": Attempt1 FAIL retained until Attempt2 result")
        n=m["nodes"][node]; exp=MAT2[node]
        req(n.get("state")=="remediation-pending-build" and n.get("package_version")==exp["version"],node+": Attempt2 runnable identity")
        req(n.get("materialization")=={k:exp[k] for k in ("workflow_run","job_id","artifact_id","artifact_sha256")},node+": Attempt2 materialization pin")
        req(n.get("support_input_ids")==["breeze-icons","kdoctools","kded"],node+": Attempt2 support closure")
        mm=mat.get("nodes",{}).get(node,{})
        req(mm.get("state")=="materialized" and mm.get("package_version")==exp["version"] and mm.get("evidence",{}).get("result")=="PASS" and mm.get("evidence",{}).get("package_attempted") is False,node+": source-only materialization PASS")
        cp=c.get("nodes",{}).get(node,{})
        req(cp.get("package_version")==exp["version"] and cp.get("materialization")==n.get("materialization"),node+": generated campaign Attempt2 pin")

    req(m.get("support_predecessors")==SUPPORT2,"Attempt2 exact support predecessor pins")

    hist=a.get("campaign_history",[])
    req(len(hist)==1 and hist[0].get("attempt")==1 and hist[0].get("result")=="FAIL","Attempt2 pre-execution campaign ledger retains only Attempt1")
    for node in T2:
        rows=a.get("nodes",{}).get(node,[])
        req(len(rows)==1 and rows[0].get("attempt")==1 and rows[0].get("result")=="FAIL",node+": Attempt2 pre-execution ledger retains only Attempt1")

    if errors:
        for e in errors: print("ERROR:",e,file=sys.stderr)
        raise SystemExit(1)
    print("KDE Tier 3 build Level 3 Attempt 2 definition: PASS")
    print("state=active-pending-ci")
    print("execution_authorized=true")
    print("canonical="+SNAP2)
    raise SystemExit(0)

if t.get("level3_remediation",{}).get("status") in {"materialization-pending-ci","materialization-PASS-pending-attempt2-planning-validation"}:
    import subprocess
    raise SystemExit(subprocess.run([sys.executable, str(ROOT/"scripts/validate_kde_tier3_level3_remediation.py")]).returncode)

T=["ktexteditor","purpose"]
D={
  "ktexteditor":["kio","kparts","karchive","kconfig","kguiaddons","ki18n","sonnet","syntax-highlighting","kcolorscheme","kauth"],
  "purpose":["kio","kcmutils","kcoreaddons","ki18n","kconfig","kirigami","knotifications","kservice","prison","kitemmodels"],
}
P={"ktexteditor":{"BUILD_TESTING":"ON"},"purpose":{"BUILD_TESTING":"ON"}}
PRE_SNAP="18 PASS / 2 pending / 0 current FAIL / 0 BLOCKED"
FAIL_SNAP="18 PASS / 0 pending / 2 current FAIL / 0 BLOCKED"

req(m.get("schema")==1 and m.get("authority")=="kde-upstream" and m.get("provider_platform")=="ubuntu-resolute","Level3 schema/authority/provider")
req(m.get("role")=="tier3-binary-build-level3" and m.get("frameworks_series")=="6.30.0","Level3 role/series")
state=m.get("state")
expected_snap=FAIL_SNAP if state=="FAIL" else PRE_SNAP
req(m.get("selected_nodes")==T and m.get("canonical_snapshot")==expected_snap,"Level3 node set/snapshot")
PV={"repository_policy_workflow_run":36606233220,"repository_policy_job_id":109535845900,"router_plan_job_id":109535845121,"commit":"87099ae7fa83a41edde584c60cea0d2880e22d4c"}
if state=="planned-pending-activation":
    req(m.get("execution_authorized") is False and m.get("next_gate")=="tier3-build-level3-planning-validation","planned Level3 authorization/gate")
elif state=="active-pending-ci":
    req(m.get("execution_authorized") is True and m.get("current_attempt")==1 and m.get("next_attempt") is None and m.get("next_gate")=="tier3-build-level3-attempt1","active Level3 authorization/gate")
    pv=m.get("planning_validation",{})
    req(all(pv.get(k)==v for k,v in PV.items()) and pv.get("planner_runner_scope")=="PASS" and pv.get("level3_definition")=="PASS" and pv.get("historical_boundary")=="PASS" and pv.get("result")=="PASS","Level3 Attempt1 planning validation evidence")
    act=m.get("activation",{})
    req(act.get("status")=="ACTIVE" and act.get("attempt")==1 and act.get("planning_policy_workflow_run")==PV["repository_policy_workflow_run"] and act.get("planning_commit")==PV["commit"],"Level3 Attempt1 activation evidence")
elif state=="FAIL":
    req(m.get("execution_authorized") is False and m.get("current_attempt")==1 and m.get("next_attempt")==2 and m.get("next_gate")=="tier3-build-level3-attempt1-remediation-definition","closed FAIL Level3 authorization/gate")
else:
    req(state in {"PASS","PARTIAL"},"Level3 lifecycle")

pre=m.get("planning_precondition",{})
req(pre.get("level2_attempt")==5 and pre.get("level2_workflow_run")==36503684811,"Level3 Level2 precondition")
req(pre.get("knewstuff_runtime_workflow_run")==36595513031 and pre.get("knewstuff_runtime_job_id")==109499716109,"Level3 runtime closure precondition")
req(pre.get("repository_policy_workflow_run")==36601250554 and pre.get("repository_policy_job_id")==109518908048,"Level3 closure policy precondition")
req(pre.get("closure_commit")=="b3890f8b1399da43527a97136365c8d4339385f7" and pre.get("result")=="PASS" and pre.get("canonical_snapshot")==PRE_SNAP,"Level3 closure commit/snapshot")

req(l2.get("state")=="PASS" and l2.get("execution_authorized") is False and l2.get("current_attempt")==5,"Level2 closed precondition")
pol=t.get("discovery_policy",{})
req(pol.get("runtime_validation")=="PASS-closed","KNewStuff runtime closure retained")
live=t.get("build_level3",{})
req(t.get("build_level3_manifest")=="manifests/kde-tier3-build-level3.json","Tier3 Level3 manifest linkage")
req(live.get("selected_nodes")==T and live.get("canonical_snapshot")==expected_snap,"Tier3 Level3 live node set/snapshot")
if state=="planned-pending-activation":
    req(pol.get("phase")=="build-level3-planning" and pol.get("package_builds")=="tier3-level3-planning-pending-validation","Tier3 Level3 planning live gate")
    req(live.get("status")=="planned-pending-activation" and live.get("execution_authorized") is False and live.get("next_gate")=="tier3-build-level3-planning-validation","Tier3 Level3 live planning state")
elif state=="active-pending-ci":
    req(pol.get("phase")=="build-level3" and pol.get("package_builds")=="tier3-level3-authorized","Tier3 Level3 active live gate")
    req(live.get("status")=="attempt1-active-pending-ci" and live.get("execution_authorized") is True and live.get("current_attempt")==1 and live.get("next_gate")=="tier3-build-level3-attempt1","Tier3 Level3 live Attempt1 state")
    lpv=live.get("planning_validation",{})
    req(all(lpv.get(k)==v for k,v in PV.items()) and lpv.get("result")=="PASS","Tier3 Level3 live planning evidence")
elif state=="FAIL":
    req(pol.get("phase")=="build-level3-remediation-planning" and pol.get("package_builds")=="tier3-level3-attempt1-closed-FAIL","Tier3 Level3 FAIL live gate")
    req(live.get("status")=="attempt1-closed-FAIL" and live.get("execution_authorized") is False and live.get("current_attempt")==1 and live.get("next_attempt")==2 and live.get("next_gate")=="tier3-build-level3-attempt1-remediation-definition","Tier3 Level3 live FAIL state")

tn={x["id"]:x for x in t.get("nodes",[])}
for x in T:
    if state=="FAIL":
        req(tn.get(x,{}).get("state")=="FAIL" and tn.get(x,{}).get("packaging",{}).get("state")=="FAIL" and tn.get(x,{}).get("packaging",{}).get("downstream_eligible") is False,x+": target must retain canonical FAIL")
    else:
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
if state in {"planned-pending-activation","active-pending-ci"}:
    req(a.get("campaign_history")==[] and all(a["nodes"][x]==[] for x in T),"pre-execution Level3 ledger must be empty")
elif state=="FAIL":
    req(len(a.get("campaign_history",[]))==1 and all(len(a["nodes"][x])==1 for x in T),"Attempt1 closed ledger cardinality")
for p in ("scripts/plan-kde-tier3-build-level3.py","scripts/test-kde-tier3-build-level3-planner.py","scripts/run-kde-tier3-build-level3.sh",".github/workflows/kde-tier3-build-level3.yml","docs/kde-tier3-build-level3.md"): req((ROOT/p).exists(),"missing Level3 component: "+p)

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 build Level 3 definition: PASS")
print("state="+m["state"])
print("execution_authorized="+str(m["execution_authorized"]).lower())
print("canonical="+m["canonical_snapshot"])

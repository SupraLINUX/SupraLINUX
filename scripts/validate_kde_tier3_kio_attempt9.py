#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())
T=load("manifests/kde-frameworks-tier3.json"); L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json"); M=load("manifests/kde-tier3-materialization.json")
P=load("manifests/kde-tier3-build-campaign.json"); A=load("manifests/kde-tier3-build-level1-attempts.json")
R=load("manifests/kde-tier3-kio-attempt9-remediation.json"); D=load("manifests/kde-dag.json")
POLICY_RUN=36415650130; PLANNER_RUN=36415653322; PLAN_COMMIT="bcc76458eecff8118d5526c043d18aa7de3b4b4c"
KIO_VERSION="6.30.0-0supralinux9"; KXML_VERSION="6.30.0-0supralinux5"
KIO_MAT={"workflow_run":36413768965,"job_id":108899950721,"artifact_id":10965892140,"artifact_sha256":"b11e6cf5142aab878578f5d7662b3c0e2cf41fd306b3ecaffbc76e78c1e63f2c"}
KXML_MAT={"workflow_run":36002910277,"job_id":107643756357,"artifact_id":10808294092,"artifact_sha256":"bccf76b46d0c9619e4306f1fe704ff5b501b9554a63f7968093e3afd4beb0d86"}
BLOCKED={"baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"}
policy=T.get("discovery_policy",{})
req(policy.get("phase")=="build-level1" and policy.get("package_builds")=="tier3-level1-authorized" and policy.get("remediation")=="attempt9-kio-proven-remediation-attempt9-active","Attempt9 canonical authorization")
nodes={n["id"]:n for n in T.get("nodes",[])}
req(nodes["kio"].get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux8" and nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"canonical KIO remains FAIL/-8")
req(nodes["kxmlgui"].get("state")=="PASS" and nodes["kxmlgui"].get("packaging",{}).get("package_version")==KXML_VERSION,"canonical KXMLGui PASS/-5")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==BLOCKED and "kio" not in D.get("nodes",{}),"canonical BLOCKED/DAG boundary")
ar=T.get("active_remediation",{})
req(ar.get("round")==11 and ar.get("status")=="level1-active-pending-ci","canonical Attempt9 active")
req(ar.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"canonical Attempt9 versions")
req(ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True and ar.get("current_attempt")==9 and ar.get("next_attempt")==9 and ar.get("next_gate")=="tier3-build-level1-attempt9","canonical Attempt9 authority/markers")
req(ar.get("activation_policy_workflow_run")==POLICY_RUN and ar.get("activation_level1_workflow_run")==PLANNER_RUN and ar.get("activation_commit")==PLAN_COMMIT,"canonical planning evidence")
req(ar.get("planning_validation")=={"repository_policy_workflow_run":POLICY_RUN,"level1_workflow_run":PLANNER_RUN,"commit":PLAN_COMMIT,"result":"PASS"},"canonical planning validation")
req(L.get("state")=="active-pending-ci" and L.get("execution_authorized") is True and L.get("current_attempt")==9 and L.get("next_attempt")==9 and L.get("next_gate")=="tier3-build-level1-attempt9","Level1 Attempt9 active")
act=L.get("activation",{})
req(act.get("status")=="ACTIVE" and act.get("attempt")==9 and act.get("scope")=="full-level1-rerun-2-nodes","Level1 Attempt9 activation")
req(act.get("remediation_validation_policy_workflow_run")==POLICY_RUN and act.get("remediation_validation_level1_workflow_run")==PLANNER_RUN and act.get("remediation_commit")==PLAN_COMMIT,"Level1 planning evidence")
lr=L.get("active_remediation",{})
req(lr.get("global_round")==11 and lr.get("status")=="materialization-PASS-attempt9-active" and lr.get("execution_authorized") is True and lr.get("level1_execution_authorized") is True,"Level1 remediation active")
req(lr.get("source_rematerialization_required") is False and lr.get("full_level1_rerun_required") is True,"Level1 source/full rerun semantics")
lk=L.get("nodes",{}).get("kio",{}); lx=L.get("nodes",{}).get("kxmlgui",{})
req(lk.get("state")=="prepared-pending-revalidation" and lk.get("package_version")==KIO_VERSION and lk.get("current_attempt")==9,"KIO runnable Attempt9")
req(lx.get("state")=="prepared-pending-revalidation" and lx.get("package_version")==KXML_VERSION and lx.get("current_attempt")==9,"KXMLGui runnable Attempt9")
for actual,expected,name in ((lk.get("materialization",{}),KIO_MAT,"KIO"),(lx.get("materialization",{}),KXML_MAT,"KXMLGui")):
    for key,val in expected.items(): req(actual.get(key)==val,f"{name} materialization {key}")
req(lk.get("last_attempt",{}).get("attempt")==8 and lk.get("last_attempt",{}).get("result")=="FAIL","KIO Attempt8 FAIL retained")
req(lx.get("last_attempt",{}).get("attempt")==8 and lx.get("last_attempt",{}).get("result")=="PASS","KXMLGui Attempt8 PASS retained")
cr=C.get("active_remediation",{})
req(cr.get("round")==11 and cr.get("status")=="materialization-PASS-attempt9-active","contracts Attempt9 active")
req(cr.get("execution_authorized") is True and cr.get("level1_execution_authorized") is True and cr.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"contracts authority/versions")
req(cr.get("activation_policy_workflow_run")==POLICY_RUN and cr.get("activation_level1_workflow_run")==PLANNER_RUN and cr.get("activation_commit")==PLAN_COMMIT,"contracts planning evidence")
req(C.get("nodes",{}).get("kio",{}).get("package_version_candidate")==KIO_VERSION,"KIO contract -9")
req(M.get("state")=="PASS" and "remediation_queue" not in M,"materialization remains PASS")
req(M.get("nodes",{}).get("kio",{}).get("package_version")==KIO_VERSION and M.get("nodes",{}).get("kio",{}).get("evidence",{}).get("artifact_id")==KIO_MAT["artifact_id"],"KIO -9 source PASS")
req(M.get("active_remediation",{}).get("next_gate")=="tier3-build-level1-attempt9","materialization Attempt9 handoff")
req(P.get("execution_authorized") is False,"generated campaign remains planning-only")
req(P.get("nodes",{}).get("kio",{}).get("package_version")==KIO_VERSION and P.get("nodes",{}).get("kio",{}).get("materialization",{}).get("artifact_id")==KIO_MAT["artifact_id"],"generated plan pins KIO -9")
req(P.get("nodes",{}).get("kxmlgui",{}).get("package_version")==KXML_VERSION and P.get("nodes",{}).get("kxmlgui",{}).get("materialization",{}).get("artifact_id")==KXML_MAT["artifact_id"],"generated plan pins KXMLGui -5")
req(not any(x.get("attempt")==9 for x in A.get("campaign_history",[])),"Attempt9 result must not exist before build")
req(R.get("status")=="attempt9-active" and R.get("execution_authorized") is True and R.get("package_execution_authorized") is True and R.get("level1_execution_authorized") is True,"Attempt9 active record")
req(R.get("gates",{}).get("current")=="tier3-build-level1-attempt9","Attempt9 current gate")
ra=R.get("activation",{})
req(ra.get("nodes")==["kio","kxmlgui"] and ra.get("repository_policy_workflow_run")==POLICY_RUN and ra.get("level1_planning_workflow_run")==PLANNER_RUN and ra.get("commit")==PLAN_COMMIT,"Attempt9 activation evidence")
for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Attempt9")): req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable policy")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 1 Attempt 9 activation: PASS")
print("runnable_nodes=kio,kxmlgui")
print("KIO=6.30.0-0supralinux9; KXMLGui=6.30.0-0supralinux5")
print("canonical package state unchanged until real Attempt9 results")

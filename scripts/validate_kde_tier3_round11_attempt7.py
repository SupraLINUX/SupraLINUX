#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
C=load("manifests/kde-tier3-package-contracts.json")
M=load("manifests/kde-tier3-materialization.json")
P=load("manifests/kde-tier3-build-campaign.json")
A=load("manifests/kde-tier3-build-level1-attempts.json")
G=load("manifests/kde-dag.json")
Q=load("manifests/kde-tier3-kio-round11-diagnostic.json")
R=load("manifests/kde-tier3-kio-round11-remediation.json")

POLICY_RUN=36076306121
PLANNER_RUN=36076306143
PLAN_COMMIT="8ac22bf8d97a592a548fbfc9a40af65773fd4d30"
KIO_VERSION="6.30.0-0supralinux7"
KXML_VERSION="6.30.0-0supralinux5"
KIO_MAT={"workflow_run":36073638711,"job_id":107879979760,"artifact_id":10839162922,"artifact_sha256":"ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c"}
KXML_MAT={"workflow_run":36002910277,"job_id":107643756357,"artifact_id":10808294092,"artifact_sha256":"bccf76b46d0c9619e4306f1fe704ff5b501b9554a63f7968093e3afd4beb0d86"}
BLOCKED=["baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"]
PASS={"kbookmarks","kconfigwidgets","kdav","kdesu","kiconthemes","kjobwidgets","kpeople","krunner","ksvg","ktextwidgets","kwallet","kxmlgui"}

policy=T.get("discovery_policy",{})
req(policy.get("phase")=="build-level1","Attempt7 canonical phase")
req(policy.get("package_builds")=="tier3-level1-authorized","Attempt7 canonical authorization")
req(policy.get("remediation")=="round11-kio-attempt7-active","Attempt7 remediation marker")

nodes={n["id"]:n for n in T.get("nodes",[])}
req({n for n,v in nodes.items() if v.get("state")=="PASS"}==PASS,"Attempt7 canonical PASS set unchanged")
req({n for n,v in nodes.items() if v.get("state")=="pending"}=={"knewstuff"},"Attempt7 canonical pending set unchanged")
req({n for n,v in nodes.items() if v.get("state")=="FAIL"}=={"kio"},"Attempt7 canonical KIO FAIL retained until result")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==set(BLOCKED),"Attempt7 canonical BLOCKED set unchanged")
req(nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux6" and nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"canonical KIO result remains -6 FAIL")
req(nodes["kxmlgui"].get("packaging",{}).get("package_version")==KXML_VERSION and nodes["kxmlgui"].get("packaging",{}).get("downstream_eligible") is True,"canonical KXMLGui PASS retained")
req("kio" not in G.get("nodes",{}),"KIO still absent from canonical DAG before Attempt7 result")
req(G.get("nodes",{}).get("kxmlgui",{}).get("state")=="PASS","KXMLGui remains canonical DAG PASS")

ar=T.get("active_remediation",{})
req(ar.get("round")==11 and ar.get("status")=="level1-active-pending-ci","canonical Round11 Attempt7 active")
req(ar.get("nodes")==["kio","kxmlgui"] and ar.get("source_materialization_nodes")==["kio"] and ar.get("retained_revalidation_nodes")==["kxmlgui"],"canonical Attempt7 scope")
req(ar.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"canonical Attempt7 versions")
req(ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True and ar.get("full_level1_rerun_required") is True,"canonical Attempt7 execution authority")
req(ar.get("current_attempt")==7 and ar.get("next_attempt")==7 and ar.get("next_gate")=="tier3-build-level1-attempt7","canonical Attempt7 markers")
req(ar.get("activation_policy_workflow_run")==POLICY_RUN and ar.get("activation_level1_workflow_run")==PLANNER_RUN and ar.get("activation_commit")==PLAN_COMMIT,"canonical planning validation evidence")

req(L.get("state")=="active-pending-ci" and L.get("execution_authorized") is True,"Level1 Attempt7 active")
req(L.get("selected_nodes")==["kio","kxmlgui"],"Level1 Attempt7 selected nodes")
req(L.get("current_attempt")==7 and L.get("next_attempt")==7 and L.get("next_gate")=="tier3-build-level1-attempt7","Level1 Attempt7 markers")
act=L.get("activation",{})
req(act.get("status")=="ACTIVE" and act.get("attempt")==7 and act.get("scope")=="full-level1-rerun-2-nodes","Level1 Attempt7 activation marker")
req(act.get("remediation_validation_policy_workflow_run")==POLICY_RUN and act.get("remediation_validation_level1_workflow_run")==PLANNER_RUN and act.get("remediation_commit")==PLAN_COMMIT,"Level1 Attempt7 planning evidence")
lr=L.get("active_remediation",{})
req(lr.get("global_round")==11 and lr.get("status")=="materialization-PASS-attempt7-active","Level1 Round11 Attempt7 state")
req(lr.get("source_changed_nodes")==["kio"] and lr.get("retained_revalidation_nodes")==["kxmlgui"],"Level1 source/revalidation classes")
req(lr.get("execution_authorized") is True and lr.get("source_rematerialization_required") is False and lr.get("full_level1_rerun_required") is True,"Level1 Attempt7 execution/source semantics")
req(lr.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"Level1 Attempt7 versions")
req(lr.get("activation_policy_workflow_run")==POLICY_RUN and lr.get("activation_level1_workflow_run")==PLANNER_RUN and lr.get("activation_commit")==PLAN_COMMIT,"Level1 remediation planning evidence")

lk=L.get("nodes",{}).get("kio",{})
lx=L.get("nodes",{}).get("kxmlgui",{})
req(lk.get("state")=="prepared-pending-revalidation" and lk.get("package_version")==KIO_VERSION and lk.get("current_attempt")==7,"KIO runnable Attempt7")
req(lx.get("state")=="prepared-pending-revalidation" and lx.get("package_version")==KXML_VERSION and lx.get("current_attempt")==7,"KXMLGui runnable Attempt7 revalidation")
for actual,expected,name in ((lk.get("materialization",{}),KIO_MAT,"KIO"),(lx.get("materialization",{}),KXML_MAT,"KXMLGui")):
    for key,val in expected.items(): req(actual.get(key)==val,f"{name} materialization {key}")
req(lk.get("last_attempt",{}).get("attempt")==6 and lk.get("last_attempt",{}).get("result")=="FAIL","KIO Attempt6 result retained")
req(lx.get("last_attempt",{}).get("attempt")==6 and lx.get("last_attempt",{}).get("result")=="PASS","KXMLGui Attempt6 PASS retained")
req(lx.get("downstream_eligible") is True and lx.get("pass_evidence",{}).get("downstream_eligible") is True,"KXMLGui canonical/pass evidence not degraded by revalidation")

cr=C.get("active_remediation",{})
req(cr.get("round")==11 and cr.get("status")=="materialization-PASS-attempt7-active","contract Attempt7 active")
req(cr.get("execution_authorized") is True and cr.get("level1_execution_authorized") is True,"contract Attempt7 execution authority")
req(cr.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"contract Attempt7 versions")
req(cr.get("activation_policy_workflow_run")==POLICY_RUN and cr.get("activation_level1_workflow_run")==PLANNER_RUN and cr.get("activation_commit")==PLAN_COMMIT,"contract planning evidence")
kc=C.get("nodes",{}).get("kio",{})
req(kc.get("package_version_candidate")==KIO_VERSION,"KIO contract -7")
rr=[x for x in kc.get("rules_text_replacements",[]) if x.get("classification")=="upstream-test-environment-targeted-nondestructive-correction"]
req(len(rr)==1 and "ENVIRONMENT_MODIFICATION" in rr[0].get("new",""),"KIO non-destructive CTest contract retained")
req(kc.get("test_policy",{}).get("failures_fatal") is True,"KIO upstream test failures remain fatal")

req(M.get("state")=="PASS" and "remediation_queue" not in M,"materialization remains PASS/no queue")
mk=M.get("nodes",{}).get("kio",{})
mx=M.get("nodes",{}).get("kxmlgui",{})
req(mk.get("state")=="materialized" and mk.get("package_version")==KIO_VERSION and mk.get("evidence",{}).get("artifact_id")==KIO_MAT["artifact_id"],"KIO -7 source PASS retained")
req(mx.get("state")=="materialized" and mx.get("package_version")==KXML_VERSION and mx.get("evidence",{}).get("artifact_id")==KXML_MAT["artifact_id"],"KXMLGui -5 source PASS retained")
req(M.get("active_remediation",{}).get("next_gate")=="tier3-build-level1-attempt7","materialization Attempt7 handoff")

req(P.get("execution_authorized") is False,"generated campaign stays planning-only")
req(P.get("nodes",{}).get("kio",{}).get("package_version")==KIO_VERSION and P.get("nodes",{}).get("kio",{}).get("materialization",{}).get("artifact_id")==KIO_MAT["artifact_id"],"generated plan pins KIO -7")
req(P.get("nodes",{}).get("kxmlgui",{}).get("package_version")==KXML_VERSION and P.get("nodes",{}).get("kxmlgui",{}).get("materialization",{}).get("artifact_id")==KXML_MAT["artifact_id"],"generated plan pins KXMLGui -5")

req(not any(x.get("attempt")==7 for x in A.get("campaign_history",[])),"Attempt7 result must not exist before build")
req(Q.get("status")=="diagnostic-PASS","Round11 diagnostic remains PASS")
req(Q.get("diagnostic_results",{}).get("krecentdocument",{}).get("rerun_policy")=="remain-fatal-in-next-full-Level1-attempt","KRecentDocument remains fatal")
req(R.get("status")=="attempt7-active" and R.get("execution_authorized") is True and R.get("source_materialization_authorized") is False,"Round11 record Attempt7 active")
req(R.get("next_gate")=="tier3-build-level1-attempt7","Round11 Attempt7 gate")
ra=R.get("activation",{})
req(ra.get("nodes")==["kio","kxmlgui"] and ra.get("repository_policy_workflow_run")==POLICY_RUN and ra.get("level1_planning_workflow_run")==PLANNER_RUN and ra.get("commit")==PLAN_COMMIT,"Round11 activation evidence")

for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Round11 remediation")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable approval policy")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 1 Attempt 7 activation: PASS")
print("runnable_nodes=kio,kxmlgui")
print("KIO=6.30.0-0supralinux7; KXMLGui=6.30.0-0supralinux5")
print("canonical package state unchanged until real Attempt7 results")

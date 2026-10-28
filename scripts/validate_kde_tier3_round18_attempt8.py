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
R=load("manifests/kde-tier3-kio-round18-remediation.json")
D=load("manifests/kde-dag.json")

POLICY_RUN=36237942524
PLANNER_RUN=36237942600
PLAN_COMMIT="349b0d543edefb2979f1712079628e25e37d8135"
KIO_VERSION="6.30.0-0supralinux8"
KXML_VERSION="6.30.0-0supralinux5"
KIO_MAT={"workflow_run":36222711238,"job_id":108350884409,"artifact_id":10898999142,"artifact_sha256":"c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d"}
KXML_MAT={"workflow_run":36002910277,"job_id":107643756357,"artifact_id":10808294092,"artifact_sha256":"bccf76b46d0c9619e4306f1fe704ff5b501b9554a63f7968093e3afd4beb0d86"}
BLOCKED={"baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"}
PASS={"kbookmarks","kconfigwidgets","kdav","kdesu","kiconthemes","kjobwidgets","kpeople","krunner","ksvg","ktextwidgets","kwallet","kxmlgui"}

policy=T.get("discovery_policy",{})
req(policy.get("phase")=="build-level1","Attempt8 canonical phase")
req(policy.get("package_builds")=="tier3-level1-authorized","Attempt8 canonical authorization")
req(policy.get("remediation")=="round18-kio-svg-test-provider-attempt8-active","Attempt8 remediation marker")

nodes={n["id"]:n for n in T.get("nodes",[])}
req({n for n,v in nodes.items() if v.get("state")=="PASS"}==PASS,"Attempt8 canonical PASS set unchanged")
req({n for n,v in nodes.items() if v.get("state")=="pending"}=={"knewstuff"},"Attempt8 canonical pending set")
req({n for n,v in nodes.items() if v.get("state")=="FAIL"}=={"kio"},"Attempt8 canonical KIO FAIL retained until result")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==BLOCKED,"Attempt8 canonical BLOCKED set")
req(nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux7" and nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"canonical KIO remains FAIL/-7")
req(nodes["kxmlgui"].get("packaging",{}).get("package_version")==KXML_VERSION and nodes["kxmlgui"].get("packaging",{}).get("downstream_eligible") is True,"canonical KXMLGui PASS retained")
req("kio" not in D.get("nodes",{}),"KIO absent from PASS DAG before Attempt8 result")

ar=T.get("active_remediation",{})
req(ar.get("round")==11 and ar.get("status")=="level1-active-pending-ci","canonical Attempt8 active")
req(ar.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"canonical Attempt8 versions")
req(ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True,"canonical Attempt8 authorization")
req(ar.get("current_attempt")==8 and ar.get("next_attempt")==8 and ar.get("next_gate")=="tier3-build-level1-attempt8","canonical Attempt8 markers")
req(ar.get("activation_policy_workflow_run")==POLICY_RUN and ar.get("activation_level1_workflow_run")==PLANNER_RUN and ar.get("activation_commit")==PLAN_COMMIT,"canonical planning evidence")

req(L.get("state")=="active-pending-ci" and L.get("execution_authorized") is True,"Level1 Attempt8 active")
req(L.get("selected_nodes")==["kio","kxmlgui"],"Level1 Attempt8 node set")
req(L.get("current_attempt")==8 and L.get("next_attempt")==8 and L.get("next_gate")=="tier3-build-level1-attempt8","Level1 Attempt8 markers")
act=L.get("activation",{})
req(act.get("status")=="ACTIVE" and act.get("attempt")==8 and act.get("scope")=="full-level1-rerun-2-nodes","Level1 Attempt8 activation")
req(act.get("remediation_validation_policy_workflow_run")==POLICY_RUN and act.get("remediation_validation_level1_workflow_run")==PLANNER_RUN and act.get("remediation_commit")==PLAN_COMMIT,"Level1 planning evidence")
lr=L.get("active_remediation",{})
req(lr.get("global_round")==11 and lr.get("status")=="materialization-PASS-attempt8-active","Level1 Round18/Attempt8 state")
req(lr.get("execution_authorized") is True and lr.get("source_rematerialization_required") is False and lr.get("full_level1_rerun_required") is True,"Level1 execution/source semantics")
req(lr.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"Level1 Attempt8 versions")

lk=L.get("nodes",{}).get("kio",{})
lx=L.get("nodes",{}).get("kxmlgui",{})
req(lk.get("state")=="prepared-pending-revalidation" and lk.get("package_version")==KIO_VERSION and lk.get("current_attempt")==8,"KIO runnable Attempt8")
req(lx.get("state")=="prepared-pending-revalidation" and lx.get("package_version")==KXML_VERSION and lx.get("current_attempt")==8,"KXMLGui runnable Attempt8")
for actual,expected,name in ((lk.get("materialization",{}),KIO_MAT,"KIO"),(lx.get("materialization",{}),KXML_MAT,"KXMLGui")):
    for key,val in expected.items(): req(actual.get(key)==val,f"{name} materialization {key}")
req(lk.get("last_attempt",{}).get("attempt")==7 and lk.get("last_attempt",{}).get("result")=="FAIL","KIO Attempt7 retained")
req(lx.get("last_attempt",{}).get("attempt")==7 and lx.get("last_attempt",{}).get("result")=="PASS","KXMLGui Attempt7 PASS retained")

cr=C.get("active_remediation",{})
req(cr.get("round")==11 and cr.get("status")=="materialization-PASS-attempt8-active","contracts Attempt8 active")
req(cr.get("execution_authorized") is True and cr.get("level1_execution_authorized") is True,"contracts execution authority")
req(cr.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"contracts Attempt8 versions")
req(cr.get("activation_policy_workflow_run")==POLICY_RUN and cr.get("activation_level1_workflow_run")==PLANNER_RUN and cr.get("activation_commit")==PLAN_COMMIT,"contracts planning evidence")
kc=C.get("nodes",{}).get("kio",{})
req(kc.get("package_version_candidate")==KIO_VERSION,"KIO contract -8")
rels=[(x.get("action"),x.get("package") or x.get("relation"),x.get("classification")) for x in kc.get("source_build_relation_overrides",[])]
req(("ensure","qt6-svg-plugins <!nocheck>","upstream-test-environment-provider") in rels,"KIO SVG provider contract retained")
req(kc.get("test_policy",{}).get("failures_fatal") is True,"KIO upstream failures remain fatal")

req(M.get("state")=="PASS" and "remediation_queue" not in M,"materialization remains PASS/no queue")
req(M.get("nodes",{}).get("kio",{}).get("package_version")==KIO_VERSION and M.get("nodes",{}).get("kio",{}).get("evidence",{}).get("artifact_id")==KIO_MAT["artifact_id"],"KIO -8 source PASS retained")
req(M.get("nodes",{}).get("kxmlgui",{}).get("package_version")==KXML_VERSION and M.get("nodes",{}).get("kxmlgui",{}).get("evidence",{}).get("artifact_id")==KXML_MAT["artifact_id"],"KXMLGui -5 source retained")
req(M.get("active_remediation",{}).get("next_gate")=="tier3-build-level1-attempt8","materialization Attempt8 handoff")

req(P.get("execution_authorized") is False,"generated campaign remains planning-only")
req(P.get("nodes",{}).get("kio",{}).get("package_version")==KIO_VERSION and P.get("nodes",{}).get("kio",{}).get("materialization",{}).get("artifact_id")==KIO_MAT["artifact_id"],"generated plan pins KIO -8")
req(P.get("nodes",{}).get("kxmlgui",{}).get("package_version")==KXML_VERSION and P.get("nodes",{}).get("kxmlgui",{}).get("materialization",{}).get("artifact_id")==KXML_MAT["artifact_id"],"generated plan pins KXMLGui -5")

req(not any(x.get("attempt")==8 for x in A.get("campaign_history",[])),"Attempt8 result must not exist before build")
req(R.get("status")=="attempt8-active" and R.get("execution_authorized") is True,"Round18 Attempt8 active record")
req(R.get("materialization",{}).get("source_materialization_authorized") is False and R.get("materialization",{}).get("binary_execution_authorized") is True,"Round18 binary-only authorization")
req(R.get("next_gate")=="tier3-build-level1-attempt8","Round18 Attempt8 gate")
ra=R.get("activation",{})
req(ra.get("nodes")==["kio","kxmlgui"] and ra.get("repository_policy_workflow_run")==POLICY_RUN and ra.get("level1_planning_workflow_run")==PLANNER_RUN and ra.get("commit")==PLAN_COMMIT,"Round18 activation evidence")

for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Round18 remediation")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable policy")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 1 Attempt 8 activation: PASS")
print("runnable_nodes=kio,kxmlgui")
print("KIO=6.30.0-0supralinux8; KXMLGui=6.30.0-0supralinux5")
print("canonical package state unchanged until real Attempt8 results")

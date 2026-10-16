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
R=load("manifests/kde-tier3-kio-attempt10-remediation.json")
D=load("manifests/kde-dag.json")
POLICY_RUN=36424710656; PLANNER_RUN=36424710626; PLAN_COMMIT="0471d2332eef5f02344b2ffad96828f31ee3a405"
KIO_VERSION="6.30.0-0supralinux10"; KXML_VERSION="6.30.0-0supralinux5"
KIO_MAT={"workflow_run":36424068585,"job_id":108933677695,"artifact_id":10970466420,"artifact_sha256":"f25ae14e1f393d24f95b1118680d7967f6bef449c8790981b170cfb78a1f3d22"}
BLOCKED={"baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"}
pol=T.get("discovery_policy",{})
req(pol.get("phase")=="build-level1" and pol.get("package_builds")=="tier3-level1-authorized" and pol.get("remediation")=="attempt10-kio-symbol-metadata-attempt10-active","Attempt10 canonical authorization")
nodes={n["id"]:n for n in T.get("nodes",[])}
req(nodes["kio"].get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux9" and nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"canonical KIO remains FAIL/-9")
req(nodes["kxmlgui"].get("state")=="PASS" and nodes["kxmlgui"].get("packaging",{}).get("package_version")==KXML_VERSION,"canonical KXMLGui PASS/-5")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==BLOCKED and "kio" not in D.get("nodes",{}),"canonical BLOCKED/DAG boundary")
ar=T.get("active_remediation",{})
req(ar.get("round")==11 and ar.get("status")=="level1-active-pending-ci","canonical Attempt10 active")
req(ar.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"canonical Attempt10 versions")
req(ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True and ar.get("current_attempt")==10 and ar.get("next_attempt")==10 and ar.get("next_gate")=="tier3-build-level1-attempt10","canonical Attempt10 authority")
req(ar.get("planning_validation")=={"repository_policy_workflow_run":POLICY_RUN,"level1_workflow_run":PLANNER_RUN,"commit":PLAN_COMMIT,"result":"PASS"},"canonical planning validation")
req(L.get("state")=="active-pending-ci" and L.get("execution_authorized") is True and L.get("current_attempt")==10 and L.get("next_attempt")==10 and L.get("next_gate")=="tier3-build-level1-attempt10","Level1 Attempt10 active")
act=L.get("activation",{})
req(act.get("status")=="ACTIVE" and act.get("attempt")==10 and act.get("scope")=="full-level1-rerun-2-nodes","Level1 Attempt10 activation")
req(act.get("remediation_validation_policy_workflow_run")==POLICY_RUN and act.get("remediation_validation_level1_workflow_run")==PLANNER_RUN and act.get("remediation_commit")==PLAN_COMMIT,"Level1 planning evidence")
lr=L.get("active_remediation",{})
req(lr.get("global_round")==11 and lr.get("status")=="materialization-PASS-attempt10-active" and lr.get("execution_authorized") is True and lr.get("level1_execution_authorized") is True,"Level1 remediation active")
lk=L.get("nodes",{}).get("kio",{}); lx=L.get("nodes",{}).get("kxmlgui",{})
req(lk.get("state")=="prepared-pending-revalidation" and lk.get("package_version")==KIO_VERSION and lk.get("current_attempt")==10,"KIO runnable Attempt10")
req(lx.get("state")=="prepared-pending-revalidation" and lx.get("package_version")==KXML_VERSION and lx.get("current_attempt")==10,"KXMLGui runnable Attempt10")
for key,val in KIO_MAT.items(): req(lk.get("materialization",{}).get(key)==val,"KIO materialization "+key)
req(lk.get("last_attempt",{}).get("attempt")==9 and lk.get("last_attempt",{}).get("result")=="FAIL","KIO Attempt9 FAIL retained")
req(lx.get("last_attempt",{}).get("attempt")==9 and lx.get("last_attempt",{}).get("result")=="PASS","KXMLGui Attempt9 PASS retained")
cr=C.get("active_remediation",{})
req(cr.get("round")==11 and cr.get("status")=="materialization-PASS-attempt10-active","contracts Attempt10 active")
req(cr.get("execution_authorized") is True and cr.get("level1_execution_authorized") is True and cr.get("candidate_package_versions")=={"kio":KIO_VERSION,"kxmlgui":KXML_VERSION},"contracts authority/versions")
adds=C.get("nodes",{}).get("kio",{}).get("symbol_template_additions",[])
req(len(adds)==34 and all(x.get("minimal_version")=="6.30.0" and x.get("tags")==["optional"] for x in adds),"KIO 34 optional symbols")
req(M.get("state")=="PASS" and "remediation_queue" not in M,"materialization remains PASS")
req(M.get("nodes",{}).get("kio",{}).get("package_version")==KIO_VERSION and M.get("nodes",{}).get("kio",{}).get("evidence",{}).get("artifact_id")==KIO_MAT["artifact_id"],"KIO -10 source PASS")
req(P.get("execution_authorized") is False,"generated campaign remains planning-only")
req(P.get("nodes",{}).get("kio",{}).get("package_version")==KIO_VERSION and P.get("nodes",{}).get("kio",{}).get("materialization",{}).get("artifact_id")==KIO_MAT["artifact_id"],"generated plan pins KIO -10")
req(P.get("nodes",{}).get("kxmlgui",{}).get("package_version")==KXML_VERSION,"generated plan pins KXMLGui -5")
req(not any(x.get("attempt")==10 for x in A.get("campaign_history",[])),"Attempt10 result must not exist before build")
req(R.get("status")=="attempt10-active" and R.get("execution_authorized") is True and R.get("package_execution_authorized") is True and R.get("level1_execution_authorized") is True,"Attempt10 active record")
req(R.get("gates",{}).get("current")=="tier3-build-level1-attempt10","Attempt10 current gate")
ra=R.get("activation",{})
req(ra.get("nodes")==["kio","kxmlgui"] and ra.get("repository_policy_workflow_run")==POLICY_RUN and ra.get("level1_planning_workflow_run")==PLANNER_RUN and ra.get("commit")==PLAN_COMMIT,"Attempt10 activation evidence")
for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Attempt10")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable policy")
if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 1 Attempt 10 activation: PASS")
print("runnable_nodes=kio,kxmlgui")
print("KIO="+KIO_VERSION+"; KXMLGui="+KXML_VERSION)
print("canonical package state unchanged until real Attempt10 results")

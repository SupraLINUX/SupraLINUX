#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

RUN=36079116873
COMMIT="ef6262ac9018df2c0d111d97f99919d8acdeb215"
ROOTFS={"artifact_id":10841431451,"artifact_sha256":"ac49ee835a7d45f00c4655c36d60e3725558d570b6af1f630849f84a2d8bb532"}
KIO={"job_id":107897110171,"artifact_id":10840963289,"artifact_sha256":"32b10c0ac337040239edea709440c5b09b898d76da1ac3c8e10339bf1477d239"}
KXML={"job_id":107897110192,"artifact_id":10841652858,"artifact_sha256":"4cc0f2a0eadbb54eefc3ae90359d842f16cb2cfd95ae2ca0adaec3c1385338fe"}
ATTEMPT7_NEXT="tier3-round12-kio-diagnostic-definition"
ROUND13_NEXT="tier3-round13-kio-build-tree-diagnostic-definition"
ROUND14_NEXT="tier3-round14-kio-kiconthemes-engine-provider-diagnostic-definition"
ROUND15_NEXT="tier3-round15-kio-breeze-icons-init-state-diagnostic-definition"
ROUND16_NEXT="tier3-round16-kio-kiconthemes-startup-kio-library-diagnostic-definition"
FAILS=["kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"]
BLOCKED=["baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"]
PASS={"kbookmarks","kconfigwidgets","kdav","kdesu","kiconthemes","kjobwidgets","kpeople","krunner","ksvg","ktextwidgets","kwallet","kxmlgui"}

T=load("manifests/kde-frameworks-tier3.json")
L=load("manifests/kde-tier3-build-level1.json")
A=load("manifests/kde-tier3-build-level1-attempts.json")
C=load("manifests/kde-tier3-package-contracts.json")
M=load("manifests/kde-tier3-materialization.json")
R=load("manifests/kde-tier3-kio-round11-remediation.json")
D12=load("manifests/kde-tier3-kio-round12-diagnostic.json")
D13=load("manifests/kde-tier3-kio-round13-diagnostic.json")
D14=load("manifests/kde-tier3-kio-round14-diagnostic.json")
D15=load("manifests/kde-tier3-kio-round15-diagnostic.json")
P=load("manifests/kde-tier3-build-campaign.json")
G=load("manifests/kde-dag.json")

policy=T.get("discovery_policy",{})
req(policy.get("package_builds")=="tier3-level1-attempt7-closed","Attempt7 closure package-build gate")
req(policy.get("remediation")=="round11-attempt7-closed-mixed","Attempt7 closure remediation marker")

nodes={n["id"]:n for n in T.get("nodes",[])}
req({n for n,v in nodes.items() if v.get("state")=="PASS"}==PASS,"canonical PASS set")
req({n for n,v in nodes.items() if v.get("state")=="pending"}=={"knewstuff"},"canonical pending set")
req({n for n,v in nodes.items() if v.get("state")=="FAIL"}=={"kio"},"canonical KIO FAIL set")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==set(BLOCKED),"canonical BLOCKED set")
req(nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux7","canonical KIO revision -7")
req(nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"KIO remains downstream-ineligible")
req(nodes["kxmlgui"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux5","KXMLGui canonical revision")
req(nodes["kxmlgui"].get("packaging",{}).get("downstream_eligible") is True,"KXMLGui remains downstream-eligible")
req("kio" not in G.get("nodes",{}),"KIO remains absent from PASS DAG")
req(G.get("nodes",{}).get("kxmlgui",{}).get("state")=="PASS","KXMLGui remains PASS in DAG")

round12_closed = D12.get("status")=="diagnostic-PASS"
round13_closed = D13.get("status")=="diagnostic-PASS"
round14_closed = D14.get("status")=="diagnostic-PASS"
round15_closed = D15.get("status")=="diagnostic-PASS"
CURRENT_NEXT = ROUND16_NEXT if round15_closed else (ROUND15_NEXT if round14_closed else (ROUND14_NEXT if round13_closed else (ROUND13_NEXT if round12_closed else ATTEMPT7_NEXT)))
if round12_closed:
    ev=D12.get("diagnostic_evidence",{})
    req(ev.get("workflow_run")==36082312546 and ev.get("job_id")==107906716315,"Round12 closure workflow evidence")
    req(ev.get("artifact_id")==10842450967 and ev.get("artifact_sha256")=="5b34f0a73e1e0f9b32e0c88d6c5bc90d3463d4b4854931eecda66244a9c52df6","Round12 closure artifact evidence")
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round12 closure remains non-promoting")
    dr=D12.get("diagnostic_results",{})
    req(dr.get("next_diagnostic_scope")=="kio-build-tree-process-specific-icon-resolution-diagnostic","Round12 handoff scope")
else:
    req(D12.get("status")=="definition-pending-diagnostic","Round12 lifecycle before closure")
if round13_closed:
    ev=D13.get("diagnostic_evidence",{})
    req(ev.get("workflow_run")==36146880757 and ev.get("job_id")==108110145068,"Round13 closure workflow evidence")
    req(ev.get("artifact_id")==10869413386 and ev.get("artifact_sha256")=="f96d4fdfebc5fcebe63633650ebf3998a51e37e5c84c12b50bc3d745097d7cd7","Round13 closure artifact evidence")
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round13 closure remains non-promoting")
    req(D13.get("diagnostic_results",{}).get("conclusion")=="build-tree-reproduces-no-simple-env-recovery-inspect-traces","Round13 closure conclusion")
elif round12_closed:
    req(D13.get("status")=="definition-pending-diagnostic","Round13 lifecycle before closure")
if round14_closed:
    ev=D14.get("diagnostic_evidence",{})
    req(ev.get("workflow_run")==36163272251 and ev.get("job_id")==108164792241,"Round14 closure workflow evidence")
    req(ev.get("artifact_id")==10876807762 and ev.get("artifact_sha256")=="2dda498091873a1c99a649ddb15c795130592c91100a3d97a78a608b8f531b87","Round14 closure artifact evidence")
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round14 closure remains non-promoting")
    req(D14.get("diagnostic_results",{}).get("conclusion")=="libkf6iconthemes-bin-does-not-recover-both-kio-tests","Round14 closure conclusion")
elif round13_closed:
    req(D14.get("status")=="definition-pending-diagnostic","Round14 lifecycle before closure")
if round15_closed:
    ev=D15.get("diagnostic_evidence",{})
    req(ev.get("workflow_run")==36208311383 and ev.get("job_id")==108309466429,"Round15 closure workflow evidence")
    req(ev.get("artifact_id")==10894857677 and ev.get("artifact_sha256")=="58413dce8261e276f08b450ac6fbab494a0d691018dd0472a997b570b5e2e136","Round15 closure artifact evidence")
    req(ev.get("result")=="DIAG_COMPLETE" and ev.get("package_attempted") is False and ev.get("package_state_effect")=="none","Round15 closure remains non-promoting")
    dr=D15.get("diagnostic_results",{})
    req(dr.get("baseline_valid") is True and dr.get("conclusion")=="breeze-init-state-does-not-reproduce-kio-icon-name-loss","Round15 closure conclusion")
    req(dr.get("next_diagnostic_scope")=="kiconthemes-startup-or-kio-library-interaction","Round15 handoff scope")
elif round14_closed:
    req(D15.get("status")=="definition-pending-diagnostic","Round15 lifecycle before closure")

ar=T.get("active_remediation",{})
req(ar.get("round")==11 and ar.get("status")=="attempt7-complete-mixed","Round11 canonical closure")
req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"binary execution closed")
req(ar.get("full_level1_rerun_required") is False and ar.get("next_gate")==CURRENT_NEXT,"current diagnostic next gate")
req(ar.get("current_attempt")==7 and ar.get("next_attempt")==8,"attempt counters")
req(ar.get("validation_workflow_run")==RUN and ar.get("validation_commit")==COMMIT,"Attempt7 workflow evidence")
req(ar.get("canonical_promotions")==0 and ar.get("remaining_failed_nodes")==["kio"],"Attempt7 canonical effect")
ae=ar.get("attempt7_evidence",{})
req(ae.get("rootfs")==ROOTFS and ae.get("kio")==KIO and ae.get("kxmlgui")==KXML,"Attempt7 exact artifact evidence")

req(L.get("state")=="attempt7-closed-mixed" and L.get("execution_authorized") is False,"Level1 closure state")
req(L.get("next_gate")==CURRENT_NEXT and L.get("current_attempt")==7 and L.get("next_attempt")==8,"Level1 closure counters/gate")
lk=L.get("nodes",{}).get("kio",{})
lx=L.get("nodes",{}).get("kxmlgui",{})
req(lk.get("state")=="FAIL" and lk.get("package_version")=="6.30.0-0supralinux7","Level1 KIO FAIL -7")
req(lk.get("last_attempt",{}).get("attempt")==7 and lk.get("last_attempt",{}).get("tests")=={"total":69,"pass":67,"fail":2},"KIO Attempt7 test totals")
req(lk.get("last_attempt",{}).get("failed_tests")==FAILS,"KIO Attempt7 failed tests")
req("kiocore-krecentdocumenttest" not in lk.get("last_attempt",{}).get("failed_tests",[]),"krecentdocumenttest recovered")
req(lx.get("state")=="PASS" and lx.get("package_version")=="6.30.0-0supralinux5","Level1 KXMLGui PASS")
req(lx.get("last_attempt",{}).get("tests")=={"total":7,"pass":7,"fail":0} and lx.get("last_attempt",{}).get("python_import")=="PASS","KXMLGui Attempt7 revalidation")

ak=[x for x in A.get("nodes",{}).get("kio",[]) if x.get("attempt")==7]
ax=[x for x in A.get("nodes",{}).get("kxmlgui",[]) if x.get("attempt")==7]
ah=[x for x in A.get("campaign_history",[]) if x.get("attempt")==7]
req(len(ak)==1 and ak[0].get("workflow_run")==RUN and ak[0].get("artifact_id")==KIO["artifact_id"] and ak[0].get("failed_tests")==FAILS,"ledger KIO Attempt7")
req(len(ax)==1 and ax[0].get("workflow_run")==RUN and ax[0].get("artifact_id")==KXML["artifact_id"] and ax[0].get("result")=="PASS","ledger KXMLGui Attempt7")
req(len(ah)==1 and ah[0].get("result")=="MIXED" and ah[0].get("workflow_jobs")=={"success":1,"fail":1} and ah[0].get("next_gate")==ATTEMPT7_NEXT,"campaign Attempt7 historical closure")

cr=C.get("active_remediation",{})
req(cr.get("round")==11 and cr.get("status")=="attempt7-complete-mixed","contracts Round11 closure")
req(cr.get("execution_authorized") is False and cr.get("level1_execution_authorized") is False and cr.get("next_gate")==CURRENT_NEXT,"contracts execution/gate")
req(cr.get("attempt7_evidence",{}).get("kio")==KIO and cr.get("attempt7_evidence",{}).get("kxmlgui")==KXML,"contracts Attempt7 evidence")

req(M.get("state")=="PASS" and "remediation_queue" not in M,"source materialization remains PASS and idle")
mr=M.get("active_remediation",{})
req(mr.get("next_gate")==CURRENT_NEXT and mr.get("attempt7_result",{}).get("result")=="MIXED","materialization current handoff")

req(R.get("status")=="attempt7-closed-mixed" and R.get("execution_authorized") is False,"Round11 record closed")
req(R.get("claim")=="attempt7-closure" and R.get("canonical_state_effect")=="KIO-FAIL-revalidated-KXMLGui-PASS","Round11 record semantics")
req(R.get("next_gate")==ATTEMPT7_NEXT and R.get("attempt7_result",{}).get("workflow_run")==RUN,"Round11 historical closure evidence")

req(P.get("execution_authorized") is False,"generated campaign remains non-executable")
for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Round11")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable approval policy")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 1 Attempt 7 canonical closure: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux7 67/69")
print("KXMLGui=PASS 6.30.0-0supralinux5 7/7 python-import=PASS")
print("attempt7_historical_next_gate="+ATTEMPT7_NEXT)
print("current_next_gate="+CURRENT_NEXT)

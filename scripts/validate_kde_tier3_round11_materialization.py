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
D=load("manifests/kde-dag.json")
Q=load("manifests/kde-tier3-kio-round11-diagnostic.json")
R=load("manifests/kde-tier3-kio-round11-remediation.json")
P=load("manifests/kde-tier3-build-campaign.json")

SNAPSHOT="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED"
BLOCKED=["baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"]
DIAG_RUN=36071103806
DIAG_JOB=107872008601
DIAG_ART=10837734340
DIAG_SHA="d4d944ac656d755ebd8c828d1e84c1b735e076c26a17adc66da42f0464a8cedc"
DEF_COMMIT="0dad8b3e82eb07bb02e90da4036001a82e885b0f"
DEF_POLICY_RUN=36072487004

policy=T.get("discovery_policy",{})
req(policy.get("phase")=="build-level1-planning","Round11 materialization phase")
req(policy.get("package_builds")=="tier3-level1-remediation-pending-materialization","Round11 materialization package gate")
req(policy.get("remediation")=="round11-kio-materialization-pending-ci","Round11 remediation marker")

nodes={n["id"]:n for n in T.get("nodes",[])}
PASS={"kbookmarks","kconfigwidgets","kdav","kdesu","kiconthemes","kjobwidgets","kpeople","krunner","ksvg","ktextwidgets","kwallet","kxmlgui"}
req({n for n,v in nodes.items() if v.get("state")=="PASS"}==PASS,"Round11 canonical PASS set")
req({n for n,v in nodes.items() if v.get("state")=="pending"}=={"knewstuff"},"Round11 canonical pending set")
req({n for n,v in nodes.items() if v.get("state")=="FAIL"}=={"kio"},"Round11 canonical FAIL set")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==set(BLOCKED),"Round11 canonical BLOCKED set")
req(nodes["kio"].get("packaging",{}).get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux6","KIO remains canonical FAIL/-6 before new package result")
req(nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"KIO remains non-eligible")
req(nodes["kxmlgui"].get("packaging",{}).get("state")=="PASS" and nodes["kxmlgui"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux5","KXMLGui retained PASS/-5")
req(nodes["kxmlgui"].get("packaging",{}).get("downstream_eligible") is True,"KXMLGui remains downstream eligible")
for node in BLOCKED:
    req(nodes[node].get("packaging",{}).get("state")=="BLOCKED" and nodes[node].get("packaging",{}).get("blocked_by")==["kio"],f"{node}: remains BLOCKED by KIO")
req("kio" not in D.get("nodes",{}),"KIO FAIL absent from canonical DAG")
req(D.get("nodes",{}).get("kxmlgui",{}).get("state")=="PASS","KXMLGui remains canonical DAG PASS")

snap=T.get("level1_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(12,1,1,6),"Round11 canonical snapshot counts")
req(L.get("canonical_snapshot")==SNAPSHOT,"Round11 Level1 snapshot")

def check_diag(ev,prefix):
    req(ev.get("workflow_run")==DIAG_RUN and ev.get("job_id")==DIAG_JOB,prefix+" diagnostic run/job")
    req(ev.get("artifact_id")==DIAG_ART and ev.get("artifact_sha256")==DIAG_SHA,prefix+" diagnostic artifact")

ar=T.get("active_remediation",{})
req(ar.get("round")==11 and ar.get("level")=="build-level1","canonical Round11 identity")
req(ar.get("nodes")==["kio","kxmlgui"],"canonical Level1 scope")
req(ar.get("source_materialization_nodes")==["kio"] and ar.get("retained_revalidation_nodes")==["kxmlgui"],"canonical source/revalidation classes")
req(ar.get("provider_closure_only_nodes")==[],"canonical no provider-closure-only nodes")
req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux7","kxmlgui":"6.30.0-0supralinux5"},"canonical Round11 versions")
req(ar.get("status")=="materialization-pending-ci" and ar.get("next_gate")=="tier3-round11-kio-materialization","canonical materialization lifecycle")
req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False and ar.get("full_level1_rerun_required") is True,"canonical execution pause/full rerun")
req(ar.get("current_attempt")==6 and ar.get("next_attempt")==7,"canonical Attempt7 handoff")
req(ar.get("remaining_failed_nodes")==["kio"] and ar.get("blocked_nodes")==BLOCKED and ar.get("canonical_promotions")==0,"canonical no premature promotion")
check_diag(ar.get("diagnostic_evidence",{}),"canonical")
dv=ar.get("definition_validation",{})
req(dv.get("commit")==DEF_COMMIT and dv.get("repository_policy_workflow_run")==DEF_POLICY_RUN and dv.get("result")=="PASS","canonical definition validation evidence")

req(L.get("state")=="remediation-pending-materialization" and L.get("execution_authorized") is False,"Level1 Round11 pending materialization")
req(L.get("current_attempt")==6 and L.get("next_attempt")==7 and L.get("next_gate")=="tier3-round11-kio-materialization","Level1 Attempt7 handoff")
lr=L.get("active_remediation",{})
req(lr.get("round")==6 and lr.get("global_round")==11,"Level1 local/global Round11 identity")
req(lr.get("nodes")==["kio","kxmlgui"] and lr.get("source_changed_nodes")==["kio"] and lr.get("retained_revalidation_nodes")==["kxmlgui"],"Level1 source/revalidation classes")
req(lr.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux7","kxmlgui":"6.30.0-0supralinux5"},"Level1 Round11 versions")
req(lr.get("source_rematerialization_required") is True and lr.get("source_rematerialization_nodes")==["kio"],"Level1 KIO-only rematerialization")
req(lr.get("package_revision_bump_required") is True and lr.get("full_level1_rerun_required") is True,"Level1 revision/full rerun")
req(lr.get("status")=="materialization-pending-ci" and lr.get("execution_authorized") is False,"Level1 materialization pause")
check_diag(lr.get("diagnostic_evidence",{}),"Level1")
req(L.get("nodes",{}).get("kio",{}).get("state")=="FAIL","Level1 KIO remains FAIL")
req(L.get("nodes",{}).get("kxmlgui",{}).get("state")=="PASS","Level1 KXMLGui remains PASS")
krem=L.get("nodes",{}).get("kio",{}).get("remediation",{})
req(krem.get("global_round")==11 and krem.get("candidate_package_version")=="6.30.0-0supralinux7","Level1 KIO Round11 remediation")
req(any("ENVIRONMENT_MODIFICATION" in x for x in krem.get("changes",[])),"Level1 KIO non-destructive environment remediation")
req(any("krecentdocumenttest unchanged and fatal" in x for x in krem.get("changes",[])),"KRecentDocument remains fatal")

cr=C.get("active_remediation",{})
req(cr.get("round")==11 and cr.get("status")=="materialization-pending-ci","contract Round11 materialization lifecycle")
req(cr.get("source_changed_nodes")==["kio"] and cr.get("retained_revalidation_nodes")==["kxmlgui"],"contract source/revalidation classes")
req(cr.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux7","kxmlgui":"6.30.0-0supralinux5"},"contract Round11 versions")
req(cr.get("execution_authorized") is False and cr.get("level1_execution_authorized") is False,"contract build execution pause")
req(cr.get("next_gate")=="tier3-round11-kio-materialization","contract next gate")
check_diag(cr.get("diagnostic_evidence",{}),"contract")
kc=C.get("nodes",{}).get("kio",{})
req(kc.get("package_version_candidate")=="6.30.0-0supralinux7","KIO contract candidate -7")
req(C.get("nodes",{}).get("kxmlgui",{}).get("package_version_candidate")=="6.30.0-0supralinux5","KXMLGui retained contract -5")
req(kc.get("test_policy",{}).get("upstream_tests_required") is True and kc.get("test_policy",{}).get("failures_fatal") is True,"KIO upstream tests remain fatal")
repls=kc.get("rules_text_replacements",[])
target=[x for x in repls if x.get("classification")=="upstream-test-environment-targeted-nondestructive-correction"]
req(len(target)==1,"KIO one Round11 targeted rules replacement")
if target:
    new=target[0].get("new","")
    req("ENVIRONMENT_MODIFICATION" in new,"KIO Round11 CMake mechanism")
    req("QT_QPA_PLATFORM=set:xcb" in new and "QT_QPA_SYSTEM_ICON_THEME=set:breeze" in new,"KIO Round11 exact QPA modifications")
    req("set_tests_properties(kiowidgets-kdirmodeltest PROPERTIES ENVIRONMENT" not in new,"KIO destructive ENVIRONMENT replacement removed")
env=kc.get("test_environment_contract",{}).get("ctest_per_test_qpa_overrides",{})
req(set(env)=={"kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"},"KIO targeted test set")
req(all(x.get("mechanism")=="ENVIRONMENT_MODIFICATION" and x.get("preserve_existing_environment") is True for x in env.values()),"KIO per-test environment preservation")

req(M.get("state")=="remediation-pending-ci","materialization Round11 executable lifecycle")
req(M.get("remediation_queue")==["kio"],"materialization queue KIO only")
mr=M.get("active_remediation",{})
req(mr.get("round")==11 and mr.get("status")=="materialization-pending-ci","materialization active Round11")
req(mr.get("source_changed_nodes")==["kio"] and mr.get("retained_revalidation_nodes")==["kxmlgui"],"materialization source/revalidation classes")
req(mr.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux7","kxmlgui":"6.30.0-0supralinux5"},"materialization versions")
req(mr.get("package_attempted") is False and mr.get("package_state_effect")=="none","materialization is source-only")
req(mr.get("next_gate")=="tier3-round11-kio-materialization","materialization next gate")
check_diag(mr.get("diagnostic_evidence",{}),"materialization")
mk=M.get("nodes",{}).get("kio",{})
req(mk.get("state")=="remediation-pending" and mk.get("candidate_package_version")=="6.30.0-0supralinux7","KIO materialization pending -7")
prev=mk.get("previous_evidence",{})
req(prev.get("result")=="PASS" and prev.get("package_version")=="6.30.0-0supralinux6","KIO retained -6 materialization baseline")
req(prev.get("workflow_run")==36002910277 and prev.get("artifact_id")==10809231495 and prev.get("artifact_sha256")=="5a0c2db21af5a87d4bd5ee2b02ebff7bce4dd98c66622398f00c67ef7210227b","KIO retained -6 source artifact")
mx=M.get("nodes",{}).get("kxmlgui",{})
req(mx.get("state")=="materialized" and mx.get("package_version")=="6.30.0-0supralinux5","KXMLGui source retained -5")

req(Q.get("status")=="diagnostic-PASS","Round11 diagnostic remains PASS")
req(Q.get("diagnostic_results",{}).get("cmake_environment_modification",{}).get("result")=="PASS","diagnostic CMake proof retained")
req(Q.get("diagnostic_results",{}).get("qt_breeze_icon_resolution",{}).get("result")=="PASS","diagnostic Qt/Breeze proof retained")
req(Q.get("diagnostic_results",{}).get("krecentdocument",{}).get("result")=="UNRESOLVED-HYPOTHESIS","KRecentDocument hypothesis retained")

req(R.get("status")=="definition-PASS-materialization-active","Round11 remediation definition validated/activated")
rv=R.get("definition_validation",{})
req(rv.get("commit")==DEF_COMMIT and rv.get("repository_policy_workflow_run")==DEF_POLICY_RUN and rv.get("result")=="PASS","Round11 remediation definition validation evidence")
req(R.get("source_materialization_authorized") is True and R.get("execution_authorized") is False,"Round11 source-only authorization")
req(R.get("next_gate")=="tier3-round11-kio-materialization","Round11 remediation handoff")

# Generated campaign intentionally remains on the last materialized KIO source (-6)
# until the new -7 source artifact is promoted.
req(P.get("nodes",{}).get("kio",{}).get("package_version")=="6.30.0-0supralinux6","campaign keeps materialized KIO -6 until source PASS")
req(P.get("nodes",{}).get("kxmlgui",{}).get("package_version")=="6.30.0-0supralinux5","campaign keeps KXMLGui -5")

for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Round11 definition")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable approval policy")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 KIO Round 11 materialization gate: PASS")
print(SNAPSHOT)
print("materialization_queue=kio; candidate=6.30.0-0supralinux7")
print("Level1 execution_authorized=false")

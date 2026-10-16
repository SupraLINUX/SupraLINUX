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
G=load("manifests/kde-dag.json")
Q=load("manifests/kde-tier3-kio-round11-diagnostic.json")
R=load("manifests/kde-tier3-kio-round11-remediation.json")

SNAPSHOT="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED"
BLOCKED=["baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"]
RUN=36073638711
JOB=107879979760
COMMIT="ebe60a0147e2a47b6c256ac015f43eea350c3ba2"
ART=10839162922
ART_SHA="ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c"
VERSION="6.30.0-0supralinux7"

policy=T.get("discovery_policy",{})
req(policy.get("phase")=="build-level1-planning","Round11 planning phase")
req(policy.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation","Round11 source PASS gate")
req(policy.get("remediation")=="round11-kio-source-PASS-pending-planning-validation","Round11 source PASS marker")

nodes={n["id"]:n for n in T.get("nodes",[])}
PASS={"kbookmarks","kconfigwidgets","kdav","kdesu","kiconthemes","kjobwidgets","kpeople","krunner","ksvg","ktextwidgets","kwallet","kxmlgui"}
req({n for n,v in nodes.items() if v.get("state")=="PASS"}==PASS,"canonical PASS set")
req({n for n,v in nodes.items() if v.get("state")=="pending"}=={"knewstuff"},"canonical pending set")
req({n for n,v in nodes.items() if v.get("state")=="FAIL"}=={"kio"},"canonical FAIL set")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==set(BLOCKED),"canonical BLOCKED set")
req(nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux6" and nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"canonical KIO stays FAIL/-6")
req(nodes["kxmlgui"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux5" and nodes["kxmlgui"].get("packaging",{}).get("downstream_eligible") is True,"canonical KXMLGui stays PASS/-5")
req("kio" not in G.get("nodes",{}),"KIO absent from canonical DAG")
req(G.get("nodes",{}).get("kxmlgui",{}).get("state")=="PASS","KXMLGui canonical DAG PASS")
for n in BLOCKED:
    req(nodes[n].get("packaging",{}).get("blocked_by")==["kio"],f"{n}: BLOCKED by KIO")

snap=T.get("level1_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(12,1,1,6),"canonical snapshot counts")
req(L.get("canonical_snapshot")==SNAPSHOT,"Level1 snapshot")

def check_art(ev,prefix):
    req(ev.get("workflow_run")==RUN and ev.get("job_id")==JOB and ev.get("commit")==COMMIT,prefix+" materialization run/job/commit")
    req(ev.get("artifact_id")==ART and ev.get("artifact_sha256")==ART_SHA,prefix+" materialization artifact")
    req(ev.get("package_version")==VERSION,prefix+" materialization version")

ar=T.get("active_remediation",{})
req(ar.get("round")==11 and ar.get("status")=="materialization-PASS-pending-level1-planning-validation","canonical Round11 source PASS")
req(ar.get("source_materialization_nodes")==["kio"] and ar.get("retained_revalidation_nodes")==["kxmlgui"],"canonical materialization/revalidation scope")
req(ar.get("candidate_package_versions")=={"kio":VERSION,"kxmlgui":"6.30.0-0supralinux5"},"canonical candidate versions")
req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"canonical build pause")
req(ar.get("current_attempt")==6 and ar.get("next_attempt")==7 and ar.get("next_gate")=="tier3-build-level1-planning-validation","canonical Attempt7 planning handoff")
ma=ar.get("materialization_artifacts",{}).get("kio",{})
req(ma.get("job_id")==JOB and ma.get("artifact_id")==ART and ma.get("artifact_sha256")==ART_SHA and ma.get("package_version")==VERSION,"canonical KIO source evidence")
pme=nodes["kio"].get("planning",{}).get("materialization_evidence",{})
req(pme.get("workflow_run")==RUN and pme.get("job_id")==JOB and pme.get("artifact_id")==ART and pme.get("artifact_sha256")==ART_SHA and pme.get("package_version")==VERSION,"canonical KIO planning source linkage")

req(L.get("state")=="remediation-materialized-pending-planning-validation" and L.get("execution_authorized") is False,"Level1 post-materialization pause")
req(L.get("current_attempt")==6 and L.get("next_attempt")==7 and L.get("next_gate")=="tier3-build-level1-planning-validation","Level1 Attempt7 planning gate")
lr=L.get("active_remediation",{})
req(lr.get("global_round")==11 and lr.get("status")=="materialization-PASS-pending-attempt7-planning-validation","Level1 Round11 source PASS")
req(lr.get("source_changed_nodes")==["kio"] and lr.get("retained_revalidation_nodes")==["kxmlgui"],"Level1 source/revalidation classes")
req(lr.get("source_rematerialization_required") is False and lr.get("full_level1_rerun_required") is True,"Level1 rematerialization complete/full rerun retained")
req(lr.get("execution_authorized") is False,"Level1 build remains unauthorized")
req(lr.get("materialization_workflow_run")==RUN and lr.get("materialization_commit")==COMMIT,"Level1 materialization evidence")
la=lr.get("materialization_artifacts",{})
req(la.get("kio",{}).get("artifact_id")==ART and la.get("kio",{}).get("package_version")==VERSION,"Level1 KIO artifact")
req(la.get("kxmlgui",{}).get("artifact_id")==10808294092 and la.get("kxmlgui",{}).get("package_version")=="6.30.0-0supralinux5","Level1 retained KXMLGui artifact")

cr=C.get("active_remediation",{})
req(cr.get("round")==11 and cr.get("status")=="materialization-PASS-pending-level1-planning-validation","contracts Round11 source PASS")
req(cr.get("candidate_package_versions")=={"kio":VERSION,"kxmlgui":"6.30.0-0supralinux5"},"contract candidate versions")
req(cr.get("execution_authorized") is False and cr.get("level1_execution_authorized") is False,"contracts build pause")
req(cr.get("next_gate")=="tier3-build-level1-planning-validation","contracts planning gate")
kc=C.get("nodes",{}).get("kio",{})
req(kc.get("package_version_candidate")==VERSION,"KIO contract candidate -7")
target=[x for x in kc.get("rules_text_replacements",[]) if x.get("classification")=="upstream-test-environment-targeted-nondestructive-correction"]
req(len(target)==1 and "ENVIRONMENT_MODIFICATION" in target[0].get("new",""),"KIO non-destructive CTest adaptation")
req(kc.get("test_policy",{}).get("upstream_tests_required") is True and kc.get("test_policy",{}).get("failures_fatal") is True,"KIO tests remain fatal")

req(M.get("state")=="PASS" and "remediation_queue" not in M,"materialization source PASS/no executable queue")
mr=M.get("active_remediation",{})
req(mr.get("round")==11 and mr.get("status")=="materialization-PASS-pending-level1-planning-validation","materialization Round11 PASS lifecycle")
req(mr.get("next_gate")=="tier3-build-level1-planning-validation","materialization planning gate")
mk=M.get("nodes",{}).get("kio",{})
req(mk.get("state")=="materialized" and mk.get("package_version")==VERSION,"KIO materialized -7")
check_art(mk.get("evidence",{}),"KIO")
req(mk.get("evidence",{}).get("dsc_sha256")=="fbba71c0d66cb4e0e09a9f6e2625dd416d642c075a7b8f9ae8bfcd51eee413ec","KIO dsc digest")
req(mk.get("evidence",{}).get("debian_tar_sha256")=="bccd518fc0be0e9f09bf06e9b346ad21d24143191eef73585cf4347a6fa41118","KIO debian tar digest")
req(mk.get("evidence",{}).get("source_tree_sha256")=="8db83e361fa632ecb36fb171ae78ec021cc6f9e1d0b67fc0476f045e3afce923","KIO source tree digest")
req(mk.get("evidence",{}).get("materialized_tree_sha256")=="9138398b41e18849de47ac93a0f5f4a68b449607a3b8b02fd16607cf99b2e18d","KIO materialized tree digest")
req(mk.get("evidence",{}).get("adapted_rules_sha256")=="c966d9328a0ab624ac5c7b5fb4d1b328d4812ac477446e0b0adf05671c410bfd","KIO adapted rules digest")
req(any(x.get("package_version")=="6.30.0-0supralinux6" and x.get("artifact_id")==10809231495 for x in mk.get("evidence_history",[])),"KIO -6 source evidence retained in history")
mx=M.get("nodes",{}).get("kxmlgui",{})
req(mx.get("state")=="materialized" and mx.get("package_version")=="6.30.0-0supralinux5" and mx.get("evidence",{}).get("artifact_id")==10808294092,"KXMLGui source retained -5")

pk=P.get("nodes",{}).get("kio",{})
req(P.get("state")=="planned" and P.get("execution_authorized") is False,"campaign remains non-executable")
req(pk.get("package_version")==VERSION,"campaign KIO version -7")
req(pk.get("materialization")=={"workflow_run":RUN,"job_id":JOB,"artifact_id":ART,"artifact_sha256":ART_SHA},"campaign KIO source artifact")
px=P.get("nodes",{}).get("kxmlgui",{})
req(px.get("package_version")=="6.30.0-0supralinux5" and px.get("materialization",{}).get("artifact_id")==10808294092,"campaign retained KXMLGui -5")

req(Q.get("status")=="diagnostic-PASS","Round11 diagnostic remains PASS")
req(Q.get("diagnostic_results",{}).get("krecentdocument",{}).get("rerun_policy")=="remain-fatal-in-next-full-Level1-attempt","KRecentDocument remains fatal")
req(R.get("status")=="source-materialization-PASS-pending-planning-validation","Round11 remediation post-materialization state")
req(R.get("source_materialization_authorized") is False and R.get("execution_authorized") is False,"Round11 no further source/build authorization")
req(R.get("next_gate")=="tier3-build-level1-planning-validation","Round11 remediation planning gate")
check_art(R.get("materialization_evidence",{}),"Round11 remediation")

for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Round11 remediation")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable approval policy")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 KIO Round 11 post-materialization planning gate: PASS")
print(SNAPSHOT)
print("KIO source=6.30.0-0supralinux7; KXMLGui retained=6.30.0-0supralinux5")
print("execution_authorized=false; next_gate=tier3-build-level1-planning-validation")

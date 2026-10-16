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
R=load("manifests/kde-tier3-kio-round18-remediation.json")
D=load("manifests/kde-dag.json")

SNAPSHOT="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED"
BLOCKED={"baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"}
VERSION="6.30.0-0supralinux8"
RETAINED="6.30.0-0supralinux5"
RUN=36222711238
JOB=108350884409
COMMIT="29b730acf3ad09c0c399b839e57b03a26df2ea2e"
ART=10898999142
ART_SHA="c31aafa0d5718a0e8287212b49f35022a58a5519a87a04991424939284d9003d"
GATE="tier3-build-level1-planning-validation"
MARKER="round18-kio-svg-test-provider-source-PASS-pending-planning-validation"

def check_art(ev,prefix):
    req(ev.get("workflow_run")==RUN and ev.get("job_id")==JOB,prefix+" run/job")
    req(ev.get("artifact_id")==ART and ev.get("artifact_sha256")==ART_SHA,prefix+" artifact")
    req(ev.get("package_version")==VERSION,prefix+" version")

pol=T.get("discovery_policy",{})
req(pol.get("phase")=="build-level1-planning","Round18 planning phase")
req(pol.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation","Round18 source PASS gate")
req(pol.get("remediation")==MARKER,"Round18 source PASS marker")

nodes={n["id"]:n for n in T.get("nodes",[])}
req(nodes["kio"].get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux7","canonical KIO remains FAIL/-7")
req(nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"canonical KIO remains ineligible")
req(nodes["kxmlgui"].get("state")=="PASS" and nodes["kxmlgui"].get("packaging",{}).get("package_version")==RETAINED,"KXMLGui retained PASS/-5")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==BLOCKED,"canonical BLOCKED set")
req("kio" not in D.get("nodes",{}),"KIO FAIL absent from PASS DAG")
snap=T.get("level1_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(12,1,1,6),"canonical snapshot")

ar=T.get("active_remediation",{})
req(ar.get("round")==11 and ar.get("status")=="materialization-PASS-pending-level1-planning-validation","canonical source PASS lifecycle")
req(ar.get("candidate_package_versions")=={"kio":VERSION,"kxmlgui":RETAINED},"canonical candidates")
req(ar.get("source_materialization_nodes")==["kio"] and ar.get("retained_revalidation_nodes")==["kxmlgui"],"canonical source/revalidation scope")
req(ar.get("source_materialization_complete") is True,"canonical materialization complete")
req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"canonical execution paused")
req(ar.get("current_attempt")==7 and ar.get("next_attempt")==8 and ar.get("next_gate")==GATE,"Attempt8 planning handoff")
ma=ar.get("materialization_artifacts",{}).get("kio",{})
req(ma=={"job_id":JOB,"artifact_id":ART,"artifact_sha256":ART_SHA,"package_version":VERSION},"canonical KIO source artifact")
check_art(nodes["kio"].get("planning",{}).get("materialization_evidence",{}),"canonical planning source")

req(L.get("state")=="remediation-materialized-pending-planning-validation" and L.get("execution_authorized") is False,"Level1 planning pause")
req(L.get("current_attempt")==7 and L.get("next_attempt")==8 and L.get("next_gate")==GATE,"Level1 Attempt8 handoff")
lr=L.get("active_remediation",{})
req(lr.get("global_round")==11 and lr.get("status")=="materialization-PASS-pending-attempt8-planning-validation","Level1 source PASS")
req(lr.get("source_rematerialization_required") is False and lr.get("full_level1_rerun_required") is True,"Level1 source complete/full rerun retained")
req(lr.get("execution_authorized") is False and lr.get("materialization_workflow_run")==RUN and lr.get("materialization_commit")==COMMIT,"Level1 evidence/pause")
req(L.get("nodes",{}).get("kio",{}).get("materialization")=={"workflow_run":RUN,"job_id":JOB,"artifact_id":ART,"artifact_sha256":ART_SHA},"Level1 KIO materialization")
req(L.get("nodes",{}).get("kio",{}).get("state")=="FAIL","Level1 KIO canonical FAIL")
req(L.get("nodes",{}).get("kxmlgui",{}).get("state")=="PASS","Level1 KXMLGui canonical PASS")

cr=C.get("active_remediation",{})
req(cr.get("round")==11 and cr.get("status")=="materialization-PASS-pending-level1-planning-validation","contracts source PASS")
req(cr.get("candidate_package_versions")=={"kio":VERSION,"kxmlgui":RETAINED},"contracts candidates")
req(cr.get("execution_authorized") is False and cr.get("level1_execution_authorized") is False and cr.get("next_gate")==GATE,"contracts planning pause")
kc=C.get("nodes",{}).get("kio",{})
req(kc.get("package_version_candidate")==VERSION,"KIO contract candidate -8")
rels=[(x.get("action"),x.get("package") or x.get("relation"),x.get("classification")) for x in kc.get("source_build_relation_overrides",[])]
req(("ensure","qt6-svg-plugins <!nocheck>","upstream-test-environment-provider") in rels,"KIO SVG test provider relation")
req(kc.get("test_policy",{}).get("upstream_tests_required") is True and kc.get("test_policy",{}).get("failures_fatal") is True,"KIO tests complete/fatal")

req(M.get("state")=="PASS" and "remediation_queue" not in M,"materialization PASS/no queue")
mr=M.get("active_remediation",{})
req(mr.get("round")==11 and mr.get("status")=="materialization-PASS-pending-level1-planning-validation" and mr.get("next_gate")==GATE,"materialization lifecycle")
mk=M.get("nodes",{}).get("kio",{})
req(mk.get("state")=="materialized" and mk.get("package_version")==VERSION,"KIO source materialized -8")
check_art(mk.get("evidence",{}),"KIO")
req(mk.get("evidence",{}).get("dsc_sha256")=="42bab29acda178a63c7ff84fade5cc1b9908be599e2bfbf676e4b101800aa826","KIO dsc")
req(mk.get("evidence",{}).get("debian_tar_sha256")=="ae5401aa60b6046585a5b10d75a8d19c6659c8739ed72917c2214ea00d6bda1b","KIO debian tar")
req(mk.get("evidence",{}).get("source_tree_sha256")=="f845907543c10b8278850aba3e0760a096ff5471a5b309b9cc238cc7a49e7d0a","KIO source tree")
req(mk.get("evidence",{}).get("materialized_tree_sha256")=="240ba85604578e0b4615c5f09049b67dbf5b41f6e2779db75fc8b662871f704b","KIO materialized tree")
req(mk.get("evidence",{}).get("adapted_control_sha256")=="b5f687a50fd97d7ca90871a49610dc35be3ca92c51bfd20d38c9f48af45585a5","KIO adapted control")
req(mk.get("evidence",{}).get("adapted_rules_sha256")=="c966d9328a0ab624ac5c7b5fb4d1b328d4812ac477446e0b0adf05671c410bfd","KIO adapted rules")
req(any(x.get("package_version")=="6.30.0-0supralinux7" and x.get("artifact_id")==10839162922 for x in mk.get("evidence_history",[])),"KIO -7 source retained historically")

pk=P.get("nodes",{}).get("kio",{})
req(P.get("state")=="planned" and P.get("execution_authorized") is False,"campaign remains non-executable")
req(pk.get("package_version")==VERSION,"campaign KIO -8")
req(pk.get("materialization")=={"workflow_run":RUN,"job_id":JOB,"artifact_id":ART,"artifact_sha256":ART_SHA},"campaign exact KIO source")
px=P.get("nodes",{}).get("kxmlgui",{})
req(px.get("package_version")==RETAINED and px.get("materialization",{}).get("artifact_id")==10808294092,"campaign retained KXMLGui -5")

req(R.get("status")=="source-materialization-PASS-pending-planning-validation","Round18 remediation source PASS")
req(R.get("next_gate")==GATE,"Round18 remediation planning gate")
req(R.get("materialization",{}).get("source_materialization_authorized") is False and R.get("materialization",{}).get("binary_execution_authorized") is False,"Round18 no source/binary authorization")
check_art(R.get("materialization_evidence",{}),"Round18 remediation")

for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(R,"Round18 remediation")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable policy")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 KIO Round 18 post-materialization planning gate: PASS")
print(SNAPSHOT)
print("KIO source=6.30.0-0supralinux8; canonical KIO=FAIL 6.30.0-0supralinux7")
print("execution_authorized=false; next_gate="+GATE)

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
P=load("manifests/kde-tier3-build-campaign.json"); A=load("manifests/kde-tier3-kio-attempt10-remediation.json"); D=load("manifests/kde-dag.json")
SNAPSHOT="12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED"
BLOCKED={"baloo","kcmutils","knotifyconfig","kparts","ktexteditor","purpose"}
VERSION="6.30.0-0supralinux10"; RETAINED="6.30.0-0supralinux5"; RUN=36424068585; JOB=108933677695; COMMIT="a77f6e1f247792ccb486720010d969e2cbc41680"; ART=10970466420; ART_SHA="f25ae14e1f393d24f95b1118680d7967f6bef449c8790981b170cfb78a1f3d22"
GATE="tier3-attempt10-kio-planning-validation"; MARKER="attempt10-kio-symbol-metadata-source-PASS-pending-planning-validation"
def check(e,p):
    req(e.get("workflow_run")==RUN and e.get("job_id")==JOB,p+" run/job")
    req(e.get("artifact_id")==ART and e.get("artifact_sha256")==ART_SHA,p+" artifact")
    req(e.get("package_version")==VERSION,p+" version")
pol=T.get("discovery_policy",{})
req(pol.get("phase")=="build-level1-planning" and pol.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation" and pol.get("remediation")==MARKER,"Attempt10 planning policy")
nodes={n["id"]:n for n in T.get("nodes",[])}
req(nodes["kio"].get("state")=="FAIL" and nodes["kio"].get("packaging",{}).get("package_version")=="6.30.0-0supralinux9" and nodes["kio"].get("packaging",{}).get("downstream_eligible") is False,"canonical KIO FAIL/-9")
req(nodes["kxmlgui"].get("state")=="PASS" and nodes["kxmlgui"].get("packaging",{}).get("package_version")==RETAINED,"canonical KXMLGui PASS/-5")
req({n for n,v in nodes.items() if v.get("state")=="BLOCKED"}==BLOCKED and "kio" not in D.get("nodes",{}),"canonical blocked/DAG boundary")
snap=T.get("level1_snapshot",{}); req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(12,1,1,6),"canonical snapshot")
ar=T.get("active_remediation",{})
req(ar.get("round")==11 and ar.get("status")=="materialization-PASS-pending-level1-planning-validation" and ar.get("next_gate")==GATE,"canonical source PASS lifecycle")
req(ar.get("candidate_package_versions")=={"kio":VERSION,"kxmlgui":RETAINED} and ar.get("source_materialization_complete") is True,"canonical source complete")
req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False and ar.get("current_attempt")==9 and ar.get("next_attempt")==10,"canonical Attempt10 paused")
req(ar.get("materialization_workflow_run")==RUN and ar.get("materialization_commit")==COMMIT and ar.get("materialization_artifacts",{}).get("kio")=={"job_id":JOB,"artifact_id":ART,"artifact_sha256":ART_SHA,"package_version":VERSION},"canonical materialization evidence")
check(nodes["kio"].get("planning",{}).get("materialization_evidence",{}),"canonical planning")
lr=L.get("active_remediation",{})
req(lr.get("global_round")==11 and lr.get("status")=="materialization-PASS-pending-attempt10-planning-validation" and lr.get("source_rematerialization_required") is False,"Level1 source PASS")
req(L.get("execution_authorized") is False and lr.get("execution_authorized") is False and lr.get("level1_execution_authorized") is False and lr.get("current_attempt")==9 and lr.get("next_attempt")==10 and lr.get("next_gate")==GATE,"Level1 Attempt10 paused")
req(lr.get("materialization_workflow_run")==RUN and lr.get("materialization_commit")==COMMIT and lr.get("materialization_artifacts",{}).get("kio")=={"job_id":JOB,"artifact_id":ART,"artifact_sha256":ART_SHA,"package_version":VERSION},"Level1 source evidence")
req(L.get("nodes",{}).get("kio",{}).get("materialization")=={"workflow_run":RUN,"job_id":JOB,"artifact_id":ART,"artifact_sha256":ART_SHA},"Level1 KIO materialization")
cr=C.get("active_remediation",{})
req(cr.get("round")==11 and cr.get("status")=="materialization-PASS-pending-level1-planning-validation" and cr.get("next_gate")==GATE,"contracts source PASS")
req(cr.get("execution_authorized") is False and cr.get("level1_execution_authorized") is False and cr.get("candidate_package_versions")=={"kio":VERSION,"kxmlgui":RETAINED},"contracts paused")
req(cr.get("materialization_evidence",{}).get("workflow_run")==RUN and cr.get("materialization_evidence",{}).get("commit")==COMMIT and cr.get("materialization_evidence",{}).get("artifacts",{}).get("kio")=={"job_id":JOB,"artifact_id":ART,"artifact_sha256":ART_SHA,"package_version":VERSION},"contracts source evidence")
req(C.get("nodes",{}).get("kio",{}).get("package_version_candidate")==VERSION,"KIO contract -10")
adds=C.get("nodes",{}).get("kio",{}).get("symbol_template_additions",[])
req(len(adds)==34 and all(x.get("minimal_version")=="6.30.0" and x.get("tags")==["optional"] for x in adds),"KIO 34 optional symbols @ 6.30.0")
req(M.get("state")=="PASS" and "remediation_queue" not in M,"materialization PASS/no queue")
mr=M.get("active_remediation",{}); req(mr.get("status")=="materialization-PASS-pending-level1-planning-validation" and mr.get("next_gate")==GATE,"materialization lifecycle")
mk=M.get("nodes",{}).get("kio",{}); req(mk.get("state")=="materialized" and mk.get("package_version")==VERSION,"KIO source materialized -10"); check(mk.get("evidence",{}),"KIO")
e=mk.get("evidence",{})
req(e.get("dsc_sha256")=="4f27b6ab8797bf44c3104e57cf33a69f921ba7ac83e90b5ea82082cdd1342eb3" and e.get("debian_tar_sha256")=="801680a76fa4013f07ae2891a0f4ab3c98f31b974bc94385912333b625719fd5","KIO source package hashes")
req(e.get("source_tree_sha256")=="05a15e08edad1e95358383e97ae326d41c308b64a116cb0dcaf37a11f4677d0e" and e.get("materialized_tree_sha256")=="06bbd34131df5bc52793703782b7db2b5f6a3a9c8541d82c4ee8daeba947c8a8","KIO tree hashes")
req(e.get("adapted_control_sha256")=="b5f687a50fd97d7ca90871a49610dc35be3ca92c51bfd20d38c9f48af45585a5" and e.get("adapted_rules_sha256")=="bda27ef4c2d07b790e6eb0473a32abe6c58371e29f909ab7f52ee45e69ed0a3f","KIO packaging hashes")
sp=e.get("supralinux_source_patches",[]); req(len(sp)==1 and sp[0].get("patch_sha256")=="8718c28a240e5cd5700fff23afe9c122d3f632b80e6db5cde83bcee7e631c602" and sp[0].get("patched_source_sha256")=="57d20f3786220178316b31819ba266432207b1f4d55859ccf8d1fad37645021b","KIO functional source unchanged")
req(any(x.get("package_version")=="6.30.0-0supralinux9" and x.get("artifact_id")==10965892140 for x in mk.get("evidence_history",[])),"KIO -9 source retained historically")
pk=P.get("nodes",{}).get("kio",{}); req(P.get("state")=="planned" and P.get("execution_authorized") is False and pk.get("package_version")==VERSION,"campaign KIO -10/non-executable")
req(pk.get("materialization")=={"workflow_run":RUN,"job_id":JOB,"artifact_id":ART,"artifact_sha256":ART_SHA},"campaign KIO source")
req(A.get("status")=="source-materialization-PASS-pending-planning-validation" and A.get("source_materialization_complete") is True and A.get("materialization_authorized") is False,"Attempt10 source closed")
req(A.get("package_execution_authorized") is False and A.get("level1_execution_authorized") is False and A.get("gates",{}).get("current")==GATE,"Attempt10 binary blocked/current gate")
check(A.get("materialization_evidence",{}),"Attempt10")
req(A.get("definition_contract",{}).get("status")=="PASS" and A.get("definition_contract",{}).get("repository_policy_workflow_run")==36424068693,"Attempt10 definition retained")
for obj,name in ((L,"Level1"),(C,"contracts"),(M,"materialization"),(A,"Attempt10")):
    req(obj.get("stable_promotion_requires_explicit_user_approval") is True,name+" stable policy")
if errors:
    for x in errors: print("ERROR:",x,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 KIO Attempt 10 post-materialization planning gate: PASS")
print(SNAPSHOT)
print("KIO source="+VERSION+"; canonical KIO=FAIL 6.30.0-0supralinux9")
print("Attempt10=NOT-AUTHORIZED; next_gate="+GATE)

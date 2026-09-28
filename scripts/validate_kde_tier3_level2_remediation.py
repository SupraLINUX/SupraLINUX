#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]; errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

rc=subprocess.run([sys.executable,str(ROOT/"scripts/validate_kde_tier3_level2_attempt4_closure.py")]).returncode
if rc:
    raise SystemExit(rc)

t=load("manifests/kde-frameworks-tier3.json")
c=load("manifests/kde-tier3-package-contracts.json")
m=load("manifests/kde-tier3-materialization.json")
l=load("manifests/kde-tier3-build-level2.json")
a=load("manifests/kde-tier3-build-level2-attempts.json")
hist=a.get("campaign_history",[])
req(bool(hist),"Level2 attempt history")
latest=hist[-1] if hist else {}
cur=latest.get("attempt")
nxt=(cur+1) if isinstance(cur,int) else None
trigger={"attempt":cur,"workflow_run":latest.get("workflow_run"),"commit":latest.get("commit"),"result":latest.get("result")}
SNAP="16 PASS / 1 pending / 1 current FAIL / 2 BLOCKED"
PENDING_GATE="tier3-level2-remediation-materialization-evidence"
READY_GATE="tier3-build-level2-attempt5-planning-validation"
READY_STATUS="materialization-PASS-pending-attempt5-activation-validation"
PACKAGE_GATE="tier3-level2-remediation-materialized-pending-attempt5-planning-validation"
MAT_RUN=36477724469
MAT_JOB=109115619026
MAT_COMMIT="2ff091a675dc7660ebeff0ebb7c7828b9e6fb0bd"
MAT_ART=10994755385
MAT_SHA="69b0be3b9f9db37f7cac1fe1acf2a0b11faa64a796add88c23766d9127f7ea3a"
MAT_VERSION="6.30.0-0supralinux3"

req(latest.get("result")=="MIXED" and latest.get("package_attempted") is True,"latest valid package attempt closure")
r=t.get("level2_remediation",{})
ready=r.get("status")==READY_STATUS
pending=r.get("status")=="materialization-pending-ci"
req(ready or pending,"Level2 remediation status")
req(r.get("trigger")==trigger,"Level2 remediation trigger follows latest closed attempt")
req(r.get("source_materialization_nodes")==["kcmutils"],"Level2 source remediation scope")
req(r.get("retained_source_nodes")==["baloo","knotifyconfig","kparts"],"Level2 retained PASS scope")
req(r.get("candidate_package_versions")=={"kcmutils":MAT_VERSION},"Level2 candidate revision")
req(r.get("execution_authorized") is False,"Level2 remediation execution pause")
req(r.get("next_gate")==(READY_GATE if ready else PENDING_GATE),"Level2 remediation next gate")
pol=t.get("discovery_policy",{})
req(pol.get("phase")=="build-level2-remediation-planning","Level2 remediation phase")
req(pol.get("package_builds")==(PACKAGE_GATE if ready else "tier3-level2-remediation-pending-materialization"),"Level2 remediation package gate")

lx=t.get("level2_execution",{})
req(lx.get("execution_authorized") is False and lx.get("current_attempt")==cur and lx.get("next_attempt")==nxt,"Level2 current/next package attempt")
req(lx.get("canonical_snapshot")==SNAP and lx.get("next_gate")==(READY_GATE if ready else PENDING_GATE),"Level2 canonical remediation handoff")
nodes={x["id"]:x for x in t.get("nodes",[])}
for x in ("baloo","knotifyconfig","kparts"):
    req(nodes[x].get("state")=="PASS" and nodes[x].get("packaging",{}).get("state")=="PASS" and nodes[x].get("packaging",{}).get("downstream_eligible") is True,x+": Attempt closure PASS")
req(nodes["kcmutils"].get("state")=="FAIL" and nodes["kcmutils"].get("packaging",{}).get("state")=="FAIL","KCMUtils current FAIL")
req(nodes["ktexteditor"].get("state")=="pending" and nodes["ktexteditor"].get("packaging",{}).get("state")=="pending","KTextEditor unblocked to pending")
for x in ("knewstuff","purpose"):
    req(nodes[x].get("state")=="BLOCKED" and nodes[x].get("packaging",{}).get("blocked_by")==["kcmutils"],x+": remains KCMUtils-blocked")
snap=t.get("level2_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(16,1,1,2),"canonical snapshot counts")

req(l.get("state")==("remediation-materialized-pending-activation" if ready else "remediation-pending-materialization") and l.get("execution_authorized") is False,"Level2 binary execution paused")
req(l.get("current_attempt")==cur and l.get("next_attempt")==nxt and l.get("next_gate")==(READY_GATE if ready else PENDING_GATE),"Level2 package-attempt markers")
req(l.get("canonical_snapshot")==SNAP,"Level2 manifest canonical snapshot")
for x in ("baloo","knotifyconfig","kparts"):
    req(l["nodes"][x].get("state")=="PASS" and l["nodes"][x].get("pass_evidence",{}).get("result")=="PASS",x+": Level2 PASS evidence")
req(l["nodes"]["kcmutils"].get("candidate_package_version",MAT_VERSION)==MAT_VERSION,"KCMUtils Level2 candidate revision")

cr=c.get("level2_remediation",{})
req(cr.get("trigger")==trigger and cr.get("package_build_authorized") is False,"contract package build remains unauthorized")
req(cr.get("candidate_package_versions")=={"kcmutils":MAT_VERSION},"contract remediation revision")
req(c["nodes"]["kcmutils"].get("package_version_candidate")==MAT_VERSION,"KCMUtils contract candidate")

if ready:
    req(r.get("source_materialization_complete") is True and r.get("materialization_authorized") is False and r.get("package_build_authorized") is False,"Level2 promoted materialization gate")
    req(l["nodes"]["kcmutils"].get("state")=="remediation-pending-build" and l["nodes"]["kcmutils"].get("package_version")==MAT_VERSION,"KCMUtils Level2 promoted source")
    req(l["nodes"]["kcmutils"].get("materialization",{})=={"workflow_run":MAT_RUN,"job_id":MAT_JOB,"artifact_id":MAT_ART,"artifact_sha256":MAT_SHA},"KCMUtils Level2 materialization pin")
    req(m.get("state")=="PASS" and m.get("remediation_queue")==[],"materialization closure")
    req(all(m["nodes"][x].get("state")=="materialized" for x in m.get("selected_nodes",[])),"all Tier3 source materializations promoted")
    me=m["nodes"]["kcmutils"].get("evidence",{})
    req(m["nodes"]["kcmutils"].get("package_version")==MAT_VERSION,"KCMUtils source revision")
    req(me.get("workflow_run")==MAT_RUN and me.get("job_id")==MAT_JOB and me.get("commit")==MAT_COMMIT and me.get("artifact_id")==MAT_ART and me.get("artifact_sha256")==MAT_SHA,"KCMUtils materialization identity")
    req(me.get("package_version")==MAT_VERSION and me.get("result")=="PASS" and me.get("package_attempted") is False and me.get("package_state_effect")=="none","KCMUtils source-only PASS semantics")
    req(me.get("orig_tar_sha256")=="0159f80d030ac250b0b353113a55c013ed7e38cb0b678df44d2f0d0b2aca944c" and me.get("reference_tree_sha256")=="ed24fd11497ef4bf09ebc8a1f7ba6267c139f36ff2ddc54a0383ca90fabf11d6","KCMUtils source/reference pins")
    req(me.get("source_tree_sha256")=="cc08eb539d12a4da323de156af2e4f17c60b4df82e6343db5c0d3eb7e24b1123" and me.get("materialized_tree_sha256")=="4a38fd45ac2d955bb32b275219330dd0e6a9560c7b103a2185a0436bc5505861","KCMUtils materialized tree pins")
    req(me.get("dsc_sha256")=="ab47f2e0d58a566e9ccf87b7cd810845b2192b3b16d944430c4c570599c6bb6e" and me.get("debian_tar_sha256")=="aad01ac6a215716a5cab7481ea1fc4f62c3135c749ca332d3776410600dbfb44","KCMUtils source artifact pins")
    req(m.get("level2_remediation",{}).get("status")=="materialization-PASS" and m.get("level2_remediation",{}).get("source_materialization_complete") is True and m.get("level2_remediation",{}).get("next_gate")==READY_GATE,"materialization remediation closure")
    req(cr.get("status")=="materialization-PASS" and cr.get("materialization_authorized") is False and cr.get("source_materialization_complete") is True and cr.get("next_gate")==READY_GATE,"contract promoted materialization")
else:
    req(r.get("next_gate")==PENDING_GATE,"pending materialization gate")
    req(l["nodes"]["kcmutils"].get("state")=="rematerialization-pending","KCMUtils Level2 rematerialization state")
    req(m.get("state")=="remediation-pending-ci" and m.get("remediation_queue")==["kcmutils"],"materialization queue")
    req(m["nodes"]["kcmutils"].get("state")=="remediation-pending" and m["nodes"]["kcmutils"].get("package_version")=="6.30.0-0supralinux2" and m["nodes"]["kcmutils"].get("candidate_package_version")==MAT_VERSION,"KCMUtils current/candidate source revisions")
    req(cr.get("status")=="materialization-pending-ci" and cr.get("materialization_authorized") is True and cr.get("next_gate")==PENDING_GATE,"contract materialization authorization")

over=c["nodes"]["kcmutils"].get("symbol_template_overrides",[])
by_symbol={x.get("symbol"):x for x in over}
for sym,klass in (
    ("_ZTVSt23_Sp_counted_ptr_inplaceI10QQmlEngineSaIvELN9__gnu_cxx12_Lock_policyE2EE@Base","toolchain-generated-template-vtable"),
    ("_ZTISt23_Sp_counted_ptr_inplaceI10QQmlEngineSaIvELN9__gnu_cxx12_Lock_policyE2EE@Base","toolchain-generated-template-typeinfo"),
):
    x=by_symbol.get(sym,{})
    req(x.get("package")=="libkf6kcmutilsquick6" and x.get("preserve_tags")==["arch=!riscv64"] and x.get("add_tags")==["optional"] and x.get("classification")==klass,"KCMUtils optional toolchain symbol: "+sym)

runner=(ROOT/"scripts/run-kde-tier3-build-level2.sh").read_text()
req("support-closure.json" in runner and '"support_input_ids"' in runner,"support closure evidence")
req('if x["kind"]=="support" and x.get("dev_package")' not in runner,"no synthetic support dev buildinfo edge")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 Level 2 live remediation: PASS")
print("current_package_attempt="+str(cur))
print("next_package_attempt="+str(nxt))
print("canonical="+SNAP)
print("materialization_status="+("PASS" if ready else "pending"))

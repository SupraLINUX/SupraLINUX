#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def req(v,m):
    if not v:
        errors.append(m)

def load(p):
    return json.loads((ROOT/p).read_text())

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
closed_attempt=latest.get("attempt")
next_attempt=(closed_attempt+1) if isinstance(closed_attempt,int) else None
trigger={"attempt":closed_attempt,"workflow_run":latest.get("workflow_run"),"commit":latest.get("commit"),"result":latest.get("result")}

SNAP="16 PASS / 1 pending / 1 current FAIL / 2 BLOCKED"
PENDING_GATE="tier3-level2-remediation-materialization-evidence"
PLANNING_GATE=f"tier3-build-level2-attempt{next_attempt}-planning-validation"
ACTIVE_GATE=f"tier3-build-level2-attempt{next_attempt}"
READY_STATUS="materialization-PASS-pending-package-attempt-activation-validation"
ACTIVE_STATUS="package-attempt-active"
MAT_RUN=36477724469
MAT_JOB=109115619026
MAT_COMMIT="2ff091a675dc7660ebeff0ebb7c7828b9e6fb0bd"
MAT_ART=10994755385
MAT_SHA="69b0be3b9f9db37f7cac1fe1acf2a0b11faa64a796add88c23766d9127f7ea3a"
MAT_VERSION="6.30.0-0supralinux3"
POLICY_RUN=36494035689
LEVEL2_RUN=36494035772
POLICY_JOB=109169283549
PLAN_JOB=109169283518
SKIP_JOB=109169328324
PLANNING_COMMIT="ed1e39fe980acdca43e668ec564a66219d5b2adf"

req(latest.get("result")=="MIXED" and latest.get("package_attempted") is True,"latest valid package attempt closure")
req(closed_attempt==4,"Level2 latest closed package attempt")
r=t.get("level2_remediation",{})
pending=r.get("status")=="materialization-pending-ci"
ready=r.get("status") in {READY_STATUS,"materialization-PASS-pending-attempt5-activation-validation"}
active=r.get("status")==ACTIVE_STATUS
req(pending or ready or active,"Level2 remediation lifecycle")
req(r.get("trigger")==trigger,"Level2 remediation trigger follows latest closed attempt")
req(r.get("source_materialization_nodes")==["kcmutils"],"Level2 source remediation scope")
req(r.get("retained_source_nodes")==["baloo","knotifyconfig","kparts"],"Level2 retained PASS scope")
req(r.get("candidate_package_versions")=={"kcmutils":MAT_VERSION},"Level2 candidate revision")

nodes={x["id"]:x for x in t.get("nodes",[])}
for x in ("baloo","knotifyconfig","kparts"):
    req(nodes[x].get("state")=="PASS" and nodes[x].get("packaging",{}).get("state")=="PASS" and nodes[x].get("packaging",{}).get("downstream_eligible") is True,x+": Attempt4 PASS retained")
req(nodes["kcmutils"].get("state")=="FAIL" and nodes["kcmutils"].get("packaging",{}).get("state")=="FAIL","KCMUtils canonical FAIL retained until package PASS")
req(nodes["ktexteditor"].get("state")=="pending" and nodes["ktexteditor"].get("packaging",{}).get("state")=="pending","KTextEditor remains pending")
for x in ("knewstuff","purpose"):
    req(nodes[x].get("state")=="BLOCKED" and nodes[x].get("packaging",{}).get("blocked_by")==["kcmutils"],x+": remains KCMUtils-blocked")
snap=t.get("level2_snapshot",{})
req((snap.get("pass"),snap.get("pending"),snap.get("current_fail"),snap.get("blocked"))==(16,1,1,2),"canonical snapshot counts")

# Promoted source evidence is identical in READY and ACTIVE states.
if ready or active:
    req(m.get("state")=="PASS" and m.get("remediation_queue")==[],"materialization closure")
    req(all(m["nodes"][x].get("state")=="materialized" for x in m.get("selected_nodes",[])),"all Tier3 sources materialized")
    me=m["nodes"]["kcmutils"].get("evidence",{})
    req(m["nodes"]["kcmutils"].get("package_version")==MAT_VERSION,"KCMUtils source revision")
    req(me.get("workflow_run")==MAT_RUN and me.get("job_id")==MAT_JOB and me.get("commit")==MAT_COMMIT and me.get("artifact_id")==MAT_ART and me.get("artifact_sha256")==MAT_SHA,"KCMUtils materialization identity")
    req(me.get("package_version")==MAT_VERSION and me.get("result")=="PASS" and me.get("package_attempted") is False and me.get("package_state_effect")=="none","KCMUtils source-only PASS semantics")
    req(me.get("orig_tar_sha256")=="0159f80d030ac250b0b353113a55c013ed7e38cb0b678df44d2f0d0b2aca944c" and me.get("reference_tree_sha256")=="ed24fd11497ef4bf09ebc8a1f7ba6267c139f36ff2ddc54a0383ca90fabf11d6","KCMUtils source/reference pins")
    req(me.get("source_tree_sha256")=="cc08eb539d12a4da323de156af2e4f17c60b4df82e6343db5c0d3eb7e24b1123" and me.get("materialized_tree_sha256")=="4a38fd45ac2d955bb32b275219330dd0e6a9560c7b103a2185a0436bc5505861","KCMUtils materialized tree pins")
    req(me.get("dsc_sha256")=="ab47f2e0d58a566e9ccf87b7cd810845b2192b3b16d944430c4c570599c6bb6e" and me.get("debian_tar_sha256")=="aad01ac6a215716a5cab7481ea1fc4f62c3135c749ca332d3776410600dbfb44","KCMUtils source artifact pins")
    req(l["nodes"]["kcmutils"].get("state")=="remediation-pending-build" and l["nodes"]["kcmutils"].get("package_version")==MAT_VERSION,"KCMUtils runnable remediated source")
    req(l["nodes"]["kcmutils"].get("materialization",{})=={"workflow_run":MAT_RUN,"job_id":MAT_JOB,"artifact_id":MAT_ART,"artifact_sha256":MAT_SHA},"KCMUtils Level2 materialization pin")

pol=t.get("discovery_policy",{})
lx=t.get("level2_execution",{})
cr=c.get("level2_remediation",{})

if active:
    req(r.get("execution_authorized") is True and r.get("package_build_authorized") is True and r.get("materialization_authorized") is False,"active remediation authorization")
    req(r.get("current_attempt")==next_attempt and r.get("next_attempt") is None and r.get("next_gate")==ACTIVE_GATE,"active remediation attempt markers")
    req(pol.get("phase")=="build-level2" and pol.get("package_builds")=="tier3-level2-remediation-package-attempt-active","active canonical build gate")
    req(lx.get("status")=="remediation-package-attempt-active" and lx.get("execution_authorized") is True,"active canonical Level2 execution")
    req(lx.get("current_attempt")==next_attempt and lx.get("next_attempt") is None and lx.get("selected_nodes")==["kcmutils"] and lx.get("next_gate")==ACTIVE_GATE,"active canonical execution scope")
    req(lx.get("canonical_prebuild_snapshot")==SNAP,"active canonical prebuild snapshot")
    req(l.get("state")=="active-pending-ci" and l.get("execution_authorized") is True,"Level2 package execution active")
    req(l.get("current_attempt")==next_attempt and l.get("next_attempt") is None and l.get("next_gate")==ACTIVE_GATE,"Level2 active package-attempt markers")
    req(cr.get("status")==ACTIVE_STATUS and cr.get("package_build_authorized") is True and cr.get("materialization_authorized") is False and cr.get("next_gate")==ACTIVE_GATE,"contract package-build authorization")
    expected_planning={"repository_policy_workflow_run":POLICY_RUN,"level2_workflow_run":LEVEL2_RUN,"commit":PLANNING_COMMIT,"policy_job_id":POLICY_JOB,"plan_job_id":PLAN_JOB,"intentional_skip_job_id":SKIP_JOB,"rootfs_job_conclusion":"skipped","package_matrix_conclusion":"skipped","runner_scope_validation":"PASS","remediation_materialization_validation":"PASS","result":"PASS"}
    for obj,name in ((r,"canonical remediation"),(lx,"canonical execution"),(l,"Level2"),(l.get("level2_remediation",{}),"Level2 remediation"),(cr,"contracts")):
        req(obj.get("planning_validation")==expected_planning,name+": planning validation")
    act=l.get("activation",{})
    req(act.get("status")=="ACTIVE" and act.get("attempt")==next_attempt and act.get("scope")=="kcmutils-only","Attempt activation identity")
    req(act.get("planning_policy_workflow_run")==POLICY_RUN and act.get("planning_level2_workflow_run")==LEVEL2_RUN and act.get("planning_commit")==PLANNING_COMMIT,"Attempt activation workflow evidence")
    req(act.get("policy_job_id")==POLICY_JOB and act.get("plan_job_id")==PLAN_JOB and act.get("intentional_skip_job_id")==SKIP_JOB,"Attempt activation job evidence")
    req(act.get("rootfs_job_conclusion")=="skipped" and act.get("package_matrix_conclusion")=="skipped","planning run did not execute packages")
    req(act.get("source_materialization_versions")=={"kcmutils":MAT_VERSION} and act.get("next_gate")==ACTIVE_GATE,"Attempt activation source/gate")
    req(l.get("level2_remediation",{}).get("activation")==act and r.get("activation")==act and cr.get("activation")==act,"activation evidence linkage")
elif ready:
    req(r.get("execution_authorized") is False and r.get("package_build_authorized") is False and r.get("materialization_authorized") is False,"ready remediation execution pause")
    req(r.get("next_gate")==PLANNING_GATE,"ready remediation planning gate")
    req(pol.get("phase")=="build-level2-remediation-planning","ready remediation phase")
    req(lx.get("execution_authorized") is False and lx.get("current_attempt")==closed_attempt and lx.get("next_attempt")==next_attempt and lx.get("next_gate")==PLANNING_GATE,"ready canonical handoff")
    req(l.get("state")=="remediation-materialized-pending-activation" and l.get("execution_authorized") is False,"Level2 ready execution pause")
    req(l.get("current_attempt")==closed_attempt and l.get("next_attempt")==next_attempt and l.get("next_gate")==PLANNING_GATE,"Level2 ready attempt markers")
    req(cr.get("package_build_authorized") is False and cr.get("next_gate")==PLANNING_GATE,"contract ready gate")
else:
    req(r.get("execution_authorized") is False and r.get("next_gate")==PENDING_GATE,"pending remediation gate")
    req(l.get("state")=="remediation-pending-materialization" and l.get("execution_authorized") is False,"Level2 pending materialization")
    req(m.get("state")=="remediation-pending-ci" and m.get("remediation_queue")==["kcmutils"],"materialization queue")

req(l.get("canonical_snapshot")==SNAP,"Level2 canonical snapshot")
for x in ("baloo","knotifyconfig","kparts"):
    req(l["nodes"][x].get("state")=="PASS" and l["nodes"][x].get("pass_evidence",{}).get("result")=="PASS",x+": Level2 PASS retained")

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
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 Level 2 live remediation: PASS")
print("latest_closed_package_attempt="+str(closed_attempt))
print("next_package_attempt="+str(next_attempt))
print("canonical="+SNAP)
print("lifecycle="+r.get("status","unknown"))

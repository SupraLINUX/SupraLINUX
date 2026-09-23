#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

m=load("manifests/kde-tier3-build-level1.json")
a=load("manifests/kde-tier3-build-level1-attempts.json")
campaign=load("manifests/kde-tier3-build-campaign.json")
l0=load("manifests/kde-tier3-build-level0.json")
dag=load("manifests/kde-dag.json")
s0=load("manifests/kde-tier3-support-build-level0.json")
s1=load("manifests/kde-tier3-support-build-level1.json")
tier3=load("manifests/kde-frameworks-tier3.json")

req(m.get("schema")==1 and m.get("authority")=="kde-upstream","Level1 schema/authority")
req(m.get("provider_platform")=="ubuntu-resolute","Level1 provider platform")
req(m.get("role")=="tier3-binary-build-level1" and m.get("frameworks_series")=="6.30.0","Level1 role/series")
req(m.get("state") in {"planned-pending-activation","active-pending-ci","remediation-pending-activation","PARTIAL","PASS"},"Level1 lifecycle")
req(m.get("selected_nodes")==["kio","kxmlgui"],"Level1 node set")
req(m.get("build_campaign_manifest")=="manifests/kde-tier3-build-campaign.json","Level1 campaign link")
req(m.get("materialization_manifest")=="manifests/kde-tier3-materialization.json","Level1 materialization link")
req(m.get("level0_manifest")=="manifests/kde-tier3-build-level0.json","Level1 Level0 link")
req(m.get("attempt_ledger")=="manifests/kde-tier3-build-level1-attempts.json","Level1 attempt ledger link")
req(m.get("canonical_snapshot")=="11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED","Level1 canonical pre-build snapshot")
req(m.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")
if m.get("state")=="planned-pending-activation":
    req(m.get("execution_authorized") is False,"planned Level1 must not authorize builds")
elif m.get("state")=="active-pending-ci":
    req(m.get("execution_authorized") is True,"active Level1 authorization")
elif m.get("state")=="remediation-pending-activation":
    req(m.get("execution_authorized") is False and m.get("current_attempt")==1,"Level1 remediation pause after attempt1")
    rem=m.get("active_remediation",{})
    req(rem.get("round")==1 and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Level1 remediation node set")
    req(rem.get("source_changed_nodes")==[] and set(rem.get("provider_closure_only_nodes",[]))=={"kio","kxmlgui"},"Level1 closure-only remediation")
    req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2","kxmlgui":"6.30.0-0supralinux1"},"Level1 unchanged package revisions")
    req(rem.get("provider_closure_inputs")=={"kio":["karchive","kcodecs","knotifications"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet"]},"Level1 closure input sets")
    req(rem.get("full_level1_rerun_required") is True and rem.get("next_gate")=="tier3-build-level1-attempt2-activation-validation","Level1 attempt2 remediation gate")

pre=m.get("planning_precondition",{})
req(pre.get("level0_attempt")==5 and pre.get("level0_workflow_run")==35818120201,"Level1 Level0 prerequisite")
req(pre.get("kio_round5_materialization_workflow_run")==35825070347,"Level1 KIO round5 materialization run")
req(pre.get("kio_round5_materialization_artifact_id")==10735250819 and pre.get("kio_round5_materialization_artifact_sha256")=="8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106","Level1 KIO materialization pin")
req(pre.get("pre_plan_repository_policy_workflow_run")==35825677329 and pre.get("pre_plan_validated_commit")=="94fb4aebcda2959653b9c436bf5b5789ca3b103f","Level1 pre-plan Policy evidence")

req(tier3.get("build_level1_manifest")=="manifests/kde-tier3-build-level1.json","canonical Level1 manifest link")
policy=tier3.get("discovery_policy",{})
req(policy.get("phase") in {"build-level1-planning","build-level1"},"canonical Level1 phase")
req(policy.get("package_builds") in {"tier3-level1-source-PASS-pending-planning-validation","tier3-level1-authorized","tier3-level1-remediation-pending-provider-closure"},"canonical Level1 build gate")
ar=tier3.get("active_remediation",{})
if policy.get("package_builds")=="tier3-level1-remediation-pending-provider-closure":
    req(ar.get("round")==6 and set(ar.get("nodes",[]))=={"kio","kxmlgui"},"canonical round6 scope")
    req(ar.get("source_materialization_nodes")==[] and set(ar.get("provider_closure_only_nodes",[]))=={"kio","kxmlgui"},"canonical round6 closure-only classes")
else:
    req(ar.get("round")==5 and ar.get("nodes")==["kio"],"canonical round5 scope")
    req(ar.get("materialization_workflow_run")==35825070347 and ar.get("materialization_commit")=="fbde9a53e357a138f4d74d7905230c7859e20444","canonical KIO materialization evidence")
if policy.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
    req(ar.get("status")=="materialization-PASS-pending-level1-planning-validation","canonical planning-validation state")
    req(ar.get("level1_execution_authorized") is False and ar.get("next_gate")=="tier3-build-level1-planning-validation","canonical Level1 execution pause")
elif policy.get("package_builds")=="tier3-level1-remediation-pending-provider-closure":
    req(policy.get("phase")=="build-level1","canonical Level1 remediation phase")
    req(ar.get("status")=="provider-closure-pending-attempt2-activation-validation","canonical round6 remediation state")
    req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"canonical Level1 remediation pause")
    req(ar.get("validation_workflow_run")==35826694664 and ar.get("validation_result")=="0 workflow SUCCESS / 2 FAIL","canonical Attempt1 failure evidence")
    req(ar.get("next_gate")=="tier3-build-level1-attempt2-activation-validation","canonical Attempt2 activation gate")
elif policy.get("package_builds")=="tier3-level1-authorized":
    req(policy.get("phase")=="build-level1","canonical active Level1 phase")
    req(ar.get("status")=="level1-active-pending-ci","canonical active Level1 state")
    req(ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True,"canonical Level1 authorization")
    req(ar.get("current_attempt")==1 and ar.get("planning_policy_workflow_run")==35826072726,"canonical Level1 attempt/planning evidence")
    req(ar.get("next_gate")=="tier3-build-level1-attempt1","canonical Level1 attempt1 gate")
    req(tier3.get("support_components",{}).get("next_gate")=="tier3-build-level1","canonical Level1 support gate")

shared=m.get("shared_predecessors",{}).get("extra-cmake-modules",{})
ecm=campaign.get("retained_pass_artifacts",{}).get("extra-cmake-modules",{})
req(shared.get("version")==ecm.get("version") and shared.get("artifact_id")==ecm.get("artifact_id") and shared.get("artifact_sha256")==ecm.get("artifact_sha256"),"Level1 ECM pin")

ret=m.get("retained_predecessors",{})
def check_pin(node,cfg,expected_version,expected_artifact,expected_sha):
    req(cfg.get("version")==expected_version,f"{node}: retained version")
    req(cfg.get("artifact_id")==expected_artifact and cfg.get("artifact_sha256")==expected_sha,f"{node}: retained artifact")

for node,cfg in ret.items():
    prov=cfg.get("provenance")
    if prov=="canonical-dag-pass":
        can=dag.get("nodes",{}).get(node,{})
        cp=campaign.get("retained_pass_artifacts",{}).get(node,{})
        req(can.get("state")=="PASS" and can.get("downstream_eligible") is True,f"{node}: canonical DAG PASS")
        check_pin(node,cfg,cp.get("version"),cp.get("artifact_id"),cp.get("artifact_sha256"))
    elif prov=="tier3-level0-pass":
        n=l0.get("nodes",{}).get(node,{})
        ev=n.get("pass_evidence",{})
        req(n.get("state")=="PASS" and ev.get("result")=="PASS" and ev.get("downstream_eligible") is True,f"{node}: Level0 PASS")
        check_pin(node,cfg,n.get("package_version"),ev.get("artifact_id"),ev.get("artifact_sha256"))
    elif prov=="tier3-support-pass":
        n=(s0 if node=="kdoctools" else s1).get("nodes",{}).get(node,{})
        ev=n.get("pass_evidence",{})
        req(n.get("state")=="PASS" and ev.get("result")=="PASS" and ev.get("downstream_eligible") is True,f"{node}: support PASS")
        check_pin(node,cfg,n.get("package_version"),ev.get("artifact_id"),ev.get("artifact_sha256"))
    elif prov=="canonical-dag-provider-closure":
        can=dag.get("nodes",{}).get(node,{})
        cp=campaign.get("retained_pass_artifacts",{}).get(node,{})
        req(can.get("state")=="PASS" and can.get("downstream_eligible") is True,f"{node}: provider-closure canonical PASS")
        check_pin(node,cfg,cp.get("version"),cp.get("artifact_id"),cp.get("artifact_sha256"))
    else:
        req(False,f"{node}: unknown predecessor provenance")
    req(cfg.get("dev_package") in cfg.get("expected_binary_packages",[]),f"{node}: dev package identity")

expected={
 "kio":{
   "version":"6.30.0-0supralinux2",
   "materialization":(35825070347,10735250819,"8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106"),
   "tier3":["kbookmarks","kiconthemes","kjobwidgets","kwallet"],
   "support_build":["kdoctools"],"support_runtime":["kded"],"python":None,
 },
 "kxmlgui":{
   "version":"6.30.0-0supralinux1",
   "materialization":(35746667704,10703925009,"9ad2056d1dbc9ab626521cd1f4bc67c13f5e36b18d93fc67da8ee6b7da3ba2fc"),
   "tier3":["kconfigwidgets","kiconthemes","ktextwidgets"],
   "support_build":[],"support_runtime":[],"python":"KXmlGui",
 },
}
for node,e in expected.items():
    n=m.get("nodes",{}).get(node,{})
    p=campaign.get("nodes",{}).get(node,{})
    req(n.get("state") in {"prepared-pending-build","prepared-pending-revalidation","remediation-pending-build","PASS","FAIL"} ,f"{node}: Level1 state")
    req(n.get("source_package")==p.get("source_package") and n.get("package_version")==e["version"],f"{node}: package identity")
    req(n.get("expected_binary_packages")==p.get("expected_binary_packages"),f"{node}: binary set")
    mat=n.get("materialization",{})
    req((mat.get("workflow_run"),mat.get("artifact_id"),mat.get("artifact_sha256"))==e["materialization"],f"{node}: materialization pin")
    classes=n.get("input_classes",{})
    req(classes.get("tier3_level0_pass")==e["tier3"],f"{node}: Tier3 predecessor class")
    req(classes.get("support_build")==e["support_build"] and classes.get("support_runtime")==e["support_runtime"],f"{node}: support classes")
    req(n.get("runtime_validation_input_ids")==e["support_runtime"],f"{node}: runtime validation inputs")
    req(n.get("python_module")==e["python"],f"{node}: Python module")
    req(n.get("success_transition")=="PASS" and n.get("downstream_eligible_on_build_success") is True,f"{node}: success transition")
    provider_closure=n.get("provider_closure_input_ids",[])
    req(provider_closure==classes.get("provider_closure",[]),f"{node}: provider closure class linkage")
    req(set(n.get("retained_input_ids",[]))==set(classes.get("external_pass",[])+classes.get("tier3_level0_pass",[])+classes.get("support_build",[])+classes.get("support_runtime",[])+provider_closure),f"{node}: retained input closure")
    req(all(ret.get(x,{}).get("provenance")=="canonical-dag-provider-closure" or x in classes.get("external_pass",[]) for x in provider_closure),f"{node}: provider closure PASS provenance")
    req(all(ret.get(x,{}).get("dev_package") not in n.get("buildinfo_proof_packages",[]) for x in provider_closure if x not in classes.get("external_pass",[])),f"{node}: provider closure must not invent buildinfo edge")
    for pkg in n.get("buildinfo_proof_packages",[]):
        providers=[x for x in n.get("retained_input_ids",[]) if ret.get(x,{}).get("dev_package")==pkg]
        req(len(providers)==1,f"{node}: buildinfo provider for {pkg}")

req(a.get("schema")==1 and a.get("batch")=="tier3-build-level1","Level1 ledger schema/batch")
req(a.get("selected_nodes")==["kio","kxmlgui"] and set(a.get("nodes",{}))=={"kio","kxmlgui"},"Level1 ledger node set")
if m.get("state")=="planned-pending-activation":
    req(a.get("campaign_history")==[] and a.get("nodes",{}).get("kio")==[] and a.get("nodes",{}).get("kxmlgui")==[],"planned Level1 ledger must be empty")
else:
    hist=a.get("campaign_history",[])
    req(len(hist)>=1 and hist[0].get("attempt")==1 and hist[0].get("workflow_run")==35826694664,"Level1 Attempt1 ledger history")
    req(hist[0].get("workflow_jobs")=={"success":0,"fail":2} and set(hist[0].get("fail",[]))=={"kio","kxmlgui"} and hist[0].get("blocked")==[],"Level1 Attempt1 result summary")
    req(hist[0].get("failure_class")=="provider-closure-incomplete","Level1 Attempt1 failure class")
    for node,job,artifact,digest,version in (
      ("kio",107070288529,10735576795,"bbc1cb4caa351a335077e4b3dc0dcee7b2a7dfb96d85e6659d112ad87069c353","6.30.0-0supralinux2"),
      ("kxmlgui",107070288573,10734929331,"9e14c20ddfed7bc1cb500e1c2544eac1469b97cc2862ed54a946fd0deb1161ed","6.30.0-0supralinux1"),
    ):
        x=a["nodes"][node][0]
        req(x.get("attempt")==1 and x.get("result")=="FAIL" and x.get("workflow_run")==35826694664 and x.get("job_id")==job,f"{node}: Attempt1 FAIL identity")
        req(x.get("artifact_id")==artifact and x.get("artifact_sha256")==digest,f"{node}: Attempt1 artifact")
        req(x.get("rootfs_artifact_id")==10735292514 and x.get("rootfs_sha256")=="65b28559cd2e23c1a2b5968e12ca0b3e48fd518b791b069ac2217898b44bfbed",f"{node}: Attempt1 rootfs evidence")
        req(x.get("package_attempted") is True and x.get("stage")=="sbuild" and x.get("failure_substage")=="install-deps",f"{node}: Attempt1 failure stage")
        req(x.get("package_version")==version and x.get("package_version_unchanged") is True and x.get("source_change") is False,f"{node}: Attempt1 no source revision change")

for path in (
 "scripts/plan-kde-tier3-build-level1.py",
 "scripts/test-kde-tier3-build-level1-planner.py",
 "scripts/run-kde-tier3-build-level1.sh",
 ".github/workflows/kde-tier3-build-level1.yml",
 "docs/kde-tier3-build-level1.md",
):
    req((ROOT/path).exists(),f"missing Level1 component: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 build Level 1 definition: PASS")
print("state="+m["state"])
print("execution_authorized="+str(m["execution_authorized"]).lower())

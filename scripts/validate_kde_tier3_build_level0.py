#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def req(v,m):
    if not v:
        errors.append(m)

def load(p):
    return json.loads((ROOT/p).read_text())

m=load("manifests/kde-tier3-build-level0.json")
a=load("manifests/kde-tier3-build-level0-attempts.json")
p=load("manifests/kde-tier3-build-campaign.json")
t=load("manifests/kde-frameworks-tier3.json")
mat=load("manifests/kde-tier3-materialization.json")
dag=load("manifests/kde-dag.json")

expected=p["levels"][0]["nodes"]
remediation_nodes={"kiconthemes","kdav","kwallet","krunner","kjobwidgets"}

req(m.get("schema")==1,"Tier3 level0 schema")
req(m.get("authority")=="kde-upstream","Tier3 level0 authority")
req(m.get("provider_platform")=="ubuntu-resolute","Tier3 level0 provider platform")
req(m.get("role")=="tier3-binary-build-level0","Tier3 level0 role")
req(m.get("frameworks_series")=="6.30.0","Tier3 level0 series")
req(m.get("state") in {"active-pending-ci","remediation-pending-materialization","remediation-materialized-pending-activation","PASS","PARTIAL"},"Tier3 level0 lifecycle")
req(m.get("package_state_effect")=="real-package-build-on-PASS","Tier3 level0 package-state effect")
req(m.get("build_campaign_manifest")=="manifests/kde-tier3-build-campaign.json","Tier3 level0 campaign linkage")
req(m.get("materialization_manifest")=="manifests/kde-tier3-materialization.json","Tier3 level0 materialization linkage")
req(m.get("attempt_ledger")=="manifests/kde-tier3-build-level0-attempts.json","Tier3 level0 attempt ledger")
req(m.get("selected_nodes")==expected and len(expected)==12,"Tier3 level0 exact node set")
req(set(m.get("nodes",{}))==set(expected),"Tier3 level0 node map")
req(set(a.get("nodes",{}))==set(expected),"Tier3 level0 attempt ledger node set")
req(p.get("state")=="planned" and p.get("execution_authorized") is False,"global campaign plan remains non-executing")

sched=m.get("scheduling",{})
req(sched.get("fail_fast") is False,"Tier3 level0 fail-fast policy")
req(sched.get("parallel_independent_nodes") is True,"Tier3 level0 parallelism policy")
req(sched.get("shared_resolute_rootfs") is True,"Tier3 level0 shared rootfs policy")
req(sched.get("only_pass_predecessor_artifacts") is True,"Tier3 level0 predecessor policy")

sem=m.get("semantics",{})
req(sem.get("pre_sbuild_failure")=="INFRA","Tier3 level0 pre-sbuild semantics")
req(sem.get("package_attempt_begins")=="immediately-before-sbuild","Tier3 level0 attempt boundary")
req(sem.get("blocked_is_not_fail") is True,"Tier3 level0 BLOCKED semantics")
req(sem.get("independent_nodes_continue_after_unrelated_failures") is True,"Tier3 level0 independent continuation")
req(sem.get("knewstuff_build_success_state")=="runtime-validation-required","KNewStuff deferred state")
req(sem.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

ecm=m.get("shared_predecessors",{}).get("extra-cmake-modules",{})
req(ecm.get("version")=="6.30.0-0supralinux3","Tier3 level0 ECM version")
req(isinstance(ecm.get("artifact_id"),int) and len(ecm.get("artifact_sha256",""))==64,"Tier3 level0 ECM artifact")
req(ecm.get("expected_binary_packages")==["extra-cmake-modules"],"Tier3 level0 ECM package set")

for pred,cfg in m.get("retained_predecessors",{}).items():
    dn=dag.get("nodes",{}).get(pred,{})
    req(dn.get("state")=="PASS" and dn.get("downstream_eligible") is True,f"{pred}: retained canonical PASS")
    req(cfg.get("version")==dn.get("package_version"),f"{pred}: retained version pin")
    req(cfg.get("expected_binary_packages")==dn.get("binary_packages"),f"{pred}: retained binary package set")
    req(isinstance(cfg.get("artifact_id"),int) and len(cfg.get("artifact_sha256",""))==64,f"{pred}: retained artifact pin")
    req(isinstance(cfg.get("dev_package"),str) and cfg.get("dev_package","").endswith("-dev"),f"{pred}: retained dev package")

breeze=m.get("support_predecessors",{}).get("breeze-icons",{})
req(breeze.get("version")=="4:6.30.0-0supralinux1","Breeze Icons support version")
req(breeze.get("dev_package")=="libkf6breezeicons-dev","Breeze Icons support dev package")
req(isinstance(breeze.get("artifact_id"),int) and len(breeze.get("artifact_sha256",""))==64,"Breeze Icons support artifact")

for node_id in expected:
    n=m["nodes"][node_id]
    gp=p["nodes"][node_id]
    req(n.get("state") in {
        "prepared-pending-build","prepared-pending-revalidation",
        "remediation-pending-build","remediation-pending-materialization",
        "PASS","FAIL","runtime-validation-required"
    },f"{node_id}: level0 node lifecycle")
    req(n.get("source_package")==gp.get("source_package"),f"{node_id}: source package")
    req(n.get("package_version")==gp.get("package_version"),f"{node_id}: package version")
    req(n.get("expected_binary_packages")==gp.get("expected_binary_packages"),f"{node_id}: binary package set")
    req(n.get("materialization")==gp.get("materialization"),f"{node_id}: materialization pin")
    req(gp.get("blocking_predecessors")==[],f"{node_id}: level0 has no Tier3 blockers")
    req(n.get("direct_build_predecessors")==gp.get("external_build_inputs"),f"{node_id}: direct build predecessors")
    req(n.get("external_runtime_inputs")==gp.get("external_runtime_inputs"),f"{node_id}: external runtime inputs")
    req(n.get("deferred_runtime_validation")==gp.get("deferred_runtime_validation"),f"{node_id}: deferred runtime linkage")
    req(n.get("success_transition")==gp.get("canonical_success_transition"),f"{node_id}: success transition")

    for pred in n.get("retained_input_ids",[]):
        req(pred in m.get("retained_predecessors",{}),f"{node_id}: retained input {pred} exists")
    for pred in n.get("direct_build_predecessors",[]):
        req(pred in n.get("retained_input_ids",[]),f"{node_id}: direct predecessor {pred} included in retained closure")
    for pred in n.get("external_runtime_inputs",[]):
        req(pred in n.get("retained_input_ids",[]),f"{node_id}: runtime predecessor {pred} included in retained closure")
    for pkg in n.get("buildinfo_proof_packages",[]):
        req(any(cfg.get("dev_package")==pkg for cfg in m.get("retained_predecessors",{}).values()),f"{node_id}: buildinfo package {pkg} comes from retained PASS")

    if node_id=="kiconthemes":
        req(n.get("support_input_ids")==["breeze-icons"],"KIconThemes Breeze support input")
    else:
        req(n.get("support_input_ids")==[],f"{node_id}: unexpected support input")

    if node_id=="kjobwidgets":
        req(n.get("python_module")=="KJobWidgets","KJobWidgets Python module")
        req(n.get("extra_buildinfo_proof_packages")==["python3-kcoreaddons"],"KJobWidgets Python predecessor proof")
        req(n.get("profile_assertions",{}).get("BUILD_PYTHON_BINDINGS")=="ON","KJobWidgets Python profile")
    if node_id=="kdesu":
        req(n.get("profile_assertions",{}).get("KDESU_USE_SUDO_DEFAULT")=="ON","KDESu sudo profile")
    req(n.get("profile_assertions",{}).get("BUILD_TESTING")=="ON",f"{node_id}: BUILD_TESTING ON")

    if node_id=="knewstuff":
        req(n.get("deferred_runtime_validation")==["kcmutils"],"KNewStuff KCMUtils deferred validation")
        req(n.get("downstream_eligible_on_build_success") is False,"KNewStuff cannot be downstream-eligible after build only")
    else:
        req(n.get("deferred_runtime_validation")==[],f"{node_id}: no deferred runtime validation")
        req(n.get("downstream_eligible_on_build_success") is True,f"{node_id}: build PASS downstream eligibility")

if m.get("state")=="active-pending-ci":
    req(m.get("execution_authorized") is True,"active Level0 execution authorization")
    req(mat.get("state")=="PASS","active Level0 requires materialization PASS")
    req(all(m["nodes"][n].get("state") in {"prepared-pending-build","remediation-pending-build"} for n in expected),"active Level0 node readiness")
    if m.get("current_attempt")==2:
        req(m.get("activation",{}).get("status")=="ACTIVE","Level0 attempt2 activation status")
        req(m.get("activation",{}).get("promotion_validation_workflow_run")==35769883615,"Level0 attempt2 promotion validation")
        req(m.get("activation",{}).get("scope")=="full-level0-rerun-12-nodes","Level0 attempt2 full rerun scope")
        req(m.get("remediation",{}).get("status")=="level0-rerun-active","Level0 attempt2 remediation state")
        req(all(m["nodes"][n].get("current_attempt")==2 for n in expected),"Level0 attempt2 node markers")
elif m.get("state")=="remediation-pending-materialization":
    req(m.get("execution_authorized") is False,"Level0 execution paused during source remediation")
    req(mat.get("state")=="remediation-pending-ci","Level0 remediation requires selective materialization")
    rem=m.get("remediation",{})
    req(set(rem.get("queue",[]))==remediation_nodes and len(rem.get("queue",[]))==5,"Level0 remediation queue")
    req(rem.get("candidate_package_version")=="6.30.0-0supralinux2","Level0 remediation package revision")
    req(rem.get("full_level0_rerun_required") is True,"Level0 full rerun policy")
    req(all(m["nodes"][n].get("state")=="remediation-pending-materialization" for n in remediation_nodes),"failed nodes await rematerialization")
    req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in remediation_nodes),"successful attempt1 nodes await full revalidation")
    for n in remediation_nodes:
        node=m["nodes"][n]
        req(node.get("previous_package_version")=="6.30.0-0supralinux1",f"{n}: previous package revision")
        req(node.get("candidate_package_version")=="6.30.0-0supralinux2",f"{n}: remediation candidate revision")
    req("kcoreaddons" in m["nodes"]["kiconthemes"].get("retained_input_ids",[]),"KIconThemes provider closure includes KCoreAddons")
    req(m["nodes"]["kiconthemes"].get("package_closure_remediation",{}).get("added_retained_input")=="kcoreaddons","KIconThemes closure remediation documented")

    summary=m.get("attempt1_summary",{})
    req(summary.get("workflow_run")==35755924197,"Level0 attempt1 workflow")
    req(summary.get("commit")=="d73a6b25ea7a9ecd1e5fa088db734b29d159d618","Level0 attempt1 commit")
    req(summary.get("result")=="PARTIAL","Level0 attempt1 result")
    req(set(summary.get("job_success",[]))=={"kbookmarks","kconfigwidgets","kdesu","knewstuff","kpeople","ksvg","ktextwidgets"},"Level0 attempt1 success set")
    req(set(summary.get("job_fail",[]))==remediation_nodes,"Level0 attempt1 fail set")
    req(summary.get("canonical_promotions")==0,"Level0 attempt1 promoted nothing")

    history=a.get("campaign_history",[])
    req(len(history)>=1 and history[-1].get("attempt")==1 and history[-1].get("workflow_run")==35755924197,"Level0 campaign history")
    expected_results={
        "kbookmarks":"PASS","kconfigwidgets":"PASS","kdav":"FAIL","kdesu":"PASS",
        "kiconthemes":"FAIL","kjobwidgets":"FAIL","knewstuff":"RUNTIME_PENDING",
        "kpeople":"PASS","krunner":"FAIL","ksvg":"PASS","ktextwidgets":"PASS","kwallet":"FAIL",
    }
    for node_id,result in expected_results.items():
        entries=a["nodes"][node_id]
        req(len(entries)>=1 and entries[-1].get("attempt")==1,f"{node_id}: attempt1 ledger entry")
        if entries:
            e=entries[-1]
            req(e.get("workflow_run")==35755924197,f"{node_id}: attempt1 workflow")
            req(e.get("package_attempted") is True,f"{node_id}: attempt1 real package attempt")
            req(e.get("result")==result,f"{node_id}: attempt1 result")
            req(isinstance(e.get("artifact_id"),int) and len(e.get("artifact_sha256",""))==64,f"{node_id}: attempt1 artifact evidence")
    req(a["nodes"]["knewstuff"][-1].get("downstream_eligible") is False,"KNewStuff attempt1 remains non-downstream-eligible")
    for n in remediation_nodes:
        req(isinstance(a["nodes"][n][-1].get("cause"),str) and isinstance(a["nodes"][n][-1].get("remediation"),str),f"{n}: root cause/remediation recorded")

elif m.get("state")=="remediation-materialized-pending-activation":
    req(m.get("execution_authorized") is False,"Level0 remains paused until remediation promotion validation")
    req(mat.get("state")=="PASS","remediation materialization must be promoted PASS")
    rem=m.get("remediation",{})
    req(rem.get("status")=="materialization-PASS-pending-activation","Level0 remediation materialization promoted")
    req(rem.get("materialization_workflow_run")==35759443440,"Level0 remediation materialization workflow")
    req(rem.get("materialization_commit")=="0c23204d90b8a40ebf078ba41667c2292673ea81","Level0 remediation materialization commit")
    req(rem.get("full_level0_rerun_required") is True,"Level0 full rerun still required")
    req(all(m["nodes"][n].get("state")=="remediation-pending-build" for n in remediation_nodes),"remediated nodes ready for rebuild")
    req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in remediation_nodes),"attempt1 successes await revalidation")
    for n in remediation_nodes:
        node=m["nodes"][n]
        req(node.get("package_version")=="6.30.0-0supralinux2",f"{n}: promoted remediation revision")
        req(node.get("materialization",{}).get("workflow_run")==35759443440,f"{n}: promoted remediation materialization workflow")
        req(node.get("materialization")==p["nodes"][n].get("materialization"),f"{n}: campaign/materialization pin refreshed")
    req("kcoreaddons" in m["nodes"]["kiconthemes"].get("retained_input_ids",[]),"KIconThemes provider closure retains KCoreAddons")

policy=t.get("discovery_policy",{})
req(policy.get("phase")=="build-level0","canonical Tier3 Level0 phase")
if m.get("state")=="remediation-pending-materialization":
    req(policy.get("package_builds")=="tier3-level0-remediation-pending","canonical Tier3 remediation build gate")
else:
    req(policy.get("package_builds") in {"tier3-level0-authorized","tier3-level0-remediation-pending"},"canonical Tier3 Level0 build gate")
req(t.get("support_components",{}).get("next_gate")=="tier3-build-level0","canonical Tier3 Level0 next gate")
req(t.get("build_level0_manifest")=="manifests/kde-tier3-build-level0.json","canonical Tier3 Level0 manifest linkage")

for path in (
 "scripts/plan-kde-tier3-build-level0.py",
 "scripts/run-kde-tier3-build-level0.sh",
 ".github/workflows/kde-tier3-build-level0.yml",
 "docs/kde-tier3-build-level0.md",
):
    req((ROOT/path).exists(),f"missing Tier3 Level0 component: {path}")

doc=(ROOT/"docs/kde-tier3-build-level0.md").read_text()
for token in ("12","FAIL","BLOCKED","KNewStuff","KCMUtils","Breeze Icons","remediation","35755924197","stable"):
    req(token in doc,f"Tier3 Level0 docs missing {token}")

if errors:
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 build Level 0 definition: PASS")
print("nodes=12")
print("state="+m["state"])
print("execution_authorized="+str(m.get("execution_authorized")).lower())

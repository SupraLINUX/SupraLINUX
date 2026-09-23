#!/usr/bin/env python3
from pathlib import Path
import json
import sys

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
round1={"kiconthemes","kdav","kwallet","krunner","kjobwidgets"}
round2={"kiconthemes","kjobwidgets","kwallet"}

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

# Retained PASS predecessors remain pinned.
ecm=m.get("shared_predecessors",{}).get("extra-cmake-modules",{})
req(ecm.get("version")=="6.30.0-0supralinux3","Tier3 level0 ECM version")
req(isinstance(ecm.get("artifact_id"),int) and len(ecm.get("artifact_sha256",""))==64,"Tier3 level0 ECM artifact")
for pred,cfg in m.get("retained_predecessors",{}).items():
    dn=dag.get("nodes",{}).get(pred,{})
    req(dn.get("state")=="PASS" and dn.get("downstream_eligible") is True,f"{pred}: retained canonical PASS")
    req(cfg.get("version")==dn.get("package_version"),f"{pred}: retained version pin")
    req(cfg.get("expected_binary_packages")==dn.get("binary_packages"),f"{pred}: retained binary package set")
    req(isinstance(cfg.get("artifact_id"),int) and len(cfg.get("artifact_sha256",""))==64,f"{pred}: retained artifact pin")

support=m.get("support_predecessors",{})
breeze=support.get("breeze-icons",{})
req(breeze.get("version")=="4:6.30.0-0supralinux1" and breeze.get("dev_package")=="libkf6breezeicons-dev","Breeze Icons support provider")
req(isinstance(breeze.get("artifact_id"),int) and len(breeze.get("artifact_sha256",""))==64,"Breeze Icons support artifact")
kdoc=support.get("kdoctools",{})
if kdoc:
    req(kdoc.get("version")=="6.30.0-0supralinux1","KDocTools support version")
    req(kdoc.get("workflow_run")==35700002095 and kdoc.get("artifact_id")==10682066198,"KDocTools support evidence")
    req(kdoc.get("artifact_sha256")=="6daeb6beed63ba7b7e441dba4dfd356be3ad48a9f3ae75acddae0945c36a683d","KDocTools support digest")
    req(kdoc.get("dev_package")=="libkf6doctools-dev","KDocTools support dev package")

for node_id in expected:
    n=m["nodes"][node_id]
    gp=p["nodes"][node_id]
    req(n.get("state") in {
        "prepared-pending-build","prepared-pending-revalidation",
        "remediation-pending-build","remediation-pending-materialization",
        "PASS","FAIL","runtime-validation-required"
    },f"{node_id}: level0 node lifecycle")
    req(n.get("source_package")==gp.get("source_package"),f"{node_id}: source package")
    req(n.get("package_version")==gp.get("package_version"),f"{node_id}: current promoted source version")
    req(n.get("expected_binary_packages")==gp.get("expected_binary_packages"),f"{node_id}: binary package set")
    req(n.get("materialization")==gp.get("materialization"),f"{node_id}: promoted materialization pin")
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

    if node_id=="kiconthemes":
        req(n.get("support_input_ids")==["breeze-icons"],"KIconThemes Breeze support input")
    elif node_id=="kwallet" and m.get("active_remediation",{}).get("round")==2:
        req(n.get("support_input_ids")==["kdoctools"],"KWallet KDocTools documentation support input")
        req(n.get("support_provider_role",{}).get("kdoctools")=="optional-upstream-documentation-provider-required-by-selected-manpage-payload","KWallet KDocTools provider role")
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

# Historical campaign 1 is retained.
history=a.get("campaign_history",[])
req(len(history)>=2,"Level0 campaign history contains attempts 1 and 2")
req(history[0].get("attempt")==1 and history[0].get("workflow_run")==35755924197,"Level0 attempt1 history")
req(history[0].get("workflow_jobs")=={"success":7,"fail":5},"Level0 attempt1 summary")

# Attempt 2 is real evidence: 9 job successes, 3 real FAILs, zero promotion.
attempt2=history[-1]
req(attempt2.get("attempt")==2 and attempt2.get("workflow_run")==35770505868,"Level0 attempt2 history")
req(attempt2.get("commit")=="b381031bd9bbd7ea5b1d9a1ed3739766588be78e","Level0 attempt2 commit")
req(attempt2.get("workflow_jobs")=={"success":9,"fail":3},"Level0 attempt2 job summary")
req(attempt2.get("canonical_promotions")==0,"Level0 attempt2 promoted nothing")
req(attempt2.get("rootfs",{}).get("artifact_id")==10714370160,"Level0 attempt2 rootfs artifact")
req(attempt2.get("rootfs",{}).get("artifact_sha256")=="5e84adbad7e684010eefad73daff28fae7f894a325ec03d744b934558a6de4ea","Level0 attempt2 rootfs digest")

expected2={
    "kbookmarks":"PASS","kconfigwidgets":"PASS","kdav":"PASS","kdesu":"PASS",
    "kiconthemes":"FAIL","kjobwidgets":"FAIL","knewstuff":"RUNTIME_PENDING",
    "kpeople":"PASS","krunner":"PASS","ksvg":"PASS","ktextwidgets":"PASS","kwallet":"FAIL",
}
for node_id,result in expected2.items():
    entries=a["nodes"][node_id]
    req(len(entries)>=2 and entries[-1].get("attempt")==2,f"{node_id}: attempt2 ledger entry")
    if entries:
        e=entries[-1]
        req(e.get("workflow_run")==35770505868,f"{node_id}: attempt2 workflow")
        req(e.get("package_attempted") is True,f"{node_id}: attempt2 real package attempt")
        req(e.get("result")==result,f"{node_id}: attempt2 result")
        req(isinstance(e.get("artifact_id"),int) and len(e.get("artifact_sha256",""))==64,f"{node_id}: attempt2 artifact evidence")

req(a["nodes"]["knewstuff"][-1].get("downstream_eligible") is False,"KNewStuff attempt2 remains non-downstream-eligible")
req(a["nodes"]["kdav"][-1].get("remediation_validation")=="round1 PASS","KDAV round1 remediation validated")
req(a["nodes"]["krunner"][-1].get("remediation_validation")=="round1 PASS","KRunner round1 remediation validated")
for node_id in round2:
    e=a["nodes"][node_id][-1]
    req(isinstance(e.get("cause"),str) and isinstance(e.get("remediation"),str),f"{node_id}: attempt2 root cause/remediation recorded")

if m.get("state")=="remediation-materialized-pending-activation":
    req(m.get("execution_authorized") is False,"Level0 remains paused before attempt3 activation")
    req(mat.get("state")=="PASS","round2 materialization promoted PASS")
    rem=m.get("active_remediation",{})
    req(rem.get("round")==2 and rem.get("status")=="materialization-PASS-pending-activation","Level0 round2 promotion state")
    req(rem.get("materialization_workflow_run")==35806738003,"Level0 round2 materialization run")
    req(rem.get("materialization_commit")=="d6aa9a9550dc3c870a9f1beb00fe216d8c20c3d6","Level0 round2 materialization commit")
    req(rem.get("full_level0_rerun_required") is True,"attempt3 full rerun policy")
    req(all(m["nodes"][n].get("state")=="remediation-pending-build" for n in round2),"round2 nodes ready for attempt3")
    req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in round2),"other Level0 nodes await attempt3 revalidation")
    for n in round2:
        node=m["nodes"][n]
        req(node.get("package_version")=="6.30.0-0supralinux3",f"{n}: promoted round2 revision")
        req(node.get("materialization",{}).get("workflow_run")==35806738003,f"{n}: promoted round2 materialization")
        req(node.get("materialization")==p["nodes"][n].get("materialization"),f"{n}: campaign pin refreshed")
    req(m["nodes"]["kwallet"].get("support_input_ids")==["kdoctools"],"KWallet KDocTools support retained for attempt3")

elif m.get("state")=="remediation-pending-materialization":
    req(m.get("execution_authorized") is False,"Level0 execution paused during round2 source remediation")
    req(mat.get("state")=="remediation-pending-ci","Level0 round2 requires selective materialization")
    rem=m.get("active_remediation",{})
    req(rem.get("round")==2 and set(rem.get("queue",[]))==round2,"Level0 round2 remediation queue")
    req(rem.get("candidate_package_version")=="6.30.0-0supralinux3","Level0 round2 candidate revision")
    req(rem.get("trigger_workflow_run")==35770505868,"Level0 round2 trigger run")
    req(rem.get("full_level0_rerun_required") is True,"Level0 round2 full rerun policy")
    req(all(m["nodes"][n].get("state")=="remediation-pending-materialization" for n in round2),"round2 failed nodes await rematerialization")
    req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in round2),"attempt2 non-failing nodes await revalidation")
    for n in round2:
        req(m["nodes"][n].get("previous_package_version")=="6.30.0-0supralinux2",f"{n}: round2 previous package revision")
        req(m["nodes"][n].get("candidate_package_version")=="6.30.0-0supralinux3",f"{n}: round2 candidate package revision")
    req(m.get("attempt2_summary",{}).get("workflow_run")==35770505868,"Level0 attempt2 summary linkage")
    req(set(m.get("attempt2_summary",{}).get("job_fail",[]))==round2,"Level0 attempt2 fail set")

policy=t.get("discovery_policy",{})
req(policy.get("phase")=="build-level0","canonical Tier3 Level0 phase")
if m.get("state")=="remediation-pending-materialization":
    req(policy.get("package_builds")=="tier3-level0-remediation-pending","canonical Tier3 round2 remediation build gate")
    ar=t.get("active_remediation",{})
    req(ar.get("round")==2 and set(ar.get("nodes",[]))==round2,"canonical Tier3 round2 remediation linkage")
    req(ar.get("candidate_package_version")=="6.30.0-0supralinux3","canonical Tier3 round2 revision")
    req(ar.get("execution_authorized") is False,"canonical Tier3 round2 execution pause")
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
for token in ("12","FAIL","BLOCKED","KNewStuff","KCMUtils","attempt 2","round 2","stable"):
    req(token.lower() in doc.lower(),f"Tier3 Level0 docs missing {token}")

if errors:
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 build Level 0 definition: PASS")
print("nodes=12")
print("state="+m["state"])
print("execution_authorized="+str(m.get("execution_authorized")).lower())
print("attempt2=9-success/3-fail round2-remediation=3-nodes")

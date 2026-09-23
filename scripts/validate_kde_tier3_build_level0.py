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
round3={"kjobwidgets","kwallet"}
round3_source={"kjobwidgets"}
round4={"kwallet"}

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
    elif node_id=="kwallet" and m.get("active_remediation",{}).get("round") in {2,3,4}:
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

# Historical attempts 1-3 are retained with zero canonical promotion.
history=a.get("campaign_history",[])
req(len(history)>=5,"Level0 campaign history contains attempts 1 through 5")
attempt1=next((x for x in history if x.get("attempt")==1),{})
attempt2=next((x for x in history if x.get("attempt")==2),{})
attempt3=next((x for x in history if x.get("attempt")==3),{})
attempt4=next((x for x in history if x.get("attempt")==4),{})
attempt5=next((x for x in history if x.get("attempt")==5),{})
req(attempt1.get("workflow_run")==35755924197 and attempt1.get("workflow_jobs")=={"success":7,"fail":5},"Level0 attempt1 history")
req(attempt2.get("workflow_run")==35770505868 and attempt2.get("commit")=="b381031bd9bbd7ea5b1d9a1ed3739766588be78e","Level0 attempt2 history")
req(attempt2.get("workflow_jobs")=={"success":9,"fail":3} and attempt2.get("canonical_promotions")==0,"Level0 attempt2 summary")
req(attempt2.get("rootfs",{}).get("artifact_id")==10714370160 and attempt2.get("rootfs",{}).get("artifact_sha256")=="5e84adbad7e684010eefad73daff28fae7f894a325ec03d744b934558a6de4ea","Level0 attempt2 rootfs evidence")
req(attempt3.get("workflow_run")==35808764577 and attempt3.get("commit")=="417444e60bd09887383fdc4ef5f1c1f3df1efc09","Level0 attempt3 history")
req(attempt3.get("workflow_jobs")=={"success":10,"fail":2} and attempt3.get("canonical_promotions")==0,"Level0 attempt3 summary")
req(attempt3.get("rootfs",{}).get("artifact_id")==10728279487 and attempt3.get("rootfs",{}).get("artifact_sha256")=="a4f7401427fb642afcb201142a7746874ab4db6c18d1aa90a4edc10c54ca86e5","Level0 attempt3 rootfs evidence")
req(attempt4.get("workflow_run")==35813710318 and attempt4.get("commit")=="01bbc2b6df1621e17b2cdf6c65ebfb0f13063c79","Level0 attempt4 history")
req(attempt4.get("workflow_jobs")=={"success":11,"fail":1} and attempt4.get("canonical_promotions")==0,"Level0 attempt4 summary")
req(attempt4.get("rootfs",{}).get("artifact_id")==10730427348 and attempt4.get("rootfs",{}).get("artifact_sha256")=="7378d328afb430a2a1211764e705b0343187fe67ae3b1c098653a3d3f51318e7","Level0 attempt4 rootfs evidence")
req(attempt5.get("workflow_run")==35818120201 and attempt5.get("commit")=="0599266fd5fc9869002629b3778d71f1e76bbdc1","Level0 attempt5 history")
req(attempt5.get("workflow_jobs")=={"success":12,"fail":0} and attempt5.get("canonical_promotions")==11,"Level0 attempt5 summary")
req(attempt5.get("runtime_pending")==["knewstuff"],"Level0 attempt5 runtime-pending set")
req(attempt5.get("rootfs",{}).get("artifact_id")==10732192564 and attempt5.get("rootfs",{}).get("artifact_sha256")=="e1c05fd6b5b486d51e79cffa9c32160dcf39d7bc10ed7e338fa286e8b6b39573","Level0 attempt5 rootfs artifact")
req(attempt5.get("rootfs",{}).get("rootfs_sha256")=="596e8d8a8865276f6bc1c4e53476485fc991a5cb6e76c4269b625486f278b349","Level0 attempt5 rootfs SHA")

expected2={
    "kbookmarks":"PASS","kconfigwidgets":"PASS","kdav":"PASS","kdesu":"PASS",
    "kiconthemes":"FAIL","kjobwidgets":"FAIL","knewstuff":"RUNTIME_PENDING",
    "kpeople":"PASS","krunner":"PASS","ksvg":"PASS","ktextwidgets":"PASS","kwallet":"FAIL",
}
expected3={
    "kbookmarks":"PASS","kconfigwidgets":"PASS","kdav":"PASS","kdesu":"PASS",
    "kiconthemes":"PASS","kjobwidgets":"FAIL","knewstuff":"RUNTIME_PENDING",
    "kpeople":"PASS","krunner":"PASS","ksvg":"PASS","ktextwidgets":"PASS","kwallet":"FAIL",
}
expected4={
    "kbookmarks":"PASS","kconfigwidgets":"PASS","kdav":"PASS","kdesu":"PASS",
    "kiconthemes":"PASS","kjobwidgets":"PASS","knewstuff":"RUNTIME_PENDING",
    "kpeople":"PASS","krunner":"PASS","ksvg":"PASS","ktextwidgets":"PASS","kwallet":"FAIL",
}
expected5={
    "kbookmarks":"PASS","kconfigwidgets":"PASS","kdav":"PASS","kdesu":"PASS",
    "kiconthemes":"PASS","kjobwidgets":"PASS","knewstuff":"RUNTIME_PENDING",
    "kpeople":"PASS","krunner":"PASS","ksvg":"PASS","ktextwidgets":"PASS","kwallet":"PASS",
}
for attempt_no,workflow_run,expected_results in ((2,35770505868,expected2),(3,35808764577,expected3),(4,35813710318,expected4),(5,35818120201,expected5)):
    for node_id,result in expected_results.items():
        entries=a["nodes"][node_id]
        e=next((x for x in entries if x.get("attempt")==attempt_no),{})
        req(bool(e),f"{node_id}: attempt{attempt_no} ledger entry")
        req(e.get("workflow_run")==workflow_run,f"{node_id}: attempt{attempt_no} workflow")
        req(e.get("package_attempted") is True,f"{node_id}: attempt{attempt_no} real package attempt")
        req(e.get("result")==result,f"{node_id}: attempt{attempt_no} result")
        req(isinstance(e.get("artifact_id"),int) and len(e.get("artifact_sha256",""))==64,f"{node_id}: attempt{attempt_no} artifact evidence")

knew3=next((x for x in a["nodes"]["knewstuff"] if x.get("attempt")==3),{})
req(knew3.get("downstream_eligible") is False and knew3.get("deferred_runtime_validation")==["kcmutils"],"KNewStuff attempt3 remains runtime-pending")
ki3=next((x for x in a["nodes"]["kiconthemes"] if x.get("attempt")==3),{})
req(ki3.get("remediation_validation")=="round2 PASS" and ki3.get("tests")=="10/10 PASS","KIconThemes round2 remediation validated by attempt3")
for node_id in round3:
    e=next((x for x in a["nodes"][node_id] if x.get("attempt")==3),{})
    req(isinstance(e.get("cause"),str) and isinstance(e.get("remediation"),str),f"{node_id}: attempt3 root cause/remediation recorded")
knew4=next((x for x in a["nodes"]["knewstuff"] if x.get("attempt")==4),{})
req(knew4.get("downstream_eligible") is False and knew4.get("deferred_runtime_validation")==["kcmutils"],"KNewStuff attempt4 remains runtime-pending")
kj4=next((x for x in a["nodes"]["kjobwidgets"] if x.get("attempt")==4),{})
req(kj4.get("result")=="PASS" and kj4.get("remediation_validation")=="round3 PASS" and kj4.get("tests")=="3/3 PASS","KJobWidgets round3 remediation validated by attempt4")
kw4=next((x for x in a["nodes"]["kwallet"] if x.get("attempt")==4),{})
req(kw4.get("result")=="FAIL" and kw4.get("failure_stage")=="lintian/symbols","KWallet attempt4 symbols failure recorded")
req(isinstance(kw4.get("cause"),str) and isinstance(kw4.get("remediation"),str),"KWallet attempt4 root cause/remediation recorded")
knew5=next((x for x in a["nodes"]["knewstuff"] if x.get("attempt")==5),{})
req(knew5.get("result")=="RUNTIME_PENDING" and knew5.get("downstream_eligible") is False and knew5.get("tests")=="5/5 PASS","KNewStuff attempt5 runtime-pending evidence")
kw5=next((x for x in a["nodes"]["kwallet"] if x.get("attempt")==5),{})
req(kw5.get("result")=="PASS" and kw5.get("tests")=="3/3 PASS" and kw5.get("artifact_id")==10732233019,"KWallet round4 remediation validated by attempt5")

if m.get("state")=="active-pending-ci":
    req(m.get("execution_authorized") is True,"Level0 execution authorization")
    req(mat.get("state")=="PASS","active Level0 requires materialization PASS")
    activation=m.get("activation",{})
    req(activation.get("status")=="ACTIVE","Level0 activation status")
    req(activation.get("scope")=="full-level0-rerun-12-nodes","Level0 full rerun scope")
    rem=m.get("active_remediation",{})
    attempt=m.get("current_attempt")
    if attempt==5:
        req(activation.get("attempt")==5,"Level0 attempt5 activation number")
        req(activation.get("promotion_validation_workflow_run")==35817928654,"Level0 attempt5 promotion validation")
        req(activation.get("promotion_commit")=="3b1387b636a7103ca8918e51836ea7ac9e105be5","Level0 attempt5 promotion commit")
        req(rem.get("round")==4 and rem.get("status")=="level0-rerun-active","Level0 attempt5 active remediation")
        req(rem.get("execution_authorized") is True and rem.get("current_attempt")==5,"Level0 attempt5 remediation authorization")
        req(rem.get("activation_policy_workflow_run")==35817928654,"Level0 attempt5 remediation validation")
        req(rem.get("next_gate")=="tier3-build-level0-attempt5","Level0 attempt5 next gate")
        req(all(m["nodes"][n].get("current_attempt")==5 for n in expected),"Level0 attempt5 node markers")
        req(m["nodes"]["kwallet"].get("state")=="remediation-pending-build","KWallet runnable in attempt5")
        req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n!="kwallet"),"non-round4 nodes revalidated in attempt5")
        req(m["nodes"]["kwallet"].get("package_version")=="6.30.0-0supralinux4","KWallet attempt5 revision")
        req(m["nodes"]["kwallet"].get("materialization",{}).get("workflow_run")==35817654811,"KWallet attempt5 source pin")
        req("karchive" in m["nodes"]["kwallet"].get("retained_input_ids",[]),"KWallet attempt5 KArchive provider closure")
        req(m["nodes"]["kwallet"].get("support_input_ids")==["kdoctools"],"KWallet attempt5 KDocTools support")
    elif attempt==4:
        req(activation.get("attempt")==4,"Level0 attempt4 activation number")
        req(activation.get("promotion_validation_workflow_run")==35813396247,"Level0 attempt4 promotion validation")
        req(activation.get("promotion_commit")=="48abcd1ed74e8d83c9c256ddc491218e102d66cf","Level0 attempt4 promotion commit")
        req(rem.get("round")==3 and rem.get("status")=="level0-rerun-active","Level0 attempt4 active remediation")
        req(rem.get("execution_authorized") is True and rem.get("current_attempt")==4,"Level0 attempt4 remediation authorization")
        req(rem.get("activation_policy_workflow_run")==35813396247,"Level0 attempt4 remediation validation")
        req(rem.get("next_gate")=="tier3-build-level0-attempt4","Level0 attempt4 next gate")
        req(all(m["nodes"][n].get("current_attempt")==4 for n in expected),"Level0 attempt4 node markers")
        req(all(m["nodes"][n].get("state")=="remediation-pending-build" for n in round3),"round3 nodes runnable in attempt4")
        req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in round3),"non-round3 nodes revalidated in attempt4")
        req(m["nodes"]["kjobwidgets"].get("package_version")=="6.30.0-0supralinux4","KJobWidgets attempt4 revision")
        req(m["nodes"]["kjobwidgets"].get("materialization",{}).get("workflow_run")==35812918054,"KJobWidgets attempt4 source pin")
        req(m["nodes"]["kwallet"].get("package_version")=="6.30.0-0supralinux3","KWallet attempt4 source unchanged")
        req("karchive" in m["nodes"]["kwallet"].get("retained_input_ids",[]),"KWallet attempt4 KArchive provider closure")
        req(m["nodes"]["kwallet"].get("support_input_ids")==["kdoctools"],"KWallet attempt4 KDocTools support")
        correction=m.get("orchestration_correction",{})
        req(correction.get("status")=="closed-corrected" and correction.get("corrected_workflow_run")==35808764577 and correction.get("corrected_matrix_nodes")==12,"Level0 corrected full-rerun orchestration retained")
    elif attempt==3:
        req(activation.get("attempt")==3,"Level0 attempt3 activation number")
        req(activation.get("promotion_validation_workflow_run")==35807934729,"Level0 attempt3 promotion validation")
        req(activation.get("promotion_commit")=="13c825b94e9c9c7de5d8ce8baf4c1631a5cd1f6e","Level0 attempt3 promotion commit")
        req(rem.get("round")==2 and rem.get("status")=="level0-rerun-active","Level0 attempt3 active remediation")
        req(rem.get("execution_authorized") is True and rem.get("current_attempt")==3,"Level0 attempt3 remediation authorization")
        req(rem.get("activation_policy_workflow_run")==35807934729,"Level0 attempt3 remediation validation")
        req(rem.get("next_gate")=="tier3-build-level0-attempt3","Level0 attempt3 next gate")
        req(all(m["nodes"][n].get("current_attempt")==3 for n in expected),"Level0 attempt3 node markers")
    else:
        req(False,"unsupported active Level0 attempt")

elif m.get("state")=="remediation-materialized-pending-activation":
    req(m.get("execution_authorized") is False,"Level0 remains paused before activation")
    req(mat.get("state")=="PASS","remediation materialization promoted PASS")
    rem=m.get("active_remediation",{})
    if rem.get("round")==4:
        req(rem.get("status")=="materialization-PASS-pending-activation","Level0 round4 promotion state")
        req(rem.get("materialization_workflow_run")==35817654811,"Level0 round4 materialization run")
        req(rem.get("materialization_commit")=="1a9a4ba82b4aac9f1df9f6457faef8b905dd17cf","Level0 round4 materialization commit")
        req(rem.get("full_level0_rerun_required") is True,"attempt5 full rerun policy")
        req(rem.get("next_gate")=="tier3-build-level0-attempt5-activation-validation","attempt5 activation validation gate")
        req(m["nodes"]["kwallet"].get("state")=="remediation-pending-build","KWallet ready for attempt5")
        req(m["nodes"]["kwallet"].get("package_version")=="6.30.0-0supralinux4","KWallet promoted round4 revision")
        req(m["nodes"]["kwallet"].get("materialization",{}).get("workflow_run")==35817654811,"KWallet promoted round4 materialization")
        req(m["nodes"]["kwallet"].get("materialization")==p["nodes"]["kwallet"].get("materialization"),"KWallet campaign pin refreshed")
        req(m["nodes"]["kwallet"].get("support_input_ids")==["kdoctools"],"KWallet KDocTools support retained for attempt5")
        req("karchive" in m["nodes"]["kwallet"].get("retained_input_ids",[]),"KWallet KArchive provider closure retained for attempt5")
        req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in round4),"other Level0 nodes await attempt5 revalidation")
    elif rem.get("round")==3:
        req(rem.get("status")=="materialization-PASS-pending-activation","Level0 round3 promotion state")
        req(rem.get("materialization_workflow_run")==35812918054,"Level0 round3 materialization run")
        req(rem.get("materialization_commit")=="a57c13059dfc206ddf57390e1cd0cfd280471965","Level0 round3 materialization commit")
        req(rem.get("full_level0_rerun_required") is True,"attempt4 full rerun policy")
        req(rem.get("next_gate")=="tier3-build-level0-attempt4-activation-validation","attempt4 activation validation gate")
        req(m["nodes"]["kjobwidgets"].get("state")=="remediation-pending-build","KJobWidgets ready for attempt4")
        req(m["nodes"]["kjobwidgets"].get("package_version")=="6.30.0-0supralinux4","KJobWidgets promoted round3 revision")
        req(m["nodes"]["kjobwidgets"].get("materialization",{}).get("workflow_run")==35812918054,"KJobWidgets promoted round3 materialization")
        req(m["nodes"]["kjobwidgets"].get("materialization")==p["nodes"]["kjobwidgets"].get("materialization"),"KJobWidgets campaign pin refreshed")
        req(m["nodes"]["kwallet"].get("state")=="remediation-pending-build" and m["nodes"]["kwallet"].get("package_version")=="6.30.0-0supralinux3","KWallet closure-only remediation ready")
        req("karchive" in m["nodes"]["kwallet"].get("retained_input_ids",[]),"KWallet KArchive provider closure retained")
        req(m["nodes"]["kwallet"].get("support_input_ids")==["kdoctools"],"KWallet KDocTools support retained for attempt4")
        req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in round3),"other Level0 nodes await attempt4 revalidation")
    else:
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

elif m.get("state")=="PARTIAL":
    req(m.get("execution_authorized") is False,"Level0 closed execution after Attempt5")
    req(m.get("current_attempt")==5,"Level0 closed on attempt5")
    summary=m.get("attempt5_summary",{})
    req(summary.get("workflow_run")==35818120201 and summary.get("workflow_jobs")=={"success":12,"fail":0},"Level0 Attempt5 summary linkage")
    expected_pass={"kbookmarks","kconfigwidgets","kdav","kdesu","kiconthemes","kjobwidgets","kpeople","krunner","ksvg","ktextwidgets","kwallet"}
    req(set(summary.get("pass",[]))==expected_pass and summary.get("runtime_pending")==["knewstuff"] and summary.get("canonical_promotions")==11,"Level0 Attempt5 canonical transition summary")
    req(all(m["nodes"][n].get("state")=="PASS" for n in expected_pass),"Level0 promoted node states")
    req(m["nodes"]["knewstuff"].get("state")=="runtime-validation-required","KNewStuff remains runtime-validation-required")
    req(all(m["nodes"][n].get("pass_evidence",{}).get("result")=="PASS" and m["nodes"][n].get("pass_evidence",{}).get("downstream_eligible") is True for n in expected_pass),"Level0 promoted PASS evidence")
    req(m["nodes"]["knewstuff"].get("pass_evidence",{}).get("result")=="RUNTIME_PENDING" and m["nodes"]["knewstuff"].get("pass_evidence",{}).get("downstream_eligible") is False,"KNewStuff retained build evidence")
    req(t.get("discovery_policy",{}).get("phase") in {"build-level1-planning","build-level1"},"Tier3 Level1 phase after Level0")
    req(t.get("discovery_policy",{}).get("package_builds") in {"tier3-level1-not-authorized-before-planning","tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation","tier3-level1-authorized","tier3-level1-remediation-pending-provider-closure"},"Tier3 Level1 build gate")
    ar=t.get("active_remediation",{})
    if ar.get("round")==8:
        req(ar.get("level")=="build-level1" and ar.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level1-planning-validation"},"Tier3 Level1 round8 source-remediation lifecycle")
        req(set(ar.get("nodes",[]))=={"kio","kxmlgui"} and ar.get("source_materialization_nodes")==["kio","kxmlgui"] and ar.get("provider_closure_only_nodes")==[],"Tier3 Level1 round8 source scope")
        req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"},"Tier3 Level1 round8 revisions")
        req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 Level1 round8 execution pause")
        req(ar.get("validation_workflow_run")==35887558758 and ar.get("validation_commit")=="7583ba2ffcf7f91a1ea061c2e8c0cecd9f031d94","Tier3 Level1 Attempt3 evidence")
        req(set(ar.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and ar.get("canonical_promotions")==0,"Tier3 Level1 Attempt3 failure/no-promotion semantics")
        req(ar.get("current_attempt")==3 and ar.get("next_attempt")==4,"Tier3 Level1 round8 attempt markers")
        if t.get("discovery_policy",{}).get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(ar.get("materialization_workflow_run")==35894317888 and ar.get("materialization_commit")=="65f5ba76a913e7acf619eb9fee86e878e2914415","Tier3 Level1 round8 materialization evidence")
            req(ar.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 Level1 round8 planning-validation gate")
        else:
            req(ar.get("next_gate")=="tier3-round8-level1-materialization","Tier3 Level1 round8 materialization gate")
        hist4=[x for x in t.get("remediation_history",[]) if x.get("round")==4]
        req(len(hist4)==1 and hist4[0].get("status")=="attempt5-complete" and hist4[0].get("canonical_promotions")==11,"Tier3 Attempt5 closure retained while Level1 round8 remediates")
    elif ar.get("round")==7:
        req(ar.get("level")=="build-level1" and ar.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level1-planning-validation","level1-active-pending-ci"},"Tier3 Level1 round7 source-remediation lifecycle")
        req(set(ar.get("nodes",[]))=={"kio","kxmlgui"} and ar.get("source_materialization_nodes")==["kio","kxmlgui"] and ar.get("provider_closure_only_nodes")==[],"Tier3 Level1 round7 source scope")
        req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux3","kxmlgui":"6.30.0-0supralinux2"},"Tier3 Level1 round7 revisions")
        if t.get("discovery_policy",{}).get("package_builds")!="tier3-level1-authorized":
            req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 Level1 round7 execution pause")
        req(ar.get("validation_workflow_run")==35829170695 and ar.get("validation_commit")=="897d3a864bc7ea164400c7d9de2e9c51cf6316ab","Tier3 Level1 Attempt2 evidence")
        req(set(ar.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and ar.get("canonical_promotions")==0,"Tier3 Level1 Attempt2 failure/no-promotion semantics")
        if t.get("discovery_policy",{}).get("package_builds")=="tier3-level1-authorized":
            req(ar.get("status")=="level1-active-pending-ci" and ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True,"Tier3 Level1 Attempt3 active authorization")
            req(ar.get("current_attempt")==3 and ar.get("activation_policy_workflow_run")==35884583361 and ar.get("activation_level1_workflow_run")==35884584590,"Tier3 Level1 Attempt3 validation evidence")
            req(ar.get("activation_commit")=="a562a145ba212349d725fad3e98a9dcb9c6c2ae0" and ar.get("next_gate")=="tier3-build-level1-attempt3","Tier3 Level1 Attempt3 activation gate")
        elif t.get("discovery_policy",{}).get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(ar.get("materialization_workflow_run")==35882795135 and ar.get("materialization_commit")=="0d6c02f3f8dc41f716ba62ee7121f56371a8dc91","Tier3 Level1 round7 materialization evidence")
            req(ar.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 Level1 round7 planning-validation gate")
        else:
            req(ar.get("next_gate")=="tier3-round7-level1-materialization","Tier3 Level1 round7 next gate")
        hist4=[x for x in t.get("remediation_history",[]) if x.get("round")==4]
        req(len(hist4)==1 and hist4[0].get("status")=="attempt5-complete" and hist4[0].get("canonical_promotions")==11,"Tier3 Attempt5 closure retained while Level1 remediates")
    elif ar.get("round")==6:
        req(ar.get("level")=="build-level1" and ar.get("status") in {"provider-closure-pending-attempt2-activation-validation","level1-active-pending-ci"},"Tier3 Level1 round6 provider closure lifecycle")
        req(set(ar.get("nodes",[]))=={"kio","kxmlgui"} and ar.get("source_materialization_nodes")==[] and set(ar.get("provider_closure_only_nodes",[]))=={"kio","kxmlgui"},"Tier3 Level1 round6 closure-only scope")
        req(ar.get("provider_closure_inputs")=={"kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"]},"Tier3 Level1 round6 complete provider closure")
        req(ar.get("validation_result")=="2 raw workflow FAIL / 0 canonical FAIL" and ar.get("remaining_failed_nodes")==[] and ar.get("canonical_failures")==0,"Tier3 Level1 round6 no current FAIL")
        if t.get("discovery_policy",{}).get("package_builds")=="tier3-level1-authorized":
            req(ar.get("status")=="level1-active-pending-ci" and ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True,"Tier3 Level1 Attempt2 active authorization")
            req(ar.get("current_attempt")==2 and ar.get("activation_policy_workflow_run")==35828634884 and ar.get("activation_level1_workflow_run")==35828634887,"Tier3 Level1 Attempt2 validation evidence")
            req(ar.get("next_gate")=="tier3-build-level1-attempt2","Tier3 Level1 Attempt2 gate")
        else:
            req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False and ar.get("next_attempt")==2,"Tier3 Level1 round6 execution pause")
            req(ar.get("next_gate")=="tier3-build-level1-attempt2-activation-validation","Tier3 Level1 round6 next gate")
    elif ar.get("round")==5:
        req(ar.get("level")=="build-level1-preflight" and ar.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level1-planning-validation","level1-active-pending-ci"},"Tier3 Level1 KIO preflight remediation")
        req(ar.get("nodes")==["kio"] and ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2"},"Tier3 Level1 KIO remediation scope")
        if t.get("discovery_policy",{}).get("package_builds")=="tier3-level1-authorized":
            req(ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True and ar.get("current_attempt")==1,"Tier3 Level1 execution active")
        else:
            req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 Level1 execution remains paused")
        hist=[x for x in t.get("remediation_history",[]) if x.get("round")==4]
        req(len(hist)==1 and hist[0].get("status")=="attempt5-complete" and hist[0].get("canonical_promotions")==11,"Tier3 Attempt5 closure retained in history")
    else:
        req(ar.get("status")=="attempt5-complete" and ar.get("execution_authorized") is False,"Tier3 Attempt5 closure state")
        req(ar.get("validation_workflow_run")==35818120201 and ar.get("canonical_promotions")==11 and ar.get("runtime_pending_nodes")==["knewstuff"],"Tier3 Attempt5 closure evidence")
        req(ar.get("next_gate")=="tier3-build-level1-planning","Tier3 Level1 planning gate")
    for n in expected_pass:
        req(dag.get("nodes",{}).get(n,{}).get("tier")==3 and dag["nodes"][n].get("state")=="PASS" and dag["nodes"][n].get("downstream_eligible") is True,f"{n}: promoted Tier3 DAG PASS")
    req("knewstuff" not in dag.get("nodes",{}),"KNewStuff must not enter DAG before runtime validation")
elif m.get("state")=="remediation-pending-materialization":
    req(m.get("execution_authorized") is False,"Level0 execution paused during remediation")
    req(mat.get("state")=="remediation-pending-ci","Level0 remediation requires selective materialization")
    rem=m.get("active_remediation",{})
    if rem.get("round")==4:
        req(set(rem.get("nodes",[]))==round4,"Level0 round4 failure set")
        req(rem.get("queue")==["kwallet"] and rem.get("source_materialization_nodes")==["kwallet"],"Level0 round4 source queue")
        req(rem.get("provider_closure_only_nodes")==[],"Level0 round4 provider-closure-only set")
        req(rem.get("candidate_package_versions")=={"kwallet":"6.30.0-0supralinux4"},"Level0 round4 candidate version")
        req(rem.get("trigger_workflow_run")==35813710318 and rem.get("trigger_commit")=="01bbc2b6df1621e17b2cdf6c65ebfb0f13063c79","Level0 round4 trigger evidence")
        req(rem.get("full_level0_rerun_required") is True,"Level0 round4 full rerun policy")
        req(m["nodes"]["kwallet"].get("state")=="remediation-pending-materialization","KWallet awaits round4 rematerialization")
        req(m["nodes"]["kwallet"].get("previous_package_version")=="6.30.0-0supralinux3","KWallet round4 previous revision")
        req(m["nodes"]["kwallet"].get("candidate_package_version")=="6.30.0-0supralinux4","KWallet round4 candidate revision")
        req(m["nodes"]["kwallet"].get("support_input_ids")==["kdoctools"],"KWallet round4 KDocTools support retained")
        req("karchive" in m["nodes"]["kwallet"].get("retained_input_ids",[]),"KWallet round4 KArchive closure retained")
        req(m["nodes"]["kwallet"].get("symbol_remediation",{}).get("symbol")=="_ZSt19piecewise_construct@Base","KWallet round4 symbol remediation model")
        req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in round4),"attempt4 non-failing nodes await full revalidation")
        summary=m.get("attempt4_summary",{})
        req(summary.get("workflow_run")==35813710318 and summary.get("workflow_jobs")=={"success":11,"fail":1},"Level0 attempt4 summary linkage")
        req(set(summary.get("job_fail",[]))==round4 and summary.get("canonical_promotions")==0,"Level0 attempt4 fail/promotion semantics")
    elif rem.get("round")==3:
        req(set(rem.get("nodes",[]))==round3,"Level0 round3 failure set")
        req(rem.get("queue")==["kjobwidgets"] and rem.get("source_materialization_nodes")==["kjobwidgets"],"Level0 round3 source queue")
        req(rem.get("provider_closure_only_nodes")==["kwallet"],"Level0 round3 provider-closure-only set")
        req(rem.get("candidate_package_versions")=={"kjobwidgets":"6.30.0-0supralinux4","kwallet":"6.30.0-0supralinux3"},"Level0 round3 candidate versions")
        req(rem.get("trigger_workflow_run")==35808764577 and rem.get("trigger_commit")=="417444e60bd09887383fdc4ef5f1c1f3df1efc09","Level0 round3 trigger evidence")
        req(rem.get("full_level0_rerun_required") is True,"Level0 round3 full rerun policy")
        req(m["nodes"]["kjobwidgets"].get("state")=="remediation-pending-materialization","KJobWidgets awaits round3 rematerialization")
        req(m["nodes"]["kjobwidgets"].get("previous_package_version")=="6.30.0-0supralinux3","KJobWidgets round3 previous revision")
        req(m["nodes"]["kjobwidgets"].get("candidate_package_version")=="6.30.0-0supralinux4","KJobWidgets round3 candidate revision")
        req(m["nodes"]["kwallet"].get("state")=="remediation-pending-build" and m["nodes"]["kwallet"].get("package_version")=="6.30.0-0supralinux3","KWallet round3 source unchanged")
        req("karchive" in m["nodes"]["kwallet"].get("retained_input_ids",[]),"KWallet round3 KArchive retained closure")
        req(m["nodes"]["kwallet"].get("support_input_ids")==["kdoctools"],"KWallet round3 KDocTools support retained")
        closure=m["nodes"]["kwallet"].get("package_closure_remediation",{})
        req(closure.get("provider")=="kdoctools" and closure.get("added_retained_input")=="karchive","KWallet round3 provider closure model")
        req(closure.get("source_rematerialization_required") is False,"KWallet round3 no source rematerialization")
        req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in round3),"attempt3 non-failing nodes await full revalidation")
        summary=m.get("attempt3_summary",{})
        req(summary.get("workflow_run")==35808764577 and summary.get("workflow_jobs")=={"success":10,"fail":2},"Level0 attempt3 summary linkage")
        req(set(summary.get("job_fail",[]))==round3 and summary.get("canonical_promotions")==0,"Level0 attempt3 fail/promotion semantics")
        correction=m.get("orchestration_correction",{})
        req(correction.get("status")=="closed-corrected" and correction.get("corrected_workflow_run")==35808764577 and correction.get("corrected_matrix_nodes")==12,"Level0 attempt3 orchestration correction closed")
    else:
        req(rem.get("round")==2 and set(rem.get("queue",[]))==round2,"Level0 round2 remediation queue")
        req(rem.get("candidate_package_version")=="6.30.0-0supralinux3","Level0 round2 candidate revision")
        req(rem.get("trigger_workflow_run")==35770505868,"Level0 round2 trigger run")
        req(rem.get("full_level0_rerun_required") is True,"Level0 round2 full rerun policy")
        req(all(m["nodes"][n].get("state")=="remediation-pending-materialization" for n in round2),"round2 failed nodes await rematerialization")
        req(all(m["nodes"][n].get("state")=="prepared-pending-revalidation" for n in expected if n not in round2),"attempt2 non-failing nodes await revalidation")

policy=t.get("discovery_policy",{})
req(policy.get("phase") in {"build-level0","build-level1-planning","build-level1"},"canonical Tier3 Level0/post-Level0 phase")
if m.get("state")=="remediation-pending-materialization":
    req(policy.get("package_builds")=="tier3-level0-remediation-pending","canonical Tier3 remediation build gate")
    ar=t.get("active_remediation",{})
    if ar.get("round")==4:
        req(set(ar.get("nodes",[]))==round4,"canonical Tier3 round4 remediation linkage")
        req(ar.get("source_materialization_nodes")==["kwallet"] and ar.get("provider_closure_only_nodes")==[],"canonical Tier3 round4 remediation classes")
        req(ar.get("candidate_package_versions")=={"kwallet":"6.30.0-0supralinux4"},"canonical Tier3 round4 version")
        req(ar.get("trigger_workflow_run")==35813710318 and ar.get("execution_authorized") is False,"canonical Tier3 round4 execution pause")
        req(ar.get("next_gate")=="tier3-round4-kwallet-materialization","canonical Tier3 round4 next gate")
    elif ar.get("round")==3:
        req(set(ar.get("nodes",[]))==round3,"canonical Tier3 round3 remediation linkage")
        req(ar.get("source_materialization_nodes")==["kjobwidgets"] and ar.get("provider_closure_only_nodes")==["kwallet"],"canonical Tier3 round3 remediation classes")
        req(ar.get("candidate_package_versions")=={"kjobwidgets":"6.30.0-0supralinux4","kwallet":"6.30.0-0supralinux3"},"canonical Tier3 round3 versions")
        req(ar.get("trigger_workflow_run")==35808764577 and ar.get("execution_authorized") is False,"canonical Tier3 round3 execution pause")
        req(ar.get("next_gate")=="tier3-round3-kjobwidgets-materialization","canonical Tier3 round3 next gate")
    else:
        req(ar.get("round")==2 and set(ar.get("nodes",[]))==round2,"canonical Tier3 round2 remediation linkage")
        req(ar.get("candidate_package_version")=="6.30.0-0supralinux3","canonical Tier3 round2 revision")
        req(ar.get("execution_authorized") is False,"canonical Tier3 round2 execution pause")
elif m.get("state")=="active-pending-ci":
    req(policy.get("package_builds")=="tier3-level0-authorized","canonical Tier3 active Level0 build gate")
    ar=t.get("active_remediation",{})
    if m.get("current_attempt")==5:
        req(ar.get("round")==4 and set(ar.get("nodes",[]))==round4,"canonical Tier3 attempt5 remediation linkage")
        req(ar.get("status")=="level0-rerun-active" and ar.get("execution_authorized") is True,"canonical Tier3 attempt5 authorization")
        req(ar.get("current_attempt")==5 and ar.get("activation_policy_workflow_run")==35817928654,"canonical Tier3 attempt5 activation evidence")
        req(ar.get("next_gate")=="tier3-build-level0-attempt5","canonical Tier3 attempt5 next gate")
    elif m.get("current_attempt")==4:
        req(ar.get("round")==3 and set(ar.get("nodes",[]))==round3,"canonical Tier3 attempt4 remediation linkage")
        req(ar.get("status")=="level0-rerun-active" and ar.get("execution_authorized") is True,"canonical Tier3 attempt4 authorization")
        req(ar.get("current_attempt")==4 and ar.get("activation_policy_workflow_run")==35813396247,"canonical Tier3 attempt4 activation evidence")
        req(ar.get("next_gate")=="tier3-build-level0-attempt4","canonical Tier3 attempt4 next gate")
    else:
        req(ar.get("round")==2 and set(ar.get("nodes",[]))==round2,"canonical Tier3 attempt3 remediation linkage")
        req(ar.get("status")=="level0-rerun-active" and ar.get("execution_authorized") is True,"canonical Tier3 attempt3 authorization")
        req(ar.get("current_attempt")==3 and ar.get("activation_policy_workflow_run")==35807934729,"canonical Tier3 attempt3 activation evidence")
        req(ar.get("next_gate")=="tier3-build-level0-attempt3","canonical Tier3 attempt3 next gate")
else:
    req(policy.get("package_builds") in {"tier3-level0-authorized","tier3-level0-remediation-pending","tier3-level1-not-authorized-before-planning","tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation","tier3-level1-authorized","tier3-level1-remediation-pending-provider-closure"},"canonical Tier3 build gate")
    if m.get("state")=="PARTIAL":
        req(policy.get("phase") in {"build-level1-planning","build-level1"} and policy.get("package_builds") in {"tier3-level1-not-authorized-before-planning","tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation","tier3-level1-authorized","tier3-level1-remediation-pending-provider-closure"},"canonical Tier3 post-Level0 gate")
    elif m.get("state")=="remediation-materialized-pending-activation":
        ar=t.get("active_remediation",{})
        if ar.get("round")==4:
            req(policy.get("package_builds")=="tier3-level0-remediation-pending","canonical Tier3 attempt5 remains paused")
            req(ar.get("status")=="materialization-PASS-pending-level0-attempt5-activation","canonical Tier3 round4 promoted state")
            req(ar.get("execution_authorized") is False and ar.get("next_gate")=="tier3-build-level0-attempt5-activation-validation","canonical Tier3 attempt5 activation gate")
        elif ar.get("round")==3:
            req(policy.get("package_builds")=="tier3-level0-remediation-pending","canonical Tier3 attempt4 remains paused")
            req(ar.get("status")=="materialization-PASS-pending-level0-attempt4-activation","canonical Tier3 round3 promoted state")
            req(ar.get("execution_authorized") is False and ar.get("next_gate")=="tier3-build-level0-attempt4-activation-validation","canonical Tier3 attempt4 activation gate")

req(t.get("support_components",{}).get("next_gate") in {"tier3-build-level0","tier3-build-level1-planning","tier3-build-level1"},"canonical Tier3 next gate")
req(t.get("build_level0_manifest")=="manifests/kde-tier3-build-level0.json","canonical Tier3 Level0 manifest linkage")

for path in (
    "scripts/plan-kde-tier3-build-level0.py",
    "scripts/run-kde-tier3-build-level0.sh",
    ".github/workflows/kde-tier3-build-level0.yml",
    "docs/kde-tier3-build-level0.md",
):
    req((ROOT/path).exists(),f"missing Tier3 Level0 component: {path}")

doc=(ROOT/"docs/kde-tier3-build-level0.md").read_text()
for token in ("12","FAIL","BLOCKED","KNewStuff","KCMUtils","attempt 3","round 3","stable"):
    req(token.lower() in doc.lower(),f"Tier3 Level0 docs missing {token}")

if errors:
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 build Level 0 definition: PASS")
print("nodes=12")
print("state="+m["state"])
print("execution_authorized="+str(m.get("execution_authorized")).lower())
print("attempt5=12-success/0-fail canonical-pass=11 runtime-pending=1 next=level1-planning")

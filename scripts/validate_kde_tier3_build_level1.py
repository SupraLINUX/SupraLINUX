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
req(m.get("state") in {"planned-pending-activation","active-pending-ci","remediation-pending-activation","remediation-pending-materialization","remediation-materialized-pending-planning-validation","PARTIAL","PASS"},"Level1 lifecycle")
req(m.get("selected_nodes")==["kio","kxmlgui"],"Level1 node set")
req(m.get("build_campaign_manifest")=="manifests/kde-tier3-build-campaign.json","Level1 campaign link")
req(m.get("materialization_manifest")=="manifests/kde-tier3-materialization.json","Level1 materialization link")
req(m.get("level0_manifest")=="manifests/kde-tier3-build-level0.json","Level1 Level0 link")
req(m.get("attempt_ledger")=="manifests/kde-tier3-build-level1-attempts.json","Level1 attempt ledger link")
req(m.get("canonical_snapshot")=="11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED","Level1 canonical pre-build snapshot")
req(m.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")
req("provider-closure-artifact-validation" in m.get("semantics",{}).get("pass_requires",[]),"Level1 provider-closure evidence gate")
req("declared-runtime-input-version-proof" in m.get("semantics",{}).get("pass_requires",[]),"Level1 runtime-input evidence gate")
if m.get("state")=="planned-pending-activation":
    req(m.get("execution_authorized") is False,"planned Level1 must not authorize builds")
elif m.get("state")=="active-pending-ci":
    req(m.get("execution_authorized") is True,"active Level1 authorization")
    if m.get("current_attempt")==4:
        act=m.get("activation",{})
        req(act.get("status")=="ACTIVE" and act.get("attempt")==4,"Level1 Attempt4 activation marker")
        req(act.get("remediation_validation_policy_workflow_run")==35895610944 and act.get("remediation_validation_level1_workflow_run")==35895610937,"Level1 Attempt4 planning validation evidence")
        req(act.get("remediation_commit")=="9f680b0d8790c7bc472e8352e6675d606f706ee7" and act.get("scope")=="full-level1-rerun-2-nodes","Level1 Attempt4 activation commit/scope")
        rem=m.get("active_remediation",{})
        req(rem.get("round")==3 and rem.get("global_round")==8 and rem.get("status")=="materialization-PASS-attempt4-active","Level1 Attempt4 round8 state")
        req(rem.get("execution_authorized") is True and rem.get("current_attempt")==4,"Level1 Attempt4 remediation authorization")
        req(rem.get("activation_policy_workflow_run")==35895610944 and rem.get("activation_level1_workflow_run")==35895610937,"Level1 Attempt4 validation linkage")
        req(rem.get("activation_commit")=="9f680b0d8790c7bc472e8352e6675d606f706ee7","Level1 Attempt4 validation commit")
        req(m.get("next_gate")=="tier3-build-level1-attempt4","Level1 Attempt4 next gate")
    elif m.get("current_attempt")==3:
        act=m.get("activation",{})
        req(act.get("status")=="ACTIVE" and act.get("attempt")==3,"Level1 Attempt3 activation marker")
        req(act.get("remediation_validation_policy_workflow_run")==35884583361 and act.get("remediation_validation_level1_workflow_run")==35884584590,"Level1 Attempt3 planning validation evidence")
        req(act.get("remediation_commit")=="a562a145ba212349d725fad3e98a9dcb9c6c2ae0" and act.get("scope")=="full-level1-rerun-2-nodes","Level1 Attempt3 activation commit/scope")
        rem=m.get("active_remediation",{})
        req(rem.get("round")==2 and rem.get("global_round")==7 and rem.get("status")=="materialization-PASS-attempt3-active","Level1 Attempt3 round7 state")
        req(rem.get("execution_authorized") is True and rem.get("current_attempt")==3,"Level1 Attempt3 remediation authorization")
        req(rem.get("activation_policy_workflow_run")==35884583361 and rem.get("activation_level1_workflow_run")==35884584590,"Level1 Attempt3 validation linkage")
        req(m.get("next_gate")=="tier3-build-level1-attempt3","Level1 Attempt3 next gate")
    elif m.get("current_attempt")==2:
        act=m.get("activation",{})
        req(act.get("status")=="ACTIVE" and act.get("attempt")==2,"Level1 Attempt2 activation marker")
        req(act.get("remediation_validation_policy_workflow_run")==35828634884 and act.get("remediation_validation_level1_workflow_run")==35828634887,"Level1 Attempt2 remediation validation evidence")
        req(act.get("remediation_commit")=="568beba8aa3dce7a3f3a51d5e91d31edb5a30523" and act.get("scope")=="full-level1-rerun-2-nodes","Level1 Attempt2 activation commit/scope")
        rem=m.get("active_remediation",{})
        req(rem.get("round")==1 and rem.get("status")=="provider-closure-PASS-attempt2-active","Level1 Attempt2 closure state")
        req(rem.get("execution_authorized") is True and rem.get("current_attempt")==2,"Level1 Attempt2 remediation authorization")
        req(rem.get("validation_policy_workflow_run")==35828634884 and rem.get("validation_level1_workflow_run")==35828634887,"Level1 Attempt2 validation linkage")
        req(m.get("next_gate")=="tier3-build-level1-attempt2","Level1 Attempt2 next gate")
elif m.get("state")=="remediation-pending-materialization":
    rem=m.get("active_remediation",{})
    if rem.get("global_round")==9:
        req(m.get("execution_authorized") is False and m.get("current_attempt")==4 and m.get("next_attempt")==5,"Level1 Attempt4 remediation pause")
        req(rem.get("round")==4 and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Level1 round9 remediation scope")
        req(set(rem.get("source_changed_nodes",[]))=={"kio","kxmlgui"} and rem.get("provider_closure_only_nodes")==[],"Level1 round9 source remediation classes")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux5","kxmlgui":"6.30.0-0supralinux4"},"Level1 round9 candidate revisions")
        req(rem.get("source_rematerialization_required") is True and rem.get("package_revision_bump_required") is True,"Level1 round9 source rematerialization requirement")
        req(rem.get("full_level1_rerun_required") is True and rem.get("next_gate")=="tier3-round9-level1-materialization","Level1 round9 next gate")
        s4=m.get("attempt4_summary",{})
        req(s4.get("workflow_run")==35961584503 and s4.get("commit")=="513cb12a96c7c79ffb5790253504482a56af2e63","Level1 Attempt4 evidence identity")
        req(s4.get("rootfs",{}).get("artifact_id")==10792995587 and s4.get("rootfs",{}).get("artifact_sha256")=="c9ed6500670e092f8fe6e0ec531857afb51c5587f9a56bef083af2267c268ce3" and s4.get("rootfs",{}).get("rootfs_sha256")=="46fd06c2725ce8f10efba3c577da62f3a0dd5cb96e59683ca9fc988bed28c3a8","Level1 Attempt4 rootfs evidence")
        req(s4.get("result")=="FAIL" and s4.get("workflow_jobs")=={"success":0,"fail":2} and set(s4.get("job_fail",[]))=={"kio","kxmlgui"},"Level1 Attempt4 real FAIL summary")
        req(s4.get("canonical_promotions")==0 and s4.get("next_attempt")==5,"Level1 Attempt4 no promotion / Attempt5 handoff")
        req(s4.get("kio_tests")=={"total":69,"pass":67,"fail":2} and s4.get("kxmlgui_tests")=={"total":7,"pass":6,"fail":1},"Level1 Attempt4 test totals")
    elif rem.get("global_round")==8:
        req(m.get("execution_authorized") is False and m.get("current_attempt")==3 and m.get("next_attempt")==4,"Level1 Attempt3 remediation pause")
        req(rem.get("round")==3 and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Level1 round8 remediation scope")
        req(set(rem.get("source_changed_nodes",[]))=={"kio","kxmlgui"} and rem.get("provider_closure_only_nodes")==[],"Level1 round8 source remediation classes")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"},"Level1 round8 candidate revisions")
        req(rem.get("source_rematerialization_required") is True and rem.get("package_revision_bump_required") is True,"Level1 round8 source rematerialization requirement")
        req(rem.get("full_level1_rerun_required") is True and rem.get("next_gate")=="tier3-round8-level1-materialization","Level1 round8 next gate")
        s3=m.get("attempt3_summary",{})
        req(s3.get("workflow_run")==35887558758 and s3.get("commit")=="7583ba2ffcf7f91a1ea061c2e8c0cecd9f031d94","Level1 Attempt3 evidence identity")
        req(s3.get("result")=="FAIL" and s3.get("workflow_jobs")=={"success":0,"fail":2} and set(s3.get("job_fail",[]))=={"kio","kxmlgui"},"Level1 Attempt3 real FAIL summary")
        req(s3.get("canonical_promotions")==0 and s3.get("next_attempt")==4,"Level1 Attempt3 no promotion / Attempt4 handoff")
        req(s3.get("kio_tests")=={"total":69,"pass":62,"fail":7} and s3.get("kxmlgui_tests")=={"total":7,"pass":1,"fail":6},"Level1 Attempt3 test totals")
    else:
        req(m.get("execution_authorized") is False and m.get("current_attempt")==2 and m.get("next_attempt")==3,"Level1 Attempt2 remediation pause")
        rem=m.get("active_remediation",{})
        req(rem.get("round")==2 and rem.get("global_round")==7 and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Level1 round7 remediation scope")
        req(set(rem.get("source_changed_nodes",[]))=={"kio","kxmlgui"} and rem.get("provider_closure_only_nodes")==[],"Level1 round7 source remediation classes")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux3","kxmlgui":"6.30.0-0supralinux2"},"Level1 round7 candidate revisions")
        req(rem.get("source_rematerialization_required") is True and rem.get("package_revision_bump_required") is True,"Level1 round7 source rematerialization requirement")
        req(rem.get("full_level1_rerun_required") is True and rem.get("next_gate")=="tier3-round7-level1-materialization","Level1 round7 next gate")
        s=m.get("attempt2_summary",{})
        req(s.get("workflow_run")==35829170695 and s.get("commit")=="897d3a864bc7ea164400c7d9de2e9c51cf6316ab","Level1 Attempt2 evidence identity")
        req(s.get("result")=="FAIL" and s.get("workflow_jobs")=={"success":0,"fail":2} and set(s.get("job_fail",[]))=={"kio","kxmlgui"},"Level1 Attempt2 real FAIL summary")
        req(s.get("canonical_promotions")==0 and s.get("next_attempt")==3,"Level1 Attempt2 no promotion / Attempt3 handoff")

elif m.get("state")=="remediation-materialized-pending-planning-validation":
    rem=m.get("active_remediation",{})
    if rem.get("global_round")==9:
        req(m.get("execution_authorized") is False and m.get("current_attempt")==4 and m.get("next_attempt")==5,"Level1 round9 post-materialization pause")
        req(m.get("next_gate")=="tier3-build-level1-planning-validation","Level1 Attempt5 planning-validation gate")
        req(rem.get("round")==4 and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Level1 round9 promoted scope")
        req(rem.get("status")=="materialization-PASS-pending-attempt5-planning-validation","Level1 round9 source PASS state")
        req(rem.get("source_rematerialization_required") is False and rem.get("execution_authorized") is False,"Level1 round9 source handoff")
        req(rem.get("materialization_workflow_run")==35965579279 and rem.get("materialization_commit")=="8380856c8161dccc9de9c12745012c555baa26b0","Level1 round9 materialization evidence")
        arts=rem.get("materialization_artifacts",{})
        req(arts.get("kio",{}).get("artifact_id")==10794251210 and arts.get("kxmlgui",{}).get("artifact_id")==10793229286,"Level1 round9 materialization artifacts")
        req(rem.get("next_gate")=="tier3-build-level1-planning-validation","Level1 round9 planning-validation next gate")
    elif rem.get("global_round")==8:
        req(m.get("execution_authorized") is False and m.get("current_attempt")==3 and m.get("next_attempt")==4,"Level1 round8 post-materialization pause")
        req(m.get("next_gate")=="tier3-build-level1-planning-validation","Level1 Attempt4 planning-validation gate")
        req(rem.get("round")==3 and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Level1 round8 promoted scope")
        req(rem.get("status")=="materialization-PASS-pending-attempt4-planning-validation","Level1 round8 source PASS state")
        req(rem.get("source_rematerialization_required") is False and rem.get("execution_authorized") is False,"Level1 round8 source handoff")
        req(rem.get("materialization_workflow_run")==35894317888 and rem.get("materialization_commit")=="65f5ba76a913e7acf619eb9fee86e878e2914415","Level1 round8 materialization evidence")
        req(rem.get("next_gate")=="tier3-build-level1-planning-validation","Level1 round8 planning-validation next gate")
    else:
        req(m.get("execution_authorized") is False and m.get("current_attempt")==2 and m.get("next_attempt")==3,"Level1 round7 post-materialization pause")
        req(m.get("next_gate")=="tier3-build-level1-planning-validation","Level1 Attempt3 planning-validation gate")
        req(rem.get("round")==2 and rem.get("global_round")==7 and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Level1 round7 promoted scope")
        req(rem.get("status")=="materialization-PASS-pending-attempt3-planning-validation","Level1 round7 source PASS state")
        req(rem.get("source_rematerialization_required") is False and rem.get("execution_authorized") is False,"Level1 round7 source handoff")
        req(rem.get("materialization_workflow_run")==35882795135 and rem.get("materialization_commit")=="0d6c02f3f8dc41f716ba62ee7121f56371a8dc91","Level1 round7 materialization evidence")
        req(rem.get("next_gate")=="tier3-build-level1-planning-validation","Level1 round7 planning-validation next gate")
elif m.get("state")=="remediation-pending-activation":
    req(m.get("execution_authorized") is False and m.get("current_attempt")==1,"Level1 remediation pause after attempt1")
    rem=m.get("active_remediation",{})
    req(rem.get("round")==1 and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Level1 remediation node set")
    req(rem.get("source_changed_nodes")==[] and set(rem.get("provider_closure_only_nodes",[]))=={"kio","kxmlgui"},"Level1 closure-only remediation")
    req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2","kxmlgui":"6.30.0-0supralinux1"},"Level1 unchanged package revisions")
    req(rem.get("provider_closure_inputs")=={"kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"]},"Level1 closure input sets")
    req(rem.get("canonical_failures")==0 and rem.get("source_rematerialization_required") is False and rem.get("package_revision_bump_required") is False,"Level1 invalidated orchestration semantics")
    req(rem.get("full_level1_rerun_required") is True and rem.get("next_gate")=="tier3-build-level1-attempt2-activation-validation","Level1 attempt2 remediation gate")
    s=m.get("attempt1_summary",{})
    req(s.get("result")=="INVALIDATED-ORCHESTRATION" and s.get("raw_workflow_jobs")=={"success":0,"fail":2},"Level1 Attempt1 raw workflow evidence")
    req(s.get("raw_failed_nodes")==["kio","kxmlgui"] and s.get("canonical_failures")==0 and s.get("canonical_promotions")==0,"Level1 Attempt1 canonical no-effect")
    req(m.get("next_attempt")==2 and m.get("next_gate")=="tier3-build-level1-attempt2-activation-validation","Level1 Attempt2 paused gate")

pre=m.get("planning_precondition",{})
req(pre.get("level0_attempt")==5 and pre.get("level0_workflow_run")==35818120201,"Level1 Level0 prerequisite")
req(pre.get("kio_round5_materialization_workflow_run")==35825070347,"Level1 KIO round5 materialization run")
req(pre.get("kio_round5_materialization_artifact_id")==10735250819 and pre.get("kio_round5_materialization_artifact_sha256")=="8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106","Level1 KIO materialization pin")
req(pre.get("pre_plan_repository_policy_workflow_run")==35825677329 and pre.get("pre_plan_validated_commit")=="94fb4aebcda2959653b9c436bf5b5789ca3b103f","Level1 pre-plan Policy evidence")

req(tier3.get("build_level1_manifest")=="manifests/kde-tier3-build-level1.json","canonical Level1 manifest link")
policy=tier3.get("discovery_policy",{})
req(policy.get("phase") in {"build-level1-planning","build-level1"},"canonical Level1 phase")
req(policy.get("package_builds") in {"tier3-level1-source-PASS-pending-planning-validation","tier3-level1-authorized","tier3-level1-remediation-pending-provider-closure","tier3-level1-remediation-pending-materialization"},"canonical Level1 build gate")
ar=tier3.get("active_remediation",{})
if ar.get("round")==9:
    req(set(ar.get("nodes",[]))=={"kio","kxmlgui"},"canonical round9 scope")
    req(set(ar.get("source_materialization_nodes",[]))=={"kio","kxmlgui"} and ar.get("provider_closure_only_nodes")==[],"canonical round9 source classes")
    req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux5","kxmlgui":"6.30.0-0supralinux4"},"canonical round9 candidate revisions")
    req(ar.get("validation_workflow_run")==35961584503 and ar.get("validation_commit")=="513cb12a96c7c79ffb5790253504482a56af2e63","canonical round9 Attempt4 evidence")
    req(policy.get("phase")=="build-level1-planning" and policy.get("package_builds") in {"tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation"},"canonical round9 materialization/planning gate")
    req(ar.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level1-planning-validation"} and ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"canonical round9 execution pause")
    req(ar.get("current_attempt")==4 and ar.get("next_attempt")==5,"canonical round9 attempt markers")
    if policy.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
        req(ar.get("status")=="materialization-PASS-pending-level1-planning-validation","canonical round9 source PASS state")
        req(ar.get("materialization_workflow_run")==35965579279 and ar.get("materialization_commit")=="8380856c8161dccc9de9c12745012c555baa26b0","canonical round9 source PASS evidence")
        req(ar.get("next_gate")=="tier3-build-level1-planning-validation","canonical round9 planning gate")
    else:
        req(ar.get("status")=="materialization-pending-ci" and ar.get("next_gate")=="tier3-round9-level1-materialization","canonical round9 materialization gate")
elif ar.get("round")==8:
    req(set(ar.get("nodes",[]))=={"kio","kxmlgui"},"canonical round8 scope")
    req(set(ar.get("source_materialization_nodes",[]))=={"kio","kxmlgui"} and ar.get("provider_closure_only_nodes")==[],"canonical round8 source classes")
    req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"},"canonical round8 candidate revisions")
    req(ar.get("validation_workflow_run")==35887558758 and ar.get("validation_commit")=="7583ba2ffcf7f91a1ea061c2e8c0cecd9f031d94","canonical round8 Attempt3 evidence")
    if policy.get("package_builds")=="tier3-level1-authorized":
        req(policy.get("phase")=="build-level1","canonical round8 active phase")
        req(ar.get("status")=="level1-active-pending-ci" and ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True,"canonical round8 active authorization")
        req(ar.get("current_attempt")==4,"canonical round8 Attempt4 marker")
        req(ar.get("activation_policy_workflow_run")==35895610944 and ar.get("activation_level1_workflow_run")==35895610937,"canonical round8 Attempt4 planning validation")
        req(ar.get("activation_commit")=="9f680b0d8790c7bc472e8352e6675d606f706ee7","canonical round8 Attempt4 validation commit")
        req(ar.get("next_gate")=="tier3-build-level1-attempt4","canonical round8 Attempt4 gate")
    else:
        req(policy.get("phase")=="build-level1-planning" and policy.get("package_builds") in {"tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation"},"canonical round8 materialization/planning gate")
        req(ar.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level1-planning-validation"} and ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"canonical round8 execution pause")
        req(ar.get("current_attempt")==3 and ar.get("next_attempt")==4,"canonical round8 attempt markers")
elif ar.get("round")==7:
    req(set(ar.get("nodes",[]))=={"kio","kxmlgui"},"canonical round7 scope")
    req(set(ar.get("source_materialization_nodes",[]))=={"kio","kxmlgui"} and ar.get("provider_closure_only_nodes")==[],"canonical round7 source classes")
    req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux3","kxmlgui":"6.30.0-0supralinux2"},"canonical round7 candidate revisions")
elif policy.get("package_builds")=="tier3-level1-remediation-pending-provider-closure" or (policy.get("package_builds")=="tier3-level1-authorized" and ar.get("round")==6):
    req(ar.get("round")==6 and set(ar.get("nodes",[]))=={"kio","kxmlgui"},"canonical round6 scope")
    req(ar.get("source_materialization_nodes")==[] and set(ar.get("provider_closure_only_nodes",[]))=={"kio","kxmlgui"},"canonical round6 closure-only classes")
else:
    req(ar.get("round")==5 and ar.get("nodes")==["kio"],"canonical round5 scope")
    req(ar.get("materialization_workflow_run")==35825070347 and ar.get("materialization_commit")=="fbde9a53e357a138f4d74d7905230c7859e20444","canonical KIO materialization evidence")
if policy.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
    req(ar.get("status")=="materialization-PASS-pending-level1-planning-validation","canonical planning-validation state")
    req(ar.get("level1_execution_authorized") is False and ar.get("next_gate")=="tier3-build-level1-planning-validation","canonical Level1 execution pause")
    if ar.get("round")==9:
        req(ar.get("materialization_workflow_run")==35965579279 and ar.get("materialization_commit")=="8380856c8161dccc9de9c12745012c555baa26b0","canonical round9 source PASS evidence")
        arts=ar.get("materialization_artifacts",{})
        req(arts.get("kio",{}).get("artifact_id")==10794251210 and arts.get("kxmlgui",{}).get("artifact_id")==10793229286,"canonical round9 source PASS artifacts")
    elif ar.get("round")==8:
        req(ar.get("materialization_workflow_run")==35894317888 and ar.get("materialization_commit")=="65f5ba76a913e7acf619eb9fee86e878e2914415","canonical round8 source PASS evidence")
    elif ar.get("round")==7:
        req(ar.get("materialization_workflow_run")==35882795135 and ar.get("materialization_commit")=="0d6c02f3f8dc41f716ba62ee7121f56371a8dc91","canonical round7 source PASS evidence")
elif policy.get("package_builds")=="tier3-level1-remediation-pending-materialization":
    req(policy.get("phase")=="build-level1-planning","canonical Level1 materialization phase")
    req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"canonical Level1 materialization execution pause")
    if ar.get("round")==9:
        req(ar.get("status")=="materialization-pending-ci","canonical Level1 round9 remediation state")
        req(ar.get("validation_workflow_run")==35961584503 and ar.get("validation_commit")=="513cb12a96c7c79ffb5790253504482a56af2e63","canonical Attempt4 validation evidence")
        req(set(ar.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and ar.get("canonical_promotions")==0,"canonical Attempt4 failure/no-promotion semantics")
        req(ar.get("current_attempt")==4 and ar.get("next_attempt")==5 and ar.get("next_gate")=="tier3-round9-level1-materialization","canonical round9 materialization gate")
    elif ar.get("round")==8:
        req(ar.get("status")=="materialization-pending-ci","canonical Level1 round8 remediation state")
        req(ar.get("validation_workflow_run")==35887558758 and ar.get("validation_commit")=="7583ba2ffcf7f91a1ea061c2e8c0cecd9f031d94","canonical Attempt3 validation evidence")
        req(set(ar.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and ar.get("canonical_promotions")==0,"canonical Attempt3 failure/no-promotion semantics")
        req(ar.get("next_gate")=="tier3-round8-level1-materialization","canonical round8 materialization gate")
    else:
        req(ar.get("round")==7 and ar.get("status")=="materialization-pending-ci","canonical Level1 round7 remediation state")
        req(ar.get("validation_workflow_run")==35829170695 and ar.get("validation_commit")=="897d3a864bc7ea164400c7d9de2e9c51cf6316ab","canonical Attempt2 validation evidence")
        req(set(ar.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and ar.get("canonical_promotions")==0,"canonical Attempt2 failure/no-promotion semantics")
        req(ar.get("next_gate")=="tier3-round7-level1-materialization","canonical round7 materialization gate")
elif policy.get("package_builds")=="tier3-level1-remediation-pending-provider-closure":
    req(policy.get("phase")=="build-level1-planning","canonical Level1 remediation planning phase")
    req(ar.get("status")=="provider-closure-pending-attempt2-activation-validation","canonical round6 remediation state")
    req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"canonical Level1 remediation pause")
    req(ar.get("validation_workflow_run")==35826694664 and ar.get("validation_result")=="2 raw workflow FAIL / 0 canonical FAIL","canonical Attempt1 raw/canonical evidence")
    req(ar.get("raw_failed_nodes")==["kio","kxmlgui"] and ar.get("remaining_failed_nodes")==[] and ar.get("canonical_failures")==0,"canonical Attempt1 no current FAIL")
    req(ar.get("provider_closure_inputs")=={"kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"]},"canonical complete provider closure")
    req(ar.get("next_attempt")==2 and ar.get("next_gate")=="tier3-build-level1-attempt2-activation-validation","canonical Attempt2 activation gate")
elif policy.get("package_builds")=="tier3-level1-authorized":
    req(policy.get("phase")=="build-level1","canonical active Level1 phase")
    req(ar.get("status")=="level1-active-pending-ci","canonical active Level1 state")
    req(ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True,"canonical Level1 authorization")
    if ar.get("round")==8:
        req(ar.get("current_attempt")==4,"canonical Level1 Attempt4 marker")
        req(ar.get("activation_policy_workflow_run")==35895610944 and ar.get("activation_level1_workflow_run")==35895610937,"canonical Attempt4 planning validation")
        req(ar.get("activation_commit")=="9f680b0d8790c7bc472e8352e6675d606f706ee7","canonical Attempt4 validation commit")
        req(ar.get("next_gate")=="tier3-build-level1-attempt4","canonical Level1 Attempt4 gate")
    elif ar.get("round")==7:
        req(ar.get("current_attempt")==3,"canonical Level1 Attempt3 marker")
        req(ar.get("activation_policy_workflow_run")==35884583361 and ar.get("activation_level1_workflow_run")==35884584590,"canonical Attempt3 planning validation")
        req(ar.get("activation_commit")=="a562a145ba212349d725fad3e98a9dcb9c6c2ae0","canonical Attempt3 validation commit")
        req(ar.get("next_gate")=="tier3-build-level1-attempt3","canonical Level1 Attempt3 gate")
    elif ar.get("round")==6:
        req(ar.get("current_attempt")==2,"canonical Level1 Attempt2 marker")
        req(ar.get("activation_policy_workflow_run")==35828634884 and ar.get("activation_level1_workflow_run")==35828634887,"canonical Attempt2 remediation validation")
        req(ar.get("activation_commit")=="568beba8aa3dce7a3f3a51d5e91d31edb5a30523","canonical Attempt2 validation commit")
        req(ar.get("provider_closure_inputs")=={"kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"]},"canonical Attempt2 provider closure")
        req(ar.get("next_gate")=="tier3-build-level1-attempt2","canonical Level1 Attempt2 gate")
    else:
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
        n=(s0 if node in s0.get("nodes",{}) else s1).get("nodes",{}).get(node,{})
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

round9_source_promoted=m.get("state")=="remediation-materialized-pending-planning-validation" and m.get("active_remediation",{}).get("global_round")==9
round8_source_promoted=round9_source_promoted or (m.get("state")=="remediation-materialized-pending-planning-validation" and m.get("active_remediation",{}).get("global_round")==8) or m.get("current_attempt")==4
round7_source_promoted=round8_source_promoted or m.get("current_attempt")==3
expected={
 "kio":{
   "version":"6.30.0-0supralinux5" if round9_source_promoted else ("6.30.0-0supralinux4" if round8_source_promoted else ("6.30.0-0supralinux3" if round7_source_promoted else "6.30.0-0supralinux2")),
   "materialization":(35965579279,10794251210,"45eac20aca30ca6a5ef78d8a94d15ee5408a8bed39c8fa72c6c8823134ffa0b2") if round9_source_promoted else ((35894317888,10766471076,"80959256047d70323b6ea311551bed573661cefb4b831f30750e27ed11076cf6") if round8_source_promoted else ((35882795135,10760324592,"b58b7a45f6df0c8f01e9bd9a37799c1470369124a7c1b48fecb82a5f7f86ae8d") if round7_source_promoted else (35825070347,10735250819,"8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106"))),
   "tier3":["kbookmarks","kiconthemes","kjobwidgets","kwallet"],
   "support_build":["kdoctools"],"support_runtime":["kded"],"provider_closure":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"python":None,
 },
 "kxmlgui":{
   "version":"6.30.0-0supralinux4" if round9_source_promoted else ("6.30.0-0supralinux3" if round8_source_promoted else ("6.30.0-0supralinux2" if round7_source_promoted else "6.30.0-0supralinux1")),
   "materialization":(35965579279,10793229286,"44b9cf9d0ad12f06b12bda37c291fcda5ecf933e25cfdd61c42d9df6e11b0093") if round9_source_promoted else ((35894317888,10766665506,"100cf903ca1ef17cf2b37bab58ba0b7bf1e562d111cc04107247c3f35b134d58") if round8_source_promoted else ((35882795135,10761208629,"72cd10276558264646a9e38d5beab7b231434338597ef8d276030e790ff02214") if round7_source_promoted else (35746667704,10703925009,"9ad2056d1dbc9ab626521cd1f4bc67c13f5e36b18d93fc67da8ee6b7da3ba2fc"))),
   "tier3":["kconfigwidgets","kiconthemes","ktextwidgets"],
   "support_build":[],"support_runtime":[],"provider_closure":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"],"python":"KXmlGui",
 },
}
for node,e in expected.items():
    n=m.get("nodes",{}).get(node,{})
    p=campaign.get("nodes",{}).get(node,{})
    req(n.get("state") in {"prepared-pending-build","prepared-pending-revalidation","remediation-pending-build","remediation-pending-materialization","PASS","FAIL"} ,f"{node}: Level1 state")
    req(n.get("source_package")==p.get("source_package") and n.get("package_version")==e["version"],f"{node}: package identity")
    req(n.get("expected_binary_packages")==p.get("expected_binary_packages"),f"{node}: binary set")
    mat=n.get("materialization",{})
    req((mat.get("workflow_run"),mat.get("artifact_id"),mat.get("artifact_sha256"))==e["materialization"],f"{node}: materialization pin")
    classes=n.get("input_classes",{})
    req(classes.get("tier3_level0_pass")==e["tier3"],f"{node}: Tier3 predecessor class")
    req(classes.get("support_build")==e["support_build"] and classes.get("support_runtime")==e["support_runtime"],f"{node}: support classes")
    req(classes.get("provider_closure")==e["provider_closure"],f"{node}: provider closure class")
    req(n.get("provider_closure_input_ids")==e["provider_closure"],f"{node}: provider closure input IDs")
    req(n.get("runtime_validation_input_ids")==e["support_runtime"],f"{node}: runtime validation inputs")
    req(n.get("python_module")==e["python"],f"{node}: Python module")
    req(n.get("success_transition")=="PASS" and n.get("downstream_eligible_on_build_success") is True,f"{node}: success transition")
    if node=="kio":
        req(n.get("sbuild_enable_network") is True, "KIO node-scoped network exception")
    else:
        req(n.get("sbuild_enable_network") is False, "KXMLGui retains network-disabled sbuild")
    provider_closure=n.get("provider_closure_input_ids",[])
    req(provider_closure==classes.get("provider_closure",[]),f"{node}: provider closure class linkage")
    req(set(n.get("retained_input_ids",[]))==set(classes.get("external_pass",[])+classes.get("tier3_level0_pass",[])+classes.get("support_build",[])+classes.get("support_runtime",[])+provider_closure),f"{node}: retained input closure")
    req(all(x in ret for x in provider_closure),f"{node}: provider closure pins exist")
    closure_dev={ret[x].get("dev_package") for x in provider_closure}
    req(not (closure_dev & set(n.get("buildinfo_proof_packages",[]))),f"{node}: provider closure must not invent buildinfo edge")
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
    req(hist[0].get("result")=="INVALIDATED-ORCHESTRATION" and hist[0].get("raw_workflow_jobs")=={"success":0,"fail":2},"Level1 Attempt1 raw result summary")
    req(hist[0].get("raw_failed_nodes")==["kio","kxmlgui"] and hist[0].get("canonical_failures")==0 and hist[0].get("canonical_promotions")==0,"Level1 Attempt1 canonical no-effect")
    req(hist[0].get("failure_class")=="provider-closure-incomplete","Level1 Attempt1 failure class")
    if len(hist)>=2:
        req(hist[1].get("attempt")==2 and hist[1].get("workflow_run")==35829170695 and hist[1].get("commit")=="897d3a864bc7ea164400c7d9de2e9c51cf6316ab","Level1 Attempt2 ledger history")
        req(hist[1].get("result")=="FAIL" and hist[1].get("workflow_jobs")=={"success":0,"fail":2},"Level1 Attempt2 real failure summary")
        req(set(hist[1].get("failed_nodes",[]))=={"kio","kxmlgui"} and hist[1].get("canonical_promotions")==0,"Level1 Attempt2 fail/no-promotion semantics")
    for node,job,artifact,digest,version in (
      ("kio",107070288529,10735576795,"bbc1cb4caa351a335077e4b3dc0dcee7b2a7dfb96d85e6659d112ad87069c353","6.30.0-0supralinux2"),
      ("kxmlgui",107070288573,10734929331,"9e14c20ddfed7bc1cb500e1c2544eac1469b97cc2862ed54a946fd0deb1161ed","6.30.0-0supralinux1"),
    ):
        x=a["nodes"][node][0]
        req(x.get("attempt")==1 and x.get("raw_result")=="FAIL" and x.get("result")=="INVALIDATED-ORCHESTRATION" and x.get("workflow_run")==35826694664 and x.get("job_id")==job,f"{node}: Attempt1 invalidated identity")
        req(x.get("canonical_state_effect")=="none" and x.get("package_version_unchanged") is True and x.get("source_change") is False,f"{node}: Attempt1 canonical no-effect")
        req(x.get("artifact_id")==artifact and x.get("artifact_sha256")==digest,f"{node}: Attempt1 artifact")
        req(x.get("rootfs_artifact_id")==10735292514 and x.get("rootfs_sha256")=="65b28559cd2e23c1a2b5968e12ca0b3e48fd518b791b069ac2217898b44bfbed",f"{node}: Attempt1 rootfs evidence")
        req(x.get("package_attempted") is True and x.get("stage")=="sbuild" and x.get("failure_substage")=="install-deps",f"{node}: Attempt1 failure stage")
        req(x.get("package_version")==version and x.get("package_version_unchanged") is True and x.get("source_change") is False,f"{node}: Attempt1 no source revision change")

    if len(hist)>=2:
        for node,job,artifact,digest,version,substage,candidate in (
          ("kio",107077795233,10736848742,"94f5c7b51f47cd29dae2604f6258b8f10d13ef78e6f36e7023887c4f4336a51b","6.30.0-0supralinux2","ctest/upstream-test-environment","6.30.0-0supralinux3"),
          ("kxmlgui",107077795323,10735938957,"fe460539e197a4549b79cb8b6cedd9eac7ae823ceed6b758483cf53fcf774800","6.30.0-0supralinux1","cmake/python-binding-build-provider","6.30.0-0supralinux2"),
        ):
            x=a["nodes"][node][1]
            req(x.get("attempt")==2 and x.get("result")=="FAIL" and x.get("workflow_run")==35829170695 and x.get("job_id")==job,f"{node}: Attempt2 failure identity")
            req(x.get("artifact_id")==artifact and x.get("artifact_sha256")==digest,f"{node}: Attempt2 artifact")
            req(x.get("rootfs_artifact_id")==10736033276 and x.get("rootfs_artifact_sha256")=="8576bb973423d12cdd805c37e6c8b479aedf82466e38762a5ed8cb99def6961f" and x.get("rootfs_sha256")=="170fdc81f745a8597880a6433026f9ef66bca68665bf3450d02f0de561f3abe6",f"{node}: Attempt2 rootfs")
            req(x.get("package_attempted") is True and x.get("failure_substage")==substage and x.get("package_version")==version,f"{node}: Attempt2 stage/version")
            req(x.get("remediation",{}).get("candidate_package_version")==candidate and x.get("remediation",{}).get("source_rematerialization_required") is True,f"{node}: Attempt2 remediation revision")

    if len(hist)>=3:
        req(hist[2].get("attempt")==3 and hist[2].get("workflow_run")==35887558758 and hist[2].get("commit")=="7583ba2ffcf7f91a1ea061c2e8c0cecd9f031d94","Level1 Attempt3 ledger history")
        req(hist[2].get("result")=="FAIL" and hist[2].get("workflow_jobs")=={"success":0,"fail":2},"Level1 Attempt3 real failure summary")
        req(set(hist[2].get("failed_nodes",[]))=={"kio","kxmlgui"} and hist[2].get("canonical_promotions")==0 and hist[2].get("next_attempt")==4,"Level1 Attempt3 fail/no-promotion semantics")
        for node,job,artifact,digest,version,substage,candidate in (
          ("kio",107272258383,10763498649,"87ece6a4a4dd51af6b8d5810aaed39b58e5f3f01e979c0f2ce8daa8b3082d564","6.30.0-0supralinux3","ctest/upstream-test-environment-followup","6.30.0-0supralinux4"),
          ("kxmlgui",107272258358,10763747234,"c4626450ad4149723818884373dfc56603e411b62eafa1d4968ac979c0fa6516","6.30.0-0supralinux2","ctest/qt-platform","6.30.0-0supralinux3"),
        ):
            x=a["nodes"][node][2]
            req(x.get("attempt")==3 and x.get("result")=="FAIL" and x.get("workflow_run")==35887558758 and x.get("job_id")==job,f"{node}: Attempt3 failure identity")
            req(x.get("artifact_id")==artifact and x.get("artifact_sha256")==digest,f"{node}: Attempt3 artifact")
            req(x.get("rootfs_artifact_id")==10763606519 and x.get("rootfs_artifact_sha256")=="bf1fe0caaf73f0595d94c75b01f560f2913511bcafe8efe6fa81d8cc2bc0aa67" and x.get("rootfs_sha256")=="bd00be95fb5b9446a527ea155d625bd7c1cfd9ff7a0c8e59ceef118b421c11b6",f"{node}: Attempt3 rootfs")
            req(x.get("package_attempted") is True and x.get("failure_substage")==substage and x.get("package_version")==version,f"{node}: Attempt3 stage/version")
            req(x.get("remediation",{}).get("candidate_package_version")==candidate and x.get("remediation",{}).get("source_rematerialization_required") is True,f"{node}: Attempt3 remediation revision")

    if len(hist)>=4:
        req(hist[3].get("attempt")==4 and hist[3].get("workflow_run")==35961584503 and hist[3].get("commit")=="513cb12a96c7c79ffb5790253504482a56af2e63","Level1 Attempt4 ledger history")
        req(hist[3].get("result")=="FAIL" and hist[3].get("workflow_jobs")=={"success":0,"fail":2},"Level1 Attempt4 real failure summary")
        req(set(hist[3].get("failed_nodes",[]))=={"kio","kxmlgui"} and hist[3].get("canonical_promotions")==0 and hist[3].get("next_attempt")==5,"Level1 Attempt4 fail/no-promotion semantics")
        req(hist[3].get("rootfs",{}).get("artifact_id")==10792995587 and hist[3].get("rootfs",{}).get("artifact_sha256")=="c9ed6500670e092f8fe6e0ec531857afb51c5587f9a56bef083af2267c268ce3" and hist[3].get("rootfs",{}).get("rootfs_sha256")=="46fd06c2725ce8f10efba3c577da62f3a0dd5cb96e59683ca9fc988bed28c3a8","Level1 Attempt4 ledger rootfs")
        for node,job,artifact,digest,version,substage,candidate in (
          ("kio",107511358507,10792898014,"507f741700f698a1252851cb3d6ef2883fab68b4db79e239885eb5dc9e8bc299","6.30.0-0supralinux4","ctest/qt-icon-theme-platform","6.30.0-0supralinux5"),
          ("kxmlgui",107511358468,10792134667,"7171d692f12eede3945b6136f175538ef6557601e7f370d2ccd9b11f45ec5849","6.30.0-0supralinux3","ctest/session-bus","6.30.0-0supralinux4"),
        ):
            x=a["nodes"][node][3]
            req(x.get("attempt")==4 and x.get("result")=="FAIL" and x.get("workflow_run")==35961584503 and x.get("job_id")==job,f"{node}: Attempt4 failure identity")
            req(x.get("artifact_id")==artifact and x.get("artifact_sha256")==digest,f"{node}: Attempt4 artifact")
            req(x.get("rootfs_artifact_id")==10792995587 and x.get("rootfs_artifact_sha256")=="c9ed6500670e092f8fe6e0ec531857afb51c5587f9a56bef083af2267c268ce3" and x.get("rootfs_sha256")=="46fd06c2725ce8f10efba3c577da62f3a0dd5cb96e59683ca9fc988bed28c3a8",f"{node}: Attempt4 rootfs")
            req(x.get("package_attempted") is True and x.get("failure_substage")==substage and x.get("package_version")==version,f"{node}: Attempt4 stage/version")
            req(x.get("remediation",{}).get("candidate_package_version")==candidate and x.get("remediation",{}).get("source_rematerialization_required") is True,f"{node}: Attempt4 remediation revision")

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

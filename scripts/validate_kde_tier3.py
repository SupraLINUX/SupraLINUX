#!/usr/bin/env python3
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v:
        errors.append(m)
def load(path):
    return json.loads((ROOT/path).read_text())

tier3=load("manifests/kde-frameworks-tier3.json")
tier2=load("manifests/kde-frameworks-tier2.json")
dag=load("manifests/kde-dag.json")

if tier3.get("discovery_policy",{}).get("package_builds")=="tier3-level1-remediation-pending-materialization" and tier3.get("active_remediation",{}).get("round")==11:
    import subprocess
    raise SystemExit(subprocess.run([sys.executable, str(ROOT/"scripts/validate_kde_tier3_round11_materialization.py")]).returncode)

if tier3.get("discovery_policy",{}).get("package_builds")=="tier3-level1-attempt6-closed":
    import subprocess
    raise SystemExit(subprocess.run([sys.executable, str(ROOT/"scripts/validate_kde_tier3_attempt6_closure.py")]).returncode)

expected={
 "baloo":"a59d33a919bfa1d164c8f3a6f992c609edaf2131ac5f52ea4ecb77f6fbc53be1",
 "kbookmarks":"680120f09929d51da0a65e96a1f7d20ffbbdd2795a165719b0d07e00475e77c4",
 "kcmutils":"0159f80d030ac250b0b353113a55c013ed7e38cb0b678df44d2f0d0b2aca944c",
 "kconfigwidgets":"6efd9fc7786a7e979b32904aeadf1d2d8e69a5da110f8ebd45f95ec02de41f77",
 "kdav":"08d95cf546c941dbe21a76fbc8b88a466f276ab29e866600994f4f60d604c7f4",
 "kdesu":"9bf244884b09ce38ad84d00e5879e798b02e1610ec8f3d9ee6c93e7502b356e2",
 "kiconthemes":"c0c684823d0e087f35168cd79f1053fd358bb8fb47b27996a11c7d7ee3da6f4d",
 "kio":"c19cbd4878347b67a9e05ee6541083f51dd90f9e58ee245b4d7634e09f9c04b2",
 "kjobwidgets":"bf36e3619df1c6ad3d900bd36433d97ab295be41c1cc401ff0e766380788bbae",
 "knewstuff":"85408768b5c3f4b0b51ee6a14ae73fea263f451404e266e286c55e0c17e44037",
 "knotifyconfig":"4a133decdb0d3731dbaa1d3625b30f057089e5c59c8326ff88a047cef35b2efb",
 "kparts":"99f5a0e3a4da10e1a0fbfb505ae966cd87627f887dd07929a920afe41c862ac0",
 "kpeople":"094868f11c8c46e57a077c2788a39c6ee0b0ebc2b64279c6f7c70a5152f518e7",
 "krunner":"0885d0936aec6dc8553c673f1c685013e345b933a52812a07c5bddd1eebdb551",
 "ksvg":"7b7aba4e9baa88bfb303977e139e8a105b5cd243443029ee773954307b51eb91",
 "ktexteditor":"d90f24e33a7aa0e6a179af253dfdeca0977992adb62bf1b6f7ad11537ab6e3e7",
 "ktextwidgets":"b06b11bb727bf9c3578797b1e40daad5f48e10433e456a337f1c40b4082879c8",
 "kwallet":"93cb9c1df2630807c04bf8c30312e75ae3bb466c77dd9b29bb2c752e71d34a26",
 "kxmlgui":"10fb8a0f7b874248ff60d9a8ee4e1f06a0efcf01b0d34d7635dfff86e848c352",
 "purpose":"4fda64d235927e3cc230416d5c9304f5d3e040dc2553b77b2c69bf54c6f04862",
}

req(tier3.get("schema")==1,"Tier3 schema")
req(tier3.get("authority")=="kde-upstream","Tier3 authority")
req(tier3.get("frameworks_series")=="6.30.0" and tier3.get("tier")==3,"Tier3 series/tier")
req(tier3.get("tier_reference")=="https://api.kde.org/","Tier3 tier reference")
req(tier3.get("release_reference")=="https://kde.org/info/kde-frameworks-6.30.0/","Tier3 release reference")
req(tier3.get("dependency_manifest")=="manifests/kde-frameworks-tier3-dependencies.json","Tier3 dependency manifest reference")
req(tier3.get("provider_audit_manifest")=="manifests/kde-tier3-provider-audit.json","Tier3 provider audit manifest reference")
req(tier3.get("package_contract_manifest")=="manifests/kde-tier3-package-contracts.json","Tier3 package-contract manifest reference")
req(tier3.get("materialization_manifest")=="manifests/kde-tier3-materialization.json","Tier3 materialization manifest reference")
req(tier3.get("build_level0_manifest")=="manifests/kde-tier3-build-level0.json","Tier3 Level0 manifest reference")
req(tier3.get("support_components",{}).get("pending")==[],"Tier3 support-component pending queue")
req(tier3.get("support_components",{}).get("pass")==["breeze-icons","kdoctools","kded"],"Tier3 support-component PASS set")
pre=tier3.get("canonical_tier2_precondition",{})
req(pre.get("required_state")=="15 PASS / 0 pending / 0 current FAIL / 0 BLOCKED","Tier3 Tier2 precondition declaration")

tier2_nodes=tier2.get("nodes",[])
req(len(tier2_nodes)==15 and all(n.get("state")=="PASS" for n in tier2_nodes),"Tier3 requires closed Tier2 15/15 PASS")

nodes={n.get("id"):n for n in tier3.get("nodes",[])}
req(set(nodes)==set(expected),"Tier3 node set must match KDE upstream 20-node inventory")
level0_pass={"kbookmarks","kconfigwidgets","kdav","kdesu","kiconthemes","kjobwidgets","kpeople","krunner","ksvg","ktextwidgets","kwallet"}
post_level0=tier3.get("discovery_policy",{}).get("phase") in {"build-level1-planning","build-level1"}
for node_id,sha in expected.items():
    n=nodes.get(node_id,{})
    req(n.get("upstream_tier")==3 and n.get("upstream_version")=="6.30.0",f"{node_id}: upstream tier/version")
    req(n.get("source_sha256")==sha,f"{node_id}: KDE release SHA-256")
    req(n.get("source_url")==f"https://download.kde.org/stable/frameworks/6.30/{node_id}-6.30.0.tar.xz",f"{node_id}: source URL")
    req(n.get("upstream_ref")=="v6.30.0",f"{node_id}: upstream ref")
    planning=n.get("planning",{})
    if post_level0 and node_id in level0_pass:
        req(n.get("state")=="PASS",f"{node_id}: Level0 canonical PASS")
        req(planning.get("readiness")=="retained-pass",f"{node_id}: retained PASS readiness")
    elif post_level0 and node_id=="knewstuff":
        req(n.get("state")=="pending",f"{node_id}: runtime validation still pending")
        req(planning.get("readiness")=="runtime-validation-required",f"{node_id}: runtime-validation readiness")
    else:
        req(n.get("state")=="pending",f"{node_id}: canonical pending state")
        req(planning.get("readiness")=="materialized",f"{node_id}: materialized lifecycle")
    req(planning.get("provider_audit")=="PASS",f"{node_id}: provider audit PASS lifecycle")
    req(planning.get("provider_audit_manifest")=="manifests/kde-tier3-provider-audit.json",f"{node_id}: provider audit manifest linkage")
    req(planning.get("dependency_authority")=="kde-upstream",f"{node_id}: dependency authority")
    req(planning.get("provider")=="supralinux",f"{node_id}: selected provider")
    req(planning.get("package_contract") in {"materialized","retained-pass"},f"{node_id}: package contract lifecycle")
    req(planning.get("package_contract_manifest")=="manifests/kde-tier3-package-contracts.json",f"{node_id}: package-contract manifest linkage")
    pe=planning.get("provider_audit_evidence",{})
    req(pe.get("workflow_run")==35725458767 and pe.get("artifact_id")==10692912109,f"{node_id}: provider audit evidence linkage")
    packaging=n.get("packaging",{})
    if post_level0 and node_id in level0_pass:
        req(packaging.get("state")=="PASS" and packaging.get("downstream_eligible") is True,f"{node_id}: Level0 packaging PASS")
        req(isinstance(packaging.get("package_version"),str) and packaging.get("package_version"),f"{node_id}: promoted package version")
        req(dag.get("nodes",{}).get(node_id,{}).get("tier")==3 and dag["nodes"][node_id].get("state")=="PASS" and dag["nodes"][node_id].get("downstream_eligible") is True,f"{node_id}: canonical DAG promotion")
    elif post_level0 and node_id=="knewstuff":
        req(packaging.get("state")=="runtime-validation-required" and packaging.get("package_version")=="6.30.0-0supralinux1" and packaging.get("downstream_eligible") is False,f"{node_id}: runtime-validation pending packaging")
        req(packaging.get("deferred_runtime_validation")==["kcmutils"],f"{node_id}: KCMUtils deferred validation")
        req(node_id not in dag.get("nodes",{}),f"{node_id}: runtime-pending node must not enter canonical DAG")
    else:
        req(packaging.get("state")=="pending" and packaging.get("package_version") is None and packaging.get("downstream_eligible") is False,f"{node_id}: pending packaging state")
        req(node_id not in dag.get("nodes",{}),f"{node_id}: pending Tier3 node must not be promoted into canonical DAG")

policy=tier3.get("discovery_policy",{})
req(policy.get("phase") in {"build-level0","build-level1-planning","build-level1"},"Tier3 discovery phase")
req(policy.get("dependencies")=="materialized-from-kde-upstream-v6.30.0","Tier3 dependency state")
req(policy.get("provider_audit")=="PASS","Tier3 provider audit gate")
req(policy.get("package_contracts")=="PASS","Tier3 package-contract gate")
req(policy.get("package_builds") in {"tier3-level0-authorized","tier3-level0-remediation-pending","tier3-level1-not-authorized-before-planning","tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation","tier3-level1-authorized","tier3-level1-remediation-pending-provider-closure"},"Tier3 package-build gate")
support=tier3.get("support_components",{})
req(support.get("provider_audit_manifest")=="manifests/kde-tier3-support-provider-audit.json","Tier3 support provider-audit manifest")
req(support.get("provider_audit")=="PASS","Tier3 support provider-audit state")
req(support.get("package_contract_manifest")=="manifests/kde-tier3-support-package-contracts.json","Tier3 support package-contract manifest")
req(support.get("materialization_manifest")=="manifests/kde-tier3-support-materialization.json","Tier3 support materialization manifest")
req(support.get("materialization")=="PASS","Tier3 support materialization state")
req(support.get("build_level0_manifest")=="manifests/kde-tier3-support-build-level0.json","Tier3 support level0 manifest")
req(support.get("build_level0")=="PASS","Tier3 support level0 state")
req(support.get("build_level1_manifest")=="manifests/kde-tier3-support-build-level1.json","Tier3 support level1 manifest")
req(support.get("build_level1")=="PASS","Tier3 support level1 state")
req(support.get("support_subdag")=="PASS","Tier3 support sub-DAG state")
req(support.get("next_gate") in {"tier3-build-level0","tier3-build-level1-planning","tier3-build-level1"},"Tier3 support next gate")
if policy.get("package_builds")=="tier3-level0-remediation-pending":
    rem=tier3.get("active_remediation",{})
    if rem.get("round")==4:
        req(rem.get("trigger_workflow_run")==35813710318,"Tier3 round4 remediation trigger")
        req(set(rem.get("nodes",[]))=={"kwallet"},"Tier3 round4 remediation nodes")
        req(rem.get("source_materialization_nodes")==["kwallet"],"Tier3 round4 source materialization nodes")
        req(rem.get("provider_closure_only_nodes")==[],"Tier3 round4 provider closure-only nodes")
        req(rem.get("candidate_package_versions")=={"kwallet":"6.30.0-0supralinux4"},"Tier3 round4 package revision")
        req(rem.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level0-attempt5-activation"},"Tier3 round4 remediation state")
        req(rem.get("next_gate") in {"tier3-round4-kwallet-materialization","tier3-build-level0-attempt5-activation-validation"},"Tier3 round4 next gate")
    elif rem.get("round")==3:
        req(rem.get("trigger_workflow_run")==35808764577,"Tier3 round3 remediation trigger")
        req(set(rem.get("nodes",[]))=={"kjobwidgets","kwallet"},"Tier3 round3 remediation nodes")
        req(rem.get("source_materialization_nodes")==["kjobwidgets"],"Tier3 round3 source materialization nodes")
        req(rem.get("provider_closure_only_nodes")==["kwallet"],"Tier3 round3 provider closure nodes")
        req(rem.get("candidate_package_versions")=={"kjobwidgets":"6.30.0-0supralinux4","kwallet":"6.30.0-0supralinux3"},"Tier3 round3 package revisions")
        req(rem.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level0-attempt4-activation"},"Tier3 round3 remediation state")
        req(rem.get("next_gate") in {"tier3-round3-kjobwidgets-materialization","tier3-build-level0-attempt4-activation-validation"},"Tier3 round3 next gate")
    elif rem.get("round")==2:
        req(rem.get("trigger_workflow_run")==35770505868,"Tier3 round2 remediation trigger")
        req(set(rem.get("nodes",[]))=={"kiconthemes","kjobwidgets","kwallet"},"Tier3 round2 remediation nodes")
        req(rem.get("candidate_package_version")=="6.30.0-0supralinux3","Tier3 round2 remediation package revision")
        req(rem.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level0-attempt3-activation"},"Tier3 round2 remediation state")
    else:
        req(rem.get("trigger_workflow_run")==35755924197,"Tier3 round1 remediation trigger")
        req(set(rem.get("nodes",[]))=={"kiconthemes","kdav","kwallet","krunner","kjobwidgets"},"Tier3 round1 remediation nodes")
        req(rem.get("candidate_package_version")=="6.30.0-0supralinux2","Tier3 round1 remediation package revision")
    req(rem.get("execution_authorized") is False and rem.get("full_level0_rerun_required") is True,"Tier3 remediation execution policy")
elif policy.get("package_builds")=="tier3-level0-authorized":
    rem=tier3.get("active_remediation",{})
    attempt=rem.get("current_attempt")
    req(rem.get("status")=="level0-rerun-active","Tier3 active Level0 rerun status")
    req(rem.get("execution_authorized") is True,"Tier3 active Level0 execution authorization")
    if attempt==5:
        req(rem.get("round")==4,"Tier3 attempt5 remediation round")
        req(set(rem.get("nodes",[]))=={"kwallet"},"Tier3 attempt5 remediation nodes")
        req(rem.get("source_materialization_nodes")==["kwallet"],"Tier3 attempt5 source-remediated node")
        req(rem.get("provider_closure_only_nodes")==[],"Tier3 attempt5 closure-only node")
        req(rem.get("activation_policy_workflow_run")==35817928654,"Tier3 attempt5 activation validation")
        req(rem.get("next_gate")=="tier3-build-level0-attempt5","Tier3 attempt5 next gate")
    elif attempt==4:
        req(rem.get("round")==3,"Tier3 attempt4 remediation round")
        req(set(rem.get("nodes",[]))=={"kjobwidgets","kwallet"},"Tier3 attempt4 remediation nodes")
        req(rem.get("source_materialization_nodes")==["kjobwidgets"],"Tier3 attempt4 source-remediated node")
        req(rem.get("provider_closure_only_nodes")==["kwallet"],"Tier3 attempt4 closure-only node")
        req(rem.get("activation_policy_workflow_run")==35813396247,"Tier3 attempt4 activation validation")
        req(rem.get("next_gate")=="tier3-build-level0-attempt4","Tier3 attempt4 next gate")
    elif attempt==3:
        req(rem.get("round")==2,"Tier3 attempt3 remediation round")
        req(set(rem.get("nodes",[]))=={"kiconthemes","kjobwidgets","kwallet"},"Tier3 attempt3 remediation nodes")
        req(rem.get("activation_policy_workflow_run")==35807934729,"Tier3 attempt3 activation validation")
        req(rem.get("next_gate")=="tier3-build-level0-attempt3","Tier3 attempt3 next gate")
    elif attempt==2:
        req(rem.get("activation_policy_workflow_run")==35769883615,"Tier3 attempt2 activation validation")
        req(rem.get("next_gate")=="tier3-build-level0-attempt2","Tier3 attempt2 next gate")
    else:
        req(False,"Tier3 authorized Level0 attempt marker")
elif policy.get("package_builds")=="tier3-level1-remediation-pending-provider-closure":
    rem=tier3.get("active_remediation",{})
    req(policy.get("phase")=="build-level1-planning","Tier3 round6 Level1 remediation planning phase")
    req(rem.get("round")==6 and rem.get("level")=="build-level1","Tier3 round6 identity")
    req(set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Tier3 round6 node set")
    req(rem.get("source_materialization_nodes")==[] and set(rem.get("provider_closure_only_nodes",[]))=={"kio","kxmlgui"},"Tier3 round6 provider-closure-only classes")
    req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2","kxmlgui":"6.30.0-0supralinux1"},"Tier3 round6 unchanged revisions")
    req(rem.get("provider_closure_inputs")=={"kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"]},"Tier3 round6 closure inputs")
    req(rem.get("execution_authorized") is False and rem.get("level1_execution_authorized") is False,"Tier3 round6 execution pause")
    req(rem.get("validation_workflow_run")==35826694664 and rem.get("validation_commit")=="e7e98703184967487198f26a488d553038756990","Tier3 round6 trigger evidence")
    req(rem.get("validation_result")=="2 raw workflow FAIL / 0 canonical FAIL","Tier3 round6 raw/canonical result")
    req(rem.get("raw_failed_nodes")==["kio","kxmlgui"] and rem.get("remaining_failed_nodes")==[] and rem.get("canonical_failures")==0,"Tier3 round6 has no current package FAIL")
    req(rem.get("next_attempt")==2,"Tier3 round6 next attempt marker")
    req(rem.get("next_gate")=="tier3-build-level1-attempt2-activation-validation","Tier3 round6 next gate")
    hist=[x for x in tier3.get("remediation_history",[]) if x.get("round")==5]
    req(len(hist)==1 and hist[0].get("validation_workflow_run")==35826694664,"Tier3 round5 history retains Attempt1 result")
elif policy.get("package_builds")=="tier3-level1-authorized":
    rem=tier3.get("active_remediation",{})
    req(policy.get("phase")=="build-level1","Tier3 active Level1 phase")
    req(rem.get("status")=="level1-active-pending-ci","Tier3 active Level1 status")
    req(rem.get("execution_authorized") is True and rem.get("level1_execution_authorized") is True,"Tier3 active Level1 authorization")
    if rem.get("round")==10:
        req(rem.get("level")=="build-level1" and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Tier3 active Level1 round10 identity")
        req(rem.get("source_materialization_nodes")==["kio","kxmlgui"] and rem.get("provider_closure_only_nodes")==[],"Tier3 Attempt6 source-remediation scope")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux6","kxmlgui":"6.30.0-0supralinux5"},"Tier3 Attempt6 source revisions")
        req(rem.get("current_attempt")==6,"Tier3 Level1 Attempt6 marker")
        req(rem.get("activation_policy_workflow_run")==36032425645 and rem.get("activation_level1_workflow_run")==36032425729,"Tier3 Attempt6 validation evidence")
        req(rem.get("activation_commit")=="0fee159ac1f24dc160e1edd9976a7708f89d657d","Tier3 Attempt6 validation commit")
        req(rem.get("next_gate")=="tier3-build-level1-attempt6","Tier3 Level1 Attempt6 gate")
    elif rem.get("round")==9:
        req(rem.get("level")=="build-level1" and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Tier3 active Level1 round9 identity")
        req(rem.get("source_materialization_nodes")==["kio","kxmlgui"] and rem.get("provider_closure_only_nodes")==[],"Tier3 Attempt5 source-remediation scope")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux5","kxmlgui":"6.30.0-0supralinux4"},"Tier3 Attempt5 source revisions")
        req(rem.get("current_attempt")==5,"Tier3 Level1 Attempt5 marker")
        req(rem.get("activation_policy_workflow_run")==35990068378 and rem.get("activation_level1_workflow_run")==35990068382,"Tier3 Attempt5 validation evidence")
        req(rem.get("activation_commit")=="45675c1fb5a43f95204c2cf0c5c15df0ef703832","Tier3 Attempt5 validation commit")
        req(rem.get("next_gate")=="tier3-build-level1-attempt5","Tier3 Level1 Attempt5 gate")
    elif rem.get("round")==8:
        req(rem.get("level")=="build-level1" and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Tier3 active Level1 round8 identity")
        req(rem.get("source_materialization_nodes")==["kio","kxmlgui"] and rem.get("provider_closure_only_nodes")==[],"Tier3 Attempt4 source-remediation scope")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"},"Tier3 Attempt4 source revisions")
        req(rem.get("current_attempt")==4,"Tier3 Level1 Attempt4 marker")
        req(rem.get("activation_policy_workflow_run")==35895610944 and rem.get("activation_level1_workflow_run")==35895610937,"Tier3 Attempt4 validation evidence")
        req(rem.get("activation_commit")=="9f680b0d8790c7bc472e8352e6675d606f706ee7","Tier3 Attempt4 validation commit")
        req(rem.get("next_gate")=="tier3-build-level1-attempt4","Tier3 Level1 Attempt4 gate")
    elif rem.get("round")==7:
        req(rem.get("level")=="build-level1" and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Tier3 active Level1 round7 identity")
        req(rem.get("source_materialization_nodes")==["kio","kxmlgui"] and rem.get("provider_closure_only_nodes")==[],"Tier3 Attempt3 source-remediation scope")
        req(rem.get("current_attempt")==3,"Tier3 Level1 Attempt3 marker")
        req(rem.get("activation_policy_workflow_run")==35884583361 and rem.get("activation_level1_workflow_run")==35884584590,"Tier3 Attempt3 validation evidence")
        req(rem.get("activation_commit")=="a562a145ba212349d725fad3e98a9dcb9c6c2ae0","Tier3 Attempt3 validation commit")
        req(rem.get("next_gate")=="tier3-build-level1-attempt3","Tier3 Level1 Attempt3 gate")
    elif rem.get("round")==6:
        req(rem.get("level")=="build-level1" and set(rem.get("nodes",[]))=={"kio","kxmlgui"},"Tier3 active Level1 round6 identity")
        req(rem.get("current_attempt")==2,"Tier3 Level1 Attempt2 marker")
        req(rem.get("activation_policy_workflow_run")==35828634884 and rem.get("activation_level1_workflow_run")==35828634887,"Tier3 Level1 Attempt2 validation evidence")
        req(rem.get("activation_commit")=="568beba8aa3dce7a3f3a51d5e91d31edb5a30523","Tier3 Level1 Attempt2 validation commit")
        req(rem.get("provider_closure_inputs")=={"kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"]},"Tier3 Level1 Attempt2 complete closure")
        req(rem.get("next_gate")=="tier3-build-level1-attempt2","Tier3 Level1 Attempt2 gate")
    else:
        req(rem.get("round")==5 and rem.get("level")=="build-level1-preflight","Tier3 active Level1 round5 identity")
        req(rem.get("current_attempt")==1,"Tier3 Level1 attempt marker")
        req(rem.get("planning_policy_workflow_run")==35826072726 and rem.get("planning_policy_commit")=="b96e925ee9f649c1b4b984ed6fed277ef911f2c2","Tier3 Level1 planning Policy evidence")
        req(rem.get("planner_workflow_run")==35826072818,"Tier3 Level1 planner evidence")
        req(rem.get("next_gate")=="tier3-build-level1-attempt1","Tier3 Level1 attempt1 gate")
    req(tier3.get("build_level1_manifest")=="manifests/kde-tier3-build-level1.json","Tier3 Level1 manifest linkage")
elif policy.get("package_builds") in {"tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation"}:
    rem=tier3.get("active_remediation",{})
    req(policy.get("phase")=="build-level1-planning","Tier3 Level1 remediation planning phase")
    if rem.get("round")==10:
        req(rem.get("level")=="build-level1","Tier3 round10 Level1 identity")
        req(set(rem.get("nodes",[]))=={"kio","kxmlgui"} and rem.get("source_materialization_nodes")==["kio","kxmlgui"],"Tier3 round10 source scope")
        req(rem.get("provider_closure_only_nodes")==[],"Tier3 round10 closure-only set")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux6","kxmlgui":"6.30.0-0supralinux5"},"Tier3 round10 package revisions")
        req(rem.get("execution_authorized") is False and rem.get("level1_execution_authorized") is False,"Tier3 round10 execution pause")
        req(rem.get("trigger_workflow_run")==35991007820 and rem.get("trigger_commit")=="3197c1988e1ab86ec5010cb693064db949bfe6b0","Tier3 round10 trigger evidence")
        req(rem.get("validation_workflow_run")==35991007820 and rem.get("validation_commit")=="3197c1988e1ab86ec5010cb693064db949bfe6b0" and rem.get("validation_result")=="0 workflow SUCCESS / 2 FAIL","Tier3 round10 Attempt5 evidence")
        req(set(rem.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and rem.get("canonical_promotions")==0,"Tier3 round10 failure/no-promotion semantics")
        req(rem.get("current_attempt")==5 and rem.get("next_attempt")==6,"Tier3 round10 attempt markers")
        if policy.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(rem.get("status")=="materialization-PASS-pending-level1-planning-validation","Tier3 round10 source PASS state")
            req(rem.get("materialization_workflow_run")==36002910277 and rem.get("materialization_commit")=="c0774e5514fd83995aad3c86e1f6a5b106b001a3","Tier3 round10 source PASS evidence")
            arts=rem.get("materialization_artifacts",{})
            req(arts.get("kio",{}).get("artifact_id")==10809231495 and arts.get("kxmlgui",{}).get("artifact_id")==10808294092,"Tier3 round10 source PASS artifacts")
            req(rem.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round10 planning-validation gate")
            nodes={x.get("id"):x for x in tier3.get("nodes",[])}
            req(nodes["kio"].get("planning",{}).get("materialization_evidence",{}).get("artifact_id")==10809231495,"KIO round10 refreshed materialization evidence")
            req(nodes["kxmlgui"].get("planning",{}).get("materialization_evidence",{}).get("artifact_id")==10808294092,"KXMLGui round10 refreshed materialization evidence")
        else:
            req(policy.get("package_builds")=="tier3-level1-remediation-pending-materialization","Tier3 round10 materialization gate")
            req(rem.get("status")=="materialization-pending-ci" and rem.get("next_gate")=="tier3-round10-level1-materialization","Tier3 round10 pending materialization state")
        hist=[x for x in tier3.get("remediation_history",[]) if x.get("round")==9]
        req(len(hist)==1 and hist[0].get("status")=="attempt5-complete-FAIL" and hist[0].get("validation_workflow_run")==35991007820,"Tier3 round9 history retains Attempt5 result")
    elif rem.get("round")==9:
        req(rem.get("level")=="build-level1","Tier3 round9 Level1 identity")
        req(set(rem.get("nodes",[]))=={"kio","kxmlgui"} and rem.get("source_materialization_nodes")==["kio","kxmlgui"],"Tier3 round9 source scope")
        req(rem.get("provider_closure_only_nodes")==[],"Tier3 round9 closure-only set")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux5","kxmlgui":"6.30.0-0supralinux4"},"Tier3 round9 package revisions")
        req(rem.get("execution_authorized") is False and rem.get("level1_execution_authorized") is False,"Tier3 round9 execution pause")
        req(rem.get("trigger_workflow_run")==35961584503 and rem.get("trigger_commit")=="513cb12a96c7c79ffb5790253504482a56af2e63","Tier3 round9 trigger evidence")
        req(rem.get("validation_workflow_run")==35961584503 and rem.get("validation_result")=="0 workflow SUCCESS / 2 FAIL","Tier3 round9 Attempt4 evidence")
        req(set(rem.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and rem.get("canonical_promotions")==0,"Tier3 round9 failure/no-promotion semantics")
        req(rem.get("current_attempt")==4 and rem.get("next_attempt")==5,"Tier3 round9 attempt markers")
        if policy.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(rem.get("status")=="materialization-PASS-pending-level1-planning-validation","Tier3 round9 source PASS state")
            req(rem.get("materialization_workflow_run")==35965579279 and rem.get("materialization_commit")=="8380856c8161dccc9de9c12745012c555baa26b0","Tier3 round9 source PASS evidence")
            arts=rem.get("materialization_artifacts",{})
            req(arts.get("kio",{}).get("artifact_id")==10794251210 and arts.get("kxmlgui",{}).get("artifact_id")==10793229286,"Tier3 round9 source PASS artifacts")
            req(rem.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round9 planning-validation gate")
            nodes={x.get("id"):x for x in tier3.get("nodes",[])}
            req(nodes["kio"].get("planning",{}).get("materialization_evidence",{}).get("artifact_id")==10794251210,"KIO round9 refreshed materialization evidence")
            req(nodes["kxmlgui"].get("planning",{}).get("materialization_evidence",{}).get("artifact_id")==10793229286,"KXMLGui round9 refreshed materialization evidence")
        else:
            req(policy.get("package_builds")=="tier3-level1-remediation-pending-materialization","Tier3 round9 materialization gate")
            req(rem.get("status")=="materialization-pending-ci","Tier3 round9 pending materialization state")
            req(rem.get("next_gate")=="tier3-round9-level1-materialization","Tier3 round9 next gate")
        hist=[x for x in tier3.get("remediation_history",[]) if x.get("round")==8]
        req(len(hist)==1 and hist[0].get("status")=="attempt4-complete-FAIL" and hist[0].get("validation_workflow_run")==35961584503,"Tier3 round8 history retains Attempt4 result")
    elif rem.get("round")==8:
        req(rem.get("level")=="build-level1","Tier3 round8 Level1 identity")
        req(set(rem.get("nodes",[]))=={"kio","kxmlgui"} and rem.get("source_materialization_nodes")==["kio","kxmlgui"],"Tier3 round8 source scope")
        req(rem.get("provider_closure_only_nodes")==[],"Tier3 round8 closure-only set")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"},"Tier3 round8 package revisions")
        req(rem.get("execution_authorized") is False and rem.get("level1_execution_authorized") is False,"Tier3 round8 execution pause")
        req(rem.get("trigger_workflow_run")==35887558758 and rem.get("trigger_commit")=="7583ba2ffcf7f91a1ea061c2e8c0cecd9f031d94","Tier3 round8 trigger evidence")
        req(rem.get("validation_workflow_run")==35887558758 and rem.get("validation_result")=="0 workflow SUCCESS / 2 FAIL","Tier3 round8 Attempt3 evidence")
        req(set(rem.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and rem.get("canonical_promotions")==0,"Tier3 round8 failure/no-promotion semantics")
        if policy.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(rem.get("status")=="materialization-PASS-pending-level1-planning-validation","Tier3 round8 source PASS state")
            req(rem.get("materialization_workflow_run")==35894317888 and rem.get("materialization_commit")=="65f5ba76a913e7acf619eb9fee86e878e2914415","Tier3 round8 source PASS evidence")
            req(rem.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round8 planning-validation gate")
            nodes={x.get("id"):x for x in tier3.get("nodes",[])}
            req(nodes["kio"].get("planning",{}).get("materialization_evidence",{}).get("artifact_id")==10766471076,"KIO round8 refreshed materialization evidence")
            req(nodes["kxmlgui"].get("planning",{}).get("materialization_evidence",{}).get("artifact_id")==10766665506,"KXMLGui round8 refreshed materialization evidence")
        else:
            req(policy.get("package_builds")=="tier3-level1-remediation-pending-materialization","Tier3 round8 materialization gate")
            req(rem.get("status")=="materialization-pending-ci","Tier3 round8 pending materialization state")
            req(rem.get("next_gate")=="tier3-round8-level1-materialization","Tier3 round8 next gate")
    elif rem.get("round")==7:
        req(rem.get("level")=="build-level1","Tier3 round7 Level1 identity")
        req(set(rem.get("nodes",[]))=={"kio","kxmlgui"} and rem.get("source_materialization_nodes")==["kio","kxmlgui"],"Tier3 round7 source scope")
        req(rem.get("provider_closure_only_nodes")==[],"Tier3 round7 closure-only set")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux3","kxmlgui":"6.30.0-0supralinux2"},"Tier3 round7 package revisions")
        req(rem.get("execution_authorized") is False and rem.get("level1_execution_authorized") is False,"Tier3 round7 execution pause")
        req(rem.get("trigger_workflow_run")==35829170695 and rem.get("trigger_commit")=="897d3a864bc7ea164400c7d9de2e9c51cf6316ab","Tier3 round7 trigger evidence")
        req(rem.get("validation_workflow_run")==35829170695 and rem.get("validation_result")=="0 workflow SUCCESS / 2 FAIL","Tier3 round7 Attempt2 evidence")
        req(set(rem.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and rem.get("canonical_promotions")==0,"Tier3 round7 failure/no-promotion semantics")
        if policy.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(rem.get("status")=="materialization-PASS-pending-level1-planning-validation","Tier3 round7 source PASS state")
            req(rem.get("materialization_workflow_run")==35882795135 and rem.get("materialization_commit")=="0d6c02f3f8dc41f716ba62ee7121f56371a8dc91","Tier3 round7 source PASS evidence")
            req(rem.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round7 planning-validation gate")
            nodes={x.get("id"):x for x in tier3.get("nodes",[])}
            req(nodes["kio"].get("planning",{}).get("materialization_evidence",{}).get("artifact_id")==10760324592,"KIO round7 refreshed materialization evidence")
            req(nodes["kxmlgui"].get("planning",{}).get("materialization_evidence",{}).get("artifact_id")==10761208629,"KXMLGui round7 refreshed materialization evidence")
        else:
            req(policy.get("package_builds")=="tier3-level1-remediation-pending-materialization","Tier3 round7 materialization gate")
            req(rem.get("status")=="materialization-pending-ci","Tier3 round7 pending materialization state")
            req(rem.get("next_gate")=="tier3-round7-level1-materialization","Tier3 round7 next gate")
    else:
        req(rem.get("round")==5 and rem.get("level")=="build-level1-preflight","Tier3 round5 Level1 preflight identity")
        req(set(rem.get("nodes",[]))=={"kio"} and rem.get("source_materialization_nodes")==["kio"],"Tier3 round5 KIO source scope")
        req(rem.get("provider_closure_only_nodes")==[],"Tier3 round5 closure-only set")
        req(rem.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2"},"Tier3 round5 KIO revision")
        req(rem.get("execution_authorized") is False and rem.get("level1_execution_authorized") is False,"Tier3 round5 execution pause")
        req(rem.get("trigger_workflow_run")==35818120201 and rem.get("trigger_commit")=="0599266fd5fc9869002629b3778d71f1e76bbdc1","Tier3 round5 trigger evidence")
        if policy.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(rem.get("status")=="materialization-PASS-pending-level1-planning-validation","Tier3 round5 source PASS state")
            req(rem.get("materialization_workflow_run")==35825070347 and rem.get("materialization_commit")=="fbde9a53e357a138f4d74d7905230c7859e20444","Tier3 round5 source PASS evidence")
            req(rem.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round5 planning-validation gate")
            kio=tier3.get("nodes",[])[[x.get("id") for x in tier3.get("nodes",[])].index("kio")]
            req(kio.get("planning",{}).get("materialization_evidence",{}).get("artifact_id")==10735250819,"KIO refreshed materialization evidence")
        else:
            req(rem.get("status")=="materialization-pending-ci","Tier3 round5 pending materialization state")
            req(rem.get("next_gate")=="tier3-level1-kio-materialization","Tier3 round5 next gate")
elif policy.get("package_builds")=="tier3-level1-not-authorized-before-planning":
    rem=tier3.get("active_remediation",{})
    req(policy.get("phase")=="build-level1-planning","Tier3 Level1 planning phase")
    req(rem.get("round")==4 and rem.get("status")=="attempt5-complete","Tier3 Attempt5 closure")
    req(rem.get("execution_authorized") is False,"Tier3 Level1 not yet authorized")
    req(rem.get("validation_workflow_run")==35818120201 and rem.get("validation_commit")=="0599266fd5fc9869002629b3778d71f1e76bbdc1","Tier3 Attempt5 validation evidence")
    req(rem.get("canonical_promotions")==11 and rem.get("remaining_failed_nodes")==[] and rem.get("runtime_pending_nodes")==["knewstuff"],"Tier3 Attempt5 promotion summary")
    req(rem.get("next_gate")=="tier3-build-level1-planning","Tier3 Level1 planning next gate")
    req(tier3.get("level0_snapshot")=={"pass":11,"pending":9,"current_fail":0,"blocked":0,"runtime_pending":["knewstuff"],"workflow_run":35818120201,"commit":"0599266fd5fc9869002629b3778d71f1e76bbdc1"},"Tier3 post-Level0 snapshot")

doc=(ROOT/"docs/kde-tier3.md").read_text()
state_token="11 PASS / 9 pending / 0 current FAIL / 0 BLOCKED" if post_level0 else "0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED"
req(state_token in doc,"Tier3 docs canonical snapshot")
req("KDE upstream" in doc and "Ubuntu" in doc,"Tier3 docs authority/provider boundary")
req("materialized" in doc and "build-level0" in doc and "remediation" in doc.lower(),"Tier3 docs lifecycle")

if errors:
    for e in errors:
        print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)

print("KDE Frameworks Tier 3 source inventory validation: PASS")
print("Frameworks series: 6.30.0")
print("Tier 3: 0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED")
print("Next gate: Tier 3 build Level 0")

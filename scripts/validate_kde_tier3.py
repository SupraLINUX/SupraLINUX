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
for node_id,sha in expected.items():
    n=nodes.get(node_id,{})
    req(n.get("upstream_tier")==3 and n.get("upstream_version")=="6.30.0",f"{node_id}: upstream tier/version")
    req(n.get("source_sha256")==sha,f"{node_id}: KDE release SHA-256")
    req(n.get("source_url")==f"https://download.kde.org/stable/frameworks/6.30/{node_id}-6.30.0.tar.xz",f"{node_id}: source URL")
    req(n.get("upstream_ref")=="v6.30.0",f"{node_id}: upstream ref")
    req(n.get("state")=="pending",f"{node_id}: initial canonical state")
    planning=n.get("planning",{})
    req(planning.get("readiness")=="materialized",f"{node_id}: materialized lifecycle")
    req(planning.get("provider_audit")=="PASS",f"{node_id}: provider audit PASS lifecycle")
    req(planning.get("provider_audit_manifest")=="manifests/kde-tier3-provider-audit.json",f"{node_id}: provider audit manifest linkage")
    req(planning.get("dependency_authority")=="kde-upstream",f"{node_id}: dependency authority")
    req(planning.get("provider")=="supralinux",f"{node_id}: selected provider")
    req(planning.get("package_contract")=="materialized",f"{node_id}: package contract materialized")
    req(planning.get("package_contract_manifest")=="manifests/kde-tier3-package-contracts.json",f"{node_id}: package-contract manifest linkage")
    pe=planning.get("provider_audit_evidence",{})
    req(pe.get("workflow_run")==35725458767 and pe.get("artifact_id")==10692912109,f"{node_id}: provider audit evidence linkage")
    packaging=n.get("packaging",{})
    req(packaging.get("state")=="pending" and packaging.get("package_version") is None and packaging.get("downstream_eligible") is False,f"{node_id}: initial packaging state")
    req(node_id not in dag.get("nodes",{}),f"{node_id}: pending Tier3 node must not be promoted into canonical DAG")

policy=tier3.get("discovery_policy",{})
req(policy.get("phase")=="build-level0","Tier3 discovery phase")
req(policy.get("dependencies")=="materialized-from-kde-upstream-v6.30.0","Tier3 dependency state")
req(policy.get("provider_audit")=="PASS","Tier3 provider audit gate")
req(policy.get("package_contracts")=="PASS","Tier3 package-contract gate")
req(policy.get("package_builds") in {"tier3-level0-authorized","tier3-level0-remediation-pending"},"Tier3 package-build gate")
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
req(support.get("next_gate")=="tier3-build-level0","Tier3 support next gate")
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

doc=(ROOT/"docs/kde-tier3.md").read_text()
req("0 PASS / 20 pending / 0 current FAIL / 0 BLOCKED" in doc,"Tier3 docs canonical snapshot")
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

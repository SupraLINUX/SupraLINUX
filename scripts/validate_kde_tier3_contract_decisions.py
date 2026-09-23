#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads((ROOT/p).read_text())

c=load("manifests/kde-tier3-package-contracts.json")
t=load("manifests/kde-frameworks-tier3.json")
d=load("manifests/kde-frameworks-tier3-dependencies.json")
selected=c.get("selected_nodes",[])
nodes={n["id"]:n for n in t.get("nodes",[])}

req(c.get("state") in {"contracts-ready","materialized"},"Tier3 contracts lifecycle")
req(len(selected)==20 and set(selected)==set(nodes),"Tier3 decision node set")
req(c.get("source_authority")=="kde-upstream" and c.get("packaging_authority")=="supralinux","Tier3 decision authority boundary")

decision=c.get("contract_decision",{})
req(decision.get("status")=="PASS","Tier3 contract decision PASS")
req(decision.get("authority")=="supralinux" and decision.get("source_authority")=="kde-upstream","Tier3 contract decision authority")
req(decision.get("baseline_policy")=="debian-sid-exact-kde-6.30-tree-with-explicit-supralinux-overrides","Tier3 baseline policy")
req(decision.get("materialization_authorized") is True,"Tier3 materialization authorization")
req(decision.get("package_build_authorized") is False,"Tier3 builds remain unauthorized")

policy=c.get("policy",{})
req(policy.get("python_bindings_follow_upstream_defaults") is True,"Tier3 Python binding policy")
req(policy.get("upstream_tests_must_run") is True,"Tier3 test policy")
req(policy.get("reference_test_suppression_not_authoritative") is True,"Tier3 test suppression policy")
req(policy.get("selected_linux_profiles_must_be_preserved") is True,"Tier3 selected Linux profile policy")
req(policy.get("development_dependencies_follow_exported_upstream_contract") is True,"Tier3 development dependency policy")
req(policy.get("test_environment_dependencies_do_not_create_dag_edges") is True,"Tier3 test/DAG separation")

adapt=c.get("provider_adaptations",{}).get("ubuntu-resolute",{})
dh=adapt.get("debhelper_compat",{})
req(dh.get("technical_reference_level")==14 and dh.get("selected_level")==13,"Tier3 debhelper Resolute adaptation")
req(dh.get("observed_provider_version")=="13.31ubuntu1","Tier3 debhelper provider evidence")
chg=adapt.get("changelog_distribution",{})
req(chg.get("selected")=="resolute","Tier3 changelog target")
shi=adapt.get("shiboken_clang_discovery",{})
req(shi.get("provider_packages")==["llvm-dev","libclang-common-21-dev"],"Tier3 Shiboken provider packages")
req(shi.get("llvm_major")==21 and shi.get("applies_to")==["kjobwidgets","kxmlgui"],"Tier3 Shiboken provider contract")
round1=c.get("remediation",{})
round1_nodes=set(round1.get("trigger",{}).get("failed_nodes",[]))
req(round1_nodes=={"kiconthemes","kdav","kwallet","krunner","kjobwidgets"},"Tier3 round1 remediation node set")
req(round1.get("status")=="materialization-PASS","Tier3 round1 materialization PASS")
pb=adapt.get("python_build_module",{})
req(pb.get("provider_package")=="python3-build" and pb.get("applies_to")==["kjobwidgets"],"Tier3 KJobWidgets Python build frontend provider")

active=c.get("active_remediation",{})
active_nodes=set(active.get("trigger",{}).get("failed_nodes",active.get("trigger",{}).get("affected_nodes",[])))
if active:
    round_no=active.get("round")
    req(active.get("status") in {"materialization-pending-ci","materialization-PASS"},"Tier3 active remediation state")
    if round_no==5:
        req(active_nodes=={"kio"},"Tier3 round5 KIO scope")
        req(active.get("level")=="build-level1-preflight","Tier3 round5 Level1 preflight")
        req(active.get("trigger",{}).get("workflow_run")==35818120201,"Tier3 round5 trigger run")
        req(active.get("source_changed_nodes")==["kio"] and active.get("provider_closure_only_nodes")==[],"Tier3 round5 remediation classes")
        req(active.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2"},"Tier3 round5 KIO revision")
        req(active.get("next_gate")=="tier3-level1-kio-materialization","Tier3 round5 next gate")
    elif round_no==4:
        req(active_nodes=={"kwallet"},"Tier3 round4 failure set")
        req(active.get("trigger",{}).get("workflow_run")==35813710318,"Tier3 round4 trigger run")
        req(active.get("source_changed_nodes")==["kwallet"],"Tier3 round4 source-changed set")
        req(active.get("provider_closure_only_nodes")==[],"Tier3 round4 closure-only set")
        req(active.get("candidate_package_versions")=={"kwallet":"6.30.0-0supralinux4"},"Tier3 round4 package revision")
    elif round_no==3:
        req(active_nodes=={"kjobwidgets","kwallet"},"Tier3 round3 failure set")
        req(active.get("trigger",{}).get("workflow_run")==35808764577,"Tier3 round3 trigger run")
        req(active.get("source_changed_nodes")==["kjobwidgets"],"Tier3 round3 source-changed set")
        req(active.get("provider_closure_only_nodes")==["kwallet"],"Tier3 round3 closure-only set")
        req(active.get("candidate_package_versions")=={"kjobwidgets":"6.30.0-0supralinux4","kwallet":"6.30.0-0supralinux3"},"Tier3 round3 package revisions")
    elif round_no==2:
        req(active_nodes=={"kiconthemes","kjobwidgets","kwallet"},"Tier3 round2 remediation node set")
        req(active.get("trigger",{}).get("workflow_run")==35770505868,"Tier3 round2 trigger run")
        req(active.get("candidate_package_version")=="6.30.0-0supralinux3","Tier3 round2 package revision")
    else:
        req(False,"unsupported Tier3 active remediation round")
    st=adapt.get("python_setuptools_backend",{})
    req(st.get("provider_package")=="python3-setuptools" and st.get("observed_provider_version")=="78.1.1-0.1build1" and st.get("applies_to")==["kjobwidgets"],"Tier3 KJobWidgets setuptools backend provider")
    svg=adapt.get("qt_svg_image_plugin",{})
    req(svg.get("provider_package")=="qt6-svg-plugins" and svg.get("observed_provider_version")=="6.10.2-2" and svg.get("applies_to")==["kiconthemes"],"Tier3 KIconThemes SVG image plugin provider")

python_nodes={
 "kjobwidgets":("python3-kf6jobwidgets","KJobWidgets",["python3-pyside6.qtwidgets","python3-kcoreaddons"],"79a60665199ccbb54ca094e25f84839aeecde040"),
 "kxmlgui":("python3-kf6xmlgui","KXmlGui",["python3-pyside6.qtwidgets"],"9db633199d697dee4b8730dd580c37ddb5c4a699"),
}

for node_id in selected:
    x=c["nodes"][node_id]
    n=nodes[node_id]
    req(x.get("contract_state")=="contract-ready",f"{node_id}: contract-ready")
    expected_versions={
        "kiconthemes":"6.30.0-0supralinux3",
        "kjobwidgets":"6.30.0-0supralinux4" if active.get("round",0)>=3 else "6.30.0-0supralinux3",
        "kwallet":"6.30.0-0supralinux4" if active.get("round",0)>=4 else "6.30.0-0supralinux3",
        "kdav":"6.30.0-0supralinux2",
        "krunner":"6.30.0-0supralinux2",
        "kio":"6.30.0-0supralinux2" if active.get("round")==5 else "6.30.0-0supralinux1",
    }
    expected_version=expected_versions.get(node_id,"6.30.0-0supralinux1")
    req(x.get("package_version_candidate")==expected_version,f"{node_id}: package version")
    tr=x.get("technical_references",{})
    req(x.get("compatibility_binary_packages")==tr.get("debian",{}).get("binary_packages"),f"{node_id}: compatibility binary identity")
    req(tr.get("ubuntu",{}).get("binary_packages")==tr.get("debian",{}).get("binary_packages"),f"{node_id}: Ubuntu/Debian binary identity")
    baseline=x.get("packaging_baseline",{})
    req(baseline.get("provider")=="debian-sid" and baseline.get("source_version")=="6.30.0-1",f"{node_id}: Debian 6.30 baseline")
    req(baseline.get("tree_sha256")==c.get("packaging_trees",{}).get(node_id,{}).get("debian",{}).get("tree_sha256"),f"{node_id}: baseline tree pin")
    req(x.get("selected_profile",{}).get("BUILD_TESTING") is True,f"{node_id}: BUILD_TESTING required")
    tp=x.get("test_policy",{})
    req(tp.get("upstream_tests_required") is True and tp.get("failures_fatal") is True,f"{node_id}: fatal upstream tests")
    packaging=n.get("packaging",{})
    if n.get("state")=="PASS":
        req(packaging.get("state")=="PASS" and packaging.get("downstream_eligible") is True,f"{node_id}: promoted package PASS")
    elif node_id=="knewstuff" and packaging.get("state")=="runtime-validation-required":
        req(n.get("state")=="pending" and packaging.get("downstream_eligible") is False,f"{node_id}: runtime validation pending")
    else:
        req(n.get("state")=="pending" and packaging.get("downstream_eligible") is False,f"{node_id}: package remains pending")
    planning=n.get("planning",{})
    req(planning.get("readiness") in {"package-contract-ready","materialized","retained-pass","runtime-validation-required"},f"{node_id}: materialization readiness")
    req(planning.get("package_contract") in {"not-materialized","materialized","retained-pass"},f"{node_id}: materialization lifecycle")
    req(node_id in d.get("nodes",{}),f"{node_id}: KDE dependency contract exists")

    additions=x.get("supralinux_additional_binary_packages",[])
    if node_id in python_nodes:
        package,module,providers,blob=python_nodes[node_id]
        req(additions==[package],f"{node_id}: Python package")
        req(x.get("target_binary_packages")==x.get("compatibility_binary_packages")+[package],f"{node_id}: target binary set")
        req(x.get("selected_profile",{}).get("BUILD_PYTHON_BINDINGS") is True,f"{node_id}: Python bindings ON")
        req(x.get("python_module")==module,f"{node_id}: Python module")
        req(x.get("python_runtime_contract",{}).get("provider_packages")==providers,f"{node_id}: Python runtime providers")
        req(any(q.get("classification")=="upstream-feature-restoration" and q.get("upstream_blob")==blob for q in x.get("contract_decisions",[])),f"{node_id}: upstream Python evidence")
    else:
        req(additions==[],f"{node_id}: unexpected extra binary package")
        req(x.get("target_binary_packages")==x.get("compatibility_binary_packages"),f"{node_id}: target binary set")

kio=c["nodes"]["kio"]
req(kio.get("selected_profile",{}).get("WITH_WAYLAND") is True,"KIO Wayland Linux profile")
req(any(q.get("package")=="kio6" and q.get("value")=="kwallet6" for q in kio.get("binary_relation_overrides",[])),"KIO KWallet runtime provider")
req("kwallet" in d["nodes"]["kio"]["frameworks"]["selected_linux_profile"],"KIO upstream KWallet selected profile")
if active.get("round")==5:
    rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in kio.get("source_build_relation_overrides",[])]
    req(rel==[("remove","libkf6auth-dev"),("remove","libkf6configwidgets-dev")],"KIO round5 false-edge removals")
    repl=kio.get("rules_text_replacements",[])
    req(len(repl)==1 and repl[0].get("old")=="ifneq (linux,$(DEB_HOST_ARCH_OS))" and repl[0].get("new")=="ifeq (linux,$(DEB_HOST_ARCH_OS))","KIO round5 Linux Wayland rules correction")
    req(kio.get("reference_patch_suppression_overrides",{}).get("reverse_and_drop")==["report_error_removing_dirs"],"KIO round5 upstream behavior restoration")

kdesu=c["nodes"]["kdesu"]
req(kdesu.get("selected_profile",{}).get("KDESU_USE_SUDO_DEFAULT") is True,"KDESu Ubuntu integration")
req(any(q.get("classification")=="base-integration-exception" and q.get("upstream_default") is False for q in kdesu.get("contract_decisions",[])),"KDESu exception documentation")

purpose=c["nodes"]["purpose"]
req(any(q.get("action")=="preserve-ubuntu-optional-integration" and q.get("value")=="Suggests: kdeconnect" for q in purpose.get("binary_relation_overrides",[])),"Purpose optional KDE Connect integration")
req(set(d["nodes"]["purpose"]["frameworks"]["qml_required"])=={"prison","kitemmodels","kcmutils"},"Purpose upstream QML contract")

canonical=t.get("discovery_policy",{})
req(canonical.get("phase") in {"materialization","build-campaign-planning","build-level0","build-level1-planning"},"Tier3 canonical materialization/build-planning phase")
req(canonical.get("package_contracts")=="PASS","Tier3 canonical contract PASS")
req(canonical.get("package_builds") in {"not-authorized-before-tier3-materialization","not-authorized-before-tier3-build-campaign","tier3-level0-authorized","tier3-level0-remediation-pending","tier3-level1-not-authorized-before-planning","tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation"},"Tier3 build gate")
if active:
    ar=t.get("active_remediation",{})
    req(ar.get("round")==active.get("round") and set(ar.get("nodes",[]))==active_nodes,"Tier3 canonical remediation linkage")
    if active.get("round")==5:
        req(ar.get("level")=="build-level1-preflight","Tier3 round5 canonical Level1 preflight")
        req(ar.get("source_materialization_nodes")==["kio"] and ar.get("provider_closure_only_nodes")==[],"Tier3 round5 canonical source scope")
        req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2"},"Tier3 round5 canonical revision")
        req(canonical.get("phase")=="build-level1-planning" and canonical.get("package_builds") in {"tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation"},"Tier3 round5 canonical gate")
        req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 round5 canonical execution pause")
        req(ar.get("trigger_workflow_run")==35818120201,"Tier3 round5 canonical trigger")
        if canonical.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(ar.get("status")=="materialization-PASS-pending-level1-planning-validation","Tier3 round5 promoted canonical state")
            req(ar.get("materialization_workflow_run")==35825070347 and ar.get("materialization_commit")=="fbde9a53e357a138f4d74d7905230c7859e20444","Tier3 round5 materialization evidence")
            req(ar.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round5 planning validation gate")
        else:
            req(ar.get("status")=="materialization-pending-ci" and ar.get("next_gate")=="tier3-level1-kio-materialization","Tier3 round5 pending canonical state")
    elif active.get("round")==4:
        req(ar.get("source_materialization_nodes")==["kwallet"],"Tier3 round4 canonical source materialization set")
        req(ar.get("provider_closure_only_nodes")==[],"Tier3 round4 canonical provider closure set")
        req(ar.get("materialization_workflow_run")==35817654811 and ar.get("materialization_commit")=="1a9a4ba82b4aac9f1df9f6457faef8b905dd17cf","Tier3 round4 promoted materialization evidence")
        if canonical.get("package_builds")=="tier3-level1-not-authorized-before-planning":
            req(ar.get("status")=="attempt5-complete" and ar.get("execution_authorized") is False,"Tier3 Attempt5 closed canonical state")
            req(ar.get("validation_workflow_run")==35818120201 and ar.get("validation_commit")=="0599266fd5fc9869002629b3778d71f1e76bbdc1","Tier3 Attempt5 closure evidence")
            req(ar.get("canonical_promotions")==11 and ar.get("runtime_pending_nodes")==["knewstuff"],"Tier3 Attempt5 promotion summary")
            req(ar.get("next_gate")=="tier3-build-level1-planning","Tier3 Level1 planning next gate")
        elif ar.get("current_attempt")==5:
            req(canonical.get("package_builds")=="tier3-level0-authorized","Tier3 attempt5 build authorization")
            req(ar.get("status")=="level0-rerun-active" and ar.get("execution_authorized") is True,"Tier3 attempt5 canonical remediation state")
            req(ar.get("activation_policy_workflow_run")==35817928654,"Tier3 attempt5 activation evidence")
            req(ar.get("next_gate")=="tier3-build-level0-attempt5","Tier3 attempt5 canonical next gate")
        else:
            req(canonical.get("package_builds")=="tier3-level0-remediation-pending","Tier3 round4 build pause")
            req(ar.get("execution_authorized") is False,"Tier3 round4 execution pause")
            if active.get("status")=="materialization-PASS":
                req(ar.get("status")=="materialization-PASS-pending-level0-attempt5-activation","Tier3 round4 promoted canonical state")
                req(ar.get("next_gate")=="tier3-build-level0-attempt5-activation-validation","Tier3 round4 activation validation gate")
            else:
                req(ar.get("status")=="materialization-pending-ci","Tier3 round4 pending canonical state")
                req(ar.get("next_gate")=="tier3-round4-kwallet-materialization","Tier3 round4 canonical next gate")
    elif active.get("round")==3:
        req(ar.get("source_materialization_nodes")==["kjobwidgets"],"Tier3 round3 canonical source materialization set")
        req(ar.get("provider_closure_only_nodes")==["kwallet"],"Tier3 round3 canonical provider closure set")
        if ar.get("current_attempt")==4:
            req(canonical.get("package_builds")=="tier3-level0-authorized","Tier3 attempt4 build authorization")
            req(ar.get("status")=="level0-rerun-active" and ar.get("execution_authorized") is True,"Tier3 attempt4 canonical remediation state")
            req(ar.get("materialization_workflow_run")==35812918054 and ar.get("materialization_commit")=="a57c13059dfc206ddf57390e1cd0cfd280471965","Tier3 attempt4 materialization evidence")
            req(ar.get("activation_policy_workflow_run")==35813396247,"Tier3 attempt4 activation evidence")
            req(ar.get("next_gate")=="tier3-build-level0-attempt4","Tier3 attempt4 canonical next gate")
        elif active.get("status")=="materialization-PASS":
            req(canonical.get("package_builds")=="tier3-level0-remediation-pending","Tier3 round3 build pause")
            req(ar.get("execution_authorized") is False,"Tier3 round3 execution pause")
            req(ar.get("status")=="materialization-PASS-pending-level0-attempt4-activation","Tier3 round3 promoted canonical state")
            req(ar.get("materialization_workflow_run")==35812918054 and ar.get("materialization_commit")=="a57c13059dfc206ddf57390e1cd0cfd280471965","Tier3 round3 promoted materialization evidence")
            req(ar.get("next_gate")=="tier3-build-level0-attempt4-activation-validation","Tier3 round3 activation validation gate")
        else:
            req(canonical.get("package_builds")=="tier3-level0-remediation-pending","Tier3 round3 build pause")
            req(ar.get("execution_authorized") is False,"Tier3 round3 execution pause")
            req(ar.get("status")=="materialization-pending-ci","Tier3 round3 pending canonical state")
            req(ar.get("next_gate")=="tier3-round3-kjobwidgets-materialization","Tier3 round3 canonical next gate")
    elif ar.get("current_attempt")==3:
        req(canonical.get("package_builds")=="tier3-level0-authorized","Tier3 attempt3 build authorization")
        req(ar.get("status")=="level0-rerun-active" and ar.get("execution_authorized") is True,"Tier3 attempt3 canonical remediation state")
        req(ar.get("activation_policy_workflow_run")==35807934729,"Tier3 attempt3 activation evidence")
        req(ar.get("next_gate")=="tier3-build-level0-attempt3","Tier3 attempt3 canonical next gate")
    else:
        req(canonical.get("package_builds")=="tier3-level0-remediation-pending","Tier3 round2 build pause")
        req(ar.get("execution_authorized") is False,"Tier3 round2 execution pause")
req(t.get("support_components",{}).get("next_gate") in {"tier3-materialization","tier3-build-campaign-planning","tier3-build-level0","tier3-build-level1-planning"},"Tier3 next gate")
req(c.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

for path in (
 "docs/kde-tier3-contract-decisions.md",
 "docs/kde-tier3-package-contracts.md",
):
    req((ROOT/path).exists(),f"missing Tier3 contract-decision documentation: {path}")


if active:
    rel={
      node:[(x.get("action"),x.get("package") or x.get("relation")) for x in c["nodes"][node].get("source_build_relation_overrides",[])]
      for node in ("kiconthemes","kjobwidgets","kwallet")
    }
    req(rel["kiconthemes"]==[("remove","libkf6configwidgets-dev"),("ensure","qt6-svg-plugins <!nocheck>")],"KIconThemes retained round2 relations")
    req(rel["kjobwidgets"]==[("ensure","python3-build"),("ensure","python3-setuptools")],"KJobWidgets retained provider relations")
    req(rel["kwallet"]==[("ensure","libkf6doctools-dev (>= 6.30.0~)")],"KWallet retained KDocTools relation")
    support=c["nodes"]["kwallet"].get("support_provider_requirements",[])
    req(len(support)==1 and support[0].get("id")=="kdoctools" and support[0].get("artifact_id")==10682066198,"KWallet KDocTools support contract")
    if active.get("round") in {3,4,5}:
        additions=c["nodes"]["kjobwidgets"].get("symbol_template_additions",[])
        req(len(additions)==1 and additions[0].get("symbol")=="_ZSt19piecewise_construct@Base","KJobWidgets retained round3 symbols addition")
        req(additions and additions[0].get("tags")==["optional"] and additions[0].get("minimal_version")=="6.30.0","KJobWidgets retained optional symbol semantics")
        closure=c["nodes"]["kwallet"].get("support_provider_closure_requirements",[])
        req(len(closure)==1 and closure[0].get("retained_input_id")=="karchive","KWallet retained KArchive provider closure")
        req(closure and closure[0].get("kde_dependency_edge") is False and closure[0].get("artifact_id")==10364726750,"KWallet retained closure authority/evidence")
        if active.get("round")==4:
            wallet_symbols=c["nodes"]["kwallet"].get("symbol_template_additions",[])
            req(len(wallet_symbols)==1 and wallet_symbols[0].get("package")=="libkf6walletbackend6","KWallet round4 symbols package")
            req(wallet_symbols and wallet_symbols[0].get("soname")=="libKF6WalletBackend.so.6","KWallet round4 symbols SONAME")
            req(wallet_symbols and wallet_symbols[0].get("symbol")=="_ZSt19piecewise_construct@Base","KWallet round4 symbols identity")
            req(wallet_symbols and wallet_symbols[0].get("tags")==["optional"] and wallet_symbols[0].get("minimal_version")=="6.30.0","KWallet round4 optional symbol semantics")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 package-contract decisions: PASS")
print("nodes=20")
print("next_gate="+t.get("support_components",{}).get("next_gate","unknown"))

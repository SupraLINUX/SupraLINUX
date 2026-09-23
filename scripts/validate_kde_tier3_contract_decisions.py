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
req(pb.get("provider_package")=="python3-build" and pb.get("applies_to")==["kjobwidgets","kxmlgui"],"Tier3 Python build frontend provider")

active=c.get("active_remediation",{})
active_nodes=set(active.get("trigger",{}).get("failed_nodes",active.get("trigger",{}).get("affected_nodes",[])))
if active:
    round_no=active.get("round")
    req(active.get("status") in {"materialization-pending-ci","materialization-PASS","materialization-PASS-attempt3-active","provider-closure-pending-attempt2-activation-validation","provider-closure-PASS"},"Tier3 active remediation state")
    if round_no==8:
        req(active_nodes=={"kio","kxmlgui"},"Tier3 round8 Level1 failure set")
        req(active.get("level")=="build-level1","Tier3 round8 Level1 identity")
        req(active.get("trigger",{}).get("workflow_run")==35887558758 and active.get("trigger",{}).get("commit")=="7583ba2ffcf7f91a1ea061c2e8c0cecd9f031d94","Tier3 round8 trigger")
        req(active.get("trigger",{}).get("level1_result")=="0 workflow SUCCESS / 2 FAIL","Tier3 round8 Attempt3 result")
        req(active.get("source_changed_nodes")==["kio","kxmlgui"] and active.get("provider_closure_only_nodes")==[],"Tier3 round8 source-remediation classes")
        req(active.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"},"Tier3 round8 package revisions")
        if active.get("status")=="materialization-PASS":
            ev2=active.get("evidence",{})
            req(ev2.get("workflow_run")==35894317888 and ev2.get("commit")=="65f5ba76a913e7acf619eb9fee86e878e2914415","Tier3 round8 materialization evidence")
            req(ev2.get("artifacts",{}).get("kio",{}).get("artifact_id")==10766471076 and ev2.get("artifacts",{}).get("kxmlgui",{}).get("artifact_id")==10766665506,"Tier3 round8 materialization artifacts")
            req(active.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round8 promoted next gate")
        else:
            req(active.get("status")=="materialization-pending-ci" and active.get("next_gate")=="tier3-round8-level1-materialization","Tier3 round8 pending next gate")
        pol=active.get("policy",{})
        req(pol.get("package_revision_bump_required_for_packaging_changes") is True and pol.get("rematerialize_only_changed_nodes") is True and pol.get("kde_dependency_graph_unchanged") is True,"Tier3 round8 remediation policy")
        ev=active.get("failure_evidence",{}); root=ev.get("rootfs",{})
        req(root.get("artifact_id")==10763606519 and root.get("artifact_sha256")=="bf1fe0caaf73f0595d94c75b01f560f2913511bcafe8efe6fa81d8cc2bc0aa67" and root.get("rootfs_sha256")=="bd00be95fb5b9446a527ea155d625bd7c1cfd9ff7a0c8e59ceef118b421c11b6","Tier3 round8 rootfs evidence")
        req(ev.get("kio",{}).get("job_id")==107272258383 and ev.get("kio",{}).get("artifact_id")==10763498649 and ev.get("kio",{}).get("failure_substage")=="ctest/upstream-test-environment-followup","Tier3 round8 KIO failure evidence")
        req(ev.get("kxmlgui",{}).get("job_id")==107272258358 and ev.get("kxmlgui",{}).get("artifact_id")==10763747234 and ev.get("kxmlgui",{}).get("failure_substage")=="ctest/qt-platform","Tier3 round8 KXMLGui failure evidence")
    elif round_no==7:
        req(active_nodes=={"kio","kxmlgui"},"Tier3 round7 Level1 failure set")
        req(active.get("level")=="build-level1","Tier3 round7 Level1 identity")
        req(active.get("trigger",{}).get("workflow_run")==35829170695 and active.get("trigger",{}).get("commit")=="897d3a864bc7ea164400c7d9de2e9c51cf6316ab","Tier3 round7 trigger")
        req(active.get("trigger",{}).get("level1_result")=="0 workflow SUCCESS / 2 FAIL","Tier3 round7 Attempt2 result")
        req(active.get("source_changed_nodes")==["kio","kxmlgui"] and active.get("provider_closure_only_nodes")==[],"Tier3 round7 source-remediation classes")
        req(active.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux3","kxmlgui":"6.30.0-0supralinux2"},"Tier3 round7 package revisions")
        if active.get("status") in {"materialization-PASS","materialization-PASS-attempt3-active"}:
            ev2=active.get("evidence",{})
            req(ev2.get("workflow_run")==35882795135 and ev2.get("commit")=="0d6c02f3f8dc41f716ba62ee7121f56371a8dc91","Tier3 round7 materialization evidence")
            req(ev2.get("artifacts",{}).get("kio",{}).get("artifact_id")==10760324592 and ev2.get("artifacts",{}).get("kxmlgui",{}).get("artifact_id")==10761208629,"Tier3 round7 materialization artifacts")
            if active.get("status")=="materialization-PASS-attempt3-active":
                req(active.get("next_gate")=="tier3-build-level1-attempt3" and active.get("activation_policy_workflow_run")==35884583361 and active.get("activation_level1_workflow_run")==35884584590,"Tier3 round7 Attempt3 contract handoff")
            else:
                req(active.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round7 promoted next gate")
        else:
            req(active.get("next_gate")=="tier3-round7-level1-materialization","Tier3 round7 next gate")
        pol=active.get("policy",{})
        req(pol.get("package_revision_bump_required_for_packaging_changes") is True and pol.get("rematerialize_only_changed_nodes") is True and pol.get("kde_dependency_graph_unchanged") is True,"Tier3 round7 remediation policy")
        ev=active.get("failure_evidence",{})
        root=ev.get("rootfs",{})
        req(root.get("artifact_id")==10736033276 and root.get("artifact_sha256")=="8576bb973423d12cdd805c37e6c8b479aedf82466e38762a5ed8cb99def6961f" and root.get("rootfs_sha256")=="170fdc81f745a8597880a6433026f9ef66bca68665bf3450d02f0de561f3abe6","Tier3 round7 rootfs evidence")
        req(ev.get("kio",{}).get("job_id")==107077795233 and ev.get("kio",{}).get("artifact_id")==10736848742 and ev.get("kio",{}).get("failure_substage")=="ctest/upstream-test-environment","Tier3 round7 KIO failure evidence")
        req(ev.get("kxmlgui",{}).get("job_id")==107077795323 and ev.get("kxmlgui",{}).get("artifact_id")==10735938957 and ev.get("kxmlgui",{}).get("failure_substage")=="cmake/python-binding-build-provider","Tier3 round7 KXMLGui failure evidence")
    elif round_no==6:
        req(active_nodes=={"kio","kxmlgui"},"Tier3 round6 Level1 failure set")
        req(active.get("level")=="build-level1","Tier3 round6 Level1 identity")
        req(active.get("trigger",{}).get("workflow_run")==35826694664 and active.get("trigger",{}).get("commit")=="e7e98703184967487198f26a488d553038756990","Tier3 round6 trigger")
        req(active.get("source_changed_nodes")==[] and set(active.get("provider_closure_only_nodes",[]))=={"kio","kxmlgui"},"Tier3 round6 closure-only classes")
        req(active.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2","kxmlgui":"6.30.0-0supralinux1"},"Tier3 round6 unchanged revisions")
        req(active.get("provider_closure_inputs")=={"kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"]},"Tier3 round6 closure inputs")
        req(active.get("canonical_failures")==0,"Tier3 round6 has no canonical package FAIL")
        if active.get("status")=="provider-closure-PASS":
            req(active.get("next_gate")=="tier3-build-level1-attempt2","Tier3 round6 active next gate")
            ev=active.get("evidence",{})
            req(ev.get("repository_policy_workflow_run")==35828634884 and ev.get("level1_validation_workflow_run")==35828634887,"Tier3 round6 provider-closure validation evidence")
            req(ev.get("commit")=="568beba8aa3dce7a3f3a51d5e91d31edb5a30523" and ev.get("provider_closure_validated") is True,"Tier3 round6 closure validation commit")
        else:
            req(active.get("next_gate")=="tier3-build-level1-attempt2-activation-validation","Tier3 round6 pending next gate")
        req(active.get("policy",{}).get("provider_closure_changes_do_not_require_source_rematerialization") is True and active.get("policy",{}).get("package_revision_unchanged") is True,"Tier3 round6 no-source policy")
    elif round_no==5:
        req(active_nodes=={"kio"},"Tier3 round5 KIO scope")
        req(active.get("level")=="build-level1-preflight","Tier3 round5 Level1 preflight")
        req(active.get("trigger",{}).get("workflow_run")==35818120201,"Tier3 round5 trigger run")
        req(active.get("source_changed_nodes")==["kio"] and active.get("provider_closure_only_nodes")==[],"Tier3 round5 remediation classes")
        req(active.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2"},"Tier3 round5 KIO revision")
        if active.get("status")=="materialization-PASS":
            req(active.get("next_gate") in {"tier3-build-level1-planning-validation","tier3-build-level1-attempt1"},"Tier3 round5 promoted next gate")
            ev=active.get("evidence",{})
            req(ev.get("workflow_run")==35825070347 and ev.get("commit")=="fbde9a53e357a138f4d74d7905230c7859e20444","Tier3 round5 promoted materialization run")
            art=ev.get("artifacts",{}).get("kio",{})
            req(art.get("job_id")==107064960565 and art.get("artifact_id")==10735250819 and art.get("artifact_sha256")=="8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106","Tier3 round5 promoted KIO artifact")
        else:
            req(active.get("next_gate")=="tier3-level1-kio-materialization","Tier3 round5 pending next gate")
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
    req(st.get("provider_package")=="python3-setuptools" and st.get("observed_provider_version")=="78.1.1-0.1build1" and st.get("applies_to")==["kjobwidgets","kxmlgui"],"Tier3 setuptools backend provider")
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
        "kio":"6.30.0-0supralinux4" if active.get("round",0)>=8 else ("6.30.0-0supralinux3" if active.get("round",0)>=7 else ("6.30.0-0supralinux2" if active.get("round",0)>=5 else "6.30.0-0supralinux1")),
        "kxmlgui":"6.30.0-0supralinux3" if active.get("round",0)>=8 else ("6.30.0-0supralinux2" if active.get("round",0)>=7 else "6.30.0-0supralinux1"),
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
if active.get("round",0)>=6:
    for node,expected in {
      "kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],
      "kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"],
    }.items():
        rows=c["nodes"][node].get("level1_provider_closure_requirements",[])
        req([x.get("retained_input_id") for x in rows]==expected,f"{node}: Level1 provider closure contract")
        req(all(x.get("kde_dependency_edge") is False and x.get("classification")=="transitive-deb-provider-closure" for x in rows),f"{node}: closure is not a KDE edge")
if active.get("round",0)>=5:
    rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in kio.get("source_build_relation_overrides",[])]
    req(("remove","libkf6auth-dev") in rel and ("remove","libkf6configwidgets-dev") in rel,"KIO retained round5 false-edge removals")
    repl=kio.get("rules_text_replacements",[])
    req(any(x.get("old")=="ifneq (linux,$(DEB_HOST_ARCH_OS))" and x.get("new")=="ifeq (linux,$(DEB_HOST_ARCH_OS))" for x in repl),"KIO retained round5 Linux Wayland rules correction")
    req(kio.get("reference_patch_suppression_overrides",{}).get("reverse_and_drop")==["report_error_removing_dirs"],"KIO retained round5 upstream behavior restoration")

if active.get("round")==8:
    rel=set((x.get("action"),x.get("package") or x.get("relation")) for x in kio.get("source_build_relation_overrides",[]))
    req(("ensure","dbus-daemon <!nocheck>") in rel and ("ensure","breeze-icon-theme (>= 4:6.30.0~) <!nocheck>") in rel,"KIO round8 retained test-environment providers")
    test_repl=[x for x in kio.get("rules_text_replacements",[]) if x.get("classification")=="upstream-test-environment-correction"]
    req(len(test_repl)==1 and "dbus-run-session -- ctest --verbose -j1" in test_repl[0].get("new",""),"KIO round8 full-suite test wrapper")
    req("QT_QPA_PLATFORM=offscreen" in test_repl[0].get("new","") and "KDECI_PLATFORM_PATH=" in test_repl[0].get("new","") and "XDG_RUNTIME_DIR=" not in test_repl[0].get("new",""),"KIO round8 runtime-directory correction")
    req(kio.get("test_environment_contract",{}).get("runtime_directory_policy")=="do-not-override-XDG_RUNTIME_DIR-use-session-default","KIO round8 runtime-directory policy")
    xnode=c["nodes"]["kxmlgui"]
    xrel=[(x.get("action"),x.get("package") or x.get("relation")) for x in xnode.get("source_build_relation_overrides",[])]
    req(xrel==[("ensure","python3-build"),("ensure","python3-setuptools")],"KXMLGui round8 retained Python build providers")
    xr=xnode.get("rules_text_replacements",[])
    req(len(xr)==1 and xr[0].get("new")=="override_dh_auto_test:\n\tQT_QPA_PLATFORM=offscreen dh_auto_test","KXMLGui round8 full-suite offscreen test wrapper")
elif active.get("round")==7:
    rel=set((x.get("action"),x.get("package") or x.get("relation")) for x in kio.get("source_build_relation_overrides",[]))
    req(("ensure","dbus-daemon <!nocheck>") in rel and ("ensure","breeze-icon-theme (>= 4:6.30.0~) <!nocheck>") in rel,"KIO round7 test-environment providers")
    test_repl=[x for x in kio.get("rules_text_replacements",[]) if x.get("classification")=="upstream-test-environment-correction"]
    req(len(test_repl)==1 and "dbus-run-session -- ctest --verbose -j1" in test_repl[0].get("new",""),"KIO round7 full-suite test wrapper")
    req("QT_QPA_PLATFORM=offscreen" in test_repl[0].get("new","") and "XDG_RUNTIME_DIR=" in test_repl[0].get("new","") and "KDECI_PLATFORM_PATH=" in test_repl[0].get("new",""),"KIO round7 deterministic test environment")
    xrel=[(x.get("action"),x.get("package") or x.get("relation")) for x in c["nodes"]["kxmlgui"].get("source_build_relation_overrides",[])]
    req(xrel==[("ensure","python3-build"),("ensure","python3-setuptools")],"KXMLGui round7 Python build providers")

kdesu=c["nodes"]["kdesu"]
req(kdesu.get("selected_profile",{}).get("KDESU_USE_SUDO_DEFAULT") is True,"KDESu Ubuntu integration")
req(any(q.get("classification")=="base-integration-exception" and q.get("upstream_default") is False for q in kdesu.get("contract_decisions",[])),"KDESu exception documentation")

purpose=c["nodes"]["purpose"]
req(any(q.get("action")=="preserve-ubuntu-optional-integration" and q.get("value")=="Suggests: kdeconnect" for q in purpose.get("binary_relation_overrides",[])),"Purpose optional KDE Connect integration")
req(set(d["nodes"]["purpose"]["frameworks"]["qml_required"])=={"prison","kitemmodels","kcmutils"},"Purpose upstream QML contract")

canonical=t.get("discovery_policy",{})
req(canonical.get("phase") in {"materialization","build-campaign-planning","build-level0","build-level1-planning","build-level1"},"Tier3 canonical materialization/build-planning phase")
req(canonical.get("package_contracts")=="PASS","Tier3 canonical contract PASS")
req(canonical.get("package_builds") in {"not-authorized-before-tier3-materialization","not-authorized-before-tier3-build-campaign","tier3-level0-authorized","tier3-level0-remediation-pending","tier3-level1-not-authorized-before-planning","tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation","tier3-level1-authorized","tier3-level1-remediation-pending-provider-closure"},"Tier3 build gate")
if active:
    ar=t.get("active_remediation",{})
    req(ar.get("round")==active.get("round") and set(ar.get("nodes",[]))==active_nodes,"Tier3 canonical remediation linkage")
    if active.get("round")==8:
        req(canonical.get("phase")=="build-level1-planning" and canonical.get("package_builds") in {"tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation"},"Tier3 round8 canonical materialization/planning gate")
        req(ar.get("level")=="build-level1" and ar.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level1-planning-validation"},"Tier3 round8 canonical Level1 state")
        req(set(ar.get("nodes",[]))=={"kio","kxmlgui"} and ar.get("source_materialization_nodes")==["kio","kxmlgui"] and ar.get("provider_closure_only_nodes")==[],"Tier3 round8 canonical source scope")
        req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"},"Tier3 round8 canonical revisions")
        req(ar.get("validation_workflow_run")==35887558758 and ar.get("validation_commit")=="7583ba2ffcf7f91a1ea061c2e8c0cecd9f031d94","Tier3 round8 canonical Attempt3 evidence")
        req(ar.get("validation_result")=="0 workflow SUCCESS / 2 FAIL" and set(ar.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and ar.get("canonical_promotions")==0,"Tier3 round8 canonical failure/no-promotion semantics")
        req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False and ar.get("current_attempt")==3 and ar.get("next_attempt")==4,"Tier3 round8 canonical execution pause")
        if canonical.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(ar.get("status")=="materialization-PASS-pending-level1-planning-validation","Tier3 round8 canonical source PASS state")
            req(ar.get("materialization_workflow_run")==35894317888 and ar.get("materialization_commit")=="65f5ba76a913e7acf619eb9fee86e878e2914415","Tier3 round8 canonical source PASS evidence")
            req(ar.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round8 canonical planning gate")
        else:
            req(ar.get("status")=="materialization-pending-ci" and ar.get("next_gate")=="tier3-round8-level1-materialization","Tier3 round8 canonical materialization gate")
    elif active.get("round")==7:
        req(canonical.get("phase") in {"build-level1-planning","build-level1"} and canonical.get("package_builds") in {"tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation","tier3-level1-authorized"},"Tier3 round7 canonical materialization/planning/build gate")
        req(ar.get("level")=="build-level1" and ar.get("status") in {"materialization-pending-ci","materialization-PASS-pending-level1-planning-validation","level1-active-pending-ci"},"Tier3 round7 canonical Level1 state")
        req(set(ar.get("nodes",[]))=={"kio","kxmlgui"} and ar.get("source_materialization_nodes")==["kio","kxmlgui"] and ar.get("provider_closure_only_nodes")==[],"Tier3 round7 canonical source scope")
        req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux3","kxmlgui":"6.30.0-0supralinux2"},"Tier3 round7 canonical revisions")
        req(ar.get("validation_workflow_run")==35829170695 and ar.get("validation_commit")=="897d3a864bc7ea164400c7d9de2e9c51cf6316ab","Tier3 round7 canonical Attempt2 evidence")
        req(ar.get("validation_result")=="0 workflow SUCCESS / 2 FAIL" and set(ar.get("remaining_failed_nodes",[]))=={"kio","kxmlgui"} and ar.get("canonical_promotions")==0,"Tier3 round7 canonical failure/no-promotion semantics")
        if canonical.get("package_builds")=="tier3-level1-authorized":
            req(ar.get("status")=="level1-active-pending-ci" and ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True,"Tier3 round7 Attempt3 canonical active state")
            req(ar.get("current_attempt")==3 and ar.get("activation_policy_workflow_run")==35884583361 and ar.get("activation_level1_workflow_run")==35884584590,"Tier3 round7 Attempt3 canonical validation")
            req(ar.get("activation_commit")=="a562a145ba212349d725fad3e98a9dcb9c6c2ae0" and ar.get("next_gate")=="tier3-build-level1-attempt3","Tier3 round7 Attempt3 canonical gate")
        elif canonical.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 round7 canonical execution pause")
            req(ar.get("materialization_workflow_run")==35882795135 and ar.get("materialization_commit")=="0d6c02f3f8dc41f716ba62ee7121f56371a8dc91","Tier3 round7 canonical source PASS evidence")
            req(ar.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round7 canonical planning-validation gate")
        else:
            req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 round7 canonical execution pause")
            req(ar.get("next_gate")=="tier3-round7-level1-materialization","Tier3 round7 canonical next gate")
    elif active.get("round")==6:
        req(ar.get("level")=="build-level1","Tier3 round6 canonical Level1")
        req(set(ar.get("nodes",[]))=={"kio","kxmlgui"} and ar.get("source_materialization_nodes")==[] and set(ar.get("provider_closure_only_nodes",[]))=={"kio","kxmlgui"},"Tier3 round6 canonical closure-only scope")
        req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2","kxmlgui":"6.30.0-0supralinux1"},"Tier3 round6 canonical revisions")
        req(ar.get("provider_closure_inputs")=={"kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"]},"Tier3 round6 canonical complete closure")
        req(ar.get("validation_workflow_run")==35826694664 and ar.get("validation_result")=="2 raw workflow FAIL / 0 canonical FAIL","Tier3 round6 canonical raw/canonical evidence")
        req(ar.get("raw_failed_nodes")==["kio","kxmlgui"] and ar.get("remaining_failed_nodes")==[] and ar.get("canonical_failures")==0,"Tier3 round6 canonical no current FAIL")
        if canonical.get("package_builds")=="tier3-level1-authorized":
            req(canonical.get("phase")=="build-level1","Tier3 round6 active phase")
            req(ar.get("status")=="level1-active-pending-ci","Tier3 round6 active canonical state")
            req(ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True,"Tier3 round6 active execution authorization")
            req(ar.get("current_attempt")==2,"Tier3 round6 Attempt2 marker")
            req(ar.get("activation_policy_workflow_run")==35828634884 and ar.get("activation_level1_workflow_run")==35828634887,"Tier3 round6 Attempt2 validation evidence")
            req(ar.get("activation_commit")=="568beba8aa3dce7a3f3a51d5e91d31edb5a30523","Tier3 round6 Attempt2 validation commit")
            req(ar.get("next_gate")=="tier3-build-level1-attempt2","Tier3 round6 active gate")
        else:
            req(canonical.get("phase")=="build-level1-planning" and canonical.get("package_builds")=="tier3-level1-remediation-pending-provider-closure","Tier3 round6 canonical gate")
            req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 round6 canonical execution pause")
            req(ar.get("next_attempt")==2 and ar.get("next_gate")=="tier3-build-level1-attempt2-activation-validation","Tier3 round6 canonical evidence/gate")
    elif active.get("round")==5:
        req(ar.get("level")=="build-level1-preflight","Tier3 round5 canonical Level1 preflight")
        req(ar.get("source_materialization_nodes")==["kio"] and ar.get("provider_closure_only_nodes")==[],"Tier3 round5 canonical source scope")
        req(ar.get("candidate_package_versions")=={"kio":"6.30.0-0supralinux2"},"Tier3 round5 canonical revision")
        req(canonical.get("phase") in {"build-level1-planning","build-level1"} and canonical.get("package_builds") in {"tier3-level1-remediation-pending-materialization","tier3-level1-source-PASS-pending-planning-validation","tier3-level1-authorized"},"Tier3 round5 canonical gate")
        req(ar.get("trigger_workflow_run")==35818120201,"Tier3 round5 canonical trigger")
        if canonical.get("package_builds")=="tier3-level1-authorized":
            req(ar.get("status")=="level1-active-pending-ci","Tier3 round5 active Level1 state")
            req(ar.get("execution_authorized") is True and ar.get("level1_execution_authorized") is True,"Tier3 round5 active execution authorization")
            req(ar.get("current_attempt")==1 and ar.get("planning_policy_workflow_run")==35826072726,"Tier3 Level1 attempt/planning evidence")
            req(ar.get("next_gate")=="tier3-build-level1-attempt1","Tier3 Level1 attempt1 gate")
        elif canonical.get("package_builds")=="tier3-level1-source-PASS-pending-planning-validation":
            req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 round5 canonical execution pause")
            req(ar.get("status")=="materialization-PASS-pending-level1-planning-validation","Tier3 round5 promoted canonical state")
            req(ar.get("materialization_workflow_run")==35825070347 and ar.get("materialization_commit")=="fbde9a53e357a138f4d74d7905230c7859e20444","Tier3 round5 materialization evidence")
            req(ar.get("next_gate")=="tier3-build-level1-planning-validation","Tier3 round5 planning validation gate")
        else:
            req(ar.get("execution_authorized") is False and ar.get("level1_execution_authorized") is False,"Tier3 round5 pending execution pause")
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
req(t.get("support_components",{}).get("next_gate") in {"tier3-materialization","tier3-build-campaign-planning","tier3-build-level0","tier3-build-level1-planning","tier3-build-level1"},"Tier3 next gate")
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
    if active.get("round",0) >= 3:
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

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

req(c.get("state")=="contracts-ready","Tier3 contracts must be ready")
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

python_nodes={
 "kjobwidgets":("python3-kf6jobwidgets","KJobWidgets",["python3-pyside6.qtwidgets","python3-kcoreaddons"],"79a60665199ccbb54ca094e25f84839aeecde040"),
 "kxmlgui":("python3-kf6xmlgui","KXmlGui",["python3-pyside6.qtwidgets"],"9db633199d697dee4b8730dd580c37ddb5c4a699"),
}

for node_id in selected:
    x=c["nodes"][node_id]
    n=nodes[node_id]
    req(x.get("contract_state")=="contract-ready",f"{node_id}: contract-ready")
    req(x.get("package_version_candidate")=="6.30.0-0supralinux1",f"{node_id}: package version")
    tr=x.get("technical_references",{})
    req(x.get("compatibility_binary_packages")==tr.get("debian",{}).get("binary_packages"),f"{node_id}: compatibility binary identity")
    req(tr.get("ubuntu",{}).get("binary_packages")==tr.get("debian",{}).get("binary_packages"),f"{node_id}: Ubuntu/Debian binary identity")
    baseline=x.get("packaging_baseline",{})
    req(baseline.get("provider")=="debian-sid" and baseline.get("source_version")=="6.30.0-1",f"{node_id}: Debian 6.30 baseline")
    req(baseline.get("tree_sha256")==c.get("packaging_trees",{}).get(node_id,{}).get("debian",{}).get("tree_sha256"),f"{node_id}: baseline tree pin")
    req(x.get("selected_profile",{}).get("BUILD_TESTING") is True,f"{node_id}: BUILD_TESTING required")
    tp=x.get("test_policy",{})
    req(tp.get("upstream_tests_required") is True and tp.get("failures_fatal") is True,f"{node_id}: fatal upstream tests")
    req(n.get("state")=="pending" and n.get("packaging",{}).get("downstream_eligible") is False,f"{node_id}: package state unchanged")
    planning=n.get("planning",{})
    req(planning.get("readiness")=="package-contract-ready",f"{node_id}: materialization readiness")
    req(planning.get("package_contract")=="not-materialized",f"{node_id}: not materialized")
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

kdesu=c["nodes"]["kdesu"]
req(kdesu.get("selected_profile",{}).get("KDESU_USE_SUDO_DEFAULT") is True,"KDESu Ubuntu integration")
req(any(q.get("classification")=="base-integration-exception" and q.get("upstream_default") is False for q in kdesu.get("contract_decisions",[])),"KDESu exception documentation")

purpose=c["nodes"]["purpose"]
req(any(q.get("action")=="preserve-ubuntu-optional-integration" and q.get("value")=="Suggests: kdeconnect" for q in purpose.get("binary_relation_overrides",[])),"Purpose optional KDE Connect integration")
req(set(d["nodes"]["purpose"]["frameworks"]["qml_required"])=={"prison","kitemmodels","kcmutils"},"Purpose upstream QML contract")

canonical=t.get("discovery_policy",{})
req(canonical.get("phase")=="materialization","Tier3 canonical materialization phase")
req(canonical.get("package_contracts")=="PASS","Tier3 canonical contract PASS")
req(canonical.get("package_builds")=="not-authorized-before-tier3-materialization","Tier3 build gate")
req(t.get("support_components",{}).get("next_gate")=="tier3-materialization","Tier3 next gate")
req(c.get("stable_promotion_requires_explicit_user_approval") is True,"stable approval policy")

for path in (
 "docs/kde-tier3-contract-decisions.md",
 "docs/kde-tier3-package-contracts.md",
):
    req((ROOT/path).exists(),f"missing Tier3 contract-decision documentation: {path}")

if errors:
    for e in errors: print("ERROR:",e,file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 3 package-contract decisions: PASS")
print("nodes=20")
print("next_gate=tier3-materialization")

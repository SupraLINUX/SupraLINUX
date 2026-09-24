#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def req(value, message):
    if not value:
        errors.append(message)

def load(path):
    return json.loads((ROOT / path).read_text())

m = load("manifests/kde-tier3-materialization.json")
c = load("manifests/kde-tier3-package-contracts.json")
t = load("manifests/kde-frameworks-tier3.json")

selected = m.get("selected_nodes", [])
canonical = {x.get("id"): x for x in t.get("nodes", [])}
contracts = c.get("nodes", {})

req(m.get("schema") == 1, "Tier3 materialization schema")
req(m.get("authority") == "kde-upstream", "Tier3 materialization source authority")
req(m.get("role") == "tier3-source-materialization", "Tier3 materialization role")
req(m.get("frameworks_series") == "6.30.0", "Tier3 materialization series")
req(m.get("contract_manifest") == "manifests/kde-tier3-package-contracts.json", "Tier3 materialization contract linkage")
req(m.get("canonical_manifest") == "manifests/kde-frameworks-tier3.json", "Tier3 materialization canonical linkage")
req(m.get("state") in {"pending-ci", "PASS", "remediation-pending-ci"}, "Tier3 materialization lifecycle")
req(m.get("package_attempted") is False and m.get("package_state_effect") == "none", "materialization cannot claim package attempt/PASS")
req(m.get("source_policy") == "verify-kde-upstream-tarball-and-pinned-debian-6.30-packaging-before-adaptation", "Tier3 source/reference policy")
req(m.get("stable_promotion_requires_explicit_user_approval") is True, "stable promotion approval policy")

req(len(selected) == 20, "Tier3 materialization selected node count")
req(selected == c.get("selected_nodes"), "Tier3 materialization selection must equal contract selection")
req(set(selected) == set(canonical) == set(contracts), "Tier3 materialization node identity set")
req(set(m.get("nodes", {})) == set(selected), "Tier3 materialization node state set")

adapt = m.get("common_adaptations", {})
req(adapt.get("maintainer") == "SupraLINUX Build System <build@supralinux.invalid>", "Tier3 materialization maintainer")
req(adapt.get("remove_reference_uploaders") is True and adapt.get("remove_reference_vcs_fields") is True, "reference maintainer/VCS metadata removal")
dh = adapt.get("debhelper_compat", {})
req(dh.get("from") == "debhelper-compat (= 14)" and dh.get("to") == "debhelper-compat (= 13)", "Resolute debhelper provider adaptation")
req(adapt.get("changelog_distribution") == "resolute", "Resolute changelog target")
req(adapt.get("build_testing") == "force-on", "BUILD_TESTING policy")
req(adapt.get("reference_test_suppressions") == "remove-noop-suppression", "reference test suppression policy")

capture = c.get("packaging_tree_capture", {})
decision = c.get("contract_decision", {})
req(capture.get("status") == "PASS", "materialization requires packaging-tree PASS")
req(decision.get("status") == "PASS", "materialization requires contract-decision PASS")
req(decision.get("materialization_authorized") is True, "materialization authorization")
req(decision.get("package_build_authorized") is False, "contract gate never authorizes binary builds")
req(c.get("source_authority") == "kde-upstream" and c.get("packaging_authority") == "supralinux", "authority/provider separation")

provider = c.get("provider_adaptations", {}).get("ubuntu-resolute", {})
req(provider.get("debhelper_compat", {}).get("selected_level") == 13, "Resolute debhelper level")
req(provider.get("changelog_distribution", {}).get("selected") == "resolute", "Resolute distribution provider")
shiboken = provider.get("shiboken_clang_discovery", {})
req(shiboken.get("provider_packages") == ["llvm-dev", "libclang-common-21-dev"], "Shiboken clang provider closure")
req(shiboken.get("applies_to") == ["kjobwidgets", "kxmlgui"], "Shiboken adaptation scope")

# Round 1 is immutable history and remains validated.
round1 = c.get("remediation", {})
round1_nodes = set(round1.get("trigger", {}).get("failed_nodes", []))
req(round1_nodes == {"kiconthemes", "kdav", "kwallet", "krunner", "kjobwidgets"}, "Tier3 round1 remediation node set")
req(round1.get("status") == "materialization-PASS", "Tier3 round1 remediation materialization PASS")
req(round1.get("evidence", {}).get("workflow_run") == 35759443440, "Tier3 round1 materialization evidence")
pb = provider.get("python_build_module", {})
req(pb.get("provider_package") == "python3-build" and pb.get("applies_to") == ["kjobwidgets","kxmlgui"], "Tier3 Python build frontend provider scope")
req(contracts["kdav"].get("source_build_relation_overrides", []) == [
    {
        "field":"Build-Depends","action":"remove","package":"kio6",
        "classification":"debian-test-provider-edge-removal",
        "rationale":"KDE 6.30 KDAV CMake/autotests require CoreAddons and I18n, not KIO; the Debian nocheck provider must not force a false KDAV→KIO build edge."
    },
    {
        "field":"Build-Depends","action":"remove","package":"libkf6kio-dev",
        "classification":"debian-test-provider-edge-removal",
        "rationale":"KDE 6.30 KDAV does not require KF6KIO; retaining this Debian Build-Depends makes upstream Level0 topology impossible."
    },
], "KDAV round1 false KIO edges remain removed")
req(contracts["krunner"].get("reference_patch_suppression_overrides", {}).get("reverse_and_drop") == ["skip-flaky-test.patch"], "KRunner upstream test restoration retained")
sym = contracts["krunner"].get("symbol_template_overrides", [])
req(len(sym) == 2 and all("optional=templinst" in x.get("add_tags", []) for x in sym), "KRunner template-symbol remediation retained")

active_c = c.get("active_remediation", {})
active_m = m.get("active_remediation", {})
active_t = t.get("active_remediation", {})
active_nodes = set(active_c.get("trigger", {}).get("failed_nodes", active_c.get("trigger", {}).get("affected_nodes", [])))
queue = m.get("remediation_queue", [])
queue_set = set(queue)

if m.get("state") == "remediation-pending-ci":
    active_round = active_c.get("round")
    req(active_round == active_m.get("round") == active_t.get("round"), "Tier3 active remediation round linkage")
    if active_round == 10:
        req(t.get("discovery_policy", {}).get("phase") == "build-level1-planning", "Tier3 round10 Level1 planning phase")
        req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level1-remediation-pending-materialization", "Tier3 round10 canonical build gate")
        req(active_t.get("execution_authorized") is False and active_t.get("level1_execution_authorized") is False, "Tier3 round10 Level1 execution pause")
    elif active_round == 9:
        req(t.get("discovery_policy", {}).get("phase") == "build-level1-planning", "Tier3 round9 Level1 planning phase")
        req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level1-remediation-pending-materialization", "Tier3 round9 canonical build gate")
        req(active_t.get("execution_authorized") is False and active_t.get("level1_execution_authorized") is False, "Tier3 round9 Level1 execution pause")
    elif active_round == 8:
        req(t.get("discovery_policy", {}).get("phase") == "build-level1-planning", "Tier3 round8 Level1 planning phase")
        req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level1-remediation-pending-materialization", "Tier3 round8 canonical build gate")
        req(active_t.get("execution_authorized") is False and active_t.get("level1_execution_authorized") is False, "Tier3 round8 Level1 execution pause")
    elif active_round == 7:
        req(t.get("discovery_policy", {}).get("phase") == "build-level1-planning", "Tier3 round7 Level1 planning phase")
        req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level1-remediation-pending-materialization", "Tier3 round7 canonical build gate")
        req(active_t.get("execution_authorized") is False and active_t.get("level1_execution_authorized") is False, "Tier3 round7 Level1 execution pause")
    elif active_round == 5:
        req(t.get("discovery_policy", {}).get("phase") == "build-level1-planning", "Tier3 round5 Level1 planning phase")
        req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level1-remediation-pending-materialization", "Tier3 round5 canonical build gate")
        req(active_t.get("execution_authorized") is False and active_t.get("level1_execution_authorized") is False, "Tier3 round5 Level1 execution pause")
    else:
        req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-remediation-pending", "Tier3 remediation canonical build gate")
        req(active_t.get("execution_authorized") is False and active_t.get("full_level0_rerun_required") is True, "Tier3 remediation binary execution pause")

    if active_round == 10:
        req(active_nodes == {"kio","kxmlgui"}, "Tier3 round10 Level1 failure set")
        req(queue == ["kio","kxmlgui"], "Tier3 round10 source materialization queue")
        req(set(active_m.get("nodes", [])) == {"kio","kxmlgui"} and set(active_t.get("nodes", [])) == {"kio","kxmlgui"}, "Tier3 round10 node linkage")
        req(active_c.get("source_changed_nodes") == ["kio","kxmlgui"] and active_c.get("provider_closure_only_nodes") == [], "Tier3 round10 contract classes")
        req(active_m.get("source_changed_nodes") == ["kio","kxmlgui"] and active_m.get("provider_closure_only_nodes") == [], "Tier3 round10 materialization classes")
        req(active_t.get("source_materialization_nodes") == ["kio","kxmlgui"] and active_t.get("provider_closure_only_nodes") == [], "Tier3 round10 canonical classes")
        req(active_c.get("trigger", {}).get("workflow_run") == 35991007820 and active_c.get("trigger", {}).get("commit") == "3197c1988e1ab86ec5010cb693064db949bfe6b0", "Tier3 round10 trigger")
        req(active_m.get("trigger_workflow_run") == 35991007820 and active_t.get("trigger_workflow_run") == 35991007820, "Tier3 round10 trigger linkage")
        versions={"kio":"6.30.0-0supralinux6","kxmlgui":"6.30.0-0supralinux5"}
        req(active_c.get("candidate_package_versions") == versions and active_m.get("candidate_package_versions") == versions and active_t.get("candidate_package_versions") == versions, "Tier3 round10 candidate revisions")
        kio_rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in contracts["kio"].get("source_build_relation_overrides",[])]
        req(kio_rel == [("remove","libkf6auth-dev"),("remove","libkf6configwidgets-dev"),("ensure","dbus-daemon <!nocheck>"),("ensure","breeze-icon-theme (>= 4:6.30.0~) <!nocheck>"),("ensure","xvfb <!nocheck>")], "KIO round10 retained test-provider relations")
        rr=contracts["kio"].get("rules_text_replacements",[])
        req(len(rr)==3 and any(x.get("classification")=="upstream-test-environment-targeted-correction" and "kiowidgets-kdirmodeltest" in x.get("new","") and "kiofilewidgets-knewfilemenutest" in x.get("new","") for x in rr), "KIO round10 targeted icon-test QPA rules")
        env=contracts["kio"].get("test_environment_contract",{})
        ov=env.get("ctest_per_test_qpa_overrides",{})
        req(set(ov)=={"kiowidgets-kdirmodeltest","kiofilewidgets-knewfilemenutest"} and all(v.get("qt_platform")=="xcb" and v.get("system_icon_theme")=="breeze" for v in ov.values()), "KIO round10 targeted QPA contract")
        kxml_rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in contracts["kxmlgui"].get("source_build_relation_overrides",[])]
        req(kxml_rel == [("ensure","python3-build"),("ensure","python3-setuptools"),("ensure","dbus-daemon <!nocheck>"),("ensure","libkf6textwidgets-dev (>= 6.30.0~) <!nocheck>")], "KXMLGui round10 exact build/test providers")
        adds=contracts["kxmlgui"].get("symbol_template_additions",[])
        req(len(adds)==1 and adds[0].get("symbol")=="_ZSt19piecewise_construct@Base" and adds[0].get("minimal_version")=="6.30.0" and adds[0].get("tags")==["optional"], "KXMLGui round10 optional template symbol")
        xr=contracts["kxmlgui"].get("rules_text_replacements",[])
        req(len(xr)==1 and xr[0].get("new")=="override_dh_auto_test:\n\tdbus-run-session -- env QT_QPA_PLATFORM=offscreen dh_auto_test", "KXMLGui round10 retained D-Bus offscreen full-suite rules")
    elif active_round == 9:
        req(active_nodes == {"kio","kxmlgui"}, "Tier3 round9 Level1 failure set")
        req(queue == ["kio","kxmlgui"], "Tier3 round9 source materialization queue")
        req(set(active_m.get("nodes", [])) == {"kio","kxmlgui"} and set(active_t.get("nodes", [])) == {"kio","kxmlgui"}, "Tier3 round9 node linkage")
        req(active_c.get("source_changed_nodes") == ["kio","kxmlgui"] and active_c.get("provider_closure_only_nodes") == [], "Tier3 round9 contract classes")
        req(active_m.get("source_changed_nodes") == ["kio","kxmlgui"] and active_m.get("provider_closure_only_nodes") == [], "Tier3 round9 materialization classes")
        req(active_t.get("source_materialization_nodes") == ["kio","kxmlgui"] and active_t.get("provider_closure_only_nodes") == [], "Tier3 round9 canonical classes")
        req(active_c.get("trigger", {}).get("workflow_run") == 35961584503 and active_c.get("trigger", {}).get("commit") == "513cb12a96c7c79ffb5790253504482a56af2e63", "Tier3 round9 trigger")
        req(active_m.get("trigger_workflow_run") == 35961584503 and active_t.get("trigger_workflow_run") == 35961584503, "Tier3 round9 trigger linkage")
        versions={"kio":"6.30.0-0supralinux5","kxmlgui":"6.30.0-0supralinux4"}
        req(active_c.get("candidate_package_versions") == versions and active_m.get("candidate_package_versions") == versions and active_t.get("candidate_package_versions") == versions, "Tier3 round9 candidate revisions")
        kio_rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in contracts["kio"].get("source_build_relation_overrides",[])]
        req(kio_rel == [("remove","libkf6auth-dev"),("remove","libkf6configwidgets-dev"),("ensure","dbus-daemon <!nocheck>"),("ensure","breeze-icon-theme (>= 4:6.30.0~) <!nocheck>"),("ensure","xvfb <!nocheck>")], "KIO round9 exact test-provider relations")
        kxml_rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in contracts["kxmlgui"].get("source_build_relation_overrides",[])]
        req(kxml_rel == [("ensure","python3-build"),("ensure","python3-setuptools"),("ensure","dbus-daemon <!nocheck>")], "KXMLGui round9 exact build/test providers")
        rr=contracts["kio"].get("rules_text_replacements",[])
        req(len(rr)==2 and "QT_QPA_PLATFORM=xcb" in rr[1].get("new","") and "QT_QPA_SYSTEM_ICON_THEME=breeze" in rr[1].get("new","") and "dbus-run-session -- xvfb-run -a" in rr[1].get("new","") and "ctest --verbose -j1" in rr[1].get("new",""), "KIO round9 Xvfb/XCB full-suite rules")
        xr=contracts["kxmlgui"].get("rules_text_replacements",[])
        req(len(xr)==1 and xr[0].get("new")=="override_dh_auto_test:\n\tdbus-run-session -- env QT_QPA_PLATFORM=offscreen dh_auto_test", "KXMLGui round9 D-Bus offscreen full-suite rules")
        env=contracts["kio"].get("test_environment_contract",{})
        req(env.get("external_network",{}).get("required") is True and env.get("ctest_parallelism")==1 and env.get("qt_platform")=="xcb" and env.get("system_icon_theme_override")=="breeze" and env.get("virtual_display",{}).get("provider_package")=="xvfb" and env.get("runtime_directory_policy")=="do-not-override-XDG_RUNTIME_DIR-use-session-default", "KIO round9 test environment contract")
        xenv=contracts["kxmlgui"].get("test_environment_contract",{})
        req(xenv.get("qt_platform")=="offscreen" and xenv.get("session_bus",{}).get("provider_package")=="dbus-daemon" and xenv.get("session_bus",{}).get("runner")=="dbus-run-session", "KXMLGui round9 test environment contract")
    elif active_round == 8:
        req(active_nodes == {"kio","kxmlgui"}, "Tier3 round8 Level1 failure set")
        req(queue == ["kio","kxmlgui"], "Tier3 round8 source materialization queue")
        req(set(active_m.get("nodes", [])) == {"kio","kxmlgui"} and set(active_t.get("nodes", [])) == {"kio","kxmlgui"}, "Tier3 round8 node linkage")
        req(active_c.get("source_changed_nodes") == ["kio","kxmlgui"] and active_c.get("provider_closure_only_nodes") == [], "Tier3 round8 contract classes")
        req(active_m.get("source_changed_nodes") == ["kio","kxmlgui"] and active_m.get("provider_closure_only_nodes") == [], "Tier3 round8 materialization classes")
        req(active_t.get("source_materialization_nodes") == ["kio","kxmlgui"] and active_t.get("provider_closure_only_nodes") == [], "Tier3 round8 canonical classes")
        req(active_c.get("trigger", {}).get("workflow_run") == 35887558758, "Tier3 round8 trigger run")
        req(active_m.get("trigger_workflow_run") == 35887558758 and active_t.get("trigger_workflow_run") == 35887558758, "Tier3 round8 trigger linkage")
        versions={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"}
        req(active_c.get("candidate_package_versions") == versions and active_m.get("candidate_package_versions") == versions and active_t.get("candidate_package_versions") == versions, "Tier3 round8 candidate revisions")
        kio_rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in contracts["kio"].get("source_build_relation_overrides",[])]
        req(kio_rel == [("remove","libkf6auth-dev"),("remove","libkf6configwidgets-dev"),("ensure","dbus-daemon <!nocheck>"),("ensure","breeze-icon-theme (>= 4:6.30.0~) <!nocheck>")], "KIO round8 retained test-provider relations")
        kxml_rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in contracts["kxmlgui"].get("source_build_relation_overrides",[])]
        req(kxml_rel == [("ensure","python3-build"),("ensure","python3-setuptools")], "KXMLGui round8 retained Python build providers")
        rr=contracts["kio"].get("rules_text_replacements",[])
        req(len(rr)==2 and "dbus-run-session -- ctest --verbose -j1" in rr[1].get("new","") and "XDG_RUNTIME_DIR=" not in rr[1].get("new",""), "KIO round8 runtime-directory correction")
        xr=contracts["kxmlgui"].get("rules_text_replacements",[])
        req(len(xr)==1 and xr[0].get("new")=="override_dh_auto_test:\n\tQT_QPA_PLATFORM=offscreen dh_auto_test", "KXMLGui round8 full-suite offscreen rules")
        env=contracts["kio"].get("test_environment_contract",{})
        req(env.get("external_network",{}).get("required") is True and env.get("ctest_parallelism")==1 and env.get("qt_platform")=="offscreen" and env.get("runtime_directory_policy")=="do-not-override-XDG_RUNTIME_DIR-use-session-default", "KIO round8 test environment contract")
    elif active_round == 7:
        req(active_nodes == {"kio","kxmlgui"}, "Tier3 round7 Level1 failure set")
        req(queue == ["kio","kxmlgui"], "Tier3 round7 source materialization queue")
        req(set(active_m.get("nodes", [])) == {"kio","kxmlgui"} and set(active_t.get("nodes", [])) == {"kio","kxmlgui"}, "Tier3 round7 node linkage")
        req(active_c.get("source_changed_nodes") == ["kio","kxmlgui"] and active_c.get("provider_closure_only_nodes") == [], "Tier3 round7 contract classes")
        req(active_m.get("source_changed_nodes") == ["kio","kxmlgui"] and active_m.get("provider_closure_only_nodes") == [], "Tier3 round7 materialization classes")
        req(active_t.get("source_materialization_nodes") == ["kio","kxmlgui"] and active_t.get("provider_closure_only_nodes") == [], "Tier3 round7 canonical classes")
        req(active_c.get("trigger", {}).get("workflow_run") == 35829170695, "Tier3 round7 trigger run")
        req(active_m.get("trigger_workflow_run") == 35829170695 and active_t.get("trigger_workflow_run") == 35829170695, "Tier3 round7 trigger linkage")
        versions={"kio":"6.30.0-0supralinux3","kxmlgui":"6.30.0-0supralinux2"}
        req(active_c.get("candidate_package_versions") == versions and active_m.get("candidate_package_versions") == versions and active_t.get("candidate_package_versions") == versions, "Tier3 round7 candidate revisions")
        kio_rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in contracts["kio"].get("source_build_relation_overrides",[])]
        req(kio_rel == [("remove","libkf6auth-dev"),("remove","libkf6configwidgets-dev"),("ensure","dbus-daemon <!nocheck>"),("ensure","breeze-icon-theme (>= 4:6.30.0~) <!nocheck>")], "KIO round7 test-provider relations")
        kxml_rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in contracts["kxmlgui"].get("source_build_relation_overrides",[])]
        req(kxml_rel == [("ensure","python3-build"),("ensure","python3-setuptools")], "KXMLGui round7 Python build providers")
        rr=contracts["kio"].get("rules_text_replacements",[])
        req(len(rr)==2 and "dbus-run-session -- ctest --verbose -j1" in rr[1].get("new",""), "KIO round7 isolated serial CTest rules")
        env=contracts["kio"].get("test_environment_contract",{})
        req(env.get("external_network",{}).get("required") is True and env.get("ctest_parallelism")==1 and env.get("qt_platform")=="offscreen", "KIO round7 test environment contract")
    elif active_round == 5:
        req(active_nodes == {"kio"}, "Tier3 round5 KIO scope")
        req(queue == ["kio"], "Tier3 round5 KIO materialization queue")
        req(set(active_m.get("nodes", [])) == {"kio"} and set(active_t.get("nodes", [])) == {"kio"}, "Tier3 round5 node linkage")
        req(active_c.get("source_changed_nodes") == ["kio"] and active_c.get("provider_closure_only_nodes") == [], "Tier3 round5 contract classes")
        req(active_m.get("source_changed_nodes") == ["kio"] and active_m.get("provider_closure_only_nodes") == [], "Tier3 round5 materialization classes")
        req(active_t.get("source_materialization_nodes") == ["kio"] and active_t.get("provider_closure_only_nodes") == [], "Tier3 round5 canonical classes")
        req(active_c.get("trigger", {}).get("workflow_run") == 35818120201, "Tier3 round5 trigger run")
        req(active_m.get("trigger_workflow_run") == 35818120201 and active_t.get("trigger_workflow_run") == 35818120201, "Tier3 round5 trigger linkage")
        req(active_c.get("candidate_package_versions") == {"kio":"6.30.0-0supralinux2"}, "Tier3 round5 contract revision")
        req(active_m.get("package_revision") == "6.30.0-0supralinux2" and active_t.get("candidate_package_versions") == {"kio":"6.30.0-0supralinux2"}, "Tier3 round5 materialization/canonical revision")
        rel=[(x.get("action"),x.get("package") or x.get("relation")) for x in contracts["kio"].get("source_build_relation_overrides",[])]
        req(rel == [("remove","libkf6auth-dev"),("remove","libkf6configwidgets-dev")], "KIO round5 false-edge removals")
        rr=contracts["kio"].get("rules_text_replacements",[])
        req(len(rr)==1 and rr[0].get("old")=="ifneq (linux,$(DEB_HOST_ARCH_OS))" and rr[0].get("new")=="ifeq (linux,$(DEB_HOST_ARCH_OS))", "KIO round5 Wayland rules correction")
        req(contracts["kio"].get("reference_patch_suppression_overrides",{}).get("reverse_and_drop")==["report_error_removing_dirs"], "KIO round5 upstream patch restoration")
    elif active_round == 4:
        req(active_nodes == {"kwallet"}, "Tier3 round4 failure set")
        req(queue == ["kwallet"], "Tier3 round4 source materialization queue")
        req(set(active_m.get("nodes", [])) == {"kwallet"}, "Tier3 round4 materialization node set")
        req(set(active_t.get("nodes", [])) == {"kwallet"}, "Tier3 round4 canonical remediation set")
        req(active_c.get("source_changed_nodes") == ["kwallet"] and active_c.get("provider_closure_only_nodes") == [], "Tier3 round4 contract remediation classes")
        req(active_m.get("source_changed_nodes") == ["kwallet"] and active_m.get("provider_closure_only_nodes") == [], "Tier3 round4 materialization classes")
        req(active_t.get("source_materialization_nodes") == ["kwallet"] and active_t.get("provider_closure_only_nodes") == [], "Tier3 round4 canonical remediation classes")
        req(active_c.get("trigger", {}).get("workflow_run") == 35813710318, "Tier3 round4 trigger run")
        req(active_m.get("trigger_workflow_run") == 35813710318 and active_t.get("trigger_workflow_run") == 35813710318, "Tier3 round4 trigger linkage")
        versions = active_c.get("candidate_package_versions", {})
        req(versions == {"kwallet":"6.30.0-0supralinux4"}, "Tier3 round4 contract versions")
        req(active_m.get("package_revision") == "6.30.0-0supralinux4", "Tier3 round4 materialization revision")
        req(active_t.get("candidate_package_versions") == versions, "Tier3 round4 canonical versions")
        additions = contracts["kwallet"].get("symbol_template_additions", [])
        req(len(additions) == 1, "KWallet round4 symbols addition count")
        if additions:
            x = additions[0]
            req(x.get("package") == "libkf6walletbackend6" and x.get("soname") == "libKF6WalletBackend.so.6", "KWallet round4 symbols package/SONAME")
            req(x.get("symbol") == "_ZSt19piecewise_construct@Base" and x.get("minimal_version") == "6.30.0", "KWallet round4 symbols identity/version")
            req(x.get("tags") == ["optional"], "KWallet round4 symbols optional tag")
        closure = contracts["kwallet"].get("support_provider_closure_requirements", [])
        req(len(closure) == 1 and closure[0].get("retained_input_id") == "karchive", "KWallet round4 retains KDocTools/KArchive closure")
    elif active_round == 3:
        req(active_nodes == {"kjobwidgets", "kwallet"}, "Tier3 round3 failure set")
        req(queue == ["kjobwidgets"], "Tier3 round3 source materialization queue")
        req(set(active_m.get("nodes", [])) == {"kjobwidgets"}, "Tier3 round3 materialization node set")
        req(set(active_t.get("nodes", [])) == {"kjobwidgets", "kwallet"}, "Tier3 round3 canonical remediation set")
        req(active_c.get("source_changed_nodes") == ["kjobwidgets"] and active_c.get("provider_closure_only_nodes") == ["kwallet"], "Tier3 round3 contract remediation classes")
        req(active_m.get("source_changed_nodes") == ["kjobwidgets"] and active_m.get("provider_closure_only_nodes") == ["kwallet"], "Tier3 round3 materialization classes")
        req(active_t.get("source_materialization_nodes") == ["kjobwidgets"] and active_t.get("provider_closure_only_nodes") == ["kwallet"], "Tier3 round3 canonical remediation classes")
        req(active_c.get("trigger", {}).get("workflow_run") == 35808764577, "Tier3 round3 trigger run")
        req(active_m.get("trigger_workflow_run") == 35808764577 and active_t.get("trigger_workflow_run") == 35808764577, "Tier3 round3 trigger linkage")
        versions = active_c.get("candidate_package_versions", {})
        req(versions == {"kjobwidgets":"6.30.0-0supralinux4","kwallet":"6.30.0-0supralinux3"}, "Tier3 round3 contract versions")
        req(active_m.get("package_revision") == "6.30.0-0supralinux4", "Tier3 round3 materialization revision")
        req(active_t.get("candidate_package_versions") == versions, "Tier3 round3 canonical versions")
        additions = contracts["kjobwidgets"].get("symbol_template_additions", [])
        req(len(additions) == 1, "KJobWidgets round3 symbols addition count")
        if additions:
            x = additions[0]
            req(x.get("package") == "libkf6jobwidgets6" and x.get("soname") == "libKF6JobWidgets.so.6", "KJobWidgets round3 symbols package/SONAME")
            req(x.get("symbol") == "_ZSt19piecewise_construct@Base" and x.get("minimal_version") == "6.30.0", "KJobWidgets round3 symbols identity/version")
            req(x.get("tags") == ["optional"], "KJobWidgets round3 symbols optional tag")
        closure = contracts["kwallet"].get("support_provider_closure_requirements", [])
        req(len(closure) == 1 and closure[0].get("provider_id") == "kdoctools" and closure[0].get("retained_input_id") == "karchive", "KWallet round3 KDocTools/KArchive closure")
        req(closure and closure[0].get("artifact_id") == 10364726750 and closure[0].get("artifact_sha256") == "0fcd8722eddf40995152df200aa576a3ff1234b8135c52e59a66f05dbc8eeb3e", "KWallet round3 KArchive closure evidence")
    elif active_round == 2:
        req(active_nodes == {"kiconthemes", "kjobwidgets", "kwallet"}, "Tier3 round2 remediation node set")
        req(queue == ["kiconthemes", "kjobwidgets", "kwallet"], "Tier3 round2 materialization queue")
        req(queue_set == active_nodes == set(active_m.get("nodes", [])) == set(active_t.get("nodes", [])), "Tier3 round2 remediation linkage")
        req(active_c.get("trigger", {}).get("workflow_run") == 35770505868, "Tier3 round2 trigger run")
    else:
        req(False, "unsupported Tier3 materialization remediation round")

    setuptools = provider.get("python_setuptools_backend", {})
    req(setuptools.get("provider_package") == "python3-setuptools", "KJobWidgets setuptools provider")
    req(setuptools.get("observed_provider_version") == "78.1.1-0.1build1", "KJobWidgets setuptools provider version")
    req(setuptools.get("applies_to") == ["kjobwidgets","kxmlgui"], "Python setuptools provider scope")
    svg = provider.get("qt_svg_image_plugin", {})
    req(svg.get("provider_package") == "qt6-svg-plugins", "KIconThemes Qt SVG plugin provider")
    req(svg.get("observed_provider_version") == "6.10.2-2", "KIconThemes Qt SVG plugin provider version")
    req(svg.get("applies_to") == ["kiconthemes"], "KIconThemes Qt SVG provider scope")
    expected_rel = {
        "kiconthemes": [("remove", "libkf6configwidgets-dev"), ("ensure", "qt6-svg-plugins <!nocheck>")],
        "kjobwidgets": [("ensure", "python3-build"), ("ensure", "python3-setuptools")],
        "kwallet": [("ensure", "libkf6doctools-dev (>= 6.30.0~)")],
        "kio": (
            [("remove","libkf6auth-dev"),("remove","libkf6configwidgets-dev"),("ensure","dbus-daemon <!nocheck>"),("ensure","breeze-icon-theme (>= 4:6.30.0~) <!nocheck>"),("ensure","xvfb <!nocheck>")]
            if active_c.get("round")==9 else
            [("remove","libkf6auth-dev"),("remove","libkf6configwidgets-dev"),("ensure","dbus-daemon <!nocheck>"),("ensure","breeze-icon-theme (>= 4:6.30.0~) <!nocheck>")]
        ),
        "kxmlgui": (
            [("ensure","python3-build"),("ensure","python3-setuptools"),("ensure","dbus-daemon <!nocheck>")]
            if active_c.get("round")==9 else
            [("ensure","python3-build"),("ensure","python3-setuptools")]
        ),
    }
    for node, expected in expected_rel.items():
        actual = [(x.get("action"), x.get("package") or x.get("relation")) for x in contracts[node].get("source_build_relation_overrides", [])]
        req(actual == expected, f"{node}: retained remediation source relation contract")
    req(contracts["kiconthemes"].get("reference_test_suppression_overrides", {}).get("rules_remove_excluded_tests") == ["kiconloader_unittest", "kiconengine_unittest"], "KIconThemes full upstream tests remain enabled")
    support_req = contracts["kwallet"].get("support_provider_requirements", [])
    req(len(support_req) == 1 and support_req[0].get("id") == "kdoctools" and support_req[0].get("artifact_id") == 10682066198, "KWallet KDocTools support-provider contract")

for node in selected:
    state = m["nodes"][node]
    contract = contracts[node]
    can = canonical[node]

    req(state.get("state") in {"pending", "materialized", "remediation-pending"}, f"{node}: materialization state")
    req(contract.get("contract_state") == "contract-ready", f"{node}: contract-ready")
    expected_candidate = state.get("candidate_package_version") if state.get("state") == "remediation-pending" else state.get("package_version")
    req(contract.get("package_version_candidate") == expected_candidate, f"{node}: candidate version")
    req(contract.get("upstream_version") == "6.30.0", f"{node}: upstream version")
    req(contract.get("source_sha256") == can.get("source_sha256"), f"{node}: KDE source SHA linkage")
    req(contract.get("technical_references", {}).get("debian", {}).get("version") == "6.30.0-1", f"{node}: exact Debian 6.30 baseline")
    req(contract.get("packaging_baseline", {}).get("provider") == "debian-sid", f"{node}: packaging baseline provider")
    req(contract.get("packaging_baseline", {}).get("tree_sha256") == c.get("packaging_trees", {}).get(node, {}).get("debian", {}).get("tree_sha256"), f"{node}: packaging tree pin")
    req(contract.get("selected_profile", {}).get("BUILD_TESTING") is True, f"{node}: BUILD_TESTING contract")
    packaging = can.get("packaging", {})
    if can.get("state") == "PASS":
        req(packaging.get("state") == "PASS" and packaging.get("downstream_eligible") is True, f"{node}: promoted package PASS")
    elif node == "knewstuff" and packaging.get("state") == "runtime-validation-required":
        req(can.get("state") == "pending" and packaging.get("downstream_eligible") is False, f"{node}: runtime validation remains pending")
    else:
        req(can.get("state") == "pending", f"{node}: canonical package state remains pending")
        req(packaging.get("state") == "pending" and packaging.get("downstream_eligible") is False, f"{node}: no downstream eligibility")

    if state.get("state") == "materialized":
        ev = state.get("evidence", {})
        req(ev.get("result") == "PASS", f"{node}: materialization evidence result")
        req(ev.get("package_attempted") is False and ev.get("package_state_effect") == "none", f"{node}: evidence package semantics")
        req(ev.get("package_version") == contract.get("package_version_candidate"), f"{node}: evidence version")
        req(ev.get("orig_tar_sha256") == contract.get("source_sha256"), f"{node}: authoritative source retained")
        req(ev.get("reference_tree_sha256") == contract.get("packaging_baseline", {}).get("tree_sha256"), f"{node}: baseline tree retained")
        req(isinstance(ev.get("artifact_sha256"), str) and len(ev.get("artifact_sha256")) == 64, f"{node}: artifact SHA-256")
        req(isinstance(ev.get("workflow_run"), int) and isinstance(ev.get("job_id"), int) and isinstance(ev.get("artifact_id"), int), f"{node}: run/job/artifact evidence")
        req(ev.get("full_result_json_retained_in_artifact") is True, f"{node}: full materialization evidence retained")
    elif state.get("state") == "remediation-pending":
        prev = state.get("previous_evidence", {})
        req(node in queue_set, f"{node}: unexpected active remediation node")
        req(prev.get("result") == "PASS", f"{node}: previous materialization PASS retained")
        req(prev.get("package_attempted") is False and prev.get("package_state_effect") == "none", f"{node}: previous materialization semantics")
        if active_c.get("round") == 10:
            req(node in {"kio","kxmlgui"}, f"{node}: round10 only KIO/KXMLGui rematerialize")
            expected_prev={"kio":"6.30.0-0supralinux5","kxmlgui":"6.30.0-0supralinux4"}[node]
            expected_next={"kio":"6.30.0-0supralinux6","kxmlgui":"6.30.0-0supralinux5"}[node]
            req(prev.get("package_version") == expected_prev, f"{node}: round10 baseline materialization revision")
            req(state.get("candidate_package_version") == expected_next, f"{node}: round10 candidate revision")
            minimum_history={"kio":5,"kxmlgui":4}[node]
            req(len(state.get("evidence_history", [])) >= minimum_history, f"{node}: round10 materialization history retained")
        elif active_c.get("round") == 9:
            req(node in {"kio","kxmlgui"}, f"{node}: round9 only KIO/KXMLGui rematerialize")
            expected_prev={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"}[node]
            expected_next={"kio":"6.30.0-0supralinux5","kxmlgui":"6.30.0-0supralinux4"}[node]
            req(prev.get("package_version") == expected_prev, f"{node}: round9 baseline materialization revision")
            req(state.get("candidate_package_version") == expected_next, f"{node}: round9 candidate revision")
            minimum_history={"kio":4,"kxmlgui":3}[node]
            req(len(state.get("evidence_history", [])) >= minimum_history, f"{node}: round9 materialization history retained")
        elif active_c.get("round") == 8:
            req(node in {"kio","kxmlgui"}, f"{node}: round8 only KIO/KXMLGui rematerialize")
            expected_prev={"kio":"6.30.0-0supralinux3","kxmlgui":"6.30.0-0supralinux2"}[node]
            expected_next={"kio":"6.30.0-0supralinux4","kxmlgui":"6.30.0-0supralinux3"}[node]
            req(prev.get("package_version") == expected_prev, f"{node}: round8 baseline materialization revision")
            req(state.get("candidate_package_version") == expected_next, f"{node}: round8 candidate revision")
            req(len(state.get("evidence_history", [])) >= 2, f"{node}: round8 materialization history retained")
        elif active_c.get("round") == 7:
            req(node in {"kio","kxmlgui"}, f"{node}: round7 only KIO/KXMLGui rematerialize")
            expected_prev={"kio":"6.30.0-0supralinux2","kxmlgui":"6.30.0-0supralinux1"}[node]
            expected_next={"kio":"6.30.0-0supralinux3","kxmlgui":"6.30.0-0supralinux2"}[node]
            req(prev.get("package_version") == expected_prev, f"{node}: round7 baseline materialization revision")
            req(state.get("candidate_package_version") == expected_next, f"{node}: round7 candidate revision")
            req(len(state.get("evidence_history", [])) >= 1, f"{node}: round7 materialization history retained")
        elif active_c.get("round") == 5:
            req(node == "kio", f"{node}: round5 only KIO rematerializes")
            req(prev.get("package_version") == "6.30.0-0supralinux1", f"{node}: round5 baseline materialization revision")
            req(state.get("candidate_package_version") == "6.30.0-0supralinux2", f"{node}: round5 candidate revision")
            req(len(state.get("evidence_history", [])) >= 1, f"{node}: round5 materialization history retained")
        elif active_c.get("round") == 4:
            req(node == "kwallet", f"{node}: round4 only KWallet rematerializes")
            req(prev.get("package_version") == "6.30.0-0supralinux3", f"{node}: round4 baseline materialization revision")
            req(state.get("candidate_package_version") == "6.30.0-0supralinux4", f"{node}: round4 candidate revision")
            req(len(state.get("evidence_history", [])) >= 3, f"{node}: round4 materialization history retained")
        elif active_c.get("round") == 3:
            req(node == "kjobwidgets", f"{node}: round3 only KJobWidgets rematerializes")
            req(prev.get("package_version") == "6.30.0-0supralinux3", f"{node}: round3 baseline materialization revision")
            req(state.get("candidate_package_version") == "6.30.0-0supralinux4", f"{node}: round3 candidate revision")
            req(len(state.get("evidence_history", [])) >= 3, f"{node}: round3 materialization history retained")
        else:
            req(prev.get("package_version") == "6.30.0-0supralinux2", f"{node}: round2 baseline materialization revision")
            req(state.get("candidate_package_version") == "6.30.0-0supralinux3", f"{node}: round2 candidate revision")
            req(len(state.get("evidence_history", [])) >= 2, f"{node}: materialization history retained")

req(t.get("materialization_manifest") == "manifests/kde-tier3-materialization.json", "canonical Tier3 materialization manifest linkage")

if m.get("state") == "pending-ci":
    req(all(m["nodes"][n].get("state") == "pending" for n in selected), "pending-ci requires all materialization nodes pending")
elif m.get("state") == "PASS":
    req(all(m["nodes"][n].get("state") == "materialized" for n in selected), "PASS requires all materialization nodes materialized")
    req(c.get("state") == "materialized", "PASS materialization contract lifecycle")
    req(t.get("discovery_policy", {}).get("phase") in {"build-campaign-planning", "build-level0", "build-level1-planning", "build-level1"}, "post-materialization phase")
    if active_c.get("round") == 9:
        req(active_c.get("status") in {"materialization-PASS","materialization-PASS-attempt5-active"}, "round9 contract materialization PASS")
        req(active_m.get("status") == "PASS" and active_m.get("workflow_run") == 35965579279, "round9 materialization evidence PASS")
        req(active_m.get("commit") == "8380856c8161dccc9de9c12745012c555baa26b0", "round9 materialization commit")
        req(active_m.get("promoted_nodes") == ["kio","kxmlgui"], "round9 promoted materialization set")
        req(active_m.get("artifacts",{}).get("kio",{}).get("artifact_id") == 10794251210 and active_m.get("artifacts",{}).get("kio",{}).get("artifact_sha256") == "45eac20aca30ca6a5ef78d8a94d15ee5408a8bed39c8fa72c6c8823134ffa0b2", "round9 KIO materialization artifact")
        req(active_m.get("artifacts",{}).get("kxmlgui",{}).get("artifact_id") == 10793229286 and active_m.get("artifacts",{}).get("kxmlgui",{}).get("artifact_sha256") == "44b9cf9d0ad12f06b12bda37c291fcda5ecf933e25cfdd61c42d9df6e11b0093", "round9 KXMLGui materialization artifact")
        req(m.get("evidence_summary",{}).get("promoted_remediation_materializations") == 2 and m.get("evidence_summary",{}).get("retained_previous_materializations") == 18, "round9 materialization summary")
        req(m["nodes"]["kio"].get("package_version") == "6.30.0-0supralinux5" and m["nodes"]["kxmlgui"].get("package_version") == "6.30.0-0supralinux4", "round9 promoted revisions")
        kev=m["nodes"]["kio"].get("evidence",{}); xev=m["nodes"]["kxmlgui"].get("evidence",{})
        req(kev.get("adapted_control_sha256")=="d291d67f1ae89ff839a1adab6c82eeecf8268cb5449d71dbed8f2c73386db280" and kev.get("adapted_rules_sha256")=="365ef3d5c2e2f13fb5e7c82891cddea72d4ec7538010b14fb834048d352bc2ee", "round9 KIO adapted-source hashes")
        req(xev.get("adapted_control_sha256")=="80533fe7cd08135fa0a1a35cd75dbb6ed2e464a6c26ec51874ebc3562bde6e0" and xev.get("adapted_rules_sha256")=="65cd53913bb5e4ac48cd96b38606acf33bc0cc054128b9733508bffdd2d8a7b2", "round9 KXMLGui adapted-source hashes")
        req(active_t.get("materialization_workflow_run") == 35965579279 and active_t.get("materialization_commit") == "8380856c8161dccc9de9c12745012c555baa26b0", "round9 canonical materialization evidence")
        if t.get("discovery_policy",{}).get("package_builds") == "tier3-level1-authorized":
            req(active_c.get("status")=="materialization-PASS-attempt5-active" and active_c.get("next_gate")=="tier3-build-level1-attempt5","round9 contract Attempt5 handoff")
            req(active_c.get("activation_policy_workflow_run")==35990068378 and active_c.get("activation_level1_workflow_run")==35990068382 and active_c.get("activation_commit")=="45675c1fb5a43f95204c2cf0c5c15df0ef703832","round9 contract Attempt5 validation evidence")
            req(active_t.get("status")=="level1-active-pending-ci" and active_t.get("execution_authorized") is True and active_t.get("level1_execution_authorized") is True,"round9 Attempt5 active state")
            req(active_t.get("current_attempt")==5 and active_t.get("activation_policy_workflow_run")==35990068378 and active_t.get("activation_level1_workflow_run")==35990068382,"round9 Attempt5 activation evidence")
            req(active_t.get("activation_commit")=="45675c1fb5a43f95204c2cf0c5c15df0ef703832" and active_t.get("next_gate")=="tier3-build-level1-attempt5","round9 Attempt5 gate")
            req(active_m.get("next_gate")=="tier3-build-level1-attempt5" and m.get("evidence_summary",{}).get("next_gate")=="tier3-build-level1-attempt5","round9 materialization Attempt5 handoff")
        else:
            req(t.get("discovery_policy",{}).get("package_builds") == "tier3-level1-source-PASS-pending-planning-validation", "round9 planning validation build gate")
            req(active_t.get("status") == "materialization-PASS-pending-level1-planning-validation", "round9 canonical source PASS state")
            req(active_t.get("execution_authorized") is False and active_t.get("level1_execution_authorized") is False, "round9 Level1 remains paused")
            req(active_t.get("current_attempt")==4 and active_t.get("next_attempt")==5, "round9 planning attempt markers")
            req(active_t.get("next_gate") == "tier3-build-level1-planning-validation", "round9 canonical planning-validation gate")
    elif active_c.get("round") == 8:
        req(active_c.get("status") in {"materialization-PASS","materialization-PASS-attempt4-active"}, "round8 contract materialization PASS")
        req(active_m.get("status") == "PASS" and active_m.get("workflow_run") == 35894317888, "round8 materialization evidence PASS")
        req(active_m.get("commit") == "65f5ba76a913e7acf619eb9fee86e878e2914415", "round8 materialization commit")
        req(active_m.get("promoted_nodes") == ["kio","kxmlgui"], "round8 promoted materialization set")
        req(active_m.get("artifacts",{}).get("kio",{}).get("artifact_id") == 10766471076 and active_m.get("artifacts",{}).get("kio",{}).get("artifact_sha256") == "80959256047d70323b6ea311551bed573661cefb4b831f30750e27ed11076cf6", "round8 KIO materialization artifact")
        req(active_m.get("artifacts",{}).get("kxmlgui",{}).get("artifact_id") == 10766665506 and active_m.get("artifacts",{}).get("kxmlgui",{}).get("artifact_sha256") == "100cf903ca1ef17cf2b37bab58ba0b7bf1e562d111cc04107247c3f35b134d58", "round8 KXMLGui materialization artifact")
        req(m.get("evidence_summary",{}).get("promoted_remediation_materializations") == 2 and m.get("evidence_summary",{}).get("retained_previous_materializations") == 18, "round8 materialization summary")
        req(m["nodes"]["kio"].get("package_version") == "6.30.0-0supralinux4" and m["nodes"]["kxmlgui"].get("package_version") == "6.30.0-0supralinux3", "round8 promoted revisions")
        kev=m["nodes"]["kio"].get("evidence",{}); xev=m["nodes"]["kxmlgui"].get("evidence",{})
        req(kev.get("adapted_control_sha256")=="582159e83e2c36e16be0da212d67a4a5eb725341b5a28fe4828bc515a9b5f505" and kev.get("adapted_rules_sha256")=="e8dae488976ef4d4748f044f52b3aebcf687ae3a52733588917fa8c397920f3e", "round8 KIO adapted-source hashes")
        req(xev.get("adapted_control_sha256")=="734bbf0fb49ba1691ec9994ea83cb7ccb11446c8a9e098aa9ae796726c417c3b" and xev.get("adapted_rules_sha256")=="597ef52317fee17c1aa1dca92b0c547ac1fa543f4a56b8b3b1d6075e07d5c14f", "round8 KXMLGui adapted-source hashes")
        req(active_t.get("materialization_workflow_run") == 35894317888 and active_t.get("materialization_commit") == "65f5ba76a913e7acf619eb9fee86e878e2914415", "round8 canonical materialization evidence")
        if t.get("discovery_policy",{}).get("package_builds") == "tier3-level1-authorized":
            req(active_c.get("status")=="materialization-PASS-attempt4-active" and active_c.get("next_gate")=="tier3-build-level1-attempt4","round8 contract Attempt4 handoff")
            req(active_c.get("activation_policy_workflow_run")==35895610944 and active_c.get("activation_level1_workflow_run")==35895610937 and active_c.get("activation_commit")=="9f680b0d8790c7bc472e8352e6675d606f706ee7","round8 contract Attempt4 validation evidence")
            req(active_t.get("status")=="level1-active-pending-ci" and active_t.get("execution_authorized") is True and active_t.get("level1_execution_authorized") is True,"round8 Attempt4 active state")
            req(active_t.get("current_attempt")==4 and active_t.get("activation_policy_workflow_run")==35895610944 and active_t.get("activation_level1_workflow_run")==35895610937,"round8 Attempt4 activation evidence")
            req(active_t.get("activation_commit")=="9f680b0d8790c7bc472e8352e6675d606f706ee7" and active_t.get("next_gate")=="tier3-build-level1-attempt4","round8 Attempt4 gate")
            req(active_m.get("next_gate")=="tier3-build-level1-attempt4" and m.get("evidence_summary",{}).get("next_gate")=="tier3-build-level1-attempt4","round8 materialization Attempt4 handoff")
        else:
            req(t.get("discovery_policy",{}).get("package_builds") == "tier3-level1-source-PASS-pending-planning-validation", "round8 planning validation build gate")
            req(active_t.get("status") == "materialization-PASS-pending-level1-planning-validation", "round8 canonical source PASS state")
            req(active_t.get("execution_authorized") is False and active_t.get("level1_execution_authorized") is False, "round8 Level1 remains paused")
            req(active_t.get("current_attempt")==3 and active_t.get("next_attempt")==4, "round8 planning attempt markers")
            req(active_t.get("next_gate") == "tier3-build-level1-planning-validation", "round8 canonical planning-validation gate")
    elif active_c.get("round") == 7:
        req(active_c.get("status") in {"materialization-PASS","materialization-PASS-attempt3-active"}, "round7 contract materialization PASS")
        req(active_m.get("status") == "PASS" and active_m.get("workflow_run") == 35882795135, "round7 materialization evidence PASS")
        req(active_m.get("commit") == "0d6c02f3f8dc41f716ba62ee7121f56371a8dc91", "round7 materialization commit")
        req(active_m.get("promoted_nodes") == ["kio","kxmlgui"], "round7 promoted materialization set")
        req(active_m.get("artifacts",{}).get("kio",{}).get("artifact_id") == 10760324592 and active_m.get("artifacts",{}).get("kio",{}).get("artifact_sha256") == "b58b7a45f6df0c8f01e9bd9a37799c1470369124a7c1b48fecb82a5f7f86ae8d", "round7 KIO materialization artifact")
        req(active_m.get("artifacts",{}).get("kxmlgui",{}).get("artifact_id") == 10761208629 and active_m.get("artifacts",{}).get("kxmlgui",{}).get("artifact_sha256") == "72cd10276558264646a9e38d5beab7b231434338597ef8d276030e790ff02214", "round7 KXMLGui materialization artifact")
        req(m.get("evidence_summary",{}).get("promoted_remediation_materializations") == 2 and m.get("evidence_summary",{}).get("retained_previous_materializations") == 18, "round7 materialization summary")
        req(m["nodes"]["kio"].get("package_version") == "6.30.0-0supralinux3" and m["nodes"]["kxmlgui"].get("package_version") == "6.30.0-0supralinux2", "round7 promoted revisions")
        kev=m["nodes"]["kio"].get("evidence",{}); xev=m["nodes"]["kxmlgui"].get("evidence",{})
        req(kev.get("adapted_control_sha256")=="582159e83e2c36e16be0da212d67a4a5eb725341b5a28fe4828bc515a9b5f505" and kev.get("adapted_rules_sha256")=="6db9a93621a73f87a6be3a38bfa914df065f9ab85962cc46738a1cb3a5817cab", "round7 KIO adapted-source hashes")
        req(xev.get("adapted_control_sha256")=="734bbf0fb49ba1691ec9994ea83cb7ccb11446c8a9e098aa9ae796726c417c3b" and xev.get("adapted_rules_sha256")=="914ecc0245b8680ca4869549d6030a974c1cde60904759a0c876fabd25a19fa6", "round7 KXMLGui adapted-source hashes")
        req(active_t.get("materialization_workflow_run") == 35882795135 and active_t.get("materialization_commit") == "0d6c02f3f8dc41f716ba62ee7121f56371a8dc91", "round7 canonical materialization evidence")
        if t.get("discovery_policy",{}).get("package_builds") == "tier3-level1-authorized":
            req(active_c.get("status")=="materialization-PASS-attempt3-active" and active_c.get("next_gate")=="tier3-build-level1-attempt3","round7 contract Attempt3 handoff")
            req(active_t.get("status")=="level1-active-pending-ci" and active_t.get("execution_authorized") is True and active_t.get("level1_execution_authorized") is True,"round7 Attempt3 active state")
            req(active_t.get("current_attempt")==3 and active_t.get("activation_policy_workflow_run")==35884583361 and active_t.get("activation_level1_workflow_run")==35884584590,"round7 Attempt3 activation evidence")
            req(active_t.get("next_gate")=="tier3-build-level1-attempt3","round7 Attempt3 gate")
            req(active_m.get("next_gate")=="tier3-build-level1-attempt3" and m.get("evidence_summary",{}).get("next_gate")=="tier3-build-level1-attempt3","round7 materialization Attempt3 handoff")
        else:
            req(t.get("discovery_policy",{}).get("package_builds") == "tier3-level1-source-PASS-pending-planning-validation", "round7 planning validation build gate")
            req(active_t.get("status") == "materialization-PASS-pending-level1-planning-validation", "round7 canonical source PASS state")
            req(active_t.get("execution_authorized") is False and active_t.get("level1_execution_authorized") is False, "round7 Level1 remains paused")
            req(active_t.get("next_gate") == "tier3-build-level1-planning-validation", "round7 canonical planning-validation gate")
    elif active_c.get("round") == 6:
        req(active_c.get("status") in {"provider-closure-pending-attempt2-activation-validation","provider-closure-PASS"}, "round6 contract provider-closure state")
        req(active_c.get("source_changed_nodes") == [] and set(active_c.get("provider_closure_only_nodes",[])) == {"kio","kxmlgui"}, "round6 has no source materialization")
        req(active_m.get("round") == 5 and active_m.get("status") == "PASS", "round6 retains round5 materialization PASS")
        req(active_m.get("workflow_run") == 35825070347 and active_m.get("artifacts",{}).get("kio",{}).get("artifact_id") == 10735250819, "round6 retains exact KIO source artifact")
        req(active_t.get("round") == 6 and active_t.get("source_materialization_nodes") == [] and set(active_t.get("provider_closure_only_nodes",[])) == {"kio","kxmlgui"}, "round6 canonical no-source scope")
        req(active_t.get("provider_closure_inputs")=={"kio":["kconfigwidgets","karchive","kcodecs","knotifications","breeze-icons"],"kxmlgui":["karchive","kcodecs","kcolorscheme","kcompletion","sonnet","breeze-icons"]},"round6 complete provider closure")
        req(active_t.get("validation_result")=="2 raw workflow FAIL / 0 canonical FAIL" and active_t.get("remaining_failed_nodes")==[] and active_t.get("canonical_failures")==0,"round6 raw/canonical no-FAIL semantics")
        if t.get("discovery_policy",{}).get("package_builds")=="tier3-level1-authorized":
            req(active_c.get("status")=="provider-closure-PASS","round6 active contract closure PASS")
            ev=active_c.get("evidence",{})
            req(ev.get("repository_policy_workflow_run")==35828634884 and ev.get("level1_validation_workflow_run")==35828634887,"round6 closure validation evidence")
            req(t.get("discovery_policy",{}).get("phase")=="build-level1","round6 active Level1 phase")
            req(active_t.get("status")=="level1-active-pending-ci" and active_t.get("execution_authorized") is True and active_t.get("level1_execution_authorized") is True,"round6 active Level1 authorization")
            req(active_t.get("current_attempt")==2 and active_t.get("activation_policy_workflow_run")==35828634884,"round6 Attempt2 activation evidence")
            req(active_t.get("next_gate")=="tier3-build-level1-attempt2","round6 Attempt2 active gate")
        else:
            req(t.get("discovery_policy",{}).get("phase") == "build-level1-planning" and t.get("discovery_policy",{}).get("package_builds") == "tier3-level1-remediation-pending-provider-closure", "round6 canonical provider-closure planning gate")
            req(active_t.get("execution_authorized") is False and active_t.get("next_attempt")==2 and active_t.get("next_gate") == "tier3-build-level1-attempt2-activation-validation", "round6 Level1 pause")
        req(m["nodes"]["kio"].get("package_version") == "6.30.0-0supralinux2" and m["nodes"]["kxmlgui"].get("package_version") == "6.30.0-0supralinux1", "round6 materialized revisions unchanged")
    elif active_c.get("round") == 5:
        req(active_c.get("status") == "materialization-PASS", "round5 contract materialization PASS")
        req(active_m.get("status") == "PASS" and active_m.get("workflow_run") == 35825070347, "round5 KIO materialization evidence PASS")
        req(active_m.get("commit") == "fbde9a53e357a138f4d74d7905230c7859e20444", "round5 KIO materialization commit")
        req(active_m.get("promoted_nodes") == ["kio"], "round5 promoted materialization set")
        req(active_m.get("artifacts",{}).get("kio",{}).get("artifact_id") == 10735250819, "round5 KIO materialization artifact")
        req(active_m.get("artifacts",{}).get("kio",{}).get("artifact_sha256") == "8d958c9ac8194cbaf26d4bf310148e129cfbe11b7ebaf6fed967d6c8400dc106", "round5 KIO materialization digest")
        req(m.get("evidence_summary", {}).get("promoted_remediation_materializations") == 1, "round5 materialization summary")
        req(m["nodes"]["kio"].get("package_version") == "6.30.0-0supralinux2", "round5 KIO promoted revision")
        ev=m["nodes"]["kio"].get("evidence",{})
        req(ev.get("adapted_control_sha256")=="b1ab7b4386e5076a2fcdddcf29b399ccf8093d1f7bcec20d717fc9ceaa8ec31b","KIO round5 control hash")
        req(ev.get("adapted_rules_sha256")=="87a32e610585ab989426006099b0e62a15f22d299ea70db3266b2a399f8dfd10","KIO round5 rules hash")
        if t.get("discovery_policy", {}).get("package_builds") == "tier3-level1-authorized":
            req(t.get("discovery_policy", {}).get("phase") == "build-level1", "round5 active Level1 phase")
            req(active_t.get("status") == "level1-active-pending-ci", "round5 active Level1 state")
            req(active_t.get("execution_authorized") is True and active_t.get("level1_execution_authorized") is True, "round5 Level1 authorized")
            req(active_t.get("current_attempt") == 1 and active_t.get("next_gate") == "tier3-build-level1-attempt1", "round5 Level1 attempt1 gate")
            req(active_m.get("next_gate") == "tier3-build-level1-attempt1", "round5 materialization handoff gate")
            req(m.get("evidence_summary",{}).get("next_gate") == "tier3-build-level1-attempt1", "round5 materialization summary handoff")
        else:
            req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level1-source-PASS-pending-planning-validation", "round5 planning validation build gate")
            req(active_t.get("status") == "materialization-PASS-pending-level1-planning-validation", "round5 canonical source PASS state")
            req(active_t.get("execution_authorized") is False and active_t.get("level1_execution_authorized") is False, "round5 Level1 remains paused")
            req(active_t.get("materialization_workflow_run") == 35825070347 and active_t.get("next_gate") == "tier3-build-level1-planning-validation", "round5 canonical evidence/next gate")
    elif active_c.get("round") == 4:
        req(active_c.get("status") == "materialization-PASS", "round4 contract materialization PASS")
        req(active_m.get("status") == "PASS" and active_m.get("workflow_run") == 35817654811, "round4 materialization evidence PASS")
        req(active_m.get("commit") == "1a9a4ba82b4aac9f1df9f6457faef8b905dd17cf", "round4 materialization commit")
        req(active_m.get("promoted_nodes") == ["kwallet"], "round4 promoted materialization set")
        req(active_m.get("artifacts",{}).get("kwallet",{}).get("artifact_id") == 10731134598, "round4 KWallet materialization artifact")
        req(active_m.get("artifacts",{}).get("kwallet",{}).get("artifact_sha256") == "de215dfb5f86816dadccc630f23360bdc4c79a010aa6f7a0e2e99b1969bcf4ef", "round4 KWallet materialization digest")
        req(m.get("evidence_summary", {}).get("promoted_remediation_materializations") == 1, "round4 materialization summary")
        req(m["nodes"]["kwallet"].get("package_version") == "6.30.0-0supralinux4", "round4 KWallet promoted revision")
        req(active_t.get("materialization_workflow_run") == 35817654811, "canonical round4 materialization linkage")
        if t.get("discovery_policy", {}).get("package_builds") == "tier3-level1-not-authorized-before-planning":
            req(active_t.get("status") == "attempt5-complete" and active_t.get("execution_authorized") is False, "Attempt5 closed before Level1 planning")
            req(active_t.get("validation_workflow_run") == 35818120201 and active_t.get("validation_commit") == "0599266fd5fc9869002629b3778d71f1e76bbdc1", "Attempt5 closure evidence")
            req(active_t.get("canonical_promotions") == 11 and active_t.get("runtime_pending_nodes") == ["knewstuff"], "Attempt5 promotion summary")
            req(active_t.get("next_gate") == "tier3-build-level1-planning", "Level1 planning gate")
        elif active_t.get("current_attempt") == 5:
            req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-authorized", "Level0 attempt5 canonical build gate")
            req(active_t.get("status") == "level0-rerun-active", "canonical attempt5 active state")
            req(active_t.get("execution_authorized") is True, "attempt5 execution authorized")
            req(active_t.get("activation_policy_workflow_run") == 35817928654, "attempt5 activation validation evidence")
            req(active_t.get("next_gate") == "tier3-build-level0-attempt5", "attempt5 canonical next gate")
        else:
            req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-remediation-pending", "Level0 remains paused after round4 promotion")
            req(active_t.get("status") == "materialization-PASS-pending-level0-attempt5-activation", "canonical round4 promotion state")
            req(active_t.get("execution_authorized") is False, "attempt5 not authorized before promotion validation")
            req(active_t.get("next_gate") == "tier3-build-level0-attempt5-activation-validation", "round4 activation validation gate")
    elif active_c.get("round") == 2:
        req(active_c.get("status") == "materialization-PASS", "round2 contract materialization PASS")
        req(active_m.get("status") == "PASS" and active_m.get("workflow_run") == 35806738003, "round2 materialization evidence PASS")
        req(set(active_m.get("promoted_nodes", [])) == {"kiconthemes","kjobwidgets","kwallet"}, "round2 promoted materialization set")
        req(m.get("evidence_summary", {}).get("promoted_remediation_materializations") == 3, "round2 materialization summary")
        if active_t.get("current_attempt") == 3:
            req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-authorized", "Level0 attempt3 canonical build gate")
            req(active_t.get("status") == "level0-rerun-active", "canonical attempt3 active state")
            req(active_t.get("execution_authorized") is True, "attempt3 execution authorized")
            req(active_t.get("activation_policy_workflow_run") == 35807934729, "attempt3 activation validation evidence")
            req(active_t.get("next_gate") == "tier3-build-level0-attempt3", "attempt3 canonical next gate")
        else:
            req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-remediation-pending", "Level0 remains paused after round2 promotion")
            req(active_t.get("status") == "materialization-PASS-pending-level0-attempt3-activation", "canonical round2 promotion state")
            req(active_t.get("execution_authorized") is False, "attempt3 not authorized before promotion validation")
    elif active_c.get("round") == 3:
        req(active_c.get("status") == "materialization-PASS", "round3 contract materialization PASS")
        req(active_m.get("status") == "PASS" and active_m.get("workflow_run") == 35812918054, "round3 materialization evidence PASS")
        req(active_m.get("commit") == "a57c13059dfc206ddf57390e1cd0cfd280471965", "round3 materialization commit")
        req(active_m.get("promoted_nodes") == ["kjobwidgets"], "round3 promoted materialization set")
        req(active_m.get("artifacts",{}).get("kjobwidgets",{}).get("artifact_id") == 10730956293, "round3 KJobWidgets materialization artifact")
        req(active_m.get("artifacts",{}).get("kjobwidgets",{}).get("artifact_sha256") == "bcd505c1d4cbc65b45861335f41d8b03f18d53995bb9ba1d9036295bd5ce7804", "round3 KJobWidgets materialization digest")
        req(m.get("evidence_summary", {}).get("promoted_remediation_materializations") == 1, "round3 materialization summary")
        req(m["nodes"]["kjobwidgets"].get("package_version") == "6.30.0-0supralinux4", "round3 KJobWidgets promoted revision")
        req(active_t.get("materialization_workflow_run") == 35812918054, "canonical round3 materialization linkage")
        if active_t.get("current_attempt") == 4:
            req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-authorized", "Level0 attempt4 canonical build gate")
            req(active_t.get("status") == "level0-rerun-active", "canonical attempt4 active state")
            req(active_t.get("execution_authorized") is True, "attempt4 execution authorized")
            req(active_t.get("activation_policy_workflow_run") == 35813396247, "attempt4 activation validation evidence")
            req(active_t.get("next_gate") == "tier3-build-level0-attempt4", "attempt4 canonical next gate")
        else:
            req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-remediation-pending", "Level0 remains paused after round3 promotion")
            req(active_t.get("status") == "materialization-PASS-pending-level0-attempt4-activation", "canonical round3 promotion state")
            req(active_t.get("execution_authorized") is False, "attempt4 not authorized before promotion validation")
            req(active_t.get("next_gate") == "tier3-build-level0-attempt4-activation-validation", "round3 activation validation gate")
else:
    expected_queue = ["kio","kxmlgui"] if active_c.get("round") in {7,8,9,10} else (["kio"] if active_c.get("round") == 5 else (["kwallet"] if active_c.get("round") == 4 else (["kjobwidgets"] if active_c.get("round") == 3 else ["kiconthemes","kjobwidgets","kwallet"])))
    req(queue == expected_queue, "active remediation materialization queue")
    req(all(m["nodes"][n].get("state") == "remediation-pending" for n in queue), "active remediation materialization queue states")
    req(all(m["nodes"][n].get("state") == "materialized" for n in selected if n not in queue_set), "unaffected materializations remain PASS")
    prev_summary = m.get("previous_evidence_summary", {})
    req(prev_summary.get("result") == "PASS" and prev_summary.get("package_attempted") is False, "previous materialization summary retained")
    if active_c.get("round") in {5,7,8,9,10}:
        req(t.get("discovery_policy", {}).get("phase") in {"build-level1-planning","build-level1"}, "Level1 remediation remains in Level1 lifecycle")
        req(t.get("support_components", {}).get("next_gate") in {"tier3-build-level1-planning","tier3-build-level1"}, "round5 remediation remains in Level1 gate")
    else:
        req(t.get("discovery_policy", {}).get("phase") == "build-level0", "remediation remains in Level0 phase")
        req(t.get("support_components", {}).get("next_gate") == "tier3-build-level0", "remediation remains in Level0 gate")

for path in (
    "scripts/materialize_kde_tier3_package.py",
    "scripts/kde-tier3-materialization-needed.sh",
    "scripts/test-kde-tier3-materialization-scope.sh",
    ".github/workflows/kde-tier3-materialization.yml",
    "docs/kde-tier3-materialization.md",
):
    req((ROOT / path).exists(), f"missing Tier3 materialization component: {path}")

if errors:
    for e in errors:
        print("ERROR:", e, file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 source materialization definition: PASS")
print("state=" + m["state"])
print("nodes=20")
if m.get("state") == "remediation-pending-ci":
    print(f"active-remediation-round={active_c.get('round')} source-nodes={len(queue)}")

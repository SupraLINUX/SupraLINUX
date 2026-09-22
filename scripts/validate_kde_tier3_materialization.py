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
req(decision.get("package_build_authorized") is False, "binary builds remain unauthorized during materialization")
req(c.get("source_authority") == "kde-upstream" and c.get("packaging_authority") == "supralinux", "authority/provider separation")

provider = c.get("provider_adaptations", {}).get("ubuntu-resolute", {})
req(provider.get("debhelper_compat", {}).get("selected_level") == 13, "Resolute debhelper level")
req(provider.get("changelog_distribution", {}).get("selected") == "resolute", "Resolute distribution provider")
shiboken = provider.get("shiboken_clang_discovery", {})
req(shiboken.get("provider_packages") == ["llvm-dev", "libclang-common-21-dev"], "Shiboken clang provider closure")
req(shiboken.get("applies_to") == ["kjobwidgets", "kxmlgui"], "Shiboken adaptation scope")
python_build = provider.get("python_build_module", {})
remediation_contract = c.get("remediation", {})
remediation_nodes = set(remediation_contract.get("trigger", {}).get("failed_nodes", []))
if "kjobwidgets" in remediation_nodes:
    req(python_build.get("provider_package") == "python3-build", "KJobWidgets Python build-module provider")
    req(python_build.get("applies_to") == ["kjobwidgets"], "Python build-module provider scope")

remediation_queue = m.get("remediation_queue", [])
remediation_set = set(remediation_queue)
if m.get("state") == "remediation-pending-ci":
    req(remediation_queue == ["kiconthemes", "kdav", "kwallet", "krunner", "kjobwidgets"], "Tier3 remediation queue")
    req(c.get("remediation", {}).get("status") == "materialization-pending-ci", "Tier3 contract remediation state")

for node in selected:
    state = m["nodes"][node]
    contract = contracts[node]
    can = canonical[node]
    req(state.get("state") in {"pending", "materialized", "remediation-pending"}, f"{node}: materialization state")
    req(contract.get("contract_state") == "contract-ready", f"{node}: contract-ready")
    if state.get("state") == "remediation-pending":
        expected_candidate = state.get("candidate_package_version")
    else:
        expected_candidate = state.get("package_version")
    req(contract.get("package_version_candidate") == expected_candidate, f"{node}: candidate version")
    req(contract.get("upstream_version") == "6.30.0", f"{node}: upstream version")
    req(contract.get("source_sha256") == can.get("source_sha256"), f"{node}: KDE source SHA linkage")
    req(contract.get("technical_references", {}).get("debian", {}).get("version") == "6.30.0-1", f"{node}: exact Debian 6.30 baseline")
    req(contract.get("packaging_baseline", {}).get("provider") == "debian-sid", f"{node}: packaging baseline provider")
    req(contract.get("packaging_baseline", {}).get("tree_sha256") == c.get("packaging_trees", {}).get(node, {}).get("debian", {}).get("tree_sha256"), f"{node}: packaging tree pin")
    req(contract.get("selected_profile", {}).get("BUILD_TESTING") is True, f"{node}: BUILD_TESTING contract")
    req(can.get("state") == "pending", f"{node}: canonical package state remains pending")
    req(can.get("packaging", {}).get("state") == "pending" and can.get("packaging", {}).get("downstream_eligible") is False, f"{node}: no downstream eligibility")
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
        req(node in remediation_set, f"{node}: unexpected remediation node")
        req(prev.get("result") == "PASS", f"{node}: previous materialization PASS retained")
        req(prev.get("package_version") == "6.30.0-0supralinux1", f"{node}: previous materialization version")
        req(prev.get("package_attempted") is False and prev.get("package_state_effect") == "none", f"{node}: previous materialization semantics")
        req(state.get("candidate_package_version") == "6.30.0-0supralinux2", f"{node}: remediation candidate revision")

req(t.get("materialization_manifest") == "manifests/kde-tier3-materialization.json", "canonical Tier3 materialization manifest linkage")

if m.get("state") == "pending-ci":
    req(all(m["nodes"][n].get("state") == "pending" for n in selected), "pending-ci requires all materialization nodes pending")
    req(c.get("state") == "contracts-ready", "pending materialization requires contracts-ready")
    req(t.get("discovery_policy", {}).get("phase") == "materialization", "canonical pending materialization phase")
    req(t.get("discovery_policy", {}).get("package_builds") == "not-authorized-before-tier3-materialization", "binary build gate before materialization")
    req(t.get("support_components", {}).get("next_gate") == "tier3-materialization", "canonical materialization next gate")
    for node in selected:
        planning = canonical[node].get("planning", {})
        req(planning.get("readiness") == "package-contract-ready", f"{node}: pending readiness")
        req(planning.get("package_contract") == "not-materialized", f"{node}: pending package contract")
elif m.get("state") == "PASS":
    req(all(m["nodes"][n].get("state") == "materialized" for n in selected), "PASS requires all materialization nodes materialized")
    req(c.get("state") == "materialized", "PASS materialization contract lifecycle")
    req(c.get("materialization", {}).get("status") == "PASS" and c.get("materialization", {}).get("workflow_run") == 35746667704, "promoted materialization evidence linkage")
    req(t.get("discovery_policy", {}).get("phase") in {"build-campaign-planning","build-level0"}, "post-materialization phase")
    req(t.get("discovery_policy", {}).get("package_builds") in {"not-authorized-before-tier3-build-campaign","tier3-level0-authorized","tier3-level0-remediation-pending"}, "post-materialization binary build gate")
    req(t.get("support_components", {}).get("next_gate") in {"tier3-build-campaign-planning","tier3-build-level0"}, "post-materialization next gate")
    summary = m.get("evidence_summary", {})
    req(summary.get("result") == "PASS" and summary.get("package_attempted") is False and summary.get("package_state_effect") == "none", "materialization evidence summary")
    if remediation_contract.get("status") == "materialization-PASS":
        req(summary.get("workflow_run") == 35759443440 and summary.get("promoted_remediation_materializations") == 5, "remediation materialization summary")
        req(remediation_contract.get("evidence", {}).get("workflow_run") == 35759443440, "contract remediation materialization evidence")
        req(set(remediation_contract.get("evidence", {}).get("promoted_nodes", [])) == remediation_nodes, "contract remediation promoted node set")
        req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-remediation-pending", "Level0 remains paused after remediation materialization")
    for node in selected:
        planning = canonical[node].get("planning", {})
        req(planning.get("readiness") == "materialized", f"{node}: materialized readiness")
        req(planning.get("package_contract") == "materialized", f"{node}: materialized package contract")
else:
    req(len(remediation_queue) == 5, "remediation materialization node count")
    req(all(m["nodes"][n].get("state") == "remediation-pending" for n in remediation_queue), "remediation queue node states")
    req(all(m["nodes"][n].get("state") == "materialized" for n in selected if n not in remediation_set), "unaffected materializations remain PASS")
    req(m.get("remediation", {}).get("trigger_workflow_run") == 35755924197, "remediation trigger run")
    req(m.get("remediation", {}).get("package_revision") == "6.30.0-0supralinux2", "remediation package revision")
    prev_summary = m.get("previous_evidence_summary", {})
    req(prev_summary.get("result") == "PASS" and prev_summary.get("package_attempted") is False, "previous materialization summary retained")
    req(t.get("discovery_policy", {}).get("phase") == "build-level0", "remediation remains in Level0 phase")
    req(t.get("support_components", {}).get("next_gate") == "tier3-build-level0", "remediation remains in Level0 gate")
    req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-remediation-pending", "remediation pauses Level0 binary execution")
    active = t.get("active_remediation", {})
    req(active.get("trigger_workflow_run") == 35755924197, "canonical remediation trigger")
    req(set(active.get("nodes", [])) == remediation_set, "canonical remediation node set")
    req(active.get("execution_authorized") is False, "canonical remediation execution pause")

    expected_rel = {
        "kiconthemes": [("remove", "libkf6configwidgets-dev")],
        "kdav": [("remove", "kio6"), ("remove", "libkf6kio-dev")],
        "kwallet": [("remove", "libkf6doctools-dev")],
        "kjobwidgets": [("ensure", "python3-build")],
    }
    for node, expected in expected_rel.items():
        actual = []
        for x in contracts[node].get("source_build_relation_overrides", []):
            actual.append((x.get("action"), x.get("package") or x.get("relation")))
        req(actual == expected, f"{node}: source Build-Depends remediation contract")

    req(contracts["kiconthemes"].get("binary_relation_overrides", []) == [{
        "package":"libkf6iconthemes-dev",
        "field":"Depends",
        "action":"remove",
        "relation":"libkf6configwidgets-dev",
        "classification":"debian-only-development-edge-removal",
        "rationale":"KF6IconThemesConfig.cmake.in in KDE 6.30 exports Archive, I18n, WidgetsAddons and ColorScheme but not KConfigWidgets; the Debian dev-package relation would recreate a false public dependency."
    }], "KIconThemes false public KConfigWidgets dependency removed")
    req(contracts["kiconthemes"].get("reference_test_suppression_overrides", {}).get("rules_remove_excluded_tests") == ["kiconloader_unittest", "kiconengine_unittest"], "KIconThemes upstream tests restored")
    req(contracts["krunner"].get("reference_patch_suppression_overrides", {}).get("reverse_and_drop") == ["skip-flaky-test.patch"], "KRunner upstream flaky test restored")
    sym = contracts["krunner"].get("symbol_template_overrides", [])
    req(len(sym) == 2 and all("optional=templinst" in x.get("add_tags", []) for x in sym), "KRunner private template symbols optionalized")

if remediation_nodes:
    req(remediation_nodes == {"kiconthemes","kdav","kwallet","krunner","kjobwidgets"}, "Tier3 remediation contract node set")
    expected_rel = {
        "kiconthemes": [("remove", "libkf6configwidgets-dev")],
        "kdav": [("remove", "kio6"), ("remove", "libkf6kio-dev")],
        "kwallet": [("remove", "libkf6doctools-dev")],
        "kjobwidgets": [("ensure", "python3-build")],
    }
    for node, expected in expected_rel.items():
        actual = [(x.get("action"), x.get("package") or x.get("relation")) for x in contracts[node].get("source_build_relation_overrides", [])]
        req(actual == expected, f"{node}: retained remediation source relation contract")
    req(contracts["kiconthemes"].get("reference_test_suppression_overrides", {}).get("rules_remove_excluded_tests") == ["kiconloader_unittest", "kiconengine_unittest"], "KIconThemes restored upstream tests retained")
    req(contracts["krunner"].get("reference_patch_suppression_overrides", {}).get("reverse_and_drop") == ["skip-flaky-test.patch"], "KRunner restored upstream test retained")
    sym = contracts["krunner"].get("symbol_template_overrides", [])
    req(len(sym) == 2 and all("optional=templinst" in x.get("add_tags", []) for x in sym), "KRunner symbol remediation retained")

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

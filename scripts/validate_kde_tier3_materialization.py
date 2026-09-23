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
req(pb.get("provider_package") == "python3-build" and pb.get("applies_to") == ["kjobwidgets"], "Tier3 round1 KJobWidgets python-build provider")
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
active_nodes = set(active_c.get("trigger", {}).get("failed_nodes", []))
queue = m.get("remediation_queue", [])
queue_set = set(queue)

if m.get("state") == "remediation-pending-ci":
    req(active_c.get("round") == 2 and active_m.get("round") == 2 and active_t.get("round") == 2, "Tier3 active remediation round")
    req(active_nodes == {"kiconthemes", "kjobwidgets", "kwallet"}, "Tier3 round2 remediation node set")
    req(queue == ["kiconthemes", "kjobwidgets", "kwallet"], "Tier3 round2 materialization queue")
    req(queue_set == active_nodes == set(active_m.get("nodes", [])) == set(active_t.get("nodes", [])), "Tier3 round2 remediation linkage")
    req(active_c.get("status") in {"materialization-pending-ci","materialization-PASS"} and active_m.get("status") in {"materialization-pending-ci","PASS"}, "Tier3 round2 remediation state")
    req(active_c.get("trigger", {}).get("workflow_run") == 35770505868, "Tier3 round2 trigger run")
    req(active_m.get("trigger_workflow_run") == 35770505868 and active_t.get("trigger_workflow_run") == 35770505868, "Tier3 round2 trigger linkage")
    req(active_c.get("candidate_package_version") == "6.30.0-0supralinux3", "Tier3 round2 candidate revision")
    req(active_m.get("package_revision") == "6.30.0-0supralinux3" and active_t.get("candidate_package_version") == "6.30.0-0supralinux3", "Tier3 round2 revision linkage")
    req(active_t.get("execution_authorized") is False and active_t.get("full_level0_rerun_required") is True, "Tier3 round2 binary execution pause")
    req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-remediation-pending", "Tier3 round2 canonical build gate")

    setuptools = provider.get("python_setuptools_backend", {})
    req(setuptools.get("provider_package") == "python3-setuptools", "KJobWidgets setuptools provider")
    req(setuptools.get("observed_provider_version") == "78.1.1-0.1build1", "KJobWidgets setuptools provider version")
    req(setuptools.get("applies_to") == ["kjobwidgets"], "KJobWidgets setuptools provider scope")

    svg = provider.get("qt_svg_image_plugin", {})
    req(svg.get("provider_package") == "qt6-svg-plugins", "KIconThemes Qt SVG plugin provider")
    req(svg.get("observed_provider_version") == "6.10.2-2", "KIconThemes Qt SVG plugin provider version")
    req(svg.get("applies_to") == ["kiconthemes"], "KIconThemes Qt SVG provider scope")

    expected_rel = {
        "kiconthemes": [("remove", "libkf6configwidgets-dev"), ("ensure", "qt6-svg-plugins <!nocheck>")],
        "kjobwidgets": [("ensure", "python3-build"), ("ensure", "python3-setuptools")],
        "kwallet": [("ensure", "libkf6doctools-dev (>= 6.30.0~)")],
    }
    for node, expected in expected_rel.items():
        actual = [(x.get("action"), x.get("package") or x.get("relation")) for x in contracts[node].get("source_build_relation_overrides", [])]
        req(actual == expected, f"{node}: round2 source relation contract")
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
        req(node in queue_set, f"{node}: unexpected active remediation node")
        req(prev.get("result") == "PASS", f"{node}: previous materialization PASS retained")
        req(prev.get("package_version") == "6.30.0-0supralinux2", f"{node}: round2 baseline materialization revision")
        req(prev.get("package_attempted") is False and prev.get("package_state_effect") == "none", f"{node}: previous materialization semantics")
        req(state.get("candidate_package_version") == "6.30.0-0supralinux3", f"{node}: round2 candidate revision")
        hist = state.get("evidence_history", [])
        req(len(hist) >= 2, f"{node}: materialization history retained")

req(t.get("materialization_manifest") == "manifests/kde-tier3-materialization.json", "canonical Tier3 materialization manifest linkage")

if m.get("state") == "pending-ci":
    req(all(m["nodes"][n].get("state") == "pending" for n in selected), "pending-ci requires all materialization nodes pending")
elif m.get("state") == "PASS":
    req(all(m["nodes"][n].get("state") == "materialized" for n in selected), "PASS requires all materialization nodes materialized")
    req(c.get("state") == "materialized", "PASS materialization contract lifecycle")
    req(t.get("discovery_policy", {}).get("phase") in {"build-campaign-planning", "build-level0"}, "post-materialization phase")
    if active_c.get("round") == 2:
        req(active_c.get("status") == "materialization-PASS", "round2 contract materialization PASS")
        req(active_m.get("status") == "PASS" and active_m.get("workflow_run") == 35806738003, "round2 materialization evidence PASS")
        req(set(active_m.get("promoted_nodes", [])) == {"kiconthemes","kjobwidgets","kwallet"}, "round2 promoted materialization set")
        req(m.get("evidence_summary", {}).get("promoted_remediation_materializations") == 3, "round2 materialization summary")
        req(t.get("discovery_policy", {}).get("package_builds") == "tier3-level0-remediation-pending", "Level0 remains paused after round2 promotion")
        req(active_t.get("status") == "materialization-PASS-pending-level0-attempt3-activation", "canonical round2 promotion state")
        req(active_t.get("execution_authorized") is False, "attempt3 not authorized before promotion validation")
else:
    req(len(queue) == 3, "round2 materialization node count")
    req(all(m["nodes"][n].get("state") == "remediation-pending" for n in queue), "round2 materialization queue states")
    req(all(m["nodes"][n].get("state") == "materialized" for n in selected if n not in queue_set), "unaffected materializations remain PASS")
    prev_summary = m.get("previous_evidence_summary", {})
    req(prev_summary.get("result") == "PASS" and prev_summary.get("package_attempted") is False, "previous materialization summary retained")
    req(t.get("discovery_policy", {}).get("phase") == "build-level0", "round2 remains in Level0 phase")
    req(t.get("support_components", {}).get("next_gate") == "tier3-build-level0", "round2 remains in Level0 gate")

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
    print("active-remediation-round=2 nodes=3 revision=6.30.0-0supralinux3")

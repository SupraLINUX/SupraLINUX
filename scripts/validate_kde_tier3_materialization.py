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
req(m.get("state") in {"pending-ci", "PASS"}, "Tier3 materialization lifecycle")
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

for node in selected:
    state = m["nodes"][node]
    contract = contracts[node]
    can = canonical[node]
    req(state.get("state") in {"pending", "materialized"}, f"{node}: materialization state")
    req(contract.get("contract_state") == "contract-ready", f"{node}: contract-ready")
    req(contract.get("package_version_candidate") == "6.30.0-0supralinux1", f"{node}: candidate version")
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
        for key in ("dsc_sha256", "debian_tar_sha256", "source_tree_sha256", "materialized_tree_sha256", "adapted_control_sha256", "adapted_rules_sha256", "artifact_sha256"):
            req(isinstance(ev.get(key), str) and len(ev.get(key)) == 64, f"{node}: {key}")
        req(isinstance(ev.get("workflow_run"), int) and isinstance(ev.get("job_id"), int) and isinstance(ev.get("artifact_id"), int), f"{node}: run/job/artifact evidence")

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
else:
    req(all(m["nodes"][n].get("state") == "materialized" for n in selected), "PASS requires all materialization nodes materialized")
    req(c.get("state") == "materialized", "PASS materialization contract lifecycle")
    req(t.get("discovery_policy", {}).get("phase") == "build-campaign-planning", "post-materialization phase")
    req(t.get("discovery_policy", {}).get("package_builds") == "not-authorized-before-tier3-build-campaign", "post-materialization binary build gate")
    req(t.get("support_components", {}).get("next_gate") == "tier3-build-campaign-planning", "post-materialization next gate")
    summary = m.get("evidence_summary", {})
    req(summary.get("result") == "PASS" and summary.get("package_attempted") is False and summary.get("package_state_effect") == "none", "materialization evidence summary")
    for node in selected:
        planning = canonical[node].get("planning", {})
        req(planning.get("readiness") == "materialized", f"{node}: materialized readiness")
        req(planning.get("package_contract") == "materialized", f"{node}: materialized package contract")

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

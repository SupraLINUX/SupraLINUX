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

deps = load("manifests/kde-frameworks-tier2-dependencies.json")
plan = load("manifests/kde-tier2-campaign-plan.json")
tier1_registry = load("manifests/kde-frameworks-tier1-dependencies.json")

audit = deps.get("provider_audit", {})
registry = deps.get("provider_registry", {})
batch = audit.get("nodes", [])

req(audit.get("schema") == 1, "Tier 2 provider-audit schema")
req(audit.get("batch") == "tier2-provider-audit-1", "Tier 2 provider-audit batch id")
req(audit.get("status") in {"pending-ci", "PASS"}, "Tier 2 provider-audit status")
req(audit.get("provider_platform") == "ubuntu-resolute", "Tier 2 provider platform")
req(audit.get("source_authority") == "kde-upstream-v6.30.0", "Tier 2 source authority")
req(audit.get("authoritative_package_build") is False, "provider audit must not claim package build certification")
if audit.get("status") == "pending-ci":
    if audit.get("mode") == "remediation-revalidation":
        req(batch == ["knotifications","kstatusnotifieritem","kunitconversion"], "remediation provider revalidation node set")
        req(audit.get("previous_pass",{}).get("status")=="PASS", "previous provider-audit PASS retained")
    else:
        req(batch == plan.get("next_provider_audit_batch"), "pending provider-audit batch must equal generated campaign next batch")
elif audit.get("status") == "PASS":
    downstream_ready=set(plan.get("package_contract_ready", [])) | set(plan.get("build_queue", []))
    req(set(batch) <= downstream_ready, "PASS provider-audit nodes must remain contract/build-ready")
    evidence = audit.get("evidence", {})
    req(evidence.get("result") == "PASS", "provider-audit PASS evidence result")
    req(evidence.get("package_state_effect") == "none", "provider-audit must not alter package state")
    req(isinstance(evidence.get("artifact_id"), int), "provider-audit artifact evidence")
    req(len(evidence.get("artifact_sha256", "")) == 64, "provider-audit artifact SHA-256")

req(registry.get("inherited_from") == "manifests/kde-frameworks-tier1-dependencies.json", "provider registry inheritance")
req(set(registry.get("inherited_sections", [])) == {"qt_provider_packages", "requirements"}, "provider registry inherited sections")

qt_registry = tier1_registry.get("qt_provider_packages", {})
ext_registry = dict(tier1_registry.get("requirements", {}))
ext_registry.update(registry.get("additions", {}))
nodes = deps.get("nodes", {})

for node_id in batch:
    node = nodes.get(node_id, {})
    req(node, f"{node_id}: dependency node exists")
    expected_audit_state = "PASS" if audit.get("status") == "PASS" else "pending-ci"
    req(node.get("provider_audit") == expected_audit_state, f"{node_id}: provider audit state")
    req(node.get("selected_linux_profile", {}).get("BUILD_TESTING") is True, f"{node_id}: BUILD_TESTING selected")
    for category in ("required", "provider_selected", "default_enabled", "test", "optional"):
        for component in node.get("qt", {}).get(category, []):
            req(component in qt_registry, f"{node_id}: Qt provider mapping exists for {component}")
        for key in node.get("external", {}).get(category, []):
            req(key in ext_registry, f"{node_id}: external provider mapping exists for {key}")

for node_id in ("knotifications", "kstatusnotifieritem", "kunitconversion"):
    node = nodes[node_id]
    req(node.get("selected_linux_profile", {}).get("BUILD_PYTHON_BINDINGS") is True, f"{node_id}: Python bindings selected")
    ext = set(node.get("external", {}).get("default_enabled", []))
    req({"python-dev", "shiboken6", "pyside6", "python-build", "shiboken-clang-tooling"} <= ext, f"{node_id}: Python binding provider closure")

req(nodes["kcrash"].get("selected_linux_profile", {}).get("WITH_X11") is True, "KCrash X11 selected")
req("x11" in nodes["kcrash"].get("external", {}).get("provider_selected", []), "KCrash X11 provider")
req(nodes["knotifications"].get("selected_linux_profile", {}).get("USE_DBUS") is True, "KNotifications DBus selected")
req("canberra" in nodes["knotifications"].get("external", {}).get("required", []), "KNotifications Canberra required")
req(nodes["kstatusnotifieritem"].get("selected_linux_profile", {}).get("WITHOUT_X11") is False, "KStatusNotifierItem X11 not disabled")
req(nodes["kstatusnotifieritem"].get("selected_linux_profile", {}).get("USE_DBUS") is True, "KStatusNotifierItem DBus selected")
clang=registry.get("additions",{}).get("shiboken-clang-tooling",{})
req(clang.get("packages")==["llvm-dev","libclang-common-21-dev"], "Shiboken Clang provider package closure")
req(clang.get("required_probe")=="/usr/lib/llvm-21/lib/clang/21/include/stddef.h", "Shiboken Clang builtin header probe")

doc = (ROOT / "docs/kde-tier2-provider-audit.md").read_text()
for token in ("KCrash", "KNotifications", "KStatusNotifierItem", "KUnitConversion", "Syndication", "provider audit", "not a package PASS"):
    req(token in doc, f"provider-audit documentation missing {token}")

if errors:
    for error in errors:
        print("ERROR:", error, file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 2 provider-audit definition: PASS")
print("batch=" + ",".join(batch))
print("claim=provider availability/profile only; package state unchanged")

#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT / path).read_text())

def req(value, message):
    if not value:
        print("ERROR:", message, file=sys.stderr)
        raise SystemExit(1)

m = load("manifests/kde-tier3-kio-round18-provider-contract.json")
r17 = load("manifests/kde-tier3-kio-round17-diagnostic.json")
tier3 = load("manifests/kde-frameworks-tier3.json")
level1 = load("manifests/kde-tier3-build-level1.json")
contracts = load("manifests/kde-tier3-package-contracts.json")
doc = (ROOT / "docs/kde-tier3-kio-round18-provider-contract.md").read_text()
workflow = (ROOT / ".github/workflows/kde-tier3-kio-round18-provider-contract.yml").read_text()
runner = (ROOT / "scripts/run-kde-tier3-kio-round18-provider-contract.py").read_text()

req(m.get("schema") == 1 and m.get("node") == "kio" and m.get("round") == 18, "Round18 identity")
req(m.get("authority") == "kde-upstream" and m.get("provider_platform") == "ubuntu-resolute", "Round18 authority/provider boundary")
req(m.get("frameworks_series") == "6.30.0" and m.get("upstream_ref") == "v6.30.0", "Round18 upstream version")
req(m.get("claim") == "non-promoting-qt-svg-provider-contract-ownership-audit", "Round18 claim")
req(m.get("non_promoting") is True and m.get("package_attempted") is False and m.get("package_state_effect") == "none", "Round18 non-promoting semantics")
req(m.get("canonical_source_modified") is False and m.get("dag_state_changes_allowed") is False and m.get("downstream_eligibility_changes_allowed") is False, "Round18 canonical safety")
req(m.get("package_revision_allocation") is False, "Round18 must not allocate KIO -8 before audit")
req(m.get("status") in {"definition-pending-audit", "audit-PASS"}, "Round18 lifecycle")
req(m.get("canonical_snapshot") == "12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED", "Round18 canonical snapshot")

req(r17.get("status") == "diagnostic-PASS", "Round17 must be closed")
req(r17.get("diagnostic_results", {}).get("conclusion") == "qt6-svg-plugins-presence-controls-both-kio-icon-name-failures", "Round17 root cause")

nodes = {n["id"]: n for n in tier3.get("nodes", [])}
kio = nodes["kio"]
req(kio.get("state") == "FAIL", "KIO remains FAIL")
req(kio.get("packaging", {}).get("package_version") == "6.30.0-0supralinux7", "KIO remains revision -7")
req(kio.get("packaging", {}).get("downstream_eligible") is False, "KIO remains downstream-ineligible")
req(level1.get("canonical_snapshot") == "12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED", "Level1 snapshot unchanged")
if m.get("status") == "definition-pending-audit":
    req(level1.get("next_gate") == "tier3-round18-kio-qt-svg-provider-contract-remediation-definition", "Round18 live handoff before audit")
else:
    req(m.get("next_gate") == "tier3-round18-kio-test-provider-remediation-materialization-definition", "Round18 historical post-audit handoff")

up = m.get("upstream_contract_evidence", {})
req(up.get("kio", {}).get("cmake_blob") == "2b655093491670009d9396b60159afbec5cc8385", "KIO upstream CMake evidence")
req(up.get("kiconthemes", {}).get("cmake_blob") == "252edc1c87f2b312801771c4e971740b71fdf01e", "KIconThemes upstream CMake evidence")
req(up.get("kiconthemes", {}).get("src_cmake_blob") == "99cbb97db7cc47828b1fde49ed1d58f86b3d76d7", "KIconThemes target linkage evidence")
req(up.get("breeze_icons", {}).get("cmake_blob") == "4482a5fa712f27feec0ee3ec4c5c7bcc07a660d3", "Breeze Icons upstream evidence")

exp = m.get("resolute_contract_expectations", {})
req(exp.get("qt6-svg-plugins", {}).get("expected_version") == "6.10.2-2", "Resolute SVG plugin version")
req(exp.get("qt6-svg-dev", {}).get("expected_version") == "6.10.2-2", "Resolute SVG dev version")
req(exp.get("libqt6gui6", {}).get("must_recommend") == "qt6-svg-plugins", "Qt GUI recommendation contract")

precedent = m.get("supralinux_precedent", {})
req(precedent.get("node") == "kiconthemes" and precedent.get("relation") == "qt6-svg-plugins <!nocheck>", "KIconThemes precedent")
kicon_rel = [(x.get("action"), x.get("package") or x.get("relation")) for x in contracts["nodes"]["kiconthemes"].get("source_build_relation_overrides", [])]
req(("ensure", "qt6-svg-plugins <!nocheck>") in kicon_rel, "KIconThemes retained SVG test provider")

decision = m.get("decision_if_audit_passes", {})
req(decision.get("owner") == "kio-build-test-closure", "Round18 owner decision")
req(decision.get("field") == "Build-Depends" and decision.get("action") == "ensure", "Round18 relation action")
req(decision.get("relation") == "qt6-svg-plugins <!nocheck>", "Round18 KIO test-provider relation")
req(decision.get("runtime_binary_relation") == "none", "Round18 must not create runtime binary relation")

kio_rel = [(x.get("action"), x.get("package") or x.get("relation")) for x in contracts["nodes"]["kio"].get("source_build_relation_overrides", [])]
if m.get("status") == "definition-pending-audit":
    req(("ensure", "qt6-svg-plugins <!nocheck>") not in kio_rel, "Round18 definition must not implement relation before audit evidence")
    req(m.get("next_gate") == "tier3-round18-kio-qt-svg-provider-contract-audit-evidence", "Round18 pending next gate")
    req("audit_evidence" not in m, "Round18 pending definition cannot claim audit evidence")
else:
    ev = m.get("audit_evidence", {})
    req(ev.get("result") == "AUDIT_COMPLETE", "Round18 audit result")
    req(ev.get("package_attempted") is False and ev.get("package_state_effect") == "none", "Round18 audit remains non-promoting")
    req(m.get("next_gate") == "tier3-round18-kio-test-provider-remediation-materialization-definition", "Round18 PASS next gate")

for token in (
    "qt6-svg-plugins <!nocheck>",
    "libqt6gui6",
    "qt6-svg-dev",
    "KIO remains `6.30.0-0supralinux7` FAIL",
):
    req(token in doc, f"Round18 documentation token {token}")

for token in (
    "qt6-svg-plugins",
    "libqt6gui6",
    "libkf6iconthemes6",
    "kf6-breeze-icon-theme",
    "AUDIT_COMPLETE",
):
    req(token in runner, f"Round18 runner token {token}")

req("scripts/validate_kde_tier3_kio_round18_provider_contract.py" in workflow, "Round18 workflow validator linkage")
req("scripts/run-kde-tier3-kio-round18-provider-contract.py" in workflow, "Round18 workflow runner linkage")
req(m.get("stable_promotion_requires_explicit_user_approval") is True, "Round18 stable gate")

print("KDE Tier 3 KIO Round 18 provider-contract definition: PASS")
print("canonical=12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED")
print("KIO=FAIL 6.30.0-0supralinux7")
print("next_gate=" + m["next_gate"])

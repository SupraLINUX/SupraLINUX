#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests" / "kde-tier1-package-campaign.json"
TIER1 = ROOT / "manifests" / "kde-frameworks-tier1.json"
RUNNER = ROOT / "scripts" / "run-kde-tier1-package-preflight.sh"
SCOPE = ROOT / "scripts" / "kde-tier1-package-preflight-needed.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-tier1-package-preflight.yml"
DOC = ROOT / "docs" / "kde-tier1-package-batch1.md"

EXPECTED = {
    "kcodecs": {
        "source_sha256": "a42c79ff3237b73789d1c63cdfd848c0d59671ce5e93723a2efa128f00cb3450",
        "symbols_sha256": "8dfcf6c469195a45e5f1d038a42cf1f223fe12d00c3ee1e3aa5125142935e1a3",
        "artifact_id": 10302917591,
        "artifact_sha256": "6fcf23a69991e453d3563d580aa63fa082c27ce8490ad52dd9e125ee41cd8f6f",
        "job_id": 103596438631,
        "required_build_deps": ["qt6-base-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
        "test_rule": "dh_auto_test",
    },
    "kdbusaddons": {
        "source_sha256": "063ef80460f76d86dc4b033ef04b65b69ba82ee0de410440fe609465e7f5a997",
        "symbols_sha256": "03b48faa6b7c5b400f3a165c38c4c5e7e7fc454a0b099ef1ad776b3809851683",
        "artifact_id": 10303285563,
        "artifact_sha256": "2a581e9f4c01c15c611b5b3d3a98343504177f1d52fb2225f92ce3c6428f54ed",
        "job_id": 103596438606,
        "required_build_deps": ["dbus-daemon <!nocheck>", "qt6-base-dev (>= 6.9.0~)", "qt6-base-private-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
        "test_rule": "dbus-run-session dh_auto_test",
    },
    "threadweaver": {
        "source_sha256": "e5400968a41820393e76190ab5dbb276c09513263d1b185d64b40f82dcd9b457",
        "symbols_sha256": "a7403ee234e24d20f20502ed4a07b13ef265ec285cd5fb2b44709dfea39907b7",
        "artifact_id": 10303265649,
        "artifact_sha256": "0b47374207ae54632c4ba9594eedbcc72d46eed552696b608110ebb5bce6acb6",
        "job_id": 103596438491,
        "required_build_deps": ["qt6-base-dev (>= 6.9.0~)"],
        "test_rule": "dh_auto_test",
    },
}

errors: list[str] = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot load {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(value, dict):
        raise SystemExit(f"{path.relative_to(ROOT)} must contain an object")
    return value

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""

campaign = load(CAMPAIGN)
tier1 = load(TIER1)
runner = read(RUNNER)
scope = read(SCOPE)
workflow = read(WORKFLOW)
doc = read(DOC)

require(campaign.get("schema") == 1, "Campaign schema must remain 1")
require(campaign.get("authority") == "kde-upstream", "Campaign authority must remain KDE upstream")
require(campaign.get("frameworks_series") == "6.30.0", "Campaign must target Frameworks 6.30.0")
require(campaign.get("state") == "remediation-pending-build", "Batch 1 must be in remediation-pending-build before attempt 2")
first = campaign.get("first_attempt", {})
require(first.get("workflow_run") == 34709829162 and first.get("commit") == "50611225422b05803ee49d8d5fc8ff4f84a21d99", "First-attempt run/commit evidence mismatch")
require(first.get("result") == "FAIL" and first.get("cause_class") == "supralinux-package-test-policy", "First-attempt failure classification mismatch")
require("reuse lint" in first.get("cause", "") and "autotests" in first.get("cause", ""), "First-attempt cause must name the invalid REUSE gate and unreached autotests")

nodes = campaign.get("nodes", {})
require(set(nodes) == set(EXPECTED), "Batch 1 node set changed")
tier1_nodes = {x.get("id"): x for x in tier1.get("nodes", []) if isinstance(x, dict)}

for node_id, expected in EXPECTED.items():
    node = nodes.get(node_id, {})
    require(node.get("state") == "remediation-pending-build", f"{node_id}: remediation state mismatch")
    require(node.get("last_result") == "FAIL", f"{node_id}: first attempt must remain recorded as FAIL")
    require(node.get("package_version") == "6.30.0-0supralinux2", f"{node_id}: remediation revision must be -0supralinux2")
    require(node.get("source_sha256") == expected["source_sha256"], f"{node_id}: source hash changed")
    require(node.get("symbols", {}).get("sha256") == expected["symbols_sha256"], f"{node_id}: symbols baseline changed")
    evidence = node.get("evidence", [])
    require(len(evidence) == 1, f"{node_id}: exactly one historical attempt expected before retry")
    if evidence:
        item = evidence[0]
        require(item.get("result") == "FAIL", f"{node_id}: historical attempt must be FAIL")
        require(item.get("workflow_run") == 34709829162 and item.get("job_id") == expected["job_id"], f"{node_id}: FAIL workflow/job mismatch")
        require(item.get("artifact_id") == expected["artifact_id"] and item.get("artifact_sha256") == expected["artifact_sha256"], f"{node_id}: FAIL artifact evidence mismatch")
        require(item.get("attempted_package_version") == "6.30.0-0supralinux1", f"{node_id}: first attempted revision mismatch")
        require(item.get("failure_stage") == "sbuild" and item.get("failure_substage") == "override_dh_auto_test/reuse-lint-before-autotests", f"{node_id}: failure stage mismatch")
        require(item.get("autotests_reached") is False, f"{node_id}: must not claim KDE autotests ran in attempt 1")

    source_node = tier1_nodes.get(node_id, {})
    require(source_node.get("source_sha256") == expected["source_sha256"], f"{node_id}: source/campaign hash mismatch")
    require(source_node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: KDE predecessor changed")

    pkg = ROOT / "packages" / "kde" / node_id / "debian"
    control = read(pkg / "control")
    rules = read(pkg / "rules")
    changelog = read(pkg / "changelog")
    require(changelog.startswith(f"kf6-{node_id} (6.30.0-0supralinux2) resolute;"), f"{node_id}: changelog remediation revision mismatch")
    require("6.30.0-0supralinux1" in changelog, f"{node_id}: first failed revision must remain in changelog")
    require("reuse" not in control.lower(), f"{node_id}: invented REUSE Build-Depends must be removed")
    require("reuse lint" not in rules, f"{node_id}: invented REUSE test gate must be removed")
    require("-DBUILD_TESTING=ON" in rules, f"{node_id}: KDE tests must remain enabled")
    require(expected["test_rule"] in rules, f"{node_id}: real KDE test command missing")
    for dep in ("debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)"):
        require(dep in control, f"{node_id}: required packaging dependency missing: {dep}")
    for dep in expected["required_build_deps"]:
        require(dep in control, f"{node_id}: required upstream/provider dependency missing: {dep}")

for token in (
    "dpkg-source -b",
    "--chroot-mode=unshare",
    "--extra-package=\"${ECM_DEB}\"",
    "sha256sum --check --strict",
    "lintian --fail-on error",
    "consumer-smoke",
    "downstream_eligible=yes",
    "remediation-pending-build",
):
    require(token in runner, f"Generic runner missing invariant: {token}")
for forbidden in ("UPSTREAM_TARBALL=", "DEV_DEB=", "DOC_DEB=", "reuse lint"):
    require(forbidden not in runner, f"Generic runner retained obsolete/unused token: {forbidden}")
require("dpkg-buildpackage -S" not in runner, "Source assembly must remain dpkg-source -b")

for token in ("kcodecs|kdbusaddons|threadweaver", 'packages/kde/"${NODE}"/*', "manifests/kde-tier1-package-campaign.json"):
    require(token in scope, f"Batch scope missing invariant: {token}")
require("docs/" not in scope, "Docs-only changes must not rebuild packages")

for token in ("fail-fast: false", "max-parallel: 3", "- kcodecs", "- kdbusaddons", "- threadweaver", "10298635300", "10301938362"):
    require(token in workflow, f"Batch workflow missing invariant: {token}")

for token in ("34709829162", "10302917591", "10303285563", "10303265649", "6.30.0-0supralinux2"):
    require(token in doc, f"Batch documentation missing evidence {token}")
require("autotests did not run" in doc.lower(), "Documentation must not imply KDE autotests passed in attempt 1")
require("reuse" in doc.lower() and "not" in doc.lower(), "Documentation must explain why REUSE gate was removed")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 batch 1 remediation validation: PASS")
print("Historical attempt 1: kcodecs/kdbusaddons/threadweaver FAIL at SupraLINUX REUSE test gate")
print("Candidate revision: 6.30.0-0supralinux2; KDE autotests remain enabled")

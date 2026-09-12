#!/usr/bin/env python3
from __future__ import annotations

import json
import re
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
        "root_cmake_blob": "a4844477467d5c7b47875f837fa6db0b22550397",
        "symbols_sha256": "8dfcf6c469195a45e5f1d038a42cf1f223fe12d00c3ee1e3aa5125142935e1a3",
        "copyright_sha256": "deb13c487cf8ec5a988f1673e690d0125bfc1fa451c95a9dd3e9bcbc867cca76",
        "required_build_deps": ["qt6-base-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
        "forbidden_build_deps": ["gperf", "doxygen", "libxkbcommon-dev", "qt6-base-private-dev"],
        "test_rule": None,
    },
    "kdbusaddons": {
        "source_sha256": "063ef80460f76d86dc4b033ef04b65b69ba82ee0de410440fe609465e7f5a997",
        "root_cmake_blob": "26cde2148db4d86adeea0f4bda597f0f9e610816",
        "symbols_sha256": "03b48faa6b7c5b400f3a165c38c4c5e7e7fc454a0b099ef1ad776b3809851683",
        "copyright_sha256": "46cde028d2d8f600ea3a3a4b41b7e0c40d5264dfb50cad40484c865fb0823ede",
        "required_build_deps": ["dbus-daemon <!nocheck>", "qt6-base-dev (>= 6.9.0~)", "qt6-base-private-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
        "forbidden_build_deps": ["doxygen", "libxkbcommon-dev"],
        "test_rule": "dbus-run-session dh_auto_test",
    },
    "threadweaver": {
        "source_sha256": "e5400968a41820393e76190ab5dbb276c09513263d1b185d64b40f82dcd9b457",
        "root_cmake_blob": "309efd1d962d925a71610ea65fed2a1007ef055d",
        "symbols_sha256": "a7403ee234e24d20f20502ed4a07b13ef265ec285cd5fb2b44709dfea39907b7",
        "copyright_sha256": "baa640b7abaa7f5f1fbfc0acd11f4ecedf9a01f187b691523ea5d879cb35ff88",
        "required_build_deps": ["qt6-base-dev (>= 6.9.0~)"],
        "forbidden_build_deps": ["doxygen", "libxkbcommon-dev", "qt6-tools-dev", "qt6-base-private-dev"],
        "test_rule": None,
    },
}

errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot load {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(data, dict):
        print(f"ERROR: {path.relative_to(ROOT)} must contain an object", file=sys.stderr)
        raise SystemExit(1)
    return data


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

require(campaign.get("schema") == 1, "Tier 1 package campaign schema must be 1")
require(campaign.get("authority") == "kde-upstream", "Tier 1 package campaign authority must remain KDE upstream")
require(campaign.get("frameworks_series") == "6.30.0", "Tier 1 package campaign must target Frameworks 6.30.0")
require(campaign.get("provider_platform") == "ubuntu-resolute", "Tier 1 package campaign provider platform must be Ubuntu Resolute")
require(campaign.get("batch") == "tier1-batch-1", "Unexpected Tier 1 campaign batch")
require(campaign.get("state") == "prepared-pending-build", "Batch must remain prepared-pending-build before first attempt")

shared = campaign.get("shared_predecessors", {})
ecm = shared.get("extra_cmake_modules", {})
require(ecm == {
    "state": "PASS",
    "version": "6.30.0-0supralinux3",
    "workflow_run": 34694951158,
    "artifact_id": 10298635300,
    "deb_sha256": "ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f",
}, "Batch must pin the retained ECM PASS predecessor")
tree_ref = shared.get("packaging_trees", {})
require(tree_ref == {
    "status": "PASS",
    "workflow_run": 34708030450,
    "artifact_id": 10301938362,
    "artifact_sha256": "6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6",
    "snapshot_json_sha256": "f761a2d92005107eac2e82322b1b776e4f8867851e657ce79748f0cb266ee345",
}, "Batch must pin the retained generic packaging-tree PASS")

nodes = campaign.get("nodes", {})
require(set(nodes) == set(EXPECTED), "Batch 1 node set must be exactly kcodecs/kdbusaddons/threadweaver")
tier1_nodes = {item.get("id"): item for item in tier1.get("nodes", []) if isinstance(item, dict)}

for node_id, expected in EXPECTED.items():
    node = nodes.get(node_id, {})
    require(node.get("state") == "prepared-pending-build", f"{node_id}: campaign node must remain prepared-pending-build before attempt")
    require(node.get("upstream_version") == "6.30.0", f"{node_id}: upstream version mismatch")
    require(node.get("source_sha256") == expected["source_sha256"], f"{node_id}: source SHA-256 mismatch")
    require(node.get("root_cmake_blob") == expected["root_cmake_blob"], f"{node_id}: upstream CMake blob mismatch")
    require(node.get("package_version") == "6.30.0-0supralinux1", f"{node_id}: initial package revision mismatch")
    require(node.get("symbols", {}).get("sha256") == expected["symbols_sha256"], f"{node_id}: Ubuntu symbols baseline hash mismatch")
    require(node.get("copyright", {}).get("sha256") == expected["copyright_sha256"], f"{node_id}: Debian copyright reference hash mismatch")

    source_node = tier1_nodes.get(node_id, {})
    require(source_node.get("source_sha256") == expected["source_sha256"], f"{node_id}: campaign/source manifest hash mismatch")
    require(source_node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: Tier 1 node must depend only on ECM in KDE DAG")
    require(source_node.get("kde_framework_dependencies") == [], f"{node_id}: Tier 1 node cannot depend on another Framework")
    require(source_node.get("state") == "pending", f"{node_id}: package state must remain pending until actually attempted")
    require(source_node.get("packaging") == {"state": "pending"}, f"{node_id}: source manifest packaging state must remain pending")

    pkg = ROOT / "packages" / "kde" / node_id / "debian"
    consumer = ROOT / "packages" / "kde" / node_id / "consumer"
    for relative in ("control", "changelog", "copyright.reference", "rules", "README.source", "watch", "source/format"):
        require((pkg / relative).is_file(), f"{node_id}: missing debian/{relative}")
    require((consumer / "CMakeLists.txt").is_file() and (consumer / "main.cpp").is_file(), f"{node_id}: missing consumer smoke source")

    control = read(pkg / "control")
    rules = read(pkg / "rules")
    changelog = read(pkg / "changelog")
    symbols_ref = read(pkg / (node["symbols"]["file"] + ".reference"))
    copyright_ref = read(pkg / "copyright.reference")
    require(control.startswith(f"Source: kf6-{node_id}\n"), f"{node_id}: source package naming mismatch")
    require("Maintainer: SupraLINUX Project <packages@supralinux.invalid>" in control, f"{node_id}: maintainer identity mismatch")
    for dep in ("debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)", "reuse"):
        require(dep in control, f"{node_id}: required build dependency missing: {dep}")
    for dep in expected["required_build_deps"]:
        require(dep in control, f"{node_id}: upstream-selected provider dependency missing: {dep}")
    for dep in expected["forbidden_build_deps"]:
        require(dep not in control, f"{node_id}: stale/reference-only Build-Depends retained: {dep}")
    require("extra-cmake-modules (>= 6.28" not in control and "extra-cmake-modules (>= 6.24" not in control, f"{node_id}: distro ECM floor must not define KDE build")
    require("BUILD_QCH" not in rules, f"{node_id}: obsolete reference BUILD_QCH switch must not be copied")
    require("-DBUILD_TESTING=ON" in rules, f"{node_id}: selected package profile must run upstream tests")
    if expected["test_rule"]:
        require(expected["test_rule"] in rules, f"{node_id}: required deterministic test wrapper missing")
    require(changelog.startswith(f"kf6-{node_id} (6.30.0-0supralinux1) resolute;"), f"{node_id}: changelog initial revision mismatch")
    require(expected["symbols_sha256"] in symbols_ref and "34708030450" in symbols_ref and "10301938362" in symbols_ref, f"{node_id}: symbols reference provenance mismatch")
    require(expected["copyright_sha256"] in copyright_ref and "34708030450" in copyright_ref and "10301938362" in copyright_ref, f"{node_id}: copyright reference provenance mismatch")
    require("reuse lint" in rules, f"{node_id}: upstream REUSE metadata must be validated during package tests")
    require(read(pkg / "source/format").strip() == "3.0 (quilt)", f"{node_id}: source format must be 3.0 (quilt)")

for token in (
    "dpkg-source -b",
    "--chroot-mode=unshare",
    "--extra-package=\"${ECM_DEB}\"",
    "sha256sum --check --strict",
    "lintian --fail-on error",
    "extra-cmake-modules (= ${ECM_VERSION})",
    "TIER1_REFERENCE_DIR",
    "packaging-reference-trees-only",
    "consumer-smoke",
    "COPYRIGHT_REFERENCE",
    "2026, SupraLINUX Project",
    "downstream_eligible=yes",
):
    require(token in runner, f"Generic Tier 1 runner missing invariant: {token}")
require("dpkg-buildpackage -S" not in runner, "Generic Tier 1 runner must not execute debian/rules on source-assembly host")
require("34708030450" not in runner, "Generic runner must read retained reference provenance from campaign manifest, not duplicate run IDs")

for token in (
    "kcodecs|kdbusaddons|threadweaver",
    'packages/kde/"${NODE}"/*',
    "manifests/kde-tier1-package-campaign.json",
    "scripts/run-kde-tier1-package-preflight.sh",
    "scripts/kde-tier1-package-preflight-needed.sh",
    ".github/workflows/kde-tier1-package-preflight.yml",
):
    require(token in scope, f"Tier 1 package scope missing invariant: {token}")
require("docs/" not in scope, "Tier 1 package builds must not rerun for docs-only changes")
require("manifests/kde-frameworks-tier1.json" not in scope, "Evidence/state-only Tier 1 manifest changes must not automatically rebuild prepared packages")

for token in (
    "fail-fast: false",
    "max-parallel: 3",
    "- kcodecs",
    "- kdbusaddons",
    "- threadweaver",
    "fetch-depth: 0",
    "bash scripts/kde-tier1-package-preflight-needed.sh",
    "10298635300",
    "34694951158",
    "10301938362",
    "34708030450",
    "bash scripts/run-kde-tier1-package-preflight.sh",
    "retention-days: 90",
):
    require(token in workflow, f"Tier 1 batch workflow missing invariant: {token}")

require("KDE upstream" in doc and "authority" in doc.lower(), "Batch documentation must preserve KDE authority")
for node_id in EXPECTED:
    require(node_id in doc, f"Batch documentation must name {node_id}")
require("prepared" in doc.lower() and "pending" in doc.lower(), "Batch documentation must not claim unattempted package PASS")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 batch 1 preparation validation: PASS")
print("Prepared independent nodes: kcodecs, kdbusaddons, threadweaver")
print("States: prepared-pending-build; source-manifest nodes remain pending until actual attempts")
print("Shared PASS inputs: ECM 6.30.0-0supralinux3 + generic 58-tree reference artifact")

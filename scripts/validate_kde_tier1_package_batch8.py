#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests" / "kde-tier1-package-campaign-batch8.json"
TIER1 = ROOT / "manifests" / "kde-frameworks-tier1.json"
PACKAGE = ROOT / "packages" / "kde" / "kguiaddons" / "debian"
CONSUMER = ROOT / "packages" / "kde" / "kguiaddons" / "consumer"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-tier1-package-batch8.yml"
ROUTER = ROOT / ".github" / "workflows" / "pr-ci-router.yml"
RUNNER = ROOT / "scripts" / "run-kde-tier1-package-batch8-preflight.sh"
SCOPE = ROOT / "scripts" / "kde-tier1-package-batch8-needed.sh"
SCOPE_TEST = ROOT / "scripts" / "test-kde-tier1-package-batch8-scope.sh"
DOC = ROOT / "docs" / "kde-tier1-package-batch8.md"
errors: list[str] = []


def require(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)


def text(path: Path) -> str:
    if not path.exists():
        errors.append(f"required Batch 8 file missing: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


try:
    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    tier1 = json.loads(TIER1.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: cannot read Batch 8 manifests: {exc}", file=sys.stderr)
    raise SystemExit(1)

require(campaign.get("schema") == 2, "Batch 8 campaign schema must be 2")
require(campaign.get("frameworks_series") == "6.30.0", "Batch 8 must target Frameworks 6.30.0")
require(campaign.get("authority") == "kde-upstream", "Batch 8 authority must be kde-upstream")
require(campaign.get("provider_platform") == "ubuntu-resolute", "Batch 8 provider platform must be Ubuntu Resolute")
require(campaign.get("batch") == "tier1-batch-8", "Batch 8 identifier mismatch")
require(campaign.get("selected_nodes") == ["kguiaddons"], "Batch 8 must select only KGuiAddons")

node = campaign.get("nodes", {}).get("kguiaddons", {})
require(node.get("upstream_version") == "6.30.0", "KGuiAddons upstream version must be 6.30.0")
require(node.get("source_package") == "kf6-kguiaddons", "KGuiAddons source package mismatch")
require(node.get("package_version") == "6.30.0-0supralinux1", "initial KGuiAddons package version mismatch")
require(node.get("source_sha256") == "e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d", "KGuiAddons source SHA-256 mismatch")
require(node.get("state") in {"prepared-pending-build", "remediation-pending-build", "PASS"}, "KGuiAddons Batch 8 state is invalid")
require(node.get("kde_framework_build_dependencies") == [], "KGuiAddons must remain Tier 1 without KDE Framework Build-Depends")
require(node.get("public_header_dependencies") == ["KCoreAddons"], "KGuiAddons KImageCache public-header dependency must be explicit")
for key in ("WITH_WAYLAND", "WITH_X11", "USE_DBUS", "BUILD_GEO_SCHEME_HANDLER", "BUILD_PYTHON_BINDINGS", "BUILD_TESTING"):
    require(node.get("upstream_defaults", {}).get(key) == "ON", f"KGuiAddons upstream default must remain ON: {key}")

canonical = next((x for x in tier1.get("nodes", []) if x.get("id") == "kguiaddons"), None)
require(isinstance(canonical, dict), "canonical Tier 1 manifest must contain kguiaddons")
if isinstance(canonical, dict):
    require(canonical.get("upstream_version") == "6.30.0", "canonical KGuiAddons version mismatch")
    require(canonical.get("source_sha256") == node.get("source_sha256"), "canonical KGuiAddons source hash mismatch")
    if node.get("state") != "PASS":
        require(canonical.get("state") == "pending", "canonical KGuiAddons must remain pending before a real PASS")

control = text(PACKAGE / "control")
rules = text(PACKAGE / "rules")
workflow = text(WORKFLOW)
router = text(ROUTER)
runner = text(RUNNER)
scope = text(SCOPE)
scope_test = text(SCOPE_TEST)
doc = text(DOC)

required_package_files = (
    "README.source", "changelog", "control", "copyright.reference",
    "libkf6guiaddons-bin.install", "libkf6guiaddons-bin.lintian-overrides",
    "libkf6guiaddons-data.install", "libkf6guiaddons-dev.install",
    "libkf6guiaddons-doc.install", "libkf6guiaddons6.install",
    "libkf6guiaddons6.symbols.reference", "python3-kguiaddons.install",
    "qml6-module-org-kde-guiaddons.install", "rules", "source/format",
    "upstream/signing-key.asc",
)
for rel in required_package_files:
    require((PACKAGE / rel).exists(), f"KGuiAddons package file missing: {rel}")
require((CONSUMER / "CMakeLists.txt").exists(), "KGuiAddons consumer CMakeLists missing")
require((CONSUMER / "main.cpp").exists(), "KGuiAddons consumer source missing")

# Fail in Repository Policy before an expensive build if the materialized key
# does not match the exact key pinned by the Batch 8 manifest.
signing_key_path = PACKAGE / "upstream" / "signing-key.asc"
if signing_key_path.exists():
    signing_key_sha256 = hashlib.sha256(signing_key_path.read_bytes()).hexdigest()
    require(
        signing_key_sha256 == node.get("signing_key", {}).get("sha256"),
        f"KGuiAddons signing key SHA-256 mismatch: {signing_key_sha256}",
    )

# Authority/provider distinction: KCoreAddons is not a build dependency, but the
# public KImageCache header requires its development surface for consumers.
build_dep_block = control.split("Build-Depends:", 1)[1].split("Standards-Version:", 1)[0] if "Build-Depends:" in control else ""
require("libkf6coreaddons-dev" not in build_dep_block, "KCoreAddons must not be a KGuiAddons Build-Depends")
require("libkf6coreaddons-dev (>= 6.30.0~)" in control, "libkf6guiaddons-dev must expose KCoreAddons public-header dependency")
require("python3-kguiaddons" in control, "upstream Python bindings must have a binary package")
require("dh-sequence-python3" in control and "python3-build" in control and "python3-setuptools" in control, "Python binding build providers are incomplete")
require("dh-sequence-qmldeps" in control, "KGuiAddons QML package must use Debian-family qmldeps integration")
for token in ("libwayland-dev (>= 1.9~)", "libx11-dev", "libxcb1-dev", "plasma-wayland-protocols (>= 1.15.0~)", "wayland-protocols (>= 1.39~)", "qt6-wayland-dev (>= 6.9.0~)"):
    require(token in control, f"KGuiAddons default Linux integration Build-Depends missing: {token}")
require("DEB_PYTHON_INSTALL_LAYOUT = deb" in rules, "KGuiAddons Python install layout must be Debian")
require("-DBUILD_PYTHON_BINDINGS=ON" in rules, "KGuiAddons Python bindings must remain enabled")
require("-DBUILD_TESTING=ON" in rules, "KGuiAddons tests must remain enabled")
require(not re.search(r"-D(?:WITH_WAYLAND|WITH_X11|USE_DBUS|BUILD_GEO_SCHEME_HANDLER)=OFF", rules), "KGuiAddons Linux upstream defaults must not be disabled")

shared = campaign.get("shared_predecessors", {})
require(shared.get("extra_cmake_modules", {}).get("state") == "PASS", "Batch 8 requires retained ECM PASS")
require(shared.get("extra_cmake_modules", {}).get("version") == "6.30.0-0supralinux3", "Batch 8 ECM predecessor mismatch")
kcore = shared.get("kcoreaddons_public_header_provider", {})
require(kcore.get("state") == "PASS", "Batch 8 requires retained KCoreAddons PASS for consumer development surface")
require(kcore.get("build_dependency") is False, "KCoreAddons predecessor role must explicitly not be a build dependency")
require(kcore.get("version") == "6.30.0-0supralinux4", "KCoreAddons retained version mismatch")
require(kcore.get("artifact_id") == 10457958023 and kcore.get("workflow_run") == 35122522242, "KCoreAddons retained evidence mismatch")

require("workflow_call:" in workflow and "workflow_dispatch:" in workflow, "Batch 8 workflow must be reusable and manually dispatchable")
require("\n  pull_request:\n" not in workflow, "Batch 8 workflow must not create an independent ordinary PR run")
require("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow, "Batch 8 workflow checkout must be immutable")
require("run-id: '34694951158'" in workflow and "artifact-ids: '10298635300'" in workflow, "Batch 8 workflow must download retained ECM evidence")
require("run-id: '34708030450'" in workflow and "artifact-ids: '10301938362'" in workflow, "Batch 8 workflow must download retained packaging tree")
require("run-id: '35122522242'" in workflow and "artifact-ids: '10457958023'" in workflow, "Batch 8 workflow must download retained KCoreAddons PASS")
require("scripts/kde-tier1-package-batch8-needed.sh" in workflow, "Batch 8 workflow must use exact event-delta scope")
require("scripts/run-kde-tier1-package-batch8-preflight.sh" in workflow, "Batch 8 workflow must execute the KGuiAddons runner")
require("uses: ./.github/workflows/kde-tier1-package-batch8.yml" in router, "central PR router must invoke Batch 8")

for token in ("KCOREADDONS_ARTIFACT_DIR", "kcoreaddons_build_dependency=no", "libkf6coreaddons-dev", "KImageCache", "python-import-smoke", "consumer-runtime-closure", "sbuild --verbose"):
    require(token in runner or token in text(CONSUMER / "main.cpp"), f"Batch 8 runner/consumer contract missing: {token}")
require("manifests/kde-tier1-package-campaign-batch8.json" in scope, "Batch 8 scope selector must fingerprint the campaign")
require("packages/kde/kguiaddons/" in scope, "Batch 8 scope selector must track package metadata")
require("Batch 8 scope selector: PASS" in scope_test, "Batch 8 scope functional test must emit PASS")
require("KGuiAddons" in doc and "KCoreAddons" in doc and "Tier 1" in doc, "Batch 8 documentation must explain KGuiAddons/KCoreAddons Tier 1 distinction")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 Batch 8 preparation validation: PASS")
print("Node: kguiaddons 6.30.0 / 6.30.0-0supralinux1")
print("KCoreAddons role: consumer development surface only; not Build-Depends")
print("Upstream defaults: Wayland/X11/DBus/geo/Python/tests ON")
print("Signing key SHA-256: manifest/materialized bytes match")

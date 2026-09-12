#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "kde-dag.json"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-ecm-package-preflight.yml"
RUNNER = ROOT / "scripts" / "run-kde-ecm-package-preflight.sh"
DELTA = ROOT / "scripts" / "kde-ecm-preflight-needed.sh"
DOC = ROOT / "docs" / "kde-dag.md"
CONTROL = ROOT / "packages" / "kde" / "extra-cmake-modules" / "debian" / "control"
CHANGELOG = ROOT / "packages" / "kde" / "extra-cmake-modules" / "debian" / "changelog"
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
UPLOAD_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
ECM_SHA256 = "22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e"
errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read(path: Path) -> str:
    if not path.exists():
        errors.append(f"required KDE DAG file missing: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


try:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: cannot read {MANIFEST.relative_to(ROOT)}: {exc}", file=sys.stderr)
    raise SystemExit(1)

require(data.get("schema") == 1, "KDE DAG manifest schema must be 1")
require(data.get("frameworks_series") == "6.30.0", "KDE DAG Frameworks series must be 6.30.0")
require(data.get("authority") == "kde-upstream", "KDE DAG authority must remain kde-upstream")
require(data.get("states") == ["PASS", "FAIL", "BLOCKED", "pending"], "KDE DAG states must preserve PASS/FAIL/BLOCKED/pending semantics")

nodes = data.get("nodes", {})
ecm = nodes.get("extra-cmake-modules", {})
require(ecm.get("tier") == "build-system-root", "ECM must be the build-system-root node")
require(ecm.get("upstream_version") == "6.30.0", "ECM upstream version must be 6.30.0")
require(ecm.get("source_authority") == "kde-upstream", "ECM source authority must be KDE upstream")
require(ecm.get("package_provider") == "supralinux", "ECM package provider must be SupraLINUX")
require(ecm.get("source_package") == "kf6-extra-cmake-modules", "ECM source package name must preserve Ubuntu/Debian-compatible source naming")
require(ecm.get("binary_packages") == ["extra-cmake-modules"], "ECM binary package name must preserve Debian contract")
require(ecm.get("package_version") == "6.30.0-0supralinux1", "ECM SupraLINUX package version is unexpected")
require(ecm.get("source_sha256") == ECM_SHA256, "ECM source SHA-256 must match KDE Frameworks 6.30.0 release metadata")
require(ecm.get("source_url") == "https://download.kde.org/stable/frameworks/6.30/extra-cmake-modules-6.30.0.tar.xz", "ECM source URL must use KDE stable release tarball")
require(ecm.get("source_evidence") == "https://kde.org/info/kde-frameworks-6.30.0/", "ECM source evidence must cite KDE release information")
require(ecm.get("depends_on") == [], "ECM root node must not depend on another KDE DAG node")
require(ecm.get("state") in {"pending", "PASS", "FAIL", "BLOCKED"}, "ECM DAG state is invalid")
if ecm.get("state") == "PASS":
    require(bool(ecm.get("evidence")), "PASS ECM node requires retained evidence")
if ecm.get("state") == "BLOCKED":
    errors.append("ECM root node cannot be BLOCKED because it has no KDE DAG dependencies")

workflow = read(WORKFLOW)
runner = read(RUNNER)
delta = read(DELTA)
doc = read(DOC)
control = read(CONTROL)
changelog = read(CHANGELOG)

require("runs-on: ubuntu-26.04" in workflow, "ECM workflow must use explicit ubuntu-26.04")
require("ubuntu-latest" not in workflow, "ECM workflow must not use ubuntu-latest")
require("pull_request_target" not in workflow, "ECM workflow must not use pull_request_target")
require(f"actions/checkout@{CHECKOUT_SHA}" in workflow, "ECM workflow must pin approved checkout SHA")
require(f"actions/upload-artifact@{UPLOAD_SHA}" in workflow, "ECM workflow must pin approved upload-artifact SHA")
require("fetch-depth: 0" in workflow, "ECM workflow must fetch history for event-delta scope")
require("scripts/kde-ecm-preflight-needed.sh" in workflow, "ECM workflow must use event-delta scope detection")
require("scripts/run-kde-ecm-package-preflight.sh" in workflow, "ECM workflow must execute clean package preflight")
require("evidence/kde-ecm-package-preflight/" in workflow, "ECM workflow must retain node evidence")

for token, message in (
    ("UPSTREAM_VERSION=\"6.30.0\"", "ECM runner must pin upstream version"),
    (ECM_SHA256, "ECM runner must pin KDE-published source SHA-256"),
    ("download.kde.org/stable/frameworks/6.30", "ECM runner must fetch from KDE stable release"),
    ("sha256sum --check --strict", "ECM runner must verify source SHA before extraction"),
    ("dpkg-buildpackage -S", "ECM runner must create a Debian source package"),
    ("--chroot-mode=unshare", "ECM runner must build in clean sbuild/unshare"),
    ("dpkg-deb -f", "ECM runner must verify binary package metadata"),
    ("find_package(ECM 6.30.0 REQUIRED NO_MODULE)", "ECM runner must configure a downstream consumer against built artifact"),
    ("downstream_eligible=yes", "ECM runner must explicitly mark PASS artifact downstream-eligible"),
):
    require(token in runner, message)

for tracked in (
    "packages/kde/extra-cmake-modules/*",
    "scripts/run-kde-ecm-package-preflight.sh",
    ".github/workflows/kde-ecm-package-preflight.yml",
    "manifests/kde-dag.json",
    "docs/kde-dag.md",
):
    require(tracked in delta, f"ECM delta detector must track {tracked}")

require("Source: kf6-extra-cmake-modules" in control, "ECM control must preserve source package name")
require(re.search(r"^Package: extra-cmake-modules$", control, re.MULTILINE) is not None, "ECM control must preserve binary package name")
require(re.search(r"^Architecture: all$", control, re.MULTILINE) is not None, "ECM package must be architecture all")
require(re.search(r"^Suggests: qt6-base-dev$", control, re.MULTILINE) is not None, "ECM package must preserve Qt development suggestion")
require(changelog.startswith("kf6-extra-cmake-modules (6.30.0-0supralinux1) resolute;"), "ECM changelog must match manifest package version")

require(ECM_SHA256 in doc, "KDE DAG docs must record ECM upstream SHA-256")
require("Ubuntu 26.04 currently carries `extra-cmake-modules` 6.24.0-0ubuntu1" in doc, "KDE DAG docs must distinguish Ubuntu reference version")
require("technical packaging reference only" in doc, "KDE DAG docs must keep Ubuntu as reference/provider rather than KDE authority")
require("`BLOCKED` is never counted as `FAIL`" in doc, "KDE DAG docs must preserve BLOCKED semantics")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE DAG policy validation: PASS")
print(f"Frameworks series: {data['frameworks_series']}")
print(f"ECM: version={ecm['upstream_version']} state={ecm['state']} provider={ecm['package_provider']}")
print(f"ECM source SHA-256: {ecm['source_sha256']}")

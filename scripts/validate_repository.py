#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "desktop-stack.json"
WORKFLOWS = ROOT / ".github" / "workflows"

errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


try:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: cannot read {MANIFEST.relative_to(ROOT)}: {exc}", file=sys.stderr)
    raise SystemExit(1)

require(data.get("schema") == 1, "manifest schema must be 1")

platform = data.get("platform", {})
require(platform.get("authority") == "ubuntu", "platform authority must be ubuntu")
require(platform.get("version") == "26.04 LTS", "platform version must be Ubuntu 26.04 LTS")
require(platform.get("series") == "resolute", "Ubuntu 26.04 series must be resolute")

desktop = data.get("desktop", {})
require(desktop.get("authority") == "kde-upstream", "desktop authority must be kde-upstream")
for component in ("plasma", "frameworks", "gear"):
    item = desktop.get(component, {})
    require(bool(item.get("version")), f"{component} version is required")
    require(str(item.get("evidence", "")).startswith("https://kde.org/"), f"{component} must cite KDE evidence")

qt = data.get("qt", {})
require(qt.get("requirement_authority") == "kde-upstream", "Qt requirement authority must be kde-upstream")
require(qt.get("source_authority") == "qt-project", "Qt source authority must be qt-project")
require(bool(qt.get("required_series")), "Qt required_series is required")

provider = qt.get("provider", {})
require(provider.get("name") in {"ubuntu", "supralinux"}, "Qt provider must be ubuntu or supralinux")
if provider.get("name") == "ubuntu":
    require(provider.get("series") == "resolute", "Ubuntu Qt provider must use resolute")

cert = qt.get("certification", {})
require(cert.get("status") in {"pending", "certified", "rejected"}, "Qt certification status is invalid")
if cert.get("status") == "certified":
    require(bool(cert.get("evidence")), "certified Qt requires evidence")

ci = data.get("ci", {})
hosted = ci.get("hosted_runner", {})
require(hosted.get("label") == "ubuntu-26.04", "hosted runner must be explicitly ubuntu-26.04")
require(hosted.get("role") == "non-authoritative-preflight", "hosted runner must be non-authoritative preflight")

authoritative = ci.get("authoritative_runner", {})
require(authoritative.get("platform") == "ubuntu-26.04", "authoritative runner platform must be ubuntu-26.04")
require(authoritative.get("virtualization") == "kvm", "authoritative runner virtualization must be kvm")
require(authoritative.get("lifecycle") == "ephemeral-vm", "authoritative runner must use ephemeral VMs")
require(authoritative.get("build_isolation") == "sbuild-unshare", "authoritative package build must use sbuild-unshare")
require(authoritative.get("system_test") == "autopkgtest-qemu", "authoritative package system test must use autopkgtest-qemu")
require(authoritative.get("nested_kvm_required") is True, "authoritative package testing requires nested KVM")

if WORKFLOWS.exists():
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        require("ubuntu-latest" not in text, f"{path.relative_to(ROOT)} must not use ubuntu-latest")

required_docs = [
    ROOT / "docs" / "architecture" / "overview.md",
    ROOT / "docs" / "architecture" / "build-ci.md",
    ROOT / "docs" / "status" / "2026-09-11.md",
    ROOT / "docs" / "decisions" / "ADR-0001-authority-provider.md",
    ROOT / "docs" / "runners" / "ubuntu-26.04.md",
]
for path in required_docs:
    require(path.exists(), f"required documentation missing: {path.relative_to(ROOT)}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Repository policy validation: PASS")
print(f"Platform: {platform['version']} ({platform['series']})")
print(
    "Desktop: Plasma {plasma}, Frameworks {frameworks}, Gear {gear}".format(
        plasma=desktop["plasma"]["version"],
        frameworks=desktop["frameworks"]["version"],
        gear=desktop["gear"]["version"],
    )
)
print(
    f"Qt: required {qt['required_series']}, provider={provider['name']}, "
    f"candidate={provider.get('candidate_version', 'n/a')}, certification={cert['status']}"
)
print(
    "CI: hosted={hosted}; authoritative={platform}/{virt}/{lifecycle}; build={build}; test={test}".format(
        hosted=hosted["role"],
        platform=authoritative["platform"],
        virt=authoritative["virtualization"],
        lifecycle=authoritative["lifecycle"],
        build=authoritative["build_isolation"],
        test=authoritative["system_test"],
    )
)

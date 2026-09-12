#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "desktop-stack.json"
WORKFLOW = ROOT / ".github" / "workflows" / "qt-provider-preflight.yml"
PREFLIGHT = ROOT / "scripts" / "run-qt-provider-preflight.sh"
DELTA = ROOT / "scripts" / "qt-provider-preflight-needed.sh"
DOC = ROOT / "docs" / "qt-provider-certification.md"
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
UPLOAD_SHA = "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read(path: Path) -> str:
    if not path.exists():
        errors.append(f"required Qt provider file missing: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


try:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: cannot read {MANIFEST.relative_to(ROOT)}: {exc}", file=sys.stderr)
    raise SystemExit(1)

qt = data.get("qt", {})
provider = qt.get("provider", {})
preflight = qt.get("provider_preflight", {})
certification = qt.get("certification", {})
required_series = str(qt.get("required_series", ""))

require(qt.get("requirement_authority") == "kde-upstream", "Qt requirement authority must remain kde-upstream")
require(qt.get("source_authority") == "qt-project", "Qt source authority must remain qt-project")
require(required_series == "6.10", "current KDE-selected Qt series must be 6.10")
require(provider.get("name") == "ubuntu", "current Qt reuse candidate provider must be ubuntu")
require(provider.get("series") == "resolute", "Ubuntu Qt provider must use resolute")
require(provider.get("status") == "reuse-candidate", "provider must remain reuse-candidate until final certification")
require(preflight.get("scope") == "plasma-frameworks-baseline", "Qt provider preflight scope must be plasma-frameworks-baseline")
require(preflight.get("status") in {"pending", "pass", "fail"}, "Qt provider preflight status is invalid")
require(certification.get("status") in {"pending", "certified", "rejected"}, "Qt final certification status is invalid")

resolved = str(preflight.get("resolved_upstream_version", ""))
if preflight.get("status") == "pass":
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", resolved)), "PASS Qt provider preflight requires a semantic resolved_upstream_version")
    require(resolved.startswith(required_series + "."), "resolved Qt provider version must satisfy the KDE-required series")
    evidence = preflight.get("evidence", [])
    require(isinstance(evidence, list) and len(evidence) >= 1, "PASS Qt provider preflight requires retained evidence")
    if isinstance(evidence, list) and evidence:
        item = evidence[0] if isinstance(evidence[0], dict) else {}
        require(item.get("type") == "github-actions-run", "Qt provider preflight evidence must identify a GitHub Actions run")
        require(isinstance(item.get("run_id"), int) and item.get("run_id", 0) > 0, "Qt provider preflight evidence requires a positive run_id")
        require(bool(re.fullmatch(r"[0-9a-f]{40}", str(item.get("commit", "")))), "Qt provider preflight evidence requires a full commit SHA")
        require(isinstance(item.get("artifact_id"), int) and item.get("artifact_id", 0) > 0, "Qt provider preflight evidence requires a positive artifact_id")
        require(bool(re.fullmatch(r"[0-9a-f]{64}", str(item.get("artifact_sha256", "")))), "Qt provider preflight evidence requires an artifact SHA-256")

if certification.get("status") == "certified":
    require(preflight.get("status") == "pass", "Qt cannot be finally certified without provider preflight PASS")
    require(bool(certification.get("evidence")), "final Qt certification requires separate evidence")

workflow = read(WORKFLOW)
script = read(PREFLIGHT)
delta = read(DELTA)
doc = read(DOC)
doc_lower = doc.lower()

require("ubuntu-latest" not in workflow, "Qt provider workflow must not use ubuntu-latest")
require("pull_request_target" not in workflow, "Qt provider workflow must not use pull_request_target")
require("runs-on: ubuntu-26.04" in workflow, "Qt provider workflow must run on explicit ubuntu-26.04")
require(f"actions/checkout@{CHECKOUT_SHA}" in workflow, "Qt provider workflow must pin the approved checkout action SHA")
require(f"actions/upload-artifact@{UPLOAD_SHA}" in workflow, "Qt provider workflow must pin the approved upload-artifact SHA")
require("types: [opened, synchronize, reopened]" in workflow, "Qt provider workflow must use explicit PR lifecycle events")
require("fetch-depth: 0" in workflow, "Qt provider workflow must fetch comparison history")
require("scripts/qt-provider-preflight-needed.sh" in workflow, "Qt provider workflow must use event-delta scope detection")
require("scripts/run-qt-provider-preflight.sh" in workflow, "Qt provider workflow must execute the provider preflight script")
require("evidence/qt-provider-preflight/" in workflow, "Qt provider workflow must upload provider evidence")

baseline_packages = (
    "qt6-base-dev",
    "qt6-base-private-dev",
    "qt6-declarative-dev",
    "qt6-declarative-private-dev",
    "qt6-svg-dev",
    "qt6-wayland-dev",
    "qt6-wayland-private-dev",
    "qt6-shadertools-dev",
    "qt6-tools-dev",
    "qt6-tools-dev-tools",
    "qt6-5compat-dev",
)
for package in baseline_packages:
    require(package in workflow, f"Qt provider workflow must install baseline package {package}")
    require(package in script, f"Qt provider script must validate baseline package {package}")

for token, message in (
    ('"${installed}" != "${candidate}"', "Qt provider preflight must require installed Debian versions to match APT candidates"),
    ("Mixed Qt upstream patch releases are not accepted", "Qt provider preflight must reject mixed upstream patch versions"),
    ("qtpaths6 --qt-version", "Qt provider preflight must validate the effective Qt runtime version"),
    ("ubuntu-qt-provider-preflight-only", "Qt provider result must explicitly limit its claim to preflight"),
    ("claim=preflight-only", "Qt provider environment evidence must explicitly limit its claim"),
    ("Qt6::GuiPrivate", "Qt provider preflight must require Qt Gui private target"),
    ("Qt6::QmlPrivate", "Qt provider preflight must require Qt QML private target"),
    ("Qt6::QuickPrivate", "Qt provider preflight must require Qt Quick private target"),
    ("Qt6::WaylandClientPrivate", "Qt provider preflight must require Qt WaylandClient private target"),
    ("QTextCodec", "Qt provider runtime probe must exercise Qt5Compat"),
    ("QQmlEngine", "Qt provider runtime probe must exercise QML"),
    ("QSvgRenderer", "Qt provider runtime probe must exercise SVG"),
    ("qt_runtime_version=", "Qt provider runtime probe must record the effective Qt runtime version"),
):
    require(token in script, message)

for tracked in (
    "manifests/desktop-stack.json",
    "scripts/run-qt-provider-preflight.sh",
    "scripts/qt-provider-preflight-needed.sh",
    ".github/workflows/qt-provider-preflight.yml",
    "docs/qt-provider-certification.md",
):
    require(tracked in delta, f"Qt provider event-delta detector must track {tracked}")

require("provider preflight" in doc_lower, "Qt provider documentation must describe the provider preflight boundary")
require("final certification" in doc_lower, "Qt provider documentation must distinguish final certification")
require("34665704108" in doc, "Qt provider documentation must record the first real PASS run")
require("10288816586" in doc, "Qt provider documentation must record the first evidence artifact")
require("90a25a24b60dcc02691c7043eb3a985f21013c73e3ea4489a7427fa74e618e33" in doc, "Qt provider documentation must record the first artifact digest")

if preflight.get("status") == "pass":
    require("provider preflight **pass**" in doc_lower or "provider preflight: **pass**" in doc_lower, "documentation must reflect provider preflight PASS")
if certification.get("status") == "pending":
    require("final certification **pending**" in doc_lower or "final certification: **pending**" in doc_lower, "documentation must reflect final Qt certification pending")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Qt provider policy validation: PASS")
print(f"Qt required series: {required_series}")
print(f"Provider: {provider['name']}/{provider['series']} status={provider['status']}")
print(f"Provider preflight: {preflight['status']} resolved={resolved or 'n/a'}")
print(f"Final certification: {certification['status']}")

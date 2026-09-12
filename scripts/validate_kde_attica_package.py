#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packages" / "kde" / "attica" / "debian"
TIER1 = ROOT / "manifests" / "kde-frameworks-tier1.json"
DAG = ROOT / "manifests" / "kde-dag.json"
RUNNER = ROOT / "scripts" / "run-kde-attica-package-preflight.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-attica-package-preflight.yml"
DOC = ROOT / "docs" / "kde-attica-packaging.md"
STATUS_DOC = ROOT / "docs" / "status" / "2026-09-12.md"

PASS_RUN = 34706416753
PASS_COMMIT = "9945bfa92d776d432c76e17516b0ff9452b6d159"
PASS_ARTIFACT = 10301851297
PASS_DIGEST = "f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27"
FAIL_RUN = 34705165994
FAIL_ARTIFACT = 10300903114
FAIL_DIGEST = "171cfe8553aba2af8f42a640ee5f50f82988005edbd104b737d93b639dc38300"
VERSION = "6.30.0-0supralinux2"
SOURCE_SHA = "3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c"
ECM_VERSION = "6.30.0-0supralinux3"
SYMBOLS_SHA = "e67d131171c8e3ea79c6bbbb2434aa2492580d19ba7dccdaa7038766cd9827ad"
EXPECTED_FILES = {
    "libkf6attica-dev_deb_sha256":"884e917a29b9618000621029d0dd42c00d4f2e1c925aa03cbf905978b82f0a4b",
    "libkf6attica-doc_deb_sha256":"30bb8e97a2a087809a1ca6d017f6beb8dcee5933d416d958c555033020d77a83",
    "libkf6attica6_deb_sha256":"5f52b2ce38c6dc1ad884d16e9d616c781b098a0445a68485d24087c4572d86de",
    "changes_sha256":"859b76c5cd99a7c949071098e44ae43943e8619a7174c120cfe2a1cf4ebc428e",
    "buildinfo_sha256":"5e10c1f72d07f6f61beff17e3ed3f0cf0254016d23d8c2bd0d1dec9c983bd5f4",
    "dsc_sha256":"25a0a2993787329d3ceae7a6485c9134605a3a188aed492bbc073ec5d5edbc72",
    "debian_tar_sha256":"0fcfabd68df435228170d657754641259c92d75147e00925c5d4766eeb105aa0",
    "orig_tar_sha256":SOURCE_SHA,
    "rootfs_sha256":"37cef66de0b97f406f0fb59be51d7cbb221b68936db998b5e5a91804cbe97763",
}

errors: list[str] = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""

def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot load {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(value, dict):
        print(f"ERROR: {path.relative_to(ROOT)} must contain an object", file=sys.stderr)
        raise SystemExit(1)
    return value

required_files = [
    "changelog", "control", "copyright", "README.source", "rules", "watch", "source/format",
    "patches/series", "patches/Disable-network-dependant-test.patch", "libkf6attica6.install",
    "libkf6attica-dev.install", "libkf6attica-doc.install", "libkf6attica6.symbols.reference",
]
for relative in required_files:
    require((PKG / relative).is_file(), f"Attica packaging file missing: debian/{relative}")

control = read(PKG / "control")
rules = read(PKG / "rules")
changelog = read(PKG / "changelog")
patch = read(PKG / "patches" / "Disable-network-dependant-test.patch")
symbols_ref = read(PKG / "libkf6attica6.symbols.reference")
readme = read(PKG / "README.source")
runner = read(RUNNER)
workflow = read(WORKFLOW)
doc = read(DOC)
status_doc = read(STATUS_DOC)

require(control.startswith("Source: kf6-attica\n"), "Attica source package name must remain kf6-attica")
require("Maintainer: SupraLINUX Project <packages@supralinux.invalid>" in control, "Attica maintainer identity changed")
for dependency in (
    "debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29)",
    "extra-cmake-modules (>= 6.30.0~)", "python3", "qt6-base-dev (>= 6.9.0~)", "reuse",
):
    require(dependency in control, f"Attica Build-Depends must include {dependency}")
for forbidden in ("extra-cmake-modules (>= 6.24", "qt6-base-dev (>= 6.8", "BUILD_QCH"):
    require(forbidden not in control + rules, f"Attica packaging retains stale reference input: {forbidden}")
for package in ("libkf6attica6", "libkf6attica-dev", "libkf6attica-doc"):
    require(f"Package: {package}" in control, f"Attica binary package missing: {package}")
require("Multi-Arch: same" in control and "Multi-Arch: foreign" in control, "Attica Multi-Arch contracts changed")
require("libkf6attica6 (= ${binary:Version})" in control, "Attica dev package must pin exact runtime")
require("libkf6attica-doc (= ${source:Version})" in control, "Attica dev package must recommend exact docs")
require("-DBUILD_TESTING=ON" in rules and "-DSKIP_LICENSE_TESTS=OFF" in rules, "Attica tests/license checks must remain enabled")
require("DEB_BUILD_MAINT_OPTIONS = hardening=+all" in rules, "Attica hardening must remain enabled")
require(changelog.startswith(f"kf6-attica ({VERSION}) resolute;"), "Attica changelog validated revision mismatch")
require("6.30.0-0supralinux1" in changelog, "Attica changelog must retain first failed revision")
require("dpkg-source -b" in runner and "dpkg-buildpackage -S" not in runner, "Attica source assembly boundary regressed")
require('DEBIAN_VERSION="${UPSTREAM_VERSION}-0supralinux2"' in runner, "Attica runner revision mismatch")
require("providertest.cpp" in patch and "# providertest.cpp" in patch, "Attica must disable only live-network provider test")
require("autoconfig.kde.org" in readme, "Attica README.source must document network test")
require(SYMBOLS_SHA in symbols_ref and "10301617541" in symbols_ref, "Attica symbols baseline reference mismatch")
require(read(PKG / "source" / "format").strip() == "3.0 (quilt)", "Attica source format changed")
require(read(PKG / "patches" / "series").strip() == "Disable-network-dependant-test.patch", "Attica patch series changed")
require("runs-on: ubuntu-26.04" in workflow, "Attica workflow must use Ubuntu 26.04")
for value in ("34694951158", "10298635300", "34704689773", "10301617541"):
    require(value in workflow, f"Attica workflow must retain pinned predecessor/reference input {value}")
require("scripts/run-kde-attica-package-preflight.sh" in workflow, "Attica workflow package runner missing")

manifest = load(TIER1)
attica = next((node for node in manifest.get("nodes", []) if isinstance(node, dict) and node.get("id") == "attica"), None)
require(isinstance(attica, dict), "Tier 1 manifest must contain attica")
if isinstance(attica, dict):
    require(attica.get("upstream_version") == "6.30.0" and attica.get("source_sha256") == SOURCE_SHA, "Attica upstream pin changed")
    require(attica.get("depends_on") == ["extra-cmake-modules"], "Attica ECM predecessor changed")
    packaging = attica.get("packaging", {})
    require(packaging.get("state") == "PASS" and attica.get("state") == "PASS", "Attica current state must be PASS")
    require(packaging.get("package_version") == VERSION, "Attica PASS package version mismatch")
    require(packaging.get("claim") == "hosted-clean-package-preflight" and packaging.get("authoritative") is False, "Attica hosted PASS semantics changed")
    require(packaging.get("downstream_eligible") is True, "Attica PASS must be downstream eligible")
    evidence = packaging.get("evidence", [])
    failures = [x for x in evidence if isinstance(x, dict) and x.get("result") == "FAIL"]
    passes = [x for x in evidence if isinstance(x, dict) and x.get("result") == "PASS"]
    require(len(failures) == 1 and len(passes) == 1, "Attica must retain exactly one FAIL and one PASS attempt")
    if failures:
        item = failures[0]
        require(item.get("workflow_run") == FAIL_RUN and item.get("artifact_id") == FAIL_ARTIFACT and item.get("artifact_sha256") == FAIL_DIGEST, "Attica historical FAIL evidence mismatch")
        require(item.get("failure_stage") == "source-package", "Attica historical FAIL stage mismatch")
    if passes:
        item = passes[0]
        require(item.get("workflow_run") == PASS_RUN and item.get("commit") == PASS_COMMIT, "Attica PASS run/commit mismatch")
        require(item.get("artifact_id") == PASS_ARTIFACT and item.get("artifact_sha256") == PASS_DIGEST, "Attica PASS artifact mismatch")
        require(item.get("attempted_package_version") == VERSION and item.get("stage") == "complete", "Attica PASS version/stage mismatch")
        require(item.get("tests") == "6/6 PASS" and item.get("lintian") == "PASS-errors" and item.get("consumer_smoke") == "PASS", "Attica PASS gates incomplete")
        require(item.get("abi_soname") == "libKF6Attica.so.6" and item.get("ecm_predecessor") == ECM_VERSION, "Attica ABI/ECM evidence mismatch")
        require(item.get("files") == EXPECTED_FILES, "Attica PASS hashes changed without review")

dag = load(DAG)
dag_attica = dag.get("nodes", {}).get("attica", {})
require(dag_attica.get("state") == "PASS", "Global KDE DAG must record Attica PASS")
require(dag_attica.get("package_version") == VERSION and dag_attica.get("depends_on") == ["extra-cmake-modules"], "Global KDE DAG Attica identity/predecessor mismatch")
require(dag_attica.get("downstream_eligible") is True and dag_attica.get("authoritative") is False, "Global KDE DAG Attica hosted PASS semantics mismatch")

for value in (str(FAIL_RUN), str(FAIL_ARTIFACT), FAIL_DIGEST, str(PASS_RUN), str(PASS_ARTIFACT), PASS_DIGEST, VERSION):
    require(value in doc, f"Attica documentation missing evidence {value}")
    require(value in status_doc, f"Status documentation missing evidence {value}")
require("6/6" in doc and "libKF6Attica.so.6" in doc and "downstream" in doc.lower(), "Attica docs must record tests, SONAME and downstream eligibility")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Attica 6.30 package validation: PASS")
print(f"Package version: {VERSION}")
print(f"Hosted package run: {PASS_RUN}; artifact: {PASS_ARTIFACT}")
print("Tests 6/6 PASS; Lintian errors PASS; consumer smoke PASS; SONAME PASS")
print("DAG: attica PASS/downstream-eligible; authoritative release certification pending")

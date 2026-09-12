#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packages" / "kde" / "attica" / "debian"
TIER1 = ROOT / "manifests" / "kde-frameworks-tier1.json"
RUNNER = ROOT / "scripts" / "run-kde-attica-package-preflight.sh"

errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""


required_files = [
    "changelog",
    "control",
    "copyright",
    "README.source",
    "rules",
    "watch",
    "source/format",
    "patches/series",
    "patches/Disable-network-dependant-test.patch",
    "libkf6attica6.install",
    "libkf6attica-dev.install",
    "libkf6attica-doc.install",
    "libkf6attica6.symbols.reference",
]
for relative in required_files:
    require((PKG / relative).is_file(), f"Attica packaging file missing: debian/{relative}")

control = text(PKG / "control")
rules = text(PKG / "rules")
changelog = text(PKG / "changelog")
patch = text(PKG / "patches" / "Disable-network-dependant-test.patch")
symbols_ref = text(PKG / "libkf6attica6.symbols.reference")
readme = text(PKG / "README.source")
runner = text(RUNNER)

require(control.startswith("Source: kf6-attica\n"), "Attica source package name must remain kf6-attica")
require("Maintainer: SupraLINUX Project <packages@supralinux.invalid>" in control, "Attica maintainer must use the SupraLINUX packaging identity")
for dependency in (
    "debhelper-compat (= 13)",
    "dh-sequence-kf6",
    "dh-sequence-pkgkde-symbolshelper",
    "cmake (>= 3.29)",
    "extra-cmake-modules (>= 6.30.0~)",
    "python3",
    "qt6-base-dev (>= 6.9.0~)",
    "reuse",
):
    require(dependency in control, f"Attica Build-Depends must include {dependency}")

for forbidden in ("extra-cmake-modules (>= 6.24", "qt6-base-dev (>= 6.8", "BUILD_QCH"):
    require(forbidden not in control + rules, f"Attica packaging must not retain stale reference input: {forbidden}")

require("Package: libkf6attica6" in control, "Attica runtime binary package missing")
require("Package: libkf6attica-dev" in control, "Attica development binary package missing")
require("Package: libkf6attica-doc" in control, "Attica documentation compatibility package missing")
require("Multi-Arch: same" in control, "Attica runtime Multi-Arch contract must remain same")
require("Multi-Arch: foreign" in control, "Attica documentation Multi-Arch contract must remain foreign")
require("libkf6attica6 (= ${binary:Version})" in control, "Attica dev package must pin the exact runtime version")
require("libkf6attica-doc (= ${source:Version})" in control, "Attica dev package must recommend the exact doc version")

require("-DBUILD_TESTING=ON" in rules, "Attica package profile must keep upstream tests enabled")
require("-DSKIP_LICENSE_TESTS=OFF" in rules, "Attica package profile must keep outbound license tests enabled")
require("DEB_BUILD_MAINT_OPTIONS = hardening=+all" in rules, "Attica package must retain Debian hardening")

require(changelog.startswith("kf6-attica (6.30.0-0supralinux2) resolute;"), "Attica changelog must use remediation revision 6.30.0-0supralinux2")
require("6.30.0-0supralinux1" in changelog, "Attica changelog must retain first attempted revision")
require("dpkg-source -b" in runner, "Attica runner must assemble the source package with dpkg-source -b")
require("dpkg-buildpackage -S" not in runner, "Attica runner must not execute debian/rules on the host while assembling source")
require('DEBIAN_VERSION="${UPSTREAM_VERSION}-0supralinux2"' in runner, "Attica runner must use remediation revision 6.30.0-0supralinux2")
require("providertest.cpp" in patch and "# providertest.cpp" in patch, "Attica package must disable only the live-network provider test")
require("https://autoconfig.kde.org" in readme or "autoconfig.kde.org" in readme, "Attica README.source must document why the network test is disabled")

expected_symbols_hash = "e67d131171c8e3ea79c6bbbb2434aa2492580d19ba7dccdaa7038766cd9827ad"
require(expected_symbols_hash in symbols_ref, "Attica symbols reference must pin the retained Ubuntu baseline hash")
require("10301617541" in symbols_ref, "Attica symbols reference must identify the retained packaging artifact")

require(text(PKG / "source" / "format").strip() == "3.0 (quilt)", "Attica source format must remain 3.0 (quilt)")
require(text(PKG / "patches" / "series").strip() == "Disable-network-dependant-test.patch", "Attica patch series changed unexpectedly")
require("Version: 5" in text(PKG / "watch"), "Attica watch file must use uscan format version 5")

try:
    tier1 = json.loads(TIER1.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: cannot load {TIER1.relative_to(ROOT)}: {exc}", file=sys.stderr)
    raise SystemExit(1)

attica = next((node for node in tier1.get("nodes", []) if isinstance(node, dict) and node.get("id") == "attica"), None)
require(isinstance(attica, dict), "Tier 1 manifest must contain attica")
if isinstance(attica, dict):
    require(attica.get("upstream_version") == "6.30.0", "Attica selected upstream version must remain 6.30.0")
    require(attica.get("source_sha256") == "3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c", "Attica upstream source hash changed unexpectedly")
    require(attica.get("depends_on") == ["extra-cmake-modules"], "Attica must depend only on ECM at this Tier")
    require(attica.get("packaging") == {"state": "pending"}, "Attica packaging manifest stays pending until remediation run result is recorded")
    require(attica.get("state") == "pending", "Attica DAG manifest stays pending until remediation run result is recorded")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Attica 6.30 packaging remediation validation: PASS")
print("Package version: 6.30.0-0supralinux2")
print("Qt floor: 6.9.0; ECM predecessor: 6.30.0")
print("Source assembly: dpkg-source -b; build helpers resolved in clean sbuild")
print("Manifest state remains pending until remediation run result is recorded")

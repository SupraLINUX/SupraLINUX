#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests/kde-tier1-package-campaign-batch4.json"
TIER1 = ROOT / "manifests/kde-frameworks-tier1.json"
DEPENDENCIES = ROOT / "manifests/kde-frameworks-tier1-dependencies.json"
DAG = ROOT / "manifests/kde-dag.json"
DOC = ROOT / "docs/kde-tier1-package-batch4.md"
DEPENDENCY_DOC = ROOT / "docs/kde-tier1-dependencies.md"
WORKFLOW = ROOT / ".github/workflows/kde-tier1-package-batch4.yml"
REPOSITORY_POLICY = ROOT / ".github/workflows/repository-policy.yml"
RUNNER = ROOT / "scripts/run-kde-tier1-package-batch4-preflight.sh"
SCOPE = ROOT / "scripts/kde-tier1-package-batch4-needed.sh"

EXPECTED = {
    "kitemviews": {
        "source": "9452f2b0cc5dd0214b88c4ce33297866be89af4177af14f5390cfb616e49c153",
        "blob": "d4abc8277881fff0ad85d06167b0f1e5c8e0977d",
        "symbols": "c95ecbc24ccee885f1aa50df1c2aab41f54eb561baf66b1b219a562a5ce372cf",
        "copyright": "add1ae526e4064439b04a0d2fa162e178f049c96411fe3922a9562a2f25304c6",
        "runtime": "libkf6itemviews6",
        "soname": "libKF6ItemViews.so.6",
        "cmake": "KF6ItemViews",
        "target": "KF6::ItemViews",
        "build": ["qt6-base-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)", "xauth <!nocheck>", "xvfb <!nocheck>"],
        "packages": 4,
    },
    "kglobalaccel": {
        "source": "e532ebd4cbfc8d6d79c6c38c556f1871315fedae8db2b69b574b9c496f171473",
        "blob": "274623176b4c0f9b72edea3bd770530f76c8f607",
        "symbols": "967876c92b88b1a0654b06084c70604191464ecaded59df4bbf4dea71c0c6bb7",
        "copyright": "1991e59510c1a15e9f0eba6479a249ec17579ad2f97d3686e0ed975f8614de34",
        "runtime": "libkf6globalaccel6",
        "soname": "libKF6GlobalAccel.so.6",
        "cmake": "KF6GlobalAccel",
        "target": "KF6::GlobalAccel",
        "build": ["qt6-base-dev (>= 6.9.0~)", "qt6-base-private-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)", "xauth <!nocheck>", "xvfb <!nocheck>"],
        "packages": 4,
    },
    "syntax-highlighting": {
        "source": "fc429b093058bec4878306cbbfb3aa0560ff4a3f166c69504036c507fe72afcc",
        "blob": "cbd31a8f3c8b981931fc0d39ee5991f5c7f6903a",
        "symbols": "3dd1d9e56a8fa8b802ffb6708ec65984cef422bcbe7660583c907a827aec47dd",
        "copyright": "96abcf79db76923a43e841f4a22c41a2e81394a0ff074ce1f06009e962ba2d35",
        "runtime": "libkf6syntaxhighlighting6",
        "soname": "libKF6SyntaxHighlighting.so.6",
        "cmake": "KF6SyntaxHighlighting",
        "target": "KF6::SyntaxHighlighting",
        "build": ["dh-sequence-qmldeps", "libxerces-c-dev", "perl:any", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)", "xauth <!nocheck>", "xvfb <!nocheck>"],
        "packages": 6,
    },
}

errors: list[str] = []

def req(value: bool, message: str) -> None:
    if not value:
        errors.append(message)

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

campaign = load(CAMPAIGN)
tier1 = {item["id"]: item for item in load(TIER1)["nodes"]}
deps = load(DEPENDENCIES)
dag = load(DAG)["nodes"]

req(campaign.get("schema") == 1, "campaign schema")
req(campaign.get("authority") == "kde-upstream", "KDE authority")
req(campaign.get("frameworks_series") == "6.30.0", "Frameworks version")
req(campaign.get("batch") == "tier1-batch-4", "batch id")
req(campaign.get("state") == "prepared-pending-build", "Batch 4 preparation state")
req(campaign.get("selected_nodes") == list(EXPECTED), "selected nodes/order")
req(campaign["shared_predecessors"]["extra_cmake_modules"]["version"] == "6.30.0-0supralinux3", "ECM predecessor")
req(campaign["shared_predecessors"]["packaging_trees"]["artifact_id"] == 10301938362, "packaging tree artifact")
req(campaign["shared_packaging_inputs"]["documentation_policy"]["qch_enabled"] is False, "QCH policy")
req(campaign["shared_packaging_inputs"]["lintian_policy"]["source_and_changes_required"] is True, "Lintian source+changes policy")
req(campaign["selection_rationale"]["deferred"].get("kconfig", "").startswith("Deferred because KConfig exports multiple ABI"), "KConfig deferral rationale")

for node, expected in EXPECTED.items():
    data = campaign["nodes"][node]
    req(data["state"] == "prepared-pending-build", f"{node}: campaign state")
    req(data["last_result"] is None, f"{node}: no fabricated result")
    req(data["downstream_eligible"] is False, f"{node}: must not be downstream eligible before build")
    req(data["package_version"] == "6.30.0-0supralinux1", f"{node}: initial package revision")
    req(data["source_sha256"] == expected["source"], f"{node}: source hash")
    req(data["root_cmake_blob"] == expected["blob"], f"{node}: root CMake blob")
    req(data["symbols"]["sha256"] == expected["symbols"], f"{node}: symbols baseline")
    req(data["symbols"]["tree_provider"] == "debian", f"{node}: symbols provider")
    req(data["copyright"]["sha256"] == expected["copyright"], f"{node}: copyright reference")
    req(data["runtime_package"] == expected["runtime"], f"{node}: runtime package")
    req(data["soname"] == expected["soname"], f"{node}: SONAME")
    req(data["cmake_package"] == expected["cmake"], f"{node}: CMake package")
    req(data["cmake_target"] == expected["target"], f"{node}: CMake target")
    req(len(data["binary_contracts"]) == expected["packages"], f"{node}: binary package count")
    req(data["evidence"] == [], f"{node}: no evidence before attempt")

    metadata = deps["metadata"][node]
    req(metadata["ref"] == "v6.30.0", f"{node}: dependency manifest ref")
    req(metadata["root_cmake_blob"] == expected["blob"], f"{node}: dependency manifest blob")
    if node == "kglobalaccel":
        req(set(deps["nodes"][node]["qt"].get("test", [])) == {"Test", "Qml"}, "kglobalaccel: dependency manifest must record QtQml test requirement")
    req(tier1[node]["state"] == "pending", f"{node}: canonical state must remain pending")
    req(tier1[node]["packaging"]["state"] == "pending", f"{node}: canonical packaging must remain pending")
    req(dag[node]["state"] == "pending", f"{node}: DAG state must remain pending")

    deb = ROOT / "packages/kde" / node / "debian"
    control = (deb / "control").read_text(encoding="utf-8")
    rules = (deb / "rules").read_text(encoding="utf-8")
    readme = (deb / "README.source").read_text(encoding="utf-8")
    docinstall = (deb / f"{data['documentation_package']}.install").read_text(encoding="utf-8")
    consumer = (ROOT / "packages/kde" / node / "consumer/CMakeLists.txt").read_text(encoding="utf-8")
    main = (ROOT / "packages/kde" / node / "consumer/main.cpp").read_text(encoding="utf-8")

    for token in ["debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)", *expected["build"]]:
        req(token in control, f"{node}: missing Build-Depends {token}")
    req("Standards-Version: 4.7.3" in control, f"{node}: Standards-Version")
    req("documentation compatibility package" in control, f"{node}: documentation description")
    req("does not ship QCH documentation files" in control, f"{node}: QCH truth")
    req("Intentionally empty" in docinstall, f"{node}: empty documentation install")
    req("-DBUILD_QCH=OFF" in rules, f"{node}: QCH disabled")
    req("dh_auto_test" in rules, f"{node}: tests enabled")
    req("KDE Frameworks 6.30.0 is the source/build authority" in readme, f"{node}: authority documentation")
    req(sha(deb / "upstream/signing-key.asc") == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", f"{node}: signing key")
    req(expected["cmake"] in consumer and expected["target"] in consumer, f"{node}: CMake consumer")
    req(expected["soname"] in main and "dlopen" in main, f"{node}: runtime consumer")

req("-DBUILD_DESIGNERPLUGIN=ON" in (ROOT / "packages/kde/kitemviews/debian/rules").read_text(), "kitemviews: Designer plugin default must be retained")
kg_control = (ROOT / "packages/kde/kglobalaccel/debian/control").read_text()
req("qt6-base-private-dev (>= 6.9.0~)" in kg_control, "kglobalaccel: Qt 6.10 GuiPrivate requirement")
req("qt6-declarative-dev (>= 6.9.0~)" in kg_control, "kglobalaccel: upstream test QtQml requirement")
syntax_control = (ROOT / "packages/kde/syntax-highlighting/debian/control").read_text()
req("perl:any" in syntax_control, "syntax-highlighting: Perl required")
req("libxerces-c-dev" in syntax_control, "syntax-highlighting: selected compile-time XML validation")
for unwanted in ("libxkbcommon-dev", "pkgconf"):
    req(unwanted not in kg_control, f"kglobalaccel: inherited reference dependency not justified by upstream: {unwanted}")
req("libxkbcommon-dev" not in (ROOT / "packages/kde/kitemviews/debian/control").read_text(), "kitemviews: inherited libxkbcommon-dev must not be treated as authority")
req("libxkbcommon-dev" not in syntax_control, "syntax-highlighting: inherited libxkbcommon-dev must not be treated as authority")

runner = RUNNER.read_text(encoding="utf-8")
workflow = WORKFLOW.read_text(encoding="utf-8")
scope = SCOPE.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")
depdoc = DEPENDENCY_DOC.read_text(encoding="utf-8")
policy = REPOSITORY_POLICY.read_text(encoding="utf-8")
for token in ["-name '*.ddeb'", 'lintian --fail-on error "${DSC}" "${CHANGES[0]}"', "Lintian:[[:space:]]+fail", "dpkg-source -b", "--chroot-mode=unshare", "dependency_contracts", "recommendation_contracts", "consumer-smoke"]:
    req(token in runner, f"runner missing {token}")
for token in ["fail-fast: false", "max-parallel: 3", "kitemviews", "kglobalaccel", "syntax-highlighting", "run-kde-tier1-package-batch4-preflight.sh"]:
    req(token in workflow, f"workflow missing {token}")
req("kde-tier1-package-campaign-batch4.json" in scope, "scope campaign")
req("validate_kde_tier1_package_batch4.py" in policy, "Repository Policy Batch 4 validator step")
for token in ["KItemViews", "KGlobalAccel", "KSyntaxHighlighting", "10 PASS / 19 pending / 0 current FAIL / 0 BLOCKED", "prepared", "KConfig"]:
    req(token.lower() in doc.lower(), f"Batch 4 documentation missing {token}")
req("10 PASS / 19 pending" in depdoc, "dependency documentation current canonical count")
req("28 package nodes pending" not in depdoc and "28 pending" not in depdoc, "dependency documentation retains stale 28-pending claim")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 Batch 4 preparation validation: PASS")
print("KItemViews, KGlobalAccel and KSyntaxHighlighting are prepared but remain pending until real package attempts pass.")

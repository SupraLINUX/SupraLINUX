#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1.json"
EXPECTED = {
    "attica": "3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c",
    "bluez-qt": "f5045b14a6c689bbfded9437582f943dd4f8f74537085ab6115bcacdea2110d8",
    "karchive": "4cf89d91e429d2ece3110e78f7ef7011952b0412cb15011329516b46f21e98e2",
    "kcalendarcore": "e8bf60e398e2f8098a4db7db44c5475d70540ad8f8948a123c8bc109dc4db776",
    "kcodecs": "a42c79ff3237b73789d1c63cdfd848c0d59671ce5e93723a2efa128f00cb3450",
    "kconfig": "0e98bac324cd716849202d4b246a948e363d6792a8eb09c78417cdde9559f56e",
    "kcoreaddons": "cc68fe15beb0fca2036cff8742f468c1345406bf99793fffacbf8f2a3f89bc4b",
    "kdbusaddons": "063ef80460f76d86dc4b033ef04b65b69ba82ee0de410440fe609465e7f5a997",
    "kglobalaccel": "e532ebd4cbfc8d6d79c6c38c556f1871315fedae8db2b69b574b9c496f171473",
    "kguiaddons": "e98864228d1c5e23f3428025eb9928697374fdc3eddebb3a9dec570de028a62d",
    "kholidays": "02bfbc33296fe86b364491f6d5cad9d83360bb4fdd2923386a325b309eac0b9b",
    "ki18n": "dfbfc8af89b3bc68810b094bf87746db87c3eeb35b75caeb1882681ebed563bd",
    "kidletime": "22873204292ddb757e5a0a57004c57debe1285cd0fd4e796d07e9de2402e60c3",
    "kirigami": "6de811e559c20dc1086c0cf2c34bb98712dbe4d45f960c62c3c3f887332c95f8",
    "kitemmodels": "f807e5b37aa913d2563ee1a21b2bce7d34495f32f38c7f35f16262d736bdfd55",
    "kitemviews": "9452f2b0cc5dd0214b88c4ce33297866be89af4177af14f5390cfb616e49c153",
    "kplotting": "f5a67be85c21665e052371301889443196b9de5b3927aff353a3d3e27730dd11",
    "kquickcharts": "9fe8c0c78ffd23ccfb99cc36477550a229c114ad057def938f38cdec35f82ab1",
    "syntax-highlighting": "fc429b093058bec4878306cbbfb3aa0560ff4a3f166c69504036c507fe72afcc",
    "ktexttemplate": "c3c229944d25294102e4e8a5b49fa0c0f481da9d33f8bec3782e8a53afd47493",
    "kuserfeedback": "c8a463c8e570f6d532cbe150732220575c6385df97c91399b6c84450691771ca",
    "kwidgetsaddons": "ab1333c258678caa7562120a1c03bb71779f7232f1a0e75b9525d921dee3e0a3",
    "kwindowsystem": "639a501b877446b19905399d27e2be2b6ebb0bb481abe3209dc4d535a12e12ca",
    "modemmanager-qt": "d7c4106dc130729fdfd435abaeaf85039a874fc18563a41755e14f7ea174ae21",
    "networkmanager-qt": "f6ba5f54d413ea0b2642207a6ebd0803e7cb8392b91fcf8a1679fd0c21062865",
    "prison": "2cdb0a2689ab45b907c76c9a01c1dc14855b8e5329ad0a9cf65c1ad64e5fed1b",
    "solid": "bdbfdc9f26b87e12b951097825af2956f2dee3f14c701d780277b69701f2c74e",
    "sonnet": "1574ef5c17f38e315de104b94580ccc1b7ec1db2650cb4bace2e14159bf61e10",
    "threadweaver": "e5400968a41820393e76190ab5dbb276c09513263d1b185d64b40f82dcd9b457",
}
errors: list[str] = []


def require(value: bool, message: str) -> None:
    if not value:
        errors.append(message)


try:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: cannot read {MANIFEST.relative_to(ROOT)}: {exc}", file=sys.stderr)
    raise SystemExit(1)

require(data.get("schema") == 1, "Tier 1 manifest schema must be 1")
require(data.get("authority") == "kde-upstream", "Tier 1 authority must be KDE upstream")
require(data.get("frameworks_series") == "6.30.0", "Tier 1 Frameworks series must be 6.30.0")
require(data.get("tier") == 1, "Tier 1 manifest must identify tier 1")
require(data.get("tier_reference") == "https://api.kde.org/", "Tier classification must reference KDE API")
require(data.get("release_reference") == "https://kde.org/info/kde-frameworks-6.30.0/", "Tier 1 release hashes must reference KDE 6.30 info page")
require(data.get("frameworks_qt_minimum") == "6.9.0", "Frameworks 6.30 Qt minimum must remain 6.9.0")

qt = data.get("selected_qt_provider", {})
require(qt.get("provider") == "ubuntu" and qt.get("series") == "resolute", "Tier 1 selected Qt provider must remain Ubuntu Resolute")
require(qt.get("resolved_version") == "6.10.2", "Tier 1 selected Qt provider evidence must remain 6.10.2")

ecm = data.get("ecm_prerequisite", {})
require(ecm.get("state") == "PASS", "Tier 1 requires a PASS ECM predecessor")
require(ecm.get("version") == "6.30.0-0supralinux3", "Tier 1 must consume the validated ECM package revision")
require(ecm.get("evidence_run_id") == 34694951158, "Tier 1 must retain the ECM PASS workflow run")
require(ecm.get("deb_sha256") == "ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f", "Tier 1 must pin the ECM PASS .deb hash")

nodes = data.get("nodes", [])
require(isinstance(nodes, list) and len(nodes) == len(EXPECTED), f"Tier 1 must contain exactly {len(EXPECTED)} upstream-classified nodes")
ids = [node.get("id") for node in nodes if isinstance(node, dict)]
require(len(ids) == len(set(ids)), "Tier 1 node IDs must be unique")
require(set(ids) == set(EXPECTED), "Tier 1 node set must match KDE upstream classification")

for node in nodes:
    if not isinstance(node, dict):
        errors.append("Tier 1 node entry must be an object")
        continue
    node_id = node.get("id")
    expected_hash = EXPECTED.get(node_id)
    require(node.get("upstream_tier") == 1, f"{node_id}: upstream tier must be 1")
    require(node.get("upstream_version") == "6.30.0", f"{node_id}: upstream version must be 6.30.0")
    require(node.get("depends_on") == ["extra-cmake-modules"], f"{node_id}: hosted DAG must depend on PASS ECM")
    require(node.get("kde_framework_dependencies") == [], f"{node_id}: a Tier 1 node cannot depend on another KDE Framework")
    require(node.get("external_dependencies") == "pending-resolution", f"{node_id}: external dependencies must remain explicitly pending until resolved")
    require(node.get("packaging") == {"state": "pending"}, f"{node_id}: packaging must remain pending until implemented")
    require(node.get("state") == "pending", f"{node_id}: node must remain pending until actually attempted")
    source_url = str(node.get("source_url", ""))
    require(source_url.startswith("https://download.kde.org/stable/frameworks/6.30/") and source_url.endswith("-6.30.0.tar.xz"), f"{node_id}: source URL must be KDE 6.30 stable tarball")
    source_hash = str(node.get("source_sha256", ""))
    require(re.fullmatch(r"[0-9a-f]{64}", source_hash) is not None, f"{node_id}: source SHA-256 must be lowercase 64-hex")
    require(source_hash == expected_hash, f"{node_id}: source SHA-256 does not match KDE 6.30 release metadata")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Frameworks Tier 1 manifest validation: PASS")
print(f"Tier 1 nodes: {len(nodes)}")
print("Frameworks 6.30 minimum Qt: 6.9.0; selected Ubuntu provider evidence: 6.10.2")
print("All Tier 1 package states: pending; external dependency resolution: pending")

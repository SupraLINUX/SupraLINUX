#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests/kde-tier1-package-campaign-batch2.json"
TIER1 = ROOT / "manifests/kde-frameworks-tier1.json"
DOC = ROOT / "docs/kde-tier1-package-batch2.md"
WORKFLOW = ROOT / ".github/workflows/kde-tier1-package-batch2.yml"
RUNNER = ROOT / "scripts/run-kde-tier1-package-batch2-preflight.sh"
SCOPE = ROOT / "scripts/kde-tier1-package-batch2-needed.sh"

EXPECTED = {
    "ktexttemplate": {
        "version": "6.30.0-0supralinux2", "state": "PASS", "last": "PASS", "eligible": True,
        "source": "c3c229944d25294102e4e8a5b49fa0c0f481da9d33f8bec3782e8a53afd47493",
        "symbols": "552e0c732cef6e8e0679d014fc7416ad23ecaa83322df9475a09d640e9831273",
        "runtime": "libkf6texttemplate6", "soname": "libKF6TextTemplate.so.6",
        "build": ["python3", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)"],
    },
    "karchive": {
        "version": "6.30.0-0supralinux3", "state": "remediation-pending-build", "last": "FAIL", "eligible": False,
        "source": "4cf89d91e429d2ece3110e78f7ef7011952b0412cb15011329516b46f21e98e2",
        "symbols": "acd4b767ad9cc821345a973e09c1e42c63d45fc3eef45197a35d84475c83878e",
        "runtime": "libkf6archive6", "soname": "libKF6Archive.so.6",
        "build": ["libbz2-dev", "liblzma-dev", "libssl-dev", "libzstd-dev", "pkgconf", "qt6-base-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)", "zlib1g-dev", "zstd"],
    },
    "kholidays": {
        "version": "6.30.0-0supralinux3", "state": "remediation-pending-build", "last": "FAIL", "eligible": False,
        "source": "02bfbc33296fe86b364491f6d5cad9d83360bb4fdd2923386a325b309eac0b9b",
        "symbols": "b0be25ddbc4c7abeb121bb0d3c3ca053d33e2a9fa88695bea210c50d56c256cd",
        "runtime": "libkf6holidays6", "soname": "libKF6Holidays.so.6",
        "build": ["dh-sequence-qmldeps", "bison (>= 2:3.3.2~)", "flex", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
    },
}

errors: list[str] = []
def req(ok: bool, message: str) -> None:
    if not ok:
        errors.append(message)
def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

campaign = load(CAMPAIGN)
tier1 = {item["id"]: item for item in load(TIER1)["nodes"]}
req(campaign.get("schema") == 1, "campaign schema")
req(campaign.get("authority") == "kde-upstream", "KDE authority")
req(campaign.get("frameworks_series") == "6.30.0", "Frameworks version")
req(campaign.get("batch") == "tier1-batch-2", "batch id")
req(campaign.get("state") == "remediation-pending-build", "batch remediation state")
req(campaign.get("selected_nodes") == ["ktexttemplate", "karchive", "kholidays"], "selected nodes")
req(campaign["shared_predecessors"]["extra_cmake_modules"]["version"] == "6.30.0-0supralinux3", "ECM predecessor")
req(campaign["shared_predecessors"]["packaging_trees"]["artifact_id"] == 10301938362, "packaging tree artifact")

for node, expected in EXPECTED.items():
    data = campaign["nodes"][node]
    req(data["state"] == expected["state"], f"{node}: state")
    req(data["last_result"] == expected["last"], f"{node}: last result")
    req(data["downstream_eligible"] is expected["eligible"], f"{node}: downstream eligibility")
    req(data["package_version"] == expected["version"], f"{node}: package revision")
    req(data["source_sha256"] == expected["source"], f"{node}: source hash")
    req(data["runtime_package"] == expected["runtime"] and data["soname"] == expected["soname"], f"{node}: ABI identity")
    req(data["symbols"]["sha256"] == expected["symbols"], f"{node}: symbols baseline")
    req(data["symbols"]["tree_provider"] == "debian" and data["symbols"]["reference_version"] == "6.28.0", f"{node}: symbols provider/version")
    deb = ROOT / "packages/kde" / node / "debian"
    control = (deb / "control").read_text(encoding="utf-8")
    rules = (deb / "rules").read_text(encoding="utf-8")
    changelog = (deb / "changelog").read_text(encoding="utf-8")
    readme = (deb / "README.source").read_text(encoding="utf-8")
    req(changelog.startswith(f"kf6-{node} ({expected['version']}) resolute;"), f"{node}: changelog revision")
    for token in ["debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)", *expected["build"]]:
        req(token in control, f"{node}: missing Build-Depends {token}")
    req("BUILD_QCH" not in rules and "-DBUILD_TESTING=ON" in rules and "dh_auto_test" in rules, f"{node}: test/QDoc policy")
    req("KDE Frameworks 6.30.0 is the source/build authority" in readme, f"{node}: authority documentation")
    req((deb / "source/format").read_text(encoding="utf-8") == "3.0 (quilt)\n", f"{node}: source format")
    req(sha(deb / "upstream/signing-key.asc") == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", f"{node}: signing key")
    req(tier1[node]["state"] == "pending" and tier1[node]["packaging"] == {"state": "pending"}, f"{node}: canonical Tier1 promotion deferred to closure")

kt = campaign["nodes"]["ktexttemplate"]
req(len(kt["evidence"]) == 3, "ktexttemplate: attempt history")
req(kt["evidence"][-1]["result"] == "PASS" and kt["evidence"][-1]["workflow_run"] == 34776524481, "ktexttemplate: current PASS run")
req(kt["evidence"][-1]["artifact_id"] == 10323233062 and kt["evidence"][-1]["artifact_sha256"] == "c0825408584e8d2e37a66ba95764e3e33adeafeaa5adcb30c253fb706c6c9f27", "ktexttemplate: current PASS artifact")
kt_override = kt["symbols"]["reviewed_override"]
req(kt_override["result_sha256"] == "2ff2111ce15f910328557c3295008fa21588518a0156626425df3c7b9f1b0e19", "ktexttemplate: symbols result")
req(sha(ROOT / "packages/kde/ktexttemplate/debian" / kt_override["file"]) == kt_override["file_sha256"], "ktexttemplate: transform hash")

ka = campaign["nodes"]["karchive"]
req(len(ka["evidence"]) == 2, "karchive: attempt history")
req(ka["evidence"][-1]["workflow_run"] == 34776389758 and ka["evidence"][-1]["artifact_id"] == 10323946438, "karchive: second FAIL evidence")
req(ka["evidence"][-1]["failure_substage"] == "dh_missing" and ka["evidence"][-1]["tests"] == "5/5 PASS", "karchive: second FAIL classification")
req("usr/lib/*/pkgconfig/KF6Archive.pc" in (ROOT / "packages/kde/karchive/debian/libkf6archive-dev.install").read_text(encoding="utf-8"), "karchive: pkg-config install contract")

kh = campaign["nodes"]["kholidays"]
req(len(kh["evidence"]) == 2, "kholidays: attempt history")
req(kh["evidence"][-1]["workflow_run"] == 34776389758 and kh["evidence"][-1]["artifact_id"] == 10323921696, "kholidays: second FAIL evidence")
req(kh["evidence"][-1]["failure_stage"] == "lintian" and kh["evidence"][-1]["tests"] == "8/8 PASS", "kholidays: second FAIL classification")
kh_override = kh["symbols"]["reviewed_override"]
req(kh_override["base_reference_sha256"] == EXPECTED["kholidays"]["symbols"], "kholidays: transform baseline")
req(kh_override["result_sha256"] == "fac03d2f96ccec7b6cbcfd30d59cee86496d3a0f6b5ad02d3392496b61e7c135", "kholidays: transform result")
req(kh_override["file_sha256"] == "07cce864692746d336af132d0c4dfd50e5127f89f430c1931a14dfb0f72a8cbf", "kholidays: transform pin")
req(sha(ROOT / "packages/kde/kholidays/debian" / kh_override["file"]) == kh_override["file_sha256"], "kholidays: transform file hash")
kh_rules = (ROOT / "packages/kde/kholidays/debian/rules").read_text(encoding="utf-8")
req("override_dh_makeshlibs" in kh_rules and "python3 debian/apply-symbols-delta.py" in kh_rules, "kholidays: transform hook")

scope = SCOPE.read_text(encoding="utf-8")
workflow = WORKFLOW.read_text(encoding="utf-8")
runner = RUNNER.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")
req("kde-tier1-package-campaign-batch2.json" in runner, "Batch2 runner ledger")
for token in ["ktexttemplate|karchive|kholidays", "kde-tier1-package-campaign-batch2.json", "run-kde-tier1-package-batch2-preflight.sh"]:
    req(token in scope, f"scope missing {token}")
for token in ["- ktexttemplate", "- karchive", "- kholidays", "fail-fast: false", "max-parallel: 3"]:
    req(token in workflow, f"workflow missing {token}")
for token in ["34720201713", "34776389758", "34776524481", "5/5", "8/8", "10/10", "KF6Archive.pc", "36", "fac03d2f96ccec7b6cbcfd30d59cee86496d3a0f6b5ad02d3392496b61e7c135"]:
    req(token in doc, f"documentation missing {token}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)
print("KDE Tier 1 Batch 2 remediation validation: PASS")
print("KTextTemplate PASS; KArchive/KHolidays -0supralinux3 remediation pending build")

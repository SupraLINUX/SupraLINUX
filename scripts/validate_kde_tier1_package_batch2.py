#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests/kde-tier1-package-campaign-batch2.json"
TIER1 = ROOT / "manifests/kde-frameworks-tier1.json"
WORKFLOW = ROOT / ".github/workflows/kde-tier1-package-batch2.yml"
RUNNER = ROOT / "scripts/run-kde-tier1-package-batch2-preflight.sh"
SCOPE = ROOT / "scripts/kde-tier1-package-batch2-needed.sh"
DOC = ROOT / "docs/kde-tier1-package-batch2.md"

EXPECTED = {
    "ktexttemplate": {
        "source": "c3c229944d25294102e4e8a5b49fa0c0f481da9d33f8bec3782e8a53afd47493",
        "root": "e68c80cc6106c87e321d23729f882052ab386972",
        "symbols": "552e0c732cef6e8e0679d014fc7416ad23ecaa83322df9475a09d640e9831273",
        "copyright": "b7b88bf2a8f3f4d19fb85b0d00d1464430a4f97a1949616a16a5a956c6c97109",
        "runtime": "libkf6texttemplate6",
        "soname": "libKF6TextTemplate.so.6",
        "contracts": [("libkf6texttemplate-dev", "amd64", None), ("libkf6texttemplate-doc", "all", "foreign"), ("libkf6texttemplate6", "amd64", "same")],
        "build": ["python3", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)"],
        "job": 103624554096,
        "artifact": 10306265683,
        "artifact_sha256": "c164640037e564a43479daaa740f55c0f7578d977a7c38bfeb691fbd6b88544a",
    },
    "karchive": {
        "source": "4cf89d91e429d2ece3110e78f7ef7011952b0412cb15011329516b46f21e98e2",
        "root": "6f86222fb967c7f3e29c15ecef40bf355d8004d0",
        "symbols": "acd4b767ad9cc821345a973e09c1e42c63d45fc3eef45197a35d84475c83878e",
        "copyright": "c82d4cf65cdfb5255a04d9e842edc6df47aece48318fd4de6c7c9a61660006ff",
        "runtime": "libkf6archive6",
        "soname": "libKF6Archive.so.6",
        "contracts": [("libkf6archive-data", "all", "foreign"), ("libkf6archive-dev", "amd64", None), ("libkf6archive-doc", "all", "foreign"), ("libkf6archive6", "amd64", "same")],
        "build": ["libbz2-dev", "liblzma-dev", "libssl-dev", "libzstd-dev", "pkgconf", "qt6-base-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)", "zlib1g-dev", "zstd"],
        "job": 103624554004,
        "artifact": 10305889632,
        "artifact_sha256": "1850a0a6dd7f267870fda83f17f5990f806ec76ae8fe810144557c46af532d01",
    },
    "kholidays": {
        "source": "02bfbc33296fe86b364491f6d5cad9d83360bb4fdd2923386a325b309eac0b9b",
        "root": "ee43159b9e7259c8c4cefe0db38e2ca715b73ad9",
        "symbols": "b0be25ddbc4c7abeb121bb0d3c3ca053d33e2a9fa88695bea210c50d56c256cd",
        "copyright": "c9b4c8797fc5a93733224a2ed442a3de75b3bdb5ef24dd8bdf5abb48d34a1e73",
        "runtime": "libkf6holidays6",
        "soname": "libKF6Holidays.so.6",
        "contracts": [("libkf6holidays-data", "all", "foreign"), ("libkf6holidays-dev", "amd64", "same"), ("libkf6holidays-doc", "all", "foreign"), ("libkf6holidays6", "amd64", "same"), ("qml6-module-org-kde-kholidays", "amd64", "same")],
        "build": ["dh-sequence-qmldeps", "bison (>= 2:3.3.2~)", "flex", "qt6-base-dev (>= 6.9.0~)", "qt6-declarative-dev (>= 6.9.0~)", "qt6-tools-dev (>= 6.9.0~)"],
        "job": 103624554109,
        "artifact": 10305513311,
        "artifact_sha256": "522257440d6e04563162178dd3d3ab3ae658dc56c129dcf7f482fef8219bb0dc",
    },
}

errors: list[str] = []


def req(value: bool, message: str) -> None:
    if not value:
        errors.append(message)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


campaign = load(CAMPAIGN)
tier1 = load(TIER1)
req(campaign.get("schema") == 1, "campaign schema")
req(campaign.get("authority") == "kde-upstream", "KDE authority")
req(campaign.get("frameworks_series") == "6.30.0", "Frameworks version")
req(campaign.get("batch") == "tier1-batch-2", "batch id")
req(campaign.get("state") == "remediation-pending-build", "batch remediation state")
req(campaign.get("selected_nodes") == ["ktexttemplate", "karchive", "kholidays"], "selected nodes")
req(set(campaign.get("nodes", {})) == set(EXPECTED), "campaign node set")
req(campaign["shared_predecessors"]["extra_cmake_modules"]["version"] == "6.30.0-0supralinux3", "ECM predecessor")
req(campaign["shared_predecessors"]["packaging_trees"]["artifact_id"] == 10301938362, "tree artifact")
req(campaign["shared_packaging_inputs"]["signing_key"]["sha256"] == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", "signing key pin")

tier = {item["id"]: item for item in tier1["nodes"]}
for node, expected in EXPECTED.items():
    data = campaign["nodes"][node]
    req(data["state"] == "remediation-pending-build", f"{node}: remediation state")
    req(data["last_result"] == "FAIL" and data["downstream_eligible"] is False, f"{node}: first attempt FAIL/downstream state")
    req(data["package_version"] == "6.30.0-0supralinux2", f"{node}: remediation revision")
    req(data["source_sha256"] == expected["source"], f"{node}: source hash")
    req(data["root_cmake_blob"] == expected["root"], f"{node}: CMake pin")
    req(data["runtime_package"] == expected["runtime"] and data["soname"] == expected["soname"], f"{node}: ABI identity")
    req(data["symbols"]["sha256"] == expected["symbols"] and data["symbols"]["tree_provider"] == "debian" and data["symbols"]["reference_version"] == "6.28.0", f"{node}: retained symbols reference")
    req(data["copyright"]["sha256"] == expected["copyright"], f"{node}: copyright hash")
    req([(x["name"], x["architecture"], x["multi_arch"]) for x in data["binary_contracts"]] == expected["contracts"], f"{node}: binary contracts")
    req(len(data["evidence"]) == 1, f"{node}: exactly one historical attempt")
    if data["evidence"]:
        ev = data["evidence"][0]
        req(ev.get("result") == "FAIL" and ev.get("workflow_run") == 34720201713, f"{node}: first FAIL run")
        req(ev.get("job_id") == expected["job"], f"{node}: first FAIL job")
        req(ev.get("artifact_id") == expected["artifact"] and ev.get("artifact_sha256") == expected["artifact_sha256"], f"{node}: first FAIL artifact")
        req(ev.get("attempted_package_version") == "6.30.0-0supralinux1", f"{node}: first attempted revision")
        req(ev.get("failure_stage") == "sbuild", f"{node}: first FAIL stage")
    req(tier[node]["state"] == "pending" and tier[node]["packaging"] == {"state": "pending"}, f"{node}: canonical Tier1 remains pending until revised PASS")

    deb = ROOT / "packages/kde" / node / "debian"
    control = (deb / "control").read_text(encoding="utf-8")
    rules = (deb / "rules").read_text(encoding="utf-8")
    changelog = (deb / "changelog").read_text(encoding="utf-8")
    readme = (deb / "README.source").read_text(encoding="utf-8")
    req(changelog.startswith(f"kf6-{node} (6.30.0-0supralinux2) resolute;"), f"{node}: changelog revision")
    for token in ["debhelper-compat (= 13)", "dh-sequence-kf6", "dh-sequence-pkgkde-symbolshelper", "cmake (>= 3.29~)", "extra-cmake-modules (>= 6.30.0~)", *expected["build"]]:
        req(token in control, f"{node}: missing Build-Depends {token}")
    req("BUILD_QCH" not in rules, f"{node}: stale BUILD_QCH forbidden")
    req("-DBUILD_TESTING=ON" in rules and "dh_auto_test" in rules, f"{node}: upstream tests must run")
    req("Disable auto tests" not in rules, f"{node}: tests may not be disabled")
    req("KDE Frameworks 6.30.0 is the source/build authority" in readme, f"{node}: authority doc")
    req((deb / "source/format").read_text(encoding="utf-8") == "3.0 (quilt)\n", f"{node}: source format")
    key = deb / "upstream/signing-key.asc"
    req(hashlib.sha256(key.read_bytes()).hexdigest() == "86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d", f"{node}: signing key")
    req((ROOT / "packages/kde" / node / "consumer/CMakeLists.txt").is_file() and (ROOT / "packages/kde" / node / "consumer/main.cpp").is_file(), f"{node}: consumer")

kt = campaign["nodes"]["ktexttemplate"]["symbols"]["reviewed_override"]
helper = ROOT / "packages/kde/ktexttemplate/debian" / kt["file"]
req(kt["method"] == "deterministic-transform", "ktexttemplate: symbols override method")
req(kt["base_reference_sha256"] == EXPECTED["ktexttemplate"]["symbols"], "ktexttemplate: symbols override base")
req(kt["result_sha256"] == "2ff2111ce15f910328557c3295008fa21588518a0156626425df3c7b9f1b0e19", "ktexttemplate: reviewed symbols result")
req(helper.is_file() and hashlib.sha256(helper.read_bytes()).hexdigest() == kt["file_sha256"], "ktexttemplate: symbols transform hash")
kt_rules = (ROOT / "packages/kde/ktexttemplate/debian/rules").read_text(encoding="utf-8")
req("python3 debian/apply-symbols-delta.py" in kt_rules and "override_dh_makeshlibs" in kt_rules, "ktexttemplate: reviewed symbols transform must run at dh_makeshlibs")

runner = RUNNER.read_text(encoding="utf-8")
scope = SCOPE.read_text(encoding="utf-8")
workflow = WORKFLOW.read_text(encoding="utf-8")
doc = DOC.read_text(encoding="utf-8")
req("kde-tier1-package-campaign-batch2.json" in runner and "kde-tier1-package-campaign.json\"" not in runner, "Batch2 runner must be isolated from Batch1 ledger")
for token in ["ktexttemplate|karchive|kholidays", "kde-tier1-package-campaign-batch2.json", "run-kde-tier1-package-batch2-preflight.sh", "kde-tier1-package-batch2.yml"]:
    req(token in scope, f"scope missing {token}")
for token in ["- ktexttemplate", "- karchive", "- kholidays", "fail-fast: false", "max-parallel: 3", "run-kde-tier1-package-batch2-preflight.sh"]:
    req(token in workflow, f"workflow missing {token}")
for token in ["KTextTemplate", "KArchive", "KHolidays", "Debian 6.28", "Ubuntu Resolute", "BUILD_TESTING", "QDoc", "34720201713", "qt6-tools-dev", "2ff2111ce15f910328557c3295008fa21588518a0156626425df3c7b9f1b0e19"]:
    req(token in doc, f"doc missing {token}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 Batch 2 remediation validation: PASS")
print("Revised nodes: ktexttemplate, karchive, kholidays")
print("Historical run 34720201713 retained as three real FAIL attempts")
print("Canonical Tier 1 state unchanged until revised clean-package PASS evidence exists")

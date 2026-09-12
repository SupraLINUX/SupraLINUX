#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests" / "kde-tier1-package-campaign.json"
SCOPE = ROOT / "scripts" / "kde-tier1-package-preflight-needed.sh"
DOC = ROOT / "docs" / "kde-tier1-package-batch1.md"
SYMBOLS = ROOT / "packages" / "kde" / "kcodecs" / "debian" / "libkf6codecs6.symbols.supralinux"
RULES = ROOT / "packages" / "kde" / "kcodecs" / "debian" / "rules"
CHANGELOG = ROOT / "packages" / "kde" / "kcodecs" / "debian" / "changelog"

errors: list[str] = []

def require(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)

def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"cannot load {path.relative_to(ROOT)}: {exc}")
    if not isinstance(value, dict):
        raise SystemExit(f"{path.relative_to(ROOT)} must contain an object")
    return value

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""

campaign = load(CAMPAIGN)
scope = read(SCOPE)
doc = read(DOC)
symbols = read(SYMBOLS)
rules = read(RULES)
changelog = read(CHANGELOG)

require(campaign.get("schema") == 1, "campaign schema must remain 1")
require(campaign.get("frameworks_series") == "6.30.0", "campaign must target Frameworks 6.30.0")
require(campaign.get("authority") == "kde-upstream", "KDE upstream must remain authority")
require(campaign.get("state") == "mixed-pass-fail-remediation", "batch state must reflect mixed PASS/FAIL")
require(campaign.get("canonical_state_role") == "current-package-attempt-ledger", "campaign must declare current-state role")
nodes = campaign.get("nodes", {})
require(set(nodes) == {"kcodecs", "kdbusaddons", "threadweaver"}, "batch node set changed")

expected = {
    "kcodecs": {
        "state": "remediation-pending-build",
        "last_result": "FAIL",
        "package_version": "6.30.0-0supralinux4",
        "job3": 103605147896,
        "artifact3": 10304255731,
        "digest3": "336d771a73091f2b0a7c60cf55833b5205f2c4bc8a8e87802065fe38333c2b0d",
        "tests3": "8/8 PASS",
    },
    "kdbusaddons": {
        "state": "PASS",
        "last_result": "PASS",
        "package_version": "6.30.0-0supralinux3",
        "job3": 103605147881,
        "artifact3": 10304340428,
        "digest3": "2bfb451724808b5318625eee3df25a6104c9b6da77482737ac54eea058a7e799",
        "tests3": "3/3 PASS",
    },
    "threadweaver": {
        "state": "PASS",
        "last_result": "PASS",
        "package_version": "6.30.0-0supralinux3",
        "job3": 103605147772,
        "artifact3": 10303986419,
        "digest3": "6395f11ed633fb034b0bf61a95639ce00005e3211994b04924abeb306deed2b8",
        "tests3": "8/8 PASS",
    },
}

for node_id, exp in expected.items():
    node = nodes.get(node_id, {})
    require(node.get("state") == exp["state"], f"{node_id}: current state mismatch")
    require(node.get("last_result") == exp["last_result"], f"{node_id}: last_result mismatch")
    require(node.get("package_version") == exp["package_version"], f"{node_id}: package revision mismatch")
    evidence = node.get("evidence", [])
    require(isinstance(evidence, list) and len(evidence) == 3, f"{node_id}: exactly three attempts must be retained")
    if isinstance(evidence, list) and len(evidence) == 3:
        a1, a2, a3 = evidence
        require(a1.get("workflow_run") == 34709829162 and a1.get("result") == "FAIL", f"{node_id}: attempt 1 evidence mismatch")
        require(a1.get("autotests_reached") is False, f"{node_id}: attempt 1 must not claim autotests")
        require(a2.get("workflow_run") == 34710627400 and a2.get("result") == "FAIL", f"{node_id}: attempt 2 evidence mismatch")
        require(str(a2.get("tests", "")).endswith("PASS"), f"{node_id}: attempt 2 test PASS evidence missing")
        require(a3.get("workflow_run") == 34713034164, f"{node_id}: attempt 3 run mismatch")
        require(a3.get("job_id") == exp["job3"], f"{node_id}: attempt 3 job mismatch")
        require(a3.get("artifact_id") == exp["artifact3"] and a3.get("artifact_sha256") == exp["digest3"], f"{node_id}: attempt 3 artifact mismatch")
        require(a3.get("tests") == exp["tests3"], f"{node_id}: attempt 3 tests mismatch")
        require(a3.get("result") == exp["last_result"], f"{node_id}: attempt 3 result mismatch")

for node_id in ("kdbusaddons", "threadweaver"):
    node = nodes[node_id]
    require(node.get("downstream_eligible") is True, f"{node_id}: PASS must be downstream eligible")
    require(node["evidence"][2].get("lintian") == "PASS-errors", f"{node_id}: Lintian PASS evidence missing")
    require(node["evidence"][2].get("consumer_smoke") == "PASS", f"{node_id}: consumer PASS evidence missing")
    require(isinstance(node.get("pass_files"), dict) and bool(node["pass_files"]), f"{node_id}: retained artifact file hashes missing")

kcodecs = nodes["kcodecs"]
sym = kcodecs.get("symbols", {})
reviewed = sym.get("reviewed_override", {})
require(sym.get("tree_provider") == "debian", "kcodecs: base symbols reference must remain Debian")
require(sym.get("sha256") == "35f6b7b6885b3db41bcce95b99610b2e917e1b4e13d5ba7e801b93dd47c4f8c7", "kcodecs: Debian 6.28 symbols baseline changed")
require(reviewed.get("sha256") == "b87cbfbfe47d7cf99248b57196257a2765987297a701310de513d1e36c51d696", "kcodecs: reviewed symbols override hash mismatch")
if SYMBOLS.exists():
    actual = hashlib.sha256(SYMBOLS.read_bytes()).hexdigest()
    require(actual == reviewed.get("sha256"), "kcodecs: reviewed symbols file content/hash mismatch")
optional_lines = [line for line in symbols.splitlines() if "(optional=toolchain)" in line]
require(len(optional_lines) == 15, "kcodecs: exactly 15 toolchain symbols must be optional")
for line in optional_lines:
    require(re.match(r"^\s+\(optional=toolchain\)\S+@Base 6\.30\.0$", line) is not None, f"kcodecs: malformed optional symbol line: {line}")
require("6.30.0-0supralinux" not in symbols, "kcodecs: source symbols template must not encode Debian revision minima")
require("override_dh_makeshlibs:" in rules and "libkf6codecs6.symbols.supralinux" in rules, "kcodecs: reviewed symbols override must be installed before dh_makeshlibs")
require(changelog.startswith("kf6-kcodecs (6.30.0-0supralinux4) resolute;"), "kcodecs: changelog must start at -0supralinux4")

for token in (
    'packages/kde/"${NODE}"/*',
    'fingerprint(load(before)) == fingerprint(load(after))',
    '"state", "last_result", "evidence", "downstream_eligible", "pass_files"',
    'Shared package runner/workflow changed',
):
    require(token in scope, f"scope helper missing invariant: {token}")
require("docs/" not in scope, "docs-only changes must not rebuild packages")

for token in (
    "34713034164",
    "10304340428",
    "10303986419",
    "10304255731",
    "6.30.0-0supralinux4",
    "optional=toolchain",
    "dpkg-gensymbols -c4",
):
    require(token in doc, f"batch documentation missing {token}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 1 batch 1 current-state validation: PASS")
print("KDBusAddons PASS; ThreadWeaver PASS; KCodecs FAIL with -0supralinux4 remediation prepared")

#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests" / "kde-tier1-package-campaign.json"
TIER1 = ROOT / "manifests" / "kde-frameworks-tier1.json"
DAG = ROOT / "manifests" / "kde-dag.json"
SCOPE = ROOT / "scripts" / "kde-tier1-package-preflight-needed.sh"
RUNNER = ROOT / "scripts" / "run-kde-tier1-package-preflight.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-tier1-package-preflight.yml"
DOC = ROOT / "docs" / "kde-tier1-package-batch1.md"
KCODECS_SYMBOLS = ROOT / "packages" / "kde" / "kcodecs" / "debian" / "libkf6codecs6.symbols.supralinux"
KCODECS_RULES = ROOT / "packages" / "kde" / "kcodecs" / "debian" / "rules"

EXPECTED = {
    "kcodecs": {
        "version": "6.30.0-0supralinux4",
        "run": 34716761551,
        "job": 103615297758,
        "artifact": 10305050385,
        "digest": "d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45",
        "tests": "8/8 PASS",
        "soname": "libKF6Codecs.so.6",
    },
    "kdbusaddons": {
        "version": "6.30.0-0supralinux3",
        "run": 34713034164,
        "job": 103605147881,
        "artifact": 10304340428,
        "digest": "2bfb451724808b5318625eee3df25a6104c9b6da77482737ac54eea058a7e799",
        "tests": "3/3 PASS",
        "soname": "libKF6DBusAddons.so.6",
    },
    "threadweaver": {
        "version": "6.30.0-0supralinux3",
        "run": 34713034164,
        "job": 103605147772,
        "artifact": 10303986419,
        "digest": "6395f11ed633fb034b0bf61a95639ce00005e3211994b04924abeb306deed2b8",
        "tests": "8/8 PASS",
        "soname": "libKF6ThreadWeaver.so.6",
    },
}
SCOPE_INCIDENT = {
    "run": 34716761551,
    "commit": "6c156b6a1dc0fc9e6c9e43eae90c3da86f6b0cb9",
    "kdbusaddons_job": 103615297686,
    "kdbusaddons_artifact": 10305410248,
    "kdbusaddons_digest": "ce17097096841a500ce8b2e4f24171253b91ba1dce4a6560d0107d626eb32b1a",
    "threadweaver_job": 103615297757,
    "threadweaver_artifact": 10304955612,
    "threadweaver_digest": "79e5393b892ae1ee3fb9a19c21e2f41bb691c7c55bf40487bb2d5de7c42fc507",
}
errors: list[str] = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot load {path.relative_to(ROOT)}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(value, dict):
        raise SystemExit(f"ERROR: {path.relative_to(ROOT)} must contain an object")
    return value

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {path.relative_to(ROOT)}: {exc}")
        return ""

campaign = load(CAMPAIGN)
tier1 = load(TIER1)
dag = load(DAG)
scope = read(SCOPE)
runner = read(RUNNER)
workflow = read(WORKFLOW)
doc = read(DOC)
symbols = read(KCODECS_SYMBOLS)
rules = read(KCODECS_RULES)

require(campaign.get("schema") == 1, "Batch campaign schema must be 1")
require(campaign.get("authority") == "kde-upstream", "Batch authority must remain KDE upstream")
require(campaign.get("frameworks_series") == "6.30.0", "Batch must remain on Frameworks 6.30.0")
require(campaign.get("state") == "PASS", "Batch 1 must be closed PASS after all three material package PASSes")
require(campaign.get("shared_predecessors", {}).get("extra_cmake_modules", {}).get("version") == "6.30.0-0supralinux3", "Batch must consume validated ECM")
require(campaign.get("shared_predecessors", {}).get("packaging_trees", {}).get("artifact_id") == 10301938362, "Batch must retain generic packaging-tree artifact")

nodes = campaign.get("nodes", {})
require(set(nodes) == set(EXPECTED), "Batch 1 node set changed unexpectedly")
for node_id, expected in EXPECTED.items():
    node = nodes.get(node_id, {})
    require(node.get("state") == "PASS", f"{node_id}: current state must be PASS")
    require(node.get("last_result") == "PASS", f"{node_id}: last result must be PASS")
    require(node.get("downstream_eligible") is True, f"{node_id}: must be downstream eligible")
    require(node.get("package_version") == expected["version"], f"{node_id}: validated revision mismatch")
    passes = [item for item in node.get("evidence", []) if isinstance(item, dict) and item.get("result") == "PASS"]
    require(len(passes) == 1, f"{node_id}: exactly one retained current PASS expected")
    if passes:
        item = passes[0]
        require(item.get("workflow_run") == expected["run"], f"{node_id}: PASS run mismatch")
        require(item.get("job_id") == expected["job"], f"{node_id}: PASS job mismatch")
        require(item.get("artifact_id") == expected["artifact"], f"{node_id}: PASS artifact mismatch")
        require(item.get("artifact_sha256") == expected["digest"], f"{node_id}: PASS artifact digest mismatch")
        require(item.get("tests") == expected["tests"], f"{node_id}: test evidence mismatch")
        require(item.get("lintian") == "PASS-errors", f"{node_id}: Lintian errors gate must pass")
        require(item.get("consumer_smoke") == "PASS", f"{node_id}: consumer smoke must pass")
        require(item.get("abi_soname") == expected["soname"], f"{node_id}: SONAME mismatch")
        require(item.get("ecm_predecessor") == "6.30.0-0supralinux3", f"{node_id}: ECM proof mismatch")
    files = node.get("pass_files", {})
    require(isinstance(files, dict) and bool(files), f"{node_id}: PASS file hashes required")
    for key, digest in files.items():
        require(re.fullmatch(r"[0-9a-f]{64}", str(digest)) is not None, f"{node_id}: invalid hash {key}")

incidents = campaign.get("ci_scope_incidents", [])
require(len(incidents) == 1, "Exactly one retained batch-1 scope incident expected")
if incidents:
    incident = incidents[0]
    require(incident.get("workflow_run") == SCOPE_INCIDENT["run"], "Scope incident run mismatch")
    require(incident.get("commit") == SCOPE_INCIDENT["commit"], "Scope incident commit mismatch")
    require(incident.get("classification") == "infrastructure-scope-selection", "Scope incident classification mismatch")
    require(incident.get("package_state_effect") == "none", "Scope incident must not alter package state")
    jobs = {item.get("node"): item for item in incident.get("jobs", []) if isinstance(item, dict)}
    for node_id in ("kdbusaddons", "threadweaver"):
        require(jobs.get(node_id, {}).get("abort_stage") == "campaign-validation", f"{node_id}: scope incident must abort before package attempt")
        require("got PASS" in jobs.get(node_id, {}).get("message", ""), f"{node_id}: scope incident abort message missing")
    require(jobs.get("kdbusaddons", {}).get("job_id") == SCOPE_INCIDENT["kdbusaddons_job"], "KDBusAddons scope incident job mismatch")
    require(jobs.get("kdbusaddons", {}).get("artifact_id") == SCOPE_INCIDENT["kdbusaddons_artifact"], "KDBusAddons scope incident artifact mismatch")
    require(jobs.get("kdbusaddons", {}).get("artifact_sha256") == SCOPE_INCIDENT["kdbusaddons_digest"], "KDBusAddons scope incident digest mismatch")
    require(jobs.get("threadweaver", {}).get("job_id") == SCOPE_INCIDENT["threadweaver_job"], "ThreadWeaver scope incident job mismatch")
    require(jobs.get("threadweaver", {}).get("artifact_id") == SCOPE_INCIDENT["threadweaver_artifact"], "ThreadWeaver scope incident artifact mismatch")
    require(jobs.get("threadweaver", {}).get("artifact_sha256") == SCOPE_INCIDENT["threadweaver_digest"], "ThreadWeaver scope incident digest mismatch")

tier_nodes = {item.get("id"): item for item in tier1.get("nodes", []) if isinstance(item, dict)}
for node_id, expected in EXPECTED.items():
    node = tier_nodes.get(node_id, {})
    require(node.get("state") == "PASS", f"{node_id}: canonical Tier 1 state must be PASS")
    require(node.get("packaging", {}).get("package_version") == expected["version"], f"{node_id}: canonical Tier 1 package version mismatch")
require(sum(1 for item in tier_nodes.values() if item.get("state") == "PASS") == 4, "Canonical Tier 1 PASS count must be 4")
require(sum(1 for item in tier_nodes.values() if item.get("state") == "pending") == 25, "Canonical Tier 1 pending count must be 25")

for node_id in EXPECTED:
    dag_node = dag.get("nodes", {}).get(node_id, {})
    require(dag_node.get("state") == "PASS", f"{node_id}: global DAG state must be PASS")
    require(dag_node.get("downstream_eligible") is True, f"{node_id}: global DAG node must be downstream eligible")
require(dag.get("nodes", {}).get("extra-cmake-modules", {}).get("state") == "PASS", "ECM DAG root must remain PASS")

require(hashlib.sha256(KCODECS_SYMBOLS.read_bytes()).hexdigest() == "b87cbfbfe47d7cf99248b57196257a2765987297a701310de513d1e36c51d696", "KCodecs reviewed symbols override hash mismatch")
toolchain_lines = [line for line in symbols.splitlines() if line.startswith("(optional=toolchain)")]
require(len(toolchain_lines) == 15, "KCodecs must retain exactly 15 reviewed optional=toolchain symbols")
for line in toolchain_lines:
    require(line.endswith(" 6.30.0"), "KCodecs toolchain symbols must use upstream minimum 6.30.0")
    require("-0supralinux" not in line, "KCodecs symbols must never use a Debian revision as minimum")
require("cp debian/libkf6codecs6.symbols.supralinux debian/libkf6codecs6.symbols" in rules, "KCodecs rules must install reviewed symbols before dh_makeshlibs")
require(rules.index("cp debian/libkf6codecs6.symbols.supralinux") < rules.index("dh_makeshlibs"), "KCodecs reviewed symbols must be installed before dh_makeshlibs")

for token in (
    '"upstream_version": node["upstream_version"]',
    '"source_package": node["source_package"]',
    '"package_version": node["package_version"]',
    '"source_url": node["source_url"]',
    '"source_sha256": node["source_sha256"]',
    '"symbols_file": symbols["file"]',
    '"symbols_sha256": symbols["sha256"]',
    '"symbols_tree_provider": symbols["tree_provider"]',
    '"copyright_sha256": copyright_meta["sha256"]',
    '"binary_contracts": node["binary_contracts"]',
    '"soname": node["soname"]',
    '"consumer_run": node["consumer_run"]',
    'state/evidence/descriptive-only',
    'already PASS and no consumed build input changed; skip',
):
    require(token in scope, f"Semantic scope missing consumed-input invariant: {token}")
for forbidden in ('"state": node["state"]', '"evidence": node["evidence"]', '"last_result": node["last_result"]', '"pass_files": node["pass_files"]'):
    require(forbidden not in scope, f"Scope fingerprint must not depend on result metadata: {forbidden}")

for token in ("fail-fast: false", "max-parallel: 3", "kcodecs", "kdbusaddons", "threadweaver", "scripts/kde-tier1-package-preflight-needed.sh"):
    require(token in workflow, f"Batch workflow missing invariant: {token}")
require("Node must be prepared/remediation-pending-build before attempt" in runner, "Runner must reject accidental rebuilds of PASS nodes")

for value in (
    "3/3 PASS",
    "4 Tier 1 PASS",
    "25 pending",
    "34716761551",
    "10305050385",
    "d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45",
    "infrastructure scope",
):
    require(value.lower() in doc.lower(), f"Batch documentation must retain closure evidence: {value}")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("KDE Frameworks Tier 1 batch 1 canonical closure: PASS")
print("Batch nodes: kcodecs, kdbusaddons, threadweaver = 3/3 PASS")
print("Canonical Tier 1: 4 PASS, 25 pending, 0 FAIL, 0 BLOCKED")
print("Scope incident retained as infrastructure-only; package PASS states unchanged")

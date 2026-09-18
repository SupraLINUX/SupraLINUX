#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "manifests/kde-tier1-global-discovery.json"
TIER1 = ROOT / "manifests/kde-frameworks-tier1.json"

def fail(message: str) -> None:
    raise SystemExit(message)

def load(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        fail(f"cannot parse {path.relative_to(ROOT)}: {exc}")

c = load(CAMPAIGN)
t = load(TIER1)
if c.get("schema") != 1 or c.get("strategy") != "dag-global-discovery":
    fail("global discovery identity mismatch")
if c.get("authority") != "kde-upstream" or c.get("provider_platform") != "ubuntu-resolute":
    fail("authority/provider separation regressed")
required_policy = {
    "build_every_runnable_node_per_topological_level": True,
    "parallelize_independent_nodes": True,
    "fail_fast": False,
    "continue_after_independent_failures": True,
    "blocked_is_not_fail": True,
    "only_pass_artifacts_feed_dependents": True,
    "preserve_every_real_attempt": True,
    "rerun_affected_nodes_after_remediation": True,
    "repeat_full_campaign_after_remediation_set": True,
}
if c.get("policy") != required_policy:
    fail("global discovery policy changed")
nodes = c.get("nodes", {})
lanes = c.get("lanes", {})
expected = {"kconfig", "ki18n", "sonnet", "kirigami", "kquickcharts", "kuserfeedback", "prison"}
if set(nodes) != expected:
    fail(f"unexpected post-Batch8 discovery set: {sorted(set(nodes) ^ expected)}")
allowed = {"runnable", "lane-pending", "dependency-blocked"}
for node, meta in nodes.items():
    if meta.get("readiness") not in allowed:
        fail(f"{node}: invalid readiness")
    lane = meta.get("lane")
    if lane not in lanes or node not in lanes[lane].get("nodes", []):
        fail(f"{node}: lane membership mismatch")
lane_members = [n for meta in lanes.values() for n in meta.get("nodes", [])]
if len(lane_members) != len(set(lane_members)) or set(lane_members) != expected:
    fail("lane membership must cover each discovery node exactly once")
tier_nodes = t.get("nodes", [])
state_by_id = {n["id"]: n.get("state") for n in tier_nodes}
nonpass = {n for n, state in state_by_id.items() if state != "PASS"}
passed = {n for n, state in state_by_id.items() if state == "PASS"}
if nonpass != expected or len(passed) != 22 or len(nonpass) != 7:
    fail(f"canonical promotion mismatch PASS={len(passed)} non-PASS={len(nonpass)}")
snapshot = c.get("promoted_snapshot", {})
if snapshot.get("pass") != 22 or snapshot.get("pending") != 7 or snapshot.get("current_fail") != 0 or snapshot.get("blocked") != 0:
    fail("promoted snapshot mismatch")
ready = {n for n, m in nodes.items() if m["readiness"] == "runnable"}
blocked = {n for n, m in nodes.items() if m["readiness"] == "dependency-blocked"}
lane_pending = {n for n, m in nodes.items() if m["readiness"] == "lane-pending"}
if ready:
    fail(f"no package lane is runnable immediately after canonical promotion: {sorted(ready)}")
if blocked:
    fail(f"no discovery node should remain dependency-blocked after KCoreAddons PASS: {sorted(blocked)}")
if lane_pending != expected:
    fail("all seven remaining nodes must be lane-pending until their package runners exist")
local_lane = lanes["local-predecessor"]
if local_lane.get("status") != "completed" or local_lane.get("nodes") != []:
    fail("KGuiAddons local-predecessor lane must be completed and empty after Batch 8 promotion")
if local_lane.get("runner") != "scripts/run-kde-tier1-package-batch8-preflight.sh":
    fail("KGuiAddons completed lane must retain its validated Batch 8 runner")
if lanes["single-abi-python"].get("status") != "completed" or lanes["single-abi-python"].get("nodes") != []:
    fail("Batch 7 single-ABI Python lane must be closed after promotion")
for lane in ("multi-abi", "qml-multisurface", "multi-surface-optional"):
    if lanes[lane].get("status") != "implementation-pending":
        fail(f"{lane}: must remain implementation-pending")
print("KDE Tier 1 global discovery policy: PASS")
print("promoted PASS=22; discovery nodes=7; runnable=0; lane-pending=7; dependency-blocked=0")

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

if c.get("schema") != 1:
    fail("global discovery schema must be 1")
if c.get("strategy") != "dag-global-discovery":
    fail("unexpected global discovery strategy")
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
    fail("global discovery policy does not match the canonical DAG campaign contract")

nodes = c.get("nodes")
lanes = c.get("lanes")
if not isinstance(nodes, dict) or not isinstance(lanes, dict):
    fail("nodes/lanes must be objects")

allowed_readiness = {"runnable", "lane-pending", "dependency-blocked"}
for node, meta in nodes.items():
    if meta.get("readiness") not in allowed_readiness:
        fail(f"{node}: invalid readiness {meta.get('readiness')!r}")
    lane = meta.get("lane")
    if lane not in lanes:
        fail(f"{node}: unknown lane {lane!r}")
    if node not in lanes[lane].get("nodes", []):
        fail(f"{node}: lane membership mismatch")

lane_members = [n for meta in lanes.values() for n in meta.get("nodes", [])]
if len(lane_members) != len(set(lane_members)):
    fail("a node appears in more than one discovery lane")
if set(lane_members) != set(nodes):
    fail("lane membership does not exactly cover discovery nodes")

expected = {
    "kcalendarcore", "kcoreaddons", "kwidgetsaddons", "kconfig", "ki18n", "sonnet",
    "kirigami", "kquickcharts", "kuserfeedback", "prison", "kguiaddons",
}
if set(nodes) != expected:
    fail(f"unexpected discovery node set: {sorted(set(nodes) ^ expected)}")

# The canonical Tier 1 manifest must agree that these are exactly the unpromoted nodes.
tier_nodes = t.get("nodes")
if not isinstance(tier_nodes, list):
    fail("Tier 1 nodes must be a list")
state_by_id = {n["id"]: n.get("state") for n in tier_nodes}
nonpass = {node for node, state in state_by_id.items() if state != "PASS"}
passed = {node for node, state in state_by_id.items() if state == "PASS"}
if nonpass != expected:
    fail(f"global discovery set != canonical non-PASS Tier 1 set: {sorted(nonpass ^ expected)}")
if len(passed) != 18 or len(nonpass) != 11:
    fail(f"unexpected promoted snapshot PASS={len(passed)} non-PASS={len(nonpass)}")

snapshot = c.get("promoted_snapshot", {})
if snapshot.get("pass") != len(passed) or snapshot.get("pending") != len(nonpass):
    fail("promoted snapshot counts do not match the canonical Tier 1 manifest")

# Ready lane must already have a real runner/package tree. Lane-pending nodes must not be mislabeled FAIL.
ready = {n for n, m in nodes.items() if m["readiness"] == "runnable"}
if ready != {"kcalendarcore", "kcoreaddons", "kwidgetsaddons"}:
    fail(f"unexpected currently runnable set: {sorted(ready)}")
for node in ready:
    if not (ROOT / "packages/kde" / node / "debian/control").is_file():
        fail(f"{node}: runnable but package tree is missing")
if not (ROOT / "scripts/run-kde-tier1-package-batch7-preflight.sh").is_file():
    fail("single-ABI Python lane runner is missing")

kgui = nodes["kguiaddons"]
if kgui["readiness"] != "dependency-blocked" or kgui.get("local_predecessors") != ["kcoreaddons"]:
    fail("KGuiAddons must remain dependency-blocked on the local KCoreAddons PASS")

if lanes["multi-abi"].get("status") != "implementation-pending":
    fail("multi-ABI lane must remain implementation-pending until its runner exists")
if lanes["qml-multisurface"].get("status") != "implementation-pending":
    fail("QML/multisurface lane must remain implementation-pending until its runner exists")
if lanes["multi-surface-optional"].get("status") != "implementation-pending":
    fail("multi-surface/optional lane must remain implementation-pending until its runner exists")

print("KDE Tier 1 global discovery policy: PASS")
print(f"promoted PASS={len(passed)}; discovery nodes={len(nonpass)}; runnable={len(ready)}; lane-pending=7; dependency-blocked=1")

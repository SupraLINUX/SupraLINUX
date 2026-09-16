#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

EXPECTED_HEAD = "411f50dec9a05bb63569ae69589e202d7278f77f"
ATTEMPT_LEDGER = "manifests/kde-tier1-package-batch7-attempts.json"
ECM = "6.30.0-0supralinux3"

PASS = {
    "kcalendarcore": {
        "version": "6.30.0-0supralinux5",
        "run": 35130213945,
        "job": 104909057699,
        "commit": "9b9e313176d5154656274976872feb7be34ab126",
        "artifact": 10461386548,
        "digest": "6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6",
        "rootfs": "eb3e6bfe65b142c1308d8a1892e00c6bd57028126147ac09376778dec60692f6",
        "tests": "507/507 PASS",
        "soname": "libKF6CalendarCore.so.6",
        "source_package": "kf6-kcalendarcore",
        "binary_packages": [
            "libkf6calendarcore-data", "libkf6calendarcore-dev", "libkf6calendarcore-doc",
            "libkf6calendarcore6", "qml6-module-org-kde-calendarcore", "python3-kcalendarcore",
        ],
        "files": {
            "libkf6calendarcore_data_deb_sha256": "a3e14761b6cb3e70cacbdfb17ea7cc410a44db7f440b84973c7bc66abd355578",
            "libkf6calendarcore_dev_deb_sha256": "b91b0fbbc45cbffad59f4b307d4499c3bda1ec10c1d81c6fb91ec4afa5c2c0ea",
            "libkf6calendarcore_doc_deb_sha256": "d29c4d07d687b9b855c56fcfd5d9d7b62d013edc228851adc38f9df62de4dd43",
            "libkf6calendarcore6_deb_sha256": "ce8063e65119b8f8b46efe848519187131878390e302cbe5aaa667ae5862ab17",
            "python3_kcalendarcore_deb_sha256": "d2a21b8ab286eec081a327130eeb48c45fc24be720757b8bf50c581a36a7fb5f",
            "qml6_module_org_kde_calendarcore_deb_sha256": "696e26826a3acc4126cb0536d8c03041f1abbf70f5b2c5b1009eb12a87fb67a0",
            "changes_sha256": "5c3c8b22ca19379ef9c8cfe11b5a381f91c692f3b51de81e5a392b2d01e8fe77",
            "buildinfo_sha256": "42a21961f0df871ccdb1fdf3c40ba1f8d23e5f1c285d7690f357669d35e55478",
            "dsc_sha256": "bc7812c4da1756a00777de3ad4a1d4d8e825803ad62130e17ce58452e282e492",
            "orig_tar_sha256": "e8bf60e398e2f8098a4db7db44c5475d70540ad8f8948a123c8bc109dc4db776",
            "debian_tar_sha256": "d7c71cfedda54211de813ba21be878dce6629a974c25f06299bd41eeac61cf11",
            "rootfs_sha256": "eb3e6bfe65b142c1308d8a1892e00c6bd57028126147ac09376778dec60692f6",
        },
    },
    "kcoreaddons": {
        "version": "6.30.0-0supralinux4",
        "run": 35122522242,
        "job": 104883541991,
        "commit": "ea465e7f78ee621f6456246e7ba76e0a89e46d78",
        "artifact": 10457958023,
        "digest": "c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64",
        "rootfs": "dd7762ba1cdc25dd57b05e8203b3d5d4d448d9ee7131ac0b99d1d85989854794",
        "tests": "34/34 PASS",
        "soname": "libKF6CoreAddons.so.6",
        "source_package": "kf6-kcoreaddons",
        "binary_packages": [
            "libkf6coreaddons-data", "libkf6coreaddons-dev", "libkf6coreaddons-doc",
            "libkf6coreaddons6", "qml6-module-org-kde-coreaddons", "python3-kcoreaddons",
        ],
        "files": {
            "libkf6coreaddons_data_deb_sha256": "f05f55e3c6486af9d3ff48aa38215784bbb347aae1cd5fb760f5513760364908",
            "libkf6coreaddons_dev_deb_sha256": "9f6fa1d04c303a2466322c86b14dee9a301a442a34c26dd77e99440f186c9636",
            "libkf6coreaddons_doc_deb_sha256": "27895f2792f26ed4c0949fecddcf5dc562f5f15f22c939694137b70c917ef2fc",
            "libkf6coreaddons6_deb_sha256": "015b8f19a909a2a7431b45235187f280c32790258052c8c08659e6ce510b11cb",
            "python3_kcoreaddons_deb_sha256": "0aff04f52eb0ad76b3fa2028ab8d04f576059d6a2ec7330d896a1ed8e150460b",
            "qml6_module_org_kde_coreaddons_deb_sha256": "8c6f82ac7c0de500b8bda6c88d912b3fd8cb6b254cece402227d38d1fb782345",
            "changes_sha256": "592ccce875d7288dc2aeae52db429d5de69a84ee047d9ea3188d178de11fe8bb",
            "buildinfo_sha256": "990702d2dd5e71146e8ed82f428aecc0320119a46d203603c320715ed12d9fbb",
            "dsc_sha256": "f4ba7ab929e3be4d122505b4af717c36d36055837d45c628eaacac0371ee5276",
            "orig_tar_sha256": "cc68fe15beb0fca2036cff8742f468c1345406bf99793fffacbf8f2a3f89bc4b",
            "debian_tar_sha256": "7d26791ae9a30406d7d23edd71ee7c470d26961a7df0f1eb4437c071e25b7152",
            "rootfs_sha256": "dd7762ba1cdc25dd57b05e8203b3d5d4d448d9ee7131ac0b99d1d85989854794",
        },
    },
    "kwidgetsaddons": {
        "version": "6.30.0-0supralinux7",
        "run": 35145607543,
        "job": 104960718770,
        "commit": "00be0b419b9f897cf7b7dbc8ca396e20916ead9b",
        "artifact": 10467164025,
        "digest": "f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e",
        "rootfs": "d381a2d238103d21dbce47af60377b48ca77b385ab8598d135d30386ac17cf12",
        "tests": "27/27 PASS",
        "soname": "libKF6WidgetsAddons.so.6",
        "source_package": "kf6-kwidgetsaddons",
        "binary_packages": [
            "libkf6widgetsaddons-data", "libkf6widgetsaddons-dev", "libkf6widgetsaddons-doc",
            "libkf6widgetsaddons6", "python3-kwidgetsaddons",
        ],
        "files": {
            "libkf6widgetsaddons_data_deb_sha256": "c9e7cfe4f8ec0f027a3ecb53383832b4971d88e0c6cd7235de563afbe8cf031f",
            "libkf6widgetsaddons_dev_deb_sha256": "53d6d367a418fe29b8514d5980b219b59c84adb635e7f3f7acded259dea7501b",
            "libkf6widgetsaddons_doc_deb_sha256": "badceb41d9d5eefa0bce370c02c0c2ccc11a8b695427a9f2947dc2c62124e788",
            "libkf6widgetsaddons6_deb_sha256": "9c12483a1cf5afec0e0b645ff541ae6ad93ac4603fa549cdb6c9cb43a873360b",
            "python3_kwidgetsaddons_deb_sha256": "01d95387e01decfea9addda3f65e39ca6eb3481510af0cc3bccbccc068fa305c",
            "libkf6widgetsaddons_dev_dbgsym_ddeb_sha256": "91c1a1076ea2896767a5236200836ef69ce364be713432aff71c27d1311e8f66",
            "libkf6widgetsaddons6_dbgsym_ddeb_sha256": "bbe2e34d3b24ccd8dd2b1e5e73e8b2e65b5e0f9919fb4560ad524c9b0ac98fdc",
            "python3_kwidgetsaddons_dbgsym_ddeb_sha256": "ee3a5fdb873ac4628d7a130ee03a7b24032bddfa582476ca5c87366f897f8bf4",
            "changes_sha256": "9160452f243b6458fdc9106c6f7abdec97ef7bd0d57b56f6e4ea42f86d3fd4ff",
            "buildinfo_sha256": "d6c69420d77524cef57b7caeda685b7223498bb12d9e9f767a9ab50fb43916e8",
            "dsc_sha256": "a93440f813dff86475febfb51b305be3e4fbab7c6dde6e0690b25aa124e9ee0d",
            "orig_tar_sha256": "ab1333c258678caa7562120a1c03bb71779f7232f1a0e75b9525d921dee3e0a3",
            "debian_tar_sha256": "a0022dc8b317e1e36e6304a82db6fd537206f236379836373de6ed00d4a55df6",
            "rootfs_sha256": "d381a2d238103d21dbce47af60377b48ca77b385ab8598d135d30386ac17cf12",
        },
    },
}


def die(msg: str) -> None:
    raise SystemExit(msg)


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        die(f"{path}: expected JSON object")
    return value


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def current_pass_evidence(exp: dict) -> dict:
    return {
        "result": "PASS",
        "workflow_run": exp["run"],
        "job_id": exp["job"],
        "commit": exp["commit"],
        "attempted_package_version": exp["version"],
        "artifact_id": exp["artifact"],
        "artifact_sha256": exp["digest"],
        "stage": "complete",
        "tests": exp["tests"],
        "lintian": "PASS-errors",
        "consumer_smoke": "PASS",
        "python_import": "PASS",
        "apt_check": "PASS",
        "abi_soname": exp["soname"],
        "ecm_predecessor": ECM,
        "downstream_eligible": True,
        "files": exp["files"],
    }


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        die(f"{label}: expected exactly one replacement target, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        die("usage: promote-batch7-canonical.py <canonical-checkout>")
    root = Path(sys.argv[1]).resolve()
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if head != EXPECTED_HEAD:
        die(f"canonical HEAD moved: expected {EXPECTED_HEAD}, got {head}")

    # Canonical Tier 1 manifest: preserve source metadata; promote only packaging state/evidence.
    tier_path = root / "manifests/kde-frameworks-tier1.json"
    tier = load_json(tier_path)
    tier["as_of"] = "2026-09-16"
    by_id = {node["id"]: node for node in tier["nodes"]}
    for node_id, exp in PASS.items():
        node = by_id[node_id]
        if node.get("state") != "pending" or node.get("packaging") != {"state": "pending"}:
            die(f"{node_id}: canonical pre-promotion state drifted")
        node["packaging"] = {
            "state": "PASS",
            "package_version": exp["version"],
            "claim": "hosted-clean-package-preflight",
            "authoritative": False,
            "downstream_eligible": True,
            "attempt_ledger": ATTEMPT_LEDGER,
            "evidence": [current_pass_evidence(exp)],
        }
        node["state"] = "PASS"
    if sum(n.get("state") == "PASS" for n in tier["nodes"]) != 21:
        die("Tier 1 promotion did not produce 21 PASS")
    if sum(n.get("state") == "pending" for n in tier["nodes"]) != 8:
        die("Tier 1 promotion did not produce 8 pending")
    write_json(tier_path, tier)

    # Canonical DAG mirrors the promoted package evidence while retaining source metadata.
    dag_path = root / "manifests/kde-dag.json"
    dag = load_json(dag_path)
    dag["as_of"] = "2026-09-16"
    for node_id, exp in PASS.items():
        node = dag["nodes"][node_id]
        if node.get("state") != "pending":
            die(f"{node_id}: DAG pre-promotion state drifted")
        node.update({
            "package_provider": "supralinux",
            "source_package": exp["source_package"],
            "binary_packages": exp["binary_packages"],
            "package_version": exp["version"],
            "state": "PASS",
            "claim": "hosted-clean-package-preflight",
            "authoritative": False,
            "downstream_eligible": True,
            "attempt_ledger": ATTEMPT_LEDGER,
            "evidence": [{"type": "github-actions-run", **{k: v for k, v in current_pass_evidence(exp).items() if k != "files"}}],
            "pass_files": exp["files"],
        })
    write_json(dag_path, dag)

    # Batch 7 campaign now points at the promoted canonical state.
    campaign_path = root / "manifests/kde-tier1-package-campaign-batch7.json"
    campaign = load_json(campaign_path)
    if campaign.get("state") != "PASS":
        die("Batch 7 technical closure is no longer PASS")
    campaign["canonical_snapshot"] = {
        "state": "canonical-promoted",
        "tier1": "21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED after Batch 7 canonical promotion",
    }
    write_json(campaign_path, campaign)

    # Global discovery now covers exactly the eight unpromoted nodes. KGuiAddons is no longer
    # dependency-blocked, but remains lane-pending until its local-predecessor runner exists.
    discovery_path = root / "manifests/kde-tier1-global-discovery.json"
    discovery = load_json(discovery_path)
    discovery["promoted_snapshot"] = {
        "pass": 21,
        "pending": 8,
        "current_fail": 0,
        "blocked": 0,
        "note": "Promoted DAG state only. Historical failed package attempts remain retained separately and do not become promoted FAIL after a later PASS.",
    }
    for node_id in PASS:
        discovery["nodes"].pop(node_id, None)
    discovery["lanes"]["single-abi-python"]["status"] = "completed"
    discovery["lanes"]["single-abi-python"]["nodes"] = []
    kgui = discovery["nodes"]["kguiaddons"]
    kgui["readiness"] = "lane-pending"
    kgui["lane"] = "local-predecessor"
    kgui["local_predecessors"] = ["kcoreaddons"]
    discovery["lanes"]["local-predecessor"]["status"] = "implementation-pending"
    discovery["next_actions"] = [
        "implement the KGuiAddons local-predecessor lane and consume only the retained SupraLINUX KCoreAddons PASS artifacts",
        "implement the multi-ABI package lane and attempt kconfig, ki18n and sonnet in parallel",
        "implement QML/multisurface and optional-feature lanes, then attempt every newly runnable independent node",
        "retain DIAG_PASS as non-promoting discovery evidence; only package PASS may feed dependents",
        "aggregate real package failures by root cause and repeat the complete runnable campaign after remediation sets",
    ]
    write_json(discovery_path, discovery)

    # Tier 1 validator: add the three retained PASS contracts and update promoted counts.
    v_path = root / "scripts/validate_kde_tier1.py"
    text = v_path.read_text()
    if "'kcalendarcore': {'version':'6.30.0-0supralinux5'" in text:
        die("Tier 1 validator already contains Batch 7 promotion")
    marker = "}\nEXPECTED_PROVIDER_PREVIOUS_EVIDENCE"
    if text.count(marker) != 1:
        die("cannot locate EXPECTED_PASS closing marker")
    additions = """    'kcalendarcore': {'version':'6.30.0-0supralinux5','run':35130213945,'job':104909057699,'artifact':10461386548,'digest':'6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6','tests':'507/507 PASS','soname':'libKF6CalendarCore.so.6'},\n    'kcoreaddons': {'version':'6.30.0-0supralinux4','run':35122522242,'job':104883541991,'artifact':10457958023,'digest':'c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64','tests':'34/34 PASS','soname':'libKF6CoreAddons.so.6'},\n    'kwidgetsaddons': {'version':'6.30.0-0supralinux7','run':35145607543,'job':104960718770,'artifact':10467164025,'digest':'f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e','tests':'27/27 PASS','soname':'libKF6WidgetsAddons.so.6'},\n"""
    text = text.replace(marker, additions + marker, 1)
    text = replace_once(text,
        "require(sum(1 for n in nodes if n.get('state') == 'PASS') == 18, 'Tier 1 current PASS count must be 18')",
        "require(sum(1 for n in nodes if n.get('state') == 'PASS') == 21, 'Tier 1 current PASS count must be 21')",
        "Tier1 PASS count")
    text = replace_once(text,
        "require(sum(1 for n in nodes if n.get('state') == 'pending') == 11, 'Tier 1 current pending count must be 11')",
        "require(sum(1 for n in nodes if n.get('state') == 'pending') == 8, 'Tier 1 current pending count must be 8')",
        "Tier1 pending count")
    text = text.replace("after Batch 6 closure", "after Batch 7 closure")
    text = replace_once(text,
        "print('Tier 1 package states: 18 PASS/downstream-eligible; 11 pending; 0 FAIL; 0 BLOCKED')",
        "print('Tier 1 package states: 21 PASS/downstream-eligible; 8 pending; 0 FAIL; 0 BLOCKED')",
        "Tier1 final summary")
    v_path.write_text(text)

    # Batch 7 validator must now require promoted canonical state.
    b7v = root / "scripts/validate_kde_tier1_package_batch7.py"
    text = b7v.read_text()
    old = '''if m.get("canonical_snapshot") != {\n    "state": "technical-closure-awaiting-canonical-promotion",\n    "tier1": "18 PASS / 11 pending in canonical manifest; all three Batch 7 nodes have retained PASS evidence and are ready for atomic canonical promotion",\n}:\n    fail("Batch 7 pre-promotion canonical snapshot mismatch")'''
    new = '''if m.get("canonical_snapshot") != {\n    "state": "canonical-promoted",\n    "tier1": "21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED after Batch 7 canonical promotion",\n}:\n    fail("Batch 7 canonical promotion snapshot mismatch")'''
    text = replace_once(text, old, new, "Batch7 snapshot validator")
    text = replace_once(text,
        'print("Canonical Tier 1 promotion remains a separate atomic state update: currently 18 PASS / 11 pending")',
        'print("Canonical Tier 1 state after Batch 7: 21 PASS / 8 pending / 0 FAIL / 0 BLOCKED")',
        "Batch7 validator summary")
    b7v.write_text(text)

    # Rewrite global-discovery validator around the post-promotion frontier.
    gdv = root / "scripts/validate_kde_tier1_global_discovery.py"
    gdv.write_text('''#!/usr/bin/env python3\nimport json\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nCAMPAIGN = ROOT / "manifests/kde-tier1-global-discovery.json"\nTIER1 = ROOT / "manifests/kde-frameworks-tier1.json"\n\ndef fail(message: str) -> None:\n    raise SystemExit(message)\n\ndef load(path: Path):\n    try:\n        return json.loads(path.read_text())\n    except Exception as exc:\n        fail(f"cannot parse {path.relative_to(ROOT)}: {exc}")\n\nc = load(CAMPAIGN)\nt = load(TIER1)\nif c.get("schema") != 1 or c.get("strategy") != "dag-global-discovery":\n    fail("global discovery identity mismatch")\nif c.get("authority") != "kde-upstream" or c.get("provider_platform") != "ubuntu-resolute":\n    fail("authority/provider separation regressed")\nrequired_policy = {\n    "build_every_runnable_node_per_topological_level": True,\n    "parallelize_independent_nodes": True,\n    "fail_fast": False,\n    "continue_after_independent_failures": True,\n    "blocked_is_not_fail": True,\n    "only_pass_artifacts_feed_dependents": True,\n    "preserve_every_real_attempt": True,\n    "rerun_affected_nodes_after_remediation": True,\n    "repeat_full_campaign_after_remediation_set": True,\n}\nif c.get("policy") != required_policy:\n    fail("global discovery policy changed")\nnodes = c.get("nodes", {})\nlanes = c.get("lanes", {})\nexpected = {"kconfig", "ki18n", "sonnet", "kirigami", "kquickcharts", "kuserfeedback", "prison", "kguiaddons"}\nif set(nodes) != expected:\n    fail(f"unexpected post-Batch7 discovery set: {sorted(set(nodes) ^ expected)}")\nallowed = {"runnable", "lane-pending", "dependency-blocked"}\nfor node, meta in nodes.items():\n    if meta.get("readiness") not in allowed:\n        fail(f"{node}: invalid readiness")\n    lane = meta.get("lane")\n    if lane not in lanes or node not in lanes[lane].get("nodes", []):\n        fail(f"{node}: lane membership mismatch")\nlane_members = [n for meta in lanes.values() for n in meta.get("nodes", [])]\nif len(lane_members) != len(set(lane_members)) or set(lane_members) != expected:\n    fail("lane membership must cover each discovery node exactly once")\ntier_nodes = t.get("nodes", [])\nstate_by_id = {n["id"]: n.get("state") for n in tier_nodes}\nnonpass = {n for n, state in state_by_id.items() if state != "PASS"}\npassed = {n for n, state in state_by_id.items() if state == "PASS"}\nif nonpass != expected or len(passed) != 21 or len(nonpass) != 8:\n    fail(f"canonical promotion mismatch PASS={len(passed)} non-PASS={len(nonpass)}")\nsnapshot = c.get("promoted_snapshot", {})\nif snapshot.get("pass") != 21 or snapshot.get("pending") != 8 or snapshot.get("current_fail") != 0 or snapshot.get("blocked") != 0:\n    fail("promoted snapshot mismatch")\nready = {n for n, m in nodes.items() if m["readiness"] == "runnable"}\nblocked = {n for n, m in nodes.items() if m["readiness"] == "dependency-blocked"}\nlane_pending = {n for n, m in nodes.items() if m["readiness"] == "lane-pending"}\nif ready:\n    fail(f"no package lane is runnable immediately after canonical promotion: {sorted(ready)}")\nif blocked:\n    fail(f"no discovery node should remain dependency-blocked after KCoreAddons PASS: {sorted(blocked)}")\nif lane_pending != expected:\n    fail("all eight remaining nodes must be lane-pending until their package runners exist")\nkgui = nodes["kguiaddons"]\nif kgui.get("local_predecessors") != ["kcoreaddons"] or kgui.get("lane") != "local-predecessor":\n    fail("KGuiAddons must retain its local KCoreAddons predecessor contract")\nif lanes["local-predecessor"].get("status") != "implementation-pending":\n    fail("KGuiAddons lane must remain implementation-pending until its runner exists")\nif lanes["single-abi-python"].get("status") != "completed" or lanes["single-abi-python"].get("nodes") != []:\n    fail("Batch 7 single-ABI Python lane must be closed after promotion")\nfor lane in ("multi-abi", "qml-multisurface", "multi-surface-optional"):\n    if lanes[lane].get("status") != "implementation-pending":\n        fail(f"{lane}: must remain implementation-pending")\nprint("KDE Tier 1 global discovery policy: PASS")\nprint("promoted PASS=21; discovery nodes=8; runnable=0; lane-pending=8; dependency-blocked=0")\n''')

    # Documentation: keep the Batch 6 historical closure marker and distinguish it from current state.
    dep_doc = root / "docs/kde-tier1-dependencies.md"
    text = dep_doc.read_text()
    text = replace_once(text,
        "Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping validated; canonical Tier 1 still 18 PASS / 11 pending; Batch 7 is technically 3/3 PASS awaiting atomic canonical promotion**",
        "Status: **upstream dependency metadata resolved; Ubuntu Resolute provider mapping validated; canonical Tier 1 21 PASS / 8 pending after Batch 7 promotion**",
        "dependency doc status")
    text = replace_once(text,
        "- canonical Tier 1 package state: **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**;\n- Batch 7 retained package evidence: **3/3 PASS, awaiting atomic canonical promotion**;\n- KGuiAddons: next local-predecessor lane after KCoreAddons canonical promotion;",
        "- canonical Tier 1 package state: **21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED**;\n- Batch 7 retained package evidence: **3/3 PASS and canonically promoted**;\n- KGuiAddons: predecessor satisfied; local-predecessor package lane implementation is the next step;",
        "dependency doc current state")
    text = text.replace("Batch 7 is now technically **3/3 PASS** while canonical promotion remains a separate atomic state update:", "Batch 7 is **3/3 PASS and canonically promoted**:")
    dep_doc.write_text(text)

    dag_doc = root / "docs/kde-dag.md"
    text = dag_doc.read_text()
    text = replace_once(text,
        "Status: **ECM root PASS; 18 Frameworks Tier 1 PASS; 11 Tier 1 pending; 0 current FAIL; 0 BLOCKED**",
        "Status: **ECM root PASS; 21 Frameworks Tier 1 PASS; 8 Tier 1 pending; 0 current FAIL; 0 BLOCKED**",
        "DAG doc status")
    if "### Batch 7 — 3/3 PASS" not in text:
        text += '''\n\n### Batch 7 — 3/3 PASS\n\nCanonical promotion completed on 2026-09-16.\n\n- KCalendarCore `6.30.0-0supralinux5`: run `35130213945`, job `104909057699`, artifact `10461386548`, 507/507 tests PASS.\n- KCoreAddons `6.30.0-0supralinux4`: run `35122522242`, job `104883541991`, artifact `10457958023`, 34/34 tests PASS.\n- KWidgetsAddons `6.30.0-0supralinux7`: run `35145607543`, job `104960718770`, artifact `10467164025`, 27/27 tests PASS.\n\nAll three pass Lintian, exact APT runtime closure and consumer smoke; Python imports pass for their enabled bindings. Historical FAIL attempts remain retained in `manifests/kde-tier1-package-batch7-attempts.json`. Canonical Tier 1 is **21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED**. KGuiAddons is no longer predecessor-blocked; its local-predecessor package runner remains to be implemented.\n'''
    dag_doc.write_text(text)

    batch_doc = root / "docs/kde-tier1-package-batch7.md"
    batch_doc.write_text('''# KDE Frameworks 6.30 Tier 1 — package Batch 7\n\nStatus: **3/3 PASS; canonical promotion complete**\n\nCanonical Tier 1 after promotion: **21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED**. Historical FAIL attempts remain immutable in `manifests/kde-tier1-package-batch7-attempts.json`; they are not BLOCKED and are not erased by later PASS results.\n\n## Final retained PASS\n\n- **KCalendarCore `6.30.0-0supralinux5`** — run `35130213945`, job `104909057699`, artifact `10461386548`, artifact SHA-256 `6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6`, rootfs `eb3e6bfe65b142c1308d8a1892e00c6bd57028126147ac09376778dec60692f6`, 507/507 tests PASS.\n- **KCoreAddons `6.30.0-0supralinux4`** — run `35122522242`, job `104883541991`, artifact `10457958023`, artifact SHA-256 `c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`, rootfs `dd7762ba1cdc25dd57b05e8203b3d5d4d448d9ee7131ac0b99d1d85989854794`, 34/34 tests PASS.\n- **KWidgetsAddons `6.30.0-0supralinux7`** — run `35145607543`, job `104960718770`, artifact `10467164025`, artifact SHA-256 `f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e`, rootfs `d381a2d238103d21dbce47af60377b48ca77b385ab8598d135d30386ac17cf12`, 27/27 tests PASS.\n\nEvery final PASS completed strict Lintian error gating, exact local-package APT closure, Python import for enabled bindings and C++ consumer smoke. KWidgetsAddons retained all upstream tests and its Designer plugin; its deterministic test fixture runs 25 suites under bare Xvfb and only the two activation-dependent gesture suites under verified Openbox.\n\n## Shared causes resolved\n\nThe campaign discovered and validated the clean-build providers required by ECM/Shiboken: Clang/LLVM built-ins plus `python3-build` and `python3-setuptools`. Package-specific remediations then handled KCalendarCore translation ownership/ABI minima, KCoreAddons ABI minima, and KWidgetsAddons deterministic GUI-test fixture, Designer-plugin `${shlibs:Depends}` and reviewed ABI minima. KDE source and selected upstream defaults remain unchanged.\n\n## Next frontier\n\nKGuiAddons is no longer blocked by KCoreAddons: the predecessor has a retained SupraLINUX PASS. It remains `lane-pending` until the local-predecessor runner is implemented; that runner must consume the SupraLINUX KCoreAddons artifacts rather than Ubuntu KDE packages.\n\nPR #1 remains **OPEN + DRAFT**. No merge is authorized.\n''')

    status_doc = root / "docs/status/2026-09-16-batch7.md"
    status_doc.write_text('''# KDE Frameworks Tier 1 Batch 7 — 2026-09-16\n\nStatus: **CLOSED — 3/3 PASS and canonically promoted**\n\nCanonical Tier 1: **21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED**.\n\nFinal retained results:\n\n- KCalendarCore `6.30.0-0supralinux5`: run `35130213945`, job `104909057699`, artifact `10461386548`, SHA-256 `6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6`, 507/507 tests PASS.\n- KCoreAddons `6.30.0-0supralinux4`: run `35122522242`, job `104883541991`, artifact `10457958023`, SHA-256 `c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64`, 34/34 tests PASS.\n- KWidgetsAddons `6.30.0-0supralinux7`: run `35145607543`, job `104960718770`, artifact `10467164025`, SHA-256 `f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e`, 27/27 tests PASS.\n\nAll final revisions pass Lintian, Python import where enabled, exact APT closure and consumer smoke. Historical real FAIL attempts are preserved in the immutable Batch 7 attempt ledger.\n\nGlobal source diagnostic remains **7 DIAG_PASS / 0 DIAG_FAIL** and is non-promoting. KGuiAddons is predecessor-unblocked but remains lane-pending until its local-predecessor package runner exists.\n\nPR #1 remains **OPEN + DRAFT**. No merge is authorized.\n''')

    promo_status = root / "docs/status/2026-09-16-batch7-promotion.md"
    promo_status.write_text('''# Batch 7 canonical promotion — 2026-09-16\n\nState: **promotion commit prepared and locally validated by the one-shot tooling workflow**.\n\nThe promotion moves KCalendarCore, KCoreAddons and KWidgetsAddons from canonical `pending` to `PASS` using only retained real package evidence. It changes no KDE source, package tree, build runner or workflow.\n\nExpected canonical snapshot after the promotion commit: **21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED**.\n\nA normal PR synchronization commit will re-run Repository Policy after this promotion so the final branch state has ordinary CI evidence.\n''')

    # Guard against accidentally changing the historical Batch 6 closure statement.
    dep_now = dep_doc.read_text()
    if "<!-- BATCH6-CANONICAL-CLOSURE -->" not in dep_now or "Batch 6 closure is **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**" not in dep_now:
        die("Batch 6 historical closure marker/state was not preserved")

    print("Batch 7 canonical promotion transform: PASS")
    print("Tier1=21 PASS/8 pending; KGuiAddons predecessor-unblocked but lane-pending")


if __name__ == "__main__":
    main()

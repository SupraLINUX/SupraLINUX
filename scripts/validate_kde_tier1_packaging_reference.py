#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1.json"
REFERENCE_MANIFEST = ROOT / "manifests" / "kde-frameworks-tier1-packaging-reference.json"
SCOPE = ROOT / "scripts" / "kde-tier1-packaging-reference-needed.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "kde-tier1-packaging-reference.yml"

EXPECTED_SNAPSHOT = {
    "status": "PASS",
    "claim": "packaging-reference-snapshot-only",
    "authoritative": False,
    "workflow_run": 34701132721,
    "head_sha": "943a99f7465e311bbc72d63cbe6555a29aa4b5ab",
    "artifact_id": 10299579234,
    "artifact_sha256": "a2951c297f125ad81d1487075f0a0a6250114c4e875f3ba3870c3c18c09adaca",
    "snapshot_json_sha256": "601c668342c206af179e9c564bf87cac6a166f1070fe9af0b640cb57d2151597",
    "versions_tsv_sha256": "af6fd90121801eaf322442c43b793422494dfd5a109edccf484f5d24b463ea9b",
    "nodes": 29,
    "ubuntu_reference_upstream_versions": ["6.23.0", "6.24.0"],
    "debian_reference_upstream_versions": ["6.28.0", "6.28.1"],
    "framework_package_build_certification": "pending",
}
EXPECTED_BINARY_CONTRACT_SNAPSHOT = {
    "status": "PASS",
    "claim": "binary-packaging-contract-reference-only",
    "authoritative": False,
    "workflow_run": 34704117024,
    "head_sha": "be7a53c34a7ac27065f848ea3abc14b867673bde",
    "artifact_id": 10301282501,
    "artifact_sha256": "9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97",
    "binary_query_plan_sha256": "b26c95d381db242c3c7a87228044a37bac8696e211358149a08bb5b55f411bb9",
    "binary_contracts_json_sha256": "e44507d0dd73db913a91bd4852c452f783618aab0bd6a3790e4c4f4c40707b7b",
    "binary_contracts_tsv_sha256": "ef29ecdf03a35616a7cd0155a54a0d93828ff2af9bd9a3dcba37c0dbdb8bb1ca",
    "ubuntu_binary_packages": 147,
    "debian_binary_packages": 151,
    "common_binary_packages": 147,
    "ubuntu_only_binary_packages": 0,
    "debian_only_binary_packages": 4,
    "debian_only_packages": ["libkirigamiforms6", "libkirigamiformsprivatecards6", "libkirigamiformsprivateflat6", "libkirigamiformsprivatetemplates6"],
    "framework_package_build_certification": "pending",
}
PASS_NODES = {
    "attica": ("6.30.0-0supralinux2", 34706416753, 10301851297, "f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27"),
    "kcodecs": ("6.30.0-0supralinux4", 34716761551, 10305050385, "d83b29f7ee32e4f170d15bd9f36caa643ab3a0a7b357496071d198e8b366fe45"),
    "kdbusaddons": ("6.30.0-0supralinux3", 34713034164, 10304340428, "2bfb451724808b5318625eee3df25a6104c9b6da77482737ac54eea058a7e799"),
    "threadweaver": ("6.30.0-0supralinux3", 34713034164, 10303986419, "6395f11ed633fb034b0bf61a95639ce00005e3211994b04924abeb306deed2b8"),
    "ktexttemplate": ("6.30.0-0supralinux3", 34884764702, 10363863115, "7b9d0390ed90c882f4b7ad1993924e722bfb7ad35238c2ced52bbd5809555bc9"),
    "karchive": ("6.30.0-0supralinux4", 34884764702, 10364726750, "0fcd8722eddf40995152df200aa576a3ff1234b8135c52e59a66f05dbc8eeb3e"),
    "kholidays": ("6.30.0-0supralinux4", 34884764702, 10364169061, "62186f3d6d0c856fed7b055ae917ceec0b6cdf216b37b93e22126bf3ebc8f37a"),
    "kitemmodels": ("6.30.0-0supralinux1", 34896417969, 10369501432, "b806eaf27f733c1a2b5cc1d108ca442fef673b6dc0a53cfc5fff38abd2bf6732"),
    "bluez-qt": ("6.30.0-0supralinux2", 34945979836, 10387429776, "db8a3718a31eaae00d5f9fbdb60014dfeb1faf1c2bc84a88f9ab0d9bffec07ed"),
    "kplotting": ("6.30.0-0supralinux1", 34896417969, 10369086459, "f4c4f7425e582b5001fdffced34d045dc46152074422bd2bcf994e544bb96bb8"),
    "kitemviews": ("6.30.0-0supralinux1", 34999449194, 10409267184, "7e34fa7ede21510cf6829448e7b45a5c2832aaf9ac2719b9cb4125d23b593e55"),
    "kglobalaccel": ("6.30.0-0supralinux2", 35006477086, 10412320520, "cb8143633cf15745a235937ea55ee096cb094cc96da3bd1fc39dc914f3acb3b1"),
    "syntax-highlighting": ("6.30.0-0supralinux2", 35006477086, 10411888269, "1ec0d1e7d046b1393fbb299c9a6fec7e85ee4ac59ed5deafa0c777ead67c0b5f"),
    "kidletime": ("6.30.0-0supralinux1", 35014875475, 10414598079, "272ccad537d21905cf75a1add74e937d176c20c05c38bf967226fef4ab28b605"),
    "modemmanager-qt": ("6.30.0-0supralinux3", 35021323444, 10417683848, "42d4f804effc6e4b9148e8c01887bdce6f95f0554ac4d03295e844a861a54eb7"),
    "networkmanager-qt": ("6.30.0-0supralinux1", 35014875475, 10414714325, "abf927b5749b34094d2b5ee530831f64638ba116a83e8b82f925a758aa018ad4"),
    "kwindowsystem": ("6.30.0-0supralinux4", 35047623320, 10428130399, "9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272"),
    "solid": ("6.30.0-0supralinux2", 35047623320, 10427653865, "cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389"),
    "kcalendarcore": ("6.30.0-0supralinux5", 35130213945, 10461386548, "6f191cad05620093d9e97e1df3fec78d82e9f9df74270ba8a6bc6b328c61e2f6"),
    "kcoreaddons": ("6.30.0-0supralinux4", 35122522242, 10457958023, "c90bb487aec031e71f49a7caaf8483002eb1e07dacf1642bcf1c9fd811473e64"),
    "kwidgetsaddons": ("6.30.0-0supralinux7", 35145607543, 10467164025, "f40e8ed941fb603578e9ad6a0b82f652f05d9035975352a4edb601fda9100c3e"),
    "kguiaddons": ("6.30.0-0supralinux2", 35185562846, 10482007092, "71d32ecb50f6617ba198325a552e68e995c20c9050c7ae21f6a69d5b680184ca"),
    "kconfig": ("6.30.0-0supralinux4", 35360530830, 10554715051, "bd36a8288c1c36fa2ae1a83d685a816cc1077fc576b59a23951972ddcbdd835e"),
    "ki18n": ("6.30.0-0supralinux1", 35358920602, 10553916882, "2a0d66f2760c49ba1128b8b51c741173a72e6f3ab51f3eb17c3584896d30a678"),
    "sonnet": ("6.30.0-0supralinux3", 35358920602, 10554216487, "ae5a33cf8699b96b7b7b8c1a83bc4d37a484878029818c1885b4f4f44f15b431"),
    "kirigami": ("6.30.0-0supralinux2", 35398956698, 10569258322, "6a008366edda84f8c285e5cf0a6b18a4b1089fc88e530d6e61b0f4f885dd7e30"),
    "kquickcharts": ("6.30.0-0supralinux4", 35409521636, 10573605864, "dc233607ea647780580405b49e8b12855af5aaaf3b2d2bfea50c75fe7ed91780"),
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

source = load(SOURCE_MANIFEST)
reference = load(REFERENCE_MANIFEST)
scope = read(SCOPE)
workflow = read(WORKFLOW)
source_nodes = source.get("nodes", [])
require(source.get("frameworks_series") == "6.30.0", "Packaging reference must follow Frameworks 6.30.0")
require(isinstance(source_nodes, list) and len(source_nodes) == 29, "Packaging reference requires the fixed 29-node Tier 1 set")
source_ids = {node.get("id") for node in source_nodes if isinstance(node, dict)}
require(len(source_ids) == 29 and None not in source_ids, "Tier 1 source node IDs are incomplete")
require(reference.get("schema") == 1, "Packaging-reference schema must be 1")
require(reference.get("authority") is False, "Packaging references must never be authoritative")
require(reference.get("role") == "packaging-reference-only", "Packaging-reference role changed unexpectedly")
require(reference.get("selected_kde") == "6.30.0", "Packaging reference must follow selected KDE 6.30.0")
require(reference.get("snapshot") == EXPECTED_SNAPSHOT, "Packaging-reference PASS evidence changed without review")
require(reference.get("binary_contract_snapshot") == EXPECTED_BINARY_CONTRACT_SNAPSHOT, "Binary-contract PASS evidence changed without review")
references = reference.get("references", {})
require(references.get("ubuntu", {}).get("distribution") == "ubuntu", "Ubuntu reference distribution missing")
require(references.get("ubuntu", {}).get("series") == "resolute", "Ubuntu reference must be Resolute")
require(references.get("ubuntu", {}).get("components") == ["main", "universe"], "Ubuntu reference components changed")
require(references.get("debian", {}).get("distribution") == "debian", "Debian reference distribution missing")
require(references.get("debian", {}).get("series") == "sid", "Debian reference must be sid")
require(references.get("debian", {}).get("components") == ["main"], "Debian reference components changed")
policy = reference.get("policy", {})
for key in ("kde_upstream_remains_authority","reference_packaging_may_not_disable_upstream_defaults_without_documented_reason","reference_versions_do_not_select_kde_version","reference_binary_names_are_inputs_for_compatibility_review_not_automatic_decisions"):
    require(policy.get(key) is True, f"Packaging reference policy must keep {key}=true")
nodes = reference.get("nodes", {})
require(set(nodes) == source_ids, "Packaging-reference node set must exactly match Tier 1")
for node_id in sorted(source_ids):
    require(nodes.get(node_id) == {"source_package": f"kf6-{node_id}"}, f"{node_id}: source package mapping changed")
for node in source_nodes:
    if not isinstance(node, dict):
        continue
    node_id = node.get("id")
    if node_id in PASS_NODES:
        version, run, artifact, digest = PASS_NODES[node_id]
        packaging = node.get("packaging", {})
        require(node.get("state") == "PASS", f"{node_id}: actual package PASS must remain intact")
        require(packaging.get("state") == "PASS", f"{node_id}: packaging PASS must remain intact")
        require(packaging.get("package_version") == version, f"{node_id}: validated revision mismatch")
        require(packaging.get("downstream_eligible") is True, f"{node_id}: PASS must remain downstream eligible")
        passes = [item for item in packaging.get("evidence", []) if isinstance(item, dict) and item.get("result") == "PASS"]
        current_passes = [item for item in passes if item.get("workflow_run") == run and item.get("artifact_id") == artifact]
        require(len(current_passes) == 1, f"{node_id}: exactly one current PASS matching expected run/artifact required")
        if current_passes:
            require(current_passes[0].get("workflow_run") == run, f"{node_id}: PASS run mismatch")
            require(current_passes[0].get("artifact_id") == artifact, f"{node_id}: PASS artifact mismatch")
            require(current_passes[0].get("artifact_sha256") == digest, f"{node_id}: PASS digest mismatch")
    else:
        require(node.get("packaging") == {"state":"pending"}, f"{node_id}: unattempted packaging must remain pending")
        require(node.get("state") == "pending", f"{node_id}: unattempted node must remain pending")
require(sum(1 for node in source_nodes if node.get("state") == "PASS") == 29, "Reference validator expects 29 actual package PASS nodes")
require(sum(1 for node in source_nodes if node.get("state") == "pending") == 0, "Reference validator expects 0 pending nodes")
for token in ("manifests/kde-frameworks-tier1.json","manifests/kde-frameworks-tier1-packaging-reference.json","scripts/run-kde-tier1-packaging-reference-snapshot.sh","scripts/kde-tier1-packaging-reference-needed.sh",".github/workflows/kde-tier1-packaging-reference.yml"):
    require(token in scope, f"Packaging-reference scope must track input {token}")
require("docs/" not in scope, "Packaging-reference snapshot must not rerun for documentation-only changes")
require("validate_kde_tier1_packaging_reference.py" not in scope, "Packaging-reference snapshot must not rerun for validator-only changes")
require('git diff --name-only "${BEFORE}" "${AFTER}" --' in scope, "Packaging-reference scope must compare exact event delta")
for token in ("fetch-depth: 0","github.event.before","github.event.after","github.event.pull_request.base.sha","github.event.pull_request.head.sha","scripts/kde-tier1-packaging-reference-needed.sh","steps.scope.outputs.run == 'true'","steps.scope.outputs.run == 'false'"):
    require(token in workflow, f"Packaging-reference workflow missing event-delta invariant: {token}")
require("paths:" not in workflow, "Packaging-reference workflow must not rely on PR-wide paths filtering")
if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)
print("KDE Frameworks Tier 1 packaging-reference policy: PASS")
print("Reference snapshots remain non-authoritative technical inputs")
print("Actual package states: 29 PASS; 0 pending")

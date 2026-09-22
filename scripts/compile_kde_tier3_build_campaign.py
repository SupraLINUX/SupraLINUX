#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "manifests/kde-frameworks-tier3.json"
DEPENDENCIES = ROOT / "manifests/kde-frameworks-tier3-dependencies.json"
MATERIALIZATION = ROOT / "manifests/kde-tier3-materialization.json"
CONTRACTS = ROOT / "manifests/kde-tier3-package-contracts.json"
DAG = ROOT / "manifests/kde-dag.json"
SUPPORT0 = ROOT / "manifests/kde-tier3-support-build-level0.json"
SUPPORT1 = ROOT / "manifests/kde-tier3-support-build-level1.json"
PLAN = ROOT / "manifests/kde-tier3-build-campaign.json"


def load(path: Path):
    return json.loads(path.read_text())


def uniq(values):
    return list(dict.fromkeys(values))


def pass_record(dag: dict, node_id: str) -> dict:
    node = dag.get("nodes", {}).get(node_id)
    if not node or node.get("state") != "PASS":
        raise ValueError(f"{node_id}: retained predecessor is not PASS")
    if node_id != "extra-cmake-modules" and node.get("downstream_eligible") is not True:
        raise ValueError(f"{node_id}: retained predecessor is not downstream-eligible")

    evidence = None
    for item in reversed(node.get("evidence", [])):
        if item.get("result") != "PASS":
            continue
        if node_id != "extra-cmake-modules" and item.get("downstream_eligible") is not True:
            continue
        evidence = item
        break
    if evidence is None:
        raise ValueError(f"{node_id}: retained PASS evidence missing")

    artifact_id = evidence.get("artifact_id")
    artifact_sha256 = evidence.get("artifact_sha256")
    if not isinstance(artifact_id, int):
        raise ValueError(f"{node_id}: retained artifact id missing")
    if not isinstance(artifact_sha256, str) or len(artifact_sha256) != 64:
        raise ValueError(f"{node_id}: retained artifact SHA-256 missing")

    return {
        "version": node.get("package_version"),
        "workflow_run": evidence.get("workflow_run", evidence.get("run_id")),
        "artifact_id": artifact_id,
        "artifact_sha256": artifact_sha256,
    }


def support_record(node: dict) -> dict:
    evidence = node.get("pass_evidence", {})
    if node.get("state") != "PASS" or node.get("downstream_eligible") is not True:
        raise ValueError("support predecessor is not PASS/downstream-eligible")
    if evidence.get("result") != "PASS" or evidence.get("downstream_eligible") is not True:
        raise ValueError("support predecessor PASS evidence missing")
    return {
        "version": node.get("package_version"),
        "workflow_run": evidence.get("workflow_run"),
        "artifact_id": evidence.get("artifact_id"),
        "artifact_sha256": evidence.get("artifact_sha256"),
    }


def compile_plan() -> dict:
    canonical = load(CANONICAL)
    deps = load(DEPENDENCIES)
    materialization = load(MATERIALIZATION)
    contracts = load(CONTRACTS)
    dag = load(DAG)
    support0 = load(SUPPORT0)
    support1 = load(SUPPORT1)

    if materialization.get("state") != "PASS":
        raise ValueError("Tier 3 materialization must be PASS before build planning")
    if contracts.get("state") != "materialized":
        raise ValueError("Tier 3 package contracts must be materialized before build planning")
    if deps.get("topology", {}).get("acyclic") is not True:
        raise ValueError("Tier 3 dependency graph is not acyclic")

    selected = list(materialization.get("selected_nodes", []))
    if len(selected) != 20:
        raise ValueError("Tier 3 build plan requires exactly 20 materialized nodes")
    selected_set = set(selected)

    canonical_nodes = {node["id"]: node for node in canonical.get("nodes", [])}
    if set(canonical_nodes) != selected_set:
        raise ValueError("Tier 3 canonical/materialization node set mismatch")

    levels = deps.get("topology", {}).get("build_and_test_levels", [])
    flat_levels = [node for level in levels for node in level]
    if len(levels) != 4 or len(flat_levels) != 20 or set(flat_levels) != selected_set:
        raise ValueError("Tier 3 topology must contain the canonical 4-level/20-node build-and-test DAG")

    level_by = {}
    for level_no, level_nodes in enumerate(levels):
        for node_id in level_nodes:
            if node_id in level_by:
                raise ValueError(f"{node_id}: appears in multiple build levels")
            level_by[node_id] = level_no

    retained_ids = set()
    nodes = {}
    for node_id in selected:
        dep = deps["nodes"][node_id]
        fw = dep.get("frameworks", {})
        edges = dep.get("tier3_edges", {})

        blocking = uniq(
            list(edges.get("build_required", []))
            + list(edges.get("selected_profile", []))
            + list(edges.get("qml_required", []))
            + list(edges.get("test_required", []))
        )
        for predecessor in blocking:
            if predecessor not in selected_set:
                raise ValueError(f"{node_id}: Tier 3 blocking edge points outside Tier 3: {predecessor}")
            if level_by[predecessor] >= level_by[node_id]:
                raise ValueError(f"{node_id}: non-topological blocking predecessor {predecessor}")

        build_inputs = uniq(
            list(fw.get("source_required", []))
            + list(fw.get("selected_linux_profile", []))
            + list(fw.get("qml_required", []))
            + list(fw.get("test_required", []))
        )
        external_build = [
            item for item in build_inputs
            if item not in selected_set and item in dag.get("nodes", {})
        ]
        runtime_external = [
            item for item in uniq(list(fw.get("runtime_required", [])))
            if item not in selected_set and item in dag.get("nodes", {})
        ]
        retained_ids.update(external_build)
        retained_ids.update(runtime_external)

        contract = contracts["nodes"][node_id]
        mat = materialization["nodes"][node_id]
        evidence = mat.get("evidence", {})
        if mat.get("state") != "materialized" or evidence.get("result") != "PASS":
            raise ValueError(f"{node_id}: materialization PASS evidence missing")

        deferred = list(edges.get("runtime_validation", []))
        nodes[node_id] = {
            "level": level_by[node_id],
            "state": "planned",
            "source_package": contract.get("source_package"),
            "package_version": contract.get("package_version_candidate"),
            "expected_binary_packages": contract.get("target_binary_packages", []),
            "materialization": {
                "workflow_run": evidence.get("workflow_run"),
                "job_id": evidence.get("job_id"),
                "artifact_id": evidence.get("artifact_id"),
                "artifact_sha256": evidence.get("artifact_sha256"),
            },
            "blocking_predecessors": blocking,
            "edge_classes": {
                "build_required": list(edges.get("build_required", [])),
                "selected_profile": list(edges.get("selected_profile", [])),
                "qml_required": list(edges.get("qml_required", [])),
                "test_required": list(edges.get("test_required", [])),
                "runtime_validation": deferred,
            },
            "external_build_inputs": external_build,
            "external_runtime_inputs": runtime_external,
            "deferred_runtime_validation": deferred,
            "canonical_success_transition": (
                "pending/runtime-validation-required" if deferred else "PASS"
            ),
        }

    retained = {"extra-cmake-modules": pass_record(dag, "extra-cmake-modules")}
    for node_id in sorted(retained_ids):
        retained[node_id] = pass_record(dag, node_id)

    support_artifacts = {
        "breeze-icons": support_record(support0["nodes"]["breeze-icons"]),
        "kdoctools": support_record(support0["nodes"]["kdoctools"]),
        "kded": support_record(support1["nodes"]["kded"]),
    }

    return {
        "schema": 1,
        "as_of": "2026-09-22",
        "authority": "kde-upstream",
        "role": "tier3-build-campaign-plan",
        "frameworks_series": "6.30.0",
        "state": "planned",
        "execution_authorized": False,
        "generated_from": [
            "manifests/kde-frameworks-tier3.json",
            "manifests/kde-frameworks-tier3-dependencies.json",
            "manifests/kde-tier3-materialization.json",
            "manifests/kde-tier3-package-contracts.json",
            "manifests/kde-dag.json",
            "manifests/kde-tier3-support-build-level0.json",
            "manifests/kde-tier3-support-build-level1.json",
        ],
        "levels": [
            {"level": level_no, "nodes": list(level_nodes)}
            for level_no, level_nodes in enumerate(levels)
        ],
        "retained_pass_artifacts": retained,
        "support_preconditions": deps.get("topology", {}).get("support_preconditions", {}),
        "support_artifacts": support_artifacts,
        "deferred_runtime_validation": deps.get("topology", {}).get("deferred_runtime_validation", {}),
        "nodes": nodes,
        "policy": {
            "only_pass_artifacts_feed_dependents": True,
            "fail_means_real_attempt_failed": True,
            "blocked_means_not_attempted_due_to_failed_required_predecessor": True,
            "independent_nodes_continue_after_unrelated_failures": True,
            "level_progression_uses_promoted_pass_artifacts_only": True,
            "upstream_tests_are_fatal": True,
            "materialization_pass_is_not_package_pass": True,
            "knewstuff_requires_deferred_runtime_validation_before_canonical_pass": True,
            "per_level_execution_requires_separate_authorization": True,
            "stable_promotion_requires_explicit_user_approval": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    compiled = compile_plan()
    if args.write:
        PLAN.write_text(json.dumps(compiled, indent=2) + "\n")

    if args.check:
        current = load(PLAN)
        if current != compiled:
            raise SystemExit(
                "Tier 3 build campaign plan is stale; run "
                "python3 scripts/compile_kde_tier3_build_campaign.py --write"
            )
        print("KDE Tier 3 generated build campaign plan: PASS")
        print("levels=12/2/4/2 nodes=20 execution-authorized=false")
    elif not args.write:
        print(json.dumps(compiled, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

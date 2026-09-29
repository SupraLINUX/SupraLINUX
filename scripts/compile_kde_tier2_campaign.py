#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "manifests/kde-frameworks-tier2.json"
PLAN = ROOT / "manifests/kde-tier2-campaign-plan.json"


def load(path: Path):
    return json.loads(path.read_text())


def dependency_view(node: dict) -> dict:
    meta = node.get("kde_framework_dependencies", {})
    required = list(meta.get("required", []))
    selected = list(meta.get("selected_profile", []))
    return {
        "required_predecessors": required + selected,
        "conditional_frameworks": list(meta.get("conditional", [])),
        "selected_profile": selected,
    }


def compile_plan(canonical: dict) -> dict:
    retained = []
    audits = []
    contract_ready = []
    build_queue = []
    decisions = []
    compatibility_required = []

    nodes = canonical.get("nodes", [])
    for node in nodes:
        node_id = node["id"]
        planning = node.get("planning", {})
        state = node.get("state")

        if state == "PASS":
            retained.append(node_id)
            continue

        if planning.get("readiness") == "compatibility-decision-required":
            decisions.append({
                "node": node_id,
                "blocker": planning.get("human_blocker"),
            })
            continue

        if planning.get("readiness") == "compatibility-provider-required":
            compatibility_required.append(node_id)
            continue

        if planning.get("provider_audit") == "required-before-materialization":
            entry = {"node": node_id}
            entry.update(dependency_view(node))
            audits.append(entry)
            continue

        if (
            planning.get("provider_audit") == "complete"
            and planning.get("package_contract") == "not-materialized"
        ):
            contract_ready.append(node_id)
            continue

        if planning.get("package_contract") == "materialized":
            build_queue.append(node_id)

    audits.sort(
        key=lambda entry: (
            len(entry["conditional_frameworks"]),
            len(entry["required_predecessors"]),
            entry["node"],
        )
    )
    decisions.sort(key=lambda entry: entry["node"])

    snapshot = {
        "pass": sum(node.get("state") == "PASS" for node in nodes),
        "pending": sum(node.get("state") == "pending" for node in nodes),
        "current_fail": sum(node.get("state") == "FAIL" for node in nodes),
        "blocked": sum(node.get("state") == "BLOCKED" for node in nodes),
    }

    return {
        "schema": 1,
        "generated_from": "manifests/kde-frameworks-tier2.json",
        "frameworks_series": canonical.get("frameworks_series"),
        "tier": canonical.get("tier"),
        "canonical_snapshot": snapshot,
        "retained_pass": sorted(retained),
        "provider_audit_required": audits,
        "package_contract_ready": sorted(contract_ready),
        "human_decision_required": decisions,
        "compatibility_provider_required": sorted(compatibility_required),
        "build_queue": sorted(build_queue),
        "audit_batch_size": 5,
        "next_provider_audit_batch": [entry["node"] for entry in audits[:5]],
        "policy": {
            "canonical_manifest_is_source_of_truth": True,
            "provider_audit_precedes_package_contract": True,
            "package_contract_precedes_build_attempt": True,
            "only_pass_artifacts_feed_dependents": True,
            "stable_promotion_requires_explicit_user_approval": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    compiled = compile_plan(load(CANONICAL))

    if args.write:
        PLAN.write_text(json.dumps(compiled, indent=2) + "\n")

    if args.check:
        current = load(PLAN)
        if current != compiled:
            raise SystemExit(
                "Tier 2 campaign plan is stale; run "
                "python3 scripts/compile_kde_tier2_campaign.py --write"
            )
        print("KDE Tier 2 generated campaign plan: PASS")
        print(
            f"retained={len(compiled['retained_pass'])} "
            f"provider-audit={len(compiled['provider_audit_required'])} "
            f"contract-ready={len(compiled['package_contract_ready'])} "
            f"decision={len(compiled['human_decision_required'])} "
            f"compatibility-provider={len(compiled['compatibility_provider_required'])} "
            f"build-queue={len(compiled['build_queue'])}"
        )
    elif not args.write:
        print(json.dumps(compiled, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

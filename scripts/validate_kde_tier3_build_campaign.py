#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compile_kde_tier3_build_campaign import compile_plan  # noqa: E402

errors = []


def req(value, message):
    if not value:
        errors.append(message)


def load(path):
    return json.loads((ROOT / path).read_text())


plan = load("manifests/kde-tier3-build-campaign.json")
canonical = load("manifests/kde-frameworks-tier3.json")
materialization = load("manifests/kde-tier3-materialization.json")
deps = load("manifests/kde-frameworks-tier3-dependencies.json")

try:
    compiled = compile_plan()
    req(plan == compiled, "Tier3 build campaign must equal generated canonical plan")
except Exception as exc:
    errors.append(f"Tier3 build campaign compilation failed: {exc}")

req(plan.get("schema") == 1, "Tier3 build campaign schema")
req(plan.get("authority") == "kde-upstream", "Tier3 build campaign dependency authority")
req(plan.get("role") == "tier3-build-campaign-plan", "Tier3 build campaign role")
req(plan.get("frameworks_series") == "6.30.0", "Tier3 build campaign Frameworks series")
req(plan.get("state") == "planned", "Tier3 build campaign planning state")
req(plan.get("execution_authorized") is False, "planning manifest must never authorize package builds")
req(materialization.get("state") == "PASS", "Tier3 build campaign requires materialization PASS")
req(canonical.get("materialization") == "PASS", "canonical Tier3 materialization PASS")
req(canonical.get("build_campaign_manifest") == "manifests/kde-tier3-build-campaign.json", "canonical build-campaign manifest linkage")

levels = plan.get("levels", [])
req([len(x.get("nodes", [])) for x in levels] == [12, 2, 4, 2], "Tier3 build levels must be 12/2/4/2")
flat = [node for level in levels for node in level.get("nodes", [])]
req(len(flat) == 20 and len(set(flat)) == 20, "Tier3 build campaign must contain 20 unique nodes")
req(set(flat) == set(materialization.get("selected_nodes", [])), "Tier3 build campaign/materialization node set")

level_by = {}
for level in levels:
    for node in level.get("nodes", []):
        level_by[node] = level.get("level")

for node_id, node in plan.get("nodes", {}).items():
    req(node.get("state") == "planned", f"{node_id}: immutable plan state")
    req(node.get("level") == level_by.get(node_id), f"{node_id}: planned level")
    mat = node.get("materialization", {})
    req(isinstance(mat.get("workflow_run"), int), f"{node_id}: materialization workflow")
    req(isinstance(mat.get("job_id"), int), f"{node_id}: materialization job")
    req(isinstance(mat.get("artifact_id"), int), f"{node_id}: materialization artifact")
    req(isinstance(mat.get("artifact_sha256"), str) and len(mat.get("artifact_sha256")) == 64, f"{node_id}: materialization digest")

    blockers = node.get("blocking_predecessors", [])
    if node.get("level") == 0:
        req(blockers == [], f"{node_id}: level0 must have no Tier3 blockers")
    for pred in blockers:
        req(pred in level_by, f"{node_id}: blocker exists in Tier3 plan")
        if pred in level_by:
            req(level_by[pred] < node.get("level"), f"{node_id}: blocker {pred} must be from earlier level")

    for pred in node.get("external_build_inputs", []) + node.get("external_runtime_inputs", []):
        rec = plan.get("retained_pass_artifacts", {}).get(pred, {})
        req(isinstance(rec.get("artifact_id"), int), f"{node_id}: retained predecessor {pred} artifact")
        req(isinstance(rec.get("artifact_sha256"), str) and len(rec.get("artifact_sha256")) == 64, f"{node_id}: retained predecessor {pred} digest")

    deferred = node.get("deferred_runtime_validation", [])
    if node_id == "knewstuff":
        req(deferred == ["kcmutils"], "KNewStuff deferred runtime validation")
        req(node.get("canonical_success_transition") == "pending/runtime-validation-required", "KNewStuff cannot become canonical PASS before runtime validation")
    else:
        req(deferred == [], f"{node_id}: unexpected deferred runtime validation")
        req(node.get("canonical_success_transition") == "PASS", f"{node_id}: normal successful transition")

req(plan.get("deferred_runtime_validation") == {"knewstuff": ["kcmutils"]}, "campaign deferred runtime-validation map")
req(plan.get("support_preconditions") == deps.get("topology", {}).get("support_preconditions"), "Tier3 support preconditions")

for node_id in ("breeze-icons", "kdoctools", "kded"):
    rec = plan.get("support_artifacts", {}).get(node_id, {})
    req(isinstance(rec.get("workflow_run"), int), f"{node_id}: support workflow")
    req(isinstance(rec.get("artifact_id"), int), f"{node_id}: support artifact")
    req(isinstance(rec.get("artifact_sha256"), str) and len(rec.get("artifact_sha256")) == 64, f"{node_id}: support digest")

ecm = plan.get("retained_pass_artifacts", {}).get("extra-cmake-modules", {})
req(ecm.get("version") == "6.30.0-0supralinux3", "ECM pinned version")
req(isinstance(ecm.get("artifact_id"), int) and len(ecm.get("artifact_sha256", "")) == 64, "ECM pinned PASS artifact")

policy = plan.get("policy", {})
for key in (
    "only_pass_artifacts_feed_dependents",
    "fail_means_real_attempt_failed",
    "blocked_means_not_attempted_due_to_failed_required_predecessor",
    "independent_nodes_continue_after_unrelated_failures",
    "level_progression_uses_promoted_pass_artifacts_only",
    "upstream_tests_are_fatal",
    "materialization_pass_is_not_package_pass",
    "knewstuff_requires_deferred_runtime_validation_before_canonical_pass",
    "per_level_execution_requires_separate_authorization",
    "stable_promotion_requires_explicit_user_approval",
):
    req(policy.get(key) is True, f"Tier3 build campaign policy: {key}")

phase = canonical.get("discovery_policy", {}).get("phase")
req(phase in {
    "build-campaign-planning",
    "build-level0",
    "build-level1",
    "build-level2",
    "build-level3",
    "runtime-validation",
    "complete",
}, "canonical Tier3 build-campaign lifecycle")

for path in (
    "scripts/compile_kde_tier3_build_campaign.py",
    "scripts/validate_kde_tier3_build_campaign.py",
    "docs/kde-tier3-build-campaign.md",
):
    req((ROOT / path).exists(), f"missing Tier3 build-campaign component: {path}")

doc = (ROOT / "docs/kde-tier3-build-campaign.md").read_text()
for token in (
    "12 / 2 / 4 / 2",
    "FAIL",
    "BLOCKED",
    "KNewStuff",
    "KCMUtils",
    "execution_authorized=false",
    "stable",
):
    req(token in doc, f"Tier3 build-campaign documentation missing {token}")

if errors:
    for error in errors:
        print("ERROR:", error, file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 build campaign plan: PASS")
print("levels=12/2/4/2")
print("nodes=20")
print("execution_authorized=false")

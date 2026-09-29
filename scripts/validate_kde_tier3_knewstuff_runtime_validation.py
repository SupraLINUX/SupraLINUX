#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def req(value, message):
    if not value:
        errors.append(message)

def load(path):
    return json.loads((ROOT / path).read_text())

t = load("manifests/kde-frameworks-tier3.json")
rv = load("manifests/kde-tier3-knewstuff-runtime-validation.json")
l0 = load("manifests/kde-tier3-build-level0.json")
l2 = load("manifests/kde-tier3-build-level2.json")
dag = load("manifests/kde-dag.json")

SNAP = "17 PASS / 3 pending / 0 current FAIL / 0 BLOCKED"
PLAN_GATE = "tier3-knewstuff-runtime-validation-planning"
ACTIVATION_GATE = "tier3-knewstuff-runtime-validation-activation"
EXECUTION_GATE = "tier3-knewstuff-runtime-validation"

req(rv.get("schema") == 1, "runtime-validation schema")
req(rv.get("authority") == "kde-upstream", "runtime-validation authority")
req(rv.get("provider_platform") == "ubuntu-resolute", "runtime-validation provider platform")
req(rv.get("role") == "tier3-knewstuff-deferred-runtime-validation", "runtime-validation role")
req(rv.get("frameworks_series") == "6.30.0", "runtime-validation Frameworks series")
req(rv.get("gate") == EXECUTION_GATE, "runtime-validation execution gate")
req(rv.get("state") == "execution-authorized", "runtime-validation execution state")
req(rv.get("execution_authorized") is True, "runtime execution must be explicitly authorized")
req(rv.get("validation_run_kind") == "runtime-only", "runtime-validation run kind")
req(rv.get("package_attempted") is False and rv.get("consumes_package_attempt") is False, "planning/runtime validation cannot consume Package Attempt")
req(rv.get("package_state_effect") == "none-until-runtime-validation-PASS", "runtime planning has no package-state effect")
req(rv.get("canonical_snapshot_before") == SNAP, "runtime planning canonical snapshot")

top = t.get("runtime_validation", {})
req(top.get("manifest") == "manifests/kde-tier3-knewstuff-runtime-validation.json", "Tier3 runtime-validation manifest linkage")
req(top.get("node") == "knewstuff", "Tier3 runtime-validation node")
req(top.get("status") == "execution-authorized", "Tier3 runtime-validation live status")
req(top.get("execution_authorized") is True, "Tier3 runtime-validation execution authorization")
req(top.get("validation_run_kind") == "runtime-only" and top.get("consumes_package_attempt") is False, "Tier3 runtime-validation attempt semantics")
req(top.get("canonical_state_effect") == "none-until-runtime-validation-PASS", "Tier3 runtime-validation state-effect guard")
req(top.get("next_gate") == EXECUTION_GATE, "Tier3 runtime-validation live next gate")

pol = t.get("discovery_policy", {})
req(pol.get("phase") == "runtime-validation-execution", "Tier3 post-Level2 phase")
req(pol.get("runtime_validation") == "execution-authorized", "Tier3 runtime-validation execution marker")
req(pol.get("package_builds") == "tier3-level2-package-attempt-PASS-closed", "Level2 package-build closure retained")

nodes = {n["id"]: n for n in t.get("nodes", [])}
kn = nodes.get("knewstuff", {})
kp = nodes.get("kcmutils", {})
req(kn.get("state") == "pending", "KNewStuff canonical state remains pending")
req(kn.get("planning", {}).get("readiness") == "runtime-validation-required", "KNewStuff runtime-validation readiness")
req(kn.get("planning", {}).get("runtime_validation_manifest") == "manifests/kde-tier3-knewstuff-runtime-validation.json", "KNewStuff planning manifest linkage")
req(kn.get("planning", {}).get("runtime_validation_status") == "execution-authorized", "KNewStuff execution status")
req(kn.get("packaging", {}).get("state") == "runtime-validation-required", "KNewStuff packaging runtime gate")
req(kn.get("packaging", {}).get("package_version") == "6.30.0-0supralinux1", "KNewStuff package version")
req(kn.get("packaging", {}).get("deferred_runtime_validation") == ["kcmutils"], "KNewStuff deferred provider")
req(kn.get("packaging", {}).get("downstream_eligible") is False, "KNewStuff remains non-downstream-eligible")
req("knewstuff" not in dag.get("nodes", {}), "KNewStuff must remain outside DAG before runtime PASS")

subject = rv.get("subject", {})
req(subject.get("node") == "knewstuff" and subject.get("source_package") == "kf6-knewstuff", "runtime subject identity")
req(subject.get("package_version") == "6.30.0-0supralinux1", "runtime subject version")
req(subject.get("canonical_state") == "pending/runtime-validation-required" and subject.get("downstream_eligible") is False, "runtime subject canonical state")
be = subject.get("retained_build_evidence", {})
expected_be = {
    "workflow_run": 35818120201,
    "job_id": 107044336736,
    "commit": "0599266fd5fc9869002629b3778d71f1e76bbdc1",
    "artifact_id": 10732461923,
    "artifact_sha256": "2d2b71cd19923c9d9896926f92c86a209fc633f5a2db04597c0ea10488b7ae4b",
    "result": "RUNTIME_PENDING",
    "build_result": "PASS",
    "tests": "5/5 PASS",
}
for key, value in expected_be.items():
    req(be.get(key) == value, f"KNewStuff retained evidence {key}")
l0k = l0.get("nodes", {}).get("knewstuff", {})
l0e = l0k.get("pass_evidence", {})
for key in ("workflow_run", "job_id", "commit", "artifact_id", "artifact_sha256", "result", "build_result", "tests"):
    req(be.get(key) == l0e.get(key), f"KNewStuff runtime plan matches Level0 evidence {key}")
req(subject.get("expected_binary_packages") == [
    "knewstuff-dialog6", "libkf6newstuff-data", "libkf6newstuff-dev", "libkf6newstuff-doc",
    "libkf6newstuffcore6", "libkf6newstuffwidgets6", "qml6-module-org-kde-newstuff"
], "KNewStuff exact binary set")

provider = rv.get("runtime_provider", {})
req(provider.get("node") == "kcmutils" and provider.get("source_package") == "kf6-kcmutils", "runtime provider identity")
req(provider.get("package_version") == "6.30.0-0supralinux3", "runtime provider version")
req(provider.get("canonical_state") == "PASS" and provider.get("downstream_eligible") is True, "runtime provider canonical PASS")
pe = provider.get("pass_evidence", {})
expected_pe = {
    "workflow_run": 36503684811,
    "job_id": 109200408066,
    "commit": "fdc9d93fcc6ec9065f173d5d47b2bca928bf6f06",
    "artifact_id": 11006467074,
    "artifact_sha256": "4dc1045a571b0cb05e61e25600a56fbdc59e5a80cde071cc3ad6af78f7b884a7",
    "result": "PASS",
    "build_result": "PASS",
    "tests": "6/6 PASS",
}
for key, value in expected_pe.items():
    req(pe.get(key) == value, f"KCMUtils PASS evidence {key}")
l2k = l2.get("nodes", {}).get("kcmutils", {})
l2e = l2k.get("pass_evidence", {})
for key in ("workflow_run", "job_id", "commit", "artifact_id", "artifact_sha256", "result", "build_result", "tests"):
    req(pe.get(key) == l2e.get(key), f"KCMUtils runtime plan matches Level2 evidence {key}")
req(kp.get("state") == "PASS" and kp.get("packaging", {}).get("state") == "PASS" and kp.get("packaging", {}).get("downstream_eligible") is True, "KCMUtils canonical live PASS")
req(provider.get("expected_binary_packages") == l2k.get("expected_binary_packages"), "KCMUtils exact binary set matches Level2")

obs = rv.get("trigger_observation", {})
req(obs.get("evidence_artifact_id") == 10732461923, "runtime trigger evidence artifact")
req(obs.get("historical_runtime_provider") == "ubuntu-resolute", "runtime trigger historical provider")
req(obs.get("observed_kcmutils_version") == "6.24.0-0ubuntu1", "runtime trigger historical KCMUtils version")
req(set(obs.get("observed_packages", [])) == {
    "libkf6kcmutils-data", "libkf6kcmutilscore6", "libkf6kcmutilsquick6", "qml6-module-org-kde-kcmutils"
}, "runtime trigger observed KCMUtils package set")

cs = rv.get("closure_sources", {})
kcs = cs.get("knewstuff", {})
req(kcs.get("manifest") == "manifests/kde-tier3-build-level0.json" and kcs.get("node") == "knewstuff", "KNewStuff closure source")
req(kcs.get("fields") == ["retained_input_ids", "external_runtime_inputs"], "KNewStuff closure source fields")
req(set(kcs.get("required_ids", [])) == set(l0k.get("retained_input_ids", [])), "KNewStuff retained closure IDs frozen from Level0")
req(set(l0k.get("external_runtime_inputs", [])) <= set(kcs.get("required_ids", [])), "KNewStuff runtime inputs included in frozen closure")
cms = cs.get("kcmutils", {})
req(cms.get("manifest") == "manifests/kde-tier3-build-level2.json" and cms.get("node") == "kcmutils", "KCMUtils closure source")
req(cms.get("fields") == ["retained_input_ids", "support_input_ids"], "KCMUtils closure source fields")
req(cms.get("required_runtime_validation_provider") == "kcmutils", "KCMUtils runtime-provider requirement")
cp = cs.get("policy", {})
for key in (
    "artifact_ids_and_outer_sha256_are_pinned",
    "exact_binary_sets_and_versions_are_verified_before_install",
    "internal_result_json_artifact_hashes_are_verified",
    "only_canonical_pass_supralinux_artifacts_feed_the_validation",
    "ubuntu_may_supply_non_supralinux_base_dependencies",
    "ubuntu_kcmutils_fallback_forbidden",
):
    req(cp.get(key) is True, f"runtime closure policy {key}")

env = rv.get("environment", {})
req(env.get("architecture") == "amd64" and env.get("base") == "ubuntu-resolute", "runtime environment platform")
req(env.get("rootfs") == "fresh-reproducible-runtime-rootfs", "runtime rootfs must be fresh/reproducible")
req(env.get("historical_rootfs_role") == "non-canonical-cache-only", "historical rootfs cannot be source of truth")
req(env.get("snapshots_role") == "execution-cache-only-never-source-of-truth", "snapshot role")
req(env.get("qml_platform") == "offscreen" and env.get("smoke_test_network") is False, "QML smoke isolation")

checks = set(rv.get("planned_checks", []))
required_checks = {
    "download-retained-artifacts-by-id-and-sha256",
    "verify-result-json-identity-and-internal-artifact-hashes",
    "verify-exact-knewstuff-and-kcmutils-binary-sets",
    "install-canonical-supralinux-runtime-closure",
    "apt-get-check",
    "assert-exact-knewstuff-version-6.30.0-0supralinux1",
    "assert-exact-kcmutils-version-6.30.0-0supralinux3",
    "assert-no-ubuntu-kcmutils-6.24-provider-remains",
    "resolve-runtime-shared-object-dependencies-without-not-found",
    "qml-import-smoke-org-kde-newstuff-and-org-kde-kcmutils",
    "qml-component-compile-installed-EntryDetails.qml-and-Page.qml-offscreen",
}
req(checks == required_checks, "runtime planned check set")

qml = rv.get("qml_runtime_surface", {})
req(qml.get("required_import") == "org.kde.kcmutils", "QML runtime required import")
req(qml.get("required_kcmutils_types") == ["SimpleKCM", "GridViewKCM"], "QML runtime KCMUtils types")
req(qml.get("knewstuff_files") == [
    "usr/lib/x86_64-linux-gnu/qt6/qml/org/kde/newstuff/EntryDetails.qml",
    "usr/lib/x86_64-linux-gnu/qt6/qml/org/kde/newstuff/Page.qml",
], "QML runtime KNewStuff files")
req("QQmlEngine/QQmlComponent" in qml.get("method", "") and "offscreen" in qml.get("method", ""), "QML runtime method")

sem = rv.get("result_semantics", {})
ps = sem.get("pass", {})
req(ps.get("validation_result") == "PASS" and ps.get("package_attempted") is False, "runtime PASS does not consume package attempt")
req(ps.get("package_state_effect") == "promote-existing-knewstuff-build-to-PASS", "runtime PASS promotion semantics")
req(ps.get("knewstuff_state") == "PASS" and ps.get("downstream_eligible") is True, "runtime PASS KNewStuff effect")
fs = sem.get("fail", {})
req(fs.get("validation_result") == "FAIL" and fs.get("package_attempted") is False, "runtime FAIL does not consume package attempt")
req(fs.get("package_state_effect") == "none-runtime-validation-failed", "runtime FAIL state effect")
req(fs.get("knewstuff_state") == "pending/runtime-validation-required" and fs.get("downstream_eligible") is False, "runtime FAIL keeps KNewStuff pending")
ii = sem.get("infra_invalid", {})
req(ii.get("validation_result") == "INFRA_INVALID" and ii.get("package_attempted") is False and ii.get("package_state_effect") == "none", "runtime INFRA_INVALID semantics")

activation = rv.get("activation", {})
planning_policy = rv.get("planning_policy_evidence", {})
req(planning_policy.get("workflow_run") == 36567527801, "planning Policy workflow evidence")
req(planning_policy.get("job_id") == 109403055592, "planning Policy job evidence")
req(planning_policy.get("commit") == "c139f70509cd321913c1e1c89565bfa60a7f22ff", "planning Policy commit evidence")
req(planning_policy.get("conclusion") == "success", "planning Policy PASS evidence")
req(planning_policy.get("validated_gate") == PLAN_GATE, "planning Policy validated gate")
req(activation.get("status") == "ACTIVE" and activation.get("execution_authorized") is True, "runtime activation must be active")
req(activation.get("activation_requires") == "Repository Policy PASS for activation contract and executable runtime lane", "runtime activation precondition")
req(activation.get("runtime_execution_gate") == EXECUTION_GATE, "runtime execution gate")
activation_policy = activation.get("activation_policy_evidence", {})
req(activation_policy.get("workflow_run") == 36573815831, "activation Policy workflow evidence")
req(activation_policy.get("job_id") == 109424159153, "activation Policy job evidence")
req(activation_policy.get("commit") == "76261018520c0f566f152b319d41e6d770fdc310", "activation Policy commit evidence")
req(activation_policy.get("conclusion") == "success", "activation Policy PASS evidence")
req(activation_policy.get("validated_gate") == ACTIVATION_GATE, "activation Policy validated gate")
req(activation.get("stable_promotion_requires_explicit_user_approval") is True, "stable approval policy")

snap = t.get("level2_snapshot", {})
req((snap.get("pass"), snap.get("pending"), snap.get("current_fail"), snap.get("blocked")) == (17,3,0,0), "canonical snapshot unchanged during planning")

doc = (ROOT / "docs/kde-tier3-knewstuff-runtime-validation.md").read_text()
for token in (
    "RUNTIME_PENDING", "10732461923", "11006467074", "6.24.0-0ubuntu1",
    "6.30.0-0supralinux3", "EntryDetails.qml", "Page.qml",
    "validation_run", "Package Attempt", "INFRA_INVALID", "execution_authorized=false"
):
    req(token in doc, f"runtime-validation docs missing {token}")

if errors:
    for error in errors:
        print("ERROR:", error, file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 KNewStuff runtime-validation execution authorization: PASS")
print("state=execution-authorized")
print("execution_authorized=true")
print("package_attempted=false")
print("canonical=" + SNAP)
print("next_gate=" + EXECUTION_GATE)

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

SNAP = "17 PASS / 3 pending / 0 current FAIL / 0 BLOCKED"\nPOST_SNAP = "18 PASS / 2 pending / 0 current FAIL / 0 BLOCKED"
PLAN_GATE = "tier3-knewstuff-runtime-validation-planning"
ACTIVATION_GATE = "tier3-knewstuff-runtime-validation-activation"
EXECUTION_GATE = "tier3-knewstuff-runtime-validation"

req(rv.get("schema") == 1, "runtime-validation schema")
req(rv.get("authority") == "kde-upstream", "runtime-validation authority")
req(rv.get("provider_platform") == "ubuntu-resolute", "runtime-validation provider platform")
req(rv.get("role") == "tier3-knewstuff-deferred-runtime-validation", "runtime-validation role")
req(rv.get("frameworks_series") == "6.30.0", "runtime-validation Frameworks series")
req(rv.get("gate") == "tier3-knewstuff-runtime-validation-closure", "runtime-validation closure gate")
req(rv.get("state") == "PASS-closed", "runtime-validation closure state")
req(rv.get("execution_authorized") is False, "runtime execution must be closed after PASS")
req(rv.get("validation_run_kind") == "runtime-only", "runtime-validation run kind")
req(rv.get("package_attempted") is False and rv.get("consumes_package_attempt") is False, "planning/runtime validation cannot consume Package Attempt")
req(rv.get("package_state_effect") == "promoted-existing-knewstuff-build-to-PASS", "runtime PASS package-state effect")
req(rv.get("canonical_snapshot_before") == SNAP, "runtime planning canonical snapshot")

top = t.get("runtime_validation", {})
req(top.get("manifest") == "manifests/kde-tier3-knewstuff-runtime-validation.json", "Tier3 runtime-validation manifest linkage")
req(top.get("node") == "knewstuff", "Tier3 runtime-validation node")
req(top.get("status") == "PASS-closed", "Tier3 runtime-validation live status")
req(top.get("execution_authorized") is False, "Tier3 runtime-validation execution must be closed")
req(top.get("validation_run_kind") == "runtime-only" and top.get("consumes_package_attempt") is False, "Tier3 runtime-validation attempt semantics")
req(top.get("canonical_state_effect") == "KNewStuff-promoted-to-PASS", "Tier3 runtime-validation applied state effect")
req(top.get("next_gate") == "tier3-knewstuff-runtime-validation-closure", "Tier3 runtime-validation closure gate")

pol = t.get("discovery_policy", {})
req(pol.get("phase") == "runtime-validation-closure", "Tier3 post-Level2 phase")
req(pol.get("runtime_validation") == "PASS-closed", "Tier3 runtime-validation closure marker")
req(pol.get("package_builds") == "tier3-level2-package-attempt-PASS-closed", "Level2 package-build closure retained")

nodes = {n["id"]: n for n in t.get("nodes", [])}
kn = nodes.get("knewstuff", {})
kp = nodes.get("kcmutils", {})
req(kn.get("state") == "PASS", "KNewStuff canonical state promoted to PASS")
req(kn.get("planning", {}).get("readiness") == "materialized", "KNewStuff readiness after runtime closure")
req(kn.get("planning", {}).get("runtime_validation_manifest") == "manifests/kde-tier3-knewstuff-runtime-validation.json", "KNewStuff planning manifest linkage")
req(kn.get("planning", {}).get("runtime_validation_status") == "PASS-closed", "KNewStuff runtime-validation closure status")
req(kn.get("packaging", {}).get("state") == "PASS", "KNewStuff packaging PASS")
req(kn.get("packaging", {}).get("package_version") == "6.30.0-0supralinux1", "KNewStuff package version")
req(kn.get("packaging", {}).get("deferred_runtime_validation") == ["kcmutils"], "KNewStuff deferred provider")
req(kn.get("packaging", {}).get("downstream_eligible") is True, "KNewStuff is downstream-eligible after runtime PASS")
req("knewstuff" in dag.get("nodes", {}), "KNewStuff must enter canonical DAG after runtime PASS")

subject = rv.get("subject", {})
req(subject.get("node") == "knewstuff" and subject.get("source_package") == "kf6-knewstuff", "runtime subject identity")
req(subject.get("package_version") == "6.30.0-0supralinux1", "runtime subject version")
req(subject.get("canonical_state") == "PASS" and subject.get("downstream_eligible") is True, "runtime subject canonical state")
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
    "legacy_artifacts_without_internal_hash_maps_use_outer_sha256_plus_exact_deb_contract",
    "result_json_fields_are_enforced_when_present",
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
    "verify-result-json-identity-and-every-recorded-internal-artifact-hash",
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

history = rv.get("validation_history", [])
req(len(history) == 4, "runtime validation history length")
incident = history[0] if history else {}
req(incident.get("validation_run") == 1, "runtime validation incident sequence")
req(incident.get("workflow_run") == 36575095841 and incident.get("job_id") == 109428639526, "runtime INFRA_INVALID run/job evidence")
req(incident.get("head_commit") == "955c9189e720633b16791b7e6f1fb7f51e7439b4", "runtime INFRA_INVALID head commit")
req(incident.get("execution_merge_commit") == "023661cb7e3181e383cb617eee17a24d67155665", "runtime INFRA_INVALID merge execution commit")
req(incident.get("artifact_id") == 11036509658 and incident.get("artifact_sha256") == "069046c2a72c5c280bb91152a093e1fae34b5debcdf4cb7aaea4646ae013815a", "runtime INFRA_INVALID evidence artifact")
req(incident.get("validation_result") == "INFRA_INVALID" and incident.get("stage") == "artifact-contract", "runtime INFRA_INVALID classification")
req(incident.get("package_attempted") is False and incident.get("consumes_package_attempt") is False and incident.get("canonical_state_effect") == "none", "runtime INFRA_INVALID state boundary")
req("sibling .zip" in incident.get("cause", "") and "synthetic" in incident.get("remediation", ""), "runtime INFRA_INVALID diagnosis/remediation")

incident2 = history[1] if len(history) > 1 else {}
req(incident2.get("validation_run") == 2, "runtime validation incident2 sequence")
req(incident2.get("workflow_run") == 36576400800 and incident2.get("job_id") == 109433549606, "runtime INFRA_INVALID2 run/job evidence")
req(incident2.get("head_commit") == "438fb5cacf4b4bd7016557b87880ed92c73afa44", "runtime INFRA_INVALID2 head commit")
req(incident2.get("execution_merge_commit") == "dee8ca3945dd7140037ce49065fca73aaf3a1009", "runtime INFRA_INVALID2 merge execution commit")
req(incident2.get("artifact_id") == 11037137944 and incident2.get("artifact_sha256") == "03847ee18320d15b4109dac0e9ec2bf71cde92d5b86308aba4e91f88f7f396ce", "runtime INFRA_INVALID2 evidence artifact")
req(incident2.get("reported_validation_result") == "PASS" and incident2.get("validation_result") == "INFRA_INVALID", "runtime INFRA_INVALID2 reported/canonical result")
req(incident2.get("stage") == "evidence-contract", "runtime INFRA_INVALID2 stage")
req(incident2.get("package_attempted") is False and incident2.get("consumes_package_attempt") is False and incident2.get("canonical_state_effect") == "none", "runtime INFRA_INVALID2 state boundary")
req("internal artifact SHA-256" in incident2.get("cause", "") and "Freeze retries" in incident2.get("remediation", ""), "runtime INFRA_INVALID2 diagnosis/remediation")

incident3 = history[2] if len(history) > 2 else {}
req(incident3.get("validation_run") == 3, "runtime validation incident3 sequence")
req(incident3.get("workflow_run") == 36585341825 and incident3.get("job_id") == 109464539716, "runtime INFRA_INVALID3 run/job evidence")
req(incident3.get("head_commit") == "7b92076e53eef84a874f3d5e51877cfa13d01741", "runtime INFRA_INVALID3 head commit")
req(incident3.get("execution_merge_commit") == "4410e30a6b47aed1f95ac87ac0bdb711a47767f2", "runtime INFRA_INVALID3 merge execution commit")
req(incident3.get("artifact_id") == 11042070381 and incident3.get("artifact_sha256") == "4afb676a88b08c150e8b3c28f4f2d1be12c5e4e81bab36f1323361e2e1fb2d1a", "runtime INFRA_INVALID3 evidence artifact")
req(incident3.get("validation_result") == "INFRA_INVALID" and incident3.get("stage") == "artifact-contract", "runtime INFRA_INVALID3 classification")
req(incident3.get("package_attempted") is False and incident3.get("consumes_package_attempt") is False and incident3.get("canonical_state_effect") == "none", "runtime INFRA_INVALID3 state boundary")
req("four historical schema generations" in incident3.get("cause", "") and "schema-adaptive verifier" in incident3.get("remediation", ""), "runtime INFRA_INVALID3 diagnosis/remediation")

run4 = history[3] if len(history) > 3 else {}
req(run4.get("validation_run") == 4 and run4.get("validation_result") == "PASS" and run4.get("stage") == "complete", "runtime validation run4 PASS closure")
req(run4.get("workflow_run") == 36595513031 and run4.get("job_id") == 109499716109, "runtime validation run4 run/job evidence")
req(run4.get("head_commit") == "49f7a2fabc15f0c75c7633e9048812801877cfc9", "runtime validation run4 head commit")
req(run4.get("execution_merge_commit") == "83ed6e84491d80ee66415ae6544880f7f2c9d904", "runtime validation run4 execution merge commit")
req(run4.get("artifact_id") == 11046266772 and run4.get("artifact_sha256") == "01fc348f3b1a4fbee86599ab6d33c3781858f46264d082747bc155cf6cef9fad", "runtime validation run4 artifact evidence")
req(run4.get("package_attempted") is False and run4.get("consumes_package_attempt") is False, "runtime validation run4 attempt boundary")
req(run4.get("exact_knewstuff_version") == "6.30.0-0supralinux1" and run4.get("exact_kcmutils_version") == "6.30.0-0supralinux3", "runtime validation run4 exact versions")
req(run4.get("apt_check") == "PASS" and run4.get("elf_resolution") == "PASS" and run4.get("qml_import_smoke") == "PASS" and run4.get("qml_component_compile") == "PASS", "runtime validation run4 runtime gates")

audit = rv.get("retained_closure_schema_audit", {})
req(audit.get("scope_artifact_count") == 34 and audit.get("outer_sha256_verified") == 34 and audit.get("outer_sha256_mismatches") == 0, "retained closure outer-hash audit")
req(audit.get("schema_counts") == {
    "legacy_minimal": 15,
    "version_no_result_hashes": 7,
    "result_no_hashes": 2,
    "hash_map": 10,
}, "retained closure schema distribution")
req(audit.get("internal_hash_map_artifacts_checked") == 10 and audit.get("internal_hash_mismatches") == 0, "retained closure internal-hash audit")
cert = rv.get("infrastructure_certification", {})
req(cert.get("status") == "PASS" and cert.get("execution_authorized") is False and cert.get("certification_round") == 2, "runtime infrastructure certification closed after PASS")
req(cert.get("next_gate_after_policy_pass") == EXECUTION_GATE, "runtime infrastructure remediation next gate")
req(set(cert.get("required_checks", [])) == {
    "exact-extracted-artifact-directory-selection",
    "legacy-minimal-result-json-compatibility",
    "version-only-result-json-strict-when-present",
    "result-without-hash-map-compatibility",
    "verify-every-recorded-internal-artifact-sha256",
    "tampered-artifact-rejection",
}, "runtime infrastructure remediation check set")

cert_history = rv.get("infrastructure_certification_history", [])
req(len(cert_history) == 2, "runtime infrastructure certification history length")
cert1 = cert_history[0] if cert_history else {}
req(cert1.get("round") == 1 and cert1.get("status") == "PASS", "runtime infrastructure certification history round1 state")
req(cert1.get("workflow_run") == 36583737052 and cert1.get("job_id") == 109458398423, "runtime infrastructure certification historical Policy evidence")
req(cert1.get("commit") == "f310c657cd3f0050ff4ffbebc0d3df284a8324d1" and cert1.get("conclusion") == "success", "runtime infrastructure certification historical commit/PASS")
req(cert1.get("validated_gate") == "tier3-knewstuff-runtime-validation-infrastructure-certification", "runtime infrastructure certification historical validated gate")
req(cert1.get("synthetic_preflight") == "PASS" and cert1.get("exact_selector") == "PASS", "runtime infrastructure historical selector certification")
req(cert1.get("internal_result_json_hash_verifier") == "PASS" and cert1.get("tamper_rejection") == "PASS", "runtime infrastructure historical evidence-verifier certification")
req("did not model all historical result.json schema generations" in cert1.get("scope_limit", ""), "runtime infrastructure historical certification scope limit")

cert2 = cert_history[1] if len(cert_history) > 1 else {}
req(cert2.get("round") == 2 and cert2.get("status") == "PASS", "runtime infrastructure certification history round2 state")
req(cert2.get("workflow_run") == 36591431061 and cert2.get("job_id") == 109485235871, "runtime infrastructure certification round2 Policy evidence")
req(cert2.get("commit") == "cfe5f54ae5ecfb16f2fd95bd1a0a526bd4257fc5" and cert2.get("conclusion") == "success", "runtime infrastructure certification round2 commit/PASS")
req(cert2.get("validated_gate") == "tier3-knewstuff-runtime-validation-infrastructure-remediation", "runtime infrastructure certification round2 validated gate")
req(cert2.get("synthetic_preflight") == "PASS" and cert2.get("exact_selector") == "PASS", "runtime infrastructure round2 selector certification")
req(cert2.get("schema_generation_legacy_minimal") == "PASS" and cert2.get("schema_generation_version_only") == "PASS", "runtime infrastructure round2 legacy schema certification")
req(cert2.get("schema_generation_result_no_hashes") == "PASS" and cert2.get("schema_generation_hash_map") == "PASS", "runtime infrastructure round2 modern schema certification")
req(cert2.get("tamper_rejection") == "PASS", "runtime infrastructure round2 tamper rejection")

reauth_history = rv.get("reauthorization_history", [])
req(len(reauth_history) == 1, "runtime reauthorization history length")
old_reauth = reauth_history[0] if reauth_history else {}
req(old_reauth.get("status") == "SUPERSEDED" and old_reauth.get("execution_authorized") is False, "runtime prior reauthorization superseded")
req(old_reauth.get("certification_workflow_run") == 36583737052 and old_reauth.get("certification_job_id") == 109458398423, "runtime prior reauthorization retained evidence")
req(old_reauth.get("superseded_by_validation_run") == 3, "runtime prior reauthorization superseded by run3")

cert_policy = cert.get("certification_policy_evidence", {})
req(cert_policy.get("workflow_run") == 36591431061 and cert_policy.get("job_id") == 109485235871, "runtime infrastructure live certification Policy evidence")
req(cert_policy.get("commit") == "cfe5f54ae5ecfb16f2fd95bd1a0a526bd4257fc5" and cert_policy.get("conclusion") == "success", "runtime infrastructure live certification commit/PASS")
req(cert_policy.get("validated_gate") == "tier3-knewstuff-runtime-validation-infrastructure-remediation", "runtime infrastructure live certification gate")
req(cert_policy.get("schema_generation_legacy_minimal") == "PASS" and cert_policy.get("schema_generation_version_only") == "PASS", "runtime infrastructure live legacy schema proof")
req(cert_policy.get("schema_generation_result_no_hashes") == "PASS" and cert_policy.get("schema_generation_hash_map") == "PASS", "runtime infrastructure live modern schema proof")
req(cert_policy.get("tamper_rejection") == "PASS", "runtime infrastructure live tamper rejection")

reauth = rv.get("reauthorization", {})
req(reauth.get("round") == 2 and reauth.get("status") == "CLOSED-PASS" and reauth.get("execution_authorized") is False, "runtime reauthorization round2 closed PASS")
req(reauth.get("certification_workflow_run") == 36591431061 and reauth.get("certification_job_id") == 109485235871, "runtime reauthorization round2 evidence")
req(reauth.get("certification_commit") == "cfe5f54ae5ecfb16f2fd95bd1a0a526bd4257fc5", "runtime reauthorization round2 commit")
req(reauth.get("closed_by_validation_run") == 4 and reauth.get("closed_workflow_run") == 36595513031 and reauth.get("closed_job_id") == 109499716109, "runtime reauthorization round2 closure evidence")
req(reauth.get("runtime_execution_gate") == EXECUTION_GATE, "runtime reauthorization round2 execution gate")
snap = t.get("level2_snapshot", {})
req((snap.get("pass"), snap.get("pending"), snap.get("current_fail"), snap.get("blocked")) == (17,3,0,0), "historical Level2 snapshot remains immutable")
post = t.get("runtime_validation_snapshot", {})
req((post.get("pass"), post.get("pending"), post.get("current_fail"), post.get("blocked")) == (18,2,0,0), "post-runtime canonical snapshot")
req(post.get("pending_nodes") == ["ktexteditor","purpose"] and post.get("runtime_pending") == [], "post-runtime pending set")
req(post.get("workflow_run") == 36595513031 and post.get("job_id") == 109499716109, "post-runtime snapshot evidence")
req(post.get("artifact_id") == 11046266772 and post.get("artifact_sha256") == "01fc348f3b1a4fbee86599ab6d33c3781858f46264d082747bc155cf6cef9fad", "post-runtime snapshot artifact")

doc = (ROOT / "docs/kde-tier3-knewstuff-runtime-validation.md").read_text()
for token in (
    "RUNTIME_PENDING", "10732461923", "11006467074", "6.24.0-0ubuntu1",
    "6.30.0-0supralinux3", "EntryDetails.qml", "Page.qml",
    "validation_run", "Package Attempt", "INFRA_INVALID", "execution_authorized=false", "18 PASS / 2 pending / 0 current FAIL / 0 BLOCKED"
):
    req(token in doc, f"runtime-validation docs missing {token}")

if errors:
    for error in errors:
        print("ERROR:", error, file=sys.stderr)
    raise SystemExit(1)

print("KDE Tier 3 KNewStuff runtime-validation canonical promotion: PASS")
print("state=PASS-closed")
print("execution_authorized=false")
print("package_attempted=false")
print("historical_level2=" + SNAP)\nprint("canonical=" + POST_SNAP)
print("next_gate=tier3-knewstuff-runtime-validation-closure")

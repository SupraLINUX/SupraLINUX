#!/usr/bin/env python3
import ast
import importlib.util
import json
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROKER = ROOT / "scripts/supralinux-authoritative-host-broker.py"
CLOSE_HELPER = ROOT / "scripts/host-close-package-evidence.py"
WORKFLOW = ROOT / ".github/workflows/host-authoritative-control.yml"
ROUTER = ROOT / ".github/workflows/pr-ci-router.yml"
JIT_CORE = ROOT / "scripts/run-kvm-jit-gate-core.sh"
REQUEST = ROOT / "ops/host-authoritative/request.json"

broker = BROKER.read_text()
close_helper = CLOSE_HELPER.read_text()
workflow = WORKFLOW.read_text()
router = ROUTER.read_text()
jit_core = JIT_CORE.read_text()
request = json.loads(REQUEST.read_text())

broker_tree = ast.parse(broker)
prepare_functions = [
    node
    for node in broker_tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "prepare_control_checkout"
]
if len(prepare_functions) != 1:
    raise SystemExit("authoritative host broker must define exactly one prepare_control_checkout")
prepare_function = prepare_functions[0]
if any(
    isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name)
    and node.func.id == "prepare_control_checkout"
    for node in ast.walk(prepare_function)
):
    raise SystemExit("prepare_control_checkout must not call itself")
prepare_source = ast.get_source_segment(broker, prepare_function) or ""
for token in (
    '["git", "init", "-q", str(checkout)]',
    '"refs/pull/{PR_NUMBER}/head"',
    '"status", "--porcelain", "--untracked-files=normal"',
):
    if token not in prepare_source:
        raise SystemExit(f"prepare_control_checkout is missing exact checkout contract: {token}")
prepare_calls = [
    node
    for node in ast.walk(broker_tree)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name)
    and node.func.id == "prepare_control_checkout"
]
if len(prepare_calls) != 3:
    raise SystemExit(
        "prepare_control_checkout must be shared by diagnose, proposed certification, and normal control execution"
    )

close_spec = importlib.util.spec_from_file_location(
    "host_close_package_evidence_test", CLOSE_HELPER
)
close_module = importlib.util.module_from_spec(close_spec)
close_spec.loader.exec_module(close_module)

with tempfile.TemporaryDirectory() as directory:
    output = Path(directory) / "output"
    output.mkdir()
    close_module.ensure_output_dir(output)
    if not output.is_dir():
        raise SystemExit("existing evidence output directory was not accepted")



prepare_helper = (ROOT / "scripts/prepare-libguestfs-runtime.sh").read_text()
for token in (
    'PRIV=()',
    'if [[ "${EUID}" -ne 0 ]]',
    'PRIV=(sudo -n)',
    '"${PRIV[@]}" install -d -o "${TARGET_USER}" -g "${TARGET_GROUP}" -m 0700',
    '"${PRIV[@]}" sha256sum "${SOURCE_KERNEL}"',
    '"${PRIV[@]}" install -o "${TARGET_USER}" -g "${TARGET_GROUP}" -m 0600',
    '"${PRIV[@]}" chown "${TARGET_USER}:${TARGET_GROUP}" "${PROVENANCE_TMP}"',
    'KERNEL_TMP="${RUNTIME_DIR}/vmlinuz.tmp.${BASHPID}"',
    'cleanup_kernel_tmp()',
    'trap cleanup_kernel_tmp EXIT',
):
    if token not in prepare_helper:
        raise SystemExit(f"missing libguestfs prepare privilege contract: {token}")
for forbidden in ("sudo sha256sum", "sudo install "):
    if forbidden in prepare_helper:
        raise SystemExit(f"interactive libguestfs prepare privilege escalation remains: {forbidden}")

required_broker = [
    'os.environ.get("SUDO_USER") != RUNNER_USER',
    '"mode", "gate", "runner_group_id", "cancel_run_id"',
    '"evidence_node"',
    '"evidence_package_artifact_sha256"',
    '"evidence_incident_cause"',
    '"evidence_incident_repair"',
    '"close-evidence-check", "close-evidence", "publish-evidence-check", "publish-evidence"',
    '"execute-and-publish-pass"',
    '"certify-proposed-content"',
    '"supralinux-proposed"',
    '"HOST_SUPRALINUX_PROPOSED_CONTENT_CERTIFICATION=PASS"',
    '"scope=supralinux-proposed-content-certification"',
    '"repository_active=no"',
    '"sbuild_invoked=no"',
    '"SUPRALINUX_GATE_RECEIPT_PATH"',
    '"auto-close-result.txt"',
    'f"/repos/{REPOSITORY}/actions/runs/{child_run_id}/artifacts?per_page=100"',
    '"HOST_AUTHORITATIVE_EXECUTE_AND_PUBLISH_PASS=PASS"',
    'check_destination = result_dir / "auto-close-check"',
    'publish_destination = result_dir / "auto-close-publish"',
    'PERSISTENT_ARTIFACT_ROOT = Path("/var/lib/supralinux/artifacts")',
    'CLOSE_EVIDENCE_HELPER = Path("/usr/local/libexec/supralinux-host-close-package-evidence")',
    'if request["mode"] in {"close-evidence-check", "close-evidence", "publish-evidence-check", "publish-evidence"}:',
    '"package_attempt_effect=none"',
    'request.get("gate") not in {"plasma-package-build", "runner-contract", "supralinux-proposed"}',
    '"Runner contract gate permits only preflight or execute mode."',
    'run.get("status") == "queued"',
    'job.get("status") != "queued"',
    'make_demote(extra_groups=())',
    'privileged_groups = tuple(sorted({libvirt_group, kvm_group}))',
    '"persistent_group_membership_changed=no"',
    '"privilege_scope=child-process-only"',
    'if request["mode"] == "diagnose":',
    'def prepare_control_checkout(checkout: Path) -> None:',
    'diagnose_checkout = diagnose_root / "repo"',
    'cwd=diagnose_checkout',
    'prepare_control_checkout(diagnose_checkout)',
    'prepare_control_checkout(checkout)',
    '"root-kvm-open"',
    '"operator-kvm-open-normal"',
    '"operator-kvm-open-scoped-groups"',
    '"runner-service-security"',
    '"operator-check-kvm-host"',
    '"operator-check-kvm-network-userspace"',
    '"host-default-routes"',
    '"host-{device}-features"',
    '"host-uptime-since"',
    '"libguestfs-runtime-dir"',
    '"libguestfs-runtime-cache"',
    '"libguestfs-runtime-provenance"',
    '"libguestfs-source-kernel-stat"',
    '"libguestfs-runtime-kernel-sha256"',
    '"libguestfs-modules-dep-sha256"',
    '"github_token_requested=no"',
    '"jit_invoked=no"',
    '/actions/runs/{cancel_run_id}/cancel',
    '/labels/ci%3Aplasma-package-build',
    'package_build_label_present = any(',
    'label.get("name") == "ci:plasma-package-build"',
    'if package_build_label_present:',
    'refs/pull/{PR_NUMBER}/head',
    '"status", "--porcelain", "--untracked-files=normal"',
    '["scripts/check-kvm-host.sh"]',
    '["scripts/with-libguestfs-runtime.sh", "true"]',
    '"scripts/check-golden-image-provenance.sh"',
    '["scripts/run-kvm-jit-gate.sh", request["gate"]]',
    '"SUPRALINUX_GITHUB_TOKEN": token',
    '"package_attempt_effect=none-before-execute"',
    'preflight_failure = None',
    'check=False',
    '"state=INFRA_INVALID"',
    'f"failed_command={\' \'.join(command)}"',
    '"vm_created=no"',
    '"jit_invoked=no"',
    'if request["mode"] == "rebuild-golden":',
    '"SUPRALINUX_REPLACE_GOLDEN_IMAGE": "1"',
    '["scripts/build-authoritative-runner-image.sh"]',
    '"HOST_AUTHORITATIVE_GOLDEN_REBUILD=PASS"',
    '"golden-rebuild-admission.txt"',
    'KVM_RUNTIME_PROBE = r"""',
    '"kvm-runtime-admission.json"',
    'kvm_runtime_result.get("open_ok") is True',
    'kvm_runtime_result.get("kvm_api_version") == 12',
    'if request["mode"] == "repair-host":',
    'if request["mode"] == "repair-libguestfs-runtime":',
    'LIBGUESTFS_PREPARE_HELPER = Path("/usr/local/libexec/supralinux-prepare-libguestfs-runtime")',
    'LIBGUESTFS_RUNTIME_HELPER = Path("/usr/local/libexec/supralinux-with-libguestfs-runtime")',
    '"HOST_LIBGUESTFS_RUNTIME_REPAIR=PASS"',
    'repair = subprocess.run(',
    'env=operator_environment({"SUPRALINUX_HOST_USER": operator.pw_name})',
    '"scope=libguestfs-private-kernel-runtime-refresh"',
    '"persistent_change=true"',
    '"/usr/local/libexec/supralinux-restore-kvm-host-network-safety"',
    '"HOST_NETWORK_SAFETY_REPAIR=PASS"',
    '"github_api_mutation=no"',
]
for token in required_broker:
    if token not in broker:
        raise SystemExit(f"missing authoritative host broker contract: {token}")

required_jit_core = [
    'GATE_RECEIPT_PATH="${SUPRALINUX_GATE_RECEIPT_PATH:-}"',
    '--arg host_manifest_sha256 "${evidence_manifest_sha256}"',
    '--argjson workflow_run_id "${WORKFLOW_RUN_ID:-0}"',
    '--arg evidence_dir "${EVIDENCE_DIR}"',
    '--arg source_commit "${PR_HEAD_SHA:-}"',
]
for token in required_jit_core:
    if token not in jit_core:
        raise SystemExit(f"missing JIT gate receipt contract: {token}")

required_helper = [
    'choices=["check", "close", "publish-check", "publish"]',
    '"scripts/close-package-revalidation-evidence.py"',
    '"scripts/close-plasma-package-evidence.py"',
    '"scripts/record-plasma-package-failure.py"',
    '"package-attempt-nonpass"',
    '"--workflow-job-meta"',
    '"--recover-hidden-files"',
    "subprocess.CalledProcessError",
    '"DIAGNOSIS_REQUIRED"',
    '"preflight-incident"',
    '"--incident-cause"',
    '"--incident-repair"',
    '"Canonical input incident lacks diagnosis."',
    '"canonical-update-manifest.json"',
    '"offline_restore_verified": True',
    '"requires_github_for_restore": False',
    'find_host_evidence(',
    '["sha256sum", "--check", "--quiet", "evidence-sha256.txt"]',
    'logical_artifacts.symlink_to(',
    'args.artifact_root.rglob(',
    '"Canonical paths changed after package execution: "',
    '"publish-check", "publish"',
    '"credential.helper=!gh auth git-credential"',
    '"--force-with-lease=refs/heads/{branch}:{args.source_commit}"',
    '"--dry-run"',
    '"ls-remote", "--heads", "origin", remote_ref',
    '"Published canonical commit is not the exact remote branch ref."',
    '"published": published',
    '"HTTP 429", "HTTP 502", "HTTP 503", "HTTP 504"',
    "time.sleep(2 ** attempt)",
    '"Closure replay differs from current canonical file: "',
    "def ensure_output_dir(path: Path)",
    'def publication_commit_message(',
    '"evidence: close {node} input preflight"',
]
for token in required_helper:
    if token not in close_helper:
        raise SystemExit(f"missing authoritative evidence closure contract: {token}")

preflight_campaign = {
    "execution_mode": "build",
    "package_input_certifications": [{"path": "proof.json", "sha256": "a" * 64}],
    "nodes": {"example": {"state": "build-pending", "attempts": []}},
}
if close_module.publication_commit_message(
    preflight_campaign, "example", "preflight"
) != "evidence: close example input preflight":
    raise SystemExit("preflight publication commit message regression")

incident_campaign = {
    "execution_mode": "preflight",
    "package_input_incidents": [
        {
            "path": "proof.json",
            "sha256": "b" * 64,
            "cause": "reviewed input closure incomplete",
            "repair": "supply the exact retained support closure",
        }
    ],
    "nodes": {"example": {"state": "build-pending", "attempts": []}},
}
if close_module.publication_commit_message(
    incident_campaign, "example", "preflight-incident"
) != "evidence: close example input incident":
    raise SystemExit("input incident publication commit message regression")

attempt_campaign = {
    "execution_mode": "complete",
    "nodes": {"example": {"state": "PASS", "attempts": [{"attempt": 3, "state": "PASS"}]}},
}
if close_module.publication_commit_message(
    attempt_campaign, "example", "package-attempt-pass"
) != "evidence: close example Attempt 3":
    raise SystemExit("package publication commit message regression")

failed_attempt_campaign = {
    "execution_mode": "guarded-build",
    "nodes": {
        "example": {
            "state": "build-pending",
            "attempts": [{
                "attempt": 4,
                "state": "FAIL",
                "package_attempt_consumed": True,
                "cause": "network-dependent upstream test",
                "repair": "run only hermetic test cases during package build",
            }],
        }
    },
}
if close_module.publication_commit_message(
    failed_attempt_campaign, "example", "package-attempt-nonpass"
) != "evidence: close example Attempt 4 FAIL":
    raise SystemExit("non-PASS package publication commit message regression")

invalid_failed_attempt = {
    "execution_mode": "guarded-build",
    "nodes": {
        "example": {
            "state": "build-pending",
            "attempts": [{
                "attempt": 4,
                "state": "FAIL",
                "package_attempt_consumed": True,
                "cause": "",
                "repair": "",
            }],
        }
    },
}
try:
    close_module.publication_commit_message(
        invalid_failed_attempt, "example", "package-attempt-nonpass"
    )
except SystemExit:
    pass
else:
    raise SystemExit("undiagnosed non-PASS Attempt publication was accepted")

invalid_preflight = {
    "execution_mode": "preflight",
    "package_input_certifications": [],
    "nodes": {"example": {"state": "build-pending", "attempts": []}},
}
try:
    close_module.publication_commit_message(invalid_preflight, "example", "preflight")
except SystemExit:
    pass
else:
    raise SystemExit("invalid preflight publication was accepted")

for content, name in ((broker, "broker"), (close_helper, "closure helper")):
    for forbidden in (
        "eval(",
        "shell=True",
        'request["script"]',
        "chmod 0777",
    ):
        if forbidden in content:
            raise SystemExit(f"forbidden {name} construct: {forbidden}")

required_workflow = [
    "workflow_call:",
    "supralinux-host-orchestrator",
    "Checkout exact PR head",
    "Refresh authoritative host broker",
    "Validate authoritative control request",
    "Execute fixed authoritative host control",
    "/usr/local/libexec/supralinux-authoritative-host-broker",
    "/usr/local/libexec/supralinux-host-close-package-evidence",
    "/usr/local/libexec/supralinux-prepare-libguestfs-runtime",
    "/usr/local/libexec/supralinux-with-libguestfs-runtime",
    "Upload authoritative control result",
    '"close-evidence-check", "close-evidence"',
    '"execute-and-publish-pass"',
    '"runner-contract"',
    '"certify-proposed-content"',
    '"supralinux-proposed"',
]
for token in required_workflow:
    if token not in workflow:
        raise SystemExit(f"missing authoritative host workflow contract: {token}")

required_router = [
    "Host control admission",
    "python3 scripts/test-host-authoritative-control.py",
    '"publish-evidence-check", "publish-evidence"',
    '"execute-and-publish-pass"',
    '"runner-contract"',
    '"certify-proposed-content"',
    '"supralinux-proposed"',
]
for token in required_router:
    if token not in router:
        raise SystemExit(f"missing authoritative host router contract: {token}")

base_request_keys = {
    "schema",
    "mode",
    "gate",
    "runner_group_id",
    "cancel_run_id",
    "cancel_run_head_sha",
}
evidence_request_keys = {
    "evidence_node",
    "evidence_package_run_id",
    "evidence_package_job_id",
    "evidence_package_artifact_id",
    "evidence_package_artifact_sha256",
    "evidence_host_manifest_sha256",
    "evidence_incident_cause",
    "evidence_incident_repair",
}
unknown_request_keys = set(request) - base_request_keys - evidence_request_keys
if unknown_request_keys:
    raise SystemExit(
        f"unexpected authoritative host request keys: {sorted(unknown_request_keys)!r}"
    )
if request.get("schema") != 1:
    raise SystemExit(f"unexpected authoritative host request schema: {request!r}")
if request.get("mode") not in {
    "diagnose",
    "repair-host",
    "repair-libguestfs-runtime",
    "preflight",
    "rebuild-golden",
    "execute",
    "execute-and-publish-pass",
    "close-evidence-check",
    "close-evidence",
    "publish-evidence-check",
    "publish-evidence",
}:
    raise SystemExit(f"unexpected authoritative host request mode: {request!r}")
if request.get("gate") not in {"plasma-package-build", "runner-contract", "supralinux-proposed"}:
    raise SystemExit(f"unexpected authoritative host request gate: {request!r}")
if request.get("gate") == "runner-contract" and request.get("mode") not in {"preflight", "execute"}:
    raise SystemExit(f"invalid runner-contract request mode: {request!r}")
if request.get("gate") == "supralinux-proposed" and request.get("mode") != "certify-proposed-content":
    raise SystemExit(f"invalid supralinux-proposed request mode: {request!r}")
if request.get("mode") == "certify-proposed-content" and request.get("gate") != "supralinux-proposed":
    raise SystemExit(f"invalid proposed certification gate: {request!r}")
if request.get("runner_group_id") != 3:
    raise SystemExit(f"unexpected authoritative host runner group: {request!r}")

if request["mode"] in {"close-evidence-check", "close-evidence", "publish-evidence-check", "publish-evidence"}:
    if not re.fullmatch(
        r"[a-z0-9][a-z0-9+.-]{0,63}",
        request.get("evidence_node", ""),
    ):
        raise SystemExit(f"invalid evidence node: {request!r}")
    for key in (
        "evidence_package_run_id",
        "evidence_package_job_id",
        "evidence_package_artifact_id",
    ):
        if not isinstance(request.get(key), int) or request[key] <= 0:
            raise SystemExit(f"invalid evidence ID {key}: {request!r}")
    for key in (
        "evidence_package_artifact_sha256",
        "evidence_host_manifest_sha256",
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", request.get(key, "")):
            raise SystemExit(f"invalid evidence digest {key}: {request!r}")
else:
    if any(request.get(key) is not None for key in evidence_request_keys):
        raise SystemExit(
            f"non-closure request contains evidence fields: {request!r}"
        )

print("Host authoritative control contract: PASS")

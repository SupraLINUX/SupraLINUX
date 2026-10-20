#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROKER = ROOT / "scripts/supralinux-authoritative-host-broker.py"
CLOSE_HELPER = ROOT / "scripts/host-close-package-evidence.py"
WORKFLOW = ROOT / ".github/workflows/host-authoritative-control.yml"
ROUTER = ROOT / ".github/workflows/pr-ci-router.yml"
REQUEST = ROOT / "ops/host-authoritative/request.json"

broker = BROKER.read_text()
close_helper = CLOSE_HELPER.read_text()
workflow = WORKFLOW.read_text()
router = ROUTER.read_text()
request = json.loads(REQUEST.read_text())

required_broker = [
    'os.environ.get("SUDO_USER") != RUNNER_USER',
    '"mode", "gate", "runner_group_id", "cancel_run_id"',
    '"evidence_node"',
    '"evidence_package_artifact_sha256"',
    '"close-evidence-check", "close-evidence", "publish-evidence-check", "publish-evidence"',
    'PERSISTENT_ARTIFACT_ROOT = Path("/var/lib/supralinux/artifacts")',
    'CLOSE_EVIDENCE_HELPER = Path("/usr/local/libexec/supralinux-host-close-package-evidence")',
    'if request["mode"] in {"close-evidence-check", "close-evidence", "publish-evidence-check", "publish-evidence"}:',
    '"package_attempt_effect=none"',
    'request.get("gate") != "plasma-package-build"',
    'run.get("status") == "queued"',
    'job.get("status") != "queued"',
    'make_demote(extra_groups=())',
    'privileged_groups = tuple(sorted({libvirt_group, kvm_group}))',
    '"persistent_group_membership_changed=no"',
    '"privilege_scope=child-process-only"',
    'if request["mode"] == "diagnose":',
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
    '"/usr/local/libexec/supralinux-restore-kvm-host-network-safety"',
    '"HOST_NETWORK_SAFETY_REPAIR=PASS"',
    '"github_api_mutation=no"',
]
for token in required_broker:
    if token not in broker:
        raise SystemExit(f"missing authoritative host broker contract: {token}")

required_helper = [
    'choices=["check", "close", "publish-check", "publish"]',
    '"scripts/close-package-revalidation-evidence.py"',
    '"scripts/close-plasma-package-evidence.py"',
    '"--workflow-job-meta"',
    '"--recover-hidden-files"',
    "subprocess.CalledProcessError",
    '"DIAGNOSIS_REQUIRED"',
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
]
for token in required_helper:
    if token not in close_helper:
        raise SystemExit(f"missing authoritative evidence closure contract: {token}")

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
    "Upload authoritative control result",
    '"close-evidence-check", "close-evidence"',
]
for token in required_workflow:
    if token not in workflow:
        raise SystemExit(f"missing authoritative host workflow contract: {token}")

required_router = [
    "Host control admission",
    "python3 scripts/test-host-authoritative-control.py",
    '"publish-evidence-check", "publish-evidence"',
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
    "preflight",
    "rebuild-golden",
    "execute",
    "close-evidence-check",
    "close-evidence",
    "publish-evidence-check",
    "publish-evidence",
}:
    raise SystemExit(f"unexpected authoritative host request mode: {request!r}")
if request.get("gate") != "plasma-package-build":
    raise SystemExit(f"unexpected authoritative host request gate: {request!r}")
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

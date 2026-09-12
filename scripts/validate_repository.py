#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
MANIFEST = ROOT / "manifests" / "desktop-stack.json"
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read_required(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        errors.append(f"required file missing: {relative}")
        return ""
    return path.read_text(encoding="utf-8")


try:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: cannot read {MANIFEST.relative_to(ROOT)}: {exc}", file=sys.stderr)
    raise SystemExit(1)

require(data.get("schema") == 1, "manifest schema must be 1")
platform = data.get("platform", {})
require(platform.get("authority") == "ubuntu", "platform authority must be ubuntu")
require(platform.get("version") == "26.04 LTS", "platform version must be Ubuntu 26.04 LTS")
require(platform.get("series") == "resolute", "Ubuntu 26.04 series must be resolute")

desktop = data.get("desktop", {})
require(desktop.get("authority") == "kde-upstream", "desktop authority must be kde-upstream")
for component in ("plasma", "frameworks", "gear"):
    item = desktop.get(component, {})
    require(bool(item.get("version")), f"{component} version is required")
    require(str(item.get("evidence", "")).startswith("https://kde.org/"), f"{component} must cite KDE upstream evidence")

qt = data.get("qt", {})
require(qt.get("requirement_authority") == "kde-upstream", "Qt requirement authority must be kde-upstream")
require(qt.get("source_authority") == "qt-project", "Qt source authority must be qt-project")
require(bool(qt.get("required_series")), "Qt required_series is required")
provider = qt.get("provider", {})
require(provider.get("name") in {"ubuntu", "supralinux"}, "Qt provider must be ubuntu or supralinux")
if provider.get("name") == "ubuntu":
    require(provider.get("series") == "resolute", "Ubuntu Qt provider must use resolute")
cert = qt.get("certification", {})
require(cert.get("status") in {"pending", "certified", "rejected"}, "Qt certification status is invalid")
if cert.get("status") == "certified":
    require(bool(cert.get("evidence")), "certified Qt requires evidence")

ci = data.get("ci", {})
hosted = ci.get("hosted_runner", {})
authoritative = ci.get("authoritative_runner", {})
require(hosted.get("label") == "ubuntu-26.04", "hosted runner must be explicitly ubuntu-26.04")
require(hosted.get("role") == "non-authoritative-preflight", "hosted runner must be non-authoritative")
require(authoritative.get("platform") == "ubuntu-26.04", "authoritative runner platform must be ubuntu-26.04")
require(authoritative.get("virtualization") == "kvm", "authoritative runner virtualization must be kvm")
require(authoritative.get("lifecycle") == "ephemeral-vm", "authoritative runner must use ephemeral VMs")
require(authoritative.get("build_isolation") == "sbuild-unshare", "authoritative build isolation must be sbuild-unshare")
require(authoritative.get("system_test") == "autopkgtest-qemu", "authoritative system test must be autopkgtest-qemu")
require(authoritative.get("nested_kvm_required") is True, "authoritative testing must require nested KVM")

workflow_texts: dict[str, str] = {}
for path in sorted(WORKFLOWS.glob("*.y*ml")):
    text = path.read_text(encoding="utf-8")
    workflow_texts[path.name] = text
    require("ubuntu-latest" not in text, f"{path.relative_to(ROOT)} must not use ubuntu-latest")
    require("pull_request_target" not in text, f"{path.relative_to(ROOT)} must not use pull_request_target")

repository_policy = workflow_texts.get("repository-policy.yml", "")
runner_contract = workflow_texts.get("runner-contract.yml", "")
authoritative_workflow = workflow_texts.get("authoritative-package-proof.yml", "")
hosted_workflow = workflow_texts.get("package-build-proof.yml", "")
qt_provider_workflow = workflow_texts.get("qt-provider-preflight.yml", "")

require(f"actions/checkout@{CHECKOUT_SHA}" in repository_policy, "repository policy checkout action must use the approved immutable SHA")
require("ubuntu-26.04" in repository_policy, "repository policy must use explicit ubuntu-26.04")
require("bash -n scripts/*.sh" in repository_policy, "repository policy must syntax-check all shell scripts")
require("shellcheck -e SC1091 scripts/*.sh" in repository_policy, "repository policy must lint all shell scripts with ShellCheck")
require("--no-install-recommends gnupg" in repository_policy, "repository policy must install Ubuntu gnupg for signed-metadata tests")
require("--no-install-recommends shellcheck" in repository_policy, "repository policy must install Ubuntu ShellCheck")
require("scripts/test-qemu-kvm-required.sh" in repository_policy, "repository policy must functionally test the KVM-only QEMU wrapper")
require("scripts/test-verify-ubuntu-cloud-image-provenance.sh" in repository_policy, "repository policy must functionally test signed Ubuntu source-image verification")
require("scripts/test-check-actions-runner-runtime.sh" in repository_policy, "repository policy must functionally test effective Actions runner provenance")
require("scripts/test-check-golden-image-provenance.sh" in repository_policy, "repository policy must functionally test the golden-image provenance gate")
require("python3 scripts/validate_qt_provider.py" in repository_policy, "repository policy must execute the Qt provider invariant validator")
require(bool(qt_provider_workflow), "missing Qt provider preflight workflow")

for filename, text, gate_label in (
    ("runner-contract.yml", runner_contract, "ci:runner-contract"),
    ("authoritative-package-proof.yml", authoritative_workflow, "ci:authoritative-package-proof"),
):
    require(bool(text), f"missing authoritative workflow: .github/workflows/{filename}")
    require("types: [labeled]" in text, f"{filename} must use controlled PR labeled events")
    require(gate_label in text, f"{filename} must require {gate_label}")
    require("github.event.pull_request.head.repo.full_name == github.repository" in text, f"{filename} must refuse fork PRs")
    for label in ("self-hosted", "linux", "x64", "supralinux", "ubuntu-26.04", "kvm", "ephemeral"):
        require(label in text, f"{filename} missing authoritative runner label {label}")

require("scripts/check-actions-runner-runtime.sh" in runner_contract, "runner contract must verify the effective Actions runner against golden provenance")
require("actions-runner-runtime.txt" in runner_contract, "runner contract must retain effective Actions runner evidence")
require("scripts/check-nested-kvm-runtime.sh" in runner_contract, "runner contract must execute the nested-KVM runtime probe")
require("types: [opened, synchronize, reopened]" in hosted_workflow, "hosted package preflight must use explicit PR lifecycle events")
require("github.event.before" in hosted_workflow and "github.event.after" in hosted_workflow, "hosted package preflight must use synchronize before/after SHAs")
require("scripts/package-preflight-needed.sh" in hosted_workflow, "hosted package preflight must gate expensive work on event delta")
require("fetch-depth: 0" in hosted_workflow, "hosted package preflight must fetch comparison history")

required_files = [
    "docs/architecture/overview.md",
    "docs/architecture/build-ci.md",
    "docs/status/2026-09-11.md",
    "docs/decisions/ADR-0001-authority-provider.md",
    "docs/runners/ubuntu-26.04.md",
    "docs/runners/provisioning.md",
    "docs/runners/host-kvm.md",
    "docs/qt-provider-certification.md",
    "scripts/validate_qt_provider.py",
    "scripts/run-qt-provider-preflight.sh",
    "scripts/qt-provider-preflight-needed.sh",
    "scripts/check-kvm-host.sh",
    "scripts/check-nested-kvm-runtime.sh",
    "scripts/check-actions-runner-runtime.sh",
    "scripts/test-check-actions-runner-runtime.sh",
    "scripts/check-golden-image-provenance.sh",
    "scripts/test-check-golden-image-provenance.sh",
    "scripts/provision-kvm-host.sh",
    "scripts/package-preflight-needed.sh",
    "scripts/fetch-ubuntu-26.04-cloud-image.sh",
    "scripts/verify-ubuntu-cloud-image-provenance.sh",
    "scripts/test-verify-ubuntu-cloud-image-provenance.sh",
    "scripts/build-authoritative-runner-image.sh",
    "scripts/install-actions-runner.sh",
    "scripts/provision-authoritative-runner-guest.sh",
    "scripts/prepare-autopkgtest-qemu-image.sh",
    "scripts/seal-authoritative-runner-image.sh",
    "scripts/qemu-kvm-required.sh",
    "scripts/test-qemu-kvm-required.sh",
    "scripts/run-kvm-jit-gate.sh",
    "scripts/run-kvm-jit-gate-core.sh",
    "scripts/run-authoritative-package-proof.sh",
]
for relative in required_files:
    require((ROOT / relative).exists(), f"required architecture/runner file missing: {relative}")

package_delta = read_required("scripts/package-preflight-needed.sh")
for tracked in ("packages/supralinux-build-test/*", "scripts/run-package-build-proof.sh", ".github/workflows/package-build-proof.yml"):
    require(tracked in package_delta, f"package preflight delta detector must track {tracked}")

host_provisioner = read_required("scripts/provision-kvm-host.sh")
for package in ("libvirt-daemon-system", "qemu-system-x86", "virt-install", "libguestfs-tools"):
    require(package in host_provisioner, f"host provisioning must install {package}")
require("does NOT change BIOS" in host_provisioner, "host provisioning must not silently alter BIOS/KVM module state")
require("/var/lib/supralinux/golden-builds" in host_provisioner, "host provisioning must create golden-build state")

host_checker = read_required("scripts/check-kvm-host.sh")
for token in ("/dev/kvm", "parameters/nested", "qemu:///system", "virt-sysprep", "virt-cat", "virt-copy-out", "flock"):
    require(token in host_checker, f"host preflight missing required check: {token}")

nested_probe = read_required("scripts/check-nested-kvm-runtime.sh")
require("-accel kvm" in nested_probe and "-cpu host" in nested_probe, "nested runtime probe must force real KVM with host CPU")
require("probe_exit_code" in nested_probe and "nested_kvm_runtime=PASS" in nested_probe, "nested runtime probe must preserve explicit result evidence")

cloud_fetcher = read_required("scripts/fetch-ubuntu-26.04-cloud-image.sh")
require("SHA256SUMS.gpg" in cloud_fetcher and "gpgv" in cloud_fetcher, "Ubuntu source-image fetch must verify signed checksum metadata")
require("/var/lib/supralinux/images/source/resolute" in cloud_fetcher, "Ubuntu source image must default to stable host storage")

source_verifier = read_required("scripts/verify-ubuntu-cloud-image-provenance.sh")
for token, message in (
    ("SHA256SUMS.gpg", "use-time source verifier must consume the retained Ubuntu signature"),
    ("gpgv --keyring", "use-time source verifier must cryptographically reverify signed metadata"),
    ("release=resolute", "use-time source verifier must require Resolute provenance"),
    ("architecture=amd64", "use-time source verifier must require amd64 provenance"),
    ("EXPECTED_SHA256", "use-time source verifier must derive an expected signed SHA-256"),
    ("ACTUAL_SHA256", "use-time source verifier must calculate the image SHA-256"),
    ("signed_metadata_verification=PASS", "use-time source verifier must emit signed-metadata PASS evidence"),
    ("Ubuntu source-image SHA-256 mismatch", "use-time source verifier must fail closed on image hash mismatch"),
):
    require(token in source_verifier, message)

source_verifier_test = read_required("scripts/test-verify-ubuntu-cloud-image-provenance.sh")
for token, message in (
    ("--quick-generate-key", "source verifier test must create an ephemeral signing key"),
    ("--detach-sign", "source verifier test must exercise a real detached signature"),
    ("checksum metadata modified after signing", "source verifier test must reject modified signed metadata"),
    ("jointly modified image/provenance", "source verifier test must reject forged image+provenance without matching signed metadata"),
    ("duplicate sha256", "source verifier test must reject ambiguous provenance hashes"),
    ("Ubuntu source-image provenance functional test: PASS", "source verifier test must emit explicit PASS evidence"),
):
    require(token in source_verifier_test, message)

golden_builder = read_required("scripts/build-authoritative-runner-image.sh")
for token, message in (
    ("scripts/check-kvm-host.sh", "golden builder must require host preflight"),
    ("scripts/verify-ubuntu-cloud-image-provenance.sh", "golden builder must reverify signed source-image metadata before use"),
    ("source-image-verification.txt", "golden builder must retain source verification evidence"),
    ("source_image_provenance_verified=yes", "golden provenance must record source revalidation"),
    ("--cpu host-passthrough", "golden builder must expose host CPU virtualization"),
    ("scripts/provision-authoritative-runner-guest.sh", "golden builder must provision the guest"),
    ("scripts/prepare-autopkgtest-qemu-image.sh", "golden builder must prepare the nested test image"),
    ("scripts/seal-authoritative-runner-image.sh", "golden builder must seal guest state"),
    ("virt-sysprep", "golden builder must perform offline clone cleanup"),
    ("qemu-img convert", "golden builder must flatten the overlay"),
    ("qemu-img check", "golden builder must validate the final qcow2"),
    ("SUPRALINUX_REPLACE_GOLDEN_IMAGE", "golden replacement must require explicit opt-in"),
    ("source_checkout_removed=yes", "golden builder must prove temporary source checkout removal"),
):
    require(token in golden_builder, message)
require("machine-id" in golden_builder and "ssh-hostkeys" in golden_builder, "golden builder must reset machine and SSH identities")
verify_pos = golden_builder.find("scripts/verify-ubuntu-cloud-image-provenance.sh")
inspect_pos = golden_builder.find('SOURCE_FORMAT="$(qemu-img info')
require(verify_pos >= 0 and inspect_pos >= 0 and verify_pos < inspect_pos, "golden builder must reverify source integrity before qemu-img inspects the source image")

installer = read_required("scripts/install-actions-runner.sh")
require(".digest" in installer and "sha256sum --check --strict" in installer, "Actions runner archive must use GitHub-published SHA-256 verification")

runner_runtime_checker = read_required("scripts/check-actions-runner-runtime.sh")
for token, message in (
    ("bin/Runner.Listener", "runner runtime checker must query Runner.Listener directly"),
    ("--version", "runner runtime checker must query the effective runner version"),
    ("--commit", "runner runtime checker must retain the effective runner commit"),
    ("runtime_matches_verified_version=yes", "runner runtime checker must emit explicit version-match evidence"),
    ("Rebuild the golden runner image", "runner runtime mismatch must fail closed and require golden refresh"),
):
    require(token in runner_runtime_checker, message)
require("run.sh" not in runner_runtime_checker, "runner runtime checker must not derive version/commit through run.sh wrapper output")

runner_runtime_test = read_required("scripts/test-check-actions-runner-runtime.sh")
for token, message in (
    ("bin/Runner.Listener", "runner runtime test must emulate the real Runner.Listener interface"),
    ("FAKE_RUNNER_VERSION=2.338.0", "runner runtime test must reject an auto-updated version mismatch"),
    ("truncated runtime runner commit", "runner runtime test must reject truncated commit evidence"),
    ("missing Runner.Listener executable", "runner runtime test must reject a missing listener binary"),
    ("Actions runner runtime provenance functional test: PASS", "runner runtime test must emit explicit PASS evidence"),
):
    require(token in runner_runtime_test, message)

golden_provenance_checker = read_required("scripts/check-golden-image-provenance.sh")
for token, message in (
    ("golden_image_sha256", "golden provenance checker must require the published golden hash"),
    ("source_image_sha256", "golden provenance checker must require the verified source-image hash"),
    ("source_commit", "golden provenance checker must require the source commit"),
    ("source_checkout_removed", "golden provenance checker must require source-checkout cleanup"),
    ("source_image_provenance_verified", "golden provenance checker must require signed source-image re-verification"),
    ("ACTUAL_GOLDEN_SHA256", "golden provenance checker must hash the current image bytes"),
    ("golden_provenance_verification=PASS", "golden provenance checker must emit explicit PASS evidence"),
):
    require(token in golden_provenance_checker, message)

golden_provenance_test = read_required("scripts/test-check-golden-image-provenance.sh")
for token, message in (
    ("modified golden-image bytes", "golden provenance test must reject modified golden bytes"),
    ("without signed source verification", "golden provenance test must reject missing signed-source proof"),
    ("without source-checkout cleanup", "golden provenance test must reject missing cleanup proof"),
    ("duplicate golden-image hashes", "golden provenance test must reject ambiguous golden hashes"),
    ("truncated source commit", "golden provenance test must reject invalid source commit evidence"),
    ("Golden image provenance functional test: PASS", "golden provenance test must emit explicit PASS evidence"),
):
    require(token in golden_provenance_test, message)

host_entrypoint = read_required("scripts/run-kvm-jit-gate.sh")
require("scripts/check-golden-image-provenance.sh" in host_entrypoint, "JIT entrypoint must verify golden provenance before orchestration")
require("scripts/run-kvm-jit-gate-core.sh" in host_entrypoint, "JIT entrypoint must delegate only after provenance verification")
require('exec "${ROOT}/scripts/run-kvm-jit-gate-core.sh" "$@"' in host_entrypoint, "JIT entrypoint must preserve arguments when delegating to the core")

host_orchestrator = read_required("scripts/run-kvm-jit-gate-core.sh")
for token, message in (
    ("generate-jitconfig", "host orchestrator must use JIT configuration"),
    ("/run/supralinux-jit-config", "JIT config must live in guest tmpfs"),
    ("Authoritative self-hosted gates refuse fork PRs", "host orchestrator must refuse fork PRs"),
    ("flock -n", "host orchestrator must serialize local authoritative jobs"),
    ("workflow-baseline-ids.json", "host orchestrator must snapshot workflow IDs before triggering"),
    ("head_sha=${PR_HEAD_SHA}", "host orchestrator must query the exact PR head SHA"),
    ("actions/runs/${WORKFLOW_RUN_ID}", "host orchestrator must bind an exact workflow run ID"),
    ("guest-exec-status", "host orchestrator must detect premature runner exit"),
    ("PROVENANCE_SHA256", "host orchestrator core must verify the golden image against provenance"),
    ("source_checkout_removed=yes", "host orchestrator core must require a source-clean golden image"),
    ("su --login --shell /bin/bash --command", "guest runner must start non-root with an explicit login shell"),
):
    require(token in host_orchestrator, message)

authoritative_proof = read_required("scripts/run-authoritative-package-proof.sh")
require("scripts/check-actions-runner-runtime.sh" in authoritative_proof, "authoritative proof must verify effective Actions runner provenance")
require("actions-runner-runtime.txt" in authoritative_proof, "authoritative proof must retain effective Actions runner evidence")
require("scripts/check-nested-kvm-runtime.sh" in authoritative_proof, "authoritative proof must run the nested-KVM runtime probe")
require("--qemu-command=\"${KVM_QEMU_WRAPPER}\"" in authoritative_proof, "authoritative autopkgtest must use the KVM-only QEMU wrapper")
require("--qemu-architecture=x86_64" in authoritative_proof, "authoritative autopkgtest must pin QEMU architecture")
require("qemu-kvm-wrapper-sha256.txt" in authoritative_proof, "authoritative evidence must hash the QEMU wrapper")
require('"system_test_acceleration": "kvm-required"' in authoritative_proof, "authoritative result must record KVM-required acceleration")

qemu_wrapper = read_required("scripts/qemu-kvm-required.sh")
require('exec "${QEMU}" -accel kvm "$@"' in qemu_wrapper, "QEMU wrapper must select KVM only")
require("tcg" not in qemu_wrapper.lower(), "KVM-only wrapper must not contain a TCG fallback")

qemu_wrapper_test = read_required("scripts/test-qemu-kvm-required.sh")
require("Supra Linux Runner" in qemu_wrapper_test, "QEMU wrapper test must preserve an argument containing spaces")
require("MISSING_RC" in qemu_wrapper_test and "127" in qemu_wrapper_test, "QEMU wrapper test must verify missing-executable failure semantics")
require("KVM-required QEMU wrapper functional test: PASS" in qemu_wrapper_test, "QEMU wrapper test must emit explicit PASS evidence")

if errors:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Repository policy validation: PASS")
print(f"Platform: {platform['version']} ({platform['series']})")
print(
    "Desktop: Plasma {plasma}, Frameworks {frameworks}, Gear {gear}".format(
        plasma=desktop["plasma"]["version"],
        frameworks=desktop["frameworks"]["version"],
        gear=desktop["gear"]["version"],
    )
)
print(
    f"Qt: required {qt['required_series']}, provider={provider['name']}, "
    f"candidate={provider.get('candidate_version', 'n/a')}, certification={cert['status']}"
)
print(
    "CI: hosted={hosted}; authoritative={platform}/{virt}/{lifecycle}; build={build}; test={test}; "
    "signed-source-reverification=required; golden-provenance-gate=required; runner-runtime-provenance=required; "
    "KVM-runtime=required; deterministic-qemu-wrapper=required; JIT=required; exact-run-binding=required; "
    "qt-provider-policy=required; shell-syntax=required; shellcheck=required".format(
        hosted=hosted["role"],
        platform=authoritative["platform"],
        virt=authoritative["virtualization"],
        lifecycle=authoritative["lifecycle"],
        build=authoritative["build_isolation"],
        test=authoritative["system_test"],
    )
)

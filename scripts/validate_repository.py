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
selection = data.get("selection_policy", {})
require(selection.get("decision_authority") == "supralinux", "desktop integration decision authority must be supralinux")
require(selection.get("objective") == "newest-stable-kde-compatible-with-ubuntu-application-contract", "desktop selection objective is invalid")
require(selection.get("internal_heuristic") == "stay-ahead-of-ubuntu-where-compatible", "desktop internal heuristic is invalid")
require(selection.get("ubuntu_desktop_packages_select_stack") is False, "Ubuntu desktop packages must not select the KDE stack")
require(selection.get("ubuntu_desktop_versions_are_upper_bound") is False, "Ubuntu desktop versions must not cap KDE")
require(selection.get("pre_release_canonical_allowed") is False, "pre-release KDE must not be canonical by default")
feature_policy = selection.get("feature_completeness", {})
require(feature_policy.get("policy") == "selected-upstream-desktop-features-available-by-default", "selected KDE feature-completeness policy is invalid")
require(feature_policy.get("documented_exceptions_required") is True, "feature-completeness exceptions must be documented")
compat = selection.get("compatibility_contract", {})
require(compat.get("baseline") == "ubuntu-26.04", "compatibility baseline must remain Ubuntu 26.04")
require(compat.get("hard_gate") is True, "Ubuntu application compatibility must be a hard gate")
require(compat.get("qt_or_platform_substitution_requires_evidence") is True, "Qt/platform substitution must require compatibility evidence")
require(compat.get("incompatible_next_release_action") == "retain-newest-compatible-stable-kde", "incompatible KDE release fallback is invalid")
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
frameworks_sample_workflow = workflow_texts.get("authoritative-frameworks-sample-proof.yml", "")
hosted_workflow = workflow_texts.get("package-build-proof.yml", "")
qt_provider_workflow = workflow_texts.get("qt-provider-preflight.yml", "")
pr_ci_router = workflow_texts.get("pr-ci-router.yml", "")
diagnostic_preflight_workflow = workflow_texts.get("diagnostic-infrastructure-preflight.yml", "")

routed_pr_workflows = (
    "package-build-proof.yml",
    "kde-ecm-package-preflight.yml",
    "kde-attica-packaging-reference.yml",
    "kde-attica-package-preflight.yml",
    "kde-tier1-dependency-preflight.yml",
    "kde-tier1-packaging-reference.yml",
    "kde-tier1-packaging-tree.yml",
    "kde-tier1-binary-contract-reference.yml",
    "kde-tier1-package-preflight.yml",
    "kde-tier1-package-batch1-revalidation.yml",
    "kde-tier1-package-batch2.yml",
    "kde-tier1-package-batch3.yml",
    "kde-tier1-package-batch4.yml",
    "kde-tier1-package-batch5.yml",
    "kde-tier1-package-batch6.yml",
    "kde-tier1-package-batch7.yml",
    "kde-tier1-package-batch8.yml",
    "kde-tier1-package-batch9.yml",
    "kde-tier1-package-batch10.yml",
    "kde-tier1-package-batch11.yml",
    "kde-tier2-package-batch1.yml",
    "kde-tier1-source-diagnostic.yml",
    "qt-provider-preflight.yml",
    "diagnostic-infrastructure-preflight.yml",
    "kde-tier3-kio-round23-diagnostic.yml",
    "kde-tier3-kio-round24-diagnostic.yml",
    "kde-tier3-kio-round25-remediation.yml",
    "kde-tier3-kio-round26-remediation.yml",
)

require(f"actions/checkout@{CHECKOUT_SHA}" in repository_policy, "repository policy checkout action must use the approved immutable SHA")
require("ubuntu-26.04" in repository_policy, "repository policy must use explicit ubuntu-26.04")
require("bash -n scripts/*.sh" in repository_policy, "repository policy must syntax-check all shell scripts")
require("shellcheck -e SC1091 scripts/*.sh" in repository_policy, "repository policy must lint all shell scripts with ShellCheck")
require("--no-install-recommends gnupg" in repository_policy, "repository policy must install Ubuntu gnupg for signed-metadata tests")
require("--no-install-recommends shellcheck" in repository_policy, "repository policy must install Ubuntu ShellCheck")
require("scripts/test-qemu-kvm-required.sh" in repository_policy, "repository policy must functionally test the KVM-only QEMU wrapper")
require("scripts/test-verify-ubuntu-cloud-image-provenance.sh" in repository_policy, "repository policy must functionally test signed Ubuntu source-image verification")
require("scripts/test-check-actions-runner-runtime.sh" in repository_policy, "repository policy must functionally test effective Actions runner provenance")
require("scripts/test-autopkgtest-workspace-contract.sh" in repository_policy, "repository policy must functionally test the persistent autopkgtest workspace contract")
require("scripts/test-check-golden-image-provenance.sh" in repository_policy, "repository policy must functionally test the golden-image provenance gate")
require("scripts/test-pr-ci-router-scope.sh" in repository_policy, "repository policy must functionally test semantic PR evidence routing")
require("python3 scripts/validate_diagnostic_infrastructure_preflight.py" in repository_policy, "repository policy must validate diagnostic infrastructure preflight")
require("python3 scripts/validate_kde_tier3_kio_round25_remediation.py" in repository_policy, "repository policy must validate Round25 remediation definition")
require("python3 scripts/validate_kde_tier3_kio_round26_remediation.py" in repository_policy, "repository policy must validate Round26 remediation definition")
require("scripts/test-kde-tier2-package-batch1-scope.sh" in repository_policy, "repository policy must test KDE Tier 2 Batch 1 scope")
require("python3 scripts/validate_kde-tier2-package-batch1.py" not in repository_policy, "repository policy must not contain a misspelled Tier 2 validator path")
require("python3 scripts/validate_kde_tier2_package_batch1.py" in repository_policy, "repository policy must execute KDE Tier 2 Batch 1 validator")
require("scripts/test-kde-development-contract-audit.sh" in repository_policy, "repository policy must functionally test the KDE development contract audit")
require("python3 scripts/validate_qt_provider.py" in repository_policy, "repository policy must execute the Qt provider invariant validator")
require("python3 scripts/validate_kde_tier2.py" in repository_policy, "repository policy must execute the KDE Tier 2 discovery validator")
require(bool(qt_provider_workflow), "missing Qt provider preflight workflow")

# Ordinary pull-request work is admitted through one router. The package/reference/provider
# lanes remain independently dispatchable/reusable, but must not each create their own PR run.
require(bool(pr_ci_router), "missing PR CI router workflow")
require("types: [opened, synchronize, reopened]" in pr_ci_router, "PR CI router must use explicit PR lifecycle events")
require(f"actions/checkout@{CHECKOUT_SHA}" in pr_ci_router, "PR CI router checkout action must use the approved immutable SHA")
require("fetch-depth: 0" in pr_ci_router, "PR CI router must fetch comparison history")
require("github.event.before" in pr_ci_router and "github.event.after" in pr_ci_router, "PR CI router must use synchronize before/after SHAs")
require("github.event.pull_request.base.sha" in pr_ci_router and "github.event.pull_request.head.sha" in pr_ci_router, "PR CI router must support opened/reopened base/head comparison")
require("scripts/pr-ci-router-needed.sh" in pr_ci_router, "PR CI router must delegate semantic evidence/build classification to the tested scope helper")
require("cancel-in-progress: true" in pr_ci_router, "PR CI router must cancel superseded runs")
require("pr-ci-router-${{ github.event.pull_request.number }}" in pr_ci_router, "PR CI router concurrency must be scoped to the PR number")
require("run_diag_preflight" in pr_ci_router and "diagnostic-infrastructure-preflight.yml" in pr_ci_router, "PR router must expose diagnostic infrastructure preflight")
require('p.get("status")=="PASS"' in pr_ci_router, "Round23 admission must require diagnostic preflight PASS")
require("run_round24" in pr_ci_router and "kde-tier3-kio-round24-diagnostic.yml" in pr_ci_router, "PR router must expose Round24 diagnostic")
require('r23.get("status")=="diagnostic-PASS"' in pr_ci_router, "Round24 admission must require closed Round23 PASS")
require('r24.get("package_execution_authorized") is False' in pr_ci_router, "Round24 admission must remain diagnostic-only")
require("run_round25" in pr_ci_router and "kde-tier3-kio-round25-remediation.yml" in pr_ci_router, "PR router must expose Round25 remediation proof")
require('r24.get("status")=="diagnostic-PASS"' in pr_ci_router, "Round25 admission must require closed Round24 PASS")
require('r25.get("package_execution_authorized") is False' in pr_ci_router, "Round25 admission must remain non-promoting")
require("run_round26" in pr_ci_router and "kde-tier3-kio-round26-remediation.yml" in pr_ci_router, "PR router must expose Round26 combined remediation proof")
require('r25.get("status")=="remediation-FAIL-contract"' in pr_ci_router, "Round26 admission must retain Round25 historical contract result")
require('r25.get("interpretation",{}).get("target_krecent_remediation")=="PASS"' in pr_ci_router, "Round26 admission must require KRecent target PASS")
require('r26.get("package_execution_authorized") is False' in pr_ci_router, "Round26 admission must remain non-promoting")

for filename in routed_pr_workflows:
    text = workflow_texts.get(filename, "")
    require(bool(text), f"missing routed reusable workflow: .github/workflows/{filename}")
    require("workflow_call:" in text, f"{filename} must expose workflow_call for PR router reuse")
    require("workflow_dispatch:" in text, f"{filename} must remain manually dispatchable")
    require("\n  pull_request:\n" not in text, f"{filename} must not independently subscribe to ordinary pull_request lifecycle events")
    require(
        f"uses: ./.github/workflows/{filename}" in pr_ci_router,
        f"PR CI router must invoke {filename}",
    )

for filename, text, gate_label in (
    ("runner-contract.yml", runner_contract, "ci:runner-contract"),
    ("authoritative-package-proof.yml", authoritative_workflow, "ci:authoritative-package-proof"),
    ("authoritative-frameworks-sample-proof.yml", frameworks_sample_workflow, "ci:frameworks-sample-proof"),
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

require("workflow_call:" in hosted_workflow, "hosted package preflight must be reusable from the PR CI router")
require("github.event.before" in hosted_workflow and "github.event.after" in hosted_workflow, "hosted package preflight must preserve synchronize before/after SHA scoping")
require("scripts/package-preflight-needed.sh" in hosted_workflow, "hosted package preflight must gate expensive work on event delta")
require("fetch-depth: 0" in hosted_workflow, "hosted package preflight must fetch comparison history")

required_files = [
    "docs/architecture/overview.md",
    "docs/architecture/build-ci.md",
    "docs/decisions/diagnostic-infrastructure-preflight-2026-09-26.md",
    "manifests/diagnostic-infrastructure-preflight.json",
    "scripts/run-diagnostic-infrastructure-preflight.sh",
    "scripts/validate_diagnostic_infrastructure_preflight.py",
    "manifests/kde-tier3-kio-round24-diagnostic.json",
    "scripts/run-kde-tier3-kio-round24-hook.sh",
    "scripts/run-kde-tier3-kio-round24-diagnostic.sh",
    "scripts/validate_kde_tier3_kio_round24_diagnostic.py",
    "scripts/validate_kde_tier3_kio_round24_closure.py",
    "docs/kde-tier3-kio-round24-diagnostic.md",
    "manifests/kde-tier3-kio-round25-remediation.json",
    "scripts/run-kde-tier3-kio-round25-hook.sh",
    "scripts/run-kde-tier3-kio-round25-diagnostic.sh",
    "scripts/validate_kde_tier3_kio_round25_remediation.py",
    "docs/kde-tier3-kio-round25-remediation.md",
    "manifests/kde-tier3-kio-round26-remediation.json",
    "scripts/run-kde-tier3-kio-round26-hook.sh",
    "scripts/run-kde-tier3-kio-round26-diagnostic.sh",
    "scripts/validate_kde_tier3_kio_round26_remediation.py",
    "scripts/validate_kde_tier3_kio_round26_closure.py",
    "manifests/kde-tier3-kio-attempt9-remediation.json",
    "scripts/validate_kde_tier3_kio_attempt9_definition.py",
    "scripts/validate_kde_tier3_kio_attempt9_planning.py",
    "scripts/validate_kde_tier3_kio_attempt9_closure.py",
    "scripts/validate_kde_tier3_kio_attempt10_planning.py",
    "scripts/validate_kde_tier3_kio_attempt10.py",
    "scripts/validate_kde_tier3_kio_attempt10_closure.py",
    "manifests/kde-tier3-kio-attempt10-remediation.json",
    "scripts/validate_kde_tier3_kio_attempt10_definition.py",
    "docs/kde-tier3-kio-attempt10-remediation.md",
    "scripts/validate_kde_tier3_kio_attempt9.py",
    "docs/kde-tier3-kio-attempt9-remediation.md",
    "docs/kde-tier3-kio-round26-remediation.md",
    "docs/status/2026-09-11.md",
    "docs/decisions/ADR-0001-authority-provider.md",
    "docs/decisions/ADR-0003-kde-integration-frontier.md",
    "docs/runners/ubuntu-26.04.md",
    "docs/runners/provisioning.md",
    "docs/runners/host-kvm.md",
    "manifests/authoritative-kvm-certification.json",
    "scripts/validate_authoritative_kvm_certification.py",
    "docs/qt-provider-certification.md",
    "scripts/validate_qt_provider.py",
    "scripts/run-qt-provider-preflight.sh",
    "scripts/qt-provider-preflight-needed.sh",
    "scripts/check-kvm-host.sh",
    "scripts/prepare-libguestfs-runtime.sh",
    "scripts/with-libguestfs-runtime.sh",
    "scripts/test-with-libguestfs-runtime.sh",
    "scripts/check-golden-preparation-lifecycle.sh",
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
    "scripts/test-install-actions-runner-staging.sh",
    "scripts/provision-authoritative-runner-guest.sh",
    "scripts/check-autopkgtest-workspace.sh",
    "scripts/test-autopkgtest-workspace-contract.sh",
    "scripts/prepare-autopkgtest-qemu-image.sh",
    "scripts/seal-authoritative-runner-image.sh",
    "scripts/qemu-kvm-required.sh",
    "scripts/test-qemu-kvm-required.sh",
    "scripts/run-kvm-jit-gate.sh",
    "scripts/run-kvm-jit-gate-core.sh",
    "scripts/run-authoritative-kvm-certification.sh",
    "scripts/run-authoritative-package-proof.sh",
    "scripts/run-authoritative-frameworks-sample-proof.sh",
    "manifests/kde-frameworks-tier2.json",
    "manifests/kde-frameworks-tier2-dependencies.json",
    "manifests/kde-tier2-global-discovery.json",
    "scripts/validate_kde_tier2.py",
    "docs/kde-tier2.md",
    "docs/kde-tier2-dependencies.md",
    "docs/decisions/ADR-0002-kmime-frameworks-transition.md",
]
for relative in required_files:
    require((ROOT / relative).exists(), f"required architecture/runner file missing: {relative}")

package_delta = read_required("scripts/package-preflight-needed.sh")
for tracked in ("packages/supralinux-build-test/*", "scripts/run-package-build-proof.sh", ".github/workflows/package-build-proof.yml"):
    require(tracked in package_delta, f"package preflight delta detector must track {tracked}")

host_provisioner = read_required("scripts/provision-kvm-host.sh")
for package in ("libvirt-daemon-system", "qemu-system-x86", "virt-install", "libguestfs-tools", "supermin"):
    require(package in host_provisioner, f"host provisioning must install {package}")
require("does NOT change BIOS" in host_provisioner, "host provisioning must not silently alter BIOS/KVM module state")
require("/var/lib/supralinux/golden-builds" in host_provisioner, "host provisioning must create golden-build state")
require("scripts/prepare-libguestfs-runtime.sh" in host_provisioner, "host provisioning must prepare the private libguestfs kernel runtime")
require("sudo env LC_ALL=C virsh" in host_provisioner, "host provisioning must parse libvirt output under a deterministic C locale")
require("LIBVIRT_QEMU_USER" in host_provisioner and 'id -gn "${LIBVIRT_QEMU_USER}"' in host_provisioner, "host provisioning must resolve the effective libvirt QEMU group")
require('for group_name in kvm libvirt "${LIBVIRT_QEMU_GROUP}"' in host_provisioner, "host provisioning must grant operator access to kvm, libvirt and the effective libvirt QEMU group")

libguestfs_prepare = read_required("scripts/prepare-libguestfs-runtime.sh")
for token, message in (
    ("/boot/vmlinuz-", "libguestfs runtime preparation must bind the current host kernel"),
    ("sudo sha256sum", "libguestfs runtime preparation must hash the root-only host kernel"),
    ("modules.dep", "libguestfs runtime preparation must bind the matching module tree"),
    ("kernel_sha256=", "libguestfs runtime preparation must record kernel provenance"),
):
    require(token in libguestfs_prepare, message)

libguestfs_wrapper = read_required("scripts/with-libguestfs-runtime.sh")
for token, message in (
    ("SUPERMIN_KERNEL", "libguestfs wrapper must select the prepared private kernel"),
    ("SUPERMIN_KERNEL_VERSION", "libguestfs wrapper must bind the host kernel version"),
    ("SUPERMIN_MODULES", "libguestfs wrapper must bind matching kernel modules"),
    ("LIBGUESTFS_CACHEDIR", "libguestfs wrapper must isolate the supermin cache"),
    ("source_kernel_stat", "libguestfs wrapper must reject host-kernel drift"),
    ("modules_dep_sha256", "libguestfs wrapper must reject module-tree drift"),
):
    require(token in libguestfs_wrapper, message)

libguestfs_wrapper_test = read_required("scripts/test-with-libguestfs-runtime.sh")
require("Libguestfs private-kernel runtime wrapper functional test: PASS" in libguestfs_wrapper_test, "libguestfs wrapper functional test must emit PASS")

host_checker = read_required("scripts/check-kvm-host.sh")
for token in ("/dev/kvm", "parameters/nested", "qemu:///system", "virt-sysprep", "virt-cat", "virt-copy-out", "flock", "with-libguestfs-runtime.sh"):
    require(token in host_checker, f"host preflight missing required check: {token}")
require("env LC_ALL=C virsh" in host_checker, "host preflight must parse libvirt output under a deterministic C locale")

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
    ("--noreboot", "golden builder must prevent virt-install from rebooting after cloud-init powers the preparation VM off"),
    ("LIBVIRT_QEMU_USER", "golden builder must resolve the system libvirt QEMU identity"),
    ('chmod 0710 "${BUILD_DIR}"', "golden builder must grant only group traversal on its private build directory"),
    ('chmod 0660 "${WORK_DISK}"', "golden builder must grant only owner/group access to the writable overlay"),
    ("libvirt-storage-access.txt", "golden builder must retain libvirt storage-access evidence"),
    ("with-libguestfs-runtime.sh", "golden builder must use the certified non-root libguestfs runtime"),
):
    require(token in golden_builder, message)
require("machine-id" in golden_builder and "ssh-hostkeys" in golden_builder, "golden builder must reset machine and SSH identities")

golden_lifecycle_preflight = read_required("scripts/check-golden-preparation-lifecycle.sh")
for token, message in (
    ("scripts/check-kvm-host.sh", "golden lifecycle preflight must require the certified KVM host contract"),
    ("/var/lib/supralinux/golden-builds/lifecycle-preflight", "golden lifecycle preflight state must stay under the provisioned operator-owned golden-build root"),
    ("scripts/verify-ubuntu-cloud-image-provenance.sh", "golden lifecycle preflight must reverify the signed Ubuntu source image"),
    ('chmod 0710 "${BUILD_DIR}"', "golden lifecycle preflight must exercise scoped build-directory traversal"),
    ('chmod 0660 "${WORK_DISK}"', "golden lifecycle preflight must exercise scoped writable-overlay access"),
    ("--noreboot", "golden lifecycle preflight must test virt-install no-reboot semantics"),
    ('[[ "${DOMAIN_STATE}" != "shut off" ]]', "golden lifecycle preflight must fail unless the domain remains shut off"),
    ("status=PASS", "golden lifecycle preflight must verify a guest-written completion marker"),
    ("libguestfs-test-tool", "golden lifecycle preflight must execute the real libguestfs appliance"),
    ("with-libguestfs-runtime.sh", "golden lifecycle preflight must inspect the guest through the certified libguestfs runtime"),
    ("Golden preparation lifecycle synthetic preflight: PASS", "golden lifecycle preflight must emit explicit PASS evidence"),
):
    require(token in golden_lifecycle_preflight, message)

verify_pos = golden_builder.find("scripts/verify-ubuntu-cloud-image-provenance.sh")
inspect_pos = golden_builder.find('SOURCE_FORMAT="$(qemu-img info')
require(verify_pos >= 0 and inspect_pos >= 0 and verify_pos < inspect_pos, "golden builder must reverify source integrity before qemu-img inspects the source image")

installer = read_required("scripts/install-actions-runner.sh")
require(".digest" in installer and "sha256sum --check --strict" in installer, "Actions runner archive must use GitHub-published SHA-256 verification")
for token, message in (
    ('TARGET_GROUP="$(id -gn "${TARGET_USER}")"', "Actions runner installer must resolve the target user primary group"),
    ('sudo chown "${TARGET_USER}:${TARGET_GROUP}" "${TMP_DIR}"', "Actions runner staging directory must be owned by the extraction user"),
    ('sudo chmod 0700 "${TMP_DIR}"', "Actions runner staging directory must remain private"),
    ('sudo -u "${TARGET_USER}" tar -xzf "${ARCHIVE}"', "Actions runner archive must still be extracted non-root"),
):
    require(token in installer, message)
require(
    installer.find('sudo chown "${TARGET_USER}:${TARGET_GROUP}" "${TMP_DIR}"')
    < installer.find('sudo -u "${TARGET_USER}" tar -xzf'),
    "Actions runner staging ownership must precede non-root extraction",
)

runner_staging_test = read_required("scripts/test-install-actions-runner-staging.sh")
require(
    "Actions runner non-root staging functional test: PASS" in runner_staging_test,
    "Actions runner staging functional test must emit PASS",
)

guest_provisioner = read_required("scripts/provision-authoritative-runner-guest.sh")
for token, message in (
    ("genisoimage", "authoritative guest provisioning must install genisoimage"),
    ("/var/lib/supralinux/autopkgtest/work", "authoritative guest provisioning must create persistent autopkgtest work storage"),
    ('-o "${TARGET_USER}"', "autopkgtest work storage must be owned by the runner user"),
):
    require(token in guest_provisioner, message)

autopkgtest_workspace = read_required("scripts/check-autopkgtest-workspace.sh")
for token, message in (
    ("21474836480", "autopkgtest workspace preflight must require at least 20 GiB by default"),
    ("tmpfs", "autopkgtest workspace preflight must reject memory-backed tmpfs"),
    ("free_bytes=", "autopkgtest workspace preflight must report available bytes"),
    ("status=PASS", "autopkgtest workspace preflight must emit explicit PASS"),
):
    require(token in autopkgtest_workspace, message)

autopkgtest_prep = read_required("scripts/prepare-autopkgtest-qemu-image.sh")
for token, message in (
    ("AUTOPKGTEST_QEMU_WORK_ROOT:-/var/lib/supralinux/autopkgtest/work", "autopkgtest image preparation must use persistent guest storage by default"),
    ("scripts/check-autopkgtest-workspace.sh", "autopkgtest image preparation must preflight its work filesystem"),
    ("genisoimage", "autopkgtest image preparation must require genisoimage"),
    ('--disk-size="${DISK_SIZE}"', "autopkgtest image preparation must explicitly bind image disk size"),
    ("AUTOPKGTEST_QEMU_RAM_MIB:-2048", "autopkgtest image preparation must preserve the upstream 2048 MiB nested RAM floor"),
    ("AUTOPKGTEST_QEMU_BUILD_SWAP_MIB:-4096", "autopkgtest image preparation must provide at least 4 GiB temporary outer-guest swap"),
    ('sudo swapon "${BUILD_SWAP_FILE}"', "autopkgtest image preparation must activate temporary build swap"),
    ('sudo swapon --show=NAME,SIZE --bytes --noheadings --raw', "autopkgtest image preparation must validate the exact active swap file and usable size"),
    ("MIN_ACTIVE_SWAP_BYTES", "autopkgtest image preparation must tolerate only the reserved swap metadata page"),
    ("temporary_build_swap_active_bytes=", "autopkgtest image preparation must retain exact active swap-size evidence"),
    ('sudo swapoff "${BUILD_SWAP_FILE}"', "autopkgtest image preparation must deactivate temporary build swap"),
    ("autopkgtest-build-resources.txt", "autopkgtest image preparation must retain resource evidence"),
    ('--ram-size="${RAM_SIZE}"', "autopkgtest image preparation must explicitly bind nested QEMU RAM"),
):
    require(token in autopkgtest_prep, message)

autopkgtest_workspace_test = read_required("scripts/test-autopkgtest-workspace-contract.sh")
require(
    "Autopkgtest persistent-workspace contract test: PASS" in autopkgtest_workspace_test,
    "autopkgtest workspace contract test must emit PASS",
)

golden_sealer = read_required("scripts/seal-authoritative-runner-image.sh")
for token, message in (
    ("AUTOPKGTEST_QEMU_BUILD_SWAP_FILE:-/var/lib/supralinux/autopkgtest/.build.swap", "golden sealing must bind the temporary build-swap path"),
    ("swapon --show=NAME --noheadings", "golden sealing must reject an active temporary build swap"),
    ("temporary_build_swap_absent=yes", "golden seal evidence must prove temporary build swap removal"),
):
    require(token in golden_sealer, message)

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

golden_input_fingerprint = read_required("scripts/golden-image-input-digest.sh")
for token, message in (
    ("FINGERPRINT_SCHEMA=1", "golden input fingerprint schema must be versioned"),
    ("scripts/golden-image-input-digest.sh", "golden input fingerprint must bind its own definition"),
    ("scripts/build-authoritative-runner-image.sh", "golden input fingerprint must bind the golden builder"),
    ("scripts/with-libguestfs-runtime.sh", "golden input fingerprint must bind offline libguestfs behavior"),
    ("scripts/provision-authoritative-runner-guest.sh", "golden input fingerprint must bind guest provisioning"),
    ("scripts/install-actions-runner.sh", "golden input fingerprint must bind Actions runner installation"),
    ("scripts/check-autopkgtest-workspace.sh", "golden input fingerprint must bind nested autopkgtest workspace admission"),
    ("scripts/prepare-autopkgtest-qemu-image.sh", "golden input fingerprint must bind nested autopkgtest image preparation"),
    ("scripts/seal-authoritative-runner-image.sh", "golden input fingerprint must bind golden sealing"),
    ("scripts/verify-ubuntu-cloud-image-provenance.sh", "golden input fingerprint must bind Ubuntu source verification"),
):
    require(token in golden_input_fingerprint, message)

golden_provenance_checker = read_required("scripts/check-golden-image-provenance.sh")
for token, message in (
    ("golden_image_sha256", "golden provenance checker must require the published golden hash"),
    ("source_image_sha256", "golden provenance checker must require the verified source-image hash"),
    ("source_commit", "golden provenance checker must retain the historical source commit"),
    ("source_checkout_removed", "golden provenance checker must require source-checkout cleanup"),
    ("source_image_provenance_verified", "golden provenance checker must require signed source-image re-verification"),
    ("golden_input_fingerprint_schema", "golden provenance checker must require the input fingerprint schema"),
    ("golden_input_digest", "golden provenance checker must require the golden-input digest"),
    ("CURRENT_INPUT_DIGEST", "golden provenance checker must recompute current golden inputs"),
    ("SUPRALINUX_GOLDEN_COMPAT_COMMIT", "golden provenance checker must bind compatibility to an explicit checkout commit"),
    ("golden_input_compatibility=PASS", "golden provenance checker must emit explicit input-compatibility evidence"),
    ("ACTUAL_GOLDEN_SHA256", "golden provenance checker must hash the current image bytes"),
    ("golden_provenance_verification=PASS", "golden provenance checker must emit explicit PASS evidence"),
):
    require(token in golden_provenance_checker, message)

golden_provenance_test = read_required("scripts/test-check-golden-image-provenance.sh")
for token, message in (
    ("Accepted modified golden bytes.", "golden provenance test must reject modified golden bytes"),
    ("Accepted missing signed-source proof.", "golden provenance test must reject missing signed-source proof"),
    ("Accepted missing source cleanup.", "golden provenance test must reject missing cleanup proof"),
    ("Accepted duplicate golden hash.", "golden provenance test must reject ambiguous golden hashes"),
    ("Accepted truncated source commit.", "golden provenance test must reject invalid source commit evidence"),
    ("Accepted unsupported fingerprint schema.", "golden provenance test must reject an unsupported fingerprint schema"),
    ("Accepted stale golden inputs.", "golden provenance test must reject stale golden-relevant inputs"),
    ("Accepted duplicate input digest.", "golden provenance test must reject ambiguous golden-input digests"),
    ("Golden image provenance functional test: PASS", "golden provenance test must emit explicit PASS evidence"),
):
    require(token in golden_provenance_test, message)

host_entrypoint = read_required("scripts/run-kvm-jit-gate.sh")
require("scripts/run-kvm-jit-gate-core.sh" in host_entrypoint, "JIT entrypoint must delegate to the fail-closed core")
require('exec "${ROOT}/scripts/run-kvm-jit-gate-core.sh" "$@"' in host_entrypoint, "JIT entrypoint must preserve arguments when delegating to the core")

host_orchestrator = read_required("scripts/run-kvm-jit-gate-core.sh")
for token, message in (
    ("generate-jitconfig", "host orchestrator must use JIT configuration"),
    ('RUNNER_ORGANIZATION="${SUPRALINUX_RUNNER_ORGANIZATION:-${REPOSITORY%%/*}}"', "host orchestrator must bind JIT runners to the repository-owning organization"),
    ('/orgs/${RUNNER_ORGANIZATION}/actions/runners/generate-jitconfig', "host orchestrator must create JIT runners through the organization scope"),
    ('/orgs/${RUNNER_ORGANIZATION}/actions/runners?per_page=100', "host orchestrator must observe JIT runners through the organization scope"),
    ("jit-create-reconciliation.json", "host orchestrator must reconcile ambiguous JIT creation side effects"),
    ("jit-create-transport.txt", "host orchestrator must retain non-secret JIT transport evidence"),
    ("SUPRALINUX_JIT_STARTUP_PREFLIGHT", "host orchestrator must support an isolated JIT startup preflight"),
    ("jit-config-write.json", "host orchestrator must retain QGA JIT write evidence"),
    ("guest-file-flush", "host orchestrator must flush JIT config before runner startup"),
    ("WRITTEN_BYTES", "host orchestrator must validate the exact JIT config byte count"),
    ("JIT runner startup synthetic preflight: PASS", "host orchestrator must expose a workflow-free startup PASS point"),
    ("/run/supralinux-jit", "JIT config must live in a private guest tmpfs directory"),
    ('"-o",$user,"-g",$user,"-m","0700"', "JIT tmpfs directory must be private and runner-owned"),
    ("rmdir ${JIT_CONFIG_DIR}", "guest runner startup must remove the private JIT tmpfs directory before the job loop"),
    ("LC_ALL=C virsh domstate", "guest cleanup must use locale-stable libvirt domain states"),
    ("Authoritative self-hosted gates refuse fork PRs", "host orchestrator must refuse fork PRs"),
    ('[[ ! "${REPOSITORY}" =~ ^[^/]+/[^/]+$ ]]', "host orchestrator must validate owner/repo syntax without rejecting matching owner and repository names"),
    ("flock -n", "host orchestrator must serialize local authoritative jobs"),
    ("workflow-baseline-ids.json", "host orchestrator must snapshot workflow IDs before triggering"),
    ("head_sha=${PR_HEAD_SHA}", "host orchestrator must query the exact PR head SHA"),
    ("actions/runs/${WORKFLOW_RUN_ID}", "host orchestrator must bind an exact workflow run ID"),
    ("ci:frameworks-sample-proof", "host orchestrator must support the Frameworks sample gate"),
    ("KDE Frameworks authoritative KVM sample proof", "host orchestrator must bind the Frameworks sample workflow"),
    ("guest-exec-status", "host orchestrator must detect premature runner exit"),
    ("PROVENANCE_SHA256", "host orchestrator core must verify the golden image against provenance"),
    ("source_checkout_removed=yes", "host orchestrator core must require a source-clean golden image"),
    ('LOCAL_HEAD="$(git -C "${ROOT}" rev-parse HEAD)"', "host orchestrator must bind the local checkout HEAD"),
    ('"${LOCAL_HEAD,,}" != "${PR_HEAD_SHA,,}"', "host orchestrator must require local HEAD to equal the PR head"),
    ("status --porcelain --untracked-files=normal", "host orchestrator must require a clean checkout"),
    ("SUPRALINUX_GOLDEN_COMPAT_COMMIT", "host orchestrator must admit golden compatibility against the exact PR head"),
    ("scripts/check-golden-image-provenance.sh", "host orchestrator core must run the golden provenance/input-compatibility gate"),
    ("GOLDEN_SOURCE_COMMIT", "host orchestrator must retain the golden source commit as historical provenance"),
    ("GOLDEN_INPUT_DIGEST", "host orchestrator must retain the golden-input digest"),
    ("with-libguestfs-runtime.sh", "host orchestrator must use the certified libguestfs runtime for offline evidence extraction"),
    ('chmod 0710 "${RUN_DIR}"', "host orchestrator must grant only group traversal to the JIT run directory"),
    ('chmod 0660 "${OVERLAY}"', "host orchestrator must grant only owner/group access to the JIT overlay"),
    ("su --login --shell /bin/bash --command", "guest runner must start non-root with an explicit login shell"),
):
    require(token in host_orchestrator, message)
require(
    '/repos/${REPOSITORY}/actions/runners/generate-jitconfig' not in host_orchestrator,
    "host orchestrator must not use repository-scoped JIT creation for the organization runner group",
)

jit_api_preflight = read_required("scripts/check-jit-runner-api-lifecycle.sh")
for token, message in (
    ('/orgs/${RUNNER_ORGANIZATION}/actions/runners/generate-jitconfig', "JIT API preflight must exercise organization-scoped JIT creation"),
    ("matching-runners.json", "JIT API preflight must reconcile exact-name side effects"),
    ("status=INFRA_INVALID", "JIT API preflight must classify ambiguous transport as INFRA_INVALID"),
    ("JIT API lifecycle synthetic preflight: PASS", "JIT API preflight must emit explicit PASS"),
):
    require(token in jit_api_preflight, message)
require(
    '/repos/${REPOSITORY}/actions/runners/generate-jitconfig' not in jit_api_preflight,
    "JIT API preflight must not fall back to repository-scoped JIT creation",
)

jit_startup_preflight = read_required("scripts/check-jit-runner-startup-lifecycle.sh")
for token, message in (
    ("SUPRALINUX_JIT_STARTUP_PREFLIGHT=1", "JIT startup preflight must enable the isolated startup mode"),
    ('run-kvm-jit-gate.sh" runner-contract', "JIT startup preflight must reuse the runner-contract infrastructure path"),
):
    require(token in jit_startup_preflight, message)

certification_orchestrator = read_required("scripts/run-authoritative-kvm-certification.sh")
for token, message in (
    ('LOCAL_HEAD="$(git -C "${ROOT}" rev-parse HEAD)"', "certification orchestrator must bind the local checkout HEAD"),
    ('"${LOCAL_HEAD,,}" == "${PR_HEAD_SHA,,}"', "certification orchestrator must require local HEAD to equal PR head"),
    ('status --porcelain --untracked-files=normal', "certification orchestrator must require a clean checkout"),
    ("scripts/check-kvm-host.sh", "certification orchestrator must run real host KVM preflight"),
    ("scripts/verify-ubuntu-cloud-image-provenance.sh", "certification orchestrator must verify the Ubuntu source image"),
    ("SUPRALINUX_REBUILD_GOLDEN", "golden replacement must require explicit certification-run opt-in"),
    ("scripts/build-authoritative-runner-image.sh", "certification orchestrator must build the golden image through the supported builder"),
    ("scripts/check-golden-image-provenance.sh", "certification orchestrator must admit the exact golden bytes"),
    ("SUPRALINUX_GOLDEN_COMPAT_COMMIT", "certification orchestrator must bind golden admission to the current PR head"),
    ("golden_input_digest", "certification orchestrator must retain the admitted golden-input digest"),
    ("run_gate runner-contract", "certification orchestrator must run runner-contract"),
    ("run_gate authoritative-package-proof", "certification orchestrator must run the synthetic package proof"),
    ("run_gate frameworks-sample-proof", "certification orchestrator must run the Frameworks sample"),
    ("certification-result.json", "certification orchestrator must emit machine-readable final evidence"),
    ("gate-results.json", "certification orchestrator must aggregate exact workflow run IDs"),
    ('"canonical_state_effect": "none"', "certification orchestrator must not mutate canonical package state"),
    ('"stable_publication_authorized": False', "certification orchestrator must not authorize stable publication"),
):
    require(token in certification_orchestrator, message)
require(
    certification_orchestrator.index("run_gate runner-contract")
    < certification_orchestrator.index("run_gate authoritative-package-proof")
    < certification_orchestrator.index("run_gate frameworks-sample-proof"),
    "authoritative certification gates must execute in strict order",
)
require("git commit" not in certification_orchestrator and "git push" not in certification_orchestrator, "certification orchestrator must never commit or push evidence automatically")

authoritative_proof = read_required("scripts/run-authoritative-package-proof.sh")
require("scripts/check-actions-runner-runtime.sh" in authoritative_proof, "authoritative proof must verify effective Actions runner provenance")
require("actions-runner-runtime.txt" in authoritative_proof, "authoritative proof must retain effective Actions runner evidence")
require("scripts/check-nested-kvm-runtime.sh" in authoritative_proof, "authoritative proof must run the nested-KVM runtime probe")
require('--qemu-command="${KVM_QEMU_WRAPPER}"' in authoritative_proof, "authoritative autopkgtest must use the KVM-only QEMU wrapper")
require("--qemu-architecture=x86_64" in authoritative_proof, "authoritative autopkgtest must pin QEMU architecture")
require("qemu-kvm-wrapper-sha256.txt" in authoritative_proof, "authoritative evidence must hash the QEMU wrapper")
require('"system_test_acceleration": "kvm-required"' in authoritative_proof, "authoritative result must record KVM-required acceleration")

frameworks_sample = read_required("scripts/run-authoritative-frameworks-sample-proof.sh")
require("scripts/check-actions-runner-runtime.sh" in frameworks_sample, "Frameworks sample must verify effective Actions runner provenance")
require("scripts/check-nested-kvm-runtime.sh" in frameworks_sample, "Frameworks sample must prove nested-KVM runtime on the sample guest")
require('"run_kind": "authoritative-certification-sample"' in frameworks_sample, "Frameworks sample must classify itself as certification evidence")
require('"package_state_effect": "none"' in frameworks_sample, "Frameworks sample must not mutate canonical package state")
require('KARCHIVE_VERSION="6.30.0-0supralinux4"' in frameworks_sample and 'kf6-karchive_${KARCHIVE_VERSION}.dsc' in frameworks_sample, "Frameworks sample must bind KArchive 6.30.0-0supralinux4")
require("extra-cmake-modules_" in frameworks_sample and "6.30.0-0supralinux3" in frameworks_sample, "Frameworks sample must bind the retained ECM 6.30 predecessor")
require('--extra-package="${ECM_DEB}"' in frameworks_sample, "Frameworks sample sbuild must inject the exact ECM predecessor")
require("100% tests passed, 0 tests failed out of 5" in frameworks_sample, "Frameworks sample must prove KArchive upstream tests")
require("STAGE=\"artifact-capture\"" in frameworks_sample and "STAGE=\"lintian\"" in frameworks_sample, "Frameworks sample must retain outputs before post-build validation")
require(frameworks_sample.index('STAGE="artifact-capture"') < frameworks_sample.index('STAGE="lintian"'), "Frameworks sample artifact capture must precede Lintian")

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
print(f"Selection: {selection['objective']} / compatibility-hard-gate={compat['hard_gate']}")
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
    "qt-provider-policy=required; shell-syntax=required; shellcheck=required; pr-ci-router=required".format(
        hosted=hosted["role"],
        platform=authoritative["platform"],
        virt=authoritative["virtualization"],
        lifecycle=authoritative["lifecycle"],
        build=authoritative["build_isolation"],
        test=authoritative["system_test"],
    )
)

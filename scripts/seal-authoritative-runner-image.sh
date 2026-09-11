#!/usr/bin/env bash
set -Eeuo pipefail

RUNNER_DIR="${SUPRALINUX_ACTIONS_RUNNER_DIR:-/opt/actions-runner}"
AUTOPKGTEST_IMAGE="${AUTOPKGTEST_QEMU_IMAGE:-/var/lib/supralinux/autopkgtest/resolute-amd64.img}"
EVIDENCE_DIR="${SUPRALINUX_EVIDENCE_DIR:-/var/lib/supralinux/evidence}"

. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Expected Ubuntu 26.04; got %s %s\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi
if [[ "$(systemd-detect-virt --vm 2>/dev/null || true)" != "kvm" ]]; then
    printf 'Golden runner image must be sealed inside its KVM preparation VM.\n' >&2
    exit 1
fi
if [[ ! -x "${RUNNER_DIR}/run.sh" ]]; then
    printf 'GitHub Actions runner is not installed at %s.\n' "${RUNNER_DIR}" >&2
    exit 1
fi
if [[ ! -f "${AUTOPKGTEST_IMAGE}" ]]; then
    printf 'Missing prepared autopkgtest QEMU image: %s\n' "${AUTOPKGTEST_IMAGE}" >&2
    exit 1
fi
if [[ ! -f "${EVIDENCE_DIR}/actions-runner.txt" ]]; then
    printf 'Missing Actions runner provenance evidence.\n' >&2
    exit 1
fi

sudo install -d -m 0755 "${EVIDENCE_DIR}"
SEAL_TMP="$(mktemp)"
trap 'rm -f "${SEAL_TMP}"' EXIT
{
    printf 'sealed_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'platform=Ubuntu 26.04 LTS\n'
    printf 'virtualization=kvm\n'
    printf 'kernel=%s\n' "$(uname -r)"
    printf 'actions_runner_evidence_sha256='; sha256sum "${EVIDENCE_DIR}/actions-runner.txt" | awk '{print $1}'
    printf 'autopkgtest_image_sha256='; sha256sum "${AUTOPKGTEST_IMAGE}" | awk '{print $1}'
    printf '\nactions_runner:\n'
    cat "${EVIDENCE_DIR}/actions-runner.txt"
    printf '\nautopkgtest_image:\n'
    qemu-img info "${AUTOPKGTEST_IMAGE}"
} > "${SEAL_TMP}"
sudo install -m 0644 "${SEAL_TMP}" "${EVIDENCE_DIR}/base-image-seal.txt"

sudo rm -f \
    "${RUNNER_DIR}/.runner" \
    "${RUNNER_DIR}/.credentials" \
    "${RUNNER_DIR}/.credentials_rsaparams"
sudo rm -rf "${RUNNER_DIR}/_work" "${RUNNER_DIR}/_diag"
sudo apt-get clean

if command -v cloud-init >/dev/null 2>&1; then
    sudo cloud-init clean --logs --machine-id
else
    printf 'cloud-init is required to safely reset clone identity.\n' >&2
    exit 1
fi

sudo rm -f /var/log/supralinux-actions-runner-console.log
sync

printf 'Golden image sealed. Power this preparation VM off now; do not boot the golden disk again before cloning it.\n'
printf 'Seal evidence: %s/base-image-seal.txt\n' "${EVIDENCE_DIR}"

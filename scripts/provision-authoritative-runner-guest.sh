#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER="${SUPRALINUX_RUNNER_USER:-${SUDO_USER:-${USER}}}"

if [[ "${EUID}" -eq 0 && -z "${SUDO_USER:-}" && -z "${SUPRALINUX_RUNNER_USER:-}" ]]; then
    printf 'Run as the intended runner user with sudo, or set SUPRALINUX_RUNNER_USER.\n' >&2
    exit 1
fi

. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Expected Ubuntu 26.04; got %s %s\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi

VIRT="$(systemd-detect-virt --vm 2>/dev/null || true)"
if [[ "${VIRT}" != "kvm" ]]; then
    printf 'This image must be prepared inside a KVM guest; detected: %s\n' "${VIRT:-none}" >&2
    exit 1
fi

if ! id "${TARGET_USER}" >/dev/null 2>&1; then
    printf 'Intended runner user does not exist: %s\n' "${TARGET_USER}" >&2
    exit 1
fi

printf 'Provisioning SupraLINUX authoritative runner guest for user %s...\n' "${TARGET_USER}"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    aptly \
    autopkgtest \
    build-essential \
    ca-certificates \
    curl \
    debhelper \
    devscripts \
    dpkg-dev \
    git \
    gnupg \
    jq \
    mmdebstrap \
    openssh-server \
    python3 \
    qemu-guest-agent \
    qemu-system-x86 \
    qemu-utils \
    sbuild \
    uidmap \
    ubuntu-keyring

if ! grep -q "^${TARGET_USER}:" /etc/subuid; then
    sudo usermod --add-subuids 100000-165535 "${TARGET_USER}"
fi
if ! grep -q "^${TARGET_USER}:" /etc/subgid; then
    sudo usermod --add-subgids 100000-165535 "${TARGET_USER}"
fi

if getent group kvm >/dev/null 2>&1; then
    sudo usermod -aG kvm "${TARGET_USER}"
else
    printf 'Expected kvm group is missing.\n' >&2
    exit 1
fi

sudo systemctl enable ssh qemu-guest-agent
sudo systemctl restart ssh
sudo systemctl restart qemu-guest-agent || true

sudo install -d -m 0755 /var/lib/supralinux/autopkgtest
sudo install -d -m 0755 /var/lib/supralinux/evidence

SUPRALINUX_RUNNER_USER="${TARGET_USER}" "${ROOT}/scripts/install-actions-runner.sh"

{
    printf 'prepared_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'user=%s\n' "${TARGET_USER}"
    printf 'virtualization=%s\n' "${VIRT}"
    printf '\nos-release:\n'
    cat /etc/os-release
    printf '\nuname:\n'
    uname -a
    printf '\npackages:\n'
    dpkg-query -W -f='${Package}\t${Version}\n' \
        aptly autopkgtest build-essential ca-certificates curl debhelper devscripts \
        dpkg-dev git gnupg jq mmdebstrap openssh-server python3 qemu-guest-agent \
        qemu-system-x86 qemu-utils sbuild uidmap ubuntu-keyring
} | sudo tee /var/lib/supralinux/evidence/runner-guest-provisioning.txt >/dev/null

printf '\nGuest tooling and verified Actions runner installed.\n'
printf 'A new login/session is required for kvm group membership to apply.\n'
printf 'After that, verify /dev/kvm and run scripts/prepare-autopkgtest-qemu-image.sh.\n'
printf 'GitHub JIT configuration is intentionally generated on the libvirt host at VM runtime.\n'

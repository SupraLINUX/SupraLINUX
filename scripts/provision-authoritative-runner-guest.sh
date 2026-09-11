#!/usr/bin/env bash
set -Eeuo pipefail

TARGET_USER="${SUDO_USER:-${USER}}"

if [[ "${EUID}" -eq 0 && -z "${SUDO_USER:-}" ]]; then
    printf 'Run this script as the intended runner user with sudo available, not as a direct root login.\n' >&2
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

printf 'Provisioning SupraLINUX authoritative runner guest for user %s...\n' "${TARGET_USER}"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    aptly \
    autopkgtest \
    build-essential \
    debhelper \
    devscripts \
    dpkg-dev \
    git \
    gnupg \
    jq \
    mmdebstrap \
    python3 \
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

sudo install -d -m 0755 /var/lib/supralinux/autopkgtest
sudo install -d -m 0755 /var/lib/supralinux/evidence

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
        aptly autopkgtest build-essential debhelper devscripts dpkg-dev git gnupg jq \
        mmdebstrap python3 qemu-system-x86 qemu-utils sbuild uidmap ubuntu-keyring
} | sudo tee /var/lib/supralinux/evidence/runner-guest-provisioning.txt >/dev/null

printf '\nGuest tooling provisioned.\n'
printf 'A new login/session is required for kvm group membership to apply.\n'
printf 'After that, verify /dev/kvm access and run scripts/prepare-autopkgtest-qemu-image.sh.\n'
printf 'GitHub runner registration is intentionally separate because it requires a short-lived registration/JIT token.\n'

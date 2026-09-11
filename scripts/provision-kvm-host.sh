#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER="${SUPRALINUX_HOST_USER:-${SUDO_USER:-${USER}}}"
LIBVIRT_URI="${SUPRALINUX_LIBVIRT_URI:-qemu:///system}"
LIBVIRT_NETWORK="${SUPRALINUX_LIBVIRT_NETWORK:-default}"
EVIDENCE_DIR="${SUPRALINUX_HOST_SETUP_EVIDENCE_DIR:-/var/lib/supralinux/evidence/host-setup}"

if [[ "${EUID}" -eq 0 && -z "${SUDO_USER:-}" && -z "${SUPRALINUX_HOST_USER:-}" ]]; then
    printf 'Run as the intended host orchestration user with sudo, or set SUPRALINUX_HOST_USER.\n' >&2
    exit 1
fi

. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Supported host bootstrap recipe requires Ubuntu 26.04; got %s %s.\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi
if [[ "$(uname -m)" != "x86_64" ]]; then
    printf 'Supported authoritative host bootstrap recipe currently requires x86_64.\n' >&2
    exit 1
fi
if ! id "${TARGET_USER}" >/dev/null 2>&1; then
    printf 'Host orchestration user does not exist: %s\n' "${TARGET_USER}" >&2
    exit 1
fi
if ! grep -Eq '\b(vmx|svm)\b' /proc/cpuinfo; then
    printf 'CPU virtualization extensions are not visible. Check BIOS/firmware or outer-hypervisor settings before continuing.\n' >&2
    exit 1
fi

printf 'Installing Ubuntu 26.04 KVM/libvirt host tooling...\n'
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    cpu-checker \
    curl \
    gnupg \
    jq \
    libguestfs-tools \
    libvirt-clients \
    libvirt-daemon-system \
    qemu-system-x86 \
    qemu-utils \
    ubuntu-keyring \
    virt-install

for group_name in kvm libvirt; do
    if ! getent group "${group_name}" >/dev/null 2>&1; then
        printf 'Expected group is missing after package installation: %s\n' "${group_name}" >&2
        exit 1
    fi
    sudo usermod -aG "${group_name}" "${TARGET_USER}"
done

printf 'Ensuring the standard libvirt network is active and persistent...\n'
if ! sudo virsh --connect "${LIBVIRT_URI}" net-info "${LIBVIRT_NETWORK}" >/dev/null 2>&1; then
    printf 'Expected libvirt network %s is not defined after package installation.\n' "${LIBVIRT_NETWORK}" >&2
    exit 1
fi
if ! sudo virsh --connect "${LIBVIRT_URI}" net-info "${LIBVIRT_NETWORK}" | grep -Eq '^Active:[[:space:]]+yes$'; then
    sudo virsh --connect "${LIBVIRT_URI}" net-start "${LIBVIRT_NETWORK}"
fi
sudo virsh --connect "${LIBVIRT_URI}" net-autostart "${LIBVIRT_NETWORK}"

sudo install -d -m 0755 /var/lib/supralinux/images
sudo install -d -m 0755 /var/lib/supralinux/ephemeral-runners
sudo install -d -m 0755 /var/lib/supralinux/evidence
sudo install -d -m 0755 "${EVIDENCE_DIR}"
sudo chown "${TARGET_USER}:$(id -gn "${TARGET_USER}")" \
    /var/lib/supralinux/images \
    /var/lib/supralinux/ephemeral-runners \
    /var/lib/supralinux/evidence

EVIDENCE_TMP="$(mktemp)"
trap 'rm -f "${EVIDENCE_TMP}"' EXIT
{
    printf 'prepared_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'host_user=%s\n' "${TARGET_USER}"
    printf 'libvirt_uri=%s\n' "${LIBVIRT_URI}"
    printf 'libvirt_network=%s\n' "${LIBVIRT_NETWORK}"
    printf '\nos-release:\n'
    cat /etc/os-release
    printf '\nuname:\n'
    uname -a
    printf '\npackages:\n'
    dpkg-query -W -f='${Package}\t${Version}\n' \
        cpu-checker curl gnupg jq libguestfs-tools libvirt-clients libvirt-daemon-system \
        qemu-system-x86 qemu-utils ubuntu-keyring virt-install
    printf '\nnetwork:\n'
    sudo virsh --connect "${LIBVIRT_URI}" net-info "${LIBVIRT_NETWORK}"
    printf '\nkvm-module-state:\n'
    for nested in /sys/module/kvm_intel/parameters/nested /sys/module/kvm_amd/parameters/nested; do
        if [[ -r "${nested}" ]]; then
            printf '%s=' "${nested}"
            cat "${nested}"
        fi
    done
} > "${EVIDENCE_TMP}"
sudo install -m 0644 "${EVIDENCE_TMP}" "${EVIDENCE_DIR}/provisioning.txt"

printf '\nHost packages and libvirt network are provisioned.\n'
printf 'A new login session is required for kvm/libvirt group membership to apply.\n'
printf 'This script does NOT change BIOS settings or reload KVM modules to force nested virtualization.\n'
printf 'After re-login, run: %s/scripts/check-kvm-host.sh\n' "${ROOT}"

#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER="${SUPRALINUX_HOST_USER:-${SUDO_USER:-${USER}}}"
LIBVIRT_URI="${SUPRALINUX_LIBVIRT_URI:-qemu:///system}"
LIBVIRT_QEMU_USER="${SUPRALINUX_LIBVIRT_QEMU_USER:-libvirt-qemu}"
EVIDENCE_DIR="${SUPRALINUX_HOST_SETUP_EVIDENCE_DIR:-/var/lib/supralinux/evidence/host-setup}"

# This is a host installation entrypoint, never a routine build prerequisite.
# Agents must obtain the operator's specific approval before invoking this flag.
if [[ "$#" != 1 || "$1" != --install-host-tools ]]; then
    printf 'Host package installation requires specific operator permission. Usage after approval: %s --install-host-tools\n' "$0" >&2
    exit 2
fi

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
    acl \
    cloud-image-utils \
    cpu-checker \
    curl \
    genisoimage \
    gnupg \
    jq \
    libguestfs-tools \
    libvirt-clients \
    libvirt-daemon-system \
    qemu-system-x86 \
    qemu-utils \
    supermin \
    ubuntu-keyring \
    virt-install

if ! id "${LIBVIRT_QEMU_USER}" >/dev/null 2>&1; then
    printf 'Configured libvirt QEMU user does not exist after package installation: %s\n' "${LIBVIRT_QEMU_USER}" >&2
    exit 1
fi
LIBVIRT_QEMU_GROUP="$(id -gn "${LIBVIRT_QEMU_USER}")"

declare -A required_groups=()
for group_name in kvm libvirt "${LIBVIRT_QEMU_GROUP}"; do
    required_groups["${group_name}"]=1
done
for group_name in "${!required_groups[@]}"; do
    if ! getent group "${group_name}" >/dev/null 2>&1; then
        printf 'Expected group is missing after package installation: %s\n' "${group_name}" >&2
        exit 1
    fi
    sudo usermod -aG "${group_name}" "${TARGET_USER}"
done

printf 'Guest networking uses bridge-free SLIRP; no libvirt network is started or enabled.\n'
# Package installation can supply a default network definition. Do not start it,
# and never remove an existing shared network from this generic provisioner.
if [[ -n "${SUPRALINUX_LIBVIRT_NETWORK:-}" ]]; then
    printf 'Libvirt/LAN network overrides are forbidden for SupraLINUX.\n' >&2
    exit 1
fi

sudo install -d -m 0755 /var/lib/supralinux/images
sudo install -d -m 0755 /var/lib/supralinux/golden-builds
sudo install -d -m 0755 /var/lib/supralinux/ephemeral-runners
sudo install -d -m 0755 /var/lib/supralinux/evidence
sudo install -d -m 0755 "${EVIDENCE_DIR}"
sudo chown "${TARGET_USER}:$(id -gn "${TARGET_USER}")" \
    /var/lib/supralinux/images \
    /var/lib/supralinux/golden-builds \
    /var/lib/supralinux/ephemeral-runners \
    /var/lib/supralinux/evidence

printf 'Preparing private non-root libguestfs kernel runtime...\n'
SUPRALINUX_HOST_USER="${TARGET_USER}" "${ROOT}/scripts/prepare-libguestfs-runtime.sh"

EVIDENCE_TMP="$(mktemp)"
trap 'rm -f "${EVIDENCE_TMP}"' EXIT
{
    printf 'prepared_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'host_user=%s\n' "${TARGET_USER}"
    printf 'libvirt_uri=%s\n' "${LIBVIRT_URI}"
    printf 'network_backend=slirp\n'
    printf 'libvirt_qemu_user=%s\n' "${LIBVIRT_QEMU_USER}"
    printf 'libvirt_qemu_group=%s\n' "${LIBVIRT_QEMU_GROUP}"
    printf '\nos-release:\n'
    cat /etc/os-release
    printf '\nuname:\n'
    uname -a
    printf '\npackages:\n'
    dpkg-query -W -f='${Package}\t${Version}\n' \
        cloud-image-utils cpu-checker curl genisoimage gnupg jq libguestfs-tools \
        libvirt-clients libvirt-daemon-system qemu-system-x86 qemu-utils supermin ubuntu-keyring virt-install
    printf '\nlibguestfs-runtime:\n'
    cat "/var/lib/supralinux/images/libguestfs-runtime/$(uname -r)/provenance.txt"
    printf '\nnetwork:\n'
    printf 'host_network_creation=forbidden\n'
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

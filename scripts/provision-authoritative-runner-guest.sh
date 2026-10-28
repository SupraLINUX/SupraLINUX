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
TARGET_GROUP="$(id -gn "${TARGET_USER}")"

printf 'Provisioning SupraLINUX authoritative runner guest for user %s...\n' "${TARGET_USER}"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    aptly \
    apparmor \
    autopkgtest \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    debhelper \
    devscripts \
    dpkg-dev \
    git \
    genisoimage \
    gnupg \
    jq \
    lintian \
    mmdebstrap \
    ninja-build \
    openssh-server \
    python3 \
    qemu-guest-agent \
    qemu-system-x86 \
    qemu-utils \
    qt6-base-dev \
    sbuild \
    uidmap \
    ubuntu-keyring

if ! grep -q "^${TARGET_USER}:" /etc/subuid; then
    sudo usermod --add-subuids 100000-165535 "${TARGET_USER}"
fi
if ! grep -q "^${TARGET_USER}:" /etc/subgid; then
    sudo usermod --add-subgids 100000-165535 "${TARGET_USER}"
fi

python3 - "${TARGET_USER}" <<'PY'
import sys
from pathlib import Path

user = sys.argv[1]
for database in ("/etc/subuid", "/etc/subgid"):
    ranges = []
    for raw in Path(database).read_text().splitlines():
        fields = raw.split(":")
        if len(fields) != 3 or fields[0] != user:
            continue
        start, count = map(int, fields[1:])
        ranges.append((start, count))
    assert ranges, f"{database}: no subordinate range for {user}"
    assert any(count >= 65536 for _, count in ranges), (
        f"{database}: {user} lacks a >=65536 subordinate ID range: {ranges}"
    )
PY
command -v newuidmap >/dev/null
command -v newgidmap >/dev/null

UNSHARE_SOURCE="$(command -v unshare)"
UNSHARE_PRIVATE_DIR="/usr/local/libexec/supralinux-autopkgtest"
UNSHARE_PRIVATE="${UNSHARE_PRIVATE_DIR}/unshare"
test "${UNSHARE_SOURCE}" = "/usr/bin/unshare"
sudo install -d -o root -g root -m 0755 "${UNSHARE_PRIVATE_DIR}"
sudo install -o root -g root -m 0755 "${UNSHARE_SOURCE}" "${UNSHARE_PRIVATE}"
test "$(sha256sum "${UNSHARE_SOURCE}" | awk '{print $1}')" = \
     "$(sha256sum "${UNSHARE_PRIVATE}" | awk '{print $1}')"

APPARMOR_PROFILE_SOURCE="${ROOT}/ops/apparmor/supralinux-autopkgtest-virt-unshare"
APPARMOR_PROFILE_TARGET="/etc/apparmor.d/supralinux-autopkgtest-virt-unshare"
test -f "${APPARMOR_PROFILE_SOURCE}"
sudo apparmor_parser -Q "${APPARMOR_PROFILE_SOURCE}"
sudo install -o root -g root -m 0644 "${APPARMOR_PROFILE_SOURCE}" "${APPARMOR_PROFILE_TARGET}"
sudo apparmor_parser -r "${APPARMOR_PROFILE_TARGET}"
if [[ -r /proc/sys/kernel/apparmor_restrict_unprivileged_userns ]]; then
    test "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns)" = "1"
fi
sudo aa-status | grep -Fq 'supralinux-autopkgtest-virt-unshare'

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
sudo install -d -o "${TARGET_USER}" -g "${TARGET_GROUP}" -m 0750 /var/lib/supralinux/autopkgtest/work
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
        apparmor aptly autopkgtest build-essential ca-certificates curl debhelper devscripts \
        cmake dpkg-dev git genisoimage gnupg jq lintian mmdebstrap ninja-build openssh-server python3 qemu-guest-agent \
        qemu-system-x86 qemu-utils qt6-base-dev sbuild uidmap ubuntu-keyring
    printf '\nsubordinate_ids:\n'
    grep -E "^${TARGET_USER}:" /etc/subuid /etc/subgid
    printf '\nautopkgtest_unshare_private_binary:\n'
    printf 'source=%s\n' "${UNSHARE_SOURCE}"
    printf 'private=%s\n' "${UNSHARE_PRIVATE}"
    sha256sum "${UNSHARE_SOURCE}" "${UNSHARE_PRIVATE}"
    dpkg-query -S "${UNSHARE_SOURCE}" || true
    printf '\nautopkgtest_unshare_apparmor:\n'
    sha256sum "${APPARMOR_PROFILE_TARGET}"
    aa-status | grep -F 'supralinux-autopkgtest-virt-unshare' || true
    printf 'apparmor_restrict_unprivileged_userns=%s\n' "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null || echo unavailable)"
    printf '\nautopkgtest_work_root:\n'
    stat -c 'mode=%a owner=%U group=%G path=%n' /var/lib/supralinux/autopkgtest/work
} | sudo tee /var/lib/supralinux/evidence/runner-guest-provisioning.txt >/dev/null

printf '\nGuest tooling and verified Actions runner installed.\n'
printf 'A new login/session is required for kvm group membership to apply.\n'
printf 'After that, verify /dev/kvm and run scripts/prepare-autopkgtest-qemu-image.sh.\n'
printf 'GitHub JIT configuration is intentionally generated on the libvirt host at VM runtime.\n'

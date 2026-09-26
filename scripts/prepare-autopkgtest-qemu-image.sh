#!/usr/bin/env bash
set -Eeuo pipefail

TARGET="${AUTOPKGTEST_QEMU_IMAGE:-/var/lib/supralinux/autopkgtest/resolute-amd64.img}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Expected Ubuntu 26.04; got %s %s\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi

if [[ "$(systemd-detect-virt --vm 2>/dev/null || true)" != "kvm" ]]; then
    printf 'The authoritative test image must be prepared inside the KVM runner guest.\n' >&2
    exit 1
fi

if [[ ! -c /dev/kvm || ! -r /dev/kvm || ! -w /dev/kvm ]]; then
    printf '/dev/kvm is not usable by the current user. Re-login after kvm group provisioning and verify nested KVM on the host.\n' >&2
    exit 1
fi

for command_name in autopkgtest-buildvm-ubuntu-cloud qemu-img sha256sum; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

printf 'Building fresh Ubuntu 26.04 autopkgtest QEMU image...\n'
autopkgtest-buildvm-ubuntu-cloud \
    --release=resolute \
    --arch=amd64 \
    --output-dir="${WORK_DIR}" \
    --ram-size=2048 \
    --cpus=2 \
    --verbose

mapfile -t IMAGES < <(find "${WORK_DIR}" -maxdepth 1 -type f -name 'autopkgtest-resolute-amd64*.img' -print | sort)
if (( ${#IMAGES[@]} != 1 )); then
    printf 'Expected exactly one resolute amd64 autopkgtest image, found %d.\n' "${#IMAGES[@]}" >&2
    find "${WORK_DIR}" -maxdepth 1 -type f -printf '%f\n' >&2
    exit 1
fi

sudo install -D -m 0644 "${IMAGES[0]}" "${TARGET}"

PROVENANCE="$(mktemp)"
{
    printf 'prepared_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'release=resolute\n'
    printf 'architecture=amd64\n'
    printf 'builder=' 
    autopkgtest-buildvm-ubuntu-cloud --help 2>&1 | head -1 || true
    printf '\nqemu_image_info:\n'
    qemu-img info "${TARGET}"
    printf '\nsha256:\n'
    sha256sum "${TARGET}"
} > "${PROVENANCE}"

sudo install -m 0644 "${PROVENANCE}" "${TARGET}.provenance.txt"
rm -f "${PROVENANCE}"
sha256sum "${TARGET}"
printf 'Prepared authoritative autopkgtest image: %s\n' "${TARGET}"

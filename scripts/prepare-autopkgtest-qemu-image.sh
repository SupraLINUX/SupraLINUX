#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${AUTOPKGTEST_QEMU_IMAGE:-/var/lib/supralinux/autopkgtest/resolute-amd64.img}"
WORK_ROOT="${AUTOPKGTEST_QEMU_WORK_ROOT:-/var/lib/supralinux/autopkgtest/work}"
DISK_SIZE="${AUTOPKGTEST_QEMU_DISK_SIZE:-20G}"
RAM_SIZE="${AUTOPKGTEST_QEMU_RAM_MIB:-2048}"
BUILD_SWAP_MIB="${AUTOPKGTEST_QEMU_BUILD_SWAP_MIB:-4096}"
BUILD_SWAP_FILE="${AUTOPKGTEST_QEMU_BUILD_SWAP_FILE:-/var/lib/supralinux/autopkgtest/.build.swap}"
EVIDENCE_DIR="${SUPRALINUX_EVIDENCE_DIR:-/var/lib/supralinux/evidence}"
RESOURCE_EVIDENCE="${EVIDENCE_DIR}/autopkgtest-build-resources.txt"
SWAP_ACTIVE=0

"${ROOT}/scripts/check-autopkgtest-workspace.sh" "${WORK_ROOT}"
WORK_DIR="$(mktemp -d "${WORK_ROOT%/}/build.XXXXXX")"

cleanup() {
    rc=$?
    trap - EXIT
    cleanup_failed=0

    if (( SWAP_ACTIVE )); then
        if sudo swapoff "${BUILD_SWAP_FILE}"; then
            SWAP_ACTIVE=0
        else
            cleanup_failed=1
        fi
    fi
    if ! sudo rm -f "${BUILD_SWAP_FILE}"; then
        cleanup_failed=1
    fi
    rm -rf "${WORK_DIR}"

    if [[ -d "${EVIDENCE_DIR}" ]]; then
        if (( cleanup_failed )); then
            printf 'temporary_build_swap_cleanup=FAIL\n' | sudo tee -a "${RESOURCE_EVIDENCE}" >/dev/null || true
        else
            printf 'temporary_build_swap_cleanup=PASS\n' | sudo tee -a "${RESOURCE_EVIDENCE}" >/dev/null || true
        fi
    fi

    if (( rc == 0 && cleanup_failed )); then
        rc=1
    fi
    exit "${rc}"
}
trap cleanup EXIT

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

for command_name in autopkgtest-buildvm-ubuntu-cloud fallocate genisoimage mkswap qemu-img sha256sum swapoff swapon; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

if [[ ! "${RAM_SIZE}" =~ ^[0-9]+$ ]] || (( RAM_SIZE < 2048 )); then
    printf 'AUTOPKGTEST_QEMU_RAM_MIB must be an integer >= 2048.\n' >&2
    exit 1
fi
if [[ ! "${BUILD_SWAP_MIB}" =~ ^[0-9]+$ ]] || (( BUILD_SWAP_MIB < 4096 )); then
    printf 'AUTOPKGTEST_QEMU_BUILD_SWAP_MIB must be an integer >= 4096.\n' >&2
    exit 1
fi
if [[ -e "${BUILD_SWAP_FILE}" ]]; then
    printf 'Refusing stale temporary build swap file: %s\n' "${BUILD_SWAP_FILE}" >&2
    exit 1
fi

SWAP_TOTAL_BEFORE_KIB="$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)"
MEM_TOTAL_KIB="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"

sudo fallocate -l "${BUILD_SWAP_MIB}M" "${BUILD_SWAP_FILE}"
sudo chmod 0600 "${BUILD_SWAP_FILE}"
sudo mkswap -q "${BUILD_SWAP_FILE}"
sudo swapon "${BUILD_SWAP_FILE}"
SWAP_ACTIVE=1

SWAP_TOTAL_ACTIVE_KIB="$(awk '/^SwapTotal:/ {print $2}' /proc/meminfo)"
EXPECTED_ADDED_SWAP_KIB=$(( BUILD_SWAP_MIB * 1024 ))
if (( SWAP_TOTAL_ACTIVE_KIB < SWAP_TOTAL_BEFORE_KIB + EXPECTED_ADDED_SWAP_KIB )); then
    printf 'Temporary build swap did not become fully active.\n' >&2
    exit 1
fi

sudo install -d -m 0755 "${EVIDENCE_DIR}"
{
    printf 'recorded_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'memory_total_kib=%s\n' "${MEM_TOTAL_KIB}"
    printf 'swap_total_before_kib=%s\n' "${SWAP_TOTAL_BEFORE_KIB}"
    printf 'swap_total_active_kib=%s\n' "${SWAP_TOTAL_ACTIVE_KIB}"
    printf 'temporary_build_swap_file=%s\n' "${BUILD_SWAP_FILE}"
    printf 'temporary_build_swap_mib=%s\n' "${BUILD_SWAP_MIB}"
    printf 'nested_qemu_ram_mib=%s\n' "${RAM_SIZE}"
    printf 'work_root=%s\n' "${WORK_ROOT}"
    printf 'temporary_build_swap_active=PASS\n'
} | sudo tee "${RESOURCE_EVIDENCE}" >/dev/null

printf 'Temporary outer-guest build swap active: %s MiB\n' "${BUILD_SWAP_MIB}"
printf 'Building fresh Ubuntu 26.04 autopkgtest QEMU image...\n'
autopkgtest-buildvm-ubuntu-cloud \
    --release=resolute \
    --arch=amd64 \
    --output-dir="${WORK_DIR}" \
    --disk-size="${DISK_SIZE}" \
    --ram-size="${RAM_SIZE}" \
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
    printf 'work_root=%s\n' "${WORK_ROOT}"
    printf 'disk_size=%s\n' "${DISK_SIZE}"
    printf 'nested_qemu_ram_mib=%s\n' "${RAM_SIZE}"
    printf 'temporary_build_swap_mib=%s\n' "${BUILD_SWAP_MIB}"
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

#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="${ROOT}/packages/supralinux-build-test"
WORK_DIR="${ROOT}/.work/authoritative-package-proof"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/authoritative-package-proof"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar.gz"
MIRROR="${SBUILD_MIRROR:-http://archive.ubuntu.com/ubuntu}"
AUTOPKGTEST_QEMU_IMAGE="${AUTOPKGTEST_QEMU_IMAGE:-/var/lib/supralinux/autopkgtest/resolute-amd64.img}"
STATE="FAIL"
STAGE="initialization"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${OUT_DIR}" "${EVIDENCE_DIR}" "$(dirname "${CHROOT_TARBALL}")"

write_result() {
    local rc="$?"
    local finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - "${RESULT_JSON}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json
import sys
from pathlib import Path

path, state, rc, stage, started, finished = sys.argv[1:]
Path(path).write_text(json.dumps({
    "node": "authoritative-package-proof",
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "authoritative": True,
    "runner_class": "supralinux-kvm-ubuntu-26.04-ephemeral",
    "outer_virtualization": "kvm",
    "sbuild_backend": "unshare",
    "system_test_backend": "autopkgtest-qemu",
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT

exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

printf '=== SupraLINUX authoritative package proof ===\n'

STAGE="runner-contract"
. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Expected Ubuntu 26.04 guest; got %s %s\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi

VIRT="$(systemd-detect-virt --vm 2>/dev/null || true)"
if [[ "${VIRT}" != "kvm" ]]; then
    printf 'Authoritative runner must itself be a KVM VM; detected: %s\n' "${VIRT:-none}" >&2
    exit 1
fi

if [[ ! -c /dev/kvm || ! -r /dev/kvm || ! -w /dev/kvm ]]; then
    printf '/dev/kvm must exist and be readable/writable by the runner user for nested KVM tests.\n' >&2
    exit 1
fi

required_commands=(
    autopkgtest
    dpkg-buildpackage
    git
    jq
    mmdebstrap
    qemu-img
    qemu-system-x86_64
    sbuild
    sha256sum
    systemd-detect-virt
    unshare
)
for command_name in "${required_commands[@]}"; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

qemu-system-x86_64 -accel help 2>&1 | grep -q 'kvm' || {
    printf 'QEMU does not expose the KVM accelerator.\n' >&2
    exit 1
}

if [[ ! -f "${AUTOPKGTEST_QEMU_IMAGE}" ]]; then
    printf 'Missing certified autopkgtest QEMU image: %s\n' "${AUTOPKGTEST_QEMU_IMAGE}" >&2
    exit 1
fi

{
    printf 'host_os:\n'
    cat /etc/os-release
    printf '\nuname:\n'
    uname -a
    printf '\nouter_virtualization:\n%s\n' "${VIRT}"
    printf '\nkvm_device:\n'
    ls -l /dev/kvm
    printf '\nkvm_modules:\n'
    lsmod | grep -E '^kvm(_intel|_amd)?\b' || true
    printf '\nnested_kvm:\n'
    for nested in /sys/module/kvm_intel/parameters/nested /sys/module/kvm_amd/parameters/nested; do
        if [[ -r "${nested}" ]]; then
            printf '%s=' "${nested}"
            cat "${nested}"
        fi
    done
    printf '\ntool_versions:\n'
    dpkg-query -W -f='${Package}\t${Version}\n' autopkgtest dpkg-dev mmdebstrap qemu-system-x86 qemu-utils sbuild uidmap ubuntu-keyring 2>/dev/null || true
    printf '\nautopkgtest_qemu_image:\n%s\n' "${AUTOPKGTEST_QEMU_IMAGE}"
    qemu-img info "${AUTOPKGTEST_QEMU_IMAGE}"
    printf '\nmirror:\n%s\n' "${MIRROR}"
} > "${EVIDENCE_DIR}/environment.txt"
sha256sum "${AUTOPKGTEST_QEMU_IMAGE}" > "${EVIDENCE_DIR}/autopkgtest-image-sha256.txt"

if ! grep -q "^${USER}:" /etc/subuid; then
    printf 'Runner user lacks a subordinate UID range required by sbuild/unshare.\n' >&2
    exit 1
fi
if ! grep -q "^${USER}:" /etc/subgid; then
    printf 'Runner user lacks a subordinate GID range required by sbuild/unshare.\n' >&2
    exit 1
fi
unshare --user --map-auto true

STAGE="source-package"
printf 'Creating source package...\n'
pushd "${PACKAGE_DIR}" >/dev/null
dpkg-buildpackage -S -us -uc -d
popd >/dev/null

DSC="${ROOT}/packages/supralinux-build-test_0.1.0.dsc"
SOURCE_TARBALL="${ROOT}/packages/supralinux-build-test_0.1.0.tar.xz"
test -f "${DSC}"
test -f "${SOURCE_TARBALL}"
sha256sum "${DSC}" "${SOURCE_TARBALL}" > "${EVIDENCE_DIR}/source-sha256.txt"

STAGE="sbuild-rootfs"
printf 'Creating fresh resolute buildd rootfs for sbuild/unshare...\n'
rm -f "${CHROOT_TARBALL}"
mmdebstrap \
    --mode=unshare \
    --variant=buildd \
    --architectures=amd64 \
    --components=main,universe \
    --include=ca-certificates,ubuntu-keyring \
    resolute \
    "${CHROOT_TARBALL}" \
    "${MIRROR}" |& tee "${EVIDENCE_DIR}/rootfs.log"
test -s "${CHROOT_TARBALL}"
sha256sum "${CHROOT_TARBALL}" > "${EVIDENCE_DIR}/rootfs-sha256.txt"

STAGE="sbuild"
printf 'Building package with sbuild/unshare...\n'
sbuild \
    --verbose \
    --chroot-mode=unshare \
    --dist=resolute \
    --arch=amd64 \
    --arch-all \
    --build-dir="${OUT_DIR}" \
    "${DSC}" |& tee "${EVIDENCE_DIR}/sbuild.log"

mapfile -t DEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t CHANGES < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)

if (( ${#DEBS[@]} == 0 || ${#CHANGES[@]} == 0 || ${#BUILDINFO[@]} == 0 )); then
    printf 'Missing required build artifact(s): deb=%d changes=%d buildinfo=%d\n' \
        "${#DEBS[@]}" "${#CHANGES[@]}" "${#BUILDINFO[@]}" >&2
    exit 1
fi

STAGE="artifact-capture"
printf 'Capturing build artifacts before system testing...\n'
sha256sum "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${EVIDENCE_DIR}/"

STAGE="autopkgtest-qemu"
printf 'Running autopkgtest in a nested QEMU/KVM Ubuntu 26.04 testbed...\n'
autopkgtest "${DSC}" "${DEBS[0]}" -- \
    qemu \
    --cpus=2 \
    --ram-size=2048 \
    "${AUTOPKGTEST_QEMU_IMAGE}" |& tee "${EVIDENCE_DIR}/autopkgtest.log"

STATE="PASS"
STAGE="complete"
printf 'Authoritative package proof: PASS\n'

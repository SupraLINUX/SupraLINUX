#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="${ROOT}/packages/supralinux-build-test"
WORK_DIR="${ROOT}/.work/package-build-proof"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/package-build-proof"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar.gz"
MIRROR="${SBUILD_MIRROR:-http://azure.archive.ubuntu.com/ubuntu}"
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
    "node": "hosted-package-build-preflight",
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "authoritative": False,
    "runner_class": "github-hosted-ubuntu-26.04",
    "scope": "source-and-clean-sbuild-only",
    "sbuild_backend": "unshare",
    "system_test_backend": None,
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT

exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

printf '=== SupraLINUX hosted package-build preflight ===\n'

STAGE="host-validation"
. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Expected Ubuntu 26.04; got %s %s\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi

printf 'Installing build tooling...\n'
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    debhelper \
    devscripts \
    dpkg-dev \
    mmdebstrap \
    sbuild \
    uidmap \
    ubuntu-keyring

if ! grep -q "^${USER}:" /etc/subuid; then
    sudo usermod --add-subuids 100000-165535 "${USER}"
fi
if ! grep -q "^${USER}:" /etc/subgid; then
    sudo usermod --add-subgids 100000-165535 "${USER}"
fi

printf 'Verifying unprivileged user namespace support...\n'
unshare --user --map-auto true

{
    printf 'host_os:\n'
    cat /etc/os-release
    printf '\nuname:\n'
    uname -a
    printf '\ntool_versions:\n'
    dpkg-query -W -f='${Package}\t${Version}\n' debhelper devscripts dpkg-dev mmdebstrap sbuild uidmap ubuntu-keyring
    printf '\nsubuid:\n'
    grep "^${USER}:" /etc/subuid || true
    printf '\nsubgid:\n'
    grep "^${USER}:" /etc/subgid || true
    printf '\nunprivileged_userns_clone:\n'
    sysctl -n kernel.unprivileged_userns_clone 2>/dev/null || printf 'not-exposed\n'
    printf '\nmirror:\n%s\n' "${MIRROR}"
} > "${EVIDENCE_DIR}/environment.txt"

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
printf 'Capturing build artifacts before any later test stage...\n'
sha256sum "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${EVIDENCE_DIR}/"

STATE="PASS"
STAGE="complete"
printf 'Hosted package-build preflight: PASS\n'
printf 'System-level package testing is intentionally not claimed by this lane.\n'

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
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${OUT_DIR}" "${EVIDENCE_DIR}" "$(dirname "${CHROOT_TARBALL}")"

write_result() {
    local rc="$?"
    local finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - "${RESULT_JSON}" "${STATE}" "${rc}" "${STARTED_AT}" "${finished_at}" <<'PY'
import json
import sys
from pathlib import Path

path, state, rc, started, finished = sys.argv[1:]
Path(path).write_text(json.dumps({
    "node": "supralinux-build-test",
    "state": state,
    "exit_code": int(rc),
    "started_at": started,
    "finished_at": finished,
    "authoritative": False,
    "runner_class": "github-hosted-ubuntu-26.04",
    "sbuild_backend": "unshare",
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT

exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

printf '=== SupraLINUX Phase 1 package-build proof ===\n'

. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Expected Ubuntu 26.04; got %s %s\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi

printf 'Installing build/test tooling...\n'
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    autopkgtest \
    debhelper \
    devscripts \
    dpkg-dev \
    mmdebstrap \
    sbuild \
    uidmap \
    ubuntu-keyring

# The unshare backend needs subordinate UID/GID ranges. GitHub-hosted images
# normally provide them; add a private range only if this disposable runner lacks one.
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
    dpkg-query -W -f='${Package}\t${Version}\n' autopkgtest debhelper devscripts dpkg-dev mmdebstrap sbuild uidmap ubuntu-keyring
    printf '\nsubuid:\n'
    grep "^${USER}:" /etc/subuid || true
    printf '\nsubgid:\n'
    grep "^${USER}:" /etc/subgid || true
    printf '\nunprivileged_userns_clone:\n'
    sysctl -n kernel.unprivileged_userns_clone 2>/dev/null || printf 'not-exposed\n'
    printf '\nmirror:\n%s\n' "${MIRROR}"
} > "${EVIDENCE_DIR}/environment.txt"

printf 'Creating source package...\n'
pushd "${PACKAGE_DIR}" >/dev/null
dpkg-buildpackage -S -us -uc -d
popd >/dev/null

DSC="${ROOT}/packages/supralinux-build-test_0.1.0.dsc"
SOURCE_TARBALL="${ROOT}/packages/supralinux-build-test_0.1.0.tar.xz"
test -f "${DSC}"
test -f "${SOURCE_TARBALL}"
sha256sum "${DSC}" "${SOURCE_TARBALL}" > "${EVIDENCE_DIR}/source-sha256.txt"

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

printf 'Building package with sbuild/unshare...\n'
sbuild \
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

printf 'Running autopkgtest in an isolated unshare testbed...\n'
autopkgtest "${DSC}" "${DEBS[0]}" -- \
    unshare \
    --release resolute \
    --arch amd64 \
    --tarball "${CHROOT_TARBALL}" |& tee "${EVIDENCE_DIR}/autopkgtest.log"

printf 'Capturing build artifact hashes...\n'
sha256sum "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${EVIDENCE_DIR}/"

STATE="PASS"
printf 'Phase 1 package-build proof: PASS\n'

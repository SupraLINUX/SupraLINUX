#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_DIR="${ROOT}/packages/supralinux-build-test"
WORK_DIR="${ROOT}/.work/package-build-proof"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/package-build-proof"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
STATE="FAIL"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

mkdir -p "${OUT_DIR}" "${EVIDENCE_DIR}"

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
    debootstrap \
    devscripts \
    dpkg-dev \
    schroot \
    sbuild \
    ubuntu-keyring

{
    printf 'host_os:\n'
    cat /etc/os-release
    printf '\nuname:\n'
    uname -a
    printf '\ntool_versions:\n'
    dpkg-query -W -f='${Package}\t${Version}\n' autopkgtest debhelper debootstrap devscripts dpkg-dev schroot sbuild ubuntu-keyring
} > "${EVIDENCE_DIR}/environment.txt"

printf 'Creating source package...\n'
rm -rf "${WORK_DIR}/source-output"
mkdir -p "${WORK_DIR}/source-output"
pushd "${PACKAGE_DIR}" >/dev/null
dpkg-buildpackage -S -us -uc -d
popd >/dev/null

DSC="${ROOT}/packages/supralinux-build-test_0.1.0.dsc"
TARBALL="${ROOT}/packages/supralinux-build-test_0.1.0.tar.xz"
test -f "${DSC}"
test -f "${TARBALL}"
sha256sum "${DSC}" "${TARBALL}" > "${EVIDENCE_DIR}/source-sha256.txt"

printf 'Creating fresh resolute sbuild chroot...\n'
sudo rm -rf /srv/chroot/resolute-amd64-sbuild
sudo sbuild-createchroot \
    --arch=amd64 \
    --components=main,universe \
    resolute \
    /srv/chroot/resolute-amd64-sbuild \
    http://archive.ubuntu.com/ubuntu

sudo usermod -aG sbuild "${USER}"
schroot -l | tee "${EVIDENCE_DIR}/schroot-list.txt"

printf 'Building package with sbuild...\n'
pushd "${OUT_DIR}" >/dev/null
sg sbuild -c "sbuild --dist=resolute --arch=amd64 '${DSC}'" |& tee "${EVIDENCE_DIR}/sbuild.log"
popd >/dev/null

mapfile -t DEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t CHANGES < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)

if (( ${#DEBS[@]} == 0 || ${#CHANGES[@]} == 0 || ${#BUILDINFO[@]} == 0 )); then
    printf 'Missing required build artifact(s): deb=%d changes=%d buildinfo=%d\n' \
        "${#DEBS[@]}" "${#CHANGES[@]}" "${#BUILDINFO[@]}" >&2
    exit 1
fi

printf 'Running autopkgtest smoke test against built binary...\n'
autopkgtest "${DSC}" "${DEBS[0]}" -- null |& tee "${EVIDENCE_DIR}/autopkgtest.log"

printf 'Capturing build artifact hashes...\n'
sha256sum "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${EVIDENCE_DIR}/"

STATE="PASS"
printf 'Phase 1 package-build proof: PASS\n'

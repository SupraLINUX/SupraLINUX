#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_META="${ROOT}/packages/kde/extra-cmake-modules/debian"
WORK_DIR="${ROOT}/.work/kde-ecm-package-preflight"
SOURCE_WORK="${WORK_DIR}/source"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/kde-ecm-package-preflight"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar"
MIRROR="${SBUILD_MIRROR:-http://azure.archive.ubuntu.com/ubuntu}"

UPSTREAM_VERSION="6.30.0"
DEBIAN_VERSION="${UPSTREAM_VERSION}-0supralinux3"
SOURCE_PACKAGE="kf6-extra-cmake-modules"
BINARY_PACKAGE="extra-cmake-modules"
UPSTREAM_TARBALL="extra-cmake-modules-${UPSTREAM_VERSION}.tar.xz"
UPSTREAM_URL="https://download.kde.org/stable/frameworks/6.30/${UPSTREAM_TARBALL}"
UPSTREAM_SHA256="22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e"
KDE_INFO_URL="https://kde.org/info/kde-frameworks-6.30.0/"

STATE="FAIL"
STAGE="initialization"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${SOURCE_WORK}" "${OUT_DIR}" "${EVIDENCE_DIR}" "$(dirname "${CHROOT_TARBALL}")"

write_result() {
    local rc="$?"
    local finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - "${RESULT_JSON}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" "${UPSTREAM_VERSION}" "${DEBIAN_VERSION}" <<'PY'
import json
import sys
from pathlib import Path

path, state, rc, stage, started, finished, version, debian_version = sys.argv[1:]
Path(path).write_text(json.dumps({
    "node": "kde-frameworks-extra-cmake-modules",
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "authoritative": False,
    "runner_class": "github-hosted-ubuntu-26.04",
    "upstream_authority": "kde-upstream",
    "upstream_version": version,
    "debian_version": debian_version,
    "artifact_role": "dag-root-provider",
    "claim": "hosted-clean-package-preflight-only",
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT

exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

printf '=== SupraLINUX KDE DAG: Extra CMake Modules %s (%s) ===\n' "${UPSTREAM_VERSION}" "${DEBIAN_VERSION}"

STAGE="host-validation"
. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Expected Ubuntu 26.04; got %s %s\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    cmake \
    curl \
    debhelper \
    devscripts \
    dpkg-dev \
    lintian \
    mmdebstrap \
    ninja-build \
    python3 \
    qt6-base-dev \
    sbuild \
    uidmap \
    ubuntu-keyring \
    xz-utils

if ! grep -q "^${USER}:" /etc/subuid; then
    sudo usermod --add-subuids 100000-165535 "${USER}"
fi
if ! grep -q "^${USER}:" /etc/subgid; then
    sudo usermod --add-subgids 100000-165535 "${USER}"
fi
unshare --user --map-auto true

if ! command -v qtpaths6 >/dev/null 2>&1 && [[ -x /usr/lib/qt6/bin/qtpaths6 ]]; then
    export PATH="/usr/lib/qt6/bin:${PATH}"
fi
if ! command -v qtpaths6 >/dev/null 2>&1; then
    printf 'qtpaths6 is required for the Qt-integrated ECM consumer smoke.\n' >&2
    exit 1
fi
qtpaths6 --qt-version > "${EVIDENCE_DIR}/qt6-consumer-version.txt"

{
    printf 'host_os:\n'
    cat /etc/os-release
    printf '\nuname:\n'
    uname -a
    printf '\ntool_versions:\n'
    dpkg-query -W -f='${Package}\t${Version}\n' \
        ca-certificates cmake curl debhelper devscripts dpkg-dev lintian mmdebstrap ninja-build python3 qt6-base-dev qt6-base-dev-tools sbuild uidmap ubuntu-keyring xz-utils
    printf '\nupstream_authority=kde-upstream\n'
    printf 'upstream_version=%s\n' "${UPSTREAM_VERSION}"
    printf 'debian_version=%s\n' "${DEBIAN_VERSION}"
    printf 'upstream_url=%s\n' "${UPSTREAM_URL}"
    printf 'upstream_sha256=%s\n' "${UPSTREAM_SHA256}"
    printf 'kde_info_url=%s\n' "${KDE_INFO_URL}"
    printf 'ubuntu_reference_version=6.24.0-0ubuntu1\n'
    printf 'package_provider=supralinux\n'
    printf 'upstream_tests=disabled-in-package-preflight\n'
    printf 'postbuild_lintian=required-fail-on-error\n'
    printf 'postbuild_consumer_smoke=required\n'
    printf 'consumer_qt_provider=ubuntu-qt6-base-dev\n'
    printf 'consumer_qtpaths=%s\n' "$(command -v qtpaths6)"
} > "${EVIDENCE_DIR}/environment.txt"

STAGE="upstream-source"
ORIG_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 \
    --output "${ORIG_TARBALL}" "${UPSTREAM_URL}"
printf '%s  %s\n' "${UPSTREAM_SHA256}" "${ORIG_TARBALL}" | sha256sum --check --strict
sha256sum "${ORIG_TARBALL}" > "${EVIDENCE_DIR}/upstream-source-sha256.txt"

tar -xJf "${ORIG_TARBALL}" -C "${SOURCE_WORK}"
EXTRACTED="${SOURCE_WORK}/extra-cmake-modules-${UPSTREAM_VERSION}"
SOURCE_DIR="${SOURCE_WORK}/${SOURCE_PACKAGE}-${UPSTREAM_VERSION}"
test -d "${EXTRACTED}"
mv "${EXTRACTED}" "${SOURCE_DIR}"
cp -a "${PACKAGE_META}" "${SOURCE_DIR}/debian"
chmod +x "${SOURCE_DIR}/debian/rules"

STAGE="source-package"
pushd "${SOURCE_DIR}" >/dev/null
dpkg-buildpackage -S -us -uc -d
popd >/dev/null

DSC="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.dsc"
DEBIAN_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${DEBIAN_VERSION}.debian.tar.xz"
test -s "${DSC}"
test -s "${DEBIAN_TARBALL}"
sha256sum "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" > "${EVIDENCE_DIR}/source-package-sha256.txt"

STAGE="sbuild-rootfs"
rm -f "${CHROOT_TARBALL}"
mmdebstrap \
    --mode=unshare \
    --variant=buildd \
    --architectures=amd64 \
    --components=main,universe \
    --skip=output/mknod \
    --format=tar \
    resolute \
    "${CHROOT_TARBALL}" \
    "${MIRROR}" |& tee "${EVIDENCE_DIR}/rootfs.log"

test -s "${CHROOT_TARBALL}"
sha256sum "${CHROOT_TARBALL}" > "${EVIDENCE_DIR}/rootfs-sha256.txt"

STAGE="sbuild"
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

ECM_DEB=""
for deb in "${DEBS[@]}"; do
    if [[ "$(dpkg-deb -f "${deb}" Package)" == "${BINARY_PACKAGE}" ]]; then
        ECM_DEB="${deb}"
        break
    fi
done
if [[ -z "${ECM_DEB}" ]]; then
    printf 'Built artifacts do not contain binary package %s.\n' "${BINARY_PACKAGE}" >&2
    exit 1
fi

BUILT_VERSION="$(dpkg-deb -f "${ECM_DEB}" Version)"
BUILT_ARCH="$(dpkg-deb -f "${ECM_DEB}" Architecture)"
if [[ "${BUILT_VERSION}" != "${DEBIAN_VERSION}" || "${BUILT_ARCH}" != "all" ]]; then
    printf 'Unexpected binary metadata: version=%s architecture=%s\n' "${BUILT_VERSION}" "${BUILT_ARCH}" >&2
    exit 1
fi

STAGE="artifact-capture"
sha256sum "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${EVIDENCE_DIR}/"
dpkg-deb -I "${ECM_DEB}" > "${EVIDENCE_DIR}/extra-cmake-modules-control.txt"
dpkg-deb -c "${ECM_DEB}" > "${EVIDENCE_DIR}/extra-cmake-modules-filelist.txt"

STAGE="lintian"
lintian --fail-on error "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian.log"

STAGE="consumer-smoke"
CONSUMER_ROOT="${WORK_DIR}/consumer-root"
CONSUMER_SRC="${WORK_DIR}/consumer-src"
CONSUMER_BUILD="${WORK_DIR}/consumer-build"
mkdir -p "${CONSUMER_ROOT}" "${CONSUMER_SRC}"
dpkg-deb -x "${ECM_DEB}" "${CONSUMER_ROOT}"

ECM_CONFIG="$(find "${CONSUMER_ROOT}" -type f -path '*/ECM/cmake/ECMConfig.cmake' -print -quit)"
if [[ -z "${ECM_CONFIG}" ]]; then
    printf 'ECMConfig.cmake not found in built package.\n' >&2
    exit 1
fi
ECM_DIR="$(dirname "${ECM_CONFIG}")"

cat > "${CONSUMER_SRC}/CMakeLists.txt" <<'EOF_CMAKE'
cmake_minimum_required(VERSION 3.29)
project(SupraLINUXECMConsumer NONE)

find_package(ECM 6.30.0 REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})

include(KDEInstallDirs6)
include(KDECMakeSettings)
include(ECMSetupVersion)
include(ECMGenerateHeaders)

if(NOT ECM_VERSION VERSION_EQUAL "6.30.0")
    message(FATAL_ERROR "Expected ECM 6.30.0, found ${ECM_VERSION}")
endif()

message(STATUS "SUPRALINUX_ECM_VERSION=${ECM_VERSION}")
message(STATUS "SUPRALINUX_ECM_MODULE_PATH=${ECM_MODULE_PATH}")
EOF_CMAKE

cmake -S "${CONSUMER_SRC}" -B "${CONSUMER_BUILD}" \
    -DECM_DIR="${ECM_DIR}" |& tee "${EVIDENCE_DIR}/consumer-cmake.log"
grep -F 'SUPRALINUX_ECM_VERSION=6.30.0' "${EVIDENCE_DIR}/consumer-cmake.log"

STAGE="dag-pass-evidence"
{
    printf 'node=extra-cmake-modules\n'
    printf 'state=PASS\n'
    printf 'upstream_version=%s\n' "${UPSTREAM_VERSION}"
    printf 'debian_version=%s\n' "${DEBIAN_VERSION}"
    printf 'binary_package=%s\n' "${BINARY_PACKAGE}"
    printf 'architecture=%s\n' "${BUILT_ARCH}"
    printf 'upstream_tests=not-run-in-package-preflight\n'
    printf 'lintian=PASS\n'
    printf 'consumer_qt=PASS\n'
    printf 'consumer_smoke=PASS\n'
    printf 'downstream_eligible=yes\n'
} > "${EVIDENCE_DIR}/dag-node.txt"

STATE="PASS"
STAGE="complete"
printf 'KDE DAG node extra-cmake-modules: PASS\n'
printf 'Built %s %s and verified it as a downstream-eligible ECM 6.30.0 artifact.\n' \
    "${BINARY_PACKAGE}" "${BUILT_VERSION}"

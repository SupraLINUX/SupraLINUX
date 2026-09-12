#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_META="${ROOT}/packages/kde/attica/debian"
WORK_DIR="${ROOT}/.work/kde-attica-package-preflight"
SOURCE_WORK="${WORK_DIR}/source"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/kde-attica-package-preflight"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar"
MIRROR="${SBUILD_MIRROR:-http://azure.archive.ubuntu.com/ubuntu}"

UPSTREAM_VERSION="6.30.0"
DEBIAN_VERSION="${UPSTREAM_VERSION}-0supralinux2"
SOURCE_PACKAGE="kf6-attica"
UPSTREAM_TARBALL="attica-${UPSTREAM_VERSION}.tar.xz"
UPSTREAM_URL="https://download.kde.org/stable/frameworks/6.30/${UPSTREAM_TARBALL}"
UPSTREAM_SHA256="3eec8d2d9c77ad5f7cfd38e44e4b1492c5d0dec695b13f711c09f7d6187c276c"
ECM_VERSION="6.30.0-0supralinux3"
ECM_DEB_SHA256="ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f"
SYMBOLS_REFERENCE_SHA256="e67d131171c8e3ea79c6bbbb2434aa2492580d19ba7dccdaa7038766cd9827ad"

: "${ECM_ARTIFACT_DIR:?ECM_ARTIFACT_DIR must point at the retained ECM PASS artifact}"
: "${ATTICA_REFERENCE_DIR:?ATTICA_REFERENCE_DIR must point at the retained Attica packaging-reference artifact}"

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
    "node": "attica",
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
    "ecm_predecessor": "6.30.0-0supralinux3",
    "claim": "hosted-clean-package-preflight",
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT

exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

echo "=== SupraLINUX KDE Tier 1: Attica ${UPSTREAM_VERSION} (${DEBIAN_VERSION}) ==="

STAGE="retained-input-validation"
ECM_DEB="$(find "${ECM_ARTIFACT_DIR}" -maxdepth 2 -type f -name "extra-cmake-modules_${ECM_VERSION}_all.deb" -print -quit)"
if [[ -z "${ECM_DEB}" || ! -s "${ECM_DEB}" ]]; then
    echo "Retained ECM PASS .deb not found under ${ECM_ARTIFACT_DIR}" >&2
    exit 1
fi
printf '%s  %s\n' "${ECM_DEB_SHA256}" "${ECM_DEB}" | sha256sum --check --strict
sha256sum "${ECM_DEB}" > "${EVIDENCE_DIR}/ecm-predecessor-sha256.txt"

dpkg-deb -f "${ECM_DEB}" Package Version Architecture > "${EVIDENCE_DIR}/ecm-predecessor-control.txt"
if [[ "$(dpkg-deb -f "${ECM_DEB}" Package)" != "extra-cmake-modules" ]] || \
   [[ "$(dpkg-deb -f "${ECM_DEB}" Version)" != "${ECM_VERSION}" ]]; then
    echo "Retained ECM artifact metadata mismatch" >&2
    exit 1
fi

SYMBOLS_REFERENCE="${ATTICA_REFERENCE_DIR}/ubuntu-resolute/debian/libkf6attica6.symbols"
if [[ ! -s "${SYMBOLS_REFERENCE}" ]]; then
    echo "Retained Ubuntu Attica symbols reference not found: ${SYMBOLS_REFERENCE}" >&2
    exit 1
fi
printf '%s  %s\n' "${SYMBOLS_REFERENCE_SHA256}" "${SYMBOLS_REFERENCE}" | sha256sum --check --strict
sha256sum "${SYMBOLS_REFERENCE}" > "${EVIDENCE_DIR}/symbols-reference-sha256.txt"

STAGE="host-validation"
. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    echo "Expected Ubuntu 26.04; got ${PRETTY_NAME}" >&2
    exit 1
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    binutils \
    ca-certificates \
    cmake \
    curl \
    debhelper \
    devscripts \
    dpkg-dev \
    g++ \
    lintian \
    mmdebstrap \
    ninja-build \
    pkg-config \
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

{
    cat /etc/os-release
    echo
    uname -a
    echo
    sbuild --version
    mmdebstrap --version
    cmake --version | head -1
    dpkg-query -W -f='${Package}\t${Version}\n' qt6-base-dev sbuild mmdebstrap lintian
} > "${EVIDENCE_DIR}/host.txt"

STAGE="upstream-source"
ORIG_TARBALL="${SOURCE_WORK}/${SOURCE_PACKAGE}_${UPSTREAM_VERSION}.orig.tar.xz"
curl --fail --location --retry 3 --retry-delay 2 --output "${ORIG_TARBALL}" "${UPSTREAM_URL}"
printf '%s  %s\n' "${UPSTREAM_SHA256}" "${ORIG_TARBALL}" | sha256sum --check --strict
sha256sum "${ORIG_TARBALL}" > "${EVIDENCE_DIR}/upstream-source-sha256.txt"

tar -xJf "${ORIG_TARBALL}" -C "${SOURCE_WORK}"
EXTRACTED="${SOURCE_WORK}/attica-${UPSTREAM_VERSION}"
SOURCE_DIR="${SOURCE_WORK}/${SOURCE_PACKAGE}-${UPSTREAM_VERSION}"
test -d "${EXTRACTED}"
mv "${EXTRACTED}" "${SOURCE_DIR}"
cp -a "${PACKAGE_META}" "${SOURCE_DIR}/debian"
cp -a "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/libkf6attica6.symbols"
chmod +x "${SOURCE_DIR}/debian/rules"

sha256sum "${SOURCE_DIR}/debian/libkf6attica6.symbols" > "${EVIDENCE_DIR}/injected-symbols-sha256.txt"
if ! cmp -s "${SYMBOLS_REFERENCE}" "${SOURCE_DIR}/debian/libkf6attica6.symbols"; then
    echo "Injected Attica symbols baseline differs from retained reference" >&2
    exit 1
fi

STAGE="source-package"
pushd "${SOURCE_WORK}" >/dev/null
dpkg-source -b "$(basename "${SOURCE_DIR}")"
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
    --extra-package="${ECM_DEB}" \
    --build-dir="${OUT_DIR}" \
    "${DSC}" |& tee "${EVIDENCE_DIR}/sbuild.log"

mapfile -t DEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t CHANGES < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)

if (( ${#DEBS[@]} != 3 || ${#CHANGES[@]} == 0 || ${#BUILDINFO[@]} == 0 )); then
    printf 'Unexpected build artifact count: deb=%d changes=%d buildinfo=%d\n' \
        "${#DEBS[@]}" "${#CHANGES[@]}" "${#BUILDINFO[@]}" >&2
    exit 1
fi

if ! grep -Fq "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}"; then
    echo "Buildinfo does not prove consumption of retained ECM ${ECM_VERSION}" >&2
    exit 1
fi
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE_DIR}/ecm-buildinfo-proof.txt"

STAGE="artifact-contract"
declare -A DEB_BY_PACKAGE=()
for deb in "${DEBS[@]}"; do
    package="$(dpkg-deb -f "${deb}" Package)"
    DEB_BY_PACKAGE["${package}"]="${deb}"
    if [[ "$(dpkg-deb -f "${deb}" Version)" != "${DEBIAN_VERSION}" ]]; then
        echo "Unexpected ${package} version: $(dpkg-deb -f "${deb}" Version)" >&2
        exit 1
    fi
done

for package in libkf6attica6 libkf6attica-dev libkf6attica-doc; do
    if [[ -z "${DEB_BY_PACKAGE[$package]:-}" ]]; then
        echo "Expected binary package missing: ${package}" >&2
        exit 1
    fi
done

RUNTIME_DEB="${DEB_BY_PACKAGE[libkf6attica6]}"
DEV_DEB="${DEB_BY_PACKAGE[libkf6attica-dev]}"
DOC_DEB="${DEB_BY_PACKAGE[libkf6attica-doc]}"

[[ "$(dpkg-deb -f "${RUNTIME_DEB}" Architecture)" == "amd64" ]]
[[ "$(dpkg-deb -f "${RUNTIME_DEB}" Multi-Arch)" == "same" ]]
[[ "$(dpkg-deb -f "${DEV_DEB}" Architecture)" == "amd64" ]]
[[ "$(dpkg-deb -f "${DOC_DEB}" Architecture)" == "all" ]]
[[ "$(dpkg-deb -f "${DOC_DEB}" Multi-Arch)" == "foreign" ]]

dev_depends="$(dpkg-deb -f "${DEV_DEB}" Depends)"
dev_recommends="$(dpkg-deb -f "${DEV_DEB}" Recommends)"
[[ "${dev_depends}" == *"libkf6attica6 (= ${DEBIAN_VERSION})"* ]]
[[ "${dev_depends}" == *"qt6-base-dev (>= 6.9.0~)"* ]]
[[ "${dev_recommends}" == *"libkf6attica-doc (= ${DEBIAN_VERSION})"* ]]

for deb in "${RUNTIME_DEB}" "${DEV_DEB}" "${DOC_DEB}"; do
    for field in Provides Breaks Replaces Conflicts; do
        value="$(dpkg-deb -f "${deb}" "${field}" 2>/dev/null || true)"
        if [[ -n "${value}" ]]; then
            echo "Unexpected compatibility field ${field} on $(dpkg-deb -f "${deb}" Package): ${value}" >&2
            exit 1
        fi
    done
done

{
    for deb in "${DEBS[@]}"; do
        echo "### $(basename "${deb}")"
        dpkg-deb -I "${deb}"
        echo
    done
} > "${EVIDENCE_DIR}/binary-control.txt"

{
    for deb in "${DEBS[@]}"; do
        echo "### $(basename "${deb}")"
        dpkg-deb -c "${deb}"
        echo
    done
} > "${EVIDENCE_DIR}/binary-filelists.txt"

STAGE="abi-check"
RUNTIME_ROOT="${WORK_DIR}/runtime-root"
mkdir -p "${RUNTIME_ROOT}"
dpkg-deb -x "${RUNTIME_DEB}" "${RUNTIME_ROOT}"
LIB_PATH="$(find "${RUNTIME_ROOT}" -type f -name 'libKF6Attica.so.6.*' -print -quit)"
test -n "${LIB_PATH}"
readelf -d "${LIB_PATH}" > "${EVIDENCE_DIR}/readelf-dynamic.txt"
grep -Fq 'Library soname: [libKF6Attica.so.6]' "${EVIDENCE_DIR}/readelf-dynamic.txt"

find "${RUNTIME_ROOT}" -type f -path '*/qlogging-categories6/attica.categories' -print -quit | grep -q .
find "${RUNTIME_ROOT}" -type f -path '*/qlogging-categories6/attica.renamecategories' -print -quit | grep -q .

STAGE="artifact-capture"
sha256sum "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${EVIDENCE_DIR}/"
cp -a "${DSC}" "${ORIG_TARBALL}" "${DEBIAN_TARBALL}" "${EVIDENCE_DIR}/"

STAGE="lintian"
lintian --fail-on error "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian.log"

STAGE="consumer-smoke"
CONSUMER_ROOT="${WORK_DIR}/consumer-root"
CONSUMER_SRC="${WORK_DIR}/consumer-src"
CONSUMER_BUILD="${WORK_DIR}/consumer-build"
mkdir -p "${CONSUMER_ROOT}" "${CONSUMER_SRC}"
dpkg-deb -x "${RUNTIME_DEB}" "${CONSUMER_ROOT}"
dpkg-deb -x "${DEV_DEB}" "${CONSUMER_ROOT}"

cat > "${CONSUMER_SRC}/CMakeLists.txt" <<'EOF_CMAKE'
cmake_minimum_required(VERSION 3.29)
project(SupraLINUXAtticaConsumer LANGUAGES CXX)
find_package(KF6Attica 6.30.0 REQUIRED CONFIG)
add_executable(attica-consumer main.cpp)
target_link_libraries(attica-consumer PRIVATE KF6::Attica)
EOF_CMAKE

cat > "${CONSUMER_SRC}/main.cpp" <<'EOF_CPP'
#include <Attica/ProviderManager>
int main()
{
    Attica::ProviderManager manager;
    return manager.providers().isEmpty() ? 0 : 0;
}
EOF_CPP

cmake -S "${CONSUMER_SRC}" -B "${CONSUMER_BUILD}" -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="${CONSUMER_ROOT}/usr" |& tee "${EVIDENCE_DIR}/consumer-configure.log"
cmake --build "${CONSUMER_BUILD}" --verbose |& tee "${EVIDENCE_DIR}/consumer-build.log"
MULTIARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
LD_LIBRARY_PATH="${CONSUMER_ROOT}/usr/lib/${MULTIARCH}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" \
    "${CONSUMER_BUILD}/attica-consumer" |& tee "${EVIDENCE_DIR}/consumer-run.log"

STAGE="dag-pass-evidence"
{
    echo "node=attica"
    echo "state=PASS"
    echo "upstream_version=${UPSTREAM_VERSION}"
    echo "debian_version=${DEBIAN_VERSION}"
    echo "ecm_predecessor=${ECM_VERSION}"
    echo "ecm_predecessor_sha256=${ECM_DEB_SHA256}"
    echo "source_sha256=${UPSTREAM_SHA256}"
    echo "symbols_baseline_sha256=${SYMBOLS_REFERENCE_SHA256}"
    echo "tests=PASS-via-sbuild"
    echo "lintian=PASS-errors"
    echo "abi_soname=libKF6Attica.so.6"
    echo "consumer_smoke=PASS"
    echo "downstream_eligible=yes"
} > "${EVIDENCE_DIR}/dag-node.txt"

STATE="PASS"
STAGE="complete"
echo "KDE Tier 1 node attica: PASS"

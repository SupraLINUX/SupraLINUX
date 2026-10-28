#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${ROOT}/.work/authoritative-frameworks-sample"
SOURCE_DIR="${WORK_DIR}/source"
OUT_DIR="${WORK_DIR}/out"
EVIDENCE_DIR="${ROOT}/evidence/authoritative-frameworks-sample"
RESULT_JSON="${EVIDENCE_DIR}/result.json"
CHROOT_TARBALL="${HOME}/.cache/sbuild/resolute-amd64.tar"
MIRROR="${SBUILD_MIRROR:-http://archive.ubuntu.com/ubuntu}"

: "${ECM_ARTIFACT_DIR:?ECM_ARTIFACT_DIR must point at retained ECM PASS evidence}"
: "${KARCHIVE_ARTIFACT_DIR:?KARCHIVE_ARTIFACT_DIR must point at retained KArchive PASS evidence}"

ECM_VERSION="6.30.0-0supralinux3"
ECM_DEB_SHA256="ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f"
KARCHIVE_VERSION="6.30.0-0supralinux4"
KARCHIVE_DSC_SHA256="4938c3df5f4299d5feae1bfe22663dec64455f62519a310d664a5daaeb5839cd"
KARCHIVE_DEBIAN_TAR_SHA256="1f76ab399b9f8c839bdd161b2e0ef0e607e54796e79c96ae8674bf0faae0a11f"
KARCHIVE_ORIG_SHA256="4cf89d91e429d2ece3110e78f7ef7011952b0412cb15011329516b46f21e98e2"
KARCHIVE_HOSTED_RUN="34884764702"
KARCHIVE_HOSTED_ARTIFACT="10364726750"
ECM_HOSTED_RUN="34694951158"
ECM_HOSTED_ARTIFACT="10298635300"

STATE="FAIL"
STAGE="initialization"
PACKAGE_EXECUTION_STARTED=false
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

rm -rf "${WORK_DIR}" "${EVIDENCE_DIR}"
mkdir -p "${SOURCE_DIR}" "${OUT_DIR}" "${EVIDENCE_DIR}" "$(dirname "${CHROOT_TARBALL}")"

write_result() {
    local rc="$?"
    local finished_at
    finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    python3 - "${RESULT_JSON}" "${STATE}" "${rc}" "${STAGE}" "${STARTED_AT}" "${finished_at}" "${PACKAGE_EXECUTION_STARTED}" <<'PY'
import json
import sys
from pathlib import Path

path, state, rc, stage, started, finished, package_started = sys.argv[1:]
Path(path).write_text(json.dumps({
    "node": "karchive",
    "state": state,
    "exit_code": int(rc),
    "stage": stage,
    "started_at": started,
    "finished_at": finished,
    "authoritative": True,
    "run_kind": "authoritative-certification-sample",
    "package_execution_started": package_started == "true",
    "package_state_effect": "none",
    "canonical_package_version": "6.30.0-0supralinux4",
    "runner_class": "supralinux-kvm-ubuntu-26.04-ephemeral",
    "outer_virtualization": "kvm",
    "nested_kvm_runtime": "required",
    "sbuild_backend": "unshare",
    "frameworks_lane_sample": "KArchive",
    "retained_inputs": {
        "ecm_run": 34694951158,
        "ecm_artifact": 10298635300,
        "karchive_run": 34884764702,
        "karchive_artifact": 10364726750,
    },
}, indent=2) + "\n", encoding="utf-8")
PY
}
trap write_result EXIT

exec > >(tee -a "${EVIDENCE_DIR}/pipeline.log") 2>&1

printf '=== SupraLINUX authoritative KDE Frameworks KVM sample ===\n'

STAGE="runner-contract"
"${ROOT}/scripts/check-actions-runner-runtime.sh" "${EVIDENCE_DIR}/actions-runner-runtime.txt"

. /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_ID}" != "26.04" ]]; then
    printf 'Expected Ubuntu 26.04 guest; got %s %s\n' "${ID}" "${VERSION_ID}" >&2
    exit 1
fi
VIRT="$(systemd-detect-virt --vm 2>/dev/null || true)"
if [[ "${VIRT}" != "kvm" ]]; then
    printf 'Frameworks sample requires an outer KVM guest; detected: %s\n' "${VIRT:-none}" >&2
    exit 1
fi
if [[ ! -c /dev/kvm || ! -r /dev/kvm || ! -w /dev/kvm ]]; then
    printf '/dev/kvm must be readable and writable inside the authoritative guest.\n' >&2
    exit 1
fi

required_commands=(
    cmake
    dpkg-architecture
    dpkg-deb
    lintian
    mmdebstrap
    ninja
    qemu-system-x86_64
    readelf
    sbuild
    sha256sum
    systemd-detect-virt
    unshare
)
for command_name in "${required_commands[@]}"; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required Frameworks sample command: %s\n' "${command_name}" >&2
        exit 1
    }
done

qemu-system-x86_64 -accel help 2>&1 | grep -q '^kvm$' || {
    printf 'QEMU does not expose the KVM accelerator.\n' >&2
    exit 1
}
"${ROOT}/scripts/check-nested-kvm-runtime.sh" "${EVIDENCE_DIR}/nested-kvm-runtime.txt"

if ! grep -q "^${USER}:" /etc/subuid; then
    printf 'Runner user lacks subordinate UID range.\n' >&2
    exit 1
fi
if ! grep -q "^${USER}:" /etc/subgid; then
    printf 'Runner user lacks subordinate GID range.\n' >&2
    exit 1
fi
unshare --user --map-auto true

{
    cat /etc/os-release
    printf '\nouter_virtualization=%s\n' "${VIRT}"
    printf 'mirror=%s\n' "${MIRROR}"
    printf '\nactions_runner_runtime:\n'
    cat "${EVIDENCE_DIR}/actions-runner-runtime.txt"
    printf '\ntool_versions:\n'
    dpkg-query -W -f='${Package}\t${Version}\n' cmake lintian ninja-build qt6-base-dev mmdebstrap sbuild 2>/dev/null
} > "${EVIDENCE_DIR}/environment.txt"

STAGE="retained-input-validation"
ECM_DEB="$(find "${ECM_ARTIFACT_DIR}" -type f -name "extra-cmake-modules_${ECM_VERSION}_all.deb" -print -quit)"
KARCHIVE_DSC="$(find "${KARCHIVE_ARTIFACT_DIR}" -type f -name "kf6-karchive_${KARCHIVE_VERSION}.dsc" -print -quit)"
KARCHIVE_DEBIAN_TAR="$(find "${KARCHIVE_ARTIFACT_DIR}" -type f -name "kf6-karchive_${KARCHIVE_VERSION}.debian.tar.xz" -print -quit)"
KARCHIVE_ORIG="$(find "${KARCHIVE_ARTIFACT_DIR}" -type f -name "kf6-karchive_6.30.0.orig.tar.xz" -print -quit)"
for retained in "${ECM_DEB}" "${KARCHIVE_DSC}" "${KARCHIVE_DEBIAN_TAR}" "${KARCHIVE_ORIG}"; do
    [[ -n "${retained}" && -s "${retained}" ]] || {
        printf 'Required retained input missing.\n' >&2
        exit 1
    }
done
printf '%s  %s\n' "${ECM_DEB_SHA256}" "${ECM_DEB}" | sha256sum --check --strict
printf '%s  %s\n' "${KARCHIVE_DSC_SHA256}" "${KARCHIVE_DSC}" | sha256sum --check --strict
printf '%s  %s\n' "${KARCHIVE_DEBIAN_TAR_SHA256}" "${KARCHIVE_DEBIAN_TAR}" | sha256sum --check --strict
printf '%s  %s\n' "${KARCHIVE_ORIG_SHA256}" "${KARCHIVE_ORIG}" | sha256sum --check --strict
[[ "$(dpkg-deb -f "${ECM_DEB}" Package)" == "extra-cmake-modules" ]]
[[ "$(dpkg-deb -f "${ECM_DEB}" Version)" == "${ECM_VERSION}" ]]
cp -a "${KARCHIVE_DSC}" "${KARCHIVE_DEBIAN_TAR}" "${KARCHIVE_ORIG}" "${SOURCE_DIR}/"
sha256sum "${ECM_DEB}" "${SOURCE_DIR}"/* > "${EVIDENCE_DIR}/retained-input-sha256.txt"
cat > "${EVIDENCE_DIR}/retained-inputs.txt" <<EOF
ecm_run=${ECM_HOSTED_RUN}
ecm_artifact=${ECM_HOSTED_ARTIFACT}
karchive_run=${KARCHIVE_HOSTED_RUN}
karchive_artifact=${KARCHIVE_HOSTED_ARTIFACT}
ecm_version=${ECM_VERSION}
karchive_version=${KARCHIVE_VERSION}
EOF

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
PACKAGE_EXECUTION_STARTED=true
sbuild \
    --verbose \
    --chroot-mode=unshare \
    --dist=resolute \
    --arch=amd64 \
    --arch-all \
    --extra-package="${ECM_DEB}" \
    --build-dir="${OUT_DIR}" \
    "${SOURCE_DIR}/kf6-karchive_${KARCHIVE_VERSION}.dsc" |& tee "${EVIDENCE_DIR}/sbuild.log"

mapfile -t DEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DDEBS < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
mapfile -t CHANGES < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.changes' -print | sort)
mapfile -t BUILDINFO < <(find "${OUT_DIR}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)

if (( ${#DEBS[@]} != 4 || ${#CHANGES[@]} != 1 || ${#BUILDINFO[@]} != 1 )); then
    printf 'Unexpected KArchive outputs: deb=%d changes=%d buildinfo=%d\n' \
        "${#DEBS[@]}" "${#CHANGES[@]}" "${#BUILDINFO[@]}" >&2
    exit 1
fi
grep -F "extra-cmake-modules (= ${ECM_VERSION})" "${BUILDINFO[0]}" > "${EVIDENCE_DIR}/ecm-buildinfo-proof.txt"
grep -Fq '100% tests passed, 0 tests failed out of 5' "${EVIDENCE_DIR}/sbuild.log"

STAGE="artifact-contract"
declare -A DEB_BY_PACKAGE=()
for deb in "${DEBS[@]}"; do
    package="$(dpkg-deb -f "${deb}" Package)"
    DEB_BY_PACKAGE["${package}"]="${deb}"
    [[ "$(dpkg-deb -f "${deb}" Version)" == "${KARCHIVE_VERSION}" ]]
done
for package in libkf6archive-data libkf6archive-dev libkf6archive-doc libkf6archive6; do
    [[ -n "${DEB_BY_PACKAGE[${package}]:-}" ]] || {
        printf 'Missing expected KArchive binary package: %s\n' "${package}" >&2
        exit 1
    }
done

STAGE="abi-check"
RUNTIME_ROOT="${WORK_DIR}/runtime-root"
mkdir -p "${RUNTIME_ROOT}"
dpkg-deb -x "${DEB_BY_PACKAGE[libkf6archive6]}" "${RUNTIME_ROOT}"
LIB_PATH="$(find "${RUNTIME_ROOT}" -type f -name 'libKF6Archive.so.6.*' -print -quit)"
[[ -n "${LIB_PATH}" ]]
readelf -d "${LIB_PATH}" > "${EVIDENCE_DIR}/readelf-dynamic.txt"
grep -Fq 'Library soname: [libKF6Archive.so.6]' "${EVIDENCE_DIR}/readelf-dynamic.txt"

# Retain successful build outputs before post-build validators.
STAGE="artifact-capture"
sha256sum "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" > "${EVIDENCE_DIR}/artifact-sha256.txt"
cp -a "${DEBS[@]}" "${DDEBS[@]}" "${CHANGES[@]}" "${BUILDINFO[@]}" "${EVIDENCE_DIR}/"

STAGE="lintian"
lintian --fail-on error "${CHANGES[0]}" |& tee "${EVIDENCE_DIR}/lintian.log"

STAGE="consumer-smoke"
CONSUMER_META="${ROOT}/packages/kde/karchive/consumer"
CONSUMER_ROOT="${WORK_DIR}/consumer-root"
CONSUMER_BUILD="${WORK_DIR}/consumer-build"
mkdir -p "${CONSUMER_ROOT}"
for deb in "${DEBS[@]}"; do
    dpkg-deb -x "${deb}" "${CONSUMER_ROOT}"
done
cmake -S "${CONSUMER_META}" -B "${CONSUMER_BUILD}" -GNinja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="${CONSUMER_ROOT}/usr" |& tee "${EVIDENCE_DIR}/consumer-configure.log"
cmake --build "${CONSUMER_BUILD}" --verbose |& tee "${EVIDENCE_DIR}/consumer-build.log"
MULTIARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
LD_LIBRARY_PATH="${CONSUMER_ROOT}/usr/lib/${MULTIARCH}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" \
    "${CONSUMER_BUILD}/karchive-consumer" |& tee "${EVIDENCE_DIR}/consumer-run.log"

STATE="PASS"
STAGE="complete"
printf 'Authoritative KDE Frameworks sample proof: PASS (KArchive %s)\n' "${KARCHIVE_VERSION}"

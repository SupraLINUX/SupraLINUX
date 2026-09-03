#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT}/build/ksq-1/environment/build-environment.env"
WRAPPER_SOURCE="${ROOT}/scripts/ci/ksq-sbuild-network-proof-wrapper.sh"
PROBE_DIR="${AURORA_KSQ_1_NATIVE_NETWORK_PROBE_DIR:-/opt/supralinux/ksq-sbuild-network-proof}"
MOUNTPOINT="/mnt"

fail() {
    echo "AURORA_KSQ_1_NATIVE_NETWORK_PROOF_FAILURE: $*" >&2
    exit 1
}

[[ -f "${ENV_FILE}" ]] || fail "build environment missing"
[[ -f "${WRAPPER_SOURCE}" ]] || fail "network proof wrapper missing"
# shellcheck disable=SC1090
. "${ENV_FILE}"

TARBALL="${AURORA_KSQ_1_BUILD_ENV_TARBALL:?missing buildd tarball}"
SBUILD_CONFIG_FILE="${AURORA_KSQ_1_SBUILD_CONFIG:?missing sbuild config}"
SLICE_ROOT="${AURORA_KSQ_1_BUILD_ENV_LOCAL_SLICE:?missing local slice}"

[[ -s "${TARBALL}" ]] || fail "buildd tarball missing"
[[ -f "${SBUILD_CONFIG_FILE}" ]] || fail "sbuild config missing"
[[ -d "${SLICE_ROOT}/ubuntu" ]] || fail "local snapshot bind source missing"
[[ "${PROBE_DIR}" == /opt/supralinux/* ]] || fail "probe source must live below /opt/supralinux"

# The unshare backend requires an existing mount target in the extracted rootfs.
tar --zstd -tf "${TARBALL}" \
    | sed -e 's#^\./##' -e 's#/$##' \
    | grep -qx 'mnt' \
    || fail "/mnt absent from buildd rootfs"

root_cmd=()
if (( EUID != 0 )); then
    command -v sudo >/dev/null || fail "sudo required to stage root-owned probe source"
    root_cmd=(sudo)
fi

"${root_cmd[@]}" rm -rf "${PROBE_DIR}"
"${root_cmd[@]}" install -d -m 0755 "${PROBE_DIR}"
"${root_cmd[@]}" install -m 0755 "${WRAPPER_SOURCE}" "${PROBE_DIR}/network-proof-wrapper"
readlink /proc/self/ns/net > "${ROOT}/build/ksq-1/environment/host-netns.txt"
"${root_cmd[@]}" install -m 0644 \
    "${ROOT}/build/ksq-1/environment/host-netns.txt" \
    "${PROBE_DIR}/host-netns.txt"

# Replace the default bind array with the same local-snapshot bind plus the
# root-owned proof source. Keep network disabled explicitly. BUILD_ENV_CMND
# wraps the real dpkg-buildpackage command, so the proof runs in the exact
# build context affected by sbuild-usernsexec --nonet.
cat >> "${SBUILD_CONFIG_FILE}" <<EOF_SBUILD_PROOF
\$unshare_bind_mounts = [
  { directory => "${SLICE_ROOT}/ubuntu", mountpoint => "${SLICE_ROOT}/ubuntu" },
  { directory => "${PROBE_DIR}", mountpoint => "${MOUNTPOINT}" },
];
\$enable_network = 0;
\$build_env_cmnd = "${MOUNTPOINT}/network-proof-wrapper";
EOF_SBUILD_PROOF

{
    echo "AURORA_KSQ_1_NATIVE_NETWORK_PROOF_SOURCE=${PROBE_DIR}"
    echo "AURORA_KSQ_1_NATIVE_NETWORK_PROOF_MOUNTPOINT=${MOUNTPOINT}"
    echo "AURORA_KSQ_1_NATIVE_NETWORK_PROOF_HOST_NETNS=$(cat "${ROOT}/build/ksq-1/environment/host-netns.txt")"
    echo "AURORA_KSQ_1_NATIVE_NETWORK_PROOF_SBUILD_CONFIG=${SBUILD_CONFIG_FILE}"
    echo "AURORA_KSQ_1_NATIVE_NETWORK_PROOF_ENABLE_NETWORK=0"
    echo "AURORA_KSQ_1_NATIVE_NETWORK_PROOF_BUILD_ENV_CMND=${MOUNTPOINT}/network-proof-wrapper"
    echo "AURORA_KSQ_1_NATIVE_NETWORK_PROOF=PASS"
} > "${ROOT}/build/ksq-1/environment/native-sbuild-network-proof.env"

{
    echo '# Native sbuild network-proof bind source'
    findmnt -T "${PROBE_DIR}" -o TARGET,SOURCE,FSTYPE,OPTIONS,PROPAGATION
    stat -c '%A %a %U %G %u %g %n' \
        "${PROBE_DIR}" \
        "${PROBE_DIR}/network-proof-wrapper" \
        "${PROBE_DIR}/host-netns.txt"
    namei -l "${PROBE_DIR}"
} > "${ROOT}/build/ksq-1/environment/native-sbuild-network-proof-topology.txt"

cat "${ROOT}/build/ksq-1/environment/native-sbuild-network-proof.env"

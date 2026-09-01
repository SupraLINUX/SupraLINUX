#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${ROOT}/build/ksq-1/environment"
SNAPSHOT="20260829T022000Z"
SLICE_ROOT="${AURORA_KSQ_LOCAL_SLICE_ROOT:-/opt/supralinux/archive/${SNAPSHOT}}"
SOURCES="${ROOT}/build/ksq-0/apt/resolute.sources"
TARBALL="${OUT}/resolute-amd64-buildd.tar.zst"
SBUILD_CONFIG_FILE="${OUT}/sbuild-local.conf"

. /etc/os-release
[[ "${VERSION_CODENAME:-}" == "resolute" ]] || { echo "AURORA_KSQ_1_ENV_FAILURE: expected Resolute" >&2; exit 1; }
[[ "$(dpkg --print-architecture)" == "amd64" ]] || { echo "AURORA_KSQ_1_ENV_FAILURE: expected amd64" >&2; exit 1; }
[[ -f "${SOURCES}" ]] || { echo "AURORA_KSQ_1_ENV_FAILURE: local Resolute source file missing" >&2; exit 1; }
[[ -f "${SLICE_ROOT}/COMPLETE" ]] || { echo "AURORA_KSQ_1_ENV_FAILURE: local snapshot incomplete" >&2; exit 1; }
for command in sbuild mmdebstrap newuidmap newgidmap zstd; do
  command -v "${command}" >/dev/null || { echo "AURORA_KSQ_1_ENV_FAILURE: missing ${command}" >&2; exit 1; }
done

mkdir -p "${OUT}"
rm -f "${TARBALL}"
mmdebstrap \
  --mode=unshare \
  --variant=buildd \
  --architectures=amd64 \
  --include=ca-certificates,ubuntu-keyring \
  --hook-dir=/usr/share/mmdebstrap/hooks/file-mirror-automount \
  resolute "${TARBALL}" "${SOURCES}"

[[ -s "${TARBALL}" ]] || { echo "AURORA_KSQ_1_ENV_FAILURE: buildd tarball missing" >&2; exit 1; }

INSPECT="${OUT}/inspect"
rm -rf "${INSPECT}"
mkdir -p "${INSPECT}"
tar --zstd -xf "${TARBALL}" -C "${INSPECT}" ./etc/apt >/dev/null

grep -RqsF "file:${SLICE_ROOT}/ubuntu" "${INSPECT}/etc/apt" || {
  echo "AURORA_KSQ_1_ENV_FAILURE: local snapshot URI absent from build environment" >&2
  exit 1
}
if grep -RqsE 'https?://' "${INSPECT}/etc/apt"; then
  echo "AURORA_KSQ_1_ENV_FAILURE: remote APT URI leaked into build environment" >&2
  grep -RnsE 'https?://' "${INSPECT}/etc/apt" >&2 || true
  exit 1
fi
if grep -RqsE '^Suites:.*stonking|[[:space:]]stonking([[:space:]]|$)' "${INSPECT}/etc/apt"; then
  echo "AURORA_KSQ_1_ENV_FAILURE: Stonking binary suite leaked into build environment" >&2
  exit 1
fi

cat > "${SBUILD_CONFIG_FILE}" <<EOF_SBUILD
\$unshare_bind_mounts = [ { directory => "${SLICE_ROOT}/ubuntu", mountpoint => "${SLICE_ROOT}/ubuntu" } ];
\$enable_network = 0;
EOF_SBUILD
chmod 0644 "${SBUILD_CONFIG_FILE}"

sha256sum "${TARBALL}" > "${OUT}/resolute-amd64-buildd.tar.zst.sha256"
{
  echo "AURORA_KSQ_1_BUILD_ENV_SNAPSHOT=${SNAPSHOT}"
  echo "AURORA_KSQ_1_BUILD_ENV_ARCH=amd64"
  echo "AURORA_KSQ_1_BUILD_ENV_BACKEND=unshare"
  echo "AURORA_KSQ_1_BUILD_ENV_TARBALL=${TARBALL}"
  echo "AURORA_KSQ_1_SBUILD_CONFIG=${SBUILD_CONFIG_FILE}"
  echo "AURORA_KSQ_1_BUILD_ENV_LOCAL_SLICE=${SLICE_ROOT}"
  echo "AURORA_KSQ_1_BUILD_ENV_REMOTE_FALLBACK=forbidden"
} > "${OUT}/build-environment.env"

{
  sbuild --version | head -n1
  mmdebstrap --version | head -n1
} > "${OUT}/build-environment-tool-versions.txt"

cat "${OUT}/build-environment.env"
echo "AURORA_KSQ_1_LOCAL_BUILD_ENV_SUCCESS"

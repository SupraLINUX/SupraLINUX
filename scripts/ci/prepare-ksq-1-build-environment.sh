#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${ROOT}/build/ksq-1/environment"
SNAPSHOT_ENV="${ROOT}/tests/kde-stack/apt-metadata-snapshot.env"

. /etc/os-release
[[ "${VERSION_CODENAME:-}" == "resolute" ]] || { echo "AURORA_KSQ_1_ENV_FAILURE: runner is not Resolute" >&2; exit 1; }
[[ "$(dpkg --print-architecture)" == "amd64" ]] || { echo "AURORA_KSQ_1_ENV_FAILURE: runner is not amd64" >&2; exit 1; }
for command in sbuild mmdebstrap newuidmap newgidmap zstd; do
  command -v "${command}" >/dev/null || { echo "AURORA_KSQ_1_ENV_FAILURE: missing ${command}" >&2; exit 1; }
done

# shellcheck disable=SC1090
. "${SNAPSHOT_ENV}"
SNAPSHOT="${AURORA_KSQ_0_APT_SNAPSHOT:?missing KSQ-0 snapshot}"
[[ "${SNAPSHOT}" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] || { echo "AURORA_KSQ_1_ENV_FAILURE: invalid snapshot ${SNAPSHOT}" >&2; exit 1; }

mkdir -p "${OUT}"
SOURCES="${OUT}/resolute-snapshot.sources"
TARBALL="${OUT}/resolute-amd64-buildd.tar.zst"
cat > "${SOURCES}" <<EOF_SOURCES
Types: deb
URIs: https://snapshot.ubuntu.com/ubuntu/${SNAPSHOT}/
Suites: resolute resolute-updates resolute-security resolute-backports
Components: main universe restricted multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF_SOURCES

rm -f "${TARBALL}"
mmdebstrap \
  --mode=unshare \
  --variant=buildd \
  --architectures=amd64 \
  --include=ca-certificates,ubuntu-keyring \
  --aptopt='Acquire::Check-Valid-Until "false";' \
  --aptopt='Acquire::Retries "5";' \
  --aptopt='APT::Update::Error-Mode "any";' \
  resolute "${TARBALL}" "${SOURCES}"

[[ -s "${TARBALL}" ]] || { echo "AURORA_KSQ_1_ENV_FAILURE: buildd tarball missing" >&2; exit 1; }

INSPECT="${OUT}/inspect"
rm -rf "${INSPECT}"
mkdir -p "${INSPECT}"
tar --zstd -xf "${TARBALL}" -C "${INSPECT}" ./etc/apt >/dev/null

grep -RqsF "https://snapshot.ubuntu.com/ubuntu/${SNAPSHOT}/" "${INSPECT}/etc/apt" || {
  echo "AURORA_KSQ_1_ENV_FAILURE: snapshot URI absent from build environment" >&2
  exit 1
}
if grep -RqsE '(^|[/.:])(archive\.ubuntu\.com|security\.ubuntu\.com)([/:]|$)' "${INSPECT}/etc/apt"; then
  echo "AURORA_KSQ_1_ENV_FAILURE: live Ubuntu archive leaked into build environment" >&2
  grep -RnsE 'archive\.ubuntu\.com|security\.ubuntu\.com' "${INSPECT}/etc/apt" >&2 || true
  exit 1
fi
if grep -RqsE '^Suites:.*stonking|[[:space:]]stonking([[:space:]]|$)' "${INSPECT}/etc/apt"; then
  echo "AURORA_KSQ_1_ENV_FAILURE: Stonking binary suite leaked into build environment" >&2
  exit 1
fi

sha256sum "${TARBALL}" > "${OUT}/resolute-amd64-buildd.tar.zst.sha256"
{
  echo "AURORA_KSQ_1_BUILD_ENV_SNAPSHOT=${SNAPSHOT}"
  echo "AURORA_KSQ_1_BUILD_ENV_ARCH=amd64"
  echo "AURORA_KSQ_1_BUILD_ENV_BACKEND=unshare"
  echo "AURORA_KSQ_1_BUILD_ENV_TARBALL=${TARBALL}"
} > "${OUT}/build-environment.env"

{
  sbuild --version | head -n1
  mmdebstrap --version | head -n1
} > "${OUT}/build-environment-tool-versions.txt"

cat "${OUT}/build-environment.env"
cat "${OUT}/build-environment-tool-versions.txt"
echo "AURORA_KSQ_1_BUILD_ENV_SUCCESS"

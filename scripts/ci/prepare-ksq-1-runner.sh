#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

. /etc/os-release
[[ "${VERSION_CODENAME:-}" == "resolute" ]] || {
  echo "AURORA_KSQ_1_RUNNER_FAILURE: runner is not Resolute" >&2
  exit 1
}
[[ "$(dpkg --print-architecture)" == "amd64" ]] || {
  echo "AURORA_KSQ_1_RUNNER_FAILURE: runner is not amd64" >&2
  exit 1
}

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  sbuild mmdebstrap uidmap libcap2-bin zstd devscripts dpkg-dev apt-utils \
  ca-certificates ubuntu-keyring gzip

build_user="$(id -un)"
if ! grep -q "^${build_user}:" /etc/subuid; then
  sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 "${build_user}"
fi

# Ubuntu Resolute uidmap 1:4.17.4-2ubuntu3 was proven on this nested-unshare
# builder to fail in stock setuid mode and to pass with the precise upstream
# file-capability model. Keep this normalization version-scoped and fail closed
# if the distribution package changes until its behavior is re-qualified.
bash "${ROOT}/scripts/ci/configure-ksq-uidmap-filecaps.sh"

mkdir -p "${ROOT}/build/ksq-1"
dpkg-query -W -f='${Package}\t${Version}\n' \
  sbuild mmdebstrap uidmap libcap2-bin dpkg-dev apt-utils ubuntu-keyring \
  | sort > "${ROOT}/build/ksq-1/build-tool-versions.tsv"

bash "${ROOT}/scripts/ci/validate-kde-stack-source-manifests.sh"
python3 "${ROOT}/scripts/ci/validate-kde-stack-roots.py"
bash "${ROOT}/scripts/ci/prepare-kde-stack-apt-metadata.sh"
python3 "${ROOT}/scripts/ci/generate-kde-build-closure.py"

# shellcheck disable=SC1091
. "${ROOT}/build/ksq-0/closure-status.env"
[[ "${AURORA_KSQ_0_CLOSURE_STATUS}" == "COMPLETE" ]]
[[ "${AURORA_KSQ_0_CLOSURE_UNRESOLVED}" == "0" ]]
[[ "${AURORA_KSQ_0_CLOSURE_SOURCES}" == "101" ]]
[[ "${AURORA_KSQ_0_CLOSURE_BUILD_ORDERED}" == "101" ]]

bash "${ROOT}/scripts/ci/audit-kde-stack-source-selections.sh"
bash "${ROOT}/scripts/ci/prepare-ksq-1-build-environment.sh"

echo "AURORA_KSQ_1_RUNNER_SNAPSHOT=${AURORA_KSQ_0_APT_SNAPSHOT}"
echo "AURORA_KSQ_1_RUNNER_SUCCESS"

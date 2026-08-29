#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${ROOT}/build/ksq-0"
APT_ROOT="${OUT}/apt"
SNAPSHOT_FILE="${ROOT}/tests/kde-stack/apt-metadata-snapshot.env"

. /etc/os-release
if [[ "${VERSION_CODENAME:-}" != "resolute" ]]; then
  echo "AURORA_KSQ_0_APT_FAILURE: expected resolute runner, got ${VERSION_CODENAME:-unknown}" >&2
  exit 1
fi
if [[ "$(dpkg --print-architecture)" != "amd64" ]]; then
  echo "AURORA_KSQ_0_APT_FAILURE: expected amd64 runner" >&2
  exit 1
fi
if [[ ! -f "${SNAPSHOT_FILE}" ]]; then
  echo "AURORA_KSQ_0_APT_FAILURE: missing snapshot manifest: ${SNAPSHOT_FILE}" >&2
  exit 1
fi
# shellcheck disable=SC1090
. "${SNAPSHOT_FILE}"
if [[ ! "${AURORA_KSQ_0_APT_SNAPSHOT:-}" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
  echo "AURORA_KSQ_0_APT_FAILURE: invalid Ubuntu snapshot ID" >&2
  exit 1
fi
SNAPSHOT_ID="${AURORA_KSQ_0_APT_SNAPSHOT}"

rm -rf "${APT_ROOT}"
mkdir -p \
  "${APT_ROOT}/resolute-lists/partial" \
  "${APT_ROOT}/stonking-lists/partial" \
  "${APT_ROOT}/resolute-cache/archives/partial" \
  "${APT_ROOT}/stonking-cache/archives/partial"
: > "${APT_ROOT}/empty-status"

cat > "${APT_ROOT}/resolute.sources" <<EOF_RESOLUTE
Types: deb deb-src
URIs: http://archive.ubuntu.com/ubuntu/
Suites: resolute resolute-updates resolute-backports
Components: main restricted universe multiverse
Architectures: amd64
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Snapshot: ${SNAPSHOT_ID}

Types: deb deb-src
URIs: http://security.ubuntu.com/ubuntu/
Suites: resolute-security
Components: main restricted universe multiverse
Architectures: amd64
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Snapshot: ${SNAPSHOT_ID}
EOF_RESOLUTE

cat > "${APT_ROOT}/stonking.sources" <<EOF_STONKING
Types: deb-src
URIs: http://archive.ubuntu.com/ubuntu/
Suites: stonking
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Snapshot: ${SNAPSHOT_ID}
EOF_STONKING

apt_opts() {
  local profile="$1"
  printf '%s\n' \
    "-o" "Dir::Etc::sourcelist=${APT_ROOT}/${profile}.sources" \
    "-o" "Dir::Etc::sourceparts=-" \
    "-o" "Dir::State::lists=${APT_ROOT}/${profile}-lists" \
    "-o" "Dir::State::status=${APT_ROOT}/empty-status" \
    "-o" "Dir::Cache=${APT_ROOT}/${profile}-cache" \
    "-o" "APT::Architecture=amd64" \
    "-o" "APT::Architectures=amd64" \
    "-o" "Acquire::Languages=none"
}

run_apt() {
  local profile="$1"
  shift
  mapfile -t opts < <(apt_opts "${profile}")
  sudo apt-get "${opts[@]}" "$@"
}

run_apt resolute update
run_apt stonking update

for profile in resolute stonking; do
  mapfile -t opts < <(apt_opts "${profile}")
  apt-get "${opts[@]}" indextargets > "${OUT}/apt-${profile}-indextargets.txt"
done

if grep -Eq '(^|[[:space:]])stonking([/[:space:]]|$)' "${OUT}/apt-resolute-indextargets.txt"; then
  echo "AURORA_KSQ_0_APT_FAILURE: Stonking leaked into Resolute APT metadata" >&2
  exit 1
fi
if grep -q '^Identifier: Packages$' "${OUT}/apt-stonking-indextargets.txt"; then
  echo "AURORA_KSQ_0_APT_FAILURE: Stonking binary Packages index is enabled" >&2
  exit 1
fi
if ! grep -q '^Identifier: Sources$' "${OUT}/apt-stonking-indextargets.txt"; then
  echo "AURORA_KSQ_0_APT_FAILURE: Stonking source index is missing" >&2
  exit 1
fi

{
  find "${APT_ROOT}/resolute-lists" "${APT_ROOT}/stonking-lists" -maxdepth 1 -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum
} > "${OUT}/apt-metadata.sha256"

printf 'AURORA_KSQ_0_APT_SNAPSHOT=%s\n' "${SNAPSHOT_ID}"
printf 'AURORA_KSQ_0_APT_BINARY_SUITE=resolute\n'
printf 'AURORA_KSQ_0_APT_SOURCE_SUITES=resolute+stonking\n'
printf 'AURORA_KSQ_0_APT_STONKING_BINARY_INDEXES=0\n'
printf 'AURORA_KSQ_0_APT_METADATA_SUCCESS\n'

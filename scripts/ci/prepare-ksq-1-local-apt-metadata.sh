#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${ROOT}/build/ksq-0"
APT_ROOT="${OUT}/apt"
SNAPSHOT="20260829T022000Z"
SLICE_ROOT="${AURORA_KSQ_LOCAL_SLICE_ROOT:-/opt/supralinux/archive/${SNAPSHOT}}"
ARCHIVE="${SLICE_ROOT}/ubuntu"

. /etc/os-release
[[ "${VERSION_CODENAME:-}" == "resolute" ]] || { echo "AURORA_KSQ_1_LOCAL_APT_FAILURE: expected Resolute" >&2; exit 1; }
[[ "$(dpkg --print-architecture)" == "amd64" ]] || { echo "AURORA_KSQ_1_LOCAL_APT_FAILURE: expected amd64" >&2; exit 1; }
[[ -f "${SLICE_ROOT}/COMPLETE" && -f "${SLICE_ROOT}/aurora-local.sources" ]] || { echo "AURORA_KSQ_1_LOCAL_APT_FAILURE: slice incomplete" >&2; exit 1; }
[[ -d "${ARCHIVE}/dists/resolute" && -d "${ARCHIVE}/dists/stonking" ]] || { echo "AURORA_KSQ_1_LOCAL_APT_FAILURE: signed archive metadata missing" >&2; exit 1; }

rm -rf "${APT_ROOT}"
mkdir -p \
  "${APT_ROOT}/resolute-lists/partial" \
  "${APT_ROOT}/stonking-lists/partial" \
  "${APT_ROOT}/resolute-cache/archives/partial" \
  "${APT_ROOT}/stonking-cache/archives/partial"
: > "${APT_ROOT}/empty-status"
chmod -R a+rX,u+w "${APT_ROOT}"

cat > "${APT_ROOT}/resolute.sources" <<EOF_RESOLUTE
Types: deb deb-src
URIs: file:${ARCHIVE}
Suites: resolute resolute-updates resolute-security resolute-backports
Components: main restricted universe multiverse
Architectures: amd64
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no
EOF_RESOLUTE

cat > "${APT_ROOT}/stonking.sources" <<EOF_STONKING
Types: deb-src
URIs: file:${ARCHIVE}
Suites: stonking
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
Check-Valid-Until: no
Snapshot: no
EOF_STONKING

apt_opts() {
  local profile="$1"
  printf '%s\n' \
    -o "Dir::Etc::sourcelist=${APT_ROOT}/${profile}.sources" \
    -o "Dir::Etc::sourceparts=-" \
    -o "Dir::State::lists=${APT_ROOT}/${profile}-lists" \
    -o "Dir::State::status=${APT_ROOT}/empty-status" \
    -o "Dir::Cache=${APT_ROOT}/${profile}-cache" \
    -o "APT::Architecture=amd64" \
    -o "APT::Architectures=amd64" \
    -o "Acquire::Languages=none" \
    -o "Acquire::Retries=0" \
    -o "Acquire::http::Proxy=http://127.0.0.1:9/" \
    -o "Acquire::https::Proxy=http://127.0.0.1:9/"
}

for profile in resolute stonking; do
  mapfile -t opts < <(apt_opts "${profile}")
  apt-get "${opts[@]}" -o APT::Update::Error-Mode=any update
  apt-get "${opts[@]}" indextargets > "${OUT}/apt-${profile}-indextargets.txt"
done

for evidence in "${OUT}/apt-resolute-indextargets.txt" "${OUT}/apt-stonking-indextargets.txt"; do
  grep -Fq "Repo-URI: file:${ARCHIVE}/" "${evidence}" || {
    echo "AURORA_KSQ_1_LOCAL_APT_FAILURE: local Repo-URI absent in ${evidence}" >&2
    exit 1
  }
  if grep -Eq '^Repo-URI: https?://' "${evidence}"; then
    echo "AURORA_KSQ_1_LOCAL_APT_FAILURE: remote Repo-URI leaked into ${evidence}" >&2
    exit 1
  fi
done
if grep -q '^Identifier: Packages$' "${OUT}/apt-stonking-indextargets.txt"; then
  echo "AURORA_KSQ_1_LOCAL_APT_FAILURE: stonking binary index enabled" >&2
  exit 1
fi
grep -q '^Identifier: Sources$' "${OUT}/apt-stonking-indextargets.txt" || {
  echo "AURORA_KSQ_1_LOCAL_APT_FAILURE: stonking source index missing" >&2
  exit 1
}

find "${APT_ROOT}/resolute-lists" "${APT_ROOT}/stonking-lists" \
  -maxdepth 1 -type f ! -name lock -print0 | sort -z | xargs -0 sha256sum > "${OUT}/apt-metadata.sha256"
chmod -R a+rX,a+w "${APT_ROOT}"

printf 'AURORA_KSQ_1_LOCAL_APT_SNAPSHOT=%s\n' "${SNAPSHOT}"
printf 'AURORA_KSQ_1_LOCAL_APT_URI=file:%s\n' "${ARCHIVE}"
printf 'AURORA_KSQ_1_LOCAL_APT_SUCCESS\n'

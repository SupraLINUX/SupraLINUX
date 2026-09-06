#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE="${1:?source package required}"
BASE_VERSION="${2:?packaging base version required}"
WORKDIR="${3:?work directory required}"
APT_ROOT="${ROOT}/build/ksq-0/apt"
AUDIT_DOWNLOADS="${ROOT}/build/ksq-0/source-audit/downloads"
FETCH_MODE="${AURORA_KSQ_1_FETCH_TRANSPORT_MODE:-local-only}"
SNAPSHOT="20260829T022000Z"
SNAPSHOT_URI="https://snapshot.ubuntu.com/ubuntu/${SNAPSHOT}/"

fail() {
  echo "AURORA_KSQ_1_FETCH_FAILURE: $*" >&2
  exit 1
}

[[ "${FETCH_MODE}" == "local-only" || "${FETCH_MODE}" == "snapshot-witness" ]] \
  || fail "unsupported transport mode ${FETCH_MODE}"
[[ -f "${APT_ROOT}/stonking.sources" ]] || fail "KSQ-0-compatible local APT metadata missing"
[[ -f "${APT_ROOT}/resolute.sources" ]] || fail "Resolute local APT metadata missing"

if [[ "${FETCH_MODE}" == "snapshot-witness" ]]; then
  for sources_file in "${APT_ROOT}/stonking.sources" "${APT_ROOT}/resolute.sources"; do
    mapfile -t source_uris < <(sed -n 's/^URIs:[[:space:]]*//p' "${sources_file}" | sort -u)
    [[ "${#source_uris[@]}" -eq 1 ]] || fail "${sources_file} does not contain exactly one source URI"
    [[ "${source_uris[0]}" == "${SNAPSHOT_URI}" ]] \
      || fail "${sources_file} source URI drifted from ${SNAPSHOT_URI}"
  done
fi

rm -rf "${WORKDIR}"
mkdir -p "${WORKDIR}"
WORKDIR="$(realpath "${WORKDIR}")"
cd "${WORKDIR}"

common_opts=(
  -o "Dir::Etc::sourceparts=-"
  -o "Dir::State::status=${APT_ROOT}/empty-status"
  -o "APT::Architecture=amd64"
  -o "APT::Architectures=amd64"
  -o "Acquire::Languages=none"
  -o "Acquire::Retries=0"
  -o "Acquire::http::Proxy=http://127.0.0.1:9/"
  -o "Acquire::https::Proxy=http://127.0.0.1:9/"
)
if [[ "${FETCH_MODE}" == "snapshot-witness" ]]; then
  common_opts+=(
    -o "Acquire::http::Proxy::snapshot.ubuntu.com=DIRECT"
    -o "Acquire::https::Proxy::snapshot.ubuntu.com=DIRECT"
  )
fi
stonking_opts=(
  "${common_opts[@]}"
  -o "Dir::Etc::sourcelist=${APT_ROOT}/stonking.sources"
  -o "Dir::State::lists=${APT_ROOT}/stonking-lists"
  -o "Dir::Cache=${APT_ROOT}/stonking-cache"
  -o "Acquire::Source-Symlinks=false"
)
resolute_opts=(
  "${common_opts[@]}"
  -o "Dir::Etc::sourcelist=${APT_ROOT}/resolute.sources"
  -o "Dir::State::lists=${APT_ROOT}/resolute-lists"
  -o "Dir::Cache=${APT_ROOT}/resolute-cache"
)

if [[ "${SOURCE}" == "wayland-protocols" && "${BASE_VERSION}" == "1.48-1" ]]; then
  for file in \
    wayland-protocols_1.48-1.dsc \
    wayland-protocols_1.48.orig.tar.xz \
    wayland-protocols_1.48.orig.tar.xz.asc \
    wayland-protocols_1.48-1.debian.tar.xz; do
    [[ -f "${AUDIT_DOWNLOADS}/${file}" ]] || fail "certified Debian source object missing: ${file}"
    cp -a "${AUDIT_DOWNLOADS}/${file}" .
  done
else
  fetch_log="${WORKDIR}/apt-source-fetch.log"
  apt-get "${stonking_opts[@]}" source --download-only "${SOURCE}=${BASE_VERSION}" 2>&1 | tee "${fetch_log}"

  if [[ "${FETCH_MODE}" == "local-only" ]]; then
    if grep -Ei '^(Get|Hit|Ign|Err):.*https?://' "${fetch_log}"; then
      fail "remote source transport attempted"
    fi
  else
    python3 - "${fetch_log}" "${SNAPSHOT_URI}" <<'PY'
import re
import sys
from pathlib import Path

log = Path(sys.argv[1])
allowed_base = sys.argv[2].rstrip("/")
seen = 0
for lineno, raw in enumerate(log.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
    if not re.match(r"^(?:Get|Hit|Ign|Err):\d+\s+https?://", raw):
        continue
    parts = raw.split()
    if len(parts) < 2:
        raise SystemExit(f"AURORA_KSQ_1_FETCH_FAILURE: malformed transport line {lineno}: {raw}")
    url = parts[1]
    if url != allowed_base and not url.startswith(allowed_base + "/"):
        raise SystemExit(f"AURORA_KSQ_1_FETCH_FAILURE: non-snapshot transport line {lineno}: {url}")
    seen += 1
if seen == 0:
    raise SystemExit("AURORA_KSQ_1_FETCH_FAILURE: snapshot witness observed no HTTP(S) source transport")
print(f"AURORA_KSQ_1_FETCH_SNAPSHOT_TRANSPORT_LINES={seen}")
PY
  fi
fi

mapfile -t dsc_files < <(find . -maxdepth 1 -type f -name '*.dsc' -printf '%f\n' | sort)
[[ "${#dsc_files[@]}" -eq 1 ]] || {
  echo "AURORA_KSQ_1_FETCH_FAILURE: expected one regular source dsc for ${SOURCE}, found ${#dsc_files[@]}" >&2
  find . -maxdepth 1 -printf '%y %p -> %l\n' >&2
  exit 1
}
ORIGINAL_DSC="${dsc_files[0]}"
grep -Fqx "Source: ${SOURCE}" "${ORIGINAL_DSC}" || fail "dsc source mismatch for ${SOURCE}"
grep -Fqx "Version: ${BASE_VERSION}" "${ORIGINAL_DSC}" || fail "dsc version mismatch for ${SOURCE}"

dpkg-source -x "${ORIGINAL_DSC}" source >/dev/null
python3 "${ROOT}/scripts/ci/prepare-ksq-1-source.py" \
  --source-tree "${WORKDIR}/source" \
  --expected-source "${SOURCE}" \
  --base-version "${BASE_VERSION}"

# shellcheck disable=SC1091
. "${WORKDIR}/supralinux-build-metadata.env"

dpkg --compare-versions "${AURORA_KSQ_1_VERSION}" lt "${BASE_VERSION}" || fail "candidate version does not sort below packaging base"

mapfile -t resolute_versions < <(
  apt-cache "${resolute_opts[@]}" showsrc "${SOURCE}" 2>/dev/null \
    | sed -n 's/^Version: //p' \
    | sort -u
)
for resolute_version in "${resolute_versions[@]}"; do
  dpkg --compare-versions "${AURORA_KSQ_1_VERSION}" gt "${resolute_version}" || {
    fail "${AURORA_KSQ_1_VERSION} does not supersede Resolute source ${resolute_version}"
  }
done

dpkg-source -b source >/dev/null

PREPARED_DSC=""
while IFS= read -r candidate; do
  if grep -Fqx "Source: ${SOURCE}" "${candidate}" && grep -Fqx "Version: ${AURORA_KSQ_1_VERSION}" "${candidate}"; then
    [[ -z "${PREPARED_DSC}" ]] || fail "multiple prepared dsc files for ${SOURCE}"
    PREPARED_DSC="${candidate}"
  fi
done < <(find . -maxdepth 1 -type f -name '*.dsc' -print | sort)
[[ -n "${PREPARED_DSC}" ]] || fail "prepared dsc not found for ${SOURCE} ${AURORA_KSQ_1_VERSION}"

PREPARED_DSC="$(realpath "${PREPARED_DSC}")"
{
  echo "AURORA_KSQ_1_PREPARED_DSC=${PREPARED_DSC}"
  echo "AURORA_KSQ_1_SOURCE=${SOURCE}"
  echo "AURORA_KSQ_1_PACKAGING_BASE=${BASE_VERSION}"
  echo "AURORA_KSQ_1_VERSION=${AURORA_KSQ_1_VERSION}"
  echo "AURORA_KSQ_1_RESOLUTE_SOURCE_VERSIONS=$(IFS=,; echo "${resolute_versions[*]:--}")"
  echo "AURORA_KSQ_1_OVERRIDES_APPLIED=${AURORA_KSQ_1_OVERRIDES_APPLIED}"
  echo "AURORA_KSQ_1_PACKAGING_ADAPTATIONS_APPLIED=${AURORA_KSQ_1_PACKAGING_ADAPTATIONS_APPLIED}"
  echo "AURORA_KSQ_1_PACKAGING_ADAPTATION_IDS=${AURORA_KSQ_1_PACKAGING_ADAPTATION_IDS}"
  echo "AURORA_KSQ_1_COMPAT13_SUBSTVARS_RESTORED=${AURORA_KSQ_1_COMPAT13_SUBSTVARS_RESTORED}"
  echo "AURORA_KSQ_1_FETCH_TRANSPORT_MODE=${FETCH_MODE}"
  if [[ "${FETCH_MODE}" == "snapshot-witness" ]]; then
    echo "AURORA_KSQ_1_FETCH_ALLOWED_REMOTE=${SNAPSHOT_URI}"
    echo "AURORA_KSQ_1_FETCH_OTHER_HTTP_TRANSPORT=blackholed"
  else
    echo "AURORA_KSQ_1_FETCH_ALLOWED_REMOTE=none"
    echo "AURORA_KSQ_1_FETCH_OTHER_HTTP_TRANSPORT=blackholed"
  fi
} > "${WORKDIR}/prepared-source.env"

sha256sum ./* 2>/dev/null | sort > "${WORKDIR}/prepared-source-files.sha256" || true

cat "${WORKDIR}/prepared-source.env"
echo "AURORA_KSQ_1_FETCH_PREP_SUCCESS"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE="${1:?source package required}"
BASE_VERSION="${2:?packaging base version required}"
WORKDIR="${3:?work directory required}"
APT_ROOT="${ROOT}/build/ksq-0/apt"
AUDIT_DOWNLOADS="${ROOT}/build/ksq-0/source-audit/downloads"

[[ -f "${APT_ROOT}/stonking.sources" ]] || { echo "AURORA_KSQ_1_FETCH_FAILURE: KSQ-0 APT metadata missing" >&2; exit 1; }
[[ -f "${APT_ROOT}/resolute.sources" ]] || { echo "AURORA_KSQ_1_FETCH_FAILURE: Resolute APT metadata missing" >&2; exit 1; }

rm -rf "${WORKDIR}"
mkdir -p "${WORKDIR}"
cd "${WORKDIR}"

stonking_opts=(
  -o "Dir::Etc::sourcelist=${APT_ROOT}/stonking.sources"
  -o "Dir::Etc::sourceparts=-"
  -o "Dir::State::lists=${APT_ROOT}/stonking-lists"
  -o "Dir::State::status=${APT_ROOT}/empty-status"
  -o "Dir::Cache=${APT_ROOT}/stonking-cache"
  -o "APT::Architecture=amd64"
  -o "APT::Architectures=amd64"
  -o "Acquire::Languages=none"
)
resolute_opts=(
  -o "Dir::Etc::sourcelist=${APT_ROOT}/resolute.sources"
  -o "Dir::Etc::sourceparts=-"
  -o "Dir::State::lists=${APT_ROOT}/resolute-lists"
  -o "Dir::State::status=${APT_ROOT}/empty-status"
  -o "Dir::Cache=${APT_ROOT}/resolute-cache"
  -o "APT::Architecture=amd64"
  -o "APT::Architectures=amd64"
  -o "Acquire::Languages=none"
)

if [[ "${SOURCE}" == "wayland-protocols" && "${BASE_VERSION}" == "1.48-1" ]]; then
  for file in \
    wayland-protocols_1.48-1.dsc \
    wayland-protocols_1.48.orig.tar.xz \
    wayland-protocols_1.48.orig.tar.xz.asc \
    wayland-protocols_1.48-1.debian.tar.xz; do
    [[ -f "${AUDIT_DOWNLOADS}/${file}" ]] || {
      echo "AURORA_KSQ_1_FETCH_FAILURE: audited Debian source object missing: ${file}" >&2
      exit 1
    }
    cp -a "${AUDIT_DOWNLOADS}/${file}" .
  done
else
  apt-get "${stonking_opts[@]}" source --download-only "${SOURCE}=${BASE_VERSION}"
fi

mapfile -t dsc_files < <(find . -maxdepth 1 -type f -name '*.dsc' -printf '%f\n' | sort)
[[ "${#dsc_files[@]}" -eq 1 ]] || {
  echo "AURORA_KSQ_1_FETCH_FAILURE: expected one source dsc for ${SOURCE}, found ${#dsc_files[@]}" >&2
  printf '%s\n' "${dsc_files[@]}" >&2
  exit 1
}
ORIGINAL_DSC="${dsc_files[0]}"
grep -Fqx "Source: ${SOURCE}" "${ORIGINAL_DSC}" || {
  echo "AURORA_KSQ_1_FETCH_FAILURE: dsc source mismatch for ${SOURCE}" >&2
  exit 1
}
grep -Fqx "Version: ${BASE_VERSION}" "${ORIGINAL_DSC}" || {
  echo "AURORA_KSQ_1_FETCH_FAILURE: dsc version mismatch for ${SOURCE}" >&2
  exit 1
}

dpkg-source -x "${ORIGINAL_DSC}" source >/dev/null
python3 "${ROOT}/scripts/ci/prepare-ksq-1-source.py" \
  --source-tree "${WORKDIR}/source" \
  --expected-source "${SOURCE}" \
  --base-version "${BASE_VERSION}"

# shellcheck disable=SC1091
. "${WORKDIR}/supralinux-build-metadata.env"

dpkg --compare-versions "${AURORA_KSQ_1_VERSION}" lt "${BASE_VERSION}" || {
  echo "AURORA_KSQ_1_FETCH_FAILURE: candidate version does not sort below packaging base" >&2
  exit 1
}

mapfile -t resolute_versions < <(
  apt-cache "${resolute_opts[@]}" showsrc "${SOURCE}" 2>/dev/null \
    | sed -n 's/^Version: //p' \
    | sort -u
)
for resolute_version in "${resolute_versions[@]}"; do
  dpkg --compare-versions "${AURORA_KSQ_1_VERSION}" gt "${resolute_version}" || {
    echo "AURORA_KSQ_1_FETCH_FAILURE: ${AURORA_KSQ_1_VERSION} does not supersede Resolute source ${resolute_version}" >&2
    exit 1
  }
done

# Rebuild the source package after the deterministic changelog/packaging delta.
dpkg-source -b source >/dev/null

PREPARED_DSC=""
while IFS= read -r candidate; do
  if grep -Fqx "Source: ${SOURCE}" "${candidate}" && grep -Fqx "Version: ${AURORA_KSQ_1_VERSION}" "${candidate}"; then
    [[ -z "${PREPARED_DSC}" ]] || {
      echo "AURORA_KSQ_1_FETCH_FAILURE: multiple prepared dsc files for ${SOURCE}" >&2
      exit 1
    }
    PREPARED_DSC="${candidate}"
  fi
done < <(find . -maxdepth 1 -type f -name '*.dsc' -print | sort)
[[ -n "${PREPARED_DSC}" ]] || {
  echo "AURORA_KSQ_1_FETCH_FAILURE: prepared dsc not found for ${SOURCE} ${AURORA_KSQ_1_VERSION}" >&2
  exit 1
}

PREPARED_DSC="$(realpath "${PREPARED_DSC}")"
{
  echo "AURORA_KSQ_1_PREPARED_DSC=${PREPARED_DSC}"
  echo "AURORA_KSQ_1_SOURCE=${SOURCE}"
  echo "AURORA_KSQ_1_PACKAGING_BASE=${BASE_VERSION}"
  echo "AURORA_KSQ_1_VERSION=${AURORA_KSQ_1_VERSION}"
  echo "AURORA_KSQ_1_RESOLUTE_SOURCE_VERSIONS=$(IFS=,; echo "${resolute_versions[*]:--}")"
} > "${WORKDIR}/prepared-source.env"

sha256sum ./* 2>/dev/null | sort > "${WORKDIR}/prepared-source-files.sha256" || true

cat "${WORKDIR}/prepared-source.env"
echo "AURORA_KSQ_1_FETCH_PREP_SUCCESS"

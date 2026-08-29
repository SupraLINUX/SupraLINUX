#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
START="${1:?start order required}"
END="${2:?end order required}"
STATE="${ROOT}/build/ksq-1/full"
CLOSURE="${ROOT}/build/ksq-0/build-order.tsv"
ENV_FILE="${ROOT}/build/ksq-1/environment/build-environment.env"

fail() {
  echo "AURORA_KSQ_1_RANGE_FAILURE: $*" >&2
  exit 1
}

[[ "${START}" =~ ^[0-9]+$ && "${END}" =~ ^[0-9]+$ ]] || fail "range must be numeric"
(( START >= 1 && END <= 101 && START <= END )) || fail "invalid range ${START}-${END}"
[[ -f "${CLOSURE}" ]] || fail "KSQ-0 build order missing"
[[ -f "${ENV_FILE}" ]] || fail "build environment missing"

# shellcheck disable=SC1090
. "${ENV_FILE}"
TARBALL="${AURORA_KSQ_1_BUILD_ENV_TARBALL:?missing chroot tarball}"
[[ -s "${TARBALL}" ]] || fail "chroot tarball not found"

DEBS="${STATE}/debs"
CHUNK_ID="$(printf '%03d-%03d' "${START}" "${END}")"
CHUNK="${STATE}/chunk-${CHUNK_ID}"
WORK="${CHUNK}/work"
RESULTS="${CHUNK}/results"
EVIDENCE="${CHUNK}/evidence"
NEW_DEBS="${CHUNK}/new-debs"
MANIFEST="${EVIDENCE}/build-manifest.tsv"
BINARIES="${EVIDENCE}/binary-packages.tsv"

rm -rf "${CHUNK}"
mkdir -p "${DEBS}" "${WORK}" "${RESULTS}" "${EVIDENCE}" "${NEW_DEBS}"
printf 'order\tsource_package\tpackaging_base\tsupra_version\tcandidate_family\tdecision\tdeb_count\tbuildinfo_count\tchanges_count\tresult\n' > "${MANIFEST}"
printf 'order\tsource_package\tbinary_package\tfilename\tversion\tarchitecture\n' > "${BINARIES}"

mapfile -t rows < <(awk -F '\t' -v start="${START}" -v end="${END}" 'NR > 1 && $1 >= start && $1 <= end' "${CLOSURE}")
expected_count=$((END - START + 1))
[[ "${#rows[@]}" -eq "${expected_count}" ]] || fail "expected ${expected_count} closure rows, got ${#rows[@]}"

normalize_result_filenames() {
  local result_dir="$1"
  local generated directory basename safe_basename
  while IFS= read -r -d '' generated; do
    directory="$(dirname "${generated}")"
    basename="$(basename "${generated}")"
    safe_basename="${basename//:/-}"
    if [[ "${safe_basename}" != "${basename}" ]]; then
      [[ ! -e "${directory}/${safe_basename}" ]] || fail "evidence filename collision ${safe_basename}"
      mv "${generated}" "${directory}/${safe_basename}"
    fi
  done < <(find "${result_dir}" -maxdepth 1 -type f -name '*:*' -print0)
}

write_deb_hashes() {
  (
    cd "${DEBS}"
    find . -maxdepth 1 -type f -name '*.deb' -printf '%f\0' | sort -z | xargs -0 -r sha256sum \
      > "${EVIDENCE}/accumulated-debs.sha256"
  )
  (
    cd "${NEW_DEBS}"
    find . -maxdepth 1 -type f -name '*.deb' -printf '%f\0' | sort -z | xargs -0 -r sha256sum \
      > "${EVIDENCE}/new-debs.sha256"
  )
}

record_failed_build() {
  local order="$1"
  local source="$2"
  local base_version="$3"
  local supra_version="$4"
  local family="$5"
  local decision="$6"
  local result="$7"
  local source_evidence="$8"
  local sbuild_rc="$9"
  local failed_output="${source_evidence}/failed-output"
  local new_deb_count accumulated_deb_count
  local -a failed_debs failed_ddebs failed_buildinfos failed_changes

  mapfile -t failed_debs < <(find "${result}" -maxdepth 1 -type f -name '*.deb' -print | sort)
  mapfile -t failed_ddebs < <(find "${result}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
  mapfile -t failed_buildinfos < <(find "${result}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
  mapfile -t failed_changes < <(find "${result}" -maxdepth 1 -type f -name '*.changes' -print | sort)

  mkdir -p "${failed_output}"
  while IFS= read -r -d '' artifact; do
    cp -a "${artifact}" "${failed_output}/"
  done < <(find "${result}" -maxdepth 1 -type f \
    \( -name '*.build' -o -name '*.buildinfo' -o -name '*.changes' -o -name '*.deb' -o -name '*.ddeb' \) \
    -print0)

  if find "${failed_output}" -maxdepth 1 -type f -print -quit | grep -q .; then
    (
      cd "${source_evidence}"
      find failed-output -maxdepth 1 -type f -printf '%p\0' | sort -z | xargs -0 -r sha256sum \
        > build-artifacts.sha256
    )
  else
    : > "${source_evidence}/build-artifacts.sha256"
  fi

  {
    echo "AURORA_KSQ_1_BUILD_RESULT=FAIL"
    echo "AURORA_KSQ_1_BUILD_ORDER=${order}"
    echo "AURORA_KSQ_1_BUILD_SOURCE=${source}"
    echo "AURORA_KSQ_1_BUILD_VERSION=${supra_version}"
    echo "AURORA_KSQ_1_BUILD_SBUILD_EXIT=${sbuild_rc}"
    echo "AURORA_KSQ_1_BUILD_RESOLVE_ALTERNATIVES=yes"
  } > "${source_evidence}/build-status.env"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\tFAIL\n' \
    "${order}" "${source}" "${base_version}" "${supra_version}" "${family}" "${decision}" \
    "${#failed_debs[@]}" "${#failed_buildinfos[@]}" "${#failed_changes[@]}" >> "${MANIFEST}"

  write_deb_hashes
  new_deb_count="$(find "${NEW_DEBS}" -maxdepth 1 -type f -name '*.deb' | wc -l)"
  accumulated_deb_count="$(find "${DEBS}" -maxdepth 1 -type f -name '*.deb' | wc -l)"
  {
    echo "AURORA_KSQ_1_RANGE_STATUS=FAIL"
    echo "AURORA_KSQ_1_RANGE_FIRST_ORDER=${START}"
    echo "AURORA_KSQ_1_RANGE_REQUESTED_LAST_ORDER=${END}"
    echo "AURORA_KSQ_1_RANGE_LAST_COMPLETED_ORDER=$((order - 1))"
    echo "AURORA_KSQ_1_RANGE_FAILED_ORDER=${order}"
    echo "AURORA_KSQ_1_RANGE_FAILED_SOURCE=${source}"
    echo "AURORA_KSQ_1_RANGE_SBUILD_EXIT=${sbuild_rc}"
    echo "AURORA_KSQ_1_RANGE_NEW_DEBS=${new_deb_count}"
    echo "AURORA_KSQ_1_RANGE_ACCUMULATED_DEBS=${accumulated_deb_count}"
    echo "AURORA_KSQ_1_RANGE_RESOLVE_ALTERNATIVES=yes"
    echo "AURORA_KSQ_1_RANGE_FULL_CERTIFIED=no"
  } > "${EVIDENCE}/range-status.env"

  cat "${MANIFEST}"
  cat "${EVIDENCE}/range-status.env"
  echo "AURORA_KSQ_1_RANGE_BUILD_FAILED order=${order} source=${source} sbuild_exit=${sbuild_rc}" >&2
  return 0
}

declare -A prior_binary_owner=()
if compgen -G "${DEBS}/*.deb" >/dev/null; then
  while IFS= read -r -d '' deb; do
    package="$(dpkg-deb -f "${deb}" Package)"
    [[ -z "${prior_binary_owner[${package}]:-}" ]] || fail "duplicate prior binary package ${package}"
    prior_binary_owner["${package}"]="$(basename "${deb}")"
  done < <(find "${DEBS}" -maxdepth 1 -type f -name '*.deb' -print0 | sort -z)
fi

for row in "${rows[@]}"; do
  IFS=$'\t' read -r order source base_version family decision <<< "${row}"
  (( order >= START && order <= END )) || fail "closure row ${order} escaped range ${START}-${END}"

  source_work="${WORK}/${order}-${source}"
  result="${RESULTS}/${order}-${source}"
  source_evidence="${EVIDENCE}/${order}-${source}"
  mkdir -p "${result}" "${source_evidence}"

  bash "${ROOT}/scripts/ci/fetch-prepare-ksq-1-source.sh" "${source}" "${base_version}" "${source_work}"
  # shellcheck disable=SC1090
  . "${source_work}/prepared-source.env"
  dsc="${AURORA_KSQ_1_PREPARED_DSC}"
  supra_version="${AURORA_KSQ_1_VERSION}"

  cp -a "${source_work}/prepared-source.env" "${source_evidence}/"
  cp -a "${source_work}/prepared-source-files.sha256" "${source_evidence}/" 2>/dev/null || true
  cp -a "${source_work}/source/debian/control" "${source_evidence}/debian-control"
  cp -a "${source_work}/source/debian/changelog" "${source_evidence}/debian-changelog"
  cp -a "${dsc}" "${source_evidence}/"
  while IFS= read -r -d '' prepared_delta; do
    cp -a "${prepared_delta}" "${source_evidence}/"
  done < <(find "${source_work}" -maxdepth 1 -type f -name '*~supra26.04.1*' ! -name '*.dsc' -print0)

  extra_args=()
  if compgen -G "${DEBS}/*.deb" >/dev/null; then
    extra_args+=("--extra-package=${DEBS}")
  fi

  echo "AURORA_KSQ_1_BUILD_START order=${order} source=${source} version=${supra_version}"
  set +e
  DEB_BUILD_OPTIONS="parallel=2" sbuild \
    --chroot-mode=unshare \
    --chroot="${TARBALL}" \
    --dist=resolute \
    --arch=amd64 \
    --build-dir="${result}" \
    --build-path=/build/supralinux-ksq1 \
    --jobs=2 \
    --no-enable-network \
    --no-run-lintian \
    --no-run-autopkgtest \
    --purge-build=always \
    --purge-deps=always \
    --resolve-alternatives \
    --bd-uninstallable-explainer=apt \
    "${extra_args[@]}" \
    "${dsc}"
  sbuild_rc=$?
  set -e

  normalize_result_filenames "${result}"

  if (( sbuild_rc != 0 )); then
    record_failed_build \
      "${order}" "${source}" "${base_version}" "${supra_version}" "${family}" "${decision}" \
      "${result}" "${source_evidence}" "${sbuild_rc}"
    exit "${sbuild_rc}"
  fi

  mapfile -t debs < <(find "${result}" -maxdepth 1 -type f -name '*.deb' -print | sort)
  mapfile -t ddebs < <(find "${result}" -maxdepth 1 -type f -name '*.ddeb' -print | sort)
  mapfile -t buildinfos < <(find "${result}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
  mapfile -t changes < <(find "${result}" -maxdepth 1 -type f -name '*.changes' -print | sort)
  [[ "${#debs[@]}" -gt 0 ]] || fail "${source} produced no DEBs"
  [[ "${#buildinfos[@]}" -gt 0 ]] || fail "${source} produced no buildinfo"
  [[ "${#changes[@]}" -gt 0 ]] || fail "${source} produced no changes"

  for binary in "${debs[@]}" "${ddebs[@]}"; do
    [[ -n "${binary}" ]] || continue
    binary_version="$(dpkg-deb -f "${binary}" Version)"
    [[ "${binary_version}" == "${supra_version}" ]] || {
      fail "$(basename "${binary}") version ${binary_version} != ${supra_version}"
    }
  done

  for deb in "${debs[@]}"; do
    package="$(dpkg-deb -f "${deb}" Package)"
    [[ -z "${prior_binary_owner[${package}]:-}" ]] || {
      fail "binary package ${package} already provided by ${prior_binary_owner[${package}]}"
    }
    target="${DEBS}/$(basename "${deb}")"
    [[ ! -e "${target}" ]] || fail "DEB filename collision $(basename "${deb}")"
    cp -a "${deb}" "${target}"
    cp -a "${deb}" "${NEW_DEBS}/"
    architecture="$(dpkg-deb -f "${deb}" Architecture)"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "${order}" "${source}" "${package}" "$(basename "${deb}")" "${supra_version}" "${architecture}" \
      >> "${BINARIES}"
    prior_binary_owner["${package}"]="$(basename "${deb}")"
  done

  (
    cd "${result}"
    files=()
    for pattern in '*.buildinfo' '*.changes' '*.deb' '*.ddeb' '*.build'; do
      while IFS= read -r file; do
        files+=("${file}")
      done < <(find . -maxdepth 1 -type f -name "${pattern}" -printf '%f\n' | sort)
    done
    ((${#files[@]} > 0)) || exit 1
    sha256sum "${files[@]}" | sort > "${source_evidence}/build-artifacts.sha256"
  )
  cp -a "${buildinfos[@]}" "${changes[@]}" "${source_evidence}/"
  while IFS= read -r -d '' log; do
    cp -a "${log}" "${source_evidence}/"
  done < <(find "${result}" -maxdepth 1 -type f -name '*.build' -print0)
  if ((${#ddebs[@]} > 0)); then
    printf '%s\n' "${ddebs[@]##*/}" > "${source_evidence}/debug-symbol-packages.txt"
  fi

  {
    echo "AURORA_KSQ_1_BUILD_RESULT=PASS"
    echo "AURORA_KSQ_1_BUILD_ORDER=${order}"
    echo "AURORA_KSQ_1_BUILD_SOURCE=${source}"
    echo "AURORA_KSQ_1_BUILD_VERSION=${supra_version}"
    echo "AURORA_KSQ_1_BUILD_RESOLVE_ALTERNATIVES=yes"
  } > "${source_evidence}/build-status.env"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\tPASS\n' \
    "${order}" "${source}" "${base_version}" "${supra_version}" "${family}" "${decision}" \
    "${#debs[@]}" "${#buildinfos[@]}" "${#changes[@]}" >> "${MANIFEST}"

  rm -rf "${source_work}/source"
  rm -f "${result}"/*.deb "${result}"/*.ddeb
  echo "AURORA_KSQ_1_BUILD_SUCCESS order=${order} source=${source} version=${supra_version}"
done

if find "${CHUNK}" -type f -printf '%f\n' | grep -Eq '[":<>|*?]'; then
  find "${CHUNK}" -type f -printf '%p\n' | grep -E '[":<>|*?]' >&2 || true
  fail "chunk contains cross-filesystem-invalid filename characters"
fi

write_deb_hashes

new_deb_count="$(find "${NEW_DEBS}" -maxdepth 1 -type f -name '*.deb' | wc -l)"
accumulated_deb_count="$(find "${DEBS}" -maxdepth 1 -type f -name '*.deb' | wc -l)"
{
  echo "AURORA_KSQ_1_RANGE_STATUS=PASS"
  echo "AURORA_KSQ_1_RANGE_FIRST_ORDER=${START}"
  echo "AURORA_KSQ_1_RANGE_LAST_ORDER=${END}"
  echo "AURORA_KSQ_1_RANGE_SOURCES=${expected_count}"
  echo "AURORA_KSQ_1_RANGE_NEW_DEBS=${new_deb_count}"
  echo "AURORA_KSQ_1_RANGE_ACCUMULATED_DEBS=${accumulated_deb_count}"
  echo "AURORA_KSQ_1_RANGE_RESOLVE_ALTERNATIVES=yes"
  echo "AURORA_KSQ_1_RANGE_FULL_CERTIFIED=no"
} > "${EVIDENCE}/range-status.env"

cat "${MANIFEST}"
cat "${EVIDENCE}/range-status.env"
echo "AURORA_KSQ_1_RANGE_SUCCESS ${CHUNK_ID}"

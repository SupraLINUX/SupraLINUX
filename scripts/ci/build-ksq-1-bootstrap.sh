#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLOSURE="${ROOT}/build/ksq-0/build-order.tsv"
ENV_FILE="${ROOT}/build/ksq-1/environment/build-environment.env"
OUT="${ROOT}/build/ksq-1/bootstrap"
COUNT="${AURORA_KSQ_1_BOOTSTRAP_COUNT:-4}"

[[ -f "${CLOSURE}" ]] || { echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: KSQ-0 build order missing" >&2; exit 1; }
[[ -f "${ENV_FILE}" ]] || { echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: build environment missing" >&2; exit 1; }
# shellcheck disable=SC1090
. "${ENV_FILE}"
TARBALL="${AURORA_KSQ_1_BUILD_ENV_TARBALL:?missing chroot tarball}"
[[ -s "${TARBALL}" ]] || { echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: chroot tarball not found" >&2; exit 1; }

rm -rf "${OUT}"
mkdir -p "${OUT}/work" "${OUT}/results" "${OUT}/debs"
MANIFEST="${OUT}/build-manifest.tsv"
printf 'order\tsource_package\tpackaging_base\tsupra_version\tdeb_count\tbuildinfo_count\tchanges_count\tresult\n' > "${MANIFEST}"

mapfile -t bootstrap_rows < <(tail -n +2 "${CLOSURE}" | head -n "${COUNT}")
[[ "${#bootstrap_rows[@]}" -eq "${COUNT}" ]] || {
  echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: requested ${COUNT} rows but closure supplied ${#bootstrap_rows[@]}" >&2
  exit 1
}

# The bootstrap scope is intentionally pinned to the first dependency-independent
# foundation nodes. A changed KSQ-0 DAG must be reviewed rather than silently
# changing this proof's meaning.
expected=(
  '1:kf6-extra-cmake-modules:6.29.0-0ubuntu1'
  '2:plasma-wayland-protocols:1.21.0-1'
  '3:qtkeychain:0.17.0-1'
  '4:wayland-protocols:1.48-1'
)

for index in "${!bootstrap_rows[@]}"; do
  IFS=$'\t' read -r order source base_version family decision <<< "${bootstrap_rows[$index]}"
  actual="${order}:${source}:${base_version}"
  [[ "${actual}" == "${expected[$index]}" ]] || {
    echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: bootstrap DAG drift at row $((index + 1)): expected ${expected[$index]}, got ${actual}" >&2
    exit 1
  }

  work="${OUT}/work/${order}-${source}"
  result="${OUT}/results/${order}-${source}"
  mkdir -p "${result}"

  bash "${ROOT}/scripts/ci/fetch-prepare-ksq-1-source.sh" "${source}" "${base_version}" "${work}"
  # shellcheck disable=SC1090
  . "${work}/prepared-source.env"
  dsc="${AURORA_KSQ_1_PREPARED_DSC}"
  supra_version="${AURORA_KSQ_1_VERSION}"

  extra_args=()
  if compgen -G "${OUT}/debs/*.deb" >/dev/null; then
    extra_args+=("--extra-package=${OUT}/debs")
  fi

  echo "AURORA_KSQ_1_BUILD_START order=${order} source=${source} version=${supra_version}"
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
    "${extra_args[@]}" \
    "${dsc}"

  # sbuild names its human-readable .build log with an ISO timestamp containing
  # colons. GitHub artifact storage rejects ':' for cross-filesystem portability.
  # The log content is evidence; only its filename is normalized before upload.
  sanitized=0
  while IFS= read -r -d '' generated; do
    directory="$(dirname "${generated}")"
    basename="$(basename "${generated}")"
    safe_basename="${basename//:/-}"
    if [[ "${safe_basename}" != "${basename}" ]]; then
      [[ ! -e "${directory}/${safe_basename}" ]] || {
        echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: evidence filename collision for ${safe_basename}" >&2
        exit 1
      }
      mv "${generated}" "${directory}/${safe_basename}"
      sanitized=$((sanitized + 1))
    fi
  done < <(find "${result}" -maxdepth 1 -type f -name '*:*' -print0)
  echo "AURORA_KSQ_1_EVIDENCE_FILENAMES_SANITIZED=${sanitized} source=${source}"

  mapfile -t debs < <(find "${result}" -maxdepth 1 -type f -name '*.deb' -print | sort)
  mapfile -t buildinfos < <(find "${result}" -maxdepth 1 -type f -name '*.buildinfo' -print | sort)
  mapfile -t changes < <(find "${result}" -maxdepth 1 -type f -name '*.changes' -print | sort)
  [[ "${#debs[@]}" -gt 0 ]] || { echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: ${source} produced no debs" >&2; exit 1; }
  [[ "${#buildinfos[@]}" -gt 0 ]] || { echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: ${source} produced no buildinfo" >&2; exit 1; }
  [[ "${#changes[@]}" -gt 0 ]] || { echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: ${source} produced no changes file" >&2; exit 1; }

  for deb in "${debs[@]}"; do
    binary_version="$(dpkg-deb -f "${deb}" Version)"
    [[ "${binary_version}" == "${supra_version}" ]] || {
      echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: $(basename "${deb}") version ${binary_version} != ${supra_version}" >&2
      exit 1
    }
    cp -a "${deb}" "${OUT}/debs/"
  done

  sha256sum "${dsc}" "${buildinfos[@]}" "${changes[@]}" "${debs[@]}" \
    | sort > "${result}/artifacts.sha256"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\tPASS\n' \
    "${order}" "${source}" "${base_version}" "${supra_version}" \
    "${#debs[@]}" "${#buildinfos[@]}" "${#changes[@]}" >> "${MANIFEST}"
  echo "AURORA_KSQ_1_BUILD_SUCCESS order=${order} source=${source} version=${supra_version}"
done

if find "${OUT}" -type f -printf '%f\n' | grep -Eq '[":<>|*?]'; then
  echo "AURORA_KSQ_1_BOOTSTRAP_FAILURE: artifact evidence still contains cross-filesystem-invalid filename characters" >&2
  find "${OUT}" -type f -printf '%p\n' | grep -E '[":<>|*?]' >&2 || true
  exit 1
fi

find "${OUT}/debs" -maxdepth 1 -type f -name '*.deb' -print0 | sort -z | xargs -0 sha256sum > "${OUT}/bootstrap-debs.sha256"
{
  echo "AURORA_KSQ_1_BOOTSTRAP_STATUS=PASS"
  echo "AURORA_KSQ_1_BOOTSTRAP_SOURCES=${COUNT}"
  echo "AURORA_KSQ_1_BOOTSTRAP_FIRST_ORDER=1"
  echo "AURORA_KSQ_1_BOOTSTRAP_LAST_ORDER=${COUNT}"
  echo "AURORA_KSQ_1_BOOTSTRAP_FULL_KSQ_1_CERTIFIED=no"
} > "${OUT}/bootstrap-status.env"

cat "${MANIFEST}"
cat "${OUT}/bootstrap-status.env"
echo "AURORA_KSQ_1_BOOTSTRAP_SUCCESS"

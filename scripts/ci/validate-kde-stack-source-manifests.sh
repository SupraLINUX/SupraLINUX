#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
META="${ROOT_DIR}/tests/kde-stack/release-sets.tsv"

fail() {
  echo "AURORA_KSQ_0_MANIFEST_FAILURE: $*" >&2
  exit 1
}

[[ -f "${META}" ]] || fail "missing release-set metadata: ${META}"
[[ "$(head -n1 "${META}")" == $'set\tversion\texpected_modules\tinfo_url\tdownload_base\trelease_signing_fingerprint' ]] || fail "invalid release-sets.tsv header"

validate_set() {
  local set_name="$1" manifest="$2"
  local row version expected info_url download_base fingerprint actual

  row="$(awk -F '\t' -v s="${set_name}" 'NR > 1 && $1 == s { print; exit }' "${META}")"
  [[ -n "${row}" ]] || fail "release metadata missing for ${set_name}"
  IFS=$'\t' read -r _ version expected info_url download_base fingerprint <<<"${row}"

  [[ -f "${manifest}" ]] || fail "missing manifest for ${set_name}: ${manifest}"
  [[ "$(head -n1 "${manifest}")" == $'module\tversion\tsha256' ]] || fail "invalid header in ${manifest}"

  actual="$(( $(wc -l <"${manifest}") - 1 ))"
  [[ "${actual}" -eq "${expected}" ]] || fail "${set_name}: expected ${expected} modules, found ${actual}"

  awk -F '\t' -v expected_version="${version}" '
    NR == 1 { next }
    NF != 3 { printf "bad field count at line %d\n", NR > "/dev/stderr"; exit 10 }
    $1 !~ /^[a-z0-9][a-z0-9+._-]*$/ { printf "bad module at line %d: %s\n", NR, $1 > "/dev/stderr"; exit 11 }
    $2 != expected_version { printf "wrong version at line %d: %s\n", NR, $2 > "/dev/stderr"; exit 12 }
    length($3) != 64 || $3 ~ /[^0-9a-f]/ { printf "bad sha256 at line %d: %s\n", NR, $3 > "/dev/stderr"; exit 13 }
  ' "${manifest}" || fail "${set_name}: malformed manifest row"

  if tail -n +2 "${manifest}" | cut -f1 | LC_ALL=C sort | uniq -d | grep -q .; then
    tail -n +2 "${manifest}" | cut -f1 | LC_ALL=C sort | uniq -d >&2
    fail "${set_name}: duplicate module names"
  fi

  if ! diff -u <(tail -n +2 "${manifest}" | cut -f1) <(tail -n +2 "${manifest}" | cut -f1 | LC_ALL=C sort) >/dev/null; then
    fail "${set_name}: modules are not in deterministic bytewise sort order"
  fi

  [[ "${fingerprint}" =~ ^[0-9A-F]{40}$ ]] || fail "${set_name}: malformed release-signing fingerprint"
  [[ "${info_url}" == https://kde.org/info/* ]] || fail "${set_name}: non-KDE info URL"
  [[ "${download_base}" == https://download.kde.org/stable/* ]] || fail "${set_name}: non-KDE download base"

  while IFS=$'\t' read -r module row_version sha256; do
    [[ "${module}" == "module" ]] && continue
    printf '%s\t%s\t%s\t%s/%s-%s.tar.xz\t%s/%s-%s.tar.xz.sig\n' \
      "${set_name}" "${module}" "${sha256}" \
      "${download_base}" "${module}" "${row_version}" \
      "${download_base}" "${module}" "${row_version}"
  done <"${manifest}"
}

mkdir -p "${ROOT_DIR}/build/ksq-0"
{
  printf 'set\tmodule\tsha256\tsource_url\tsignature_url\n'
  validate_set plasma "${ROOT_DIR}/tests/kde-stack/plasma-6.7.4-sources.tsv"
  validate_set frameworks "${ROOT_DIR}/tests/kde-stack/frameworks-6.29.0-sources.tsv"
} >"${ROOT_DIR}/build/ksq-0/validated-source-urls.tsv"

printf 'AURORA_KSQ_0_PLASMA_SOURCES=75\n'
printf 'AURORA_KSQ_0_FRAMEWORKS_SOURCES=74\n'
printf 'AURORA_KSQ_0_MANIFEST_SUCCESS\n'

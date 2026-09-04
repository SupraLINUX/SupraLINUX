#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEB_ARTIFACT="${1:?DEB artifact directory required}"
EVIDENCE="${2:?range evidence directory required}"
FIRST="${3:?first order required}"
LAST="${4:?last order required}"
BASE_COUNT="${5:?base accumulated DEB count required}"
TARGET="${ROOT}/build/ksq-1/full/debs"

fail() {
    echo "AURORA_KSQ_1_WITNESS_STAGE_FAILURE: $*" >&2
    exit 1
}

[[ "${FIRST}" =~ ^[0-9]+$ && "${LAST}" =~ ^[0-9]+$ && "${BASE_COUNT}" =~ ^[0-9]+$ ]] || fail "numeric argument invalid"
[[ -d "${DEB_ARTIFACT}" ]] || fail "DEB artifact directory missing"
[[ -f "${EVIDENCE}/range-status.env" ]] || fail "range-status.env missing"
[[ -f "${EVIDENCE}/new-debs.sha256" ]] || fail "new-debs.sha256 missing"

grep -qx 'AURORA_KSQ_1_RANGE_STATUS=PASS' "${EVIDENCE}/range-status.env" || fail "prior range not PASS"
grep -qx "AURORA_KSQ_1_RANGE_FIRST_ORDER=${FIRST}" "${EVIDENCE}/range-status.env" || fail "prior first order drifted"
grep -qx "AURORA_KSQ_1_RANGE_LAST_ORDER=${LAST}" "${EVIDENCE}/range-status.env" || fail "prior last order drifted"
expected_sources=$((LAST - FIRST + 1))
grep -qx "AURORA_KSQ_1_RANGE_SOURCES=${expected_sources}" "${EVIDENCE}/range-status.env" || fail "prior source count drifted"

new_count="$(sed -n 's/^AURORA_KSQ_1_RANGE_NEW_DEBS=//p' "${EVIDENCE}/range-status.env")"
accumulated="$(sed -n 's/^AURORA_KSQ_1_RANGE_ACCUMULATED_DEBS=//p' "${EVIDENCE}/range-status.env")"
[[ "${new_count}" =~ ^[0-9]+$ && "${new_count}" -gt 0 ]] || fail "invalid prior new DEB count"
[[ "${accumulated}" =~ ^[0-9]+$ ]] || fail "invalid prior accumulated DEB count"
[[ "${accumulated}" -eq $((BASE_COUNT + new_count)) ]] || fail "prior accumulated DEB arithmetic mismatch"
actual_new="$(find "${DEB_ARTIFACT}" -maxdepth 1 -type f -name '*.deb' | wc -l)"
[[ "${actual_new}" -eq "${new_count}" ]] || fail "prior DEB artifact count ${actual_new} != ${new_count}"

(
    cd "${DEB_ARTIFACT}"
    sha256sum -c "${EVIDENCE}/new-debs.sha256"
) || fail "prior range DEB hashes failed"

mkdir -p "${TARGET}"
current="$(find "${TARGET}" -maxdepth 1 -type f -name '*.deb' | wc -l)"
[[ "${current}" -eq "${BASE_COUNT}" ]] || fail "target base count ${current} != ${BASE_COUNT}"

declare -A package_owner=()
while IFS= read -r -d '' deb; do
    pkg="$(dpkg-deb -f "${deb}" Package)"
    [[ -n "${pkg}" ]] || fail "empty Package field in ${deb}"
    [[ -z "${package_owner[${pkg}]:-}" ]] || fail "duplicate existing package ${pkg}"
    package_owner["${pkg}"]="$(basename "${deb}")"
done < <(find "${TARGET}" -maxdepth 1 -type f -name '*.deb' -print0 | sort -z)

while IFS= read -r -d '' deb; do
    pkg="$(dpkg-deb -f "${deb}" Package)"
    [[ -n "${pkg}" ]] || fail "empty Package field in prior witness ${deb}"
    [[ -z "${package_owner[${pkg}]:-}" ]] || fail "package collision ${pkg} with ${package_owner[${pkg}]}"
    target="${TARGET}/$(basename "${deb}")"
    [[ ! -e "${target}" ]] || fail "filename collision $(basename "${deb}")"
    cp -a "${deb}" "${target}"
    package_owner["${pkg}"]="$(basename "${deb}")"
done < <(find "${DEB_ARTIFACT}" -maxdepth 1 -type f -name '*.deb' -print0 | sort -z)

final="$(find "${TARGET}" -maxdepth 1 -type f -name '*.deb' | wc -l)"
[[ "${final}" -eq "${accumulated}" ]] || fail "staged accumulated count ${final} != ${accumulated}"

echo "AURORA_KSQ_1_WITNESS_STAGE_STATUS=PASS"
echo "AURORA_KSQ_1_WITNESS_STAGE_FIRST_ORDER=${FIRST}"
echo "AURORA_KSQ_1_WITNESS_STAGE_LAST_ORDER=${LAST}"
echo "AURORA_KSQ_1_WITNESS_STAGE_NEW_DEBS=${new_count}"
echo "AURORA_KSQ_1_WITNESS_STAGE_ACCUMULATED_DEBS=${final}"
echo AURORA_KSQ_1_WITNESS_STAGE_SUCCESS

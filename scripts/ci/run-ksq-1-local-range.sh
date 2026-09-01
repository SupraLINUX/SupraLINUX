#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
START="${1:?start order required}"
END="${2:?end order required}"
SNAPSHOT="20260829T022000Z"
SLICE_ROOT="${AURORA_KSQ_LOCAL_SLICE_ROOT:-/opt/supralinux/archive/${SNAPSHOT}}"

[[ "$(id -u)" -eq 0 ]] || { echo "AURORA_KSQ_1_LOCAL_RANGE_FAILURE: must run as root in builder" >&2; exit 1; }
[[ "${START}" =~ ^[0-9]+$ && "${END}" =~ ^[0-9]+$ ]] || { echo "AURORA_KSQ_1_LOCAL_RANGE_FAILURE: numeric range required" >&2; exit 1; }
(( START >= 1 && END <= 101 && START <= END )) || { echo "AURORA_KSQ_1_LOCAL_RANGE_FAILURE: invalid range" >&2; exit 1; }

AURORA_KSQ_LOCAL_SLICE_ROOT="${SLICE_ROOT}" bash "${ROOT}/scripts/ci/prepare-ksq-1-local-runner.sh"
ENV_FILE="${ROOT}/build/ksq-1/environment/build-environment.env"
[[ -f "${ENV_FILE}" ]] || { echo "AURORA_KSQ_1_LOCAL_RANGE_FAILURE: build environment missing" >&2; exit 1; }
# shellcheck disable=SC1090
. "${ENV_FILE}"
[[ -n "${AURORA_KSQ_1_SBUILD_CONFIG:-}" && -f "${AURORA_KSQ_1_SBUILD_CONFIG}" ]] || {
  echo "AURORA_KSQ_1_LOCAL_RANGE_FAILURE: local sbuild config missing" >&2
  exit 1
}

chmod -R a+rX,a+w "${ROOT}/build"

cmd="cd '${ROOT}' && export AURORA_KSQ_LOCAL_SLICE_ROOT='${SLICE_ROOT}' SBUILD_CONFIG='${AURORA_KSQ_1_SBUILD_CONFIG}' && bash scripts/ci/build-ksq-1-range.sh '${START}' '${END}'"
su -s /bin/bash ubuntu -c "${cmd}"

status="${ROOT}/build/ksq-1/full/chunk-$(printf '%03d-%03d' "${START}" "${END}")/evidence/range-status.env"
[[ -f "${status}" ]] || { echo "AURORA_KSQ_1_LOCAL_RANGE_FAILURE: range status missing" >&2; exit 1; }
grep -qx 'AURORA_KSQ_1_RANGE_STATUS=PASS' "${status}" || {
  cat "${status}" >&2
  echo "AURORA_KSQ_1_LOCAL_RANGE_FAILURE: range did not PASS" >&2
  exit 1
}

printf 'AURORA_KSQ_1_LOCAL_RANGE_START=%s\n' "${START}"
printf 'AURORA_KSQ_1_LOCAL_RANGE_END=%s\n' "${END}"
printf 'AURORA_KSQ_1_LOCAL_RANGE_SUCCESS\n'

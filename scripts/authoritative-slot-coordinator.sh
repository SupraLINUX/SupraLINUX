#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-}"
shift || true

SLOTS="${SUPRALINUX_AUTHORITATIVE_SLOTS:-1}"
LOCK_ROOT="${SUPRALINUX_AUTHORITATIVE_LOCK_ROOT:-/var/lib/supralinux/kvm-jit/.locks}"
REPOSITORY="${SUPRALINUX_REPOSITORY:-SupraLINUX/SupraLINUX}"

if [[ "${MODE}" != "worker" && "${MODE}" != "maintenance" ]]; then
    printf 'Usage: %s {worker|maintenance} -- command [args...]\n' "$0" >&2
    exit 64
fi
if [[ "${1:-}" != "--" ]]; then
    printf 'Expected -- before command.\n' >&2
    exit 64
fi
shift
if (( $# == 0 )); then
    printf 'Missing command.\n' >&2
    exit 64
fi
if [[ ! "${SLOTS}" =~ ^[1-9][0-9]*$ ]] || (( SLOTS > 8 )); then
    printf 'SUPRALINUX_AUTHORITATIVE_SLOTS must be an integer from 1 through 8.\n' >&2
    exit 64
fi

SAFE_REPOSITORY="${REPOSITORY//[^a-zA-Z0-9._-]/-}"
mkdir -p "${LOCK_ROOT}"

MAINTENANCE_LOCK="${LOCK_ROOT}/${SAFE_REPOSITORY}-maintenance.lock"
exec {maintenance_fd}>"${MAINTENANCE_LOCK}"

if [[ "${MODE}" == "maintenance" ]]; then
    if ! flock -n -x "${maintenance_fd}"; then
        printf 'Authoritative maintenance is blocked by active workers: %s\n' "${MAINTENANCE_LOCK}" >&2
        exit 75
    fi
    export SUPRALINUX_AUTHORITATIVE_LOCK_MODE=maintenance
    export SUPRALINUX_AUTHORITATIVE_SLOT=maintenance
    "$@"
    exit $?
fi

if ! flock -n -s "${maintenance_fd}"; then
    printf 'Authoritative worker is blocked by active maintenance: %s\n' "${MAINTENANCE_LOCK}" >&2
    exit 75
fi

selected_slot=""
selected_lock=""
selected_fd=""
for ((slot=1; slot<=SLOTS; slot++)); do
    candidate_lock="${LOCK_ROOT}/${SAFE_REPOSITORY}-authoritative-slot-${slot}.lock"
    exec {candidate_fd}>"${candidate_lock}"
    if flock -n -x "${candidate_fd}"; then
        selected_slot="${slot}"
        selected_lock="${candidate_lock}"
        selected_fd="${candidate_fd}"
        break
    fi
    exec {candidate_fd}>&-
done

if [[ -z "${selected_slot}" ]]; then
    printf 'No authoritative execution slot is available (slots=%s).\n' "${SLOTS}" >&2
    exit 75
fi

export SUPRALINUX_AUTHORITATIVE_LOCK_MODE=worker
export SUPRALINUX_AUTHORITATIVE_SLOT="${selected_slot}"
export SUPRALINUX_AUTHORITATIVE_SLOT_LOCK="${selected_lock}"
"$@"

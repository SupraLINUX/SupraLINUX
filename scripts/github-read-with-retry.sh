#!/usr/bin/env bash
# Read-only API transport. Mutations and JIT creation must remain single-shot.
set -Eeuo pipefail
RETRY_DELAY="${SUPRALINUX_API_RETRY_DELAY_SECONDS:-5}"
[[ "${RETRY_DELAY}" =~ ^[0-9]+$ ]] || exit 2
BODY="$(mktemp)"
trap 'rm -f "${BODY}"' EXIT
for attempt in {1..8}; do
    rc=0
    status="$(curl --fail-with-body --silent --show-error --location \
        --connect-timeout 10 --max-time 30 --output "${BODY}" --write-out '%{http_code}' "$@")" || rc=$?
    if (( rc == 0 )); then cat "${BODY}"; exit 0; fi
    retry=false
    case "${rc}" in
        5|6|7|28|35|52|55|56) retry=true ;;
        22) case "${status}" in 408|429|500|502|503|504) retry=true ;; esac ;;
    esac
    if [[ "${retry}" != true ]] || (( attempt == 8 )); then
        cat "${BODY}" >&2
        exit "${rc}"
    fi
    printf 'Transient GitHub read failure (curl=%s HTTP=%s); retry %s/8.\n' "${rc}" "${status}" "$((attempt + 1))" >&2
    sleep "${RETRY_DELAY}"
    if (( RETRY_DELAY > 0 && RETRY_DELAY < 30 )); then RETRY_DELAY=$((RETRY_DELAY * 2)); fi
    if (( RETRY_DELAY > 30 )); then RETRY_DELAY=30; fi
done

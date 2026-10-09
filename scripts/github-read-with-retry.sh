#!/usr/bin/env bash
# Read-only API transport. Mutations and JIT creation must remain single-shot.
set -Eeuo pipefail
RETRY_DELAY="${SUPRALINUX_API_RETRY_DELAY_SECONDS:-5}"
[[ "${RETRY_DELAY}" =~ ^[0-9]+$ ]] || exit 2
# Artifact bodies need time to cross the bounded guest network. Keep short API
# reads short and cap artifact retries separately; never emit a partial body.
MAX_TIME=30
MAX_ATTEMPTS=8
for argument in "$@"; do
    if [[ "${argument}" =~ ^https://api\.github\.com/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/artifacts/[0-9]+/zip$ ]]; then
        MAX_TIME=900
        MAX_ATTEMPTS=3
    fi
done
BODY="$(mktemp)"
trap 'rm -f "${BODY}"' EXIT
for ((attempt = 1; attempt <= MAX_ATTEMPTS; attempt++)); do
    rc=0
    status="$(curl --fail-with-body --silent --show-error --location \
        --connect-timeout 10 --max-time "${MAX_TIME}" --speed-limit 1024 --speed-time 60 \
        --output "${BODY}" --write-out '%{http_code}' "$@")" || rc=$?
    if (( rc == 0 )); then cat "${BODY}"; exit 0; fi
    retry=false
    case "${rc}" in
        5|6|7|28|35|52|55|56) retry=true ;;
        22) case "${status}" in 408|429|500|502|503|504) retry=true ;; esac ;;
    esac
    if [[ "${retry}" != true ]] || (( attempt == MAX_ATTEMPTS )); then
        printf 'GitHub read failed (curl=%s HTTP=%s attempts=%s); response body withheld.\n' "${rc}" "${status}" "${attempt}" >&2
        exit "${rc}"
    fi
    printf 'Transient GitHub read failure (curl=%s HTTP=%s); retry %s/%s.\n' "${rc}" "${status}" "$((attempt + 1))" "${MAX_ATTEMPTS}" >&2
    sleep "${RETRY_DELAY}"
    if (( RETRY_DELAY > 0 && RETRY_DELAY < 30 )); then RETRY_DELAY=$((RETRY_DELAY * 2)); fi
    if (( RETRY_DELAY > 30 )); then RETRY_DELAY=30; fi
done

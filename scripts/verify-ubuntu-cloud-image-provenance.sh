#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${1:-/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img}"
PROVENANCE="${2:-${IMAGE}.provenance.txt}"

for command_name in awk grep sha256sum; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

if [[ ! -f "${IMAGE}" || ! -r "${IMAGE}" ]]; then
    printf 'Ubuntu source image is missing or unreadable: %s\n' "${IMAGE}" >&2
    exit 1
fi
if [[ ! -f "${PROVENANCE}" || ! -r "${PROVENANCE}" ]]; then
    printf 'Ubuntu source-image provenance is missing or unreadable: %s\n' "${PROVENANCE}" >&2
    exit 1
fi

for required_line in \
    'release=resolute' \
    'architecture=amd64' \
    'signature=verified-with-gpgv'; do
    if ! grep -Fqx "${required_line}" "${PROVENANCE}"; then
        printf 'Required provenance field is missing or invalid: %s\n' "${required_line}" >&2
        exit 1
    fi
done

mapfile -t PROVENANCE_HASHES < <(awk -F= '$1 == "sha256" {print $2}' "${PROVENANCE}")
if (( ${#PROVENANCE_HASHES[@]} != 1 )); then
    printf 'Expected exactly one sha256 field in provenance; found %d.\n' "${#PROVENANCE_HASHES[@]}" >&2
    exit 1
fi
EXPECTED_SHA256="${PROVENANCE_HASHES[0]}"
if [[ ! "${EXPECTED_SHA256}" =~ ^[0-9a-fA-F]{64}$ ]]; then
    printf 'Invalid provenance SHA-256: %s\n' "${EXPECTED_SHA256}" >&2
    exit 1
fi

ACTUAL_SHA256="$(sha256sum "${IMAGE}" | awk '{print $1}')"
if [[ "${ACTUAL_SHA256,,}" != "${EXPECTED_SHA256,,}" ]]; then
    printf 'Ubuntu source-image SHA-256 mismatch.\n' >&2
    printf 'Expected: %s\n' "${EXPECTED_SHA256}" >&2
    printf 'Actual:   %s\n' "${ACTUAL_SHA256}" >&2
    exit 1
fi

printf 'Ubuntu source-image provenance verification: PASS\n'
printf 'image=%s\n' "${IMAGE}"
printf 'sha256=%s\n' "${ACTUAL_SHA256,,}"

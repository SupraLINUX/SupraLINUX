#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${1:-${SUPRALINUX_GOLDEN_IMAGE:-/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2}}"
PROVENANCE="${SUPRALINUX_GOLDEN_PROVENANCE:-${IMAGE}.provenance.txt}"
EVIDENCE_OUT="${2:-${SUPRALINUX_GOLDEN_PROVENANCE_EVIDENCE:-}}"

for command_name in awk git sha256sum; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

if [[ ! -f "${IMAGE}" || ! -r "${IMAGE}" ]]; then
    printf 'Golden image is missing or unreadable: %s\n' "${IMAGE}" >&2
    exit 1
fi
if [[ ! -f "${PROVENANCE}" || ! -r "${PROVENANCE}" ]]; then
    printf 'Golden image provenance is missing or unreadable: %s\n' "${PROVENANCE}" >&2
    exit 1
fi

read_exact_field() {
    local key="$1"
    local description="$2"
    local -a values=()
    mapfile -t values < <(awk -F= -v key="${key}" '$1 == key {print $2}' "${PROVENANCE}")
    if (( ${#values[@]} != 1 )); then
        printf 'Expected exactly one %s field (%s) in golden provenance; found %d.\n' \
            "${key}" "${description}" "${#values[@]}" >&2
        exit 1
    fi
    printf '%s' "${values[0]}"
}

EXPECTED_GOLDEN_SHA256="$(read_exact_field golden_image_sha256 'published golden image hash')"
SOURCE_IMAGE_SHA256="$(read_exact_field source_image_sha256 'verified Ubuntu source image hash')"
SOURCE_COMMIT="$(read_exact_field source_commit 'SupraLINUX source commit used to build the golden image')"
SOURCE_CLEANUP="$(read_exact_field source_checkout_removed 'temporary source checkout cleanup marker')"
SOURCE_VERIFIED="$(read_exact_field source_image_provenance_verified 'signed source-image re-verification marker')"
FINGERPRINT_SCHEMA="$(read_exact_field golden_input_fingerprint_schema 'golden input fingerprint schema')"
RECORDED_INPUT_DIGEST="$(read_exact_field golden_input_digest 'golden input compatibility digest')"

[[ "${EXPECTED_GOLDEN_SHA256}" =~ ^[0-9a-fA-F]{64}$ ]] || { printf 'Invalid golden_image_sha256 in provenance: %s\n' "${EXPECTED_GOLDEN_SHA256}" >&2; exit 1; }
[[ "${SOURCE_IMAGE_SHA256}" =~ ^[0-9a-fA-F]{64}$ ]] || { printf 'Invalid source_image_sha256 in provenance: %s\n' "${SOURCE_IMAGE_SHA256}" >&2; exit 1; }
[[ "${SOURCE_COMMIT}" =~ ^[0-9a-fA-F]{40}$ ]] || { printf 'Invalid source_commit in golden provenance: %s\n' "${SOURCE_COMMIT}" >&2; exit 1; }
[[ "${SOURCE_CLEANUP}" == "yes" ]] || { printf 'Golden provenance does not prove removal of the temporary source checkout.\n' >&2; exit 1; }
[[ "${SOURCE_VERIFIED}" == "yes" ]] || { printf 'Golden provenance does not prove signed Ubuntu source-image re-verification before build.\n' >&2; exit 1; }
[[ "${FINGERPRINT_SCHEMA}" == "1" ]] || { printf 'Unsupported golden input fingerprint schema: %s\n' "${FINGERPRINT_SCHEMA}" >&2; exit 1; }
[[ "${RECORDED_INPUT_DIGEST}" =~ ^[0-9a-fA-F]{64}$ ]] || { printf 'Invalid golden_input_digest in provenance: %s\n' "${RECORDED_INPUT_DIGEST}" >&2; exit 1; }

ACTUAL_GOLDEN_SHA256="$(sha256sum "${IMAGE}" | awk '{print $1}')"
if [[ "${ACTUAL_GOLDEN_SHA256,,}" != "${EXPECTED_GOLDEN_SHA256,,}" ]]; then
    printf 'Golden image SHA-256 does not match its provenance.\nExpected: %s\nActual:   %s\n' "${EXPECTED_GOLDEN_SHA256}" "${ACTUAL_GOLDEN_SHA256}" >&2
    exit 1
fi

COMPAT_COMMIT="${SUPRALINUX_GOLDEN_COMPAT_COMMIT:-HEAD}"
RESOLVED_COMPAT_COMMIT="$(git -C "${ROOT}" rev-parse --verify "${COMPAT_COMMIT}^{commit}")" || {
    printf 'Could not resolve golden compatibility commit: %s\n' "${COMPAT_COMMIT}" >&2
    exit 1
}
CURRENT_INPUT_DIGEST="$("${ROOT}/scripts/golden-image-input-digest.sh" "${RESOLVED_COMPAT_COMMIT}")"
if [[ "${CURRENT_INPUT_DIGEST,,}" != "${RECORDED_INPUT_DIGEST,,}" ]]; then
    printf 'Golden image inputs differ from the checkout being certified.\n' >&2
    printf 'Golden source_commit:   %s\nCompatibility commit:   %s\nRecorded golden digest: %s\nCurrent input digest:    %s\n' \
        "${SOURCE_COMMIT}" "${RESOLVED_COMPAT_COMMIT}" "${RECORDED_INPUT_DIGEST}" "${CURRENT_INPUT_DIGEST}" >&2
    printf 'Rebuild the golden image because a golden-relevant input changed.\n' >&2
    exit 1
fi

if [[ -n "${EVIDENCE_OUT}" ]]; then
    mkdir -p "$(dirname "${EVIDENCE_OUT}")"
    {
        printf 'checked_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf 'golden_image=%s\n' "${IMAGE}"
        printf 'golden_image_sha256=%s\n' "${ACTUAL_GOLDEN_SHA256,,}"
        printf 'source_image_sha256=%s\n' "${SOURCE_IMAGE_SHA256,,}"
        printf 'source_commit=%s\n' "${SOURCE_COMMIT,,}"
        printf 'source_checkout_removed=yes\n'
        printf 'source_image_provenance_verified=yes\n'
        printf 'golden_input_fingerprint_schema=1\n'
        printf 'golden_input_digest=%s\n' "${RECORDED_INPUT_DIGEST,,}"
        printf 'compatibility_commit=%s\n' "${RESOLVED_COMPAT_COMMIT,,}"
        printf 'golden_input_compatibility=PASS\n'
        printf 'golden_provenance_verification=PASS\n'
    } > "${EVIDENCE_OUT}"
fi

printf 'Golden image provenance verification: PASS\n'
printf 'golden_image_sha256=%s\n' "${ACTUAL_GOLDEN_SHA256,,}"
printf 'source_commit=%s\n' "${SOURCE_COMMIT,,}"
printf 'golden_input_digest=%s\n' "${RECORDED_INPUT_DIGEST,,}"
printf 'compatibility_commit=%s\n' "${RESOLVED_COMPAT_COMMIT,,}"

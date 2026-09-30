#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMIT="${1:-HEAD}"
MODE="${2:-digest}"
FINGERPRINT_SCHEMA=1

INPUTS=(
    scripts/build-authoritative-runner-image.sh
    scripts/provision-authoritative-runner-guest.sh
    scripts/install-actions-runner.sh
    scripts/prepare-autopkgtest-qemu-image.sh
    scripts/seal-authoritative-runner-image.sh
    scripts/verify-ubuntu-cloud-image-provenance.sh
)

if [[ "${MODE}" != "digest" && "${MODE}" != "--manifest" ]]; then
    printf 'Usage: %s [commit] [--manifest]\n' "$0" >&2
    exit 2
fi

RESOLVED_COMMIT="$(git -C "${ROOT}" rev-parse --verify "${COMMIT}^{commit}")" || {
    printf 'Could not resolve golden-input commit: %s\n' "${COMMIT}" >&2
    exit 1
}

TMP_MANIFEST="$(mktemp)"
trap 'rm -f "${TMP_MANIFEST}"' EXIT

printf 'golden_input_fingerprint_schema=%s\n' "${FINGERPRINT_SCHEMA}" > "${TMP_MANIFEST}"
for path in "${INPUTS[@]}"; do
    if ! git -C "${ROOT}" cat-file -e "${RESOLVED_COMMIT}:${path}" 2>/dev/null; then
        printf 'Golden-input path is missing at %s: %s\n' "${RESOLVED_COMMIT}" "${path}" >&2
        exit 1
    fi
    file_sha256="$(git -C "${ROOT}" show "${RESOLVED_COMMIT}:${path}" | sha256sum | awk '{print $1}')"
    printf '%s\t%s\n' "${path}" "${file_sha256}" >> "${TMP_MANIFEST}"
done

if [[ "${MODE}" == "--manifest" ]]; then
    cat "${TMP_MANIFEST}"
else
    sha256sum "${TMP_MANIFEST}" | awk '{print $1}'
fi

#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${1:-/var/lib/supralinux/images/source/resolute/ubuntu-26.04-server-cloudimg-amd64.img}"
PROVENANCE="${2:-${IMAGE}.provenance.txt}"
IMAGE_NAME="$(basename "${IMAGE}")"
METADATA_DIR="$(dirname "${IMAGE}")"
SUMS="${SUPRALINUX_CLOUD_IMAGE_SUMS:-${METADATA_DIR}/SHA256SUMS}"
SIGNATURE="${SUPRALINUX_CLOUD_IMAGE_SIGNATURE:-${METADATA_DIR}/SHA256SUMS.gpg}"
KEYRING="${SUPRALINUX_CLOUD_IMAGE_KEYRING:-/usr/share/keyrings/ubuntu-cloudimage-keyring.gpg}"
EXPECTED_IMAGE_NAME="ubuntu-26.04-server-cloudimg-amd64.img"

for command_name in awk basename dirname gpgv grep sha256sum; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

if [[ "${IMAGE_NAME}" != "${EXPECTED_IMAGE_NAME}" ]]; then
    printf 'Unexpected Ubuntu source-image filename: %s\n' "${IMAGE_NAME}" >&2
    exit 1
fi

for path in "${IMAGE}" "${PROVENANCE}" "${SUMS}" "${SIGNATURE}" "${KEYRING}"; do
    if [[ ! -f "${path}" || ! -r "${path}" ]]; then
        printf 'Required source-integrity file is missing or unreadable: %s\n' "${path}" >&2
        exit 1
    fi
done

for required_line in \
    'release=resolute' \
    'architecture=amd64' \
    'signature=verified-with-gpgv'; do
    if ! grep -Fqx "${required_line}" "${PROVENANCE}"; then
        printf 'Required provenance field is missing or invalid: %s\n' "${required_line}" >&2
        exit 1
    fi
done

printf 'Re-verifying signed Ubuntu checksum metadata...\n'
gpgv --keyring "${KEYRING}" "${SIGNATURE}" "${SUMS}"

mapfile -t SIGNED_HASHES < <(
    awk -v name="${IMAGE_NAME}" '$2 == "*"name || $2 == name {print $1}' "${SUMS}"
)
if (( ${#SIGNED_HASHES[@]} != 1 )); then
    printf 'Expected exactly one signed SHA-256 entry for %s; found %d.\n' \
        "${IMAGE_NAME}" "${#SIGNED_HASHES[@]}" >&2
    exit 1
fi
EXPECTED_SHA256="${SIGNED_HASHES[0]}"
if [[ ! "${EXPECTED_SHA256}" =~ ^[0-9a-fA-F]{64}$ ]]; then
    printf 'Invalid SHA-256 in signed metadata: %s\n' "${EXPECTED_SHA256}" >&2
    exit 1
fi

mapfile -t PROVENANCE_HASHES < <(awk -F= '$1 == "sha256" {print $2}' "${PROVENANCE}")
if (( ${#PROVENANCE_HASHES[@]} != 1 )); then
    printf 'Expected exactly one sha256 field in provenance; found %d.\n' "${#PROVENANCE_HASHES[@]}" >&2
    exit 1
fi
PROVENANCE_SHA256="${PROVENANCE_HASHES[0]}"
if [[ ! "${PROVENANCE_SHA256}" =~ ^[0-9a-fA-F]{64}$ ]]; then
    printf 'Invalid provenance SHA-256: %s\n' "${PROVENANCE_SHA256}" >&2
    exit 1
fi
if [[ "${PROVENANCE_SHA256,,}" != "${EXPECTED_SHA256,,}" ]]; then
    printf 'Provenance SHA-256 does not match signed Ubuntu metadata.\n' >&2
    printf 'Signed:     %s\n' "${EXPECTED_SHA256}" >&2
    printf 'Provenance: %s\n' "${PROVENANCE_SHA256}" >&2
    exit 1
fi

ACTUAL_SHA256="$(sha256sum "${IMAGE}" | awk '{print $1}')"
if [[ "${ACTUAL_SHA256,,}" != "${EXPECTED_SHA256,,}" ]]; then
    printf 'Ubuntu source-image SHA-256 mismatch against signed Ubuntu metadata.\n' >&2
    printf 'Signed: %s\n' "${EXPECTED_SHA256}" >&2
    printf 'Actual: %s\n' "${ACTUAL_SHA256}" >&2
    exit 1
fi

printf 'Ubuntu source-image provenance verification: PASS\n'
printf 'signed_metadata_verification=PASS\n'
printf 'image=%s\n' "${IMAGE}"
printf 'sha256=%s\n' "${ACTUAL_SHA256,,}"

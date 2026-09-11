#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${SUPRALINUX_CLOUD_IMAGE_BASE_URL:-https://cloud-images.ubuntu.com/releases/resolute/release}"
IMAGE_NAME="ubuntu-26.04-server-cloudimg-amd64.img"
DEST_DIR="${SUPRALINUX_CLOUD_IMAGE_DIR:-${PWD}/.work/cloud-images/resolute}"
KEYRING="${SUPRALINUX_CLOUD_IMAGE_KEYRING:-/usr/share/keyrings/ubuntu-cloudimage-keyring.gpg}"
REFRESH="${SUPRALINUX_REFRESH_CLOUD_IMAGE:-0}"

for command_name in curl gpgv sha256sum awk grep; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done
if [[ ! -r "${KEYRING}" ]]; then
    printf 'Ubuntu cloud-image verification keyring is missing: %s\n' "${KEYRING}" >&2
    printf 'Install ubuntu-keyring on Ubuntu before fetching the image.\n' >&2
    exit 1
fi

mkdir -p "${DEST_DIR}"
IMAGE="${DEST_DIR}/${IMAGE_NAME}"
SUMS="${DEST_DIR}/SHA256SUMS"
SIGNATURE="${DEST_DIR}/SHA256SUMS.gpg"
PROVENANCE="${DEST_DIR}/${IMAGE_NAME}.provenance.txt"

if [[ -e "${IMAGE}" && "${REFRESH}" != "1" ]]; then
    printf 'Refusing to replace existing image without SUPRALINUX_REFRESH_CLOUD_IMAGE=1: %s\n' "${IMAGE}" >&2
    exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

printf 'Downloading signed Ubuntu 26.04 released-image metadata...\n'
curl --fail --show-error --location --output "${TMP_DIR}/SHA256SUMS" "${BASE_URL}/SHA256SUMS"
curl --fail --show-error --location --output "${TMP_DIR}/SHA256SUMS.gpg" "${BASE_URL}/SHA256SUMS.gpg"
gpgv --keyring "${KEYRING}" "${TMP_DIR}/SHA256SUMS.gpg" "${TMP_DIR}/SHA256SUMS"

EXPECTED="$(awk -v name="${IMAGE_NAME}" '$2 == "*"name || $2 == name {print $1; exit}' "${TMP_DIR}/SHA256SUMS")"
if [[ ! "${EXPECTED}" =~ ^[0-9a-fA-F]{64}$ ]]; then
    printf 'Could not resolve SHA-256 for %s from signed SHA256SUMS.\n' "${IMAGE_NAME}" >&2
    exit 1
fi

printf 'Downloading released Ubuntu 26.04 amd64 cloud image...\n'
curl --fail --show-error --location --output "${TMP_DIR}/${IMAGE_NAME}" "${BASE_URL}/${IMAGE_NAME}"
printf '%s  %s\n' "${EXPECTED}" "${TMP_DIR}/${IMAGE_NAME}" | sha256sum --check --strict

install -m 0644 "${TMP_DIR}/${IMAGE_NAME}" "${IMAGE}"
install -m 0644 "${TMP_DIR}/SHA256SUMS" "${SUMS}"
install -m 0644 "${TMP_DIR}/SHA256SUMS.gpg" "${SIGNATURE}"
{
    printf 'fetched_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'release=resolute\n'
    printf 'architecture=amd64\n'
    printf 'source=%s/%s\n' "${BASE_URL}" "${IMAGE_NAME}"
    printf 'sha256=%s\n' "${EXPECTED}"
    printf 'signature=verified-with-gpgv\n'
    printf 'keyring=%s\n' "${KEYRING}"
} > "${PROVENANCE}"

printf 'Verified image: %s\n' "${IMAGE}"
printf 'SHA-256: %s\n' "${EXPECTED}"

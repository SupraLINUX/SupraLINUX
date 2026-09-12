#!/usr/bin/env bash
set -Eeuo pipefail

TARGET_USER="${SUPRALINUX_RUNNER_USER:-${SUDO_USER:-${USER}}}"
INSTALL_DIR="${SUPRALINUX_ACTIONS_RUNNER_DIR:-/opt/actions-runner}"
EVIDENCE_DIR="${SUPRALINUX_EVIDENCE_DIR:-/var/lib/supralinux/evidence}"
API_URL="https://api.github.com/repos/actions/runner/releases/latest"

for command_name in curl jq sha256sum tar; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

if ! id "${TARGET_USER}" >/dev/null 2>&1; then
    printf 'Runner user does not exist: %s\n' "${TARGET_USER}" >&2
    exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

printf 'Resolving latest stable GitHub Actions runner release...\n'
RELEASE_JSON="$(curl --fail --silent --show-error --location \
    -H 'Accept: application/vnd.github+json' \
    -H 'X-GitHub-Api-Version: 2026-03-10' \
    "${API_URL}")"

TAG="$(jq -r '.tag_name // empty' <<<"${RELEASE_JSON}")"
VERSION="${TAG#v}"
if [[ -z "${VERSION}" || "${VERSION}" == "${TAG}" ]]; then
    printf 'Could not resolve a v-prefixed actions/runner release tag.\n' >&2
    exit 1
fi

ASSET_NAME="actions-runner-linux-x64-${VERSION}.tar.gz"
ASSET_JSON="$(jq -c --arg name "${ASSET_NAME}" '.assets[] | select(.name == $name)' <<<"${RELEASE_JSON}")"
if [[ -z "${ASSET_JSON}" ]]; then
    printf 'Latest release %s has no expected Linux x64 asset %s.\n' "${TAG}" "${ASSET_NAME}" >&2
    exit 1
fi

DOWNLOAD_URL="$(jq -r '.browser_download_url // empty' <<<"${ASSET_JSON}")"
DIGEST="$(jq -r '.digest // empty' <<<"${ASSET_JSON}")"
if [[ -z "${DOWNLOAD_URL}" || ! "${DIGEST}" =~ ^sha256:[0-9a-fA-F]{64}$ ]]; then
    printf 'Runner asset is missing a usable SHA-256 digest from GitHub release metadata.\n' >&2
    exit 1
fi
EXPECTED_SHA256="${DIGEST#sha256:}"
ARCHIVE="${TMP_DIR}/${ASSET_NAME}"

printf 'Downloading %s...\n' "${ASSET_NAME}"
curl --fail --show-error --location --output "${ARCHIVE}" "${DOWNLOAD_URL}"
printf '%s  %s\n' "${EXPECTED_SHA256}" "${ARCHIVE}" | sha256sum --check --strict

sudo install -d -o "${TARGET_USER}" -g "$(id -gn "${TARGET_USER}")" -m 0755 "${INSTALL_DIR}"
sudo find "${INSTALL_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
sudo -u "${TARGET_USER}" tar -xzf "${ARCHIVE}" -C "${INSTALL_DIR}"

if [[ -x "${INSTALL_DIR}/bin/installdependencies.sh" ]]; then
    sudo "${INSTALL_DIR}/bin/installdependencies.sh"
fi

sudo install -d -m 0755 "${EVIDENCE_DIR}"
{
    printf 'installed_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'source_repo=actions/runner\n'
    printf 'tag=%s\n' "${TAG}"
    printf 'asset=%s\n' "${ASSET_NAME}"
    printf 'asset_sha256=%s\n' "${EXPECTED_SHA256}"
    printf 'asset_url=%s\n' "${DOWNLOAD_URL}"
    printf 'install_dir=%s\n' "${INSTALL_DIR}"
    printf 'runner_user=%s\n' "${TARGET_USER}"
} | sudo tee "${EVIDENCE_DIR}/actions-runner.txt" >/dev/null

printf 'Installed GitHub Actions runner %s with verified SHA-256.\n' "${TAG}"

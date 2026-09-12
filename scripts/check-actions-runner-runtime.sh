#!/usr/bin/env bash
set -Eeuo pipefail

RUNNER_DIR="${SUPRALINUX_ACTIONS_RUNNER_DIR:-/opt/actions-runner}"
PROVENANCE="${SUPRALINUX_RUNNER_PROVENANCE:-/var/lib/supralinux/evidence/actions-runner.txt}"
EVIDENCE_OUT="${1:-${SUPRALINUX_RUNNER_RUNTIME_EVIDENCE:-}}"
LISTENER="${RUNNER_DIR}/bin/Runner.Listener"

for command_name in awk tr; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Missing required command: %s\n' "${command_name}" >&2
        exit 1
    }
done

if [[ ! -x "${LISTENER}" ]]; then
    printf 'GitHub Actions Runner.Listener is missing or not executable: %s\n' "${LISTENER}" >&2
    exit 1
fi
if [[ ! -f "${PROVENANCE}" || ! -r "${PROVENANCE}" ]]; then
    printf 'GitHub Actions runner provenance is missing or unreadable: %s\n' "${PROVENANCE}" >&2
    exit 1
fi

mapfile -t TAGS < <(awk -F= '$1 == "tag" {print $2}' "${PROVENANCE}")
mapfile -t ASSET_HASHES < <(awk -F= '$1 == "asset_sha256" {print $2}' "${PROVENANCE}")
if (( ${#TAGS[@]} != 1 )); then
    printf 'Expected exactly one tag field in runner provenance; found %d.\n' "${#TAGS[@]}" >&2
    exit 1
fi
if (( ${#ASSET_HASHES[@]} != 1 )); then
    printf 'Expected exactly one asset_sha256 field in runner provenance; found %d.\n' "${#ASSET_HASHES[@]}" >&2
    exit 1
fi

INSTALLED_TAG="${TAGS[0]}"
INSTALLED_VERSION="${INSTALLED_TAG#v}"
ASSET_SHA256="${ASSET_HASHES[0]}"
if [[ "${INSTALLED_TAG}" == "${INSTALLED_VERSION}" || ! "${INSTALLED_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf 'Invalid runner tag in verified provenance: %s\n' "${INSTALLED_TAG}" >&2
    exit 1
fi
if [[ ! "${ASSET_SHA256}" =~ ^[0-9a-fA-F]{64}$ ]]; then
    printf 'Invalid runner asset SHA-256 in verified provenance: %s\n' "${ASSET_SHA256}" >&2
    exit 1
fi

RUNTIME_VERSION="$("${LISTENER}" --version | tr -d '\r[:space:]')"
RUNTIME_COMMIT="$("${LISTENER}" --commit | tr -d '\r[:space:]')"
if [[ ! "${RUNTIME_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf 'Could not resolve a valid runtime Actions runner version: %s\n' "${RUNTIME_VERSION}" >&2
    exit 1
fi
if [[ ! "${RUNTIME_COMMIT}" =~ ^[0-9a-fA-F]{40}$ ]]; then
    printf 'Could not resolve a full runtime Actions runner commit SHA: %s\n' "${RUNTIME_COMMIT}" >&2
    exit 1
fi

if [[ "${RUNTIME_VERSION}" != "${INSTALLED_VERSION}" ]]; then
    printf 'Runtime Actions runner version differs from verified golden-image provenance.\n' >&2
    printf 'Verified golden version: %s\n' "${INSTALLED_VERSION}" >&2
    printf 'Runtime version:         %s\n' "${RUNTIME_VERSION}" >&2
    printf 'Rebuild the golden runner image with the current supported runner release before authoritative execution.\n' >&2
    exit 1
fi

if [[ -n "${EVIDENCE_OUT}" ]]; then
    mkdir -p "$(dirname "${EVIDENCE_OUT}")"
    {
        printf 'checked_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        printf 'verified_tag=%s\n' "${INSTALLED_TAG}"
        printf 'verified_asset_sha256=%s\n' "${ASSET_SHA256,,}"
        printf 'runtime_version=%s\n' "${RUNTIME_VERSION}"
        printf 'runtime_commit=%s\n' "${RUNTIME_COMMIT,,}"
        printf 'runtime_matches_verified_version=yes\n'
    } > "${EVIDENCE_OUT}"
fi

printf 'Actions runner runtime provenance verification: PASS\n'
printf 'runtime_version=%s\n' "${RUNTIME_VERSION}"
printf 'runtime_commit=%s\n' "${RUNTIME_COMMIT,,}"

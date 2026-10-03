#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FINGERPRINT="${ROOT}/scripts/kde-tier1-dependency-contract-fingerprint.py"
MANIFEST="manifests/kde-frameworks-tier1-dependencies.json"

if [[ "$#" -ne 2 ]]; then
    printf 'Usage: %s <before-sha> <after-sha>\n' "$0" >&2
    exit 2
fi

BEFORE="$1"
AFTER="$2"

for sha in "${BEFORE}" "${AFTER}"; do
    if [[ ! "${sha}" =~ ^[0-9a-fA-F]{40}$ ]]; then
        printf 'Invalid commit SHA: %s\n' "$sha" >&2
        exit 2
    fi
    git -C "$ROOT" cat-file -e "${sha}^{commit}" 2>/dev/null || {
        printf 'Commit is not available locally: %s\n' "$sha" >&2
        exit 2
    }
done

mapfile -t CHANGED_PATHS < <(git -C "$ROOT" diff --name-only "$BEFORE" "$AFTER" --)
printf 'Changed paths for KDE Tier 1 dependency preflight scope:\n'
printf '  %s\n' "${CHANGED_PATHS[@]:-<none>}"

for path in "${CHANGED_PATHS[@]}"; do
    case "$path" in
        scripts/run-kde-tier1-dependency-preflight.sh|.github/workflows/kde-tier1-dependency-preflight.yml)
            printf 'Provider-preflight execution input changed: %s\n' "$path"
            exit 0
            ;;
    esac
done

if printf '%s\n' "${CHANGED_PATHS[@]}" | grep -Fxq "$MANIFEST"; then
    if ! git -C "$ROOT" cat-file -e "${BEFORE}:${MANIFEST}" 2>/dev/null; then
        printf 'Dependency manifest is new; provider preflight required.\n'
        exit 0
    fi
    before_fp="$(python3 "$FINGERPRINT" --git-ref "$BEFORE")"
    after_fp="$(python3 "$FINGERPRINT" --git-ref "$AFTER")"
    printf 'Dependency contract fingerprint before: %s\n' "$before_fp"
    printf 'Dependency contract fingerprint after:  %s\n' "$after_fp"
    if [[ "$before_fp" != "$after_fp" ]]; then
        printf 'Dependency provider contract changed; provider preflight required.\n'
        exit 0
    fi
    printf 'Dependency manifest changed only outside provider-input semantics; no provider rebuild required.\n'
fi

printf 'No Tier 1 dependency-provider input changed in this event delta.\n'
exit 1

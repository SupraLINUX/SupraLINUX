#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 2 ]]; then
    printf 'Usage: %s <before-sha> <after-sha>\n' "$0" >&2
    exit 2
fi

BEFORE="$1"
AFTER="$2"

for sha in "${BEFORE}" "${AFTER}"; do
    if [[ ! "${sha}" =~ ^[0-9a-fA-F]{40}$ ]]; then
        printf 'Invalid commit SHA: %s\n' "${sha}" >&2
        exit 2
    fi
    git cat-file -e "${sha}^{commit}" 2>/dev/null || {
        printf 'Commit is not available locally: %s\n' "${sha}" >&2
        exit 2
    }
done

mapfile -t CHANGED_PATHS < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
printf 'Changed paths for KDE Tier 1 dependency preflight scope:\n'
printf '  %s\n' "${CHANGED_PATHS[@]:-<none>}"

for path in "${CHANGED_PATHS[@]}"; do
    case "${path}" in
        manifests/kde-frameworks-tier1.json|\
        manifests/kde-frameworks-tier1-dependencies.json|\
        manifests/desktop-stack.json|\
        scripts/validate_kde_tier1.py|\
        scripts/run-kde-tier1-dependency-preflight.sh|\
        scripts/kde-tier1-dependency-preflight-needed.sh|\
        .github/workflows/kde-tier1-dependency-preflight.yml|\
        docs/kde-tier1.md|\
        docs/kde-tier1-dependencies.md)
            printf 'Relevant Tier 1 dependency-preflight change: %s\n' "${path}"
            exit 0
            ;;
    esac
done

printf 'No Tier 1 dependency-preflight-relevant change in this event delta.\n'
exit 1

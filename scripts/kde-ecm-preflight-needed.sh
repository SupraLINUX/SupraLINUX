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
printf 'Changed paths for KDE ECM package scope:\n'
printf '  %s\n' "${CHANGED_PATHS[@]:-<none>}"

for path in "${CHANGED_PATHS[@]}"; do
    case "${path}" in
        packages/kde/extra-cmake-modules/*|scripts/run-kde-ecm-package-preflight.sh|scripts/kde-ecm-preflight-needed.sh|.github/workflows/kde-ecm-package-preflight.yml|manifests/kde-dag.json|docs/kde-dag.md)
            printf 'Relevant KDE-ECM change: %s\n' "${path}"
            exit 0
            ;;
    esac
done

printf 'No KDE-ECM-relevant change in this event delta.\n'
exit 1

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
printf 'Changed paths for KDE Attica packaging-reference scope:\n'
printf '  %s\n' "${CHANGED_PATHS[@]:-<none>}"

for path in "${CHANGED_PATHS[@]}"; do
    case "${path}" in
        scripts/run-kde-attica-packaging-reference.sh|scripts/kde-attica-packaging-reference-needed.sh|.github/workflows/kde-attica-packaging-reference.yml)
            printf 'Relevant KDE-Attica packaging-reference change: %s\n' "${path}"
            exit 0
            ;;
    esac
done

printf 'No KDE-Attica-packaging-reference-relevant change in this event delta.\n'
exit 1

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

mapfile -t changed_paths < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
printf 'Changed paths for Tier 1 packaging-reference scope:\n'
printf '  %s\n' "${changed_paths[@]:-<none>}"

for path in "${changed_paths[@]}"; do
    case "${path}" in
        manifests/kde-frameworks-tier1.json|\
        manifests/kde-frameworks-tier1-packaging-reference.json|\
        scripts/run-kde-tier1-packaging-reference-snapshot.sh|\
        scripts/kde-tier1-packaging-reference-needed.sh|\
        .github/workflows/kde-tier1-packaging-reference.yml)
            printf 'Relevant Tier 1 packaging-reference change: %s\n' "${path}"
            exit 0
            ;;
    esac
done

printf 'No Tier 1 packaging-reference-relevant change in this event delta.\n'
exit 1

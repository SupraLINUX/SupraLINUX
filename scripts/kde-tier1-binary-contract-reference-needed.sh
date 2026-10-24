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
printf 'Changed paths for Tier 1 binary-contract reference scope:\n'
printf '  %s\n' "${changed_paths[@]:-<none>}"

for path in "${changed_paths[@]}"; do
    case "${path}" in
        manifests/kde-frameworks-tier1-packaging-reference.json|\
        scripts/run-kde-tier1-binary-contract-snapshot.sh|\
        scripts/kde-tier1-binary-contract-reference-needed.sh|\
        scripts/validate_kde_tier1_packaging_reference.py|\
        .github/workflows/kde-tier1-binary-contract-reference.yml|\
        docs/kde-tier1-packaging.md)
            printf 'Relevant Tier 1 binary-contract reference change: %s\n' "${path}"
            exit 0
            ;;
    esac
done

printf 'No Tier 1 binary-contract-reference-relevant change in this event delta.\n'
exit 1

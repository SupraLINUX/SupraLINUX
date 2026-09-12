#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 3 ]]; then
    printf 'Usage: %s <node> <before-sha> <after-sha>\n' "$0" >&2
    exit 2
fi

NODE="$1"
BEFORE="$2"
AFTER="$3"

case "${NODE}" in
    kcodecs|kdbusaddons|threadweaver) ;;
    *)
        printf 'Unsupported Tier 1 batch node: %s\n' "${NODE}" >&2
        exit 2
        ;;
esac

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
printf 'Changed paths for Tier 1 batch node %s:\n' "${NODE}"
printf '  %s\n' "${changed_paths[@]:-<none>}"

for path in "${changed_paths[@]}"; do
    case "${path}" in
        packages/kde/"${NODE}"/*|\
        manifests/kde-tier1-package-campaign.json|\
        scripts/run-kde-tier1-package-preflight.sh|\
        scripts/kde-tier1-package-preflight-needed.sh|\
        .github/workflows/kde-tier1-package-preflight.yml)
            printf 'Relevant Tier 1 package change for %s: %s\n' "${NODE}" "${path}"
            exit 0
            ;;
    esac
done

printf 'No Tier 1 package-build-relevant change for %s in this event delta.\n' "${NODE}"
exit 1

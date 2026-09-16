#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
    [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
    git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done
mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
    case "${path}" in
        manifests/kde-tier1-source-diagnostic.json|\
        manifests/kde-frameworks-tier1-dependencies.json|\
        scripts/run-kde-tier1-source-diagnostic.sh|\
        scripts/kde-tier1-source-diagnostic-needed.sh|\
        .github/workflows/kde-tier1-source-diagnostic.yml)
            exit 0
            ;;
    esac
done
exit 1

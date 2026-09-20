#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"
AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
    [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
    git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done
mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
    case "${path}" in
        manifests/kde-frameworks-tier2-dependencies.json|scripts/run-kde-tier2-provider-audit.sh|scripts/kde-tier2-provider-audit-needed.sh|.github/workflows/kde-tier2-provider-audit.yml)
            echo "${path}: Tier 2 provider-audit input changed."
            exit 0
            ;;
    esac
done
if printf '%s\n' "${changed[@]}" | grep -Fxq "manifests/kde-tier2-campaign-plan.json"; then
    before_batch="$(git -C "${ROOT}" show "${BEFORE}:manifests/kde-tier2-campaign-plan.json" | python3 -c 'import json,sys; print(",".join(json.load(sys.stdin).get("next_provider_audit_batch",[])))')"
    after_batch="$(git -C "${ROOT}" show "${AFTER}:manifests/kde-tier2-campaign-plan.json" | python3 -c 'import json,sys; print(",".join(json.load(sys.stdin).get("next_provider_audit_batch",[])))')"
    if [[ "${before_batch}" != "${after_batch}" ]]; then
        echo "Generated Tier 2 provider-audit batch changed."
        exit 0
    fi
fi
echo "No Tier 2 provider-audit input changed."
exit 1

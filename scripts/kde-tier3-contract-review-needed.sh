#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

review_at(){
  git -C "${ROOT}" show "$1:manifests/kde-tier3-package-contracts.json" 2>/dev/null |
    python3 -c 'import json,sys; d=json.load(sys.stdin); r=d.get("contract_review",{}); print(r.get("status","")+"|"+r.get("execution_request",{}).get("status",""))'
}

if ! git -C "${ROOT}" cat-file -e "${BEFORE}:manifests/kde-tier3-package-contracts.json" 2>/dev/null; then
  echo "Tier 3 contract-review campaign is new."; exit 0
fi
review="$(review_at "${AFTER}")"
if [[ "${review}" == "pending-ci|requested" ]]; then
  echo "Tier 3 contract review has an explicit pending execution request."; exit 0
fi
mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    manifests/kde-tier3-package-contracts.json|manifests/kde-frameworks-tier3-dependencies.json|manifests/kde-frameworks-tier3.json|scripts/review_kde_tier3_package_contracts.py|scripts/kde-tier3-contract-review-needed.sh|.github/workflows/kde-tier3-contract-review.yml)
      if [[ "${review}" == pending-ci* ]]; then
        echo "${path}: active Tier 3 contract-review input changed."; exit 0
      fi
      ;;
  esac
done
echo "No active Tier 3 contract-review semantic input changed."
exit 1

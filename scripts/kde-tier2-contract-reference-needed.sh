#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$#" -eq 2 ]] || exit 2
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done
mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    manifests/kde-tier2-package-contracts.json|scripts/run-kde-tier2-contract-reference-snapshot.sh|scripts/kde-tier2-contract-reference-needed.sh|.github/workflows/kde-tier2-contract-reference.yml)
      echo "${path}: Tier 2 contract-reference input changed."
      exit 0 ;;
  esac
done
echo "No Tier 2 contract-reference input changed."
exit 1

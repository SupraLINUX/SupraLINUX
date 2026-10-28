#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

capture_at(){
  git -C "${ROOT}" show "$1:manifests/kde-tier3-package-contracts.json" 2>/dev/null |
    python3 -c 'import json,sys; d=json.load(sys.stdin); c=d.get("packaging_tree_capture",{}); print(c.get("status","")+"|"+c.get("execution_request",{}).get("status",""))'
}
fingerprint_at(){
  git -C "${ROOT}" show "$1:manifests/kde-tier3-package-contracts.json" 2>/dev/null |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin); selected=d.get("selected_nodes",[])
v={
 "selected_nodes":selected,
 "references":{n:d.get("nodes",{}).get(n,{}).get("technical_references") for n in selected},
 "capture":{k:d.get("packaging_tree_capture",{}).get(k) for k in ("selected_sides","claim","authoritative")},
}
print(hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

if ! git -C "${ROOT}" cat-file -e "${BEFORE}:manifests/kde-tier3-package-contracts.json" 2>/dev/null; then
  echo "Tier 3 packaging-tree campaign is new."; exit 0
fi
capture="$(capture_at "${AFTER}")"
if [[ "${capture}" == "pending-ci|requested" ]]; then
  echo "Tier 3 packaging-tree capture has an explicit pending execution request."; exit 0
fi
if [[ "$(fingerprint_at "${BEFORE}")" != "$(fingerprint_at "${AFTER}")" ]]; then
  echo "Tier 3 packaging-tree semantic input changed."; exit 0
fi
mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    scripts/capture_kde_tier3_packaging_trees.py|scripts/kde-tier3-packaging-tree-needed.sh|.github/workflows/kde-tier3-packaging-tree.yml)
      if [[ "${capture}" == pending-ci* ]]; then
        echo "${path}: active packaging-tree execution input changed."; exit 0
      fi
      ;;
  esac
done
echo "No active Tier 3 packaging-tree semantic input changed."
exit 1

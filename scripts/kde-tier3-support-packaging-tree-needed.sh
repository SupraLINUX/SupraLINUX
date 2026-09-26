#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

capture_status() {
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-package-contracts.json" 2>/dev/null |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("packaging_tree_capture",{}).get("status",""))'
}
fingerprint() {
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-package-contracts.json" 2>/dev/null |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin)
c=d.get("packaging_tree_capture",{})
selected=c.get("selected_components",[])
refs=d.get("technical_references",{})
v={
 "selected_components":selected,
 "selected_sides":c.get("selected_sides",[]),
 "references":{n:{side:{
    "source_package":refs.get(n,{}).get(side,{}).get("source_package"),
    "version":refs.get(n,{}).get(side,{}).get("version"),
    "checksums_sha256":refs.get(n,{}).get(side,{}).get("checksums_sha256",[]),
 } for side in c.get("selected_sides",[])} for n in selected},
}
print(hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

if ! git -C "${ROOT}" cat-file -e "${BEFORE}:manifests/kde-tier3-support-package-contracts.json" 2>/dev/null; then exit 0; fi
after_status="$(capture_status "${AFTER}")"
if [[ "${after_status}" == pending-ci ]]; then
  echo "Tier 3 support packaging-tree capture remains pending."
  exit 0
fi
if [[ "$(fingerprint "${BEFORE}")" != "$(fingerprint "${AFTER}")" ]]; then
  echo "Tier 3 support packaging-tree semantic input changed."
  exit 0
fi
mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    scripts/run-kde-tier3-support-packaging-tree-capture.sh|scripts/kde-tier3-support-packaging-tree-needed.sh|.github/workflows/kde-tier3-support-packaging-tree.yml)
      if [[ "${after_status}" == pending-ci ]]; then exit 0; fi
      ;;
  esac
done
echo "No Tier 3 support packaging-tree semantic input changed."
exit 1

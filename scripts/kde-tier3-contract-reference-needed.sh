#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

state_at(){
  git -C "${ROOT}" show "$1:manifests/kde-tier3-package-contracts.json" 2>/dev/null |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("state",""))'
}
request_at(){
  git -C "${ROOT}" show "$1:manifests/kde-tier3-package-contracts.json" 2>/dev/null |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("execution_request",{}).get("status",""))'
}
fingerprint_at(){
  git -C "${ROOT}" show "$1:manifests/kde-tier3-package-contracts.json" 2>/dev/null |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin); selected=d.get("selected_nodes",[])
v={
 "frameworks_series":d.get("frameworks_series"),
 "selected_nodes":selected,
 "compatibility_reference":d.get("compatibility_reference",{}),
 "reference_capture":{k:d.get("reference_capture",{}).get(k) for k in ("ubuntu_suite","debian_suite","selection_policy")},
 "nodes":{n:{
   "upstream_version":d.get("nodes",{}).get(n,{}).get("upstream_version"),
   "source_sha256":d.get("nodes",{}).get(n,{}).get("source_sha256"),
   "source_package":d.get("nodes",{}).get(n,{}).get("source_package"),
 } for n in selected},
}
print(hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

if ! git -C "${ROOT}" cat-file -e "${BEFORE}:manifests/kde-tier3-package-contracts.json" 2>/dev/null; then
  echo "Tier 3 package-contract reference campaign is new."
  exit 0
fi
after_state="$(state_at "${AFTER}")"
if [[ "${after_state}" == reference-capture-pending && "$(request_at "${AFTER}")" == requested ]]; then
  echo "Tier 3 package-contract reference capture has an explicit pending execution request."
  exit 0
fi
if [[ "$(fingerprint_at "${BEFORE}")" != "$(fingerprint_at "${AFTER}")" ]]; then
  echo "Tier 3 package-contract reference semantic input changed."
  exit 0
fi
mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    scripts/run-kde-tier3-contract-reference-snapshot.sh|scripts/kde-tier3-contract-reference-needed.sh|.github/workflows/kde-tier3-contract-reference.yml)
      if [[ "${after_state}" == reference-capture-pending ]]; then
        echo "${path}: active Tier 3 reference-capture execution input changed."
        exit 0
      fi
      ;;
  esac
done
echo "No active Tier 3 package-contract reference input changed."
exit 1

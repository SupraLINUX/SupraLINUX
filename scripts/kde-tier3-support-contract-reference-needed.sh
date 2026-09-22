#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

state_at() {
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-package-contracts.json" 2>/dev/null |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("state",""))'
}

fingerprint_at() {
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-package-contracts.json" 2>/dev/null |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin)
selected=d.get("selected_components",[])
projection={
 "frameworks_series":d.get("frameworks_series"),
 "selected_components":selected,
 "provider_audit":d.get("provider_audit",{}),
 "components":{n:{
   "upstream_source":d.get("components",{}).get(n,{}).get("upstream_source"),
   "upstream_version":d.get("components",{}).get(n,{}).get("upstream_version"),
   "upstream_source_sha256":d.get("components",{}).get(n,{}).get("upstream_source_sha256"),
   "reference_sources":d.get("components",{}).get(n,{}).get("reference_sources",{}),
 } for n in selected},
 "capture_policy":{k:d.get("reference_capture",{}).get(k) for k in ("ubuntu_suite","debian_suite","debian_selection_policy")},
}
print(hashlib.sha256(json.dumps(projection,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

if ! git -C "${ROOT}" cat-file -e "${BEFORE}:manifests/kde-tier3-support-package-contracts.json" 2>/dev/null; then
  echo "Tier 3 support contract-reference manifest is new."
  exit 0
fi

after_state="$(state_at "${AFTER}")"
if [[ "${after_state}" == "reference-capture-pending" ]]; then
  echo "Tier 3 support contract-reference capture remains pending."
  exit 0
fi

if [[ "$(fingerprint_at "${BEFORE}")" != "$(fingerprint_at "${AFTER}")" ]]; then
  echo "Tier 3 support contract-reference semantic input changed."
  exit 0
fi

mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    scripts/run-kde-tier3-support-contract-reference.sh|scripts/kde-tier3-support-contract-reference-needed.sh|.github/workflows/kde-tier3-support-contract-reference.yml)
      if [[ "${after_state}" == "reference-capture-pending" ]]; then
        echo "${path}: active reference-capture execution input changed."
        exit 0
      fi
      ;;
  esac
done
echo "No Tier 3 support contract-reference semantic input changed."
exit 1

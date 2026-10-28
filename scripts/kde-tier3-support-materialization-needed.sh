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
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-materialization.json" 2>/dev/null |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("state",""))'
}
fingerprint() {
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-materialization.json" 2>/dev/null |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin); nodes=d.get("selected_nodes",[])
v={"frameworks_series":d.get("frameworks_series"),"contract_manifest":d.get("contract_manifest"),"selected_nodes":nodes,"common_adaptations":d.get("common_adaptations",{}),"nodes":{n:{k:d.get("nodes",{}).get(n,{}).get(k) for k in ("source_package","upstream_version","upstream_source_sha256","packaging_reference_version","packaging_reference_tree_sha256","package_version","expected_binary_packages")} for n in nodes}}
print(hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}
if ! git -C "${ROOT}" cat-file -e "${BEFORE}:manifests/kde-tier3-support-materialization.json" 2>/dev/null; then exit 0; fi
after_state="$(state_at "${AFTER}")"
if [[ "${after_state}" == pending-ci ]]; then echo "Tier 3 support materialization remains pending."; exit 0; fi
if [[ "$(fingerprint "${BEFORE}")" != "$(fingerprint "${AFTER}")" ]]; then echo "Tier 3 support materialization semantic input changed."; exit 0; fi
mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    scripts/materialize-kde-tier3-support-package.sh|scripts/kde-tier3-support-materialization-needed.sh|.github/workflows/kde-tier3-support-materialization.yml)
      echo "${path}: materialization execution input changed."
      exit 0
      ;;
  esac
done
echo "No Tier 3 support materialization semantic input changed."
exit 1

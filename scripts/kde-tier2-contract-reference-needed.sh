#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$#" -eq 2 ]] || exit 2
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

state_at() {
  git show "$1:manifests/kde-tier2-package-contracts.json" 2>/dev/null |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("state",""))'
}

fingerprint_at() {
  git show "$1:manifests/kde-tier2-package-contracts.json" |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin)
selected=d.get("selected_nodes",[])
projection={
 "selected_nodes":selected,
 "compatibility_reference":d.get("compatibility_reference",{}),
 "nodes":{
   node:{
     "source_package":d.get("nodes",{}).get(node,{}).get("source_package"),
     "compatibility_binary_packages":d.get("nodes",{}).get(node,{}).get("compatibility_binary_packages",[]),
   }
   for node in selected
 },
}
print(hashlib.sha256(json.dumps(projection,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
after_state="$(state_at "${AFTER}")"
for path in "${changed[@]}"; do
  case "${path}" in
    manifests/kde-tier2-package-contracts.json)
      if ! git cat-file -e "${BEFORE}:${path}" 2>/dev/null; then exit 0; fi
      if [[ "$(fingerprint_at "${BEFORE}")" != "$(fingerprint_at "${AFTER}")" ]]; then
        echo "Tier 2 contract-reference semantic input changed."
        exit 0
      fi
      ;;
    scripts/run-kde-tier2-contract-reference-snapshot.sh|scripts/kde-tier2-contract-reference-needed.sh|.github/workflows/kde-tier2-contract-reference.yml)
      if [[ "${after_state}" == "reference-capture-pending" ]]; then
        echo "${path}: active contract-reference execution input changed."
        exit 0
      fi
      ;;
  esac
done
echo "No active Tier 2 contract-reference input changed."
exit 1

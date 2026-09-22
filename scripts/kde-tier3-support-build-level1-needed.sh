#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done
fingerprint(){
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-build-level1.json" 2>/dev/null |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin)
sel=d.get("selected_nodes",[])
v={
 "frameworks_series":d.get("frameworks_series"),
 "selected_nodes":sel,
 "materialization_manifest":d.get("materialization_manifest"),
 "level0_manifest":d.get("level0_manifest"),
 "shared_predecessors":d.get("shared_predecessors",{}),
 "retained_predecessors":d.get("retained_predecessors",{}),
 "package_dependency_closure":d.get("package_dependency_closure",{}),
 "nodes":{n:{k:d.get("nodes",{}).get(n,{}).get(k) for k in ("source_package","upstream_version","package_version","expected_binary_packages","materialization","direct_predecessors","package_dependency_closure","test_policy","executable_contract","cmake_package","cmake_variable","payload_contract")} for n in sel},
}
print(hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}
runnable(){
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-build-level1.json" 2>/dev/null |
    python3 -c 'import json,sys
d=json.load(sys.stdin); print("yes" if any(d["nodes"][n].get("state") in {"prepared-pending-build","remediation-pending-build"} for n in d.get("selected_nodes",[])) else "no")'
}
if ! git -C "${ROOT}" cat-file -e "${BEFORE}:manifests/kde-tier3-support-build-level1.json" 2>/dev/null; then
  echo "Tier 3 support level1 campaign is new."; exit 0
fi
if [[ "$(fingerprint "${BEFORE}")" != "$(fingerprint "${AFTER}")" ]]; then
  echo "Tier 3 support level1 semantic build input changed."; exit 0
fi
if [[ "$(runnable "${AFTER}")" == yes ]]; then
  attempts="$(git -C "${ROOT}" show "${AFTER}:manifests/kde-tier3-support-build-level1-attempts.json" 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sum(len(v) for v in d.get("nodes",{}).values()))' || echo 0)"
  if [[ "${attempts}" -eq 0 ]]; then
    echo "Tier 3 support level1 has runnable nodes and no recorded attempt yet."; exit 0
  fi
fi
mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    scripts/run-kde-tier3-support-build-level1.sh|scripts/validate-kde-tier3-support-level1-retained-inputs.py|scripts/plan-kde-tier3-support-build-level1.py|scripts/kde-tier3-support-build-level1-needed.sh|.github/workflows/kde-tier3-support-build-level1.yml)
      if [[ "$(runnable "${AFTER}")" == yes ]]; then echo "${path}: active level1 execution input changed."; exit 0; fi
      ;;
  esac
done
echo "No Tier 3 support level1 semantic build input changed."
exit 1

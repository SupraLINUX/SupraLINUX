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
  git -C "${ROOT}" show "$1:manifests/kde-tier3-materialization.json" 2>/dev/null |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("state",""))'
}

fingerprint() {
  python3 - "${ROOT}" "$1" <<'PY'
import hashlib,json,subprocess,sys
root,sha=sys.argv[1:]
def show(path):
    raw=subprocess.check_output(["git","-C",root,"show",f"{sha}:{path}"],text=True)
    return json.loads(raw)
m=show("manifests/kde-tier3-materialization.json")
c=show("manifests/kde-tier3-package-contracts.json")
t=show("manifests/kde-frameworks-tier3.json")
nodes=m.get("selected_nodes",[])
contract_nodes={}
for node in nodes:
    x=c.get("nodes",{}).get(node,{})
    contract_nodes[node]={
      "source_package":x.get("source_package"),
      "upstream_version":x.get("upstream_version"),
      "source_sha256":x.get("source_sha256"),
      "package_version_candidate":x.get("package_version_candidate"),
      "packaging_baseline":x.get("packaging_baseline"),
      "target_binary_packages":x.get("target_binary_packages"),
      "supralinux_additional_binary_packages":x.get("supralinux_additional_binary_packages"),
      "selected_profile":x.get("selected_profile"),
      "binary_relation_overrides":x.get("binary_relation_overrides",[]),
      "python_module":x.get("python_module"),
      "python_runtime_contract":x.get("python_runtime_contract"),
      "debian_reference":x.get("technical_references",{}).get("debian",{}),
    }
canonical={x.get("id"):{"source_url":x.get("source_url"),"source_sha256":x.get("source_sha256")} for x in t.get("nodes",[]) if x.get("id") in nodes}
v={
  "frameworks_series":m.get("frameworks_series"),
  "contract_manifest":m.get("contract_manifest"),
  "canonical_manifest":m.get("canonical_manifest"),
  "source_policy":m.get("source_policy"),
  "selected_nodes":nodes,
  "common_adaptations":m.get("common_adaptations",{}),
  "contract_decision":c.get("contract_decision",{}),
  "provider_adaptations":c.get("provider_adaptations",{}),
  "contract_nodes":contract_nodes,
  "canonical_sources":canonical,
}
print(hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest())
PY
}

if ! git -C "${ROOT}" cat-file -e "${BEFORE}:manifests/kde-tier3-materialization.json" 2>/dev/null; then
  echo "Tier 3 materialization definition introduced."
  exit 0
fi

after_state="$(state_at "${AFTER}")"
if [[ "${after_state}" == "pending-ci" ]]; then
  echo "Tier 3 materialization remains pending."
  exit 0
fi

if [[ "$(fingerprint "${BEFORE}")" != "$(fingerprint "${AFTER}")" ]]; then
  echo "Tier 3 materialization semantic input changed."
  exit 0
fi

mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    scripts/materialize_kde_tier3_package.py|scripts/kde-tier3-materialization-needed.sh|.github/workflows/kde-tier3-materialization.yml)
      echo "${path}: materialization execution input changed."
      exit 0
      ;;
  esac
done

echo "No Tier 3 materialization semantic input changed."
exit 1

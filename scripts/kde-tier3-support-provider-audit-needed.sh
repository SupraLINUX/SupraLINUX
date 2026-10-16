#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

status() {
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-provider-audit.json" 2>/dev/null |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))'
}

fingerprint() {
  git -C "${ROOT}" show "$1:manifests/kde-tier3-support-provider-audit.json" 2>/dev/null |
    python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin)
v={
 "authority":d.get("authority"),
 "frameworks_series":d.get("frameworks_series"),
 "provider_platform":d.get("provider_platform"),
 "components":{k:{
   "role":x.get("role"),
   "required_upstream_version":x.get("required_upstream_version"),
   "ubuntu_probe_package":x.get("ubuntu_probe_package"),
   "retained_kde_predecessors":x.get("retained_kde_predecessors"),
   "selected_ci_predecessors":x.get("selected_ci_predecessors",[]),
   "external_requirements":x.get("external_requirements",[]),
 } for k,x in d.get("components",{}).items()}
}
print(hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

if ! git -C "${ROOT}" cat-file -e "${BEFORE}:manifests/kde-tier3-support-provider-audit.json" 2>/dev/null; then
  echo "Tier 3 support provider audit is new."
  exit 0
fi

after_status="$(status "${AFTER}")"
if [[ "${after_status}" == "pending-ci" ]]; then
  echo "Tier 3 support provider audit remains pending-ci."
  exit 0
fi

if [[ "$(fingerprint "${BEFORE}")" != "$(fingerprint "${AFTER}")" ]]; then
  echo "Tier 3 support provider-audit semantic inputs changed."
  exit 0
fi

mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
for path in "${changed[@]}"; do
  case "${path}" in
    scripts/run-kde-tier3-support-provider-audit.sh|scripts/kde-tier3-support-provider-audit-needed.sh|.github/workflows/kde-tier3-support-provider-audit.yml)
      echo "${path}: provider-audit execution input changed."
      exit 0
      ;;
  esac
done

echo "No Tier 3 support provider-audit semantic input changed."
exit 1

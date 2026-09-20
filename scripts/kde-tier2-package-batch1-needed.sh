#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done
mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
for p in "${changed[@]}"; do
  case "${p}" in
    packages/kde/kauth/*|scripts/run-kde-tier2-package-batch1-preflight.sh|scripts/kde-tier2-package-batch1-needed.sh|scripts/audit-kde-development-contract.py|.github/workflows/kde-tier2-package-batch1.yml)
      exit 0 ;;
  esac
done
CAMPAIGN="manifests/kde-tier2-package-campaign-batch1.json"
if printf '%s\n' "${changed[@]}" | grep -Fxq "${CAMPAIGN}"; then
  git cat-file -e "${BEFORE}:${CAMPAIGN}" 2>/dev/null || exit 0
  if ! python3 - "${BEFORE}" "${AFTER}" <<'PY'
import json,subprocess,sys
before,after=sys.argv[1:]
def load(ref):
 return json.loads(subprocess.check_output(["git","show",f"{ref}:manifests/kde-tier2-package-campaign-batch1.json"],text=True))
def fp(d):
 n=d["nodes"]["kauth"]; s=d["shared_predecessors"]; r=d["technical_references"]["debian_6_30"]
 keys=("upstream_version","source_package","package_version","source_url","source_sha256","signing_key","kde_framework_build_dependencies","external_build_dependencies","backend_profile","runtime_package","soname","binary_contracts","dependency_contracts","required_artifact_contracts")
 return {"schema":d["schema"],"frameworks":d["frameworks_series"],"authority":d["authority"],"provider":d["provider_platform"],"selected":tuple(d["selected_nodes"]),"predecessors":s,"reference":r,"node":{k:n[k] for k in keys}}
raise SystemExit(0 if fp(load(before))==fp(load(after)) else 1)
PY
  then exit 0; fi
fi
exit 1

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
    packages/kde/kguiaddons/*|scripts/run-kde-tier1-package-batch8-preflight.sh|scripts/kde-tier1-package-batch8-needed.sh|.github/workflows/kde-tier1-package-batch8.yml)
      exit 0 ;;
  esac
done

CAMPAIGN="manifests/kde-tier1-package-campaign-batch8.json"
if printf '%s\n' "${changed[@]}" | grep -Fxq "${CAMPAIGN}"; then
  git cat-file -e "${BEFORE}:${CAMPAIGN}" 2>/dev/null || exit 0
  if ! python3 - "${BEFORE}" "${AFTER}" <<'PY2'
import json,subprocess,sys
before,after=sys.argv[1:]
def load(ref):
 return json.loads(subprocess.check_output(["git","show",f"{ref}:manifests/kde-tier1-package-campaign-batch8.json"],text=True))
def fp(d):
 n=d["nodes"]["kguiaddons"]; s=d["shared_predecessors"]
 keys=("upstream_version","source_package","package_version","source_url","source_sha256","runtime_package","python_package","python_module","soname","binary_contracts","dependency_contracts","recommendation_contracts","upstream_defaults","kde_framework_build_dependencies","public_header_dependencies","symbols","copyright","signing_key")
 return {"schema":d["schema"],"frameworks":d["frameworks_series"],"authority":d["authority"],"provider":d["provider_platform"],"selected":tuple(d["selected_nodes"]),"ecm":s["extra_cmake_modules"],"trees":s["packaging_trees"],"kcore":s["kcoreaddons_public_header_provider"],"node":{k:n[k] for k in keys}}
raise SystemExit(0 if fp(load(before))==fp(load(after)) else 1)
PY2
  then
    exit 0
  fi
fi

# Attempt history and result/planning-only state changes are not build inputs.
exit 1

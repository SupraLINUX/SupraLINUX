#!/usr/bin/env bash
set -Eeuo pipefail
# Exit contract: 0 = rebuild this node, 1 = intentional scope-skip, any other status = selector error.
# Kirigami package-input changes propagate to KQuickCharts because Kirigami is its package-validation predecessor.
[[ "$#" -eq 3 ]] || { echo "Usage: $0 <node> <before-sha> <after-sha>" >&2; exit 2; }
NODE="$1"; BEFORE="$2"; AFTER="$3"
case "${NODE}" in kirigami|kquickcharts) ;; *) exit 2 ;; esac
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done
mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
for p in "${changed[@]}"; do
  case "${p}" in
    packages/kde/${NODE}/*|scripts/run-kde-tier1-package-batch10-preflight.sh|scripts/audit-kde-development-contract.py|scripts/kde-tier1-package-batch10-needed.sh|.github/workflows/kde-tier1-package-batch10.yml)
      exit 0 ;;
  esac
  if [[ "${NODE}" == kquickcharts && "${p}" == packages/kde/kirigami/* ]]; then exit 0; fi
done
CAMPAIGN="manifests/kde-tier1-package-campaign-batch10.json"
if printf '%s
' "${changed[@]}" | grep -Fxq "${CAMPAIGN}"; then
  git cat-file -e "${BEFORE}:${CAMPAIGN}" 2>/dev/null || exit 0
  if ! python3 - "${NODE}" "${BEFORE}" "${AFTER}" <<'PY2'
import json,subprocess,sys
node,before,after=sys.argv[1:]
def load(ref): return json.loads(subprocess.check_output(['git','show',f'{ref}:manifests/kde-tier1-package-campaign-batch10.json'],text=True))
def clean_node(n):
 ignore={'state','last_result','downstream_eligible','pass_evidence','last_failure_evidence','last_pass_files'}
 return {k:v for k,v in n.items() if k not in ignore}
def fp(d):
 s=d['shared_predecessors']; n=d['nodes'][node]
 x={'schema':d['schema'],'frameworks':d['frameworks_series'],'authority':d['authority'],'provider':d['provider_platform'],'lane':d['lane'],'selected':tuple(d['selected_nodes']),'ecm':s['extra_cmake_modules'],'trees':s['packaging_trees'],'contracts':s['binary_contracts'],'node':clean_node(n)}
 if node=='kquickcharts':
  k=d['nodes']['kirigami']; x['kirigami_package_contract']={'version':k['package_version'],'source_sha256':k['source_sha256'],'binary_contracts':k['binary_contracts'],'qml_contracts':k['qml_contracts']}
 return x
raise SystemExit(0 if fp(load(before))==fp(load(after)) else 1)
PY2
  then exit 0; fi
fi
# Attempts, result-only evidence, canonical promotion and documentation are not build inputs.
exit 1

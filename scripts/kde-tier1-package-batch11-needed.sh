#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$#" -eq 3 ]] || { echo "Usage: $0 <node> <before-sha> <after-sha>" >&2; exit 2; }
NODE="$1"; BEFORE="$2"; AFTER="$3"
case "${NODE}" in kuserfeedback|prison) ;; *) exit 2 ;; esac
for sha in "${BEFORE}" "${AFTER}"; do [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2; git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2; done
mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
for p in "${changed[@]}"; do
  case "${p}" in
    packages/kde/${NODE}/*|scripts/run-kde-tier1-package-batch11-preflight.sh|scripts/audit-kde-development-contract.py|scripts/kde-tier1-package-batch11-needed.sh|.github/workflows/kde-tier1-package-batch11.yml) exit 0 ;;
  esac
done
CAMPAIGN="manifests/kde-tier1-package-campaign-batch11.json"
if printf '%s\n' "${changed[@]}" | grep -Fxq "${CAMPAIGN}"; then
  git cat-file -e "${BEFORE}:${CAMPAIGN}" 2>/dev/null || exit 0
  if ! python3 - "${NODE}" "${BEFORE}" "${AFTER}" <<'PY'
import json,subprocess,sys
node,before,after=sys.argv[1:]; path='manifests/kde-tier1-package-campaign-batch11.json'
def load(ref): return json.loads(subprocess.check_output(['git','show',f'{ref}:{path}'],text=True))
def clean(n):
 ignore={'state','last_result','downstream_eligible','pass_evidence','last_failure_evidence','last_validation_incident','last_blocked_evidence','last_pass_files'}
 return {k:v for k,v in n.items() if k not in ignore}
def fp(d):
 s=d['shared_predecessors']
 return {'schema':d['schema'],'frameworks':d['frameworks_series'],'authority':d['authority'],'provider':d['provider_platform'],'lane':d['lane'],'selected':tuple(d['selected_nodes']),'ecm':s['extra_cmake_modules'],'trees':s['packaging_trees'],'node':clean(d['nodes'][node])}
raise SystemExit(0 if fp(load(before))==fp(load(after)) else 1)
PY
  then exit 0; fi
fi
exit 1

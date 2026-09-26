#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$#" -eq 3 ]] || { echo "Usage: $0 <node> <before-sha> <after-sha>" >&2; exit 2; }
NODE="$1"; BEFORE="$2"; AFTER="$3"
case "${NODE}" in kitemmodels|bluez-qt|kplotting) ;; *) echo "Unsupported Batch 3 node: ${NODE}" >&2; exit 2;; esac
for sha in "${BEFORE}" "${AFTER}"; do [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2; git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2; done
mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
for p in "${changed[@]}"; do
 case "$p" in
  packages/kde/"${NODE}"/*|scripts/run-kde-tier1-package-batch3-preflight.sh|.github/workflows/kde-tier1-package-batch3.yml) exit 0;;
 esac
done
if printf '%s\n' "${changed[@]}" | grep -Fxq manifests/kde-tier1-package-campaign-batch3.json; then
 if ! git cat-file -e "${BEFORE}:manifests/kde-tier1-package-campaign-batch3.json" 2>/dev/null; then exit 0; fi
 if ! python3 - "${BEFORE}" "${AFTER}" "${NODE}" <<'PY'
import json,subprocess,sys
b,a,n=sys.argv[1:]
def load(r): return json.loads(subprocess.check_output(['git','show',f'{r}:manifests/kde-tier1-package-campaign-batch3.json'],text=True))
def fp(d):
 x=d['nodes'][n]; e=d['shared_predecessors']['extra_cmake_modules']; t=d['shared_predecessors']['packaging_trees']; s=d['shared_packaging_inputs']['signing_key']; y=x['symbols']; c=x['copyright']
 return {'frameworks':d['frameworks_series'],'authority':d['authority'],'provider':d['provider_platform'],'ecm':[e['version'],e['deb_sha256']],'trees':t['snapshot_json_sha256'],'key':s['sha256'],'node':{k:x[k] for k in ('upstream_version','source_package','package_version','source_url','source_sha256','runtime_package','development_package','documentation_package','binary_contracts','soname','cmake_package','cmake_target','consumer_run')}|{'symbols':[y['file'],y['sha256'],y['tree_provider']],'copyright':c['sha256']}}
raise SystemExit(0 if fp(load(b))==fp(load(a)) else 1)
PY
 then exit 0; fi
fi
if printf '%s\n' "${changed[@]}" | grep -Fxq scripts/kde-tier1-package-batch3-needed.sh; then
 state="$(python3 - "${AFTER}" "${NODE}" <<'PY'
import json,subprocess,sys
d=json.loads(subprocess.check_output(['git','show',f'{sys.argv[1]}:manifests/kde-tier1-package-campaign-batch3.json'],text=True)); print(d['nodes'][sys.argv[2]]['state'])
PY
)"
 [[ "${state}" == PASS ]] || exit 0
fi
exit 1

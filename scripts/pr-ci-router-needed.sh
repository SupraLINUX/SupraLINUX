#!/usr/bin/env bash
set -Eeuo pipefail
# Exit contract: 0 = reusable hosted CI required, 1 = Repository Policy only, any other status = classifier error.
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"; AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done
mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
(("${#changed[@]}" > 0)) || { echo "No changed paths; Repository Policy only."; exit 1; }

canonical_state_is_promotion_only() {
  local path="$1"
  git cat-file -e "${BEFORE}:${path}" 2>/dev/null || return 1
  git cat-file -e "${AFTER}:${path}" 2>/dev/null || return 1
  python3 - "${BEFORE}" "${AFTER}" "${path}" <<'PY'
import copy,json,subprocess,sys
before,after,path=sys.argv[1:]
def load(ref):
    return json.loads(subprocess.check_output(['git','show',f'{ref}:{path}'],text=True))
def norm(d):
    d=copy.deepcopy(d)
    d.pop('as_of',None)
    if path=='manifests/kde-frameworks-tier1.json':
        for node in d.get('nodes',[]):
            node.pop('state',None)
            node.pop('packaging',None)
    elif path=='manifests/kde-dag.json':
        d.pop('nodes',None)
        d.pop('ci_scope_incidents',None)
    elif path=='manifests/kde-tier1-global-discovery.json':
        for key in ('promoted_snapshot','lanes','nodes','next_actions'):
            d.pop(key,None)
    elif path=='manifests/kde-frameworks-tier1-packaging-tree-evidence.json':
        for key in ('status','evidence'):
            d.pop(key,None)
    else:
        raise SystemExit(1)
    return d
raise SystemExit(0 if norm(load(before))==norm(load(after)) else 1)
PY
}

canonical_tier2_is_planning_only() {
  local path="manifests/kde-frameworks-tier2.json"
  git cat-file -e "${BEFORE}:${path}" 2>/dev/null || return 1
  git cat-file -e "${AFTER}:${path}" 2>/dev/null || return 1
  python3 - "${BEFORE}" "${AFTER}" "${path}" <<'PY'
import copy,json,subprocess,sys
before,after,path=sys.argv[1:]
def load(ref):
    return json.loads(subprocess.check_output(['git','show',f'{ref}:{path}'],text=True))
def norm(data):
    data=copy.deepcopy(data)
    data.pop('as_of',None)
    for node in data.get('nodes',[]):
        node.pop('planning',None)
        if node.get('state') != 'PASS':
            node.pop('package_identity',None)
            node.pop('packaging',None)
    return data
raise SystemExit(0 if norm(load(before))==norm(load(after)) else 1)
PY
}

tier2_dependencies_are_unmaterialized_only() {
  local deps_path="manifests/kde-frameworks-tier2-dependencies.json"
  local tier_path="manifests/kde-frameworks-tier2.json"
  for ref in "${BEFORE}" "${AFTER}"; do
    git cat-file -e "${ref}:${deps_path}" 2>/dev/null || return 1
    git cat-file -e "${ref}:${tier_path}" 2>/dev/null || return 1
  done
  python3 - "${BEFORE}" "${AFTER}" "${deps_path}" "${tier_path}" <<'PY'
import json,subprocess,sys
before,after,deps_path,tier_path=sys.argv[1:]
def load(ref,path):
    return json.loads(subprocess.check_output(['git','show',f'{ref}:{path}'],text=True))
def active_ids(ref):
    tier=load(ref,tier_path)
    ids=set()
    for node in tier.get('nodes',[]):
        planning=node.get('planning',{})
        if node.get('state') == 'PASS' or planning.get('package_contract') not in (None,'not-materialized'):
            ids.add(node['id'])
    return ids
ids=active_ids(before)|active_ids(after)
bd=load(before,deps_path).get('nodes',{})
ad=load(after,deps_path).get('nodes',{})
raise SystemExit(0 if {i:bd.get(i) for i in ids} == {i:ad.get(i) for i in ids} else 1)
PY
}

campaign_is_evidence_only() {
  local path="$1" batch selector rc node
  local -a nodes=()
  batch="${path#manifests/kde-tier1-package-campaign-batch}"; batch="${batch%.json}"
  [[ "${batch}" =~ ^[0-9]+$ ]] || return 1
  selector="scripts/kde-tier1-package-batch${batch}-needed.sh"
  [[ -f "${selector}" ]] || return 1
  mapfile -t nodes < <(python3 - "${AFTER}" "${path}" <<'PY'
import json,subprocess,sys
ref,path=sys.argv[1:]
d=json.loads(subprocess.check_output(['git','show',f'{ref}:{path}'],text=True))
for node in d.get('selected_nodes',[]): print(node)
PY
  )
  (("${#nodes[@]}" > 0)) || return 1
  for node in "${nodes[@]}"; do
    if bash "${selector}" "${node}" "${BEFORE}" "${AFTER}"; then return 1
    else rc=$?; [[ "${rc}" -eq 1 ]] || return 1
    fi
  done
  return 0
}

for path in "${changed[@]}"; do
  case "${path}" in
    docs/*|README.md|scripts/validate_*.py|scripts/test-*.sh|scripts/compile_kde_tier2_campaign.py|manifests/kde-tier1-package-batch*-attempts.json|manifests/kde-tier2-campaign-plan.json|.github/workflows/repository-policy.yml) continue ;;
    manifests/kde-frameworks-tier2.json)
      if canonical_tier2_is_planning_only; then continue; fi
      echo "${path}: canonical Tier 2 build identity changed; reusable hosted CI required."; exit 0 ;;
    manifests/kde-frameworks-tier2-dependencies.json)
      if tier2_dependencies_are_unmaterialized_only; then continue; fi
      echo "${path}: materialized/retained Tier 2 dependency input changed; reusable hosted CI required."; exit 0 ;;
    .github/workflows/kde-tier2-provider-audit.yml|scripts/run-kde-tier2-provider-audit.sh|scripts/kde-tier2-provider-audit-needed.sh)
      continue ;;
    .github/workflows/kde-tier2-contract-reference.yml|scripts/run-kde-tier2-contract-reference-snapshot.sh|scripts/kde-tier2-contract-reference-needed.sh|manifests/kde-tier2-package-contracts.json)
      continue ;;
    .github/workflows/kde-tier2-package-materialization.yml|scripts/materialize_kde_tier2_package.py|scripts/run-kde-tier2-package-materialization.sh|scripts/kde-tier2-materialization-needed.sh)
      continue ;;
    .github/workflows/kde-tier2-package-batch2.yml|scripts/run-kde-tier2-package-batch2.sh|scripts/plan-kde-tier2-package-batch2.py|scripts/kde-tier2-package-batch2-needed.sh|manifests/kde-tier2-package-campaign-batch2.json|manifests/kde-tier2-package-batch2-attempts.json)
      continue ;;
    manifests/kde-tier1-package-campaign-batch*.json)
      if campaign_is_evidence_only "${path}"; then continue; fi
      echo "${path}: semantic package input changed; reusable hosted CI required."; exit 0 ;;
    manifests/kde-frameworks-tier1.json|manifests/kde-dag.json|manifests/kde-tier1-global-discovery.json|manifests/kde-frameworks-tier1-packaging-tree-evidence.json)
      if canonical_state_is_promotion_only "${path}"; then continue; fi
      echo "${path}: canonical build identity changed; reusable hosted CI required."; exit 0 ;;
    *) echo "${path}: build/reference/provider input may have changed; reusable hosted CI required."; exit 0 ;;
  esac
done
echo "Event delta is evidence/policy-only; reusable hosted CI fan-out is skipped."
exit 1

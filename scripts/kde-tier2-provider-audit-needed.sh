#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$#" -eq 2 ]] || { echo "Usage: $0 <before-sha> <after-sha>" >&2; exit 2; }
BEFORE="$1"
AFTER="$2"
for sha in "${BEFORE}" "${AFTER}"; do
    [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
    git -C "${ROOT}" cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

audit_status() {
    git -C "${ROOT}" show "$1:manifests/kde-frameworks-tier2-dependencies.json" |
        python3 -c 'import json,sys; print(json.load(sys.stdin).get("provider_audit",{}).get("status",""))'
}

audit_nodes() {
    git -C "${ROOT}" show "$1:manifests/kde-frameworks-tier2-dependencies.json" |
        python3 -c 'import json,sys; print(",".join(json.load(sys.stdin).get("provider_audit",{}).get("nodes",[])))'
}

audit_fingerprint() {
    git -C "${ROOT}" show "$1:manifests/kde-frameworks-tier2-dependencies.json" |
        python3 -c 'import hashlib,json,sys
d=json.load(sys.stdin)
a=d.get("provider_audit",{})
nodes=a.get("nodes",[])
v={
 "batch":a.get("batch"),
 "nodes":nodes,
 "source_authority":a.get("source_authority"),
 "provider_platform":a.get("provider_platform"),
 "registry":d.get("provider_registry",{}),
 "profiles":{n:{k:d.get("nodes",{}).get(n,{}).get(k) for k in ("frameworks","qt","external","selected_linux_profile")} for n in nodes},
}
print(hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest())'
}

mapfile -t changed < <(git -C "${ROOT}" diff --name-only "${BEFORE}" "${AFTER}" --)
after_status="$(audit_status "${AFTER}")"

for path in "${changed[@]}"; do
    case "${path}" in
        manifests/kde-frameworks-tier2-dependencies.json)
            if ! git -C "${ROOT}" cat-file -e "${BEFORE}:${path}" 2>/dev/null; then
                echo "Tier 2 provider-audit manifest is new."
                exit 0
            fi
            if [[ "$(audit_fingerprint "${BEFORE}")" != "$(audit_fingerprint "${AFTER}")" ]]; then
                echo "Tier 2 provider-audit semantic profile changed."
                exit 0
            fi
            echo "Tier 2 provider-audit manifest changed only in state/evidence; no provider rerun required."
            ;;
        scripts/run-kde-tier2-provider-audit.sh|scripts/kde-tier2-provider-audit-needed.sh|.github/workflows/kde-tier2-provider-audit.yml)
            if [[ "${after_status}" == "pending-ci" ]]; then
                echo "${path}: active provider-audit execution input changed."
                exit 0
            fi
            ;;
    esac
done

if printf '%s\n' "${changed[@]}" | grep -Fxq "manifests/kde-tier2-campaign-plan.json"; then
    after_batch="$(git -C "${ROOT}" show "${AFTER}:manifests/kde-tier2-campaign-plan.json" | python3 -c 'import json,sys; print(",".join(json.load(sys.stdin).get("next_provider_audit_batch",[])))')"
    if [[ "${after_status}" == "pending-ci" && "$(audit_nodes "${AFTER}")" == "${after_batch}" ]]; then
        echo "Active provider-audit batch matches changed campaign queue."
        exit 0
    fi
fi

echo "No active Tier 2 provider-audit input changed."
exit 1

#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 3 ]]; then
    printf 'Usage: %s <node> <before-sha> <after-sha>\n' "$0" >&2
    exit 2
fi

NODE="$1"
BEFORE="$2"
AFTER="$3"

case "${NODE}" in
    kcodecs|kdbusaddons|threadweaver) ;;
    *)
        printf 'Unsupported Tier 1 batch node: %s\n' "${NODE}" >&2
        exit 2
        ;;
esac

for sha in "${BEFORE}" "${AFTER}"; do
    [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || {
        printf 'Invalid commit SHA: %s\n' "${sha}" >&2
        exit 2
    }
    git cat-file -e "${sha}^{commit}" 2>/dev/null || {
        printf 'Commit is not available locally: %s\n' "${sha}" >&2
        exit 2
    }
done

mapfile -t changed_paths < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
printf 'Changed paths for Tier 1 batch node %s:\n' "${NODE}"
printf '  %s\n' "${changed_paths[@]:-<none>}"

for path in "${changed_paths[@]}"; do
    case "${path}" in
        packages/kde/"${NODE}"/*)
            printf 'Node packaging/consumer changed for %s: %s\n' "${NODE}" "${path}"
            exit 0
            ;;
        scripts/run-kde-tier1-package-preflight.sh|.github/workflows/kde-tier1-package-preflight.yml)
            printf 'Shared package runner/workflow changed for %s: %s\n' "${NODE}" "${path}"
            exit 0
            ;;
    esac
done

if printf '%s\n' "${changed_paths[@]}" | grep -Fxq 'manifests/kde-tier1-package-campaign.json'; then
    if ! git cat-file -e "${BEFORE}:manifests/kde-tier1-package-campaign.json" 2>/dev/null; then
        printf 'Campaign manifest is new; %s requires a build.\n' "${NODE}"
        exit 0
    fi
    if ! python3 - "${BEFORE}" "${AFTER}" "${NODE}" <<'PY'
import json
import subprocess
import sys

before, after, node_id = sys.argv[1:]

def load(ref):
    raw = subprocess.check_output(
        ["git", "show", f"{ref}:manifests/kde-tier1-package-campaign.json"],
        text=True,
    )
    return json.loads(raw)

def fingerprint(data):
    node = dict(data["nodes"][node_id])
    for key in ("state", "last_result", "evidence", "downstream_eligible", "pass_files"):
        node.pop(key, None)
    return {
        "frameworks_series": data.get("frameworks_series"),
        "authority": data.get("authority"),
        "provider_platform": data.get("provider_platform"),
        "shared_predecessors": data.get("shared_predecessors"),
        "shared_packaging_inputs": data.get("shared_packaging_inputs"),
        "node": node,
    }

raise SystemExit(0 if fingerprint(load(before)) == fingerprint(load(after)) else 1)
PY
    then
        printf 'Build-relevant campaign inputs changed for %s.\n' "${NODE}"
        exit 0
    fi
    printf 'Campaign change for %s is state/evidence-only; no rebuild required.\n' "${NODE}"
fi

if printf '%s\n' "${changed_paths[@]}" | grep -Fxq 'scripts/kde-tier1-package-preflight-needed.sh'; then
    state="$(python3 - "${AFTER}" "${NODE}" <<'PY'
import json
import subprocess
import sys
ref, node = sys.argv[1:]
data = json.loads(subprocess.check_output(
    ["git", "show", f"{ref}:manifests/kde-tier1-package-campaign.json"],
    text=True,
))
print(data["nodes"][node]["state"])
PY
)"
    if [[ "${state}" != "PASS" ]]; then
        printf 'Scope implementation changed and %s is not PASS; rebuild required.\n' "${NODE}"
        exit 0
    fi
    printf 'Scope implementation changed but %s is already PASS and no build input changed; skip.\n' "${NODE}"
fi

printf 'No Tier 1 package-build-relevant change for %s in this event delta.\n' "${NODE}"
exit 1

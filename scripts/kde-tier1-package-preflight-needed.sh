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
    [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || { printf 'Invalid commit SHA: %s\n' "${sha}" >&2; exit 2; }
    git cat-file -e "${sha}^{commit}" 2>/dev/null || { printf 'Commit is not available locally: %s\n' "${sha}" >&2; exit 2; }
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

campaign_changed=false
if printf '%s\n' "${changed_paths[@]}" | grep -Fxq 'manifests/kde-tier1-package-campaign.json'; then
    campaign_changed=true
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
    return json.loads(subprocess.check_output(
        ["git", "show", f"{ref}:manifests/kde-tier1-package-campaign.json"],
        text=True,
    ))

def fingerprint(data):
    node = data["nodes"][node_id]
    ecm = data["shared_predecessors"]["extra_cmake_modules"]
    trees = data["shared_predecessors"]["packaging_trees"]
    signing = data["shared_packaging_inputs"]["signing_key"]
    symbols = node["symbols"]
    copyright_meta = node["copyright"]
    return {
        "frameworks_series": data["frameworks_series"],
        "authority": data["authority"],
        "provider_platform": data["provider_platform"],
        "ecm_version": ecm["version"],
        "ecm_deb_sha256": ecm["deb_sha256"],
        "tree_snapshot_sha256": trees["snapshot_json_sha256"],
        "signing_key_sha256": signing["sha256"],
        "node": {
            "upstream_version": node["upstream_version"],
            "source_package": node["source_package"],
            "package_version": node["package_version"],
            "source_url": node["source_url"],
            "source_sha256": node["source_sha256"],
            "symbols_file": symbols["file"],
            "symbols_sha256": symbols["sha256"],
            "symbols_tree_provider": symbols["tree_provider"],
            "copyright_sha256": copyright_meta["sha256"],
            "runtime_package": node["runtime_package"],
            "development_package": node["development_package"],
            "documentation_package": node["documentation_package"],
            "binary_contracts": node["binary_contracts"],
            "soname": node["soname"],
            "consumer_run": node["consumer_run"],
        },
    }

raise SystemExit(0 if fingerprint(load(before)) == fingerprint(load(after)) else 1)
PY
    then
        printf 'Build-relevant campaign inputs changed for %s.\n' "${NODE}"
        exit 0
    fi
    printf 'Campaign change for %s is state/evidence/descriptive-only; no rebuild required.\n' "${NODE}"
fi

if printf '%s\n' "${changed_paths[@]}" | grep -Fxq 'scripts/kde-tier1-package-preflight-needed.sh'; then
    state="$(python3 - "${AFTER}" "${NODE}" <<'PY'
import json, subprocess, sys
ref, node = sys.argv[1:]
data = json.loads(subprocess.check_output(
    ["git", "show", f"{ref}:manifests/kde-tier1-package-campaign.json"], text=True))
print(data["nodes"][node]["state"])
PY
)"
    if [[ "${state}" != "PASS" ]]; then
        printf 'Scope implementation changed and %s is not PASS; rebuild required.\n' "${NODE}"
        exit 0
    fi
    printf 'Scope implementation changed but %s is already PASS and no consumed build input changed; skip.\n' "${NODE}"
fi

if [[ "${campaign_changed}" == true ]]; then
    printf 'Only non-build campaign metadata changed for %s.\n' "${NODE}"
fi
printf 'No Tier 1 package-build-relevant change for %s in this event delta.\n' "${NODE}"
exit 1

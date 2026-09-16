#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$#" -eq 3 ]] || { echo "Usage: $0 <node> <before-sha> <after-sha>" >&2; exit 2; }
NODE="$1"; BEFORE="$2"; AFTER="$3"
case "${NODE}" in
  kcalendarcore|kcoreaddons|kwidgetsaddons) ;;
  *) echo "Unsupported Batch 7 node: ${NODE}" >&2; exit 2 ;;
esac
for sha in "${BEFORE}" "${AFTER}"; do
  [[ "${sha}" =~ ^[0-9a-fA-F]{40}$ ]] || exit 2
  git cat-file -e "${sha}^{commit}" 2>/dev/null || exit 2
done

mapfile -t changed < <(git diff --name-only "${BEFORE}" "${AFTER}" --)
for p in "${changed[@]}"; do
  case "${p}" in
    packages/kde/"${NODE}"/*|scripts/run-kde-tier1-package-batch7-preflight.sh|.github/workflows/kde-tier1-package-batch7.yml)
      exit 0 ;;
  esac
done

CAMPAIGN="manifests/kde-tier1-package-campaign-batch7.json"
if printf '%s\n' "${changed[@]}" | grep -Fxq "${CAMPAIGN}"; then
  git cat-file -e "${BEFORE}:${CAMPAIGN}" 2>/dev/null || exit 0
  if ! python3 - "${BEFORE}" "${AFTER}" "${NODE}" <<'PY2'
import json
import subprocess
import sys

before, after, node = sys.argv[1:]

def load(ref):
    return json.loads(subprocess.check_output(
        ["git", "show", f"{ref}:manifests/kde-tier1-package-campaign-batch7.json"],
        text=True,
    ))

def fingerprint(data):
    if data.get("schema") != 2:
        raise SystemExit(1)
    selected = tuple(data.get("selected_nodes", []))
    if node not in selected:
        raise SystemExit(1)
    n = data["nodes"][node]
    shared = data["shared_predecessors"]
    ecm = shared["extra_cmake_modules"]
    trees = shared["packaging_trees"]
    py = shared["python_wheel_backend_provider"]
    keys = (
        "upstream_version", "source_package", "package_version", "source_url",
        "source_sha256", "runtime_package", "python_package", "python_module",
        "soname", "binary_contracts", "dependency_contracts",
        "recommendation_contracts", "upstream_defaults", "symbols",
        "copyright", "signing_key",
    )
    return {
        "schema": data["schema"],
        "frameworks": data["frameworks_series"],
        "authority": data["authority"],
        "provider": data["provider_platform"],
        "selected_nodes": selected,
        "ecm": [ecm["version"], ecm["deb_sha256"]],
        "packaging_tree": trees["snapshot_json_sha256"],
        "python_backend": [py["package"], py["version"], py["backend_module"]],
        "node": {k: n[k] for k in keys},
    }

raise SystemExit(0 if fingerprint(load(before)) == fingerprint(load(after)) else 1)
PY2
  then
    exit 0
  fi
fi

# The append-only attempt ledger and planning/result metadata do not alter the
# package build contract. They therefore do not trigger an expensive rebuild.
exit 1

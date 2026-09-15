#!/usr/bin/env bash
set -Eeuo pipefail

BEFORE="${1:?before SHA required}"
AFTER="${2:?after SHA required}"

# ECM package preflight is intentionally scoped to inputs consumed by the
# package lane itself. Canonical DAG state/evidence and documentation do not
# change the artifact built by run-kde-ecm-package-preflight.sh and therefore
# must not request a rebuild.
#
# In particular, these are state/documentation-only and are NOT build inputs:
#   manifests/kde-dag.json
#   docs/kde-dag.md
#   scripts/kde-ecm-preflight-needed.sh

mapfile -t CHANGED < <(
    git diff --name-only "${BEFORE}" "${AFTER}" -- \
        'packages/kde/extra-cmake-modules/*' \
        'scripts/run-kde-ecm-package-preflight.sh' \
        '.github/workflows/kde-ecm-package-preflight.yml'
)

if (( ${#CHANGED[@]} > 0 )); then
    printf 'run=true\n'
    printf 'reason=ECM package-consumed input changed\n'
    printf 'changed=%s\n' "$(IFS=,; printf '%s' "${CHANGED[*]}")"
else
    printf 'run=false\n'
    printf 'reason=event delta changes no ECM package-consumed input; skip rebuild\n'
    printf 'changed=\n'
fi

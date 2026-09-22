#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests" "${TMP}/.github/workflows"
cp "${ROOT}/scripts/kde-tier3-materialization-needed.sh" "${TMP}/scripts/"
cat > "${TMP}/manifests/kde-tier3-materialization.json" <<'JSON'
{"state":"PASS","frameworks_series":"6.30.0","contract_manifest":"c","canonical_manifest":"t","source_policy":"x","selected_nodes":["x"],"common_adaptations":{"x":1},"nodes":{"x":{"state":"materialized","evidence":{"result":"PASS"}}}}
JSON
cat > "${TMP}/manifests/kde-tier3-package-contracts.json" <<'JSON'
{"contract_decision":{"status":"PASS","materialization_authorized":true,"package_build_authorized":false},"provider_adaptations":{},"nodes":{"x":{"source_package":"kf6-x","upstream_version":"6.30.0","source_sha256":"a","package_version_candidate":"6.30.0-0supralinux1","packaging_baseline":{"tree_sha256":"b"},"target_binary_packages":["x"],"supralinux_additional_binary_packages":[],"selected_profile":{"BUILD_TESTING":true},"technical_references":{"debian":{"version":"6.30.0-1"}}}}}
JSON
cat > "${TMP}/manifests/kde-frameworks-tier3.json" <<'JSON'
{"nodes":[{"id":"x","source_url":"https://example.invalid/x.tar.xz","source_sha256":"a"}]}
JSON
echo script > "${TMP}/scripts/materialize_kde_tier3_package.py"
echo workflow > "${TMP}/.github/workflows/kde-tier3-materialization.yml"
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add . && git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"

python3 - "${TMP}/manifests/kde-tier3-materialization.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["x"]["evidence"]["workflow_run"]=1; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm evidence
EV="$(git -C "${TMP}" rev-parse HEAD)"
set +e
bash "${TMP}/scripts/kde-tier3-materialization-needed.sh" "${BASE}" "${EV}"
rc=$?
set -e
[[ "${rc}" -eq 1 ]]

python3 - "${TMP}/manifests/kde-tier3-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["x"]["package_version_candidate"]="6.30.0-0supralinux2"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm semantic
SEM="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-materialization-needed.sh" "${EV}" "${SEM}"
echo "Tier 3 materialization semantic scope: PASS"

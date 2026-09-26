#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests" "${TMP}/.github/workflows"
cp "${ROOT}/scripts/kde-tier3-support-materialization-needed.sh" "${TMP}/scripts/"
cat > "${TMP}/manifests/kde-tier3-support-materialization.json" <<'JSON'
{"state":"PASS","frameworks_series":"6.30.0","contract_manifest":"x","selected_nodes":["x"],"common_adaptations":{"x":1},"nodes":{"x":{"state":"materialized","source_package":"x","upstream_version":"6.30.0","upstream_source_sha256":"a","packaging_reference_version":"1","packaging_reference_tree_sha256":"b","package_version":"2","expected_binary_packages":["x"],"evidence":{"result":"PASS"}}}}
JSON
echo script > "${TMP}/scripts/materialize-kde-tier3-support-package.sh"
echo workflow > "${TMP}/.github/workflows/kde-tier3-support-materialization.yml"
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add . && git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"
python3 - "${TMP}/manifests/kde-tier3-support-materialization.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["x"]["evidence"]["workflow_run"]=1; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm evidence
EV="$(git -C "${TMP}" rev-parse HEAD)"
set +e; bash "${TMP}/scripts/kde-tier3-support-materialization-needed.sh" "${BASE}" "${EV}"; rc=$?; set -e
[[ "${rc}" -eq 1 ]]
python3 - "${TMP}/manifests/kde-tier3-support-materialization.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["x"]["package_version"]="3"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm semantic
SEM="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-support-materialization-needed.sh" "${EV}" "${SEM}"
echo "Tier 3 support materialization semantic scope: PASS"

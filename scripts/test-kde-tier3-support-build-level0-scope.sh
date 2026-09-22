#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests"
cp "${ROOT}/scripts/kde-tier3-support-build-level0-needed.sh" "${TMP}/scripts/"
cat > "${TMP}/manifests/kde-tier3-support-build-level0.json" <<'JSON'
{"frameworks_series":"6.30.0","selected_nodes":["x"],"materialization_manifest":"m","shared_predecessors":{},"retained_predecessors":{},"nodes":{"x":{"state":"PASS","source_package":"x","upstream_version":"6.30.0","package_version":"1","runtime_package":"r","dev_package":"d","soname":"s","cmake_package":"c","cmake_target":"t","expected_binary_packages":["r","d"],"materialization":{"artifact_id":1},"predecessors":[],"test_policy":"p","payload_contract":"q","pass_evidence":{"result":"PASS"}}}}
JSON
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add .
git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"
python3 - "${TMP}/manifests/kde-tier3-support-build-level0.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["x"]["pass_evidence"]["artifact_id"]=9; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm evidence
EV="$(git -C "${TMP}" rev-parse HEAD)"
set +e; bash "${TMP}/scripts/kde-tier3-support-build-level0-needed.sh" "${BASE}" "${EV}"; rc=$?; set -e
[[ "${rc}" -eq 1 ]]
python3 - "${TMP}/manifests/kde-tier3-support-build-level0.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["x"]["state"]="remediation-pending-build"; d["nodes"]["x"]["package_version"]="2"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm semantic
SEM="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-support-build-level0-needed.sh" "${EV}" "${SEM}"
echo "Tier 3 support level0 semantic scope: PASS"

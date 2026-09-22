#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests"
cp "${ROOT}/scripts/kde-tier3-support-build-level1-needed.sh" "${TMP}/scripts/"
cat > "${TMP}/manifests/kde-tier3-support-build-level1.json" <<'JSON'
{"frameworks_series":"6.30.0","selected_nodes":["kded"],"materialization_manifest":"m","level0_manifest":"l0","shared_predecessors":{},"retained_predecessors":{},"package_dependency_closure":{},"nodes":{"kded":{"state":"PASS","source_package":"kf6-kded","upstream_version":"6.30.0","package_version":"1","expected_binary_packages":["kded6","kded6-dev"],"materialization":{"artifact_id":1},"direct_predecessors":[],"package_dependency_closure":[],"test_policy":"p","executable_contract":"usr/bin/kded6","cmake_package":"KF6KDED","cmake_variable":"KDED_DBUS_INTERFACE","payload_contract":"q","pass_evidence":{"result":"PASS"}}}}
JSON
cat > "${TMP}/manifests/kde-tier3-support-build-level1-attempts.json" <<'JSON'
{"schema":1,"batch":"tier3-support-build-level1","nodes":{"kded":[{"result":"PASS"}]}}
JSON
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add . && git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"
python3 - "${TMP}/manifests/kde-tier3-support-build-level1.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["kded"]["pass_evidence"]["artifact_id"]=9; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm evidence
EV="$(git -C "${TMP}" rev-parse HEAD)"
set +e; bash "${TMP}/scripts/kde-tier3-support-build-level1-needed.sh" "${BASE}" "${EV}"; rc=$?; set -e
[[ "${rc}" -eq 1 ]]
python3 - "${TMP}/manifests/kde-tier3-support-build-level1.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["nodes"]["kded"]["state"]="remediation-pending-build"; d["nodes"]["kded"]["package_version"]="2"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm semantic
SEM="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-support-build-level1-needed.sh" "${EV}" "${SEM}"
echo "Tier 3 support level1 semantic scope: PASS"

#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests" "${TMP}/.github/workflows"
cp "${ROOT}/scripts/kde-tier3-provider-audit-needed.sh" "${TMP}/scripts/"
cat > "${TMP}/manifests/kde-tier3-provider-audit.json" <<'JSON'
{"status":"PASS","authority":"kde-upstream","frameworks_series":"6.30.0","release_reference":"https://kde.org/info/kde-frameworks-6.30.0/","provider_platform":"ubuntu-resolute","selected_nodes":["x"],"platform_contract":{"qt_minimum":"6.9.0"},"components":{"x":{"required_upstream_version":"6.30.0","kde_source_url":"u","kde_source_sha256":"s","ubuntu_source_package":"kf6-x","provider_decision":"supralinux-required"}},"execution_request":{"status":"consumed"},"evidence":{"result":"PASS"}}
JSON
echo run > "${TMP}/scripts/run-kde-tier3-provider-audit.sh"
echo wf > "${TMP}/.github/workflows/kde-tier3-provider-audit.yml"
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add . && git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"

python3 - "${TMP}/manifests/kde-tier3-provider-audit.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["evidence"]={"result":"PASS","workflow_run":1}; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm evidence
EV="$(git -C "${TMP}" rev-parse HEAD)"
set +e; bash "${TMP}/scripts/kde-tier3-provider-audit-needed.sh" "${BASE}" "${EV}"; rc=$?; set -e
[[ "${rc}" -eq 1 ]]

python3 - "${TMP}/manifests/kde-tier3-provider-audit.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["execution_request"]={"status":"requested"}; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm request
REQ="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-provider-audit-needed.sh" "${EV}" "${REQ}"

python3 - "${TMP}/manifests/kde-tier3-provider-audit.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["execution_request"]["status"]="consumed"; d["components"]["x"]["required_upstream_version"]="6.31.0"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm semantic
SEM="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-provider-audit-needed.sh" "${REQ}" "${SEM}"

echo "Tier 3 provider-audit semantic scope: PASS"

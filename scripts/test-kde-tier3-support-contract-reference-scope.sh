#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests"
cp "${ROOT}/scripts/kde-tier3-support-contract-reference-needed.sh" "${TMP}/scripts/"
cat > "${TMP}/manifests/kde-tier3-support-package-contracts.json" <<'JSON'
{"frameworks_series":"6.30.0","selected_components":["x"],"provider_audit":{"required_status":"PASS","selected_provider":"supralinux"},"state":"reference-capture-pass","reference_capture":{"ubuntu_suite":"resolute","debian_suite":"sid","debian_selection_policy":"prefer-exact-kde-6.30.0-otherwise-newest-not-newer","status":"PASS","evidence":{"result":"PASS"}},"components":{"x":{"upstream_source":"x","upstream_version":"6.30.0","upstream_source_sha256":"abc","reference_sources":{"ubuntu":"x","debian":"x"},"contract_state":"reference-capture-pass"}}}
JSON
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add .
git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"

python3 - "${TMP}/manifests/kde-tier3-support-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["reference_capture"]["evidence"]["workflow_run"]=1; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add .
git -C "${TMP}" commit -qm evidence
EV="$(git -C "${TMP}" rev-parse HEAD)"
set +e
bash "${TMP}/scripts/kde-tier3-support-contract-reference-needed.sh" "${BASE}" "${EV}"
rc=$?
set -e
[[ "${rc}" -eq 1 ]]

python3 - "${TMP}/manifests/kde-tier3-support-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["components"]["x"]["reference_sources"]["debian"]="y"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add .
git -C "${TMP}" commit -qm semantic
SEM="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-support-contract-reference-needed.sh" "${EV}" "${SEM}"

echo "Tier 3 support contract-reference semantic scope: PASS"

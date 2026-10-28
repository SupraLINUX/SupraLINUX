#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests"
cp "${ROOT}/scripts/kde-tier3-contract-reference-needed.sh" "${TMP}/scripts/"
cat > "${TMP}/manifests/kde-tier3-package-contracts.json" <<'JSON'
{"state":"reference-capture-pass","frameworks_series":"6.30.0","selected_nodes":["x"],"compatibility_reference":{"ubuntu":{"series":"resolute"},"debian":{"series":"sid"}},"reference_capture":{"ubuntu_suite":"resolute","debian_suite":"sid","selection_policy":"p"},"nodes":{"x":{"upstream_version":"6.30.0","source_sha256":"a","source_package":"kf6-x"}},"execution_request":{"status":"consumed"}}
JSON
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add . && git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"
python3 - "${TMP}/manifests/kde-tier3-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["evidence_only"]=1; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm evidence
EV="$(git -C "${TMP}" rev-parse HEAD)"
set +e; bash "${TMP}/scripts/kde-tier3-contract-reference-needed.sh" "${BASE}" "${EV}"; rc=$?; set -e
[[ "${rc}" -eq 1 ]]
python3 - "${TMP}/manifests/kde-tier3-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["state"]="reference-capture-pending"; d["execution_request"]={"status":"requested"}; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm request
REQ="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-contract-reference-needed.sh" "${EV}" "${REQ}"
echo "Tier 3 package-contract reference semantic scope: PASS"

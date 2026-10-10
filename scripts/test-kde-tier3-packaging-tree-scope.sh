#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests"
cp "${ROOT}/scripts/kde-tier3-packaging-tree-needed.sh" "${TMP}/scripts/"
cat > "${TMP}/manifests/kde-tier3-package-contracts.json" <<'JSON'
{"selected_nodes":["x"],"nodes":{"x":{"technical_references":{"ubuntu":{"version":"1"},"debian":{"version":"2"}}}},"packaging_tree_capture":{"status":"PASS","execution_request":{"status":"consumed"},"selected_sides":["ubuntu","debian"],"claim":"technical-packaging-tree-only","authoritative":false}}
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
set +e; bash "${TMP}/scripts/kde-tier3-packaging-tree-needed.sh" "${BASE}" "${EV}"; rc=$?; set -e
[[ "${rc}" -eq 1 ]]
python3 - "${TMP}/manifests/kde-tier3-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["packaging_tree_capture"]["status"]="pending-ci"; d["packaging_tree_capture"]["execution_request"]={"status":"requested"}; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm request
REQ="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-packaging-tree-needed.sh" "${EV}" "${REQ}"
echo "Tier 3 packaging-tree semantic scope: PASS"

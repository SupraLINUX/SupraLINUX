#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
mkdir -p "${TMP}/scripts" "${TMP}/manifests"
cp "${ROOT}/scripts/kde-tier3-support-packaging-tree-needed.sh" "${TMP}/scripts/"
cat > "${TMP}/manifests/kde-tier3-support-package-contracts.json" <<'JSON'
{"packaging_tree_capture":{"status":"PASS","selected_components":["x"],"selected_sides":["ubuntu","debian"],"evidence":{"result":"PASS"}},"technical_references":{"x":{"ubuntu":{"source_package":"x","version":"1","checksums_sha256":[{"file":"x.dsc","sha256":"a"},{"file":"x.debian.tar.xz","sha256":"b"},{"file":"x.orig.tar.xz","sha256":"c"}]},"debian":{"source_package":"x","version":"2","checksums_sha256":[{"file":"x.dsc","sha256":"d"},{"file":"x.debian.tar.xz","sha256":"e"},{"file":"x.orig.tar.xz","sha256":"f"}]}}}}
JSON
git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add .
git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"
python3 - "${TMP}/manifests/kde-tier3-support-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["packaging_tree_capture"]["evidence"]["workflow_run"]=1; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm evidence
EV="$(git -C "${TMP}" rev-parse HEAD)"
set +e; bash "${TMP}/scripts/kde-tier3-support-packaging-tree-needed.sh" "${BASE}" "${EV}"; rc=$?; set -e
[[ "${rc}" -eq 1 ]]
python3 - "${TMP}/manifests/kde-tier3-support-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["technical_references"]["x"]["debian"]["version"]="3"; open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm semantic
SEM="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-support-packaging-tree-needed.sh" "${EV}" "${SEM}"
echo "Tier 3 support packaging-tree semantic scope: PASS"

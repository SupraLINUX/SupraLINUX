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

# A selective remediation state is itself executable semantic scope.
python3 - "${TMP}/manifests/kde-tier3-materialization.json" "${TMP}/manifests/kde-tier3-package-contracts.json" <<'PY'
import json,sys
mp,cp=sys.argv[1:]
m=json.load(open(mp)); c=json.load(open(cp))
m["state"]="remediation-pending-ci"
m["remediation_queue"]=["x"]
m["remediation"]={"reason":"test-remediation","package_revision":"6.30.0-0supralinux2"}
m["nodes"]["x"]["state"]="remediation-pending"
m["nodes"]["x"]["candidate_package_version"]="6.30.0-0supralinux2"
c["nodes"]["x"]["package_version_candidate"]="6.30.0-0supralinux2"
c["nodes"]["x"]["source_build_relation_overrides"]=[{"field":"Build-Depends","action":"ensure","relation":"python3-build"}]
c["remediation"]={"status":"materialization-pending-ci"}
open(mp,"w").write(json.dumps(m)+"\n")
open(cp,"w").write(json.dumps(c)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm remediation
REM="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-materialization-needed.sh" "${SEM}" "${REM}"

# Once promoted back to PASS, a remediation-contract change must still alter
# the semantic fingerprint and request a new materialization run.
python3 - "${TMP}/manifests/kde-tier3-materialization.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p))
d["state"]="PASS"
d.pop("remediation_queue",None)
d.pop("remediation",None)
d["nodes"]["x"]["state"]="materialized"
d["nodes"]["x"].pop("candidate_package_version",None)
open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm remediation-pass
PASS2="$(git -C "${TMP}" rev-parse HEAD)"

# Promotion from remediation-pending-ci to PASS is evidence/lifecycle only when
# the package contracts and materialization inputs are unchanged.
set +e
bash "${TMP}/scripts/kde-tier3-materialization-needed.sh" "${REM}" "${PASS2}"
rc=$?
set -e
[[ "${rc}" -eq 1 ]]

# Editing only the selector does not alter the materialized source package.
echo "# selector-only-test" >> "${TMP}/scripts/kde-tier3-materialization-needed.sh"
git -C "${TMP}" add . && git -C "${TMP}" commit -qm selector-only
SELECTOR="$(git -C "${TMP}" rev-parse HEAD)"
set +e
bash "${TMP}/scripts/kde-tier3-materialization-needed.sh" "${PASS2}" "${SELECTOR}"
rc=$?
set -e
[[ "${rc}" -eq 1 ]]

python3 - "${TMP}/manifests/kde-tier3-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p))
d["nodes"]["x"]["source_build_relation_overrides"][0]["relation"]="python3-build (>= 1.0)"
open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm remediation-contract-change
REMCHANGE="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-materialization-needed.sh" "${SELECTOR}" "${REMCHANGE}"

# Symbols-template additions are source-materialization semantics too.
python3 - "${TMP}/manifests/kde-tier3-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p))
d["nodes"]["x"]["symbol_template_additions"]=[{
  "package":"libx1","soname":"libx.so.1","symbol":"_ZSt19piecewise_construct@Base",
  "minimal_version":"6.30.0","tags":["optional"]
}]
open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm symbol-addition
SYMBOLADD="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-materialization-needed.sh" "${REMCHANGE}" "${SYMBOLADD}"

echo "Tier 3 materialization remediation scope: PASS"


# Generic rules-text replacements are source-materialization semantics.
python3 - "${TMP}/manifests/kde-tier3-package-contracts.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p))
d["nodes"]["x"]["rules_text_replacements"]=[{
  "old":"ifneq (linux,$(DEB_HOST_ARCH_OS))",
  "new":"ifeq (linux,$(DEB_HOST_ARCH_OS))",
  "expected_count":1
}]
open(p,"w").write(json.dumps(d)+"\n")
PY
git -C "${TMP}" add . && git -C "${TMP}" commit -qm rules-text-replacement
RULESREPL="$(git -C "${TMP}" rev-parse HEAD)"
bash "${TMP}/scripts/kde-tier3-materialization-needed.sh" "${SYMBOLADD}" "${RULESREPL}"
echo "Tier 3 materialization rules-replacement scope: PASS"

#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

mkdir -p "${TMP}/scripts" "${TMP}/manifests" "${TMP}/.github/workflows" "${TMP}/docs"
cp "${ROOT}/scripts/kde-tier2-kmime-legacy-provider-needed.sh" "${TMP}/scripts/"

cat > "${TMP}/manifests/kde-tier2-kmime-legacy-provider.json" <<'JSON'
{
  "schema": 1,
  "state": "materialized",
  "source_reference": {"source_package":"kmime","ubuntu_version":"25.12.3-0ubuntu1"},
  "supralinux_package": {"package_version":"25.12.3-0ubuntu1+supralinux1"},
  "adaptation": {"new_dependency":"libkf6mime-data"},
  "build_evidence": {}
}
JSON

cat > "${TMP}/.github/workflows/kde-tier2-kmime-legacy-provider.yml" <<'YAML'
jobs:
  materialize:
    runs-on: ubuntu-26.04
    steps:
      - run: scripts/materialize-kde-tier2-kmime-legacy-provider.sh
  rootfs:
    runs-on: ubuntu-26.04
    steps:
      - run: echo rootfs
  build:
    needs: [materialize, rootfs]
    runs-on: ubuntu-26.04
    steps:
      - run: scripts/run-kde-tier2-kmime-legacy-provider-build.sh
YAML

echo 'echo materialize' > "${TMP}/scripts/materialize-kde-tier2-kmime-legacy-provider.sh"
echo 'echo build' > "${TMP}/scripts/run-kde-tier2-kmime-legacy-provider-build.sh"
echo base > "${TMP}/docs/provider.md"

git -C "${TMP}" init -q
git -C "${TMP}" config user.name test
git -C "${TMP}" config user.email test@example.invalid
git -C "${TMP}" add .
git -C "${TMP}" commit -qm base
BASE="$(git -C "${TMP}" rev-parse HEAD)"

expect_rc() {
  local want="$1" before="$2" after="$3" label="$4" rc
  set +e
  bash "${TMP}/scripts/kde-tier2-kmime-legacy-provider-needed.sh" "${before}" "${after}" >"${TMP}/${label}.log" 2>&1
  rc=$?
  set -e
  if [[ "${rc}" -ne "${want}" ]]; then
    cat "${TMP}/${label}.log" >&2
    echo "${label}: expected ${want}, got ${rc}" >&2
    exit 1
  fi
}

python3 - "${TMP}/manifests/kde-tier2-kmime-legacy-provider.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["state"]="PASS"; d["build_evidence"]={"result":"PASS"}; open(p,"w").write(json.dumps(d,indent=2)+"\n")
PY
git -C "${TMP}" add .
git -C "${TMP}" commit -qm evidence
EVIDENCE="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${BASE}" "${EVIDENCE}" evidence_only

python3 - "${TMP}/manifests/kde-tier2-kmime-legacy-provider.json" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d["adaptation"]["new_dependency"]="changed-provider"; open(p,"w").write(json.dumps(d,indent=2)+"\n")
PY
git -C "${TMP}" add .
git -C "${TMP}" commit -qm semantic
SEMANTIC="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${EVIDENCE}" "${SEMANTIC}" semantic_manifest

echo '# implementation change' >> "${TMP}/scripts/run-kde-tier2-kmime-legacy-provider-build.sh"
git -C "${TMP}" add .
git -C "${TMP}" commit -qm runner
RUNNER="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${SEMANTIC}" "${RUNNER}" runner

python3 - "${TMP}/.github/workflows/kde-tier2-kmime-legacy-provider.yml" <<'PY'
import sys
p=sys.argv[1]; s=open(p).read(); s=s.replace("echo rootfs","echo changed-rootfs"); open(p,"w").write(s)
PY
git -C "${TMP}" add .
git -C "${TMP}" commit -qm workflow
WORKFLOW="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 0 "${RUNNER}" "${WORKFLOW}" workflow_build_semantics

echo more >> "${TMP}/docs/provider.md"
git -C "${TMP}" add .
git -C "${TMP}" commit -qm docs
DOCS="$(git -C "${TMP}" rev-parse HEAD)"
expect_rc 1 "${WORKFLOW}" "${DOCS}" docs_only

echo "KDE Tier 2 KMime legacy-provider semantic scope: PASS"

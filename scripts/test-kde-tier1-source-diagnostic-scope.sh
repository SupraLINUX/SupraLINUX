#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
cd "${TMP}"
git init -q
git config user.email test@supralinux.invalid
git config user.name SupraLINUX-Test
mkdir -p manifests scripts .github/workflows docs
cp "${ROOT}/manifests/kde-tier1-source-diagnostic.json" manifests/
cp "${ROOT}/manifests/kde-frameworks-tier1-dependencies.json" manifests/
cp "${ROOT}/scripts/kde-tier1-source-diagnostic-needed.sh" scripts/
printf '#!/bin/sh\n' > scripts/run-kde-tier1-source-diagnostic.sh
printf 'name: diagnostic\n' > .github/workflows/kde-tier1-source-diagnostic.yml
printf 'baseline\n' > docs/readme.md
git add . && git commit -qm baseline
BASE="$(git rev-parse HEAD)"

expect_skip() {
  local before="$1" after="$2" node="$3"
  if scripts/kde-tier1-source-diagnostic-needed.sh "${before}" "${after}" "${node}"; then
    echo "${node}: unexpectedly triggered" >&2; exit 1
  else
    local rc=$?; [[ "${rc}" -eq 1 ]] || exit "${rc}"
  fi
}
expect_run() {
  scripts/kde-tier1-source-diagnostic-needed.sh "$1" "$2" "$3"
}

printf 'docs only\n' >> docs/readme.md
git add docs && git commit -qm docs-only
DOCS="$(git rev-parse HEAD)"
expect_skip "${BASE}" "${DOCS}" kconfig
expect_skip "${BASE}" "${DOCS}" ki18n

git reset --hard -q "${BASE}"
python3 - <<'PY'
import json
p='manifests/kde-tier1-source-diagnostic.json'; d=json.load(open(p))
d['nodes']['kconfig']['provider_packages'].append('sentinel-provider')
open(p,'w').write(json.dumps(d,indent=2)+'\n')
PY
git add manifests && git commit -qm kconfig-only
KCONFIG="$(git rev-parse HEAD)"
expect_run "${BASE}" "${KCONFIG}" kconfig
expect_skip "${BASE}" "${KCONFIG}" ki18n
expect_skip "${BASE}" "${KCONFIG}" sonnet

git reset --hard -q "${BASE}"
python3 - <<'PY'
import json
p='manifests/kde-tier1-source-diagnostic.json'; d=json.load(open(p))
d['last_campaign']={'workflow_run':999}
open(p,'w').write(json.dumps(d,indent=2)+'\n')
PY
git add manifests && git commit -qm evidence-only
EVIDENCE="$(git rev-parse HEAD)"
expect_skip "${BASE}" "${EVIDENCE}" kconfig
expect_skip "${BASE}" "${EVIDENCE}" ki18n

git reset --hard -q "${BASE}"
python3 - <<'PY'
import json
p='manifests/kde-tier1-source-diagnostic.json'; d=json.load(open(p))
d['provider_platform']='changed-common-provider'
open(p,'w').write(json.dumps(d,indent=2)+'\n')
PY
git add manifests && git commit -qm common-manifest
COMMON="$(git rev-parse HEAD)"
expect_run "${BASE}" "${COMMON}" kconfig
expect_run "${BASE}" "${COMMON}" ki18n

git reset --hard -q "${BASE}"
printf '# changed\n' >> scripts/run-kde-tier1-source-diagnostic.sh
git add scripts && git commit -qm runner-change
RUNNER="$(git rev-parse HEAD)"
expect_run "${BASE}" "${RUNNER}" kconfig
expect_run "${BASE}" "${RUNNER}" prison

echo "KDE Tier 1 per-node source diagnostic scope selector: PASS"

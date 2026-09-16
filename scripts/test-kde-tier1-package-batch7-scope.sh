#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
cd "${TMP}"
git init -q
git config user.email test@supralinux.invalid
git config user.name SupraLINUX-Test
mkdir -p manifests scripts packages/kde/kcalendarcore/debian .github/workflows
cp "${ROOT}/manifests/kde-tier1-package-campaign-batch7.json" manifests/
cp "${ROOT}/scripts/kde-tier1-package-batch7-needed.sh" scripts/
printf 'baseline\n' > packages/kde/kcalendarcore/debian/control
printf 'baseline\n' > .github/workflows/kde-tier1-package-batch7.yml
printf '#!/bin/sh\n' > scripts/run-kde-tier1-package-batch7-preflight.sh
git add .
git commit -qm baseline
BASE="$(git rev-parse HEAD)"

python3 - <<'PY'
import json
from pathlib import Path
p=Path("manifests/kde-tier1-package-campaign-batch7.json")
d=json.loads(p.read_text())
d["nodes"]["kcalendarcore"]["evidence"]=[{"result":"PASS","workflow_run":1}]
d["nodes"]["kcalendarcore"]["state"]="PASS"
d["nodes"]["kcalendarcore"]["downstream_eligible"]=True
p.write_text(json.dumps(d,indent=2)+"\n")
PY
git add manifests
git commit -qm evidence-only
EVIDENCE="$(git rev-parse HEAD)"
if scripts/kde-tier1-package-batch7-needed.sh kcalendarcore "${BASE}" "${EVIDENCE}"; then
  echo "evidence-only delta incorrectly triggered Batch 7" >&2
  exit 1
else
  rc=$?
  [[ "${rc}" -eq 1 ]] || exit "${rc}"
fi

git reset --hard -q "${BASE}"
python3 - <<'PY'
import json
from pathlib import Path
p=Path("manifests/kde-tier1-package-campaign-batch7.json")
d=json.loads(p.read_text())
d["nodes"]["kcalendarcore"]["source_sha256"]="0"*64
p.write_text(json.dumps(d,indent=2)+"\n")
PY
git add manifests
git commit -qm contract-change
CONTRACT="$(git rev-parse HEAD)"
scripts/kde-tier1-package-batch7-needed.sh kcalendarcore "${BASE}" "${CONTRACT}"

git reset --hard -q "${BASE}"
printf 'changed\n' >> packages/kde/kcalendarcore/debian/control
git add packages
git commit -qm package-change
PACKAGE="$(git rev-parse HEAD)"
scripts/kde-tier1-package-batch7-needed.sh kcalendarcore "${BASE}" "${PACKAGE}"

echo "KDE Tier 1 Batch 7 scope selector: PASS"

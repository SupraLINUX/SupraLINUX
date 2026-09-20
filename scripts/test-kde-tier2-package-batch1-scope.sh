#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEL="${ROOT}/scripts/kde-tier2-package-batch1-needed.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
cd "${TMP}"; git init -q; git config user.email test@supralinux.invalid; git config user.name test
mkdir -p manifests scripts packages/kde/kauth .github/workflows docs
cp "${ROOT}/manifests/kde-tier2-package-campaign-batch1.json" manifests/
cp "${SEL}" scripts/
printf '# runner\n' > scripts/run-kde-tier2-package-batch1-preflight.sh
printf '# audit\n' > scripts/audit-kde-development-contract.py
printf 'package\n' > packages/kde/kauth/control
printf 'workflow\n' > .github/workflows/kde-tier2-package-batch1.yml
git add .; git commit -qm baseline; BASE="$(git rev-parse HEAD)"

python3 - <<'PY'
import json
p='manifests/kde-tier2-package-campaign-batch1.json'; d=json.load(open(p))
d['state']='PASS'; d['nodes']['kauth']['state']='PASS'; d['nodes']['kauth']['last_result']='PASS'; d['nodes']['kauth']['downstream_eligible']=True
open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm planning; P="$(git rev-parse HEAD)"
if "${SEL}" "${BASE}" "${P}"; then echo "planning-only change triggered KAuth" >&2; exit 1; else rc=$?; [[ "${rc}" -eq 1 ]]; fi

git reset --hard -q "${BASE}"; echo changed >> packages/kde/kauth/control; git add .; git commit -qm package
"${SEL}" "${BASE}" "$(git rev-parse HEAD)"

git reset --hard -q "${BASE}"; python3 - <<'PY'
import json
p='manifests/kde-tier2-package-campaign-batch1.json'; d=json.load(open(p)); d['nodes']['kauth']['source_sha256']='0'*64; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm contract
"${SEL}" "${BASE}" "$(git rev-parse HEAD)"

git reset --hard -q "${BASE}"; echo note > docs/note.md; git add .; git commit -qm docs
if "${SEL}" "${BASE}" "$(git rev-parse HEAD)"; then echo "docs-only change triggered KAuth" >&2; exit 1; else rc=$?; [[ "${rc}" -eq 1 ]]; fi
echo "KDE Tier 2 Batch 1 scope selector: PASS"

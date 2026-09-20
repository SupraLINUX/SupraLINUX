#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SEL="${ROOT}/scripts/kde-tier2-package-batch1-needed.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "${TMP}"' EXIT
cd "${TMP}"; git init -q; git config user.email test@supralinux.invalid; git config user.name test
mkdir -p manifests scripts packages/kde/kauth .github/workflows docs
cp "${ROOT}/manifests/kde-tier2-package-campaign-batch1.json" manifests/
cp "${ROOT}/manifests/kde-tier2-package-batch1-attempts.json" manifests/
cp "${SEL}" scripts/
printf '# runner\n' > scripts/run-kde-tier2-package-batch1-preflight.sh
printf '# audit\n' > scripts/audit-kde-development-contract.py
printf 'package\n' > packages/kde/kauth/control
printf 'workflow\n' > .github/workflows/kde-tier2-package-batch1.yml
git add .; git commit -qm baseline; BASE="$(git rev-parse HEAD)"

# Current revision is intentionally unattempted. Even a docs-only event must
# keep the runnable remediation alive after a superseded/cancelled run.
echo note > docs/unattempted.md
git add .; git commit -qm unattempted-docs
UNATTEMPTED="$(git rev-parse HEAD)"
"${SEL}" "${BASE}" "${UNATTEMPTED}"

# Once the current revision has a real attempt, return to ordinary delta scope.
git reset --hard -q "${BASE}"
python3 - <<'PY'
import json
p='manifests/kde-tier2-package-batch1-attempts.json'
d=json.load(open(p))
v=json.load(open('manifests/kde-tier2-package-campaign-batch1.json'))['nodes']['kauth']['package_version']
d['real_attempts']['kauth'].append({'attempt':999,'package_version':v,'package_attempted':True,'result':'FAIL'})
open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm attempted-baseline; ATTEMPTED="$(git rev-parse HEAD)"

python3 - <<'PY'
import json
p='manifests/kde-tier2-package-campaign-batch1.json'; d=json.load(open(p))
d['state']='PASS'; d['nodes']['kauth']['state']='PASS'; d['nodes']['kauth']['last_result']='PASS'; d['nodes']['kauth']['downstream_eligible']=True
open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm planning; P="$(git rev-parse HEAD)"
if "${SEL}" "${ATTEMPTED}" "${P}"; then echo "planning-only change triggered already-attempted KAuth" >&2; exit 1; else rc=$?; [[ "${rc}" -eq 1 ]]; fi

git reset --hard -q "${ATTEMPTED}"; echo changed >> packages/kde/kauth/control; git add .; git commit -qm package
"${SEL}" "${ATTEMPTED}" "$(git rev-parse HEAD)"

git reset --hard -q "${ATTEMPTED}"; python3 - <<'PY'
import json
p='manifests/kde-tier2-package-campaign-batch1.json'; d=json.load(open(p)); d['nodes']['kauth']['source_sha256']='0'*64; open(p,'w').write(json.dumps(d))
PY
git add .; git commit -qm contract
"${SEL}" "${ATTEMPTED}" "$(git rev-parse HEAD)"

git reset --hard -q "${ATTEMPTED}"; echo note > docs/attempted.md; git add .; git commit -qm docs
if "${SEL}" "${ATTEMPTED}" "$(git rev-parse HEAD)"; then echo "docs-only change triggered already-attempted KAuth" >&2; exit 1; else rc=$?; [[ "${rc}" -eq 1 ]]; fi

echo "KDE Tier 2 Batch 1 scope selector: PASS"

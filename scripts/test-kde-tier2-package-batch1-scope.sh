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

# Synthesize a pending current revision with no real attempt, regardless of
# the repository's current canonical PASS state.
python3 - <<'PY'
import json
cp='manifests/kde-tier2-package-campaign-batch1.json'
ap='manifests/kde-tier2-package-batch1-attempts.json'
c=json.load(open(cp)); a=json.load(open(ap)); n=c['nodes']['kauth']; v=n['package_version']
c['state']='remediation-pending-build'; n['state']='remediation-pending-build'; n['last_result']='FAIL'; n['downstream_eligible']=False; n.pop('pass_evidence',None)
a['real_attempts']['kauth']=[x for x in a['real_attempts']['kauth'] if not (x.get('package_version')==v and x.get('package_attempted') is True)]
open(cp,'w').write(json.dumps(c))
open(ap,'w').write(json.dumps(a))
PY
git add .; git commit -qm baseline; BASE="$(git rev-parse HEAD)"

mkdir -p docs; echo note > docs/unattempted.md
git add .; git commit -qm unattempted-docs; UNATTEMPTED="$(git rev-parse HEAD)"
"${SEL}" "${BASE}" "${UNATTEMPTED}"

git reset --hard -q "${BASE}"
python3 - <<'PY'
import json
cp='manifests/kde-tier2-package-campaign-batch1.json'; ap='manifests/kde-tier2-package-batch1-attempts.json'
c=json.load(open(cp)); a=json.load(open(ap)); v=c['nodes']['kauth']['package_version']
a['real_attempts']['kauth'].append({'attempt':999,'package_version':v,'package_attempted':True,'result':'FAIL'})
open(ap,'w').write(json.dumps(a))
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

git reset --hard -q "${ATTEMPTED}"; mkdir -p docs; echo note > docs/attempted.md; git add .; git commit -qm docs
if "${SEL}" "${ATTEMPTED}" "$(git rev-parse HEAD)"; then echo "docs-only change triggered already-attempted KAuth" >&2; exit 1; else rc=$?; [[ "${rc}" -eq 1 ]]; fi

echo "KDE Tier 2 Batch 1 scope selector: PASS"

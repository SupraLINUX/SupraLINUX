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
git add .
git commit -qm baseline
BASE="$(git rev-parse HEAD)"

printf 'docs only\n' >> docs/readme.md
git add docs && git commit -qm docs-only
DOCS="$(git rev-parse HEAD)"
if scripts/kde-tier1-source-diagnostic-needed.sh "${BASE}" "${DOCS}"; then
    echo "docs-only delta incorrectly triggered source diagnostic" >&2
    exit 1
else
    rc=$?; [[ "${rc}" -eq 1 ]] || exit "${rc}"
fi

git reset --hard -q "${BASE}"
printf '\n' >> manifests/kde-tier1-source-diagnostic.json
git add manifests && git commit -qm diagnostic-manifest
scripts/kde-tier1-source-diagnostic-needed.sh "${BASE}" "$(git rev-parse HEAD)"

git reset --hard -q "${BASE}"
printf '\n' >> manifests/kde-frameworks-tier1-dependencies.json
git add manifests && git commit -qm provider-manifest
scripts/kde-tier1-source-diagnostic-needed.sh "${BASE}" "$(git rev-parse HEAD)"

git reset --hard -q "${BASE}"
printf '# changed\n' >> scripts/run-kde-tier1-source-diagnostic.sh
git add scripts && git commit -qm runner-change
scripts/kde-tier1-source-diagnostic-needed.sh "${BASE}" "$(git rev-parse HEAD)"

echo "KDE Tier 1 source diagnostic scope selector: PASS"
